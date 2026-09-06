#!/usr/bin/env python3
"""Refresh Q-029 native denominators from proven-equivalent retained census ledgers."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

from build_selected_age_dual_space_energetics import (
    CASES, ProductError, build_product, finite, native_selected_rows, read_rows, write_rows,
)

METHODS = ("binary_threshold_1e-3", "fractional", "binary_threshold_5e-3", "binary_threshold_1e-2")
EXPECTED = {(case, age) for case in CASES for age in (10, 20, 30, 40, 50) if (case, age) != ("G-HI", 50)}
NATIVE_METRICS = (
    "lobe_volume_kpc3", "lobe_mass_g", "lobe_mean_pressure_dyn_cm2", "lobe_enthalpy_2p5pv_erg",
    "lobe_thermal_erg", "lobe_kinetic_erg", "lobe_gravitational_erg", "lobe_total_erg",
    "ambient_thermal_delta_erg", "ambient_kinetic_delta_erg", "ambient_gravitational_delta_erg",
    "ambient_total_delta_erg", "retained_energy_erg", "closure_fraction_of_injected",
)


def validate_equivalence(proof_path: Path, census_root: Path) -> None:
    proof = json.loads(proof_path.read_text())
    if not (proof.get("primary_threshold") == 0.001 and proof.get("strict_equivalent") is True
            and proof.get("comparison_dtype") == "float64"
            and proof.get("proof_method") == "float32_threshold_not_representable_after_float64_promotion"):
        raise ProductError("strict primary requires an explicit supported threshold-equivalence proof")
    if float(np.float32(0.001)) == 0.001:
        raise ProductError("float32 threshold nonrepresentability premise failed")
    covered = proof.get("covered_case_ages", [])
    if len(covered) != len(EXPECTED) or {(r["case"], int(r["snapshot_index"])) for r in covered} != EXPECTED:
        raise ProductError("strict proof must cover exactly the 19 accepted case-ages")
    manifest = {}
    for case in CASES:
        for row in read_rows(census_root / case / "snapshot_manifest.csv"):
            key = (row["case"], int(row["snapshot_index"]))
            if key in manifest:
                raise ProductError(f"duplicate source manifest key: {key}")
            manifest[key] = row
    for row in covered:
        key = (row["case"], int(row["snapshot_index"]))
        source = manifest.get(key)
        dtype = np.dtype(row["tracer_dtype"])
        if dtype.kind != "f" or dtype.itemsize != 4:
            raise ProductError(f"strict proof requires float32 source tracer: {key}")
        if (source is None or row["input_h5"] != source["input_h5"]
                or row["timestep"] != source["timestep"]
                or list(row["tracer_shape"]) != [int(n) for n in source["shape_nz_ny_nx"].split("x")]):
            raise ProductError(f"strict proof does not match retained census source: {key}")


def selected_inputs(census_root: Path, reference_path: Path) -> tuple[dict[str, list[dict]], list[dict]]:
    context = {(r["case"], int(r["snapshot_index"])): r for r in read_rows(reference_path)}
    if set(context) != EXPECTED:
        raise ProductError("reference context must contain the 19 accepted case-ages")
    by_method: dict[str, list[dict]] = {method: [] for method in METHODS}
    checks = []
    for case in CASES:
        rows = read_rows(census_root / case / "energy_partition_timeseries.csv")
        lookup = {}
        for row in rows:
            key = (row["case"], int(row["snapshot_index"]), row["partition_method"])
            if row["side"] == "bipolar_total" and key[:2] in EXPECTED and key[2] in METHODS:
                if key in lookup:
                    raise ProductError(f"duplicate native census row: {key}")
                lookup[key] = row
        for key in sorted(k for k in EXPECTED if k[0] == case):
            baseline = lookup.get((*key, "fractional"))
            if baseline is None:
                raise ProductError(f"missing fractional native census row: {key}")
            injected = finite(baseline["injected_energy_erg"], context="injected", positive=True)
            for method in METHODS:
                source = lookup.get((*key, method))
                if source is None:
                    raise ProductError(f"missing native census row: {key}/{method}")
                row = {field: context[key][field] for field in (
                    "case", "snapshot_index", "actual_time_myr", "ambient_energy_interpretation", "mean_mach_kinematic"
                )}
                if not math.isclose(float(source["actual_time_myr"]), float(row["actual_time_myr"]), rel_tol=1e-12):
                    raise ProductError(f"native and context age mismatch: {key}")
                for component in ("thermal", "kinetic", "gravitational", "total"):
                    row[f"direct_lobe_{component}_erg"] = source[f"lobe_{component}_erg"]
                    row[f"ambient_{component}_delta_erg"] = source[f"gas_{component}_delta_erg"]
                for quantity, unit in (("volume", "kpc3"), ("mass", "g")):
                    row[f"direct_lobe_{quantity}_{unit}"] = finite(
                        source[f"lobe_{quantity}_{unit}"], context=f"lobe {quantity}", positive=True
                    )
                row["injected_energy_erg"] = source["injected_energy_erg"]
                row["ambient_total_fraction_of_injected"] = float(source["gas_total_delta_erg"]) / injected
                row["direct_lobe_fraction_of_injected"] = float(source["lobe_total_erg"]) / injected
                row["boundary_status"] = source["boundary_status"]
                row["closure_fraction_of_injected"] = source["closure_fraction_of_injected"]
                row["native_partition_method"] = (
                    "binary_tr1_gt_1e-3_full_cell_initial_state_subtraction_proven_ge_equivalent"
                    if method == METHODS[0] else
                    "fractional_tracer_cellwise_initial_state_subtraction" if method == "fractional" else
                    f"{method}_ge_full_cell_initial_state_subtraction"
                )
                # Retained totals include the same full initial-state subtraction in every partition.
                check = {"case": key[0], "snapshot_index": key[1], "partition_method": method}
                for component in ("thermal", "kinetic", "gravitational", "total"):
                    total = finite(source[f"lobe_{component}_erg"], context=component) + finite(source[f"gas_{component}_delta_erg"], context=component)
                    reference = finite(baseline[f"lobe_{component}_erg"], context=component) + finite(baseline[f"gas_{component}_delta_erg"], context=component)
                    error = abs(total - reference) / injected
                    if error > 1e-9:
                        raise ProductError(f"complementary {component} energy does not close: {key}/{method}")
                    check[f"{component}_difference_fraction_of_injected"] = error
                for quantity, unit in (("volume", "kpc3"), ("mass", "g")):
                    total = finite(source[f"lobe_{quantity}_{unit}"], context=quantity) + finite(source[f"gas_{quantity}_{unit}"], context=quantity)
                    reference = finite(baseline[f"lobe_{quantity}_{unit}"], context=quantity) + finite(baseline[f"gas_{quantity}_{unit}"], context=quantity)
                    error = abs(total - reference) / reference
                    if error > 1e-9:
                        raise ProductError(f"complementary {quantity} does not close: {key}/{method}")
                    check[f"{quantity}_relative_difference"] = error
                closure_error = abs(finite(source["closure_fraction_of_injected"], context="closure") - finite(baseline["closure_fraction_of_injected"], context="closure"))
                if closure_error > 1e-9:
                    raise ProductError(f"closure changed: {key}/{method}")
                check["closure_fraction_absolute_difference"] = closure_error
                checks.append(check)
                by_method[method].append(row)
    return by_method, checks


def build_refresh(*, census_root: Path, reference_native_case_age_path: Path,
                  strict_equivalence_proof: Path, observer_root: Path, output_root: Path) -> dict:
    validate_equivalence(strict_equivalence_proof, census_root)
    inputs, checks = selected_inputs(census_root, reference_native_case_age_path)
    if output_root.exists():
        raise ProductError(f"refusing to overwrite output: {output_root}")
    output_root.mkdir(parents=True)
    native = {}
    for method, rows in inputs.items():
        path = output_root / f"native_case_age_{method}.csv"
        write_rows(path, rows)
        native[method] = native_selected_rows(path)
    build_product(native_case_age_path=output_root / f"native_case_age_{METHODS[0]}.csv",
                  observer_root=observer_root, output_root=output_root / "primary_join")
    baseline = {(r["case"], r["snapshot_index"]): r for r in native["fractional"]}
    comparisons = []
    for method, rows in native.items():
        for row in rows:
            old = baseline[(row["case"], row["snapshot_index"])]
            comparison = {**row, "source_partition_method": method,
                          "role": "primary" if method == METHODS[0] else "sensitivity"}
            for metric in NATIVE_METRICS:
                value, reference = float(row[metric]), float(old[metric])
                comparison[f"{metric}_relative_change_from_fractional"] = (value - reference) / reference if reference else ""
            comparisons.append(comparison)
    write_rows(output_root / "native_partition_sensitivity.csv", comparisons)
    write_rows(output_root / "complementary_partition_checks.csv", checks)
    matched = read_rows(output_root / "primary_join" / "matched_native_xray_energetics.csv")
    recovery = []
    for method, rows in native.items():
        lookup = {(r["case"], r["snapshot_index"]): r for r in rows}
        for match in matched:
            valid = match["matched_status"] == "quantitative_dual_space_match"
            if valid and (match["volume_depth_assumption"], match["pressure_method"], match["energy_model"]) != ("geometric_depth", "ellipsoid_volume_average", "2.5pV"):
                continue
            key = (match["case"], int(match["snapshot_index"]))
            row, old = lookup[key], baseline[key]
            result = {"case": key[0], "snapshot_index": key[1], "view": match["view"],
                      "source_partition_method": method, "native_partition_method": row["native_partition_method"],
                      "quantitative_cavity_valid": match["quantitative_cavity_valid"],
                      "topology_class": match["topology_class"], "matched_status": match["matched_status"],
                      "observer_method": "geometric_depth_ellipsoid_volume_average_2.5pV"}
            for metric, numerator, denominator in (
                ("volume_recovery", "observer_volume_kpc3", "lobe_volume_kpc3"),
                ("pressure_recovery", "observer_effective_pressure_dyn_cm2", "lobe_mean_pressure_dyn_cm2"),
                ("ratio_to_native_lobe_enthalpy", "observer_enthalpy_erg", "lobe_enthalpy_2p5pv_erg"),
                ("ratio_to_retained_energy", "observer_enthalpy_erg", "retained_energy_erg"),
                ("ratio_to_injected_energy", "observer_enthalpy_erg", "injected_energy_erg"),
            ):
                result[metric] = float(match[numerator]) / float(row[denominator]) if valid else ""
                result[f"{metric}_relative_change_from_fractional"] = float(old[denominator]) / float(row[denominator]) - 1 if valid else ""
            recovery.append(result)
    write_rows(output_root / "observer_recovery_sensitivity.csv", recovery)
    sources = [strict_equivalence_proof, reference_native_case_age_path]
    sources += [census_root / case / name for case in CASES for name in ("snapshot_manifest.csv", "energy_partition_timeseries.csv")]
    sources += list(observer_root.glob("xray_*.csv")) or list(observer_root.glob("*/xray_*.csv"))
    metadata = {
        "primary": "tr1 > 0.001 at full cell weight; ambient exact complement tr1 <= 0.001",
        "reuse_basis": "retained >= census equivalent to strict > under source-bound float32-to-float64 proof",
        "initial_state_convention": "gas delta = complement-weighted current energy minus full initial cell energy; retained = gas delta + full-weight lobe energy",
        "sensitivity_masks": "fractional clip(tr1,0,1), binary >=0.005, binary >=0.01",
        "accepted_case_age_count": len(EXPECTED), "sensitivity_native_row_count": len(comparisons),
        "observer_recovery_row_count": len(recovery), "closure_tolerance_fraction_of_injected": 1e-9,
        "g_hi_50_status": "excluded", "shock_status": "separate strict-ambient refresh required",
        "sources_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
    }
    (output_root / "binary_native_refresh_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("census-root", "reference-native-case-age-path", "strict-equivalence-proof", "observer-root", "output-root"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    print(json.dumps(build_refresh(**vars(parser.parse_args())), indent=2))


if __name__ == "__main__":
    main()
