#!/usr/bin/env python3
"""Join the accepted four-case fluid, validity, X-ray, and radio surfaces."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.science.build_snapshot_science import (
    build_energy_recovery_rows,
    read_rows,
    select_cavity_recovery_surface,
    validate_fluid_surface,
    write_json,
    write_rows,
)
from scripts.science.snapshot_synthesis import (
    build_radio_power_surface,
    fit_spectral_surface,
    validate_radio_surface,
)


ASSETS = ROOT / "docs/science/assets"
FLUID_ROOT = ASSETS / "four_case_fluid_snapshot_census_2026-08-25/review_products"
VALIDITY_ROOT = ASSETS / "cluster_background_and_age_validity_2026-08-26"
OBS_ROOT = ASSETS / "four_case_selected_age_observables_2026-08-26"
XRAY_ROOT = OBS_ROOT / "four_case_xray_complete/review_products/products"
RADIO_ROOTS = {
    "C-HI": OBS_ROOT / "completed_radio_pair_1/C-HI",
    "C-LO": OBS_ROOT / "completed_radio_final/C-LO",
    "G-HI": OBS_ROOT / "completed_radio_pair_1/G-HI",
    "G-LO": OBS_ROOT / "completed_pair_2/G-LO-radio",
}
AGE_METHOD_ROOT = ASSETS / "four_case_cavity_age_method_comparison_2026-08-28"
DEFAULT_OUTPUT = ASSETS / "four_case_scientific_synthesis_2026-08-26"

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
FLUID_AGES = (0, *AGES)
VIEWS = ("0deg", "45deg", "90deg")
ENERGY_MODELS = ("pV", "2.5pV", "4pV")
AGE_METHODS = (
    "true_source_age",
    "sound_crossing_age",
    "buoyant_rise_age",
    "refill_age",
    "shock_kinematic_age",
    "spectral_age_mean_pressure",
    "spectral_age_emissivity_weighted",
)
CASE_CONTRACT = {
    "C-HI": {"environment": "cluster", "power_class": "high", "known_power": 2.0e45},
    "C-LO": {"environment": "cluster", "power_class": "low", "known_power": 2.0e43},
    "G-HI": {"environment": "group", "power_class": "high", "known_power": 2.0e45},
    "G-LO": {"environment": "group", "power_class": "low", "known_power": 2.0e43},
}


class SynthesisError(ValueError):
    """Raised when an accepted input cannot support the synthesis contract."""


def science_age_allowed(case: str, age: int) -> bool:
    """Return whether a selected snapshot is physically valid for science."""

    return case != "G-HI" or age != 50


def _float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise SynthesisError(f"invalid numeric value for {label}: {value!r}") from exc
    if not math.isfinite(result):
        raise SynthesisError(f"non-finite numeric value for {label}: {value!r}")
    return result


def _bool(value: Any, label: str) -> bool:
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise SynthesisError(f"invalid Boolean for {label}: {value!r}")
    return normalized == "true"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _selected(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if int(row["snapshot_index"]) in FLUID_AGES]


def _normalize_xray_rows(case: str) -> tuple[list[dict[str, Any]], Path]:
    path = XRAY_ROOT / case / "xray_cavity_energy.csv"
    rows = []
    for source in read_rows(path):
        rows.append(
            dict(source)
            | {
                "nominal_age_myr": source["snapshot_index"],
                "topology_status": source["topology_class"],
            }
        )
    return rows, path


def _validity_lookup() -> tuple[dict[tuple[str, int], dict[str, str]], Path]:
    path = VALIDITY_ROOT / "shock_validity_by_snapshot.csv"
    rows = read_rows(path)
    lookup = {(row["case"], int(row["snapshot_index"])): row for row in rows}
    expected = {(case, age) for case in CASES for age in range(51)}
    if set(lookup) != expected:
        raise SynthesisError("Goal 063 shock-validity table is not the exact four-case 0..50 surface")
    return lookup, path


def _background_lookup() -> tuple[dict[int, dict[str, str]], Path]:
    path = VALIDITY_ROOT / "c_lo_background_accounting.csv"
    rows = {int(row["snapshot_index"]): row for row in read_rows(path)}
    if not set(AGES).issubset(rows):
        raise SynthesisError("C-LO background accounting misses a selected age")
    return rows, path


def _load_fluid_case(case: str) -> tuple[dict[str, list[dict[str, Any]]], list[Path]]:
    root = FLUID_ROOT / case
    paths = [
        root / "snapshot_manifest.csv",
        root / "source_truth.csv",
        root / "energy_partition_timeseries.csv",
        root / "shock_dynamics.csv",
    ]
    product = validate_fluid_surface(
        case=case,
        expected_bipolar_power_erg_s=CASE_CONTRACT[case]["known_power"],
        manifest_rows=_selected(read_rows(paths[0])),
        source_rows=_selected(read_rows(paths[1])),
        energy_rows=_selected(read_rows(paths[2])),
        shock_rows=_selected(read_rows(paths[3])),
    )
    return product, paths


def _mean_or_blank(values: Sequence[Any]) -> float | str:
    parsed = [_float(value, "mean input") for value in values if value not in {"", None}]
    return float(np.mean(parsed)) if parsed else ""


def build_physics_surface(
    fluid: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    validity: Mapping[tuple[str, int], Mapping[str, Any]],
    background: Mapping[int, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for case in CASES:
        energy = {int(row["snapshot_index"]): row for row in fluid[case]["energy"]}
        shocks = {
            (int(row["snapshot_index"]), str(row["side"])): row
            for row in fluid[case]["shock"]
        }
        for age in AGES:
            if not science_age_allowed(case, age):
                continue
            row = energy[age]
            shock_rows = [shocks[(age, side)] for side in ("negative_z", "positive_z")]
            kinematics_valid = _bool(
                validity[(case, age)]["three_snapshot_kinematics_valid"],
                f"{case}/{age} shock validity",
            )
            mach = _mean_or_blank([shock["mach_kinematic"] for shock in shock_rows])
            if not kinematics_valid:
                mach = ""
            injected = _float(row["injected_energy_erg"], "injected energy")
            c_lo = background.get(age) if case == "C-LO" else None
            output.append(
                {
                    "case": case,
                    "environment": CASE_CONTRACT[case]["environment"],
                    "power_class": CASE_CONTRACT[case]["power_class"],
                    "snapshot_index": age,
                    "actual_time_myr": row["actual_time_myr"],
                    "known_bipolar_power_erg_s": CASE_CONTRACT[case]["known_power"],
                    "injected_energy_erg": injected,
                    "ambient_thermal_delta_erg": row["gas_thermal_delta_erg"],
                    "ambient_kinetic_delta_erg": row["gas_kinetic_delta_erg"],
                    "ambient_gravitational_delta_erg": row["gas_gravitational_delta_erg"],
                    "ambient_total_delta_erg": row["gas_total_delta_erg"],
                    "direct_lobe_thermal_erg": row["lobe_thermal_erg"],
                    "direct_lobe_kinetic_erg": row["lobe_kinetic_erg"],
                    "direct_lobe_gravitational_erg": row["lobe_gravitational_erg"],
                    "direct_lobe_total_erg": row["lobe_total_erg"],
                    "direct_lobe_volume_kpc3": row["lobe_volume_kpc3"],
                    "ambient_total_fraction_of_injected": _float(row["gas_total_delta_erg"], "ambient total") / injected,
                    "direct_lobe_fraction_of_injected": _float(row["lobe_total_erg"], "lobe total") / injected,
                    "closure_fraction_of_injected": row["closure_fraction_of_injected"],
                    "boundary_status": row["boundary_status"],
                    "shock_position_valid": validity[(case, age)]["both_side_position_and_jump_valid"],
                    "shock_kinematics_valid": str(kinematics_valid).lower(),
                    "negative_mach_kinematic": shock_rows[0]["mach_kinematic"] if kinematics_valid else "",
                    "positive_mach_kinematic": shock_rows[1]["mach_kinematic"] if kinematics_valid else "",
                    "mean_mach_kinematic": mach,
                    "mean_mach_rh_pressure": _mean_or_blank([shock["mach_rh_pressure"] for shock in shock_rows]) if kinematics_valid else "",
                    "mean_mach_rh_density": _mean_or_blank([shock["mach_rh_density"] for shock in shock_rows]) if kinematics_valid else "",
                    "c_lo_far_field_fraction_of_injected": c_lo["far_field_fraction_of_injected"] if c_lo else "",
                    "c_lo_inside_100_kpc_upper_bound_fraction": c_lo["inside_100_kpc_fraction_of_injected"] if c_lo else "",
                    "ambient_energy_interpretation": (
                        "whole_domain_background_dominated_inside100_upper_bound_only"
                        if case == "C-LO"
                        else "uncorrected_no_nojet_control"
                    ),
                    "inference_scope": "descriptive_single_simulation_factorial_cell",
                }
            )
    return output


def build_cavity_surface(
    fluid: Mapping[str, Mapping[str, Sequence[Mapping[str, Any]]]],
    xray: Mapping[str, Sequence[Mapping[str, Any]]],
    physics_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    physics = {(row["case"], int(row["snapshot_index"])): row for row in physics_rows}
    output: list[dict[str, Any]] = []
    for case in CASES:
        selected = select_cavity_recovery_surface(xray[case], case=case)
        recovered = build_energy_recovery_rows(energy_rows=fluid[case]["energy"], cavity_rows=selected)
        for row in recovered:
            age = int(row["snapshot_index"])
            if not science_age_allowed(case, age):
                continue
            context = physics[(case, age)]
            quantitative = bool(row["quantitative_energy_valid"])
            output.append(
                dict(row)
                | {
                    "environment": CASE_CONTRACT[case]["environment"],
                    "power_class": CASE_CONTRACT[case]["power_class"],
                    "known_bipolar_power_erg_s": CASE_CONTRACT[case]["known_power"],
                    "shock_kinematics_valid": context["shock_kinematics_valid"],
                    "mean_mach_kinematic": context["mean_mach_kinematic"] if quantitative else "",
                    "mean_mach_rh_pressure": context["mean_mach_rh_pressure"] if quantitative else "",
                    "mean_mach_rh_density": context["mean_mach_rh_density"] if quantitative else "",
                    "scientific_test_status": (
                        "quantitative_with_valid_shock"
                        if quantitative and context["shock_kinematics_valid"] == "true"
                        else "quantitative_shock_excluded"
                        if quantitative
                        else "excluded_by_xray_topology_gate"
                    ),
                    "pressure_role": "tracer_shell_proxy_not_xray_fitted",
                }
            )
    return output


def _design_matrix(
    rows: Sequence[Mapping[str, Any]],
    *,
    include_mach: bool,
    case_effects: bool,
    view_effects: bool,
) -> np.ndarray:
    columns: list[list[float]] = [[1.0] * len(rows)]
    if include_mach:
        columns.append([_float(row["mean_mach_kinematic"], "Mach") for row in rows])
    if case_effects:
        represented_cases = [case for case in CASES if any(row["case"] == case for row in rows)]
        columns.extend(
            [[float(row["case"] == case) for row in rows] for case in represented_cases[1:]]
        )
    if view_effects:
        represented_views = [view for view in VIEWS if any(row["view"] == view for row in rows)]
        columns.extend(
            [[float(row["view"] == view) for row in rows] for view in represented_views[1:]]
        )
    return np.column_stack(columns)


def _ols_effect(
    rows: Sequence[Mapping[str, Any]],
    response: str,
    *,
    case_effects: bool,
    view_effects: bool,
) -> tuple[float, float, float]:
    y = np.log10([_float(row[response], response) for row in rows])
    full = _design_matrix(rows, include_mach=True, case_effects=case_effects, view_effects=view_effects)
    reduced = _design_matrix(rows, include_mach=False, case_effects=case_effects, view_effects=view_effects)
    beta = np.linalg.lstsq(full, y, rcond=None)[0]
    prediction = full @ beta
    reduced_prediction = reduced @ np.linalg.lstsq(reduced, y, rcond=None)[0]
    total = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - float(np.sum((y - prediction) ** 2)) / total
    reduced_r2 = 1.0 - float(np.sum((y - reduced_prediction) ** 2)) / total
    return float(beta[1]), r2, r2 - reduced_r2


def build_shock_test_summary(cavity_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    primary = [
        row
        for row in cavity_rows
        if row["cavity_energy_model"] == "2.5pV"
        and row["scientific_test_status"] == "quantitative_with_valid_shock"
    ]
    output: list[dict[str, Any]] = []
    for response in ("cavity_to_injected_ratio", "cavity_to_direct_lobe_total_ratio"):
        for view in VIEWS:
            rows = [row for row in primary if row["view"] == view]
            x = np.asarray([_float(row["mean_mach_kinematic"], "Mach") for row in rows])
            y = np.log10([_float(row[response], response) for row in rows])
            output.append(
                {
                    "analysis_scope": "within_view_pooled_cases",
                    "response": response,
                    "view": view,
                    "excluded_case": "",
                    "n_case_age_view_rows": len(rows),
                    "cases_represented": ";".join(case for case in CASES if any(row["case"] == case for row in rows)),
                    "spearman_rho": float(spearmanr(x, y).statistic),
                    "mach_slope_dex_per_unit": float(np.polyfit(x, y, 1)[0]),
                    "model_r2": float(np.corrcoef(x, y)[0, 1] ** 2),
                    "incremental_mach_r2": "",
                    "inference_scope": "descriptive_nonindependent_case_age_surface_no_p_value",
                }
            )
        slope, r2, increment = _ols_effect(
            primary,
            response,
            case_effects=True,
            view_effects=True,
        )
        output.append(
            {
                "analysis_scope": "case_and_view_fixed_effect_descriptive",
                "response": response,
                "view": "all",
                "excluded_case": "",
                "n_case_age_view_rows": len(primary),
                "cases_represented": ";".join(CASES),
                "spearman_rho": "",
                "mach_slope_dex_per_unit": slope,
                "model_r2": r2,
                "incremental_mach_r2": increment,
                "inference_scope": "descriptive_fixed_effect_sensitivity_no_replicate_inference",
            }
        )
    for excluded in CASES:
        rows = [row for row in primary if row["case"] != excluded]
        slope, r2, increment = _ols_effect(
            rows,
            "cavity_to_injected_ratio",
            case_effects=True,
            view_effects=True,
        )
        output.append(
            {
                "analysis_scope": "leave_one_case_out_fixed_effect_sensitivity",
                "response": "cavity_to_injected_ratio",
                "view": "all",
                "excluded_case": excluded,
                "n_case_age_view_rows": len(rows),
                "cases_represented": ";".join(case for case in CASES if case != excluded),
                "spearman_rho": "",
                "mach_slope_dex_per_unit": slope,
                "model_r2": r2,
                "incremental_mach_r2": increment,
                "inference_scope": "descriptive_leave_one_factorial_cell_out_no_p_value",
            }
        )
    return output


def build_radio_surfaces() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    radio_power: list[dict[str, Any]] = []
    spectral_fits: list[dict[str, Any]] = []
    paths: list[Path] = []
    for case in CASES:
        path = RADIO_ROOTS[case] / "radio_view_luminosity.csv"
        paths.append(path)
        source = read_rows(path)
        for view in VIEWS:
            radio = validate_radio_surface(
                [row for row in source if row["view"] == view],
                case=case,
            )
            radio_power.extend(
                dict(row) | {"view": view}
                for row in build_radio_power_surface(
                    radio,
                    known_bipolar_power_erg_s=CASE_CONTRACT[case]["known_power"],
                )
                if science_age_allowed(case, int(row["snapshot_index"]))
            )
            fits = fit_spectral_surface(radio)
            spectral_fits.extend(
                dict(row) | {"view": view}
                for row in fits
                if science_age_allowed(case, int(row["snapshot_index"]))
            )
    return radio_power, spectral_fits, paths


def load_cavity_age_surfaces() -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, Any]],
    list[Path],
]:
    paths = [
        AGE_METHOD_ROOT / "xray_cavity_age_geometry.csv",
        AGE_METHOD_ROOT / "age_method_comparison.csv",
        AGE_METHOD_ROOT / "cavity_power_method_comparison.csv",
        AGE_METHOD_ROOT / "age_power_method_summary.csv",
    ]
    geometry, ages, powers, source_summary = (read_rows(path) for path in paths)
    for name, rows in (("geometry", geometry), ("ages", ages), ("powers", powers)):
        if any(not science_age_allowed(row["case"], int(row["snapshot_index"])) for row in rows):
            raise SynthesisError(f"{name} surface contains excluded G-HI/50 science rows")
    if len(geometry) != 74 or len(ages) != 259 or len(powers) != 518:
        raise SynthesisError("cavity-age method surface does not match the accepted 37-view contract")
    if {row["age_method"] for row in ages} != set(AGE_METHODS):
        raise SynthesisError("cavity-age method surface does not contain the seven accepted clocks")

    enriched_summary: list[dict[str, Any]] = []
    for row in source_summary:
        matching = [
            power
            for power in powers
            if power["case"] == row["case"]
            and power["age_method"] == row["age_method"]
            and power["cavity_energy_model"] == row["cavity_energy_model"]
        ]
        lower_limits = [
            _float(power["inferred_to_known_power_ratio"], "power lower limit")
            for power in matching
            if power["power_limit_direction"] == "lower_limit"
        ]
        enriched_summary.append(
            dict(row)
            | {
                "median_lower_limit_inferred_to_known_power_ratio": (
                    float(np.median(lower_limits)) if lower_limits else ""
                )
            }
        )
    return geometry, ages, powers, enriched_summary, paths


def _quantiles(values: Sequence[float]) -> tuple[float, float, float, float, float]:
    array = np.asarray(values, dtype=float)
    return (
        float(np.min(array)),
        float(np.quantile(array, 0.1)),
        float(np.median(array)),
        float(np.quantile(array, 0.9)),
        float(np.max(array)),
    )


def build_radio_power_summary(
    radio_power: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    def append_summary(
        *,
        case: str,
        method: str,
        comparator: str,
        rows: Sequence[Mapping[str, Any]],
        scatter_dex: float | str = "",
    ) -> None:
        values = [_float(row["inferred_to_known_ratio"], "power ratio") for row in rows]
        minimum, p10, median, p90, maximum = _quantiles(values)
        if scatter_dex == "":
            within = ""
        else:
            factor = 10.0 ** float(scatter_dex)
            within = sum(1.0 / factor <= value <= factor for value in values) / len(values)
        output.append(
            {
                "estimator_family": "radio_luminosity_scaling",
                "case": case,
                "environment": CASE_CONTRACT[case]["environment"],
                "power_class": CASE_CONTRACT[case]["power_class"],
                "method": method,
                "comparator": comparator,
                "quantitative_rows": len(values),
                "minimum_inferred_to_known": minimum,
                "p10_inferred_to_known": p10,
                "median_inferred_to_known": median,
                "p90_inferred_to_known": p90,
                "maximum_inferred_to_known": maximum,
                "intrinsic_scatter_dex": scatter_dex,
                "fraction_within_published_scatter": within,
                "inference_scope": "descriptive_case_age_view_surface_no_replicate_inference",
            }
        )

    for case in CASES:
        for relation in ("kokotanekov_2017_150mhz_approx", "cavagnolo_2010_1p4ghz"):
            for loss_model in ("full_loss", "lossless"):
                rows = [
                    row
                    for row in radio_power
                    if row["case"] == case
                    and row["relation"] == relation
                    and row["loss_model"] == loss_model
                ]
                append_summary(
                    case=case,
                    method=relation,
                    comparator=loss_model,
                    rows=rows,
                    scatter_dex=rows[0]["intrinsic_scatter_dex"],
                )
    return output


def build_factorial_effects(
    physics_rows: Sequence[Mapping[str, Any]],
    cavity_rows: Sequence[Mapping[str, Any]],
    radio_power: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    values: dict[tuple[str, int, str], float] = {}
    for row in physics_rows:
        case, age = row["case"], int(row["snapshot_index"])
        values[(case, age, "direct_lobe_fraction_of_injected")] = _float(
            row["direct_lobe_fraction_of_injected"], "direct lobe fraction"
        )
        if row["mean_mach_kinematic"] != "":
            values[(case, age, "mean_valid_shock_mach")] = _float(row["mean_mach_kinematic"], "Mach")
    for case in CASES:
        for age in AGES:
            if not science_age_allowed(case, age):
                continue
            selected = [
                row
                for row in cavity_rows
                if row["case"] == case
                and int(row["snapshot_index"]) == age
                and row["cavity_energy_model"] == "2.5pV"
                and row["cavity_to_injected_ratio"] != ""
            ]
            if selected:
                values[(case, age, "median_valid_2.5pV_to_injected")] = float(
                    np.median([_float(row["cavity_to_injected_ratio"], "cavity ratio") for row in selected])
                )
            values[(case, age, "quantitative_cavity_view_fraction")] = len(selected) / len(VIEWS)
            for relation, metric in (
                ("kokotanekov_2017_150mhz_approx", "median_full_loss_150MHz_power_ratio"),
                ("cavagnolo_2010_1p4ghz", "median_full_loss_1.4GHz_power_ratio"),
            ):
                rows = [
                    row
                    for row in radio_power
                    if row["case"] == case
                    and int(row["snapshot_index"]) == age
                    and row["relation"] == relation
                    and row["loss_model"] == "full_loss"
                ]
                if rows:
                    values[(case, age, metric)] = float(
                        np.median([_float(row["inferred_to_known_ratio"], "radio power ratio") for row in rows])
                    )
    metrics = sorted({key[2] for key in values})
    comparisons = (
        ("power_effect_cluster", "C-HI", "C-LO"),
        ("power_effect_group", "G-HI", "G-LO"),
        ("environment_effect_high", "G-HI", "C-HI"),
        ("environment_effect_low", "G-LO", "C-LO"),
    )
    output: list[dict[str, Any]] = []
    for age in AGES:
        for metric in metrics:
            for name, numerator_case, denominator_case in comparisons:
                numerator = values.get((numerator_case, age, metric))
                denominator = values.get((denominator_case, age, metric))
                valid = numerator is not None and denominator is not None and numerator > 0 and denominator > 0
                output.append(
                    {
                        "comparison": name,
                        "snapshot_index": age,
                        "metric": metric,
                        "numerator_expression": numerator_case,
                        "denominator_expression": denominator_case,
                        "numerator_value": numerator if numerator is not None else "",
                        "denominator_value": denominator if denominator is not None else "",
                        "positive_ratio": numerator / denominator if valid else "",
                        "log10_ratio": math.log10(numerator / denominator) if valid else "",
                        "status": "quantitative" if valid else "not_estimable_from_valid_surface",
                        "inference_scope": "descriptive_2x2_factorial_contrast_no_replicate_inference",
                    }
                )
            needed = {case: values.get((case, age, metric)) for case in CASES}
            valid = all(value is not None and value > 0 for value in needed.values())
            ratio = (
                (needed["G-HI"] / needed["G-LO"]) / (needed["C-HI"] / needed["C-LO"])
                if valid
                else ""
            )
            output.append(
                {
                    "comparison": "power_by_environment_interaction",
                    "snapshot_index": age,
                    "metric": metric,
                    "numerator_expression": "G-HI/G-LO",
                    "denominator_expression": "C-HI/C-LO",
                    "numerator_value": needed["G-HI"] / needed["G-LO"] if valid else "",
                    "denominator_value": needed["C-HI"] / needed["C-LO"] if valid else "",
                    "positive_ratio": ratio,
                    "log10_ratio": math.log10(ratio) if valid else "",
                    "status": "quantitative" if valid else "not_estimable_from_valid_surface",
                    "inference_scope": "descriptive_2x2_factorial_interaction_no_replicate_inference",
                }
            )
    return output


def build_decision_summary(
    shock_summary: Sequence[Mapping[str, Any]],
    radio_summary: Sequence[Mapping[str, Any]],
    age_summary: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    raw = [
        row
        for row in shock_summary
        if row["analysis_scope"] == "within_view_pooled_cases"
        and row["response"] == "cavity_to_injected_ratio"
    ]
    adjusted = next(
        row
        for row in shock_summary
        if row["analysis_scope"] == "case_and_view_fixed_effect_descriptive"
        and row["response"] == "cavity_to_injected_ratio"
    )
    leave_one_out = [
        row
        for row in shock_summary
        if row["analysis_scope"] == "leave_one_case_out_fixed_effect_sensitivity"
    ]
    raw_rho = [_float(row["spearman_rho"], "rho") for row in raw]
    loo_slopes = [_float(row["mach_slope_dex_per_unit"], "LOCO slope") for row in leave_one_out]
    t1_decision = (
        "strong_pooled_negative_pattern_not_case_robust"
        if max(raw_rho) < -0.5
        and _float(adjusted["mach_slope_dex_per_unit"], "adjusted slope") < 0
        and min(loo_slopes) < 0 < max(loo_slopes)
        else "pattern_requires_review"
    )

    def radio_medians(method: str) -> dict[str, float]:
        return {
            row["case"]: _float(row["median_inferred_to_known"], "median power ratio")
            for row in radio_summary
            if row["method"] == method and row["comparator"] == "full_loss"
        }

    age_lookup = {
        (row["case"], row["age_method"]): row
        for row in age_summary
        if row["cavity_energy_model"] == "2.5pV"
    }
    true_power = {
        case: _float(
            age_lookup[(case, "true_source_age")]["median_exact_inferred_to_known_power_ratio"],
            "true-age median power ratio",
        )
        for case in CASES
    }
    mean_pressure_parts: list[str] = []
    for case in CASES:
        row = age_lookup[(case, "spectral_age_mean_pressure")]
        exact = row["median_exact_inferred_to_known_power_ratio"]
        if exact != "":
            mean_pressure_parts.append(f"{case} exact median={float(exact):.3g}")
        else:
            lower = _float(
                row["median_lower_limit_inferred_to_known_power_ratio"],
                "spectral power lower limit",
            )
            mean_pressure_parts.append(f"{case} median lower bound>{lower:.3g}")
    primary_censored = sum(
        int(age_lookup[(case, "spectral_age_mean_pressure")]["power_lower_limit_rows"])
        for case in CASES
    )
    radio150 = radio_medians("kokotanekov_2017_150mhz_approx")
    radio14 = radio_medians("cavagnolo_2010_1p4ghz")
    return [
        {
            "test_id": "T1",
            "question": "Does X-ray cavity-energy bias worsen with shock Mach?",
            "observation": (
                f"Pooled within-view Spearman rho spans {min(raw_rho):.3f} to {max(raw_rho):.3f}; "
                f"case/view-adjusted slope is {float(adjusted['mach_slope_dex_per_unit']):.4f} dex per Mach."
            ),
            "inference": "The pooled anticorrelation is clear, but case/power/environment and age jointly carry much of it.",
            "decision": t1_decision,
            "material_uncertainty": "Leave-one-case-out slopes change sign; four deterministic factorial cells provide no replicate inference.",
            "supervisor_input": "The paired native-grid/X-ray audit is required before framing Mach as an independent explanatory effect.",
        },
        {
            "test_id": "T2",
            "question": "How do seven distinct cavity-age estimators alter recovery of known bipolar jet power?",
            "observation": (
                "True-age 2.5pV medians: "
                + "; ".join(f"{case}={true_power[case]:.3g}" for case in CASES)
                + ". Mean-pressure spectral: "
                + "; ".join(mean_pressure_parts)
                + "."
            ),
            "inference": "Age choice changes inferred power by factors of a few, but cannot explain the very large high-power cavity-energy deficit.",
            "decision": "age_method_bias_modulates_not_explains_cavity_energy_deficit",
            "material_uncertainty": (
                f"{primary_censored}/37 mean-pressure spectral rows are lower limits; "
                "pressure remains a tracer-shell proxy and age methods must remain separate."
            ),
            "supervisor_input": "Stas method directive applied; dual-space volume and pressure decomposition is next.",
        },
        {
            "test_id": "T3",
            "question": "Do standard radio-luminosity relations recover known bipolar jet power?",
            "observation": (
                "150 MHz full-loss medians: "
                + "; ".join(f"{case}={radio150[case]:.3g}" for case in CASES)
                + ". 1.4 GHz medians: "
                + "; ".join(f"{case}={radio14[case]:.3g}" for case in CASES)
                + "."
            ),
            "inference": "The relations show systematic jet-power and environment dependence, not a common unbiased recovery.",
            "decision": "radio_scalings_power_and_environment_dependent",
            "material_uncertainty": "Published intrinsic scatter is carried, but the four simulations are controlled examples rather than a sampled population.",
            "supervisor_input": "Use with the corrected G-HI boundary gate; final framing follows the dual-space energetics audit.",
        },
    ]


def plot_synthesis(
    physics: Sequence[Mapping[str, Any]],
    cavity: Sequence[Mapping[str, Any]],
    radio_power: Sequence[Mapping[str, Any]],
    age_summary: Sequence[Mapping[str, Any]],
    output: Path,
) -> None:
    colors = {"C-HI": "#0072B2", "C-LO": "#56B4E9", "G-HI": "#D55E00", "G-LO": "#E69F00"}
    markers = {"0deg": "o", "45deg": "s", "90deg": "^"}
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 8.4), constrained_layout=True)

    for case in CASES:
        rows = sorted([row for row in physics if row["case"] == case], key=lambda row: int(row["snapshot_index"]))
        axes[0, 0].plot(
            [_float(row["actual_time_myr"], "time") for row in rows],
            [_float(row["direct_lobe_fraction_of_injected"], "lobe fraction") for row in rows],
            marker="o",
            color=colors[case],
            label=case,
        )
    axes[0, 0].set(xlabel="Actual source age (Myr)", ylabel="Direct lobe energy / injected", title="Direct lobe retention")
    axes[0, 0].set_yscale("log")

    primary = [
        row
        for row in cavity
        if row["cavity_energy_model"] == "2.5pV"
        and row["scientific_test_status"] == "quantitative_with_valid_shock"
    ]
    for case in CASES:
        for view in VIEWS:
            rows = [row for row in primary if row["case"] == case and row["view"] == view]
            if rows:
                axes[0, 1].scatter(
                    [_float(row["mean_mach_kinematic"], "Mach") for row in rows],
                    [_float(row["cavity_to_injected_ratio"], "cavity ratio") for row in rows],
                    color=colors[case],
                    marker=markers[view],
                    alpha=0.8,
                )
    axes[0, 1].axhline(1.0, color="black", linestyle=":", linewidth=1)
    axes[0, 1].set(xlabel="Mean valid kinematic shock Mach", ylabel="2.5pV / injected energy", title="Cavity bias versus shock strength")
    axes[0, 1].set_yscale("log")
    axes[0, 1].legend(
        handles=(
            *(
                Line2D([], [], color=colors[case], marker="o", linestyle="none", label=case)
                for case in CASES
            ),
            *(
                Line2D([], [], color="0.35", marker=markers[view], linestyle="none", label=view)
                for view in VIEWS
            ),
        ),
        fontsize=7,
        ncol=2,
        loc="lower left",
    )

    for case in CASES:
        rows = [
            row
            for row in radio_power
            if row["case"] == case
            and row["relation"] == "kokotanekov_2017_150mhz_approx"
            and row["loss_model"] == "full_loss"
        ]
        points = []
        for age in AGES:
            values = [
                _float(row["inferred_to_known_ratio"], "radio ratio")
                for row in rows
                if int(row["snapshot_index"]) == age
            ]
            if values:
                points.append((age, float(np.median(values))))
        axes[1, 0].plot(
            [point[0] for point in points],
            [point[1] for point in points],
            marker="o",
            color=colors[case],
            label=case,
        )
    axes[1, 0].axhline(1.0, color="black", linestyle=":", linewidth=1)
    axes[1, 0].set(xlabel="Source age (Myr)", ylabel="150 MHz inferred / known power", title="Radio-scaling power recovery")
    axes[1, 0].set_yscale("log")

    method_labels = {
        "true_source_age": "True",
        "sound_crossing_age": "Sound",
        "buoyant_rise_age": "Buoyant",
        "refill_age": "Refill",
        "shock_kinematic_age": "Shock",
        "spectral_age_mean_pressure": "Spec mean",
        "spectral_age_emissivity_weighted": "Spec emiss",
    }
    lookup = {
        (row["case"], row["age_method"]): row
        for row in age_summary
        if row["cavity_energy_model"] == "2.5pV"
    }
    matrix = np.full((len(CASES), len(AGE_METHODS)), np.nan)
    annotations: list[list[str]] = [["--"] * len(AGE_METHODS) for _ in CASES]
    for case_index, case in enumerate(CASES):
        for method_index, method in enumerate(AGE_METHODS):
            row = lookup[(case, method)]
            exact = row["median_exact_inferred_to_known_power_ratio"]
            lower = row["median_lower_limit_inferred_to_known_power_ratio"]
            if exact != "":
                value = _float(exact, "exact median cavity power")
                annotations[case_index][method_index] = f"{value:.2g}"
            elif lower != "":
                value = _float(lower, "median cavity power lower limit")
                annotations[case_index][method_index] = f">{value:.2g}"
            else:
                continue
            matrix[case_index, method_index] = math.log10(value)
    image = axes[1, 1].imshow(matrix, aspect="auto", cmap="viridis", vmin=-3.2, vmax=0.3)
    axes[1, 1].set_xticks(range(len(AGE_METHODS)), [method_labels[method] for method in AGE_METHODS], rotation=35, ha="right")
    axes[1, 1].set_yticks(range(len(CASES)), CASES)
    axes[1, 1].set_title("Median 2.5pV power recovery by age method")
    for row_index, labels in enumerate(annotations):
        for column_index, label in enumerate(labels):
            cell = matrix[row_index, column_index]
            text_color = "black" if np.isnan(cell) or cell > -0.4 else "white"
            axes[1, 1].text(column_index, row_index, label, ha="center", va="center", fontsize=7, color=text_color)
    colorbar = fig.colorbar(image, ax=axes[1, 1], fraction=0.046, pad=0.04)
    colorbar.set_label("log10(inferred / known power)")

    axes[0, 0].legend(fontsize=8, ncol=2)
    axes[1, 0].legend(fontsize=8, ncol=2)
    fig.savefig(output, dpi=180)
    plt.close(fig)


def build_synthesis(output_root: Path) -> dict[str, Any]:
    output_root = Path(output_root)
    if output_root.exists():
        raise SynthesisError(f"refusing to overwrite output root: {output_root}")
    output_root.mkdir(parents=True)

    validity, validity_path = _validity_lookup()
    background, background_path = _background_lookup()
    fluid: dict[str, dict[str, list[dict[str, Any]]]] = {}
    provenance_paths: list[Path] = [validity_path, background_path]
    xray: dict[str, list[dict[str, Any]]] = {}
    for case in CASES:
        product, paths = _load_fluid_case(case)
        fluid[case] = product
        provenance_paths.extend(paths)
        xray[case], path = _normalize_xray_rows(case)
        provenance_paths.append(path)

    physics = build_physics_surface(fluid, validity, background)
    cavity = build_cavity_surface(fluid, xray, physics)
    shock_summary = build_shock_test_summary(cavity)
    radio_power, spectral_fits, radio_paths = build_radio_surfaces()
    provenance_paths.extend(radio_paths)
    geometry, age_methods, cavity_powers, age_summary, age_paths = load_cavity_age_surfaces()
    provenance_paths.extend(age_paths)
    radio_summary = build_radio_power_summary(radio_power)
    factorial = build_factorial_effects(physics, cavity, radio_power)
    decisions = build_decision_summary(shock_summary, radio_summary, age_summary)

    tables = {
        "case_age_physics.csv": physics,
        "cavity_energy_recovery.csv": cavity,
        "shock_cavity_test_summary.csv": shock_summary,
        "radio_power_inference.csv": radio_power,
        "spectral_fits.csv": spectral_fits,
        "xray_cavity_age_geometry.csv": geometry,
        "age_method_comparison.csv": age_methods,
        "cavity_power_method_comparison.csv": cavity_powers,
        "age_power_method_summary.csv": age_summary,
        "radio_power_recovery_summary.csv": radio_summary,
        "factorial_effects.csv": factorial,
        "scientific_decision_summary.csv": decisions,
    }
    for name, rows in tables.items():
        write_rows(output_root / name, rows)

    provenance = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
            "role": "accepted_compact_science_input",
        }
        for path in sorted(set(provenance_paths))
    ]
    write_rows(output_root / "input_provenance.csv", provenance)
    plot_synthesis(
        physics,
        cavity,
        radio_power,
        age_summary,
        output_root / "four_case_scientific_synthesis.png",
    )

    metadata = {
        "status": "complete_corrected_local_scientific_synthesis",
        "decision_label": "FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT",
        "cases": list(CASES),
        "selected_snapshot_indices_by_case": {
            case: [age for age in AGES if science_age_allowed(case, age)]
            for case in CASES
        },
        "known_bipolar_power_erg_s": {
            case: CASE_CONTRACT[case]["known_power"] for case in CASES
        },
        "primary_tests": {
            row["test_id"]: row["decision"] for row in decisions
        },
        "method_gates": {
            "cavity": "exactly two non-crossing opposite-side X-ray components",
            "boundary": "G-HI 50 Myr excluded from every science product",
            "shock": "bilateral positive-speed supersonic gate; Goal 063 centred kinematics",
            "pressure": "tracer-shell midpoint proxy, not X-ray fitted",
            "C-LO_ambient_energy": "whole-domain background dominated; inside 100 kpc is an upper bound",
            "radio": "corrected PRAiSE2 full-loss primary; lossless comparator",
            "spectral_age": "mean-pressure primary; emissivity-weighted sensitivity; censored rows excluded from ordinary medians",
            "cavity_age": "true, sound, buoyant, refill, shock, and both spectral clocks retained separately",
            "inference": "descriptive deterministic 2x2 factorial; no replicate p-values",
        },
        "row_counts": {name: len(rows) for name, rows in tables.items()},
        "input_count": len(provenance),
        "figure": "four_case_scientific_synthesis.png",
    }
    write_json(output_root / "four_case_scientific_synthesis_metadata.json", metadata)

    manifest_paths = sorted(path for path in output_root.iterdir() if path.is_file())
    (output_root / "local_asset_manifest.sha256").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in manifest_paths)
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metadata = build_synthesis(args.output_root)
    print(f"status={metadata['status']}")
    print(f"decision_label={metadata['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
