"""Compare native lobe enthalpy gains with gas delivery in the two low-power 10–12 Myr restarts."""

import argparse
import hashlib
import json
import math
import zipfile
from pathlib import Path

from pluto_h5_level3_ambient_extract import UNIT_LENGTH_CM
from reduce_entropy_lobes import ASSETS, CUTS, HISTORICAL, PRODUCTION, fingerprint, records, reconstruct_delivery, same, write_table


OUT = ASSETS / "low_power_entropy_result_2026-11-23"
ARCHIVE = OUT / "compact_inputs.zip"
INTERVALS = OUT / "budget/primary_intervals.csv"
WORKERS = OUT / "lobe_readout_pbs.json"
REVIEW = ASSETS / "native_delivery_review_2026-11-21/recomputed_rows.csv"
HISTORICAL_CUTS = ASSETS / "q029_binary_native_refresh_2026-09-06/remote_analysis"
CASES = ("C-LO", "G-LO")


def read_native(source):
    raw = (json.loads(source.read_text()) if source.is_file() else
           [json.loads(p.read_text()) for p in source.glob("*/*/lobe_*.json")])
    keyed = {(r["case"], r["arm"], r["index"]): r for r in raw}
    expected = {(case, arm, i) for case in CASES for arm, i in (("ON", 10), ("ON", 30), ("OFF", 30))}
    if len(raw) != len(expected) or set(keyed) != expected:
        raise ValueError("expected two shared seeds and four low-power 12-Myr endpoints")
    hashes = {f"{case}/{arm}/lobe_{i}.json": hashlib.sha256(
        (json.dumps(r, indent=2, allow_nan=False) + "\n").encode()).hexdigest()
        for (case, arm, i), r in keyed.items()}
    if hashes != json.loads(WORKERS.read_text())["files"]:
        raise ValueError("native lobe measurement differs from the six PBS receipts")
    return keyed


def check_snapshot(r, archive):
    case, arm, i = r["case"], r["arm"], r["index"]
    g = json.loads(archive.read(f"snapshots/{case}/{arm}/grid_{i}.json"))
    j = json.loads(archive.read(f"snapshots/{case}/{arm}/injector_{i}.json"))
    if (any(r[k] != g[k] or r[k] != j[k] for k in ("case", "arm", "index", "step", "time_code", "age_myr"))
            or any(r["source"][k] != g["input"][k] for k in ("filename", "bytes", "mtime_ns"))
            or r["grid_out_sha256"] != g["input"]["grid_out_sha256"]
            or r["field_sha256"]["prs"] != g["input"]["field_sha256_c_order_float32_le"]["prs"]
            or tuple(v["tracer_cut"] for v in r["lobes"]) != CUTS
            or j["labelled_power_erg_s"] != 2e43 or (i == 30 and r["age_myr"] != 12.0)):
        raise ValueError(f"native low-power snapshot or cuts differ from verified score inputs at {case}/{arm}/{i}")


def seed_controls(case, seed):
    row, = (r for r in records(PRODUCTION / case / "measurements.csv")
            if int(r["snapshot_index"]) == 10 and float(r["speed_threshold_km_s"]) == 100)
    measured = seed["lobes"][0]
    for value, field in ((seed["age_myr"], "actual_time_myr"), (measured["volume_kpc3"], "cocoon_volume_kpc3"),
                         (measured["enthalpy_2p5pv_erg"], "native_enthalpy_2.5_erg")):
        same(value, float(row[field]), f"original production seed {case}/{field}")
    earlier = {float(r["tracer_threshold"]): r for r in records(HISTORICAL_CUTS / case / "native_energy_selected_age.csv")
               if r["snapshot_index"] == "10" and r["side"] == "bipolar_total" and r["tracer_threshold"]
               and r["threshold_comparison"] == "float64_stored_value_strict_gt"}
    return dict(turn15_primary_h_relative_difference=measured["enthalpy_2p5pv_erg"]/float(row["native_enthalpy_2.5_erg"])-1,
                turn15_primary_volume_relative_difference=measured["volume_kpc3"]/float(row["cocoon_volume_kpc3"])-1,
                q029_seed_comparisons=[dict(tracer_cut=v["tracer_cut"],
                    h_relative_difference=v["enthalpy_2p5pv_erg"]/float(earlier[v["tracer_cut"]]["lobe_enthalpy_2p5pv_erg"])-1,
                    volume_relative_difference=v["volume_kpc3"]/float(earlier[v["tracer_cut"]]["lobe_volume_kpc3"])-1)
                    for v in seed["lobes"]])


def reduce(source, output):
    keyed = read_native(source)
    historic = {r["case"]: r for r in records(HISTORICAL) if int(r["snapshot_index"]) == 10}
    reviewed = {r["case"]: r for r in records(REVIEW) if r["snapshot_index"] == "10"
                and (r["method"], r["rule"]) == ("linear_snapshot_flags", "trapezoid")}
    intervals = records(INTERVALS)
    measurements, effects, controls = [], [], {}
    with zipfile.ZipFile(ARCHIVE) as archive:
        terminal = {line.split(maxsplit=1)[1].strip(): line.split(maxsplit=1)[0]
                    for line in archive.read("terminal_SHA256SUMS").decode().splitlines()}
        if fingerprint(INTERVALS) != terminal["budget/primary_intervals.csv"]:
            raise ValueError("low-power measurement table differs from its terminal hash")
        for record in keyed.values():
            check_snapshot(record, archive)
        for case in CASES:
            if json.loads(archive.read(f"raw/{case}/gate.json"))["passed"] is not True:
                raise ValueError(f"11-Myr control did not pass for {case}")
            seed = keyed[case, "ON", 10]
            controls[case] = seed_controls(case, seed)
            same(float(historic[case]["cumulative_net_gas_delivery_erg"]), float(reviewed[case]["net_gas_erg"]),
                 "seed cumulative gas, original and reviewed integrations")
            endpoints = {}
            for arm in ("ON", "OFF"):
                ages, _, gas = reconstruct_delivery(case, arm, historic[case], intervals, archive)
                arm_rows = [r for r in intervals if (r["case"], r["arm"]) == (case, arm)]
                labelled = math.fsum(float(r["labelled_energy_erg"]) for r in arm_rows)
                cone, stationary = (math.fsum(float(r[name])*float(r["labelled_energy_erg"]) for r in arm_rows)
                                    for name in ("cone_gas", "stationary_gas"))
                same(cone + stationary, gas[30]-gas[10], "summed signed delivery from primary interval table")
                for i in ((10, 30) if arm == "ON" else (30,)):
                    r = keyed[case, arm, i]
                    same(ages[i], r["age_myr"], "lobe and denominator age")
                    for original, current in zip(seed["lobes"], r["lobes"], strict=True):
                        h, volume = current["enthalpy_2p5pv_erg"], current["volume_kpc3"]
                        dh, dg = h-original["enthalpy_2p5pv_erg"], gas[i]-gas[10]
                        row = dict(case=case, arm=arm, index=i, age_myr=ages[i], **current,
                                   mean_pressure_dyn_cm2=h/(2.5 * volume * UNIT_LENGTH_CM**3),
                                   post_seed_enthalpy_gain_erg=dh, post_seed_net_gas_erg=dg,
                                   post_seed_cone_gas_erg=cone if i == 30 else 0.,
                                   post_seed_stationary_gas_erg=stationary if i == 30 else 0.,
                                   post_seed_labelled_input_erg=labelled if i == 30 else 0.,
                                   gain_over_post_seed_net_gas=dh/dg if i == 30 else None,
                                   cumulative_net_gas_erg=gas[i], enthalpy_over_cumulative_net_gas=h/gas[i])
                        measurements.append(row)
                        if i == 30:
                            endpoints[arm, current["tracer_cut"]] = row
            for cut in CUTS:
                a, b = (endpoints[arm, cut] for arm in ("ON", "OFF"))
                effects.append(dict(case=case, tracer_cut=cut, seed_age_myr=seed["age_myr"], endpoint_myr=a["age_myr"],
                    post_seed_enthalpy_gain_on_erg=a["post_seed_enthalpy_gain_erg"], post_seed_enthalpy_gain_off_erg=b["post_seed_enthalpy_gain_erg"],
                    post_seed_net_gas_on_erg=a["post_seed_net_gas_erg"], post_seed_net_gas_off_erg=b["post_seed_net_gas_erg"],
                    gain_over_post_seed_gas_on=a["gain_over_post_seed_net_gas"],
                    gain_over_post_seed_gas_off=b["gain_over_post_seed_net_gas"],
                    gain_ratio_change_pp=100*(b["gain_over_post_seed_net_gas"]-a["gain_over_post_seed_net_gas"]),
                    enthalpy_on_erg=a["enthalpy_2p5pv_erg"], enthalpy_off_erg=b["enthalpy_2p5pv_erg"],
                    enthalpy_change_percent=100*(b["enthalpy_2p5pv_erg"]/a["enthalpy_2p5pv_erg"]-1),
                    volume_on_kpc3=a["volume_kpc3"], volume_off_kpc3=b["volume_kpc3"],
                    volume_change_percent=100*(b["volume_kpc3"]/a["volume_kpc3"]-1),
                    mean_pressure_change_percent=100*(b["mean_pressure_dyn_cm2"]/a["mean_pressure_dyn_cm2"]-1),
                    cumulative_ratio_on=a["enthalpy_over_cumulative_net_gas"],
                    cumulative_ratio_off=b["enthalpy_over_cumulative_net_gas"],
                    cumulative_ratio_change_pp=100*(b["enthalpy_over_cumulative_net_gas"]-a["enthalpy_over_cumulative_net_gas"])))
    output.mkdir(parents=True, exist_ok=True)
    raw_path = output/"lobe_native_snapshots.json"
    raw_path.write_text(json.dumps([keyed[k] for k in sorted(keyed)], indent=2, allow_nan=False) + "\n")
    write_table(output/"lobe_measurements.csv", measurements)
    write_table(output/"lobe_paired_effects.csv", effects)
    inputs = [ARCHIVE, INTERVALS, WORKERS, HISTORICAL, REVIEW,
              *(PRODUCTION/c/"measurements.csv" for c in CASES),
              *(HISTORICAL_CUTS/c/"native_energy_selected_age.csv" for c in CASES)]
    verification = dict(native_snapshots=len(keyed), pressure_hash_matches=len(keyed), signed_gas_interval_checks=len(intervals),
                        thresholds=list(CUTS), controls=controls, source_sha256={str(p.relative_to(ASSETS)): fingerprint(p) for p in inputs},
                        output_sha256={p.name: fingerprint(p) for p in (raw_path, output/"lobe_measurements.csv", output/"lobe_paired_effects.csv")})
    (output/"lobe_verification.json").write_text(json.dumps(verification, indent=2, allow_nan=False)+"\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=OUT/"lobe_native_snapshots.json",
                        help="native results directory or the public lobe_native_snapshots.json")
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    reduce(args.source, args.output)
