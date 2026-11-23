"""Integrate the native RK2 mapper ledger over each entropy-restart output interval."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import itertools
import json
import math
import tempfile
from pathlib import Path

import numpy as np

from check_entropy_restart_control import OPERATIONS, catalogue, labelled_power, paired_cases
from pluto_h5_level3_ambient_extract import UNIT_VELOCITY_CMS
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR


RADII = ("injector_flag", "r_lt_0.75", "r_0.75_5", "r_5_10", "r_10_25",
         "r_25_50", "r_50_100", "r_ge_100")
TRACERS = ("f_le_0.001", "f_0.001_0.005", "f_0.005_0.5", "f_gt_0.5", "invalid")
REGIONS = {"whole_grid": slice(None), "injector_flag": slice(0, 1),
           "unflagged_inside_0.75": slice(1, 2), "exterior": slice(2, None)}
COUNTS = ("cell_visits", "entropy_visits", "density_floors", "gas_energy_floors",
          "p_entropy_floors", "p_energy_floors", "entropy_visits_with_negative_p_energy",
          "nonfinite_energy_visits")
SIGNED = tuple(f"{op}_{sign}" for op in (*OPERATIONS, "cell") for sign in ("gain", "loss"))
METRICS = (*COUNTS, *(f"raw_{name}" for name in SIGNED), "raw_density_floor_mass_code",
           "effective_net_code", "effective_cell_gross_code")
COLUMN = {name: i for i, name in enumerate(METRICS)}
WEIGHTS = (0.5, 1.0)
CELLS = 1014 * 960 * 960
# Native MU_NORM, atomic mass unit and parsec from the pinned production build.
NATIVE_UNIT_ERG = 0.60364 * 1.66053886e-24 * UNIT_VELOCITY_CMS**2 * (3.0856775807e21)**3


def open_ledger(path, mode):
    return gzip.open(path, mode) if path.suffix == ".gz" else path.open(mode)


def read_ledger(stream, *, times, steps, setting, physical_cells=CELLS):
    """A saved state at step s includes operations through s-1, in its own arm."""
    if (len(times) != len(steps) or len(times) < 2
            or not all(b > a for a, b in zip(times, times[1:]))
            or not all(b > a for a, b in zip(steps, steps[1:]))):
        raise ValueError("output times and steps must increase strictly together")
    totals = np.zeros((len(times)-1, 2, len(RADII), len(TRACERS), len(METRICS)))
    reader = csv.DictReader(stream)
    groups = itertools.groupby(reader, key=lambda row: int(row["step"]))
    interval, next_step, previous_time, row_count = 0, steps[0], times[0], 0
    unit = None
    flagged_cells_per_stage = set()
    for step, rows in groups:
        if step != next_step or step >= steps[-1]:
            raise ValueError(f"step coverage fails at {step}, expected {next_step}")
        if step == steps[interval+1]:
            interval += 1
        if step == steps[interval] and abs(previous_time-times[interval]) > 1e-8:
            raise ValueError(f"output time and step mismatch at {step}")
        visited = set()
        cell_counts = [0, 0]
        flag_counts = [0, 0]
        step_timing = None
        for row in rows:
            stage = int(row["stage"])
            if stage not in (1, 2) or float(row["rk_weight"]) != WEIGHTS[stage-1]:
                raise ValueError("unexpected RK2 stage or weight")
            if row["entropy_switch"] != setting:
                raise ValueError("ledger entropy label differs from arm")
            location = (stage-1, RADII.index(row["radius_kpc"]), TRACERS.index(row["tracer_fraction"]))
            if location in visited:
                raise ValueError(f"duplicate RK stage and spatial bin at step {step}")
            visited.add(location)
            start, end, dt = timing = tuple(float(row[k]) for k in ("time_start_code", "time_end_code", "dt_code"))
            if (not all(map(math.isfinite, timing)) or dt <= 0 or abs(start+dt-end) > 1e-9
                    or abs(start-previous_time) > 1e-9 or (step_timing is not None and timing != step_timing)):
                raise ValueError(f"noncontiguous or conflicting RK times at step {step}")
            step_timing = timing
            row_unit = float(row["energy_unit_erg"])
            if unit is None:
                unit = row_unit
            if row_unit != unit or not math.isclose(unit, NATIVE_UNIT_ERG, rel_tol=2e-15):
                raise ValueError("native energy unit differs from the production source")
            data = [float(row[k]) for k in METRICS]
            if not all(map(math.isfinite, data)):
                raise ValueError(f"nonfinite accounting at step {step}")
            cells, entropy, rho_floor, e_floor, ps_floor, pe_floor, would_floor, nonfinite = data[:len(COUNTS)]
            if (cells <= 0 or any(n < 0 or n > cells or not n.is_integer() for n in data[:len(COUNTS)])
                    or nonfinite or ps_floor > entropy or would_floor > entropy or pe_floor > cells-entropy
                    or (setting == "off" and entropy)):
                raise ValueError(f"invalid event or cell counts at step {step}")
            gain = data[COLUMN["raw_cell_gain"]]
            loss = data[COLUMN["raw_cell_loss"]]
            op_changes = data[len(COUNTS):COLUMN["raw_cell_gain"]]
            tolerance = 1e-9 * max(gain-loss, sum(map(abs, op_changes)), 1e-100)
            if (any(v < 0 for v in data[len(COUNTS):COLUMN["raw_density_floor_mass_code"]:2])
                    or any(v > 0 for v in data[len(COUNTS)+1:COLUMN["raw_density_floor_mass_code"]:2])
                    or abs(sum(op_changes)-(gain+loss)) > tolerance
                    or abs(data[COLUMN["effective_net_code"]]-WEIGHTS[stage-1]*(gain+loss)) > tolerance
                    or abs(data[COLUMN["effective_cell_gross_code"]]-WEIGHTS[stage-1]*(gain-loss)) > tolerance):
                raise ValueError(f"signed operation and RK energy accounting disagree at step {step}")
            for op, n in zip(OPERATIONS, (e_floor, entropy-ps_floor, ps_floor, pe_floor), strict=True):
                if n == 0 and (data[COLUMN[f"raw_{op}_gain"]] or data[COLUMN[f"raw_{op}_loss"]]):
                    raise ValueError(f"{op} changed energy without a recorded visit at step {step}")
            floor_mass = data[COLUMN["raw_density_floor_mass_code"]]
            if floor_mass < 0 or (rho_floor == 0 and floor_mass != 0):
                raise ValueError(f"density floor mass inconsistent with counts at step {step}")
            cell_counts[stage-1] += int(cells)
            if location[1] == 0:
                flag_counts[stage-1] += int(cells)
            totals[(interval, *location)] += data
            row_count += 1
        if cell_counts != [physical_cells, physical_cells]:
            raise ValueError(f"incomplete physical grid or RK stage at step {step}")
        flagged_cells_per_stage.update(flag_counts)
        previous_time = step_timing[1]
        next_step += 1
    if next_step != steps[-1] or abs(previous_time-times[-1]) > 1e-8:
        raise ValueError("native RK ledger did not reach the last saved state")
    info = {"native_ledger_rows": row_count, "accepted_steps": next_step-steps[0],
            "first_step": steps[0], "last_completed_step": steps[-1]-1,
            "physical_cells_per_stage": physical_cells, "flagged_cells_per_stage": sorted(flagged_cells_per_stage),
            "energy_unit_erg": unit}
    return totals, info


def load_arm(raw, case, arm):
    root = raw / case / arm
    outputs = root / "outputs"
    series = json.loads((root / "series.json").read_text())
    state = json.loads((root.parent / "restart.json").read_text())
    cat = catalogue(outputs)
    indices = [10, *series["new_indices"]]
    if (state["case"] != case or series["case"] != case or series["arm"] != arm or not series["new_indices"]
            or indices != list(range(10, indices[-1]+1)) or indices[-1] != max(cat)
            or len(indices)-1 != len(series["ages_myr"])):
        raise ValueError(f"inconsistent restart series or catalogue for {case} {arm}")
    times = [state["restart_time_code"], *(t*CODE_TIME_PER_MYR for t in series["ages_myr"])]
    steps = [cat[i][2] for i in indices]
    if (abs(times[0]/CODE_TIME_PER_MYR - 10) > .0015 or abs(series["ages_myr"][-1]-12) > 1e-8
            or any(min(abs(age-i/10) for age in series["ages_myr"]) > .0015 for i in range(101, 121))
            or any(abs(cat[i][0]-t) > .001 for i, t in zip(indices, times, strict=True))
            or steps[0] != series["diagnostic_first_step"] or steps[-1]-1 != series["diagnostic_last_step"]):
        raise ValueError(f"series receipts and native catalogue disagree for {case} {arm}")
    paths = sorted(outputs.glob("entropy_rk_*.csv")) + sorted(outputs.glob("entropy_rk_*.csv.gz"))
    if len(paths) != 1:
        raise ValueError(f"expected one raw entropy ledger for {case} {arm}, found {len(paths)}")
    with open_ledger(paths[0], "rt") as stream:
        cubes, info = read_ledger(stream, times=times, steps=steps, setting="selective" if arm == "ON" else "off")
    with open_ledger(paths[0], "rb") as stream:
        info["raw_csv_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    records = (root / "series.json", root.parent / "restart.json", outputs / "flt.h5.out")
    info["receipt_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in records}
    return indices, times, steps, cubes, info


def row_metrics(stages, weights, unit, label, *, include_raw):
    unweighted = stages.sum(axis=0)
    weighted = np.asarray(weights) @ stages
    row = {k: int(unweighted[COLUMN[k]]) for k in COUNTS}
    for quantity in SIGNED:
        k = "raw_" + quantity
        energy = weighted[COLUMN[k]] * unit
        if include_raw:
            row[k+"_code"] = unweighted[COLUMN[k]]
        row[quantity+"_erg"] = energy
        row[quantity+"_over_label"] = energy / label
    for k in ("effective_net", "effective_cell_gross"):
        energy = unweighted[COLUMN[k+"_code"]] * unit
        row[k+"_erg"] = energy
        row[k+"_over_label"] = energy / label
    mass = COLUMN["raw_density_floor_mass_code"]
    row["raw_density_floor_mass_code"] = unweighted[mass]
    row["effective_density_floor_mass_g"] = weighted[mass] * unit / UNIT_VELOCITY_CMS**2
    return row


def make_rows(case, arm, indices, times, steps, cubes, info):
    for whole_window, first, last in [(False, i, i+1) for i in range(len(cubes))] + [(True, 0, len(cubes))]:
        label = labelled_power(case) * SECONDS_PER_MYR * (times[last]-times[first]) / CODE_TIME_PER_MYR
        prefix = dict(case=case, arm=arm, start_index=indices[first], end_index=indices[last],
                      start_step=steps[first], end_step_exclusive=steps[last],
                      start_age_myr=times[first]/CODE_TIME_PER_MYR, end_age_myr=times[last]/CODE_TIME_PER_MYR,
                      labelled_energy_erg=label)
        data = cubes.sum(axis=0) if whole_window else cubes[first]
        period = "window" if whole_window else "interval"
        for region, selection in REGIONS.items():
            stages = data[:, selection].sum(axis=(1, 2))
            yield f"rk_{period}_regions.csv", {
                **prefix, "region": region,
                **row_metrics(stages, WEIGHTS, info["energy_unit_erg"], label, include_raw=False)}
        for stage, radius, tracer in zip(*np.nonzero(data[..., COLUMN["cell_visits"]]), strict=True):
            metrics = row_metrics(data[stage, radius, tracer][None, :], [WEIGHTS[stage]],
                                  info["energy_unit_erg"], label, include_raw=True)
            filename = "rk_window_bins.csv" if whole_window else "rk_interval_bins.csv.gz"
            yield filename, {**prefix, "stage": stage+1, "rk_weight": WEIGHTS[stage],
                             "radius_kpc": RADII[radius], "tracer_fraction": TRACERS[tracer], **metrics}


def reduce(raw, output):
    output.parent.mkdir(parents=True, exist_ok=True)
    verification = {}
    tables = {}
    present = sorted(p.parent.name for p in raw.glob("*/restart.json"))
    if len(present) != 2 or set(present) != set(paired_cases(present[0])):
        raise ValueError(f"expected a matched group and cluster restart pair, found {present}")
    for case, arm in itertools.product(paired_cases(present[0]), ("ON", "OFF")):
        indices, times, steps, cubes, info = load_arm(raw, case, arm)
        verification[f"{case}/{arm}"] = info
        for name, row in make_rows(case, arm, indices, times, steps, cubes, info):
            tables.setdefault(name, []).append(row)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        stage = Path(tmp) / "tables"
        stage.mkdir()
        for name, rows in tables.items():
            path = stage / name
            raw_csv = path.with_suffix("") if name.endswith(".gz") else path
            with raw_csv.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            if name.endswith(".gz"):
                path.write_bytes(gzip.compress(raw_csv.read_bytes(), mtime=0))
                raw_csv.unlink()
        (stage / "rk_verification.json").write_text(json.dumps(verification, indent=2, allow_nan=False)+"\n")
        if output.is_dir() and any(output.iterdir()):
            files = {p.name for p in stage.iterdir()}
            if files == {p.name for p in output.iterdir()} and all(
                (stage/name).read_bytes() == (output/name).read_bytes() for name in files
            ):
                return verification
            raise FileExistsError(f"different results already exist in {output}")
        stage.replace(output)
    return verification


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("raw_root", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(reduce(args.raw_root, args.output_dir), indent=2))
