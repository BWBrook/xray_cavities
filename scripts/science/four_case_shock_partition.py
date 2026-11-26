"""Reconcile the selected-age ambient downstream inventories with measured injector delivery."""
from __future__ import annotations

import argparse
import itertools
import json
import math
from pathlib import Path

import numpy as np

from restate_native_delivery import CASES, PRIMARY, ROOT, csv_rows, digest, write
from snapshot_shocks import GAMMA_GAS, SECONDS_PER_MYR, UNIT_LENGTH_CM, local_three_point_slope

ASSETS = ROOT / "docs/science/assets"
BINARY = ASSETS / "q029_binary_native_refresh_2026-09-06"
CLOSEOUT = BINARY / "shock_closeout"
VALIDITY = ASSETS / "cluster_background_and_age_validity_2026-08-26"
DELIVERY = ASSETS / "native_delivery_restatement_2026-11-21"
OUT = ASSETS / "four_case_shock_partition_2026-11-26"
SIDES = ("negative_z", "positive_z")
COMPONENTS = ("thermal", "kinetic", "gravitational", "total")
FACTORS = (0.5, 1.0, 2.0)
GUARDS = {
    CLOSEOUT / "local_asset_manifest.sha256": "16c0c0450148b9925fe8a4ed02e342c5edc10129fd0d049c382ea569561abcfa",
    VALIDITY / "local_asset_manifest.sha256": "a3906b3180694e01ad49678c0e09e27e7a3e09313454f142206bf35f329577d6",
    DELIVERY / "verification.json": "76b4d15678936241ebf44a3c117c6cacdf8c5845e3dfeba527d533f600d53bef",
}


def match(a, b, label, scale=1.0):
    if not all(math.isfinite(x) for x in (a, b, scale)) or abs(a - b) > 2e-11 * max(abs(a), abs(b), scale):
        raise ValueError(f"{label}: {a} differs from {b}")


def keyed(rows, keys):
    result = {}
    for row in rows:
        index = tuple(int(row[k]) if k == "snapshot_index" else row[k] for k in keys)
        if index in result:
            raise ValueError(f"duplicate row {index}")
        result[index] = row
    return result


def load_inputs():
    hashes = {}

    def read(path, expected):
        raw = path.read_bytes()
        actual = digest(raw)
        if actual != expected:
            raise ValueError(f"hash mismatch for {path.name}")
        hashes[str(path.relative_to(ROOT))] = actual
        return raw

    def manifest(path, expected):
        lines = read(path, expected).decode().splitlines()
        return {Path(name).name: checksum for checksum, name in (line.split(None, 1) for line in lines)}

    def member(directory, checksum, name):
        return read(directory / name, checksum[name])

    shock_hashes = manifest(CLOSEOUT / "local_asset_manifest.sha256", GUARDS[CLOSEOUT / "local_asset_manifest.sha256"])
    meta = json.loads(member(CLOSEOUT, shock_hashes, "selected_age_native_shock_closeout_metadata.json"))
    shock = csv_rows(member(CLOSEOUT, shock_hashes, "native_shock_energy_selected_age.csv"))
    validity_hashes = manifest(VALIDITY / "local_asset_manifest.sha256", GUARDS[VALIDITY / "local_asset_manifest.sha256"])
    validity = csv_rows(member(VALIDITY, validity_hashes, "shock_validity_by_snapshot.csv"))
    delivery_hashes = json.loads(read(DELIVERY / "verification.json", GUARDS[DELIVERY / "verification.json"]))
    delivery = csv_rows(member(DELIVERY, delivery_hashes["products_sha256"], "primary_selected_ages.csv"))

    ambient, axial, native = [], [], []
    for case in CASES:
        directory = BINARY / "remote_analysis" / case
        case_hashes = manifest(directory / "local_asset_manifest.sha256", meta["sources"]["case_manifest_sha256"][case])
        components = csv_rows(member(directory, case_hashes, "native_energy_selected_age.csv"))
        dynamics = csv_rows(member(directory, case_hashes, "accepted_axial_shock_dynamics.csv"))
        native.extend(csv_rows(member(directory, case_hashes, "source_manifest.csv")))
        ambient.extend(r for r in components if r["partition_method"] == "binary_threshold_1e-3")
        axial.extend(r for r in dynamics if float(r["velocity_threshold_factor"]) == 1.0)
    return shock, ambient, axial, validity, delivery, native, hashes


def axial_evidence(dynamics, validity, inventories):
    gates = keyed(validity, ("case", "snapshot_index"))
    surfaces = keyed(dynamics, ("case", "side", "snapshot_index"))
    rows = []
    for case, last in CASES.items():
        for side in SIDES:
            history = sorted((r for (c, s, i), r in surfaces.items()
                              if (c, s) == (case, side) and r["status"] == "detected"),
                             key=lambda r: int(r["snapshot_index"]))
            t, d, u = (np.array([float(r[name]) for r in history]) for name in
                       ("actual_time_myr", "shock_distance_kpc", "position_uncertainty_kpc"))
            signed_speeds = {}
            for j, r in enumerate(history):
                slope, _ = local_three_point_slope(t, d, u, j)
                speed = slope * UNIT_LENGTH_CM / SECONDS_PER_MYR / 1e5
                match(abs(speed), float(r["shock_speed_km_s"]), "archived speed magnitude")
                signed_speeds[int(r["snapshot_index"])] = speed
            for i in range(last + 1):
                r, gate = surfaces[case, side, i], gates[case, i]
                match(float(r["actual_time_myr"]), float(gate["actual_time_myr"]), "axial actual age")
                position_valid = gate["both_side_position_and_jump_valid"] == "True"
                speed_valid = gate["three_snapshot_kinematics_valid"] == "True"
                inventory = inventories.get((case, i, side, 1.0))
                inventory_status = inventory["status"] if inventory else ("initial_reference" if i == 0 else "unmeasured")
                row = {"case": case, "snapshot_index": i, "actual_age_myr": float(r["actual_time_myr"]),
                       "side": side, "axial_detector_status": r["status"], "both_position_and_jump_samples_valid": position_valid,
                       "three_snapshot_kinematics_valid": speed_valid, "fit_members": gate["fit_members"],
                       "minimum_domain_margin_kpc": gate["minimum_domain_margin_kpc"], "downstream_inventory_status": inventory_status}
                for field in ("shock_distance_kpc", "position_uncertainty_kpc", "pressure_jump_ratio", "density_jump_ratio",
                              "mach_rh_pressure", "mach_rh_density"):
                    row[field] = r[field] if position_valid else ""
                row["axial_pressure_excess_over_upstream_adiabat_fraction"] = (
                    float(r["pressure_jump_ratio"]) / float(r["density_jump_ratio"])**GAMMA_GAS - 1
                    if position_valid else None
                )
                for field in ("mach_kinematic", "shock_speed_km_s", "ambient_sound_speed_km_s"):
                    row[field] = r[field] if speed_valid else ""
                row["signed_radial_speed_km_s"] = signed_speeds[i] if speed_valid else None
                row["signed_radial_mach"] = signed_speeds[i] / float(r["ambient_sound_speed_km_s"]) if speed_valid else None
                row["both_jump_machs_defined"] = bool(r["mach_rh_pressure"] and r["mach_rh_density"]) if position_valid else None
                rows.append(row)
    return rows


def build():
    shock, ambient, dynamics, validity, delivery, native, hashes = load_inputs()
    supply = keyed(delivery, ("case", "snapshot_index"))
    files = keyed(native, ("case", "snapshot_index"))
    parent = keyed(ambient, ("case", "snapshot_index", "side"))
    expected = {(c, i) for c, last in CASES.items() for i in range(10, last + 1, 10)}
    if set(supply) != expected or set(files) != expected:
        raise ValueError("selected-age source or injector inventory differs")
    for (case, i), metadata in files.items():
        if (metadata["shape_nz_ny_nx"], metadata["timestep"], metadata["baseline_timestep"],
            Path(metadata["input_h5"]).name, Path(metadata["baseline_h5"]).name) != (
                "1014x960x960", f"Timestep_{i}", "Timestep_0", f"data.{i:04d}.flt.h5", "data.0000.flt.h5"):
            raise ValueError(f"{case}/{i}: source grid, file or timestep binding differs")
        match(float(metadata["actual_time_myr"]), float(supply[case, i]["actual_age_myr"]), "source age")
    expected_rows = {(c, i, s, f) for c, i in expected for s in (*SIDES, "bipolar_total") for f in FACTORS}
    rows = {}
    for r in shock:
        case, i, side, factor = r["case"], int(r["snapshot_index"]), r["side"], float(r["threshold_factor"])
        key = (case, i, side, factor)
        if key in rows or key not in expected_rows:
            raise ValueError(f"unexpected downstream row {key}")
        a, d = parent[case, i, side], supply[case, i]
        age = float(d["actual_age_myr"])
        for source in (r, a):
            match(float(source["actual_time_myr"]), age, f"{key}: actual age")
        if (d["method"], d["quadrature"]) != PRIMARY or float(r["ambient_tracer_max"]) != .001 or r["ambient_energy_weighting"] != "binary_full_cell":
            raise ValueError(f"{key}: method mismatch")
        den = float(d["cumulative_net_gas_delivery_erg"])
        label = float(d["labelled_cumulative_kinetic_energy_erg"])
        side_label = float(a["injected_energy_erg"])
        match(side_label, label if side == "bipolar_total" else label / 2, "signed-side label")
        match(den, float(d["cumulative_cone_gas_erg"]) + float(d["cumulative_stationary_gas_erg"]), "delivery")
        if den <= 0:
            raise ValueError(f"{key}: invalid denominator")
        measured = r["status"] in {"quantitative_seeded_component", "quantitative_bilateral"}
        if measured != bool(r["total_delta_erg"]):
            raise ValueError(f"{key}: downstream status inconsistent")
        if measured and r["boundary_touch"] != "False":
            raise ValueError(f"{key}: subset touches a domain face")
        row = {"case": case, "snapshot_index": i, "actual_age_myr": age, "side": side, "threshold_factor": factor,
               "status": r["status"], "cumulative_bipolar_gas_delivery_erg": den, "cumulative_bipolar_label_erg": label,
               "selected_cell_count": r["selected_cell_count"], "volume_kpc3": r["mask_volume_kpc3"],
               "ambient_mass_g": r["ambient_weighted_mass_g"], "boundary_touch": r["boundary_touch"],
               "front_seed_cell_count": r["front_seed_cell_count"], "front_extent_offset_kpc": r["front_extent_offset_kpc"],
               "pressure_excess_threshold": float(r["pressure_excess_threshold"]),
               "density_excess_threshold": float(r["density_excess_threshold"]),
               "entropy_excess_threshold": float(r["entropy_excess_threshold"])}
        for component in COMPONENTS:
            enclosing = float(a[f"ambient_region_{component}_delta_erg"])
            part = float(r[f"{component}_delta_erg"]) if measured else None
            for name, value in (("ambient", enclosing), ("downstream", part),
                                ("ambient_outside_downstream", enclosing - part if measured else None)):
                row[f"{name}_{component}_change_erg"] = value
                row[f"{name}_{component}_change_over_delivery"] = None if value is None else value / den
        excess = float(r["irreversible_heating_erg"]) if measured else None
        thermal = row["downstream_thermal_change_erg"]
        for name, value in (("thermal_excess_over_same_cell_adiabat", excess),
                            ("same_cell_adiabatic_thermal_change", thermal - excess if measured else None)):
            row[f"{name}_erg"] = value
            row[f"{name}_over_delivery"] = None if value is None else value / den
        for name in ("ambient", "downstream", "ambient_outside_downstream"):
            if name == "ambient" or measured:
                energies = [row[f"{name}_{k}_change_erg"] for k in COMPONENTS]
                match(sum(energies[:3]), energies[3], f"{key}: components", den)
        if measured:
            match(row["downstream_total_change_erg"] / side_label, float(r["shock_fraction_of_injected"]), "old normalization")
            match(excess / side_label, float(r["irreversible_fraction_of_injected"]), "old normalization of proxy")
        rows[key] = row
    if set(rows) != expected_rows:
        raise ValueError("incomplete regional inventory")
    for (case, i), factor in itertools.product(sorted(expected), FACTORS):
        left, right, both = (rows[case, i, s, factor] for s in (*SIDES, "bipolar_total"))
        qualified = all(r["status"] == "quantitative_seeded_component" for r in (left, right))
        if (both["status"] == "quantitative_bilateral") != qualified:
            raise ValueError("bilateral gate differs from two sides")
        if qualified:
            for k in (*[f"downstream_{c}_change_erg" for c in COMPONENTS], "thermal_excess_over_same_cell_adiabat_erg", "volume_kpc3"):
                match(float(left[k]) + float(right[k]), float(both[k]), f"{case}/{i}/{k}")
    axial = axial_evidence(dynamics, validity, rows)
    axial_index = keyed(axial, ("case", "snapshot_index", "side"))
    qualified = [r for r in rows.values() if r["side"] == "bipolar_total" and r["threshold_factor"] == 1
                 and r["status"] == "quantitative_bilateral"]
    both_jumps = []
    for r in qualified:
        case, i = r["case"], r["snapshot_index"]
        if all(axial_index[case, i, s]["both_jump_machs_defined"] for s in SIDES):
            both_jumps.append(f"{case}/{i}")
    summary = {"denominator": "Cumulative signed gas energy through injector faces, both cones and stationary zone; bipolar for every row.",
               "region": "Whole-domain current ambient full cells, tr1 <= 0.001; axial gate and connected entropy-excess component.",
               "interpretation": "Instantaneous stock changes on the same cells relative to t=0. Neither a shock-dissipation integral nor a measurement of internal shocks.",
               "retained_snapshots": len(axial)//2, "positive_age_snapshots": len(axial)//2-len(CASES),
               "selected_case_ages": len(expected), "qualified_bilateral_primary": len(qualified),
               "positive_ages_without_3d_measurement": len(axial)//2-len(CASES)-len(expected),
               "qualified_with_both_jump_inversions_on_both_sides": both_jumps, "input_sha256": hashes}
    return list(rows.values()), axial, summary


def run(out):
    inventory, axial, summary = build()
    out.mkdir(parents=True, exist_ok=True)
    products = {"downstream_components.csv": inventory, "axial_evidence.csv": axial}
    for name, rows in products.items():
        write(out / name, rows)
    summary["product_sha256"] = {name: digest((out / name).read_bytes()) for name in products}
    (out / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    run(parser.parse_args().out)
