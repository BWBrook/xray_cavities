"""Run the original and instrumented PLUTO RK2 and HD mappers on manufactured stage inputs."""

import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import patch_entropy_restart as patch


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tracer_bin(tracer: float, rho: float) -> str:
    f = tracer / rho if rho > 0 else math.nan
    if not 0 <= f <= 1:
        return "invalid"
    for bound, name in ((.001, "f_le_0.001"), (.005, "f_0.001_0.005"), (.5, "f_0.005_0.5")):
        if f <= bound:
            return name
    return "f_gt_0.5"


def radius_bin(injector: int, radius: float) -> str:
    if injector:
        return "injector_flag"
    for bound, name in zip((.75, 5., 10., 25., 50., 100.),
                           ("r_lt_0.75", "r_0.75_5", "r_5_10", "r_10_25", "r_25_50", "r_50_100")):
        if radius < bound:
            return name
    return "r_ge_100"


def expected(arm: str, lines: list[str]) -> dict:
    totals = defaultdict(lambda: defaultdict(float))
    for line in lines:
        fields = line.split(",")
        if fields[0] != "input":
            continue
        stage, _, injector, flagged = map(int, fields[1:5])
        radius, dv, rho0, tracer, momentum, initial, entropy, gamma = map(float, fields[5:])
        row = totals[stage, radius_bin(injector, radius), tracer_bin(tracer, rho0)]
        row["cell_visits"] += 1
        rho = rho0
        if rho < 0:
            rho = .4
            row["density_floors"] += 1
            row["raw_density_floor_mass_code"] += (rho - rho0)*dv
        kinetic = .5*momentum**2/rho
        intermediate = initial
        if initial < 0:
            intermediate = kinetic + .25/(gamma - 1.)
            row["gas_energy_floors"] += 1
            row["raw_E_floor_gain"] += (intermediate - initial)*dv
        final = intermediate
        category = None
        if arm == "on" and flagged:
            p = entropy*rho**(gamma - 1.)
            row["entropy_visits"] += 1
            row["entropy_visits_with_negative_p_energy"] += (intermediate < kinetic)
            category = "entropy"
            if p < 0:
                p = .25
                row["p_entropy_floors"] += 1
                category = "entropy_with_p_floor"
            final = kinetic + p/(gamma - 1.)
        elif (gamma - 1.)*(intermediate - kinetic) < 0:
            final = kinetic + .25/(gamma - 1.)
            row["p_energy_floors"] += 1
            category = "p_energy_floor"
        if category:
            delta = (final - intermediate)*dv
            row[f"raw_{category}_{'gain' if delta >= 0 else 'loss'}"] += delta
        delta = (final - initial)*dv
        row[f"raw_cell_{'gain' if delta >= 0 else 'loss'}"] += delta
        weight = .5 if stage == 1 else 1.
        row["effective_net_code"] += weight*delta
        row["effective_cell_gross_code"] += weight*abs(delta)
    return totals


def audit(arm: str, ledger: Path, output: str) -> dict:
    lines = output.splitlines()
    expected_rows = expected(arm, lines)
    with ledger.open() as stream:
        rows = list(csv.DictReader(stream))
    keys = {(int(row["stage"]), row["radius_kpc"], row["tracer_fraction"]) for row in rows}
    if len(rows) != len(keys) or keys != set(expected_rows):
        raise ValueError("missing, duplicate or unexpected stage membership")
    residual = 0.
    per_stage = defaultdict(lambda: defaultdict(float))
    for row in rows:
        stage = int(row["stage"])
        key = stage, row["radius_kpc"], row["tracer_fraction"]
        if (row["entropy_switch"], float(row["rk_weight"])) != (("selective" if arm == "on" else "off"), (.5 if stage == 1 else 1.)):
            raise ValueError("switch or RK weighting differs")
        columns = list(row)
        for field in columns[columns.index("cell_visits"):columns.index("energy_unit_erg")]:
            value = float(row[field])
            error = abs(value - expected_rows[key][field])
            residual = max(residual, error)
            if not math.isclose(value, expected_rows[key][field], abs_tol=2e-13, rel_tol=1e-14):
                raise ValueError(f"{arm} {key} {field}: {value} vs {expected_rows[key][field]}")
            per_stage[stage][field] += value
    external_balance = float(next(line.split(",")[1] for line in lines if line.startswith("closure,")))
    effective = sum(fields["effective_net_code"] for fields in per_stage.values())
    if not math.isclose(external_balance, effective, abs_tol=2e-13, rel_tol=1e-14):
        raise ValueError(f"full RK step energy fails closure: {external_balance} vs {effective}")
    return {
        "independent_stage_rows": len(rows), "max_bin_absolute_error": residual,
        "final_minus_initial_minus_rk_transport": external_balance, "effective_sum": effective,
        "per_stage": per_stage, "ledger_sha256": sha(ledger),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pluto-dir", required=True, type=Path)
    parser.add_argument("--problem-src", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--cc", default="cc")
    args = parser.parse_args()
    src = args.pluto_dir.resolve() / "Src"
    problem = args.problem_src.resolve()
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=False)
    staged = work / "instrumented"
    for name in patch.SOURCE:
        dest = staged / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src.parent / name, dest)
    here = Path(__file__).resolve().parent
    subprocess.run([sys.executable, str(here / "patch_entropy_restart.py"), "--pluto-dir", str(staged),
                    "--receipt", str(work / "patch.json")], check=True)
    fixture = here / "entropy_restart_fixture.c"
    common = ("mappers3D.c", "arrays.c", "rbox.c")
    results = {}
    for arm in ("on", "off"):
        cfg = work / arm
        cfg.mkdir()
        definition = (problem / "definitions.h").read_text()
        if arm == "off":
            definition, count = re.subn(r"(#define\s+ENTROPY_SWITCH\s+)SELECTIVE\b", r"\g<1>NO", definition)
            if count != 1:
                raise ValueError("expected production selective entropy setting")
        (cfg / "definitions.h").write_text(definition)
        commands = {}
        streams = {}
        for build, native in (("original", src), ("instrumented", staged / "Src")):
            run = cfg / build
            run.mkdir()
            flags = [args.cc, "-std=c99", "-O2", "-ffunction-sections", "-fdata-sections",
                     "-Wl,-dead_strip" if sys.platform == "darwin" else "-Wl,--gc-sections"]
            for inc in (cfg, problem, problem / "Particles", native, src, src / "HD", src / "EOS/Ideal"):
                flags.extend(("-I", str(inc)))
            exe = run / "solver_fixture"
            sources = [str(fixture), *(str(src / name) for name in common),
                       str(native / "HD/mappers.c"), str(native / "Time_Stepping/rk_step.c")]
            subprocess.run(flags + sources + ["-lm", "-o", str(exe)], check=True)
            out = subprocess.check_output([str(exe), str(run)], text=True)
            (run / "native.txt").write_text(out)
            streams[build] = out
            commands[build] = sha(exe)
        if streams["original"] != streams["instrumented"]:
            raise ValueError(f"{arm}: instrumentation changed native stage input, final state or flags")
        results[arm] = audit(arm, cfg / "instrumented/entropy_rk_1234.csv", streams["original"])
        results[arm]["executable_sha256"] = commands
        results[arm]["bit_identical_native_fixture_stdout_sha256"] = sha(cfg / "original/native.txt")
    receipt = {
        "scope": "serial native AdvanceStep + 3D/HD mappers, manufactured transport, flags and boundary",
        "compiler": subprocess.check_output([args.cc, "--version"], text=True).splitlines()[0],
        "patch_receipt_sha256": sha(work / "patch.json"), "fixture_sha256": sha(fixture),
        "checker_sha256": sha(Path(__file__)), "native_sha256": {name: sha(src / name) for name in common},
        "results": results,
    }
    (work / "verification.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(work / "verification.json")


if __name__ == "__main__":
    main()
