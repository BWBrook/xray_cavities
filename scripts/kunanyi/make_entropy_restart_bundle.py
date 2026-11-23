"""Assemble the private deployable bundle from the verified production captures."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "private_archive"
IDENTITIES = CAPTURES / "turn15_native_identity_2026-11-05_r1"
ASSETS = ROOT / "docs/science/assets"
BUILD_OUTPUT = {
    "C-HI": "cluster_full_history_production_2026-08-17/c_hi_completion/remote_logs/c_hi_full_history_production.out",
    "C-LO": "cluster_full_history_production_2026-08-17/c_lo_completion/remote_logs/c_lo_full_history_production.out",
    "G-HI": "g_hi_full_history_production_2026-08-20/failure_786189/remote_logs/g_hi_full_history_production.out",
    "G-LO": "g_lo_matched_full_history_production_2026-08-23/remote_logs/g_lo_matched_full_history_production.out",
}
sys.path.insert(0, str(ROOT / "scripts/science"))
from validate_pluto_particle_restart_pair import RESTART_RECORD_SIZE, read_restart_records


def captured_text(record, pattern):
    entry, = [item for item in record["files"].values() if re.search(pattern, item["capture"])]
    data = (IDENTITIES / entry["capture"]).read_bytes()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"hash mismatch in retained {entry['capture']}")
    return data.decode()


def production_build(case, parent):
    log = ASSETS / BUILD_OUTPUT[case]
    lines = log.read_text().splitlines()

    def setting(name):
        value, = [line.partition("=")[2] for line in lines if line.startswith(name + "=")]
        return value

    main_source, = [line.split()[-1] for line in lines if line.startswith("mpicc ") and line.endswith("/Src/main.c")]
    original_core = str(Path(main_source).parents[1])
    commands = sorted(line.replace(original_core, "@CORE@").split() for line in lines if line.startswith("mpicc "))
    if len(commands) < 100 or sum("-o" in c and c[-1] == "pluto" for c in commands) != 1:
        raise ValueError(f"incomplete production build transcript for {case}")
    nodefile = captured_text(parent, r"/pbs_nodefile\.[^/]+$").splitlines()
    machinefile = captured_text(parent, r"/intelmpi_machinefile\.[^/]+$").splitlines()
    counts = Counter(machinefile)
    ranks_per_node, = set(counts.values())
    if (setting("CASE_ID") != case or setting("MPI_FLAVOR") != "intelmpi" or
            setting("RUN_ARGS").split() != ["-i", "pluto.ini", "-e", "environment.ini", "-maxtime", "47.5"] or
            nodefile != machinefile or len(nodefile) != int(setting("NRANKS"))):
        raise ValueError(f"unrecognised production layout or solver arguments for {case}")
    layout = dict(mpi_ranks=len(nodefile), mpi_nodes=len(counts), mpi_ranks_per_node=ranks_per_node,
                  mpi_decomposition="automatic", production_build_log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
    return commands, [setting("mpicc"), setting("mpirun")], layout


def low_power_seed(case, config, probe, probe_root):
    record_path = probe_root / case / "restart.out"
    raw = record_path.read_bytes()
    restart = read_restart_records(record_path)[2]
    particle = probe["particle_header"]
    if (probe["production"] != config["production"] or hashlib.sha256(raw).hexdigest() != probe["restart_sha256"]
            or len(raw) != probe["sizes"]["restart.out"] or restart.record_index != 2 or
            (restart.nfiles[2], restart.nfiles[3], restart.nfiles[8]) != (2, 10, 1000)
            or restart.nstep != config["step10"] or restart.time != config["time10"]
            or particle["step_number"] != restart.nstep or abs(particle["time"] - restart.time) > 0.005
            or particle["precision"] != "double" or particle["nparticles"] <= 0
            or particle["header_offset"] + 8 * particle["nelem"] * particle["nparticles"] != probe["sizes"]["particles.1000.dbl"]
            or not re.fullmatch(r"[0-9a-f]{64}", probe["particle_sha256"])):
        raise ValueError(f"{case} restart record, particle identity or seed time disagrees")
    for name, dtype, time, size in (("data.0002.dbl.h5", "float64", config["time10"], 67318639276),
                                    ("data.0010.flt.h5", "float32", config["time10"], 44890581676),
                                    ("data.0011.flt.h5", "float32", config["time11"], 44890581676)):
        h5 = probe["hdf5"][name]
        if (probe["sizes"][name] != size or h5["shape"] != [1014, 960, 960] or
                h5["fields"] != ["prs", "rho", "tr1", "vx1", "vx2", "vx3"] or
                h5["dtype"] != dtype or h5["time"] != time):
            raise ValueError(f"{case} {name} differs from the retained fluid history")
    if not any(re.search(r"Number of processors:\s+" + str(config["mpi_ranks"]) + "$", line)
               for line in probe["decomposition"]):
        raise ValueError(f"{case} solver log and historical rank count disagree")
    return dict(particle_count10=particle["nparticles"], particle_sha256=probe["particle_sha256"],
                restart_prefix_sha256=hashlib.sha256(raw[:3 * RESTART_RECORD_SIZE]).hexdigest())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("destination", type=Path)
    p.add_argument("--work-root", required=True)
    p.add_argument("--core-root", required=True)
    p.add_argument("--reference-checkout", type=Path,
                   default=CAPTURES / "turn22_entropy/pluto-reference")
    selection = p.add_mutually_exclusive_group()
    selection.add_argument("--include-cluster", action="store_true", help="G-HI and C-HI")
    selection.add_argument("--low-power", action="store_true", help="G-LO and C-LO")
    p.add_argument("--low-power-probe", type=Path, default=CAPTURES / "turn24_entropy_2026-11-23",
                   help="production_probe.json and the two original binary integrator catalogues")
    args = p.parse_args()
    if args.destination.exists():
        raise FileExistsError(args.destination)
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.destination.parent) as temp:
        out = Path(temp) / "bundle"
        out.mkdir()
        build(args, out)
        out.rename(args.destination)


def build(args, out):
    for name in ("stage_entropy_restart.py", "patch_entropy_restart.py",
                 "entropy_restart_diagnostics.h", "entropy_restart.pbs", "entropy_restart_cases.pbs",
                 "submit_entropy_restart.sh"):
        shutil.copyfile(ROOT / "scripts/kunanyi" / name, out / name)
    for name in ("check_entropy_restart_control", "validate_pluto_particle_restart_pair",
                 "measure_q031_fluxes", "pluto_h5_level3_ambient_extract",
                 "snapshot_energy", "select_common_age_hdf5"):
        shutil.copyfile(ROOT / "scripts/science" / (name + ".py"), out / (name + ".py"))
    inventory = json.loads((IDENTITIES / "inventory.json").read_text())
    oracle = json.loads((CAPTURES / "turn21_injector/solver_check/replay_manifest.json").read_text())
    selected = ("G-HI",)
    if args.low_power:
        selected = ("G-LO", "C-LO")
    elif args.include_cluster:
        selected = ("G-HI", "C-HI")
    builds = {case: production_build(case, inventory["G-HI-early" if case == "G-HI" else case])
              for case in selected}
    commands, wrappers, _ = builds[selected[0]]
    if any((cmd, mpi) != (commands, wrappers) for cmd, mpi, _ in builds.values()):
        raise ValueError("selected cases use different historical compiler commands or wrappers")
    if args.low_power:
        probe_path = args.low_power_probe / "production_probe.json"
        probe = json.loads(probe_path.read_bytes())["cases"]
        if set(probe) != set(selected):
            raise ValueError("the low-power probe must cover both production cases")
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
    for case in selected:
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
        catalogue = {int(line.split()[0]): line.split() for line in
                     captured_text(prod, r"/outputs/flt\.h5\.out$").splitlines() if line.strip()}
        if any(not math.isclose(float(catalogue[i][1]), hist[i]["time_code"], rel_tol=0, abs_tol=0.001)
               or hist[i]["native"]["path"] != str(Path(prod["problem"]) / "outputs" / f"data.{i:04d}.flt.h5")
               for i in (10, 11)):
            raise ValueError(f"native catalogue disagrees with the accepted 10/11-Myr histories for {case}")
        power, = [float(line.split()[1]) for line in captured_text(prod, r"/problem/pluto\.ini$").splitlines()
                  if line.split()[:1] == ["JET_PWR"]]
        c = dict(source_problem=parent["problem"], production=prod["problem"],
                 binary_sha256=prod["binary_sha256"], runtime_files=params, project_sources=code,
                 time10=hist[10]["time_code"], float10_sha256=hist[10]["native"]["sha256"],
                 time11=hist[11]["time_code"], float11_sha256=hist[11]["native"]["sha256"],
                 step10=int(catalogue[10][3]), step11=int(catalogue[11][3]), atmosphere=atmosphere,
                 label_power_erg_s=2 * power, **builds[case][2])
        if args.low_power:
            c.update(low_power_seed(case, c, probe[case], args.low_power_probe))
        if case == "G-HI":
            witness = ASSETS / ("g_hi_full_history_production_2026-08-20/"
                                "home_continuation_786326/completion/remote_logs/restart_pair_validation_job.json")
            ghi_hashes = json.loads(witness.read_text())["input_sha256"]
            c.update(fluid_sha256=ghi_hashes["fluid_hdf5"], particle_sha256=ghi_hashes["particle_restart"])
        cases[case] = c
    cfg = dict(core_root=args.core_root, work_root=args.work_root, cases=cases,
               core_witnesses=core_witnesses, core_commit=commit,
               production_build_commands=commands, production_wrappers=wrappers)
    if args.low_power:
        cfg["production_probe_sha256"] = hashlib.sha256(probe_path.read_bytes()).hexdigest()
    (out / "contract.json").write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n")
    lines = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in sorted(out.iterdir())]
    (out / "SHA256SUMS").write_text("".join(lines))


if __name__ == "__main__":
    main()
