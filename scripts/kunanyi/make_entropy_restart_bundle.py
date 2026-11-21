"""Assemble the private deployable bundle from the verified production captures."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "private_archive"


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("destination", type=Path)
    p.add_argument("--work-root", required=True)
    p.add_argument("--core-root", required=True)
    p.add_argument("--reference-checkout", type=Path,
                   default=CAPTURES / "turn22_entropy/pluto-reference")
    p.add_argument("--include-cluster", action="store_true")
    args = p.parse_args()
    out = args.destination
    out.mkdir(parents=True, exist_ok=False)
    for name in ("stage_entropy_restart.py", "patch_entropy_restart.py",
                 "entropy_restart_diagnostics.h", "entropy_restart.pbs", "entropy_restart_cases.pbs",
                 "submit_entropy_restart.sh"):
        shutil.copyfile(ROOT / "scripts/kunanyi" / name, out / name)
    for name in ("check_entropy_restart_control", "validate_pluto_particle_restart_pair",
                 "measure_q031_fluxes", "pluto_h5_level3_ambient_extract",
                 "snapshot_energy", "select_common_age_hdf5"):
        shutil.copyfile(ROOT / "scripts/science" / (name + ".py"), out / (name + ".py"))
    inventory = json.loads((CAPTURES / "turn15_native_identity_2026-11-05_r1/inventory.json").read_text())
    oracle = json.loads((CAPTURES / "turn21_injector/solver_check/replay_manifest.json").read_text())
    witness = ROOT / ("docs/science/assets/g_hi_full_history_production_2026-08-20/"
                      "home_continuation_786326/completion/remote_logs/restart_pair_validation_job.json")
    ghi_hashes = json.loads(witness.read_text())["input_sha256"]
    build_log = ROOT / ("docs/science/assets/cluster_full_history_production_2026-08-17/"
                        "c_hi_completion/remote_logs/c_hi_full_history_production.out")
    build_lines = build_log.read_text().splitlines()
    (main_source,) = [line.split()[-1] for line in build_lines
                      if line.startswith("mpicc ") and line.endswith("/Src/main.c")]
    original_core = str(Path(main_source).parents[1])
    commands = sorted(line.replace(original_core, "@CORE@").split()
                      for line in build_lines if line.startswith("mpicc "))
    if len(commands) < 100 or sum("-o" in c and c[-1] == "pluto" for c in commands) != 1:
        raise ValueError("retained production build transcript is incomplete")
    wrappers = [next(line.split("=",1)[1] for line in build_lines if line.startswith(name+"="))
                for name in ("mpicc", "mpirun")]
    commit = oracle["pinned_core_commit"]
    git = ["git", "-C", str(args.reference_checkout)]
    active_files = {c[-1].removeprefix("@CORE@/") for c in commands if c[-1].startswith("@CORE@/")}
    directories = {str(Path(name).parent) for name in active_files}
    directories.update(word.removeprefix("-I@CORE@/") for c in commands for word in c if word.startswith("-I@CORE@/"))
    filenames = subprocess.check_output([*git, "ls-tree", "-r", "--name-only", commit, "Src"], text=True).splitlines()
    active_files.update(name for name in filenames if str(Path(name).parent) in directories
                        and (name.endswith(".h") or Path(name).name == "makefile"))
    active_files.update({"Config/Kunanyi.defs", *("Src/" + k for k in oracle["pinned_core_sha256"])})
    core_witnesses = {name: hashlib.sha256(subprocess.check_output([*git, "show", f"{commit}:{name}"])).hexdigest()
                      for name in sorted(active_files)}
    if any(core_witnesses["Src/" + k] != v for k, v in oracle["pinned_core_sha256"].items()):
        raise ValueError("compiled solver witnesses differ from the earlier native replay")
    cases = {}
    for case in (["G-HI", "C-HI"] if args.include_cluster else ["G-HI"]):
        parent = inventory["G-HI-early" if case == "G-HI" else case]
        prod = inventory["G-HI-late" if case == "G-HI" else case]
        hist = json.loads((CAPTURES / f"turn21_injector/native_stage_repair/requests/{case}/request.json").read_text())["history"]
        params = {}
        code = {}
        for binding in parent["files"].values():
            _, rel = binding["capture"].split("/problem/", 1) if "/problem/" in binding["capture"] else (None, "")
            if rel.startswith("src/"):
                code[rel] = binding["sha256"]
        for entry in prod["files"].values():
            rel = entry["capture"].partition("/problem/")[2]
            if rel in ("pluto.ini", "environment.ini") or ("/" not in rel and rel.endswith(".csv")):
                params[rel] = entry["sha256"]
        (atmosphere,) = [k for k in params if k.endswith(".csv")]
        if len(code) != 50 or hist[10]["index"] != 10 or hist[11]["index"] != 11:
            raise ValueError(f"incomplete retained source or history for {case}")
        c = dict(source_problem=parent["problem"], production=prod["problem"],
                 binary_sha256=prod["binary_sha256"], runtime_files=params, project_sources=code,
                 time10=hist[10]["time_code"], float10_sha256=hist[10]["native"]["sha256"],
                 step10=10011 if case == "G-HI" else 10183, atmosphere=atmosphere)
        if case == "G-HI":
            c.update(fluid_sha256=ghi_hashes["fluid_hdf5"], particle_sha256=ghi_hashes["particle_restart"])
        cases[case] = c
    cfg = dict(core_root=args.core_root, work_root=args.work_root, cases=cases,
               core_witnesses=core_witnesses, core_commit=commit,
               production_build_commands=commands, production_wrappers=wrappers)
    (out / "contract.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(out.iterdir())]
    (out / "SHA256SUMS").write_text("".join(lines))


if __name__ == "__main__":
    main()
