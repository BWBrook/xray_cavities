"""Compare the 11-Myr entropy-ON fluid state with the canonical production output."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from pathlib import Path

import h5py
import numpy as np

from measure_q031_fluxes import parse_pluto_parameters, read_grid
from pluto_h5_level3_ambient_extract import (
    GAMMA_GAS, REQUIRED_DATASETS, UNIT_ENERGY_ERG, UNIT_LENGTH_CM, UNIT_VELOCITY_CMS,
    require_datasets,
)
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR, load_environment, sha256_file
from validate_pluto_particle_restart_pair import parse_particle_header


MAX_FIELD_L1 = 0.01
MAX_COMPONENT_L1_PER_INTERVAL = 0.005
LABEL_POWER = 2e45
OPERATIONS = ("E_floor", "entropy", "entropy_with_p_floor", "p_energy_floor")
KNOWN_11 = {
    "G-HI": ("5e427ae7ad1efdc7141ee5b03063157f7e6eb144f58fd8e36ce8e0317e564c01", 10990),
    "C-HI": ("198578a32ff2b7c48a45fff7bea768584dd286bdf5c88545654e0e236bcc3c05", 11159),
    "G-LO": ("fa7d48233007223f29b274fbba07847579cb563654d42e397e06a25337ecaf8c", 11526),
    "C-LO": ("fc03993609b51ac4cb208ade551d2113fd1ddce24b32af3d55c151b0392097b6", 12729),
}
TIME_11 = {"G-HI": 3372.5675539758126, "C-HI": 3372.3525100513866,
           "G-LO": 3372.414663985967, "C-LO": 3372.379435794779}
MPI_NODES, RANKS_PER_NODE = 64, 28
FIELD_SHAPE = (1014, 960, 960)


def paired_cases(case):
    if case not in KNOWN_11:
        raise ValueError(f"unknown production case {case!r}")
    power_class = case.split("-")[1]
    return f"G-{power_class}", f"C-{power_class}"


def labelled_power(case):
    return 2e43 if paired_cases(case)[0] == "G-LO" else LABEL_POWER


def runtime_power(case, ini):
    power = 2 * parse_pluto_parameters(ini)["JET_PWR"]
    if power != labelled_power(case):
        raise ValueError(f"{case}: runtime bipolar jet power differs from the production label")
    return power


def checked_particle_seed(arm):
    seed = json.loads((arm.parent / "seed-validation.json").read_text())
    path = arm / "outputs" / "particles.1000.dbl"
    if sha256_file(path) != seed["input_sha256"]["particle_restart"]:
        raise ValueError("particle restart differs from the validated seed")
    particle = parse_particle_header(path)
    if particle.nparticles != seed["particle_restart"]["nparticles"]:
        raise ValueError("particle count differs from the validated seed")
    return particle


def catalogue(directory):
    rows = [line.split() for line in (directory / "flt.h5.out").read_text().splitlines()
            if line.strip() and line.split()[0].isdigit()]
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError("duplicate output index in float catalogue")
    return {int(row[0]): (float(row[1]), float(row[2]), int(row[3])) for row in rows}


def check_series(arm):
    state = json.loads((arm.parent / "restart.json").read_text())
    outputs = arm / "outputs"
    rows = catalogue(outputs)
    new = sorted(i for i in rows if i > 10)
    if not new or new != list(range(11, new[-1] + 1)):
        raise ValueError("missing or nonconsecutive new native output indices")
    ages = []
    for index in new:
        file = outputs / f"data.{index:04d}.flt.h5"
        if file.is_symlink() or file.stat().st_size != 44890581676:
            raise ValueError(f"{file.name}: expected independent, full-sized native output")
        with h5py.File(file) as h5:
            group = f"Timestep_{index}"
            if require_datasets(h5, group) != FIELD_SHAPE:
                raise ValueError(f"{file.name}: production grid shape changed")
            t = float(h5[group].attrs["Time"])
            if not math.isclose(t, rows[index][0], abs_tol=.001, rel_tol=0):
                raise ValueError(f"{file.name}: catalogue time does not match native time")
            ages.append(t / CODE_TIME_PER_MYR)
    if (not all(b > a for a, b in zip(ages, ages[1:])) or abs(ages[-1] - 12) > 1e-8
            or any(min(abs(age - n/10) for age in ages) > .0015 for n in range(101, 121))):
        raise ValueError("native 0.1-Myr sampling or the 12-Myr endpoint is incomplete")
    particle = checked_particle_seed(arm)
    counts = []
    ranks = state.get("mpi_ranks", MPI_NODES * RANKS_PER_NODE)
    if ranks != MPI_NODES * RANKS_PER_NODE:
        raise ValueError("staged rank count differs from the verified production layout")
    for rank in range(ranks):
        log = (outputs / "logs" / f"pluto.{rank}.log").read_text(errors="replace")
        matches = re.findall(r"Restarted with (\d+) local particles", log)
        if len(matches) != 1 or "Continuing without restarting particles" in log:
            raise ValueError(f"rank {rank} did not confirm one particle restart")
        counts.append(int(matches[0]))
    if sum(counts) != particle.nparticles:
        raise ValueError("global restarted particle count differs from the checkpoint")
    (diagnostic,) = outputs.glob("entropy_rk_*.csv")
    start, end = None, None
    counts_by_stage = {}
    bins = set()
    expected_counts = dict.fromkeys((1, 2), math.prod(FIELD_SHAPE))
    step_time = None
    previous_end = None
    setting = "selective" if arm.name == "ON" else "off"
    with diagnostic.open() as stream:
        for row in csv.DictReader(stream):
            step = int(row["step"])
            if row["entropy_switch"] != setting:
                raise ValueError("instrumented entropy setting differs from arm label")
            if start is None:
                start = step
            if end != step:
                if end is not None and (step != end + 1 or counts_by_stage != expected_counts):
                    raise ValueError("missing diagnostic step, physical cells or RK stage")
                counts_by_stage = {}
                bins = set()
                previous_end = state["restart_time_code"] if step_time is None else step_time[1]
                step_time = None
            end = step
            stage = int(row["stage"])
            numbers = {k: float(v) for k, v in row.items()
                       if k not in ("radius_kpc", "tracer_fraction", "entropy_switch")}
            if not all(map(math.isfinite, numbers.values())) or numbers["energy_unit_erg"] <= 0:
                raise ValueError("nonfinite diagnostic entry or invalid energy unit")
            start_time, end_time, dt = (numbers[k] for k in ("time_start_code", "time_end_code", "dt_code"))
            timing = (start_time, end_time, dt)
            weight = numbers["rk_weight"]
            if (stage not in (1, 2) or weight != (0.5 if stage == 1 else 1.0) or dt <= 0
                    or not math.isclose(start_time, previous_end, rel_tol=0, abs_tol=1e-9)
                    or not math.isclose(start_time+dt, end_time, rel_tol=0, abs_tol=1e-9)
                    or (step_time is not None and timing != step_time)):
                raise ValueError("invalid RK time, stage or weight")
            step_time = timing
            net = numbers["raw_cell_gain"] + numbers["raw_cell_loss"]
            gross = numbers["raw_cell_gain"] - numbers["raw_cell_loss"]
            changes = [numbers[f"raw_{op}_{sign}"] for op in OPERATIONS for sign in ("gain", "loss")]
            tolerance = 1.e-9 * max(gross, sum(map(abs, changes)), 1.e-100)
            if (abs(sum(changes) - net) > tolerance or abs(numbers["effective_net_code"]-weight*net) > tolerance
                    or abs(numbers["effective_cell_gross_code"]-weight*gross) > tolerance):
                raise ValueError("RK-weighted or per-operation gas energy does not reconcile")
            key = (stage, row["radius_kpc"], row["tracer_fraction"])
            count = float(row["cell_visits"])
            if (key in bins or not count.is_integer() or count <= 0
                    or float(row["nonfinite_energy_visits"]) != 0):
                raise ValueError("invalid diagnostic cell totals, duplicate bin or nonfinite energy")
            bins.add(key)
            counts_by_stage[stage] = counts_by_stage.get(stage, 0) + int(count)
    if start != particle.step_number or end != rows[new[-1]][2] - 1 or counts_by_stage != expected_counts:
        raise ValueError("diagnostics do not cover every step from the seed to the endpoint")
    if not math.isclose(step_time[1] / CODE_TIME_PER_MYR, ages[-1], rel_tol=0, abs_tol=1e-8):
        raise ValueError("RK ledger does not reach the saved endpoint")
    result = dict(case=state["case"], arm=arm.name, new_indices=new, ages_myr=ages,
                  particle_count=sum(counts), diagnostic_first_step=start, diagnostic_last_step=end)
    (arm / "series.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


def compare_fields(reference, trial, original_grid, trial_grid, atmosphere, interval_label):
    ref_group = next(k for k in reference if k.startswith("Timestep_"))
    new_group = next(k for k in trial if k.startswith("Timestep_"))
    shape = require_datasets(reference, ref_group)
    if require_datasets(trial, new_group) != shape:
        raise ValueError("control and reference shapes differ")
    grid = read_grid(reference, shape, grid_file=original_grid)
    other = read_grid(trial, shape, grid_file=trial_grid)
    for axis in ("x", "y", "z", "x_edges", "y_edges", "z_edges"):
        if not np.array_equal(getattr(grid, axis), getattr(other, axis)):
            raise ValueError(f"grid mismatch on {axis}")
    fields = tuple(REQUIRED_DATASETS)
    errors = dict.fromkeys(fields, 0.0)
    norms = dict.fromkeys(fields, 0.0)
    unequal = dict.fromkeys(fields, 0)
    components = dict.fromkeys(("thermal", "kinetic", "potential"), 0.0)
    tags = [reference[ref_group]["vars"], trial[new_group]["vars"]]
    if any(g[f].dtype.kind != "f" or g[f].dtype.itemsize != 4 for g in tags for f in fields):
        raise ValueError("11-Myr comparison expects native single-precision fields")
    area = np.outer(grid.dy, grid.dx)
    rxy2 = grid.x[None, :] ** 2 + grid.y[:, None] ** 2
    speed_limit = 1e7 / UNIT_VELOCITY_CMS
    affected_cells = 0
    for iz, dz in enumerate(grid.dz):
        pair = [{f: g[f][iz].astype(np.float64) for f in fields} for g in tags]
        if any(not np.isfinite(a).all() for state in pair for a in state.values()):
            raise ValueError(f"nonfinite state in slab {iz}")
        if any((s["rho"] <= 0).any() or (s["prs"] <= 0).any() for s in pair):
            raise ValueError(f"nonpositive density or pressure in slab {iz}")
        speeds2 = [s["vx1"]**2 + s["vx2"]**2 + s["vx3"]**2 for s in pair]
        affected = ((pair[0]["tr1"] > 1e-3) | (pair[1]["tr1"] > 1e-3) |
                    (speeds2[0] >= speed_limit**2) | (speeds2[1] >= speed_limit**2))
        affected_cells += np.count_nonzero(affected)
        vol = area * dz
        weight = vol * affected
        for f in fields:
            x, y = pair[0][f], pair[1][f]
            errors[f] += np.sum(weight * np.abs(y - x))
            norms[f] += np.sum(weight * np.abs(x))
            unequal[f] += int(np.count_nonzero(x != y))
        r = np.sqrt(rxy2 + grid.z[iz]**2) * UNIT_LENGTH_CM
        phi = atmosphere.potential_at_radius(r) / UNIT_VELOCITY_CMS**2
        a, b = pair
        changes = {
            "thermal": (b["prs"] - a["prs"]) / (GAMMA_GAS - 1),
            "kinetic": 0.5 * (b["rho"]*speeds2[1] - a["rho"]*speeds2[0]),
            "potential": (b["rho"] - a["rho"]) * phi,
        }
        for name, difference in changes.items():
            components[name] += np.sum(vol * np.abs(difference))
    if not affected_cells or any(n <= 0 for n in norms.values()):
        raise ValueError("empty affected region or zero reference field norm")
    return {
        "affected_cells": int(affected_cells), "unequal_cells_full_grid": unequal,
        "relative_L1_in_affected_gas": {f: errors[f]/norms[f] for f in fields},
        "component_L1_per_labelled_interval": {
            k: v * UNIT_ENERGY_ERG / interval_label for k, v in components.items()
        },
    }


def check(case, production, arm):
    state = json.loads((arm.parent / "restart.json").read_text())
    if arm.name != "ON" or state["case"] != case:
        raise ValueError("control gate requires its case's ON arm")
    outputs, originals = arm / "outputs", production / "outputs"
    original_hash, original_step = KNOWN_11[case]
    ref_path = originals / "data.0011.flt.h5"
    if sha256_file(ref_path) != original_hash:
        raise ValueError("production 11-Myr file differs from the accepted native identity")
    ref_index = catalogue(originals)[11]
    if ref_index[2] != original_step:
        raise ValueError("production 11-Myr catalogue step differs from the accepted step")
    rows = {n: row for n, row in catalogue(outputs).items() if n > 10}
    idx = min(rows, key=lambda n: abs(rows[n][0] - ref_index[0]))
    file = outputs / f"data.{idx:04d}.flt.h5"
    if file.samefile(ref_path):
        raise ValueError("a linked production file cannot serve as a new control")
    log = (outputs / "logs" / "pluto.0.log").read_text(errors="replace")
    particle = checked_particle_seed(arm)
    if ("Restarting from Particle File" not in log or "particles.1000.dbl" not in log
            or f"building linked list of {particle.nparticles} particles" not in log
            or "Continuing without restarting particles" in log):
        raise ValueError("rank zero did not confirm the expected particle restart")
    with h5py.File(ref_path) as ref, h5py.File(file) as new:
        t0 = state["restart_time_code"]
        t1 = float(ref["Timestep_11"].attrs["Time"])
        t2 = float(new[f"Timestep_{idx}"].attrs["Time"])
        if (not all(map(math.isfinite, (t0, t1, t2))) or t1 != TIME_11[case] or not t1 > t0
                or abs(t1 - t2) > ref_index[1] or abs(rows[idx][2] - original_step) > 1):
            raise ValueError("11-Myr control is displaced by more than one native hydro step")
        profile = load_environment(arm / state["atmosphere"])
        power = runtime_power(case, arm / "pluto.ini")
        if state.get("label_power_erg_s", power) != power:
            raise ValueError("staged bipolar jet power differs from the runtime")
        interval = power * (t1 - t0) / CODE_TIME_PER_MYR * SECONDS_PER_MYR
        result = compare_fields(ref, new, originals / "grid.out", outputs / "grid.out", profile, interval)
    result.update(case=case, reference_sha256=original_hash, control_output=idx,
                  reference_step=original_step, control_step=rows[idx][2],
                  reference_time=t1, control_time=t2, particle_count_at_restart=particle.nparticles)
    if "label_power_erg_s" in state:
        result.update(labelled_power_erg_s=power, labelled_control_interval_erg=interval)
    result["passed"] = bool(max(result["relative_L1_in_affected_gas"].values()) <= MAX_FIELD_L1
                            and max(result["component_L1_per_labelled_interval"].values()) <= MAX_COMPONENT_L1_PER_INTERVAL)
    return result


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--check-series":
        check_series(Path(sys.argv[2]))
        return 0
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("case", choices=KNOWN_11)
    p.add_argument("production", type=Path)
    p.add_argument("arm", type=Path)
    p.add_argument("receipt", type=Path)
    args = p.parse_args()
    result = check(args.case, args.production, args.arm)
    args.receipt.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, allow_nan=False))
    return 0 if result["passed"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
