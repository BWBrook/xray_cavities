"""Package or replay public receipts for the registered C-LO and G-LO entropy tests."""

import argparse
import csv
import gzip
import hashlib
import json
import re
import tarfile
import tempfile
import zipfile
from pathlib import Path

from entropy_restart_budget import csv_data, read_json, run as integrate_budget
from package_entropy_restart_receipts import STAGE_FILES, build_receipts, digest_file, json_bytes, series_receipt
from reduce_entropy_restart_stages import CELLS
from score_low_power_entropy import ARMS, CLO_REFUTATION, FORECASTS, accepted_gate, labelled_power, require, score_tables


CODE = Path(__file__).resolve().parent
REGISTRATION = CODE.parents[1] / "docs/science/assets/low_power_entropy_restart_2026-11-23"
SNAPSHOTS = {f"snapshots/{case}/{arm}/{kind}_{index}.json" for case in FORECASTS for arm in ARMS
             for kind in ("grid", "injector") for index in range(10 if arm == "ON" else 11, 31)}
INPUTS = (SNAPSHOTS | {f"raw/{case}/gate.json" for case in FORECASTS} |
          {f"stages/{name}" for name in STAGE_FILES} | {"raw/native-inventory.json"})
OUTCOMES = {"budget/" + name for name in ("primary_intervals.csv", "primary_windows.csv", "method_windows.csv",
            "paired_windows.csv", "annual_sampling_windows.csv", "all_interval_methods.csv.gz")} | {
            "on_counter_windows.csv", "off_interval_scores.csv", "score.json"}
SUPPORT = {"terminal_SHA256SUMS", "native_SHA256SUMS", "verification.json"}
SOURCES = ("score_low_power_entropy.py", "reduce_entropy_restart_stages.py", "entropy_restart_budget.py")


def manifest(data):
    hashes = {}
    for line in data.decode().splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        require(match is not None, "malformed SHA-256 manifest")
        digest, name = match.groups()
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and name not in hashes,
                f"unsafe or duplicate manifest member {name}")
        hashes[name] = digest
    return hashes


def verify_files(root, hashes):
    for name, digest in hashes.items():
        require(digest_file(root / name) == digest, f"SHA-256 mismatch for {name}")


def retained_verification(receipts, held, scored):
    raw = receipts / "raw"
    submitted = read_json(REGISTRATION / "submission.json")
    readout = REGISTRATION / "readout_inputs.sha256"
    require(digest_file(held/"SHA256SUMS") == submitted["native_input_manifest_sha256"]
            and digest_file(held/"contract.json") == submitted["contract_sha256"]
            and digest_file(readout) == submitted["readout_manifest_sha256"], "held release differs from registration")
    verify_files(held, manifest((held / "SHA256SUMS").read_bytes()))
    registered_code = manifest(readout.read_bytes())
    verify_files(CODE, {p.removeprefix("readers/"): h for p, h in registered_code.items() if p.startswith("readers/")})
    transfer = manifest((receipts/"transfers.sha256").read_bytes())
    require(set(transfer) == {"native-receipts.tar.gz", "native-members.sha256", "scored.tar.gz"},
            "unexpected transfer manifest")
    verify_files(receipts, transfer)
    with tarfile.open(receipts/"scored.tar.gz", "r:gz") as archived:
        member = archived.getmember("scored/SHA256SUMS")
        require(member.isfile() and archived.extractfile(member).read() == (scored/"SHA256SUMS").read_bytes(),
                "terminal manifest differs from the transferred archive")
    native_hashes = manifest((receipts/"native-members.sha256").read_bytes())
    require({p.relative_to(raw).as_posix() for p in raw.rglob("*") if p.is_file()} == set(native_hashes),
            "native receipt list differs from the transfer")
    verify_files(raw, native_hashes)
    contract = read_json(held/"contract.json")["cases"]
    catalogue = read_json(scored/"raw/native-inventory.json")
    inventory = {(r["case"], r["arm"], r["index"]): r for r in catalogue["outputs"]}
    require(len(inventory) == len(catalogue["outputs"]) == 84 and
            len({(r["device"], r["inode"]) for r in inventory.values()}) == 82, "native float coverage")
    rk = read_json(scored/"stages/rk_verification.json")
    proof = {}
    for case in FORECASTS:
        gate = accepted_gate(scored/"raw", case)
        target = contract[case]
        state = read_json(raw/case/"restart.json")
        seed = read_json(raw/case/"seed-validation.json")
        fluid, part = seed["fluid_hdf5"], seed["particle_restart"]
        require(gate == read_json(raw/case/"gate.json") and gate["reference_sha256"] == target["float11_sha256"]
                and state["original_executable_sha256"] == target["binary_sha256"]
                and seed["status"] == "ok" and fluid["time"] == target["time10"] == state["restart_time_code"]
                and seed["fluid_restart"]["nstep"] == target["step10"] == part["stepNumber"]
                and gate["particle_count_at_restart"] == target["particle_count10"] == part["nparticles"]
                == part["content"]["unique_ids"] == part["content"]["records_scanned"]
                and seed["input_sha256"]["particle_restart"] == target["particle_sha256"]
                and seed["input_sha256"]["restart_out"] == target["restart_prefix_sha256"]
                and set(seed["production_float_check"]) == set(gate["relative_L1_in_affected_gas"])
                and all(f["cells_checked"] == CELLS for f in seed["production_float_check"].values()),
                f"{case} seed or control differs from its held contract")
        arms = {}
        for arm in ARMS:
            stats, steps, ages = series_receipt(receipts, case, arm, seed, rk, catalogue["arms"][f"{case}_{arm}"],
                                               native_hashes)
            for index, age in enumerate(ages, 10):
                native = inventory[case, arm, index]
                source_arm = "ON" if index == 10 else arm
                grid = read_json(scored/f"snapshots/{case}/{source_arm}/grid_{index}.json")
                require(native["step"] == grid["step"] == steps[index] and grid["age_myr"] == age,
                        f"{case}/{arm}/{index} capture differs from native history")
            arms[arm] = stats
        proof[case] = {"seed_validation_sha256": native_hashes[f"{case}/seed-validation.json"],
                       "seed_input_sha256": seed["input_sha256"], "seed_float_sha256": target["float10_sha256"],
                       "seed_production_float_check": seed["production_float_check"], "arms": arms,
                       "build": build_receipts(raw, case, state, native_hashes)}
    return {"registration": 3665, "contract_sha256": submitted["contract_sha256"],
            "native_input_manifest_sha256": submitted["native_input_manifest_sha256"],
            "readout_manifest_sha256": submitted["readout_manifest_sha256"], "terminal_job": 883305,
            "transfers_sha256": transfer, "terminal_manifest_sha256": digest_file(scored/"SHA256SUMS"),
            "native_catalogue_positions": len(inventory), "distinct_native_floats": len(SNAPSHOTS)//2,
            "cases": proof}


def pack(receipts, held, dest):
    scored = receipts/"scored"
    outcomes = (scored/"SHA256SUMS").read_bytes()
    listed = manifest(outcomes)
    require(set(listed) == INPUTS | OUTCOMES, "unexpected/missing terminal inputs or results")
    verify_files(scored, listed)
    members = {name: (scored / name).read_bytes() for name in INPUTS}
    members.update({"verification.json": json_bytes(retained_verification(receipts, held, scored)),
                    "native_SHA256SUMS": (receipts/"native-members.sha256").read_bytes(),
                    "terminal_SHA256SUMS": outcomes})
    for name, value in members.items():
        plain = gzip.decompress(value) if name.endswith(".gz") else value
        require(not re.search(rb'(?:^|[" =])/(?:[A-Za-z]|~)|@|\b(?:exec_host|exec_vnode|node_name)\b', plain),
                f"private path, address or host field in public member {name}")
    members["SHA256SUMS"] = "".join(f"{hashlib.sha256(b).hexdigest()}  {n}\n"
                                    for n, b in sorted(members.items())).encode()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        path = Path(tmp)/dest.name
        with zipfile.ZipFile(path, "w") as archive:
            for name, value in sorted(members.items()):
                info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                archive.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        if dest.exists():
            require(digest_file(dest) == digest_file(path), "destination already contains a different archive")
        else:
            path.rename(dest)


def score(root, out):
    for case in FORECASTS:
        accepted_gate(root/"raw", case)
    integrate_budget(root, out/"budget")
    with (out/"budget/primary_intervals.csv").open() as budgets, (root/"stages/rk_interval_regions.csv").open() as stages:
        annual, off = score_tables(list(csv.DictReader(budgets)), list(csv.DictReader(stages)))
    (out/"on_counter_windows.csv").write_bytes(csv_data(annual))
    (out/"off_interval_scores.csv").write_bytes(csv_data(off))
    summary = {"registration": 3665, "bipolar_label_erg_s": labelled_power("C-LO"),
               "source_sha256": {name: digest_file(CODE/name) for name in SOURCES},
               "counter_branches": ["entropy", "entropy_with_p_floor"], "clo_refutation_below": CLO_REFUTATION,
               "off_excludes_first_interval": True,
               "on_forecasts": {c: [r["score"] for r in annual if r["case"] == c and r["forecast"] is not None]
                                for c in FORECASTS},
               "clo_combined_net_below_threshold": next(r["below_clo_refutation_threshold"] for r in annual
                                                        if r["case"] == "C-LO" and r["forecast"] is None),
               "off_passes_out_of_19": {c: sum(r["score"] == "pass" for r in off if r["case"] == c)
                                        for c in FORECASTS}}
    (out/"score.json").write_bytes(json_bytes(summary))


def replay(archive_path, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as working:
        root, out = Path(working)/"input", Path(working)/"out"
        with zipfile.ZipFile(archive_path) as archive:
            expected = INPUTS | SUPPORT | {"SHA256SUMS"}
            require(len(archive.namelist()) == len(expected) and set(archive.namelist()) == expected,
                    "unexpected, missing or duplicated public member")
            listed = manifest(archive.read("SHA256SUMS"))
            require(set(listed) == INPUTS | SUPPORT, "incomplete public checksum manifest")
            for name, digest in listed.items():
                data = archive.read(name)
                require(hashlib.sha256(data).hexdigest() == digest, f"public checksum mismatch for {name}")
                target = root/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        terminal = manifest((root/"terminal_SHA256SUMS").read_bytes())
        proof = read_json(root/"verification.json")
        submitted = read_json(REGISTRATION/"submission.json")
        require(set(terminal) == INPUTS | OUTCOMES and all(terminal[n] == listed[n] for n in INPUTS)
                and proof["terminal_manifest_sha256"] == listed["terminal_SHA256SUMS"]
                and proof["transfers_sha256"]["native-members.sha256"] == listed["native_SHA256SUMS"]
                and all(proof[key] == submitted[key] for key in
                        ("contract_sha256", "native_input_manifest_sha256", "readout_manifest_sha256")),
                "public inputs disagree with original manifests")
        score(root, out)
        verify_files(out, {name: terminal[name] for name in OUTCOMES})
        if dest.is_dir() and any(dest.iterdir()):
            require({p.relative_to(dest).as_posix() for p in dest.rglob("*") if p.is_file()} == OUTCOMES,
                    "destination already contains other files")
            verify_files(dest, {name: terminal[name] for name in OUTCOMES})
        else:
            out.replace(dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    packing = commands.add_parser("pack", help="maintainer build from retained transfers and held simulation bundle")
    packing.add_argument("receipts", type=Path, help="directory containing raw/, scored/ and the transfer manifests")
    packing.add_argument("held", type=Path, help="registered simulation release directory with contract.json")
    packing.add_argument("zip", type=Path)
    reading = commands.add_parser("replay", help="recompute and verify all nine terminal results from the public ZIP")
    reading.add_argument("zip", type=Path)
    reading.add_argument("output", type=Path, help="new or empty output directory")
    args = parser.parse_args()
    if args.command == "pack":
        pack(args.receipts, args.held, args.zip)
        print(f"{digest_file(args.zip)}  {args.zip.name}  ({args.zip.stat().st_size} bytes)")
    else:
        replay(args.zip, args.output)
        print(f"Verified {len(INPUTS)} inputs and reproduced all {len(OUTCOMES)} terminal results in {args.output}")
