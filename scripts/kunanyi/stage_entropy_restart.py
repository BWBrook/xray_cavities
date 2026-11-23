"""Prepare immutable restart seeds, independent output trees and the common build inputs."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import h5py
import numpy as np

from check_entropy_restart_control import (
    FIELD_SHAPE, KNOWN_11, MPI_NODES, RANKS_PER_NODE, TIME_11, catalogue, labelled_power, runtime_power,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from validate_pluto_particle_restart_pair import RESTART_RECORD_SIZE, sha256_file, validate_restart_pair


FIELDS = ("rho", "prs", "tr1", "vx1", "vx2", "vx3")
PARTICLES = "id x1 x2 x3 vx1 vx2 vx3 tinj color tracer last_shock_time density pressure".split()
# With MXCSR FTZ enabled, the x86 cast rounds to 24 significant bits before
# testing for a tiny result. This tie rounds up to the smallest normal float.
FLOAT32_FTZ_BOUNDARY = float.fromhex("0x1.ffffffp-127")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def verified(path, expected):
    digest = sha256_file(path)
    if digest != expected:
        raise ValueError(f"identity mismatch for {path.name}: {digest} expected {expected}")
    return digest


def config_line(text, name, value):
    result, count = re.subn(r"^(" + re.escape(name) + r"[ \t]+)[^\n]+$",
                            lambda m: m[1] + value, text, flags=re.M)
    if count != 1:
        raise ValueError(f"expected one active {name} setting, found {count}")
    return result


def native_copy(source, dest, expected=None):
    shutil.copyfile(source, dest)
    if expected:
        verified(dest, expected)
    dest.chmod(0o444)


def compare_checkpoint_slab(values, stored, field, iz):
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        rounded = values.astype(np.float32)
    if not np.isfinite(rounded).all() or not np.isfinite(stored).all():
        raise ValueError(f"{field}: nonfinite checkpoint float at slab {iz}")
    flushed = (np.abs(values) < FLOAT32_FTZ_BOUNDARY) & (rounded != 0)
    count = int(np.count_nonzero(flushed))
    rounded[flushed] = np.copysign(np.float32(0), rounded[flushed])
    if not np.array_equal(rounded, stored):
        different = rounded != stored
        first = np.unravel_index(np.argmax(different), different.shape)
        raise ValueError(f"{field}: {np.count_nonzero(different)} native float discrepancies at "
                         f"slab {iz}, first offset {first}: expected {rounded[first]}, stored {stored[first]}")
    return count


def validate_case_contract(case, config, production):
    digest, step = KNOWN_11[case]
    expected = {"float11_sha256": digest, "step11": step, "time11": TIME_11[case],
                "label_power_erg_s": labelled_power(case), "mpi_nodes": MPI_NODES,
                "mpi_ranks_per_node": RANKS_PER_NODE, "mpi_ranks": MPI_NODES*RANKS_PER_NODE,
                "mpi_decomposition": "automatic"}
    if case.endswith("-LO"):
        required = set(expected) | {"particle_count10", "particle_sha256", "restart_prefix_sha256"}
        missing = required - config.keys()
        if missing or config.get("particle_count10", 0) <= 0:
            raise ValueError(f"{case}: incomplete low-power restart contract; missing {sorted(missing)}")
    for key, value in expected.items():
        if key in config and config[key] != value:
            raise ValueError(f"{case}: {key} differs from verified production")
    runtime_power(case, production / "pluto.ini")
    rows = catalogue(production / "outputs")
    for index, time, step in ((10, config["time10"], config["step10"]), (11, TIME_11[case], step)):
        if rows[index][2] != step or abs(rows[index][0] - time) > .001:
            raise ValueError(f"{case}: production float catalogue differs at index {index}")


def allocated_ranks(config, nodefile):
    hosts = Counter(nodefile.read_text().split())
    nodes = config.get("mpi_nodes", MPI_NODES)
    per_node = config.get("mpi_ranks_per_node", RANKS_PER_NODE)
    ranks = config.get("mpi_ranks", MPI_NODES*RANKS_PER_NODE)
    if ((nodes, per_node) != (MPI_NODES, RANKS_PER_NODE) or ranks != nodes*per_node
            or len(hosts) != nodes or set(hosts.values()) != {per_node}):
        raise ValueError("PBS allocation differs from the verified production MPI layout")
    return ranks


def seed_checkpoint(case_root, config, source):
    seed = case_root / "seed"
    seed.mkdir()
    orig = source / "outputs"
    fluid = "data.0002.dbl.h5"
    companion = "data.0010.flt.h5"
    particle = "particles.1000.dbl"
    for name, key in ((fluid, "fluid_sha256"), (companion, "float10_sha256"),
                      (particle, "particle_sha256")):
        native_copy(orig / name, seed / name, config.get(key))
    for name, last_index in (("flt.h5.out", 10), ("dbl.h5.out", 2)):
        rows = []
        for line in (orig / name).read_text().splitlines(keepends=True):
            if line.split() and line.split()[0].isdigit() and int(line.split()[0]) <= last_index:
                rows.append(line)
        if [int(x.split()[0]) for x in rows] != list(range(last_index + 1)):
            raise ValueError(f"invalid production catalogue prefix in {name}")
        (seed / name).write_text("".join(rows))
    raw = (orig / "restart.out").read_bytes()
    (seed / "restart.out").write_bytes(raw[:3 * RESTART_RECORD_SIZE])
    if "restart_prefix_sha256" in config:
        verified(seed / "restart.out", config["restart_prefix_sha256"])
    report = validate_restart_pair(
        restart_out=seed / "restart.out", fluid_restart_index=2, fluid_output_slot=2,
        particle_output_slot=8, expected_particle_index=1000, expected_record_count=3,
        expected_output_indices=[(3, 10)], particle_dir=seed, expected_step=config["step10"],
        fluid_hdf5=seed / fluid, fluid_catalogue=seed / "dbl.h5.out", fluid_timestep="Timestep_2",
        expected_fluid_hdf5_size=67318639276, expected_fluid_shape=FIELD_SHAPE,
        required_fluid_datasets=FIELDS, expected_field_names=PARTICLES,
        expected_field_dims=[1]*10+[3,1,1], nonnegative_fields=["density", "pressure"],
        hash_inputs=True,
    )
    if config.get("fluid_sha256") and report["input_sha256"]["fluid_hdf5"] != config["fluid_sha256"]:
        raise ValueError("10-Myr fluid digest disagrees with the validated historical restart")
    if "particle_count10" in config and report["particle_restart"]["nparticles"] != config["particle_count10"]:
        raise ValueError("10-Myr particle count differs from the captured production header")
    with h5py.File(seed / fluid) as dbl, h5py.File(seed / companion) as flt:
        d, f = dbl["Timestep_2"], flt["Timestep_10"]
        if float(d.attrs["Time"]) != float(f.attrs["Time"]) or float(d.attrs["Time"]) != config["time10"]:
            raise ValueError("checkpoint and accepted float history have different times")
        report["production_float_check"] = {}
        for field in FIELDS:
            a, b = d["vars"][field], f["vars"][field]
            if a.dtype.itemsize != 8 or b.dtype.itemsize != 4 or a.shape != b.shape:
                raise ValueError(f"unexpected native field types or shape for {field}")
            flushed = 0
            for iz in range(0, a.shape[0], 4):
                slab = slice(iz, iz+4)
                flushed += compare_checkpoint_slab(a[slab], b[slab], field, iz)
            report["production_float_check"][field] = {
                "cells_checked": int(a.size), "nonzero_numpy_casts_flushed_to_zero": flushed,
            }
    write_json(case_root / "seed-validation.json", report)
    return seed


def source_inventory(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(root.rglob("*")) if p.is_file()}


def build_commands(text, core):
    return sorted(line.replace(str(core), "@CORE@").split()
                  for line in text.splitlines() if line.startswith("mpicc "))


def check_build(stage_dir, arm):
    cfg = json.loads((stage_dir / "contract.json").read_text())
    lines = (arm / "build.log").read_text()
    actual = build_commands(lines, Path(cfg["work_root"]) / "core")
    if not actual or actual != cfg["production_build_commands"]:
        raise ValueError("compiler commands or link inputs differ from the production recipe")
    wrappers = (arm / "wrappers.txt").read_text().splitlines()
    if wrappers != cfg["production_wrappers"]:
        raise ValueError("compiler or MPI launcher is outside the original module stack")
    write_json(arm / "compiler.json", {
        "checked_commands":len(actual), "wrappers":wrappers,
        "recipe_sha256":hashlib.sha256(json.dumps(actual, separators=(",", ":")).encode()).hexdigest(),
        "executable_sha256":sha256_file(arm / "src" / "pluto"),
    })


def stage(staging, contract):
    stage_root = staging.resolve()
    cfg = json.loads(contract.read_text())
    run = Path(cfg["work_root"]).resolve()
    if stage_root == run or stage_root.is_relative_to(run):
        raise ValueError("stage controls must live outside the new output directory")
    for case, c in cfg["cases"].items():
        for key in ("source_problem", "production"):
            archive = Path(c[key]).resolve()
            if run == archive or run.is_relative_to(archive) or archive.is_relative_to(run):
                raise ValueError("the experiment directory overlaps the production source")
        validate_case_contract(case, c, Path(c["production"]))
    run.mkdir(parents=True, exist_ok=False)
    source = Path(cfg["core_root"])
    core = run / "core"
    for folder in ("Config", "Src"):
        shutil.copytree(source / folder, core / folder, symlinks=False,
                        ignore=shutil.ignore_patterns(".git", "*.o", "__pycache__"))
    before = source_inventory(core)
    for filename, digest in cfg["core_witnesses"].items():
        if before.get(filename) != digest:
            raise ValueError(f"core solver witness differs for {filename}")
    write_json(run / "core-before.json", before)
    # Apply the same passive measurement to the single core shared by both builds.
    subprocess.run([sys.executable, str(stage_root / "patch_entropy_restart.py"), "--pluto-dir",
                    str(core), "--receipt", str(run / "instrumentation.json")], check=True)
    write_json(run / "core-after.json", source_inventory(core))
    for case, config in cfg["cases"].items():
        croot = run / case
        croot.mkdir()
        original = Path(config["production"])
        parent = Path(config["source_problem"])
        verified(original / "pluto", config["binary_sha256"])
        for rel, digest in config["project_sources"].items():
            verified(parent / rel, digest)
        for rel, digest in config["runtime_files"].items():
            verified(original / rel, digest)
        seed = seed_checkpoint(croot, config, original)
        text = (original / "pluto.ini").read_text()
        text = config_line(text, "tstop", f"{12 * CODE_TIME_PER_MYR:.12f}")
        text = config_line(text, "flt.h5", f"{CODE_TIME_PER_MYR/10:.12f}  -1")
        for arm in ("ON", "OFF"):
            dest = croot / arm
            out = dest / "outputs"
            (out / "logs").mkdir(parents=True)
            for name in ("data.0002.dbl.h5", "data.0010.flt.h5", "particles.1000.dbl"):
                (out / name).symlink_to(seed / name)
            for name in ("restart.out", "dbl.h5.out", "flt.h5.out"):
                shutil.copyfile(seed / name, out / name)
            shutil.copyfile(original / "outputs/grid.out", out / "grid.out")
            for name in config["runtime_files"]:
                if name != "pluto.ini":
                    shutil.copyfile(original / name, dest / name)
            (dest / "pluto.ini").write_text(text)
            src = dest / "src"
            shutil.copytree(parent / "src", src, symlinks=False,
                            ignore=shutil.ignore_patterns("*.o", "*.a", "pluto", "outputs", ".git", "__pycache__"))
            defs = src / "definitions.h"
            content = defs.read_text()
            pat = r"^(#define\s+ENTROPY_SWITCH\s+)SELECTIVE\b"
            if len(re.findall(pat, content, flags=re.M)) != 1:
                raise ValueError("original build is not SELECTIVE")
            if arm == "OFF":
                defs.write_text(re.sub(pat, r"\g<1>NO", content, flags=re.M))
            for name in ("HD/mappers.c", "mappers3D.c", "Time_Stepping/rk_step.c"):
                if (src / Path(name).name).exists():
                    raise ValueError(f"local source shadows instrumented {name}")
            write_json(dest / "build-inputs.json", source_inventory(src))
        on = json.loads((croot / "ON/build-inputs.json").read_text())
        off = json.loads((croot / "OFF/build-inputs.json").read_text())
        if on.keys() != off.keys() or {k for k in on if on[k] != off[k]} != {"definitions.h"}:
            raise ValueError("arm sources differ beyond the entropy switch")
        state = {"case":case, "restart_time_code":config["time10"],
                   "atmosphere":config["atmosphere"], "original_executable_sha256":config["binary_sha256"],
                   "paired_runtime_sha256":hashlib.sha256(text.encode()).hexdigest()}
        state.update({k: config[k] for k in ("mpi_ranks", "mpi_nodes", "mpi_ranks_per_node", "mpi_decomposition",
                                             "label_power_erg_s", "time11", "step11", "float11_sha256",
                                             "particle_count10") if k in config})
        write_json(croot / "restart.json", state)
    print("Validated and staged " + ", ".join(cfg["cases"]))


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--allocated-ranks":
        cfg = json.loads(Path(sys.argv[2]).read_text())["cases"][sys.argv[3]]
        print(allocated_ranks(cfg, Path(sys.argv[4])))
        raise SystemExit(0)
    if len(sys.argv) == 4 and sys.argv[1] == "--check-build":
        check_build(Path(sys.argv[2]), Path(sys.argv[3]))
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", type=Path)
    parser.add_argument("contract", type=Path)
    args = parser.parse_args()
    stage(args.stage, args.contract)
