#!/usr/bin/env python3
"""Independently validate the Q-029 compact native ledger and dtype proof."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from build_binary_native_refresh import CASES, EXPECTED, METHODS
from build_selected_age_dual_space_energetics import ProductError, finite, read_rows

SIDES = ("negative_z", "positive_z", "bipolar_total")
COMPONENTS = ("thermal", "kinetic", "gravitational")
TEXT_FIELDS = {"case", "side", "partition_method", "boundary_status", "residual_interpretation",
               "baseline_allocation", "region_delta_reference", "threshold_comparison",
               "input_h5", "timestep", "raw_tracer_dtype"}
OLD_ENERGY_CODE_SHA256 = "eadc395b39446af78c44d4028a8bece21b1c7f3144e8f745a21f7e1e9ce7117f"


def number(row: dict, field: str) -> float:
    return finite(row[field], context=field)


def close(actual: float, expected: float, scale: float, context: str) -> None:
    if abs(actual - expected) > 1e-9 * abs(scale):
        raise ProductError(f"{context}: {actual} != {expected} at tolerance {1e-9 * abs(scale)}")


def index(rows: list[dict], extra: tuple[str, ...] = ()) -> dict:
    result = {}
    for row in rows:
        key = (row["case"], int(row["snapshot_index"]), *(row[field] for field in extra))
        if key in result:
            raise ProductError(f"duplicate row: {key}")
        result[key] = row
    return result


def validate_numbers(row: dict) -> None:
    for field, value in row.items():
        if field in TEXT_FIELDS:
            continue
        if value == "" and (field == "boundary_energy_erg"
                            or (field == "tracer_threshold" and row.get("partition_method") == "fractional")
                            or (field == "lobe_mean_pressure_dyn_cm2" and number(row, "lobe_volume_kpc3") == 0)):
            continue
        number(row, field)


def validate_ledger(row: dict) -> None:
    validate_numbers(row)
    fractional = row["partition_method"] == "fractional"
    if row["threshold_comparison"] != ("fractional_clipped" if fractional else "float64_stored_value_strict_gt"):
        raise ProductError("unsupported native threshold comparison")
    if not fractional and number(row, "tracer_threshold") != float(row["partition_method"].removeprefix("binary_threshold_")):
        raise ProductError("native threshold does not match partition")
    injected = finite(row["injected_energy_erg"], context="injected", positive=True)
    for component in COMPONENTS:
        lobe = number(row, f"lobe_{component}_erg")
        b0 = number(row, f"masked_initial_lobe_{component}_erg")
        gas = number(row, f"gas_{component}_delta_erg")
        ld = number(row, f"lobe_region_{component}_delta_erg")
        ad = number(row, f"ambient_region_{component}_delta_erg")
        retained = number(row, f"retained_{component}_delta_erg")
        for actual, expected, label in ((lobe + gas, retained, "allocation"), (ld + ad, retained, "regions"),
                                         (lobe - b0, ld, "masked initial lobe"), (ad - b0, gas, "ambient allocation")):
            close(actual, expected, injected, f"{component} {label}")
        close(number(row, f"allocation_{component}_invariant_residual_erg"), lobe + gas - retained,
              injected, f"{component} recorded allocation invariant")
        close(number(row, f"region_{component}_invariant_residual_erg"), ld + ad - retained,
              injected, f"{component} recorded region invariant")
    for target, template in (("lobe_total_erg", "lobe_{}_erg"), ("gas_total_delta_erg", "gas_{}_delta_erg"),
                             ("masked_initial_lobe_total_erg", "masked_initial_lobe_{}_erg"),
                             ("lobe_region_total_delta_erg", "lobe_region_{}_delta_erg"),
                             ("ambient_region_total_delta_erg", "ambient_region_{}_delta_erg"),
                             ("retained_energy_erg", "retained_{}_delta_erg")):
        close(number(row, target), sum(number(row, template.format(c)) for c in COMPONENTS), injected, target)
    retained = number(row, "retained_energy_erg")
    close(number(row, "lobe_total_erg") + number(row, "gas_total_delta_erg"), retained, injected, "total allocation")
    close(number(row, "lobe_region_total_delta_erg") + number(row, "ambient_region_total_delta_erg"), retained, injected, "total regions")
    close(number(row, "unattributed_residual_erg"), injected - retained, injected, "closure residual")
    close(number(row, "closure_fraction_of_injected"), (injected - retained) / injected, 1.0, "closure fraction")
    for field in ("volume_kpc3", "mass_g", "cell_equivalent"):
        total = finite(row[f"current_{field}"], context=f"current {field}", positive=True)
        close(number(row, f"lobe_{field}") + number(row, f"gas_{field}"), total, total, f"complementary {field}")


def validate_refresh(analysis_root: Path, census_root: Path | None = None,
                     proof_output: Path | None = None) -> dict:
    if proof_output is not None and proof_output.exists():
        raise ProductError(f"refusing to overwrite proof: {proof_output}")
    sources, native, precision, hashes = {}, {}, {}, {}
    census, old_sources = {}, {}
    for case in CASES:
        for name, target, extra in (("source_manifest.csv", sources, ()),
                                    ("native_energy_selected_age.csv", native, ("partition_method", "side")),
                                    ("tracer_threshold_precision.csv", precision, ())):
            path = analysis_root / case / name
            rows = read_rows(path)
            if any(row["case"] != case for row in rows):
                raise ProductError(f"wrong case in {path}")
            target.update(index(rows, extra))
            hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        if census_root is not None:
            for name, target, extra in (("snapshot_manifest.csv", old_sources, ()),
                                       ("energy_partition_timeseries.csv", census, ("partition_method", "side"))):
                path = census_root / case / name
                target.update(index(read_rows(path), extra))
                hashes[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    expected_native = {(*key, mode, side) for key in EXPECTED for mode in METHODS for side in SIDES}
    if set(sources) != EXPECTED or set(precision) != EXPECTED or set(native) != expected_native:
        raise ProductError("refresh must contain exactly 19 source/precision rows and 228 native rows")
    for key, row in native.items():
        validate_ledger(row)
        source = sources[key[:2]]
        for field in ("actual_time_code", "actual_time_myr"):
            close(number(row, field), number(source, field), abs(number(source, field)), f"source {key} {field}")
        reference = native[(*key[:2], METHODS[0], key[3])]
        for field in ("retained_energy_erg", *(f"retained_{c}_delta_erg" for c in COMPONENTS)):
            close(number(row, field), number(reference, field), number(row, "injected_energy_erg"), f"partition {key} {field}")
        if census_root is not None:
            old = census[key]
            for field in ("lobe_volume_kpc3", "lobe_mass_g", "lobe_thermal_erg", "lobe_kinetic_erg",
                          "lobe_gravitational_erg", "lobe_total_erg", "gas_thermal_delta_erg",
                          "gas_kinetic_delta_erg", "gas_gravitational_delta_erg", "gas_total_delta_erg"):
                scale = abs(number(old, field)) if field in ("lobe_volume_kpc3", "lobe_mass_g") else number(row, "injected_energy_erg")
                close(number(row, field), number(old, field), scale, f"census {key} {field}")
    covered = []
    for key, row in sorted(precision.items()):
        validate_numbers(row)
        source = sources[key]
        if any(row[field] != source[field] for field in ("input_h5", "timestep")):
            raise ProductError(f"precision source mismatch: {key}")
        close(number(row, "actual_time_myr"), number(source, "actual_time_myr"), number(source, "actual_time_myr"), f"precision time {key}")
        if census_root is not None:
            old = old_sources[key]
            if any(source[field] != old[field] for field in ("input_h5", "timestep", "shape_nz_ny_nx")):
                raise ProductError(f"census source mismatch: {key}")
            for field in ("actual_time_myr", "actual_time_code"):
                close(number(source, field), number(old, field), number(old, field), f"census time {key}")
            baseline = old_sources[(key[0], 0)]
            if source["baseline_h5"] != baseline["input_h5"] or source["baseline_timestep"] != baseline["timestep"]:
                raise ProductError(f"census baseline mismatch: {key}")
        dtype = np.dtype(row["raw_tracer_dtype"])
        if (dtype.kind != "f" or dtype.itemsize != 4 or number(row, "exact_double_equality_cell_count") != 0
                or number(row, "primary_threshold_float64") != 0.001
                or number(row, "raw_dtype_quantized_threshold") != float(dtype.type(0.001))):
            raise ProductError(f"unsupported float32 threshold equivalence: {key}")
        primary = native[(*key, METHODS[0], "bipolar_total")]
        shape = [int(n) for n in source["shape_nz_ny_nx"].split("x")]
        if len(shape) != 3 or min(shape) < 1 or np.prod(shape) != number(primary, "current_cell_equivalent"):
            raise ProductError(f"source shape disagrees with integrated cell count: {key}")
        if any(number(row, field) != 0 for field in row if field.startswith("exact_double_equality_")):
            raise ProductError(f"nonzero exact-double equality cohort: {key}")
        for field in row:
            if field.endswith("_count"):
                value = number(row, field)
                if value < 0 or value != int(value) or value > number(primary, "current_cell_equivalent"):
                    raise ProductError(f"invalid precision count: {key}/{field}")
        covered.append({"case": key[0], "snapshot_index": key[1], "tracer_dtype": str(dtype),
                        "input_h5": source["input_h5"], "timestep": source["timestep"],
                        "tracer_shape": shape,
                        "actual_time_myr": number(source, "actual_time_myr"),
                        **{field: number(row, field) for field in row if "equality_" in field},
                        "quantized_equality_volume_fraction_of_primary": number(row, "raw_dtype_quantized_equality_volume_kpc3") / number(primary, "lobe_volume_kpc3"),
                        "quantized_equality_enthalpy_fraction_of_primary": 2.5 * number(row, "raw_dtype_quantized_equality_pressure_volume_erg") / number(primary, "lobe_enthalpy_2p5pv_erg")})
    proof = {"primary_threshold": 0.001, "strict_equivalent": True, "comparison_dtype": "float64",
             "proof_method": "float32_threshold_not_representable_after_float64_promotion",
             "covered_case_ages": covered, "quantized_threshold_materiality": "pending scientific review",
             "historical_energy_code_sha256": OLD_ENERGY_CODE_SHA256,
             "compact_source_sha256": hashes, "census_compared": census_root is not None,
             "energy_tolerance_fraction_of_injected": 1e-9, "mass_volume_relative_tolerance": 1e-9}
    if proof_output is not None:
        proof_output.parent.mkdir(parents=True, exist_ok=True)
        with proof_output.open("x") as handle:
            json.dump(proof, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--analysis-root", type=Path, required=True)
    parser.add_argument("--census-root", type=Path)
    parser.add_argument("--proof-output", type=Path)
    args = parser.parse_args()
    result = validate_refresh(args.analysis_root, args.census_root, args.proof_output)
    print(json.dumps({"status": "validated", "accepted_case_ages": len(result["covered_case_ages"]),
                      "census_compared": result["census_compared"]}))
