"""Integrate the registered exterior energy balance from the paired 10–12 Myr restarts."""

import argparse
import csv
import gzip
import io
import itertools
import json
import math
from pathlib import Path

from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR


INJECTORS = ("linear_snapshot_flags", "linear_hllc", "linear_hll", "first_order_snapshot_flags")
BOUNDARIES = ("outer_active_cell", "linear_to_boundary_face")
RULES = {"trapezoid": 0.5, "left": 0.0, "right": 1.0}
PRIMARY = (INJECTORS[0], BOUNDARIES[0], "trapezoid")
GRID_STOCK = ("thermal_erg", "kinetic_erg", "gravitational_erg")
SPHERE_STOCK = ("thermal_erg", "kinetic_erg", "potential_erg")
BUDGET_FIELDS = ("grid_storage", "boundary_outward", "whole_grid_source", "flagged_storage",
                 "net_injector", "cone_gas", "stationary_gas", "tagged_mass", "exterior",
                 "collar", "beyond_collar", "native_stage", "unexplained")


def read_json(path):
    return json.loads(path.read_text())


def paired_snapshots(root, case, arm, inventory):
    seed = inventory[case, "ON", 10]
    if any(seed[k] != inventory[case, "OFF", 10][k]
           for k in ("device", "inode", "time_code", "size", "mtime_ns")):
        raise ValueError(f"{case} seed is not shared by the two arms")
    samples = []
    for index in range(10, 31):
        source_arm = "ON" if index == 10 else arm
        folder = root / "snapshots" / case / source_arm
        grid = read_json(folder / f"grid_{index}.json")
        injector = read_json(folder / f"injector_{index}.json")
        identity = (case, source_arm, index)
        native = inventory[case, arm, index]
        for record in (grid, injector):
            if tuple(record[k] for k in ("case", "arm", "index")) != identity:
                raise ValueError(f"wrong snapshot {identity}")
        if (any(grid[k] != injector[k] for k in ("age_myr", "time_code", "step"))
                or grid["time_code"] != native["time_code"]
                or grid["input"]["mtime_ns"] != native["mtime_ns"]
                or grid["input"]["bytes"] != native["size"] or injector["file_size_bytes"] != native["size"]
                or grid["input"]["atmosphere_sha256"] != injector["atmosphere_sha256"]):
            raise ValueError(f"unmatched native snapshot receipts {identity}")
        samples.append((grid, injector))
    if len({(i["grid_axes_sha256"], i["atmosphere_sha256"], i["labelled_power_erg_s"],
             i["labelled_mass_rate_g_s"]) for _, i in samples}) != 1:
        raise ValueError(f"grid, potential or label changed in {case} {arm}")
    # Each arm writes its own timestamp in grid.out. The two arms share the numeric grid and seed.
    if len({g["input"]["grid_out_sha256"] for g, _ in samples if g["arm"] == arm}) != 1:
        raise ValueError(f"grid file changed within {case} {arm}")
    return samples


def stock_change(start, end, fields):
    return math.fsum(end[k] - start[k] for k in fields)


def mean_rate(start, end, w):
    # An unused, invalid endpoint does not invalidate a left or right sum.
    terms = [(rate, weight) for rate, weight in ((start, 1-w), (end, w)) if weight]
    if any(rate is None for rate, _ in terms):
        return None
    return math.fsum(rate * weight for rate, weight in terms)


def interval(start, end, stage, case, arm, method, boundary, rule):
    (ga, ia), (gb, ib) = start, end
    dt = (gb["time_code"] - ga["time_code"]) / CODE_TIME_PER_MYR * SECONDS_PER_MYR
    label = dt * ia["labelled_power_erg_s"]
    if (dt <= 0 or not math.isclose(label, float(stage["labelled_energy_erg"]), rel_tol=1e-12)
            or (ga["step"], gb["step"]) != (int(stage["start_step"]), int(stage["end_step_exclusive"]))):
        raise ValueError(f"native stage interval differs at {case} {arm} {gb['index']}")
    w = RULES[rule]
    a, b = ia["rates"][method], ib["rates"][method]

    def rate(region, field):
        return mean_rate(a[region][field], b[region][field], w)

    grid_change = stock_change(ga["storage"], gb["storage"], GRID_STOCK) / label
    flag_change = stock_change(ia["flagged_storage"], ib["flagged_storage"], SPHERE_STOCK) / label
    sa, sb = ia["spheres"]["0.85"], ib["spheres"]["0.85"]
    sphere_change = stock_change(sa["storage"], sb["storage"], SPHERE_STOCK) / label
    power = ia["labelled_power_erg_s"]
    domain_flux = mean_rate(ga["boundary"][boundary]["total_energy_flux_outward_erg_s"],
                            gb["boundary"][boundary]["total_energy_flux_outward_erg_s"], w)
    net = rate("net", "total_energy_erg_s") / power
    sphere_flux = mean_rate(sa["rates"][method]["total_energy_erg_s"],
                            sb["rates"][method]["total_energy_erg_s"], w) / power
    collar = math.fsum((sphere_change, -flag_change, sphere_flux, -net))
    source = None if domain_flux is None else grid_change + domain_flux / power
    exterior = None if source is None else math.fsum((source, -flag_change, -net))
    native = float(stage["effective_net_erg"]) / label
    return dict(case=case, arm=arm, start_index=ga["index"], end_index=gb["index"],
                start_age_myr=ga["age_myr"], end_age_myr=gb["age_myr"], injector_method=method,
                outer_boundary=boundary, time_rule=rule, labelled_energy_erg=label,
                grid_storage=grid_change, boundary_outward=None if domain_flux is None else domain_flux / power,
                whole_grid_source=source, flagged_storage=flag_change, net_injector=net,
                cone_gas=rate("cap", "gas_energy_erg_s") / power,
                stationary_gas=rate("stationary", "gas_energy_erg_s") / power,
                tagged_mass=rate("net", "tracer_mass_g_s") / ia["labelled_mass_rate_g_s"],
                exterior=exterior, collar=collar, beyond_collar=None if exterior is None else exterior-collar,
                native_stage=native, unexplained=None if exterior is None else exterior-native)


def weighted_window(rows):
    first, last = rows[0], rows[-1]
    label = math.fsum(r["labelled_energy_erg"] for r in rows)
    window = dict(case=first["case"], arm=first["arm"], start_age_myr=first["start_age_myr"],
                  end_age_myr=last["end_age_myr"], injector_method=first["injector_method"],
                  outer_boundary=first["outer_boundary"], time_rule=first["time_rule"],
                  intervals=len(rows), valid_exterior_intervals=sum(r["exterior"] is not None for r in rows),
                  labelled_energy_erg=label)
    for k in BUDGET_FIELDS:
        window[k] = (math.fsum(r[k]*r["labelled_energy_erg"] for r in rows)/label
                     if all(r[k] is not None for r in rows) else None)
    return window


def csv_data(rows):
    f = io.StringIO(newline="")
    writer = csv.DictWriter(f, fieldnames=rows[0], lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return f.getvalue().encode()


def compare_arms(windows):
    def key(r):
        return tuple(r[k] for k in ("case", "injector_method", "outer_boundary", "time_rule"))

    controls = {key(r): r for r in windows if r["arm"] == "ON"}
    comparisons = []
    for off in (r for r in windows if r["arm"] == "OFF"):
        on = controls[key(off)]
        if (on["start_age_myr"], on["end_age_myr"]) != (off["start_age_myr"], off["end_age_myr"]):
            raise ValueError("the two arms cover different times")
        a, b = on["exterior"], off["exterior"]
        change = b - a if a is not None and b is not None else None
        comparisons.append(dict(case=on["case"], injector_method=on["injector_method"],
                                outer_boundary=on["outer_boundary"], time_rule=on["time_rule"],
                                on_exterior=a, off_exterior=b, off_minus_on=change,
                                fraction_of_on_deficit_removed=change / -a if change is not None and a < 0 else None,
                                on_injector=on["net_injector"], off_injector=off["net_injector"]))
    return comparisons


def annual_sampling(case, arm, samples, native_intervals):
    rows = []
    for first, last in ((0, 10), (10, 20)):
        start, end = samples[first], samples[last]
        stages = native_intervals[first:last]
        stage = dict(labelled_energy_erg=math.fsum(float(s["labelled_energy_erg"]) for s in stages),
                     effective_net_erg=math.fsum(float(s["effective_net_erg"]) for s in stages),
                     start_step=stages[0]["start_step"], end_step_exclusive=stages[-1]["end_step_exclusive"])
        rows.append(interval(start, end, stage, case, arm, *PRIMARY))
    return weighted_window(rows)


def run(root, out):
    native = read_json(root / "raw/native-inventory.json")
    inventory = {(r["case"], r["arm"], r["index"]): r for r in native["outputs"]}
    if len(inventory) != 84 or len(native["outputs"]) != 84:
        raise ValueError("expected 84 native catalogue entries")
    for case in ("G-HI", "C-HI"):
        gate = read_json(root / "raw" / case / "gate.json")
        if gate["case"] != case or gate["passed"] is not True:
            raise ValueError(f"11-Myr control failed for {case}")
    with (root / "stages/rk_interval_regions.csv").open(newline="") as f:
        stages = {(r["case"], r["arm"], int(r["end_index"])): r
                  for r in csv.DictReader(f) if r["region"] == "exterior"}
    if len(stages) != 80:
        raise ValueError("expected 80 exterior stage intervals")
    intervals, windows, primary_intervals, primary_windows, annual_windows = [], [], [], [], []
    for case, arm in itertools.product(("G-HI", "C-HI"), ("ON", "OFF")):
        samples = paired_snapshots(root, case, arm, inventory)
        native_intervals = [stages[case, arm, i] for i in range(11, 31)]
        annual_windows.append(annual_sampling(case, arm, samples, native_intervals))
        for method, boundary, rule in itertools.product(INJECTORS, BOUNDARIES, RULES):
            rows = [interval(a, b, stage, case, arm, method, boundary, rule)
                    for (a, b), stage in zip(itertools.pairwise(samples), native_intervals, strict=True)]
            window = weighted_window(rows)
            intervals.extend(rows)
            windows.append(window)
            if (method, boundary, rule) == PRIMARY:
                if window["valid_exterior_intervals"] != 20:
                    raise ValueError(f"incomplete primary exterior budget for {case} {arm}")
                primary_intervals.extend(rows)
                primary_windows.append(window)
    out.mkdir(parents=True, exist_ok=True)
    for filename, rows in (("primary_intervals.csv", primary_intervals), ("primary_windows.csv", primary_windows),
                           ("method_windows.csv", windows), ("paired_windows.csv", compare_arms(windows)),
                           ("annual_sampling_windows.csv", annual_windows)):
        (out / filename).write_bytes(csv_data(rows))
    with (out / "all_interval_methods.csv.gz").open("wb") as f:
        with gzip.GzipFile(filename="", fileobj=f, mode="wb", mtime=0) as encoded:
            encoded.write(csv_data(intervals))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="extracted compact receipts with raw/, snapshots/ and stages/")
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    run(args.root, args.out)
