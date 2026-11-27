"""Bound the 30-Myr tracer-weighted R100 thermal partition from archived positive moments."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tarfile
import zipfile
from pathlib import Path

from build_tracer_mass_budget import volume_bounds
from four_case_energy_partition import ASSETS, CASES, PUBLISHED

OUTPUT = ASSETS / "aperture_partition_followup_2026-11-27"
NATIVE = ASSETS / "q029_binary_native_refresh_2026-09-06/remote_analysis"
AXES = ASSETS / "ghi20_compressive_front_native_2026-11-23/native_axes.npz"
CUTS = (0.001, 0.005, 0.01)


def rows30(path):
    with path.open(newline="") as stream:
        return [row for row in csv.DictReader(stream) if int(row["snapshot_index"]) == 30]


def positive_moment_bounds(moments, field, all_field, volume_ratio):
    frac = moments["fractional"]
    tracer_energy, grid_energy = float(frac[field]), float(frac[all_field])
    by_cut = {float(r["tracer_threshold"]): float(r[field]) for r in moments.values() if r["tracer_threshold"]}
    ordered = [by_cut[cut] for cut in CUTS]
    if not (0 <= tracer_energy <= grid_energy and 0 <= ordered[2] <= ordered[1] <= ordered[0] <= grid_energy):
        raise ValueError("Inconsistent positive thermal inventories")
    # Each stricter cohort is enclosed. Outside the sphere the tracer is at most CUTS[0].
    enclosed_min = sum((cut - previous) * energy for previous, cut, energy in zip((0, *CUTS), CUTS, ordered))
    exterior_max = CUTS[0] * (grid_energy - ordered[0])
    lower = max(enclosed_min, tracer_energy - exterior_max)
    if lower > tracer_energy:
        raise ValueError("Positive bounds cross")
    return volume_ratio[0] * lower, volume_ratio[1] * tracer_energy


def read_receipts(source_archive):
    with zipfile.ZipFile(OUTPUT / "outer_30myr.zip") as zipped:
        copies = {case: zipped.read(f"native/results/{case}/outer/snapshot_0030.json") for case in CASES}
    if source_archive:
        verification = json.loads((ASSETS / "production_injector_histories_2026-11-21/verification.json").read_bytes())
        with source_archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != verification["archive"]["archive_sha256"]:
                raise ValueError("Production archive hash differs from its release receipt")
        with tarfile.open(source_archive) as tar:
            for case, receipt in copies.items():
                if receipt != tar.extractfile(f"native/results/{case}/outer/snapshot_0030.json").read():
                    raise ValueError(f"Outer receipt differs for {case}")
    return copies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT / "thermal_tracer_30myr.csv")
    parser.add_argument("--source-archive", type=Path, help="Verify the packaged receipts against the full production archive")
    args = parser.parse_args()
    stocks = rows30(PUBLISHED / "sphere_components.csv")
    registration = json.loads((ASSETS / "aperture_transport_2026-11-26/registration.json").read_bytes())["cases"]
    axes_hash = hashlib.sha256(AXES.read_bytes()).hexdigest()
    volume_ratio = volume_bounds(AXES)
    receipts = read_receipts(args.source_archive)
    results = []
    for case in CASES:
        current, baseline = "lobe_thermal_erg", "masked_initial_lobe_thermal_erg"
        regional = {r["region"]: r for r in stocks if r["case"] == case and r["aperture"] == "R100"}
        all_gas = regional["all"]
        age = float(all_gas["actual_age_myr"])
        reg = registration[case]
        snap = reg["snapshots"][30]
        outer = json.loads(receipts[case])
        if (outer["case"] != case or outer["mode"] != "outer" or snap["index"] != outer["index"] or
                snap["age_myr"] != age or outer["age_myr"] != age or outer["geometry"]["threshold"] != CUTS[0] or
                snap["fixed_sha256"] != outer["fixed_receipt_sha256"] or snap["native_sha256"] != outer["historical_native_sha256"] or
                reg["input_request_sha256"] != outer["request_sha256"] or reg["static_sha256"]["axes.npz"] != axes_hash or
                all_gas["all_lobe_cells_enclosed"] != "True" or not snap["apertures"]["R100"]["available"]):
            raise ValueError(f"Input identity, geometry or containment differs for {case}")
        folder = NATIVE / case
        precision, = rows30(folder / "tracer_threshold_precision.csv")
        if (precision["case"] != case or float(precision["actual_time_myr"]) != age or
                precision["raw_tracer_dtype"] != "float32" or int(precision["exact_double_equality_cell_count"]) != 0 or
                float(precision["primary_threshold_float64"]) != CUTS[0] or int(precision["tracer_outside_unit_interval_count"]) != 0):
            raise ValueError(f"Tracer precision differs for {case}")
        moments = {r["partition_method"]: r for r in rows30(folder / "native_energy_selected_age.csv") if r["side"] == "bipolar_total"}
        if len(moments) != 4 or any(
                r["case"] != case or float(r["actual_time_myr"]) != age or
                r["region_delta_reference"] != "same_t0_cells_under_current_partition_weights" or
                r["threshold_comparison"] != ("float64_stored_value_strict_gt" if r["tracer_threshold"] else "fractional_clipped")
                for r in moments.values()):
            raise ValueError(f"Thermal moment definitions differ for {case}")
        low_now, high_now = positive_moment_bounds(moments, current, "current_thermal_erg", volume_ratio)
        low_initial, high_initial = positive_moment_bounds(moments, baseline, "initial_thermal_erg", volume_ratio)
        change = float(all_gas["thermal_delta_erg"])
        if change != snap["apertures"]["R100"]["stock"]["thermal_delta_erg"]:
            raise ValueError(f"R100 thermal stock differs for {case}")
        delivery = float(all_gas["cumulative_net_gas_delivery_erg"])
        mass = outer["tracer"]["whole_grid"]
        dilute, total = mass["dilute_tagged_mass_g"], mass["raw_tagged_mass_g"]
        if not 0 <= dilute <= total or total <= 0 or delivery <= 0:
            raise ValueError(f"Invalid mass or delivery for {case}")
        results.append(dict(
            case=case, index=30, actual_age_myr=age, historical_native_sha256=snap["native_sha256"],
            outer_receipt_sha256=hashlib.sha256(receipts[case]).hexdigest(),
            grid_tracer_mass_g=total, grid_tracer_mass_le_0p001_g=dilute, grid_dilute_share_of_tracer=dilute / total,
            r100_dilute_share_of_tracer_upper=dilute / total, r100_thermal_change_erg=change,
            cumulative_net_gas_delivery_erg=delivery, primary_ambient_thermal_over_delivery=float(regional["ambient"]["thermal_over_delivery"]),
            native_to_centre_volume_min=volume_ratio[0], native_to_centre_volume_max=volume_ratio[1],
            r100_current_tracer_thermal_min_erg=low_now, r100_current_tracer_thermal_max_erg=high_now,
            r100_initial_tracer_thermal_min_erg=low_initial, r100_initial_tracer_thermal_max_erg=high_initial,
            r100_continuous_ambient_thermal_over_delivery_min=(change - high_now + low_initial) / delivery,
            r100_continuous_ambient_thermal_over_delivery_max=(change - low_now + high_initial) / delivery,
        ))
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=results[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    main()
