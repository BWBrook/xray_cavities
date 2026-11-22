"""Package the compact, public inputs to the paired 10–12 Myr energy budget."""

import argparse
import gzip
import hashlib
import io
import json
import math
import re
import tempfile
import zipfile
from pathlib import Path

from validate_pluto_particle_restart_pair import (
    parse_particle_header, read_restart_records, validate_particle_file_size,
)
from verify_entropy_restart_budget import ARMS, CASES, gate, history, read, require, snapshots


REPO = Path(__file__).resolve().parents[2]
RELEASE = REPO / "docs/science/assets/entropy_restart_protocol_2026-11-21/seed_validation_repair.json"
STAGE_FILES = ("rk_interval_regions.csv", "rk_window_regions.csv", "rk_interval_bins.csv.gz",
               "rk_window_bins.csv", "rk_verification.json")
SHARED_FIELDS = ("device", "inode", "size", "mtime_ns", "time_code")
HEX = re.compile(r"[a-f0-9]{64}")


def digest_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()


def source_hashes(raw):
    manifest = read(raw / "raw-sha256.json")
    for name, digest in manifest.items():
        path = Path(name)
        require(not path.is_absolute() and ".." not in path.parts and HEX.fullmatch(digest),
                f"invalid native receipt entry {name}")
        require(digest_file(raw / path) == digest, f"native receipt digest mismatch for {name}")
    return manifest


def check_pbs(raw):
    released = read(RELEASE)["replacement_submission"]["jobs"]
    finished = read(raw / "pbs-completion.json")
    by_id = {int(row["id"]): row for row in finished}
    require(len(by_id) == len(finished) == len(released) == 5, "expected five distinct PBS completions")
    for job in released:
        row = by_id[job["id"]]
        require(row["name"] == job["name"] and row["ncpus"] == job["ncpus"]
                and row["state"] == "F" and row["exit"] == 0, f"incomplete PBS job {job['id']}")
    return {row["name"]: int(row["id"]) for row in finished}


def build_receipts(raw, case, state, hashes):
    sources, compilers, products, results = {}, {}, {}, {}
    for arm in ARMS:
        base = raw / case / arm
        sources[arm] = read(base / "build-inputs.json")
        compilers[arm] = read(base / "compiler.json")
        products[arm] = {name: digest for digest, name in
                         (row.split() for row in (base / "build.sha256").read_text().splitlines())}
        src, compiler, built = sources[arm], compilers[arm], products[arm]
        require(all(HEX.fullmatch(v) for v in src.values()) and
                built["src/definitions.h"] == src["definitions.h"]
                and built["pluto"] == compiler["executable_sha256"] and compiler["checked_commands"] == 126
                and built["pluto.ini"] == hashes[f"{case}/{arm}/pluto.ini"] == state["paired_runtime_sha256"]
                and built["environment.ini"] == hashes[f"{case}/{arm}/environment.ini"],
                f"build, compiler or runtime mismatch for {case}/{arm}")
        results[arm] = {
            "definitions_sha256": src["definitions.h"], "executable_sha256": built["pluto"],
            "source_manifest_sha256": hashes[f"{case}/{arm}/build-inputs.json"],
            "build_receipt_sha256": hashes[f"{case}/{arm}/build.sha256"],
            "compiler_receipt_sha256": hashes[f"{case}/{arm}/compiler.json"],
        }
    on, off = (sources[arm] for arm in ARMS)
    require(on.keys() == off.keys() and {key for key in on if on[key] != off[key]} == {"definitions.h"},
            f"{case} paired source inventories differ beyond definitions.h")
    require(all(compilers["ON"][key] == compilers["OFF"][key]
                for key in ("checked_commands", "recipe_sha256", "wrappers"))
            and products["ON"]["environment.ini"] == products["OFF"]["environment.ini"]
            and products["ON"]["pluto"] != products["OFF"]["pluto"], f"{case} paired builds disagree")
    return {
        "source_files_per_arm": len(on), "differing_source_inputs": ["definitions.h"],
        "production_executable_sha256": state["original_executable_sha256"],
        "shared_compiler_recipe_sha256": compilers["ON"]["recipe_sha256"],
        "checked_compiler_commands": compilers["ON"]["checked_commands"],
        "shared_runtime_ini_sha256": state["paired_runtime_sha256"],
        "shared_environment_ini_sha256": products["ON"]["environment.ini"], "arms": results,
    }


def seed_receipt(raw, case, state, seed, control, hashes):
    fluid, restart, particle = (seed[key] for key in ("fluid_hdf5", "fluid_restart", "particle_restart"))
    name = f"{case}/seed/particles.1000.dbl"
    path = raw / name
    header = parse_particle_header(path)
    validate_particle_file_size(path, header)
    count = header.nparticles
    fields = set(control["unequal_cells_full_grid"])
    require(header.step_number == particle["stepNumber"] == restart["nstep"] and
            header.time == particle["time"] and abs(header.time - fluid["time"]) <= seed["time_atol"] and
            fluid["time"] == restart["time"] == state["restart_time_code"] and
            particle["nparticles"] == particle["content"]["unique_ids"] == particle["content"]["records_scanned"]
            == control["particle_count_at_restart"] == count and set(fluid["datasets"]) == fields and
            set(seed["production_float_check"]) == fields and math.prod(fluid["shape"]) == 934502400 and
            hashes[name] == seed["input_sha256"]["particle_restart"], f"{case} native seed mismatch")
    return {
        "step": restart["nstep"], "time_code": fluid["time"], "shape_zyx": fluid["shape"],
        "fluid_double_bytes": fluid["size_bytes"], "unique_particle_ids": count,
        "particle_bytes": path.stat().st_size, "seed_input_sha256": seed["input_sha256"],
        "seed_validation_sha256": hashes[f"{case}/seed-validation.json"],
        "production_float_comparison": seed["production_float_check"],
    }


def series_receipt(root, case, arm, seed, summary, native, hashes):
    base = root / "raw" / case / arm
    label = f"{case}/{arm}"
    cat, ages = history(root, case, arm, seed)
    series = read(base / "series.json")
    first, last = series["diagnostic_first_step"], series["diagnostic_last_step"]
    rk = summary[label]
    records = read_restart_records(base / "outputs/restart.out")
    double = [line.split() for line in (base / "outputs/dbl.h5.out").read_text().splitlines()]
    require(len(double) == len(records) == 4 and [int(row[0]) for row in double] == list(range(4)),
            f"{label} double catalogue")
    initial, final = records[2:]
    require((initial.nfiles[2], initial.nfiles[3], initial.nfiles[8]) == (2, 10, 1000) and
            (final.nfiles[2], final.nfiles[3], final.nfiles[8]) == (3, 30, 1200) and
            initial.nstep == first == rk["first_step"] == native["first_step"] == cat[10] and
            final.nstep == cat[30] == int(double[-1][3]) == last + 1 and
            last == rk["last_completed_step"] == native["last_step"] and
            rk["accepted_steps"] == final.nstep - initial.nstep and
            initial.time == seed["fluid_hdf5"]["time"] and final.time == native["final_double_time_code"] and
            abs(float(double[-1][1]) - final.time) < 0.001 and
            native["final_double_bytes"] == seed["fluid_hdf5"]["size_bytes"] == 67318639276 and
            native["particle_files"] == final.nfiles[8] - initial.nfiles[8] + 1 == 201 and
            native["ranks"] == 1792 and series["particle_count"] == seed["particle_restart"]["nparticles"],
            f"{label} restart, series, RK, particle or final double evidence disagrees")
    require(rk["raw_csv_sha256"] == hashes[f"{label}/outputs/entropy_rk_{first}.csv"] and
            rk["receipt_sha256"] == {"series.json": hashes[f"{label}/series.json"],
                                     "restart.json": hashes[f"{case}/restart.json"],
                                     "flt.h5.out": hashes[f"{label}/outputs/flt.h5.out"]},
            f"{label} RK source provenance")
    return {
        "new_float_outputs": len(ages)-1, "new_float_index_range": [11, 30],
        "float_catalogue_sha256": hashes[f"{label}/outputs/flt.h5.out"],
        "series_sha256": hashes[f"{label}/series.json"], "accepted_steps": rk["accepted_steps"],
        "particle_files_including_seed": native["particle_files"], "particles_restored": series["particle_count"],
        "ranks": native["ranks"], "final_double_index": final.nfiles[2], "final_double_step": final.nstep,
        "final_double_time_code": final.time, "final_double_bytes": native["final_double_bytes"],
        "double_catalogue_sha256": hashes[f"{label}/outputs/dbl.h5.out"],
        "integrator_records_sha256": hashes[f"{label}/outputs/restart.out"],
    }, cat, ages


def verify_inputs(root):
    raw = root / "raw"
    hashes = source_hashes(raw)
    jobs = check_pbs(raw)
    native = read(raw / "native-inventory.json")
    inventory = {(r["case"], r["arm"], r["index"]): r for r in native["outputs"]}
    distinct_files = {(r["device"], r["inode"]) for r in native["outputs"]}
    require(len(inventory) == len(native["outputs"]) == 84 and len(distinct_files) == 82,
            "expected 82 distinct native files at 84 catalogue positions")
    rk = read(root / "stages/rk_verification.json")
    members = ["raw/native-inventory.json", "raw/pbs-completion.json", *(f"stages/{x}" for x in STAGE_FILES)]
    cases = {}
    for case in CASES:
        control, seed = gate(raw, case)
        state = read(raw / case / "restart.json")
        require(state["case"] == case and all(inventory[case, "ON", 10][k] == inventory[case, "OFF", 10][k]
                for k in SHARED_FIELDS), f"{case} paired native seed identity")
        members.append(f"raw/{case}/gate.json")
        builds = build_receipts(raw, case, state, hashes)
        case_seed = seed_receipt(raw, case, state, seed, control, hashes)
        arms = {}
        for arm in ARMS:
            arm_info, cat, ages = series_receipt(root, case, arm, seed, rk, native["arms"][f"{case}_{arm}"], hashes)
            samples = snapshots(root, case, arm, cat, ages, inventory)
            require(arm != "ON" or (samples[10][0]["step"], samples[10][0]["time_code"]) ==
                    (control["control_step"], control["control_time"]), f"{case} 11-Myr control readout")
            arm_info["pbs_simulation_job"] = jobs[f"ent_cases_{arm.lower()}"]
            arms[arm] = arm_info
            for index in range(10 if arm == "ON" else 11, 31):
                members.extend(f"snapshots/{case}/{arm}/{kind}_{index}.json" for kind in ("grid", "injector"))
        cases[case] = {"seed": case_seed, "build": builds, "series": arms}
    for arm in ARMS:
        require(all(len({cases[case]["build"]["arms"][arm][key] for case in CASES}) == 1
                    for key in ("executable_sha256", "compiler_receipt_sha256", "source_manifest_sha256")),
                f"case executable, compiler or source digests differ for {arm}")
    overview = {
        "cases": cases, "distinct_grid_snapshots": 82, "distinct_injector_snapshots": 82,
        "shared_seeds": "Index 10 is stored once in each ON directory and used for both arms.",
        "final_double_evidence": "Native HDF5 time and byte count, double catalogue and integrator record.",
        "source_receipt_manifest_sha256": digest_file(raw / "raw-sha256.json"),
        "native_transport_archive_sha256": digest_file(root / "native-receipts.tar.gz"),
        "matched_source_receipts": len(hashes), "pbs_submission_receipt_sha256": digest_file(RELEASE),
    }
    return members, overview


def package(root, output):
    names, overview = verify_inputs(root)
    members = {name: (root / name).read_bytes() for name in names}
    snapshot_hashes = root / "staging/snapshot-hashes.json"
    measured = {name.replace("snapshots/", "results/", 1): hashlib.sha256(data).hexdigest()
                for name, data in members.items() if name.startswith("snapshots/")}
    require(len(measured) == 164 and measured == read(snapshot_hashes),
            "compact snapshots disagree with the remote per-member SHA-256 manifest")
    overview["remote_snapshot_manifest_sha256"] = digest_file(snapshot_hashes)
    members["verification.json"] = json_bytes(overview)
    for name, data in members.items():
        plain = gzip.decompress(data) if name.endswith(".gz") else data
        require(not re.search(rb'(?:^|[" =])/(?:[A-Za-z]|~)|@|\b(?:exec_host|exec_vnode|node_name)\b', plain),
                f"public member contains an absolute path, address or host field: {name}")
    members["SHA256SUMS"] = "".join(f"{hashlib.sha256(data).hexdigest()}  {name}\n"
                                   for name, data in sorted(members.items())).encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in sorted(members.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    encoded = buffer.getvalue()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        require(output.read_bytes() == encoded, f"existing compact receipt differs: {output}")
    else:
        with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
            target = Path(temporary) / output.name
            target.write_bytes(encoded)
            target.replace(output)
    return len(encoded), hashlib.sha256(encoded).hexdigest()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="native receipts, reduced stages and compact snapshot tree")
    parser.add_argument("output", type=Path, help="public compact_inputs.zip")
    args = parser.parse_args()
    size, digest = package(args.root, args.output)
    print(f"{digest}  {args.output.name}  ({size} bytes)")
