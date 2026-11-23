"""Compare paired native lobe enthalpy and R100 storage at the saved and matched ages."""

import argparse
import csv
import hashlib
import json
import math
import zipfile
from pathlib import Path

from select_common_age_hdf5 import CODE_TIME_PER_MYR
from snapshot_energy import SECONDS_PER_MYR


ASSETS = Path(__file__).resolve().parents[2] / "docs/science/assets"
PRODUCTION = ASSETS / "turn15_review_2026-11-11/budgets"
HISTORICAL = ASSETS / "native_delivery_restatement_2026-11-21/primary_selected_ages.csv"
INTERVALS = ASSETS / "entropy_restart_result_2026-11-22/primary_intervals.csv"
COMPACT = ASSETS / "entropy_restart_result_2026-11-22/compact_inputs.zip"
OUTPUT = ASSETS / "entropy_restart_lobes_2026-11-23"
INITIAL_BINDINGS = OUTPUT / "initial_source_bindings.json"
PBS_RECEIPT = OUTPUT / "readout-pbs.json"
BRACKET = {"G-HI": 21, "C-HI": 19}
CUTS = (0.001, 0.005, 0.01)
COMPONENTS = ("thermal_delta_erg", "kinetic_delta_erg", "gravitational_delta_erg", "total_delta_erg")


def records(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def same(actual, expected, label, tolerance=1e-12):
    if not math.isclose(actual, expected, rel_tol=tolerance, abs_tol=0):
        raise ValueError(f"{label}: {actual} != {expected}")


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reconstruct_delivery(case, arm, seed, intervals, archive):
    def injector(index):
        source_arm = "ON" if index == 10 else arm
        return json.loads(archive.read(f"snapshots/{case}/{source_arm}/injector_{index}.json"))

    delivered = {10: float(seed["cumulative_net_gas_delivery_erg"])}
    power = {}
    ages = {}
    selected = sorted((r for r in intervals if (r["case"], r["arm"]) == (case, arm)),
                      key=lambda r: int(r["end_index"]))
    if [(int(r["start_index"]), int(r["end_index"])) for r in selected] != [(i, i+1) for i in range(10, 30)]:
        raise ValueError("invalid primary restart intervals")
    parts = [delivered[10]]
    for i in range(10, 31):
        snap = injector(i)
        ages[i] = snap["age_myr"]
        power[i] = snap["rates"]["linear_snapshot_flags"]["net"]["gas_energy_erg_s"]
        if i == 10:
            same(ages[i], float(seed["actual_age_myr"]), "seed age")
            previous_time = snap["time_code"]
            continue
        r = selected[i-11]
        same(ages[i-1], float(r["start_age_myr"]), "interval start age")
        same(ages[i], float(r["end_age_myr"]), "interval end age")
        dt = (snap["time_code"] - previous_time) / CODE_TIME_PER_MYR * SECONDS_PER_MYR
        integral = 0.5 * (power[i-1] + power[i]) * dt
        independent = (float(r["cone_gas"]) + float(r["stationary_gas"])) * float(r["labelled_energy_erg"])
        same(integral, independent, "signed cone plus stationary gas integral")
        parts.append(integral)
        delivered[i] = math.fsum(parts)
        previous_time = snap["time_code"]
    return ages, power, delivered


def checked_snapshot(record, archive):
    case, arm, index = record["case"], record["arm"], record["index"]
    grid = json.loads(archive.read(f"snapshots/{case}/{arm}/grid_{index}.json"))
    src, original = record["source"], grid["input"]
    if (any(record[k] != grid[k] for k in ("case", "arm", "index", "step", "time_code", "age_myr"))
            or any(src[k] != original[k] for k in ("filename", "bytes", "mtime_ns"))
            or record["field_sha256"]["prs"] != original["field_sha256_c_order_float32_le"]["prs"]
            or record["grid_out_sha256"] != original["grid_out_sha256"]
            or record["atmosphere_sha256"] != original["atmosphere_sha256"]):
        raise ValueError(f"native identity mismatch: {case} {arm} {index}")
    if tuple(r["tracer_cut"] for r in record["lobes"]) != CUTS:
        raise ValueError("incomplete tracer cuts")


def check_production(record, original):
    primary = record["lobes"][0]
    pairs = {"actual_time_myr": record["age_myr"], "raw_radius_kpc": record["r100_radius_kpc"],
             "cocoon_volume_kpc3": primary["volume_kpc3"], "native_enthalpy_2.5_erg": primary["enthalpy_2p5pv_erg"],
             **{"all_" + k: record["r100_storage"][k] for k in COMPONENTS}}
    for key, value in pairs.items():
        same(value, float(original[key]), f"{record['case']}/{record['index']}/{key}", tolerance=5e-11)
    return max(abs(value / float(original[k]) - 1) for k, value in pairs.items())


def interpolate(rows, lo, hi, weight, fields):
    return {k: rows[lo][k] + weight * (rows[hi][k] - rows[lo][k]) for k in fields}


def write_table(path, table):
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=table[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(table)


def reduce(source, output):
    raw = (json.loads(source.read_text()) if source.is_file() else
           [json.loads(p.read_text()) for p in sorted(source.glob("*/*/lobe_*.json"))])
    keyed = {(r["case"], r["arm"], r["index"]): r for r in raw}
    expected = {(c, a, i) for c, side in BRACKET.items() for a, ids in
                (("ON", (10, 20, 30)), ("OFF", (side, 20, 30))) for i in ids}
    if set(keyed) != expected or len(raw) != len(expected):
        raise ValueError("missing, extra or duplicate native lobe snapshot")
    raw = [keyed[k] for k in sorted(keyed)]
    native_hashes = json.loads(PBS_RECEIPT.read_text())["files"]
    measured_hashes = {f"{r['case']}/{r['arm']}/lobe_{r['index']}.json":
                       hashlib.sha256((json.dumps(r, indent=2, allow_nan=False) + "\n").encode()).hexdigest()
                       for r in raw}
    if measured_hashes != native_hashes:
        raise ValueError("native lobe measurement differs from the archived worker result")
    seed_rows = {r["case"]: r for r in records(HISTORICAL) if r["snapshot_index"] == "10"}
    initial_sources = json.loads(INITIAL_BINDINGS.read_text())["cases"]
    intervals = records(INTERVALS)
    lobes, spheres, effects, controls = [], [], [], []
    with zipfile.ZipFile(COMPACT) as archive:
        for r in raw:
            checked_snapshot(r, archive)
        for case, neighbour in BRACKET.items():
            original = {int(r["snapshot_index"]): r for r in records(PRODUCTION / case / "measurements.csv")
                        if float(r["speed_threshold_km_s"]) == 100}
            for i, original_index in ((10, 10), (20, 11)):
                r = keyed[case, "ON", i]
                controls.append(dict(case=case, index=i, production_index=original_index,
                                     maximum_relative_difference=check_production(r, original[original_index])))
            for r in raw:
                if r["case"] == case and any(r["initial"][k] != initial_sources[case][k]
                                            for k in ("filename", "bytes", "inode", "mtime_ns")):
                    raise ValueError(f"production initial file differs from original request for {case}")
            by_arm, source_by_arm = {}, {}
            for arm in ("ON", "OFF"):
                ages, powers, delivery = reconstruct_delivery(case, arm, seed_rows[case], intervals, archive)
                source_by_arm[arm] = (ages, powers, delivery)
                selections = {}
                for index in ((10, 20, 30) if arm == "ON" else sorted((neighbour, 20, 30))):
                    r = keyed[case, arm, index]
                    age = r["age_myr"]
                    same(age, ages[index], "lobe and delivery age")
                    prefix = dict(case=case, arm=arm, index=index, age_myr=age)
                    sphere = r["r100_storage"]
                    spheres.append(dict(**prefix, radius_kpc=r["r100_radius_kpc"],
                                        contains_primary_lobe=r["lobe_outermost_centre_kpc"] <= r["r100_radius_kpc"],
                                        **sphere, storage_over_cumulative_net_gas=sphere["total_delta_erg"]/delivery[index]))
                    selections[index] = {}
                    for measured in r["lobes"]:
                        h = measured["enthalpy_2p5pv_erg"]
                        value = dict(**measured, cumulative_net_gas_erg=delivery[index],
                                     cumulative_net_gas_at_seed_erg=delivery[10],
                                     post_seed_net_gas_erg=delivery[index]-delivery[10],
                                     enthalpy_over_cumulative_net_gas=h/delivery[index])
                        lobes.append(dict(**prefix, **value))
                        selections[index][measured["tracer_cut"]] = dict(**value,
                            r100_radius_kpc=r["r100_radius_kpc"], r100_total_delta_erg=sphere["total_delta_erg"])
                by_arm[arm] = selections
            on_ages, _, _ = source_by_arm["ON"]
            off_ages, off_power, off_delivery = source_by_arm["OFF"]
            for index, timing in ((20, "native_outputs"), (20, "off_interpolated_to_on"), (30, "native_outputs")):
                target = on_ages[index]
                lo = hi = index
                weight = 0.
                expected_off_age = off_ages[index]
                d_off = off_delivery[index]
                if timing == "off_interpolated_to_on":
                    lo, hi = sorted((index, neighbour))
                    weight = (target - off_ages[lo]) / (off_ages[hi] - off_ages[lo])
                    if not 0 < weight < 1:
                        raise ValueError("OFF interpolation does not bracket the measured ON time")
                    dt = (target - off_ages[lo]) * SECONDS_PER_MYR
                    d_off = off_delivery[lo] + dt * (off_power[lo] + .5*weight*(off_power[hi]-off_power[lo]))
                    expected_off_age = target
                for cut in CUTS:
                    on = by_arm["ON"][index][cut]
                    off = interpolate({i: v[cut] for i, v in by_arm["OFF"].items()}, lo, hi, weight,
                                      ("enthalpy_2p5pv_erg", "volume_kpc3", "r100_radius_kpc", "r100_total_delta_erg"))
                    h_on, h_off = on["enthalpy_2p5pv_erg"], off["enthalpy_2p5pv_erg"]
                    d_on = on["cumulative_net_gas_erg"]
                    # Both arms have 2e45 erg/s labelled power. Use the ON duration for a named common reference.
                    post_label = (target-on_ages[10]) * SECONDS_PER_MYR * 2e45
                    delta_ratio = 100 * (h_off/d_off - h_on/d_on)
                    h_part = 100 * (h_off-h_on) / d_on
                    d_part = 100 * h_off * ((d_on-d_off) / (d_on*d_off))
                    if not math.isclose(delta_ratio, h_part+d_part, rel_tol=1e-12, abs_tol=3e-14):
                        raise ValueError("ratio change does not equal its numerator and denominator contributions")
                    effects.append(dict(case=case, nominal_myr=11 if index == 20 else 12, timing=timing, tracer_cut=cut,
                        on_age_myr=target, off_age_myr=expected_off_age, off_saved_low_myr=off_ages[lo],
                        off_saved_high_myr=off_ages[hi], off_high_weight=weight,
                        enthalpy_on_erg=h_on, enthalpy_off_erg=h_off, enthalpy_off_minus_on_erg=h_off-h_on,
                        volume_on_kpc3=on["volume_kpc3"], volume_off_kpc3=off["volume_kpc3"],
                        volume_off_minus_on_kpc3=off["volume_kpc3"]-on["volume_kpc3"],
                        net_gas_on_erg=d_on, net_gas_off_erg=d_off, net_gas_off_minus_on_erg=d_off-d_on,
                        post_seed_label_on_erg=post_label,
                        enthalpy_difference_over_post_seed_label=(h_off-h_on)/post_label,
                        enthalpy_over_net_gas_on=h_on/d_on, enthalpy_over_net_gas_off=h_off/d_off,
                        ratio_difference_percentage_points=delta_ratio, numerator_percentage_points=h_part,
                        denominator_percentage_points=d_part, r100_radius_on_kpc=on["r100_radius_kpc"],
                        r100_radius_off_kpc=off["r100_radius_kpc"], r100_storage_on_erg=on["r100_total_delta_erg"],
                        r100_storage_off_erg=off["r100_total_delta_erg"],
                        r100_storage_difference_over_post_seed_label=(off["r100_total_delta_erg"]-on["r100_total_delta_erg"])/post_label))
    output.mkdir(parents=True, exist_ok=True)
    (output/"snapshot_readout.json").write_text(json.dumps(raw, indent=2, allow_nan=False) + "\n")
    for filename, rows in (("native_lobes.csv", lobes), ("r100_storage.csv", spheres), ("paired_effects.csv", effects)):
        write_table(output/filename, rows)
    paths = [HISTORICAL, INTERVALS, COMPACT, INITIAL_BINDINGS, PBS_RECEIPT,
             *(PRODUCTION/c/"measurements.csv" for c in BRACKET)]
    receipt = dict(snapshot_count=len(raw), tracer_rows=len(lobes), sphere_rows=len(spheres), paired_rows=len(effects),
                   signed_gas_interval_crosschecks=len(intervals),
                   controls=controls, source_sha256={str(p.relative_to(ASSETS)): fingerprint(p) for p in paths},
                   output_sha256={f: fingerprint(output/f) for f in
                                  ("snapshot_readout.json", "native_lobes.csv", "r100_storage.csv", "paired_effects.csv")})
    (output/"verification.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="native results directory or committed snapshot_readout.json")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    reduce(args.source, args.output)
