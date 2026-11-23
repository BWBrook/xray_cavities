"""Score the registered low-power entropy predictions from both completed restart pairs."""

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from pathlib import Path

import h5py

from check_entropy_restart_control import (
    FIELD_SHAPE, KNOWN_11, MAX_COMPONENT_L1_PER_INTERVAL, MAX_FIELD_L1, TIME_11,
    catalogue, labelled_power, runtime_power,
)
from entropy_restart_budget import PRIMARY, csv_data, read_json, run as integrate_budget
from pluto_h5_level3_ambient_extract import REQUIRED_DATASETS, require_datasets
from reduce_entropy_restart_stages import reduce as reduce_stages
from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR
from validate_pluto_particle_restart_pair import read_restart_records


# Closed bounds are written directly to keep decimal forecast endpoints inclusive.
FORECASTS = {"C-LO": [(0.030, 0.025, 0.035), (0.047, 0.042, 0.052)],
             "G-LO": [(-0.017, -0.022, -0.012), (-0.022, -0.027, -0.017)]}
OFF_BOUND = 0.002
CLO_REFUTATION = 0.01
ARMS = ("ON", "OFF")


def require(ok, detail):
    if not ok:
        raise ValueError(detail)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n")


def accepted_gate(native, case):
    g = read_json(native / case / "gate.json")
    digest, step = KNOWN_11[case]
    require(g["case"] == case and g["passed"] is True and g["control_output"] == 20
            and g["reference_sha256"] == digest and g["reference_step"] == step
            and g["reference_time"] == TIME_11[case] and abs(g["control_step"]-step) <= 1
            and g["affected_cells"] > 0 and g["labelled_power_erg_s"] == labelled_power(case),
            f"{case} lacks the registered 11-Myr control")
    for key, expected, bound in (("relative_L1_in_affected_gas", REQUIRED_DATASETS, MAX_FIELD_L1),
                                 ("component_L1_per_labelled_interval", ("thermal","kinetic","potential"),
                                  MAX_COMPONENT_L1_PER_INTERVAL)):
        require(set(g[key]) == set(expected) and all(0 <= x <= bound for x in g[key].values()),
                f"{case} control {key} exceeds the registered tolerance")
    return g


def header(path, index, size, word_bytes):
    before = path.stat()
    require(before.st_size == size, f"incomplete native file {path.name}")
    with h5py.File(path, "r") as h5:
        group = f"Timestep_{index}"
        require(require_datasets(h5, group) == FIELD_SHAPE and
                all(h5[group]["vars"][key].dtype.str == f"<f{word_bytes}" for key in REQUIRED_DATASETS),
                f"wrong native shape or dtype for {path.name}")
        time = float(h5[group].attrs["Time"])
    after = path.stat()
    require(math.isfinite(time) and (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns), f"native file changed: {path.name}")
    return dict(time_code=time, size=size, mtime_ns=before.st_mtime_ns, device=before.st_dev, inode=before.st_ino)


def arm_inventory(native, case, arm, gate):
    root = native / case / arm
    outputs = root / "outputs"
    series, state = read_json(root / "series.json"), read_json(root.parent / "restart.json")
    require(state["case"] == case and runtime_power(case, root / "pluto.ini") == state["label_power_erg_s"]
            and series["case"] == case and series["arm"] == arm and series["new_indices"] == list(range(11, 31))
            and len(series["ages_myr"]) == 20 and series["particle_count"] == gate["particle_count_at_restart"],
            f"incomplete native 10–12 Myr series for {case}/{arm}")
    cat = catalogue(outputs)
    ages = [state["restart_time_code"]/CODE_TIME_PER_MYR, *series["ages_myr"]]
    rows = []
    for index, age in enumerate(ages, start=10):
        path = outputs / f"data.{index:04d}.flt.h5"
        row = header(path, index, 44890581676, 4)
        time = row["time_code"]
        require(float(time / CODE_TIME_PER_MYR) == age and abs(time-cat[index][0]) <= 0.001
                and (index == 10 or not path.is_symlink()), f"{case}/{arm} native float {index}")
        rows.append(dict(case=case, arm=arm, index=index, step=cat[index][2], **row))
    if arm == "ON":
        control_label = labelled_power(case) * (gate["reference_time"] - state["restart_time_code"]) / CODE_TIME_PER_MYR * SECONDS_PER_MYR
        require(rows[10]["step"] == gate["control_step"] and rows[10]["time_code"] == gate["control_time"]
                and math.isclose(control_label, gate["labelled_control_interval_erg"], rel_tol=1e-12),
                f"{case} gate refers to a different native output")
    records = read_restart_records(outputs / "restart.out")
    require(len(records) == 4, f"{case}/{arm} missing final native restart record")
    seed, final = records[2:]
    last = header(outputs / "data.0003.dbl.h5", 3, 67318639276, 8)
    particles = {p.name for p in outputs.glob("particles.*.dbl")}
    require(particles == {f"particles.{i:04d}.dbl" for i in range(1000, 1201)}
            and (seed.nfiles[2], seed.nfiles[3], seed.nfiles[8]) == (2,10,1000)
            and (final.nfiles[2], final.nfiles[3], final.nfiles[8]) == (3,30,1200)
            and seed.time == rows[0]["time_code"] and final.time == last["time_code"] == rows[-1]["time_code"]
            and abs(ages[-1]-12.0) < 1e-8 and seed.nstep == rows[0]["step"] == series["diagnostic_first_step"]
            and final.nstep == rows[-1]["step"] == series["diagnostic_last_step"]+1,
            f"{case}/{arm} native seed, final double, particles or RK coverage disagree")
    return rows, dict(ranks=state["mpi_ranks"], particle_files=len(particles), final_double_bytes=last["size"],
                      final_double_time_code=final.time, first_step=seed.nstep, last_step=final.nstep-1)


def sum_interval_energies(intervals):
    label = math.fsum(float(r["labelled_energy_erg"]) for r, _ in intervals)

    def energy(key):
        return math.fsum(float(stage[key]) for _, stage in intervals)

    gain = energy("entropy_gain_erg") + energy("entropy_with_p_floor_gain_erg")
    loss = energy("entropy_loss_erg") + energy("entropy_with_p_floor_loss_erg")
    net = math.fsum(float(stage[key]) for _, stage in intervals for key in
                    ("entropy_gain_erg", "entropy_with_p_floor_gain_erg", "entropy_loss_erg", "entropy_with_p_floor_loss_erg"))
    residual = math.fsum(float(r["exterior"])*float(r["labelled_energy_erg"]) for r, _ in intervals)
    return dict(start_index=int(intervals[0][0]["start_index"]), end_index=int(intervals[-1][0]["end_index"]),
                start_age_myr=float(intervals[0][0]["start_age_myr"]), end_age_myr=float(intervals[-1][0]["end_age_myr"]),
                labelled_energy_erg=label, entropy_gain_erg=gain, entropy_loss_erg=loss,
                entropy_net_erg=net, entropy_net_over_label=net/label,
                all_mapper_net_over_label=energy("effective_net_erg")/label,
                exterior_residual_erg=residual, exterior_residual_over_label=residual/label)


def score_tables(budget_rows, stage_rows):
    expected = {(case, arm, i) for case in FORECASTS for arm in ARMS for i in range(11, 31)}

    def index(rows):
        result = {(r["case"], r["arm"], int(r["end_index"])): r for r in rows}
        require(len(rows) == len(result) and set(result) == expected, "incomplete or duplicated scoring intervals")
        return result

    budgets = index(budget_rows)
    stages = index([r for r in stage_rows if r["region"] == "exterior"])
    annual, off = [], []
    for case, forecasts in FORECASTS.items():
        for arm in ARMS:
            intervals = []
            for i in range(11, 31):
                r, s = budgets[case, arm, i], stages[case, arm, i]
                label = float(r["labelled_energy_erg"])
                actual = (float(r["end_age_myr"])-float(r["start_age_myr"]))*SECONDS_PER_MYR*labelled_power(case)
                require(int(r["start_index"]) == int(s["start_index"]) == i-1 and
                        (r["injector_method"], r["outer_boundary"], r["time_rule"]) == PRIMARY
                        and label > 0 and math.isclose(label, actual, rel_tol=1e-12)
                        and math.isclose(label, float(s["labelled_energy_erg"]), rel_tol=1e-12)
                        and math.isfinite(float(r["exterior"])), f"mismatched scoring inputs {case}/{arm}/{i}")
                intervals.append((r,s))
                if arm == "OFF":
                    value = float(r["exterior"])
                    status = "excluded_startup" if i == 11 else ("pass" if abs(value) <= OFF_BOUND else "miss")
                    off.append(dict(case=case, start_index=i-1, end_index=i, start_age_myr=r["start_age_myr"],
                                    end_age_myr=r["end_age_myr"], labelled_energy_erg=label,
                                    exterior_residual_over_label=value, absolute_limit=OFF_BOUND, score=status))
            if arm == "ON":
                for portion, forecast in zip((intervals[:10], intervals[10:], intervals), (*forecasts, None), strict=True):
                    total = sum_interval_energies(portion)
                    value = total["entropy_net_over_label"]
                    point, low, high = forecast if forecast else (None, None, None)
                    status = ("pass" if low <= value <= high else "miss") if forecast else "no_annual_forecast"
                    annual.append(dict(case=case, **total, forecast=point, lower_bound=low, upper_bound=high,
                                       score=status, below_clo_refutation_threshold=(value < CLO_REFUTATION)
                                       if case == "C-LO" else None))
    return annual, off


def run(native, receipts, output):
    gates = {case: accepted_gate(native, case) for case in FORECASTS}
    relative = {Path(case)/arm/f"{kind}_{i}.json" for case in FORECASTS for arm in ARMS
                for i in range(10 if arm == "ON" else 11, 31) for kind in ("grid", "injector")}
    require({p.relative_to(receipts) for p in receipts.glob("*/*/*.json")} == relative,
            "expected 164 complete grid and injector receipts with one shared seed per case")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as working:
        out = Path(working)/"output"
        (out/"raw").mkdir(parents=True)
        inventory = {"outputs": [], "arms": {}}
        for case, gate in gates.items():
            (out/"raw"/case).mkdir()
            shutil.copyfile(native/case/"gate.json", out/"raw"/case/"gate.json")
            for arm in ARMS:
                rows, stats = arm_inventory(native, case, arm, gate)
                inventory["outputs"].extend(rows)
                inventory["arms"][f"{case}_{arm}"] = stats
        require(len({(r["device"],r["inode"]) for r in inventory["outputs"]}) == 82,
                "expected 82 distinct native floats across two pairs")
        write_json(out/"raw/native-inventory.json", inventory)
        for name in sorted(relative):
            dest = out/"snapshots"/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(receipts/name, dest)
        reduce_stages(native, out/"stages")
        integrate_budget(out, out/"budget")
        with (out/"budget/primary_intervals.csv").open() as b, (out/"stages/rk_interval_regions.csv").open() as s:
            annual, off = score_tables(list(csv.DictReader(b)), list(csv.DictReader(s)))
        (out/"on_counter_windows.csv").write_bytes(csv_data(annual))
        (out/"off_interval_scores.csv").write_bytes(csv_data(off))
        code = Path(__file__).resolve().parent
        code_hashes = {name: hashlib.sha256((code/name).read_bytes()).hexdigest() for name in
                       ("score_low_power_entropy.py", "reduce_entropy_restart_stages.py", "entropy_restart_budget.py")}
        write_json(out/"score.json", {"registration": 3665, "bipolar_label_erg_s": labelled_power("C-LO"),
                   "source_sha256": code_hashes,
                   "counter_branches": ["entropy", "entropy_with_p_floor"],
                   "clo_refutation_below": CLO_REFUTATION, "off_excludes_first_interval": True,
                   "on_forecasts": {c: [r["score"] for r in annual if r["case"] == c and r["forecast"] is not None]
                                    for c in FORECASTS},
                   "clo_combined_net_below_threshold": next(r["below_clo_refutation_threshold"] for r in annual
                           if r["case"] == "C-LO" and r["forecast"] is None),
                   "off_passes_out_of_19": {c: sum(r["score"] == "pass" for r in off if r["case"] == c)
                                           for c in FORECASTS}})
        manifest = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out)}\n"
                           for p in sorted(out.rglob("*")) if p.is_file())
        (out/"SHA256SUMS").write_text(manifest)
        if output.exists():
            files = {p.relative_to(out) for p in out.rglob("*") if p.is_file()}
            require(files == {p.relative_to(output) for p in output.rglob("*") if p.is_file()} and
                    all((output/p).read_bytes() == (out/p).read_bytes() for p in files),
                    f"conflicting score packet {output}")
        else:
            out.rename(output)
    return read_json(output/"score.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("native_root", type=Path)
    parser.add_argument("snapshot_receipts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.native_root, args.snapshot_receipts, args.output), indent=2, allow_nan=False))
