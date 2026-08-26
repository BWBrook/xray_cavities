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
from scripts.science.snapshot_inference import (
    equipartition_field_ug_delta,
    maximum_age_field_ug,
    spectral_age_myr,
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
DEFAULT_OUTPUT = ASSETS / "four_case_scientific_synthesis_2026-08-26"

CASES = ("C-HI", "C-LO", "G-HI", "G-LO")
AGES = (10, 20, 30, 40, 50)
FLUID_AGES = (0, *AGES)
VIEWS = ("0deg", "45deg", "90deg")
ENERGY_MODELS = ("pV", "2.5pV", "4pV")
FIELD_TREATMENTS = (
    "observer_delta_equipartition",
    "matched_praise_effective",
    "maximum_age",
)
AGE_ESTIMATORS = ("true_source_age", "sound_age", "buoyancy_age", "refill_age")
SECONDS_PER_MYR = 3.15576e13
CASE_CONTRACT = {
    "C-HI": {"environment": "cluster", "power_class": "high", "known_power": 2.0e45},
    "C-LO": {"environment": "cluster", "power_class": "low", "known_power": 2.0e43},
    "G-HI": {"environment": "group", "power_class": "high", "known_power": 2.0e45},
    "G-LO": {"environment": "group", "power_class": "low", "known_power": 2.0e43},
}


class SynthesisError(ValueError):
    """Raised when an accepted input cannot support the synthesis contract."""


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


def build_radio_and_spectral_surfaces(
    cavity_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[Path]]:
    cavity = {
        (row["case"], int(row["snapshot_index"]), row["view"], row["cavity_energy_model"]): row
        for row in cavity_rows
    }
    radio_power: list[dict[str, Any]] = []
    spectral_fits: list[dict[str, Any]] = []
    spectral_power: list[dict[str, Any]] = []
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
            )
            fits = fit_spectral_surface(radio)
            spectral_fits.extend(dict(row) | {"view": view} for row in fits)
            radio_by_key = {
                (int(row["snapshot_index"]), row["loss_model"], float(row["frequency_ghz"])): row
                for row in radio
            }
            for fit in fits:
                age = int(fit["snapshot_index"])
                radio_1p4 = radio_by_key[(age, "full_loss", 1.4)]
                for model in ENERGY_MODELS:
                    cav = cavity[(case, age, view, model)]
                    valid = bool(cav["quantitative_energy_valid"]) and _float(cav["cavity_energy_erg"], "cavity energy") > 0.0
                    fields: dict[str, float | None]
                    if valid:
                        fields = {
                            "observer_delta_equipartition": equipartition_field_ug_delta(
                                _float(radio_1p4["luminosity_w_hz"], "radio luminosity"),
                                frequency_ghz=1.4,
                                volume_kpc3=_float(cav["cavity_volume_kpc3"], "cavity volume"),
                                alpha_injection=_float(fit["alpha_injection"], "injection index"),
                            ),
                            "matched_praise_effective": _float(
                                radio_1p4["effective_magnetic_field_ug"], "PRAiSE effective field"
                            ),
                            "maximum_age": maximum_age_field_ug(0.05),
                        }
                    else:
                        fields = {name: None for name in FIELD_TREATMENTS}
                    for treatment, field in fields.items():
                        if field is None:
                            age_spec: float | str = ""
                            power: float | str = ""
                            power_ratio: float | str = ""
                            age_ratio: float | str = ""
                            status = "excluded_by_xray_topology_gate"
                        else:
                            age_spec = spectral_age_myr(
                                _float(fit["reported_break_ghz"], "reported break"),
                                field,
                                redshift=0.05,
                            )
                            power = _float(cav["cavity_energy_erg"], "cavity energy") / (age_spec * SECONDS_PER_MYR)
                            power_ratio = power / CASE_CONTRACT[case]["known_power"]
                            age_ratio = age_spec / _float(cav["actual_time_myr"], "actual time")
                            status = (
                                "quantitative_censored_break"
                                if fit["spectral_age_limit_direction"] != "none"
                                else "quantitative_in_band_break"
                            )
                        spectral_power.append(
                            {
                                "case": case,
                                "environment": CASE_CONTRACT[case]["environment"],
                                "power_class": CASE_CONTRACT[case]["power_class"],
                                "snapshot_index": age,
                                "actual_time_myr": cav["actual_time_myr"],
                                "view": view,
                                "cavity_energy_model": model,
                                "cavity_energy_erg": cav["cavity_energy_erg"],
                                "quantitative_energy_valid": str(bool(cav["quantitative_energy_valid"])).lower(),
                                "break_status": fit["break_status"],
                                "spectral_age_limit_direction": fit["spectral_age_limit_direction"],
                                "reported_break_ghz": fit["reported_break_ghz"],
                                "field_treatment": treatment,
                                "magnetic_field_ug": field if field is not None else "",
                                "spectral_age_myr": age_spec,
                                "spectral_to_true_age_ratio": age_ratio,
                                "inferred_cavity_power_erg_s": power,
                                "known_bipolar_power_erg_s": CASE_CONTRACT[case]["known_power"],
                                "inferred_to_known_ratio": power_ratio,
                                "status": status,
                            }
                        )
    return radio_power, spectral_fits, spectral_power, paths


def build_cavity_age_power_surface(
    cavity_rows: Sequence[Mapping[str, Any]],
    xray_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[Path]]:
    shells: dict[tuple[str, int, str], dict[str, str]] = {}
    paths: list[Path] = []
    side_energy: dict[tuple[str, int, str, str, str], dict[str, Any]] = {}
    for case in CASES:
        path = XRAY_ROOT / case / "cavity_shell_context.csv"
        paths.append(path)
        for row in read_rows(path):
            shells[(case, int(row["nominal_age_myr"]), row["side"])] = row
        for row in xray_rows[case]:
            if (
                row["side"] in {"negative_z", "positive_z"}
                and row["volume_depth_assumption"] == "geometric_depth"
                and row["energy_model"] in ENERGY_MODELS
            ):
                side_energy[(case, int(row["snapshot_index"]), row["view"], row["energy_model"], row["side"])] = row
    output: list[dict[str, Any]] = []
    for cavity in cavity_rows:
        case = cavity["case"]
        age = int(cavity["snapshot_index"])
        view = cavity["view"]
        model = cavity["cavity_energy_model"]
        valid = bool(cavity["quantitative_energy_valid"])
        for estimator in AGE_ESTIMATORS:
            if not valid:
                inferred: float | str = ""
                inferred_ratio: float | str = ""
                negative_age: float | str = ""
                positive_age: float | str = ""
                status = "excluded_by_xray_topology_gate"
            elif estimator == "true_source_age":
                negative_age = positive_age = cavity["actual_time_myr"]
                inferred = _float(cavity["cavity_energy_erg"], "cavity energy") / (
                    _float(cavity["actual_time_myr"], "actual time") * SECONDS_PER_MYR
                )
                inferred_ratio = inferred / CASE_CONTRACT[case]["known_power"]
                status = "quantitative_truth_age_diagnostic"
            else:
                field = {
                    "sound_age": "sound_age_myr",
                    "buoyancy_age": "buoyancy_age_myr",
                    "refill_age": "refill_age_myr",
                }[estimator]
                ages = {
                    side: _float(shells[(case, age, side)][field], field)
                    for side in ("negative_z", "positive_z")
                }
                energies = {
                    side: _float(side_energy[(case, age, view, model, side)]["energy_erg"], "side cavity energy")
                    for side in ("negative_z", "positive_z")
                }
                negative_age = ages["negative_z"]
                positive_age = ages["positive_z"]
                inferred = sum(energies[side] / (ages[side] * SECONDS_PER_MYR) for side in ages)
                inferred_ratio = inferred / CASE_CONTRACT[case]["known_power"]
                status = "quantitative_tracer_geometry_age_proxy"
            output.append(
                {
                    "case": case,
                    "environment": CASE_CONTRACT[case]["environment"],
                    "power_class": CASE_CONTRACT[case]["power_class"],
                    "snapshot_index": age,
                    "actual_time_myr": cavity["actual_time_myr"],
                    "view": view,
                    "cavity_energy_model": model,
                    "quantitative_energy_valid": str(valid).lower(),
                    "age_estimator": estimator,
                    "negative_side_age_myr": negative_age,
                    "positive_side_age_myr": positive_age,
                    "inferred_cavity_power_erg_s": inferred,
                    "known_bipolar_power_erg_s": CASE_CONTRACT[case]["known_power"],
                    "inferred_to_known_ratio": inferred_ratio,
                    "status": status,
                    "age_role": (
                        "simulation_truth_age_diagnostic"
                        if estimator == "true_source_age"
                        else "tracer_geometry_context_not_xray_fitted"
                    ),
                }
            )
    return output, paths


def _quantiles(values: Sequence[float]) -> tuple[float, float, float, float, float]:
    array = np.asarray(values, dtype=float)
    return (
        float(np.min(array)),
        float(np.quantile(array, 0.1)),
        float(np.median(array)),
        float(np.quantile(array, 0.9)),
        float(np.max(array)),
    )


def build_jet_power_summary(
    radio_power: Sequence[Mapping[str, Any]],
    spectral_power: Sequence[Mapping[str, Any]],
    cavity_age_power: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    def append_summary(
        *,
        family: str,
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
                "estimator_family": family,
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
                    family="radio_luminosity_scaling",
                    case=case,
                    method=relation,
                    comparator=loss_model,
                    rows=rows,
                    scatter_dex=rows[0]["intrinsic_scatter_dex"],
                )
        for model in ("2.5pV", "4pV"):
            for field in FIELD_TREATMENTS:
                rows = [
                    row
                    for row in spectral_power
                    if row["case"] == case
                    and row["cavity_energy_model"] == model
                    and row["field_treatment"] == field
                    and row["inferred_to_known_ratio"] != ""
                ]
                append_summary(
                    family="cavity_energy_over_spectral_age",
                    case=case,
                    method=model,
                    comparator=field,
                    rows=rows,
                )
            for estimator in AGE_ESTIMATORS:
                rows = [
                    row
                    for row in cavity_age_power
                    if row["case"] == case
                    and row["cavity_energy_model"] == model
                    and row["age_estimator"] == estimator
                    and row["inferred_to_known_ratio"] != ""
                ]
                append_summary(
                    family="cavity_energy_over_age_proxy",
                    case=case,
                    method=model,
                    comparator=estimator,
                    rows=rows,
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
    jet_summary: Sequence[Mapping[str, Any]],
    spectral_fits: Sequence[Mapping[str, Any]],
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

    def medians(family: str, method: str, comparator: str) -> dict[str, float]:
        return {
            row["case"]: _float(row["median_inferred_to_known"], "median power ratio")
            for row in jet_summary
            if row["estimator_family"] == family
            and row["method"] == method
            and row["comparator"] == comparator
        }

    cavity = medians("cavity_energy_over_spectral_age", "2.5pV", "matched_praise_effective")
    radio150 = medians("radio_luminosity_scaling", "kokotanekov_2017_150mhz_approx", "full_loss")
    radio14 = medians("radio_luminosity_scaling", "cavagnolo_2010_1p4ghz", "full_loss")
    censored = sum(row["spectral_age_limit_direction"] != "none" for row in spectral_fits)
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
            "supervisor_input": "Required before framing Mach as an independent explanatory effect.",
        },
        {
            "test_id": "T2",
            "question": "Does 2.5pV divided by an integrated spectral age recover known bipolar jet power?",
            "observation": "; ".join(f"{case} median={cavity[case]:.3g}" for case in CASES),
            "inference": "The estimator is case dependent: roughly order-unity only for C-LO and strongly low for the high-power and G-LO cases.",
            "decision": "cavity_spectral_power_not_universal_recovery_estimator",
            "material_uncertainty": f"{censored}/60 integrated spectra have an out-of-band censored break; pressure is a tracer-shell proxy.",
            "supervisor_input": "Required for publication interpretation of censored spectral ages and the pressure proxy.",
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
            "supervisor_input": "Required to choose the strongest defensible paper framing and literature comparison.",
        },
    ]


def plot_synthesis(
    physics: Sequence[Mapping[str, Any]],
    cavity: Sequence[Mapping[str, Any]],
    radio_power: Sequence[Mapping[str, Any]],
    spectral_power: Sequence[Mapping[str, Any]],
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
        by_age = {
            age: np.median([_float(row["inferred_to_known_ratio"], "radio ratio") for row in rows if int(row["snapshot_index"]) == age])
            for age in AGES
        }
        axes[1, 0].plot(AGES, [by_age[age] for age in AGES], marker="o", color=colors[case], label=case)
    axes[1, 0].axhline(1.0, color="black", linestyle=":", linewidth=1)
    axes[1, 0].set(xlabel="Source age (Myr)", ylabel="150 MHz inferred / known power", title="Radio-scaling power recovery")
    axes[1, 0].set_yscale("log")

    for case in CASES:
        rows = [
            row
            for row in spectral_power
            if row["case"] == case
            and row["cavity_energy_model"] == "2.5pV"
            and row["field_treatment"] == "matched_praise_effective"
            and row["inferred_to_known_ratio"] != ""
        ]
        points = []
        for age in AGES:
            values = [_float(row["inferred_to_known_ratio"], "spectral power ratio") for row in rows if int(row["snapshot_index"]) == age]
            if values:
                points.append((age, float(np.median(values))))
        if points:
            axes[1, 1].plot(
                [point[0] for point in points],
                [point[1] for point in points],
                marker="o",
                color=colors[case],
                label=case,
            )
    axes[1, 1].axhline(1.0, color="black", linestyle=":", linewidth=1)
    axes[1, 1].set(
        xlabel="Source age (Myr)",
        ylabel="Inferred (2.5pV / spectral age) / known power",
        title="Cavity-spectral power recovery",
    )
    axes[1, 1].set_yscale("log")

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
    radio_power, spectral_fits, spectral_power, radio_paths = build_radio_and_spectral_surfaces(cavity)
    provenance_paths.extend(radio_paths)
    cavity_age_power, shell_paths = build_cavity_age_power_surface(cavity, xray)
    provenance_paths.extend(shell_paths)
    jet_summary = build_jet_power_summary(radio_power, spectral_power, cavity_age_power)
    factorial = build_factorial_effects(physics, cavity, radio_power)
    decisions = build_decision_summary(shock_summary, jet_summary, spectral_fits)

    tables = {
        "case_age_physics.csv": physics,
        "cavity_energy_recovery.csv": cavity,
        "shock_cavity_test_summary.csv": shock_summary,
        "radio_power_inference.csv": radio_power,
        "spectral_fits.csv": spectral_fits,
        "spectral_cavity_power_inference.csv": spectral_power,
        "cavity_age_power_inference.csv": cavity_age_power,
        "jet_power_recovery_summary.csv": jet_summary,
        "factorial_effects.csv": factorial,
        "scientific_decision_summary.csv": decisions,
    }
    for name, rows in tables.items():
        write_rows(output_root / name, rows)

    provenance = [
        {
            "path": str(path.relative_to(ROOT)),
            "sha256": _sha256(path),
            "role": "accepted_Goal062_063_064_compact_input",
        }
        for path in sorted(set(provenance_paths))
    ]
    write_rows(output_root / "input_provenance.csv", provenance)
    plot_synthesis(
        physics,
        cavity,
        radio_power,
        spectral_power,
        output_root / "four_case_scientific_synthesis.png",
    )

    metadata = {
        "status": "complete_local_scientific_synthesis",
        "decision_label": "FOUR_CASE_SYNTHESIS_COMPLETE_SUPERVISOR_INTERPRETATION_READY",
        "cases": list(CASES),
        "selected_snapshot_indices": list(AGES),
        "known_bipolar_power_erg_s": {
            case: CASE_CONTRACT[case]["known_power"] for case in CASES
        },
        "primary_tests": {
            row["test_id"]: row["decision"] for row in decisions
        },
        "method_gates": {
            "cavity": "exactly two non-crossing opposite-side X-ray components",
            "shock": "Goal 063 centred-kinematic validity; G-HI 50 Myr excluded",
            "pressure": "tracer-shell midpoint proxy, not X-ray fitted",
            "C-LO_ambient_energy": "whole-domain background dominated; inside 100 kpc is an upper bound",
            "radio": "corrected PRAiSE2 full-loss primary; lossless comparator",
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
