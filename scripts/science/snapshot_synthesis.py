#!/usr/bin/env python3
"""Reusable radio, cavity, and spectral-age synthesis for snapshot science."""

from __future__ import annotations

import math
from itertools import product
from typing import Any, Mapping, Sequence

import numpy as np

from scripts.science.snapshot_inference import (
    cavagnolo_2010_power_w,
    equipartition_field_ug_delta,
    fit_continuous_injection_spectrum,
    fit_injection_index,
    kokotanekov_2017_power_w,
    maximum_age_field_ug,
    spectral_age_myr,
)


SECONDS_PER_MYR = 3.15576e13
SNAPSHOT_INDICES = (0, 10, 20, 30, 40, 50)
RADIO_SNAPSHOT_INDICES = SNAPSHOT_INDICES[1:]
RADIO_FREQUENCIES_GHZ = (0.15, 0.5, 1.4, 4.5, 15.0)
RADIO_LOSS_MODELS = ("lossless", "full_loss")
XRAY_VIEWS = ("0deg", "45deg", "90deg")
CAVITY_ENERGY_MODELS = ("2.5pV", "4pV")
FIELD_TREATMENTS = ("observer_delta_equipartition", "matched_praise_effective", "maximum_age")
KNOWN_BIPOLAR_POWER_ERG_S = 2.0e43
SPECTRAL_MODEL = "continuous_injection_delta_kernel"


def _float(row: Mapping[str, Any], field: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"missing or invalid {field}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite {field}")
    return value


def _int(row: Mapping[str, Any], field: str) -> int:
    value = _float(row, field)
    integer = int(value)
    if value != integer:
        raise ValueError(f"non-integer {field}")
    return integer


def _bool(row: Mapping[str, Any], field: str) -> bool:
    value = str(row.get(field, "")).strip().lower()
    if value not in {"true", "false"}:
        raise ValueError(f"invalid Boolean {field}")
    return value == "true"


def validate_radio_surface(
    rows: Sequence[Mapping[str, Any]], *, case: str
) -> list[dict[str, Any]]:
    """Validate the exact five-age, five-frequency corrected-PRAiSE2 surface."""
    normalized: list[dict[str, Any]] = []
    seen: set[tuple[int, str, float]] = set()
    for row in rows:
        if row.get("case") != case:
            raise ValueError(f"radio surface contains a non-{case} row")
        index = _int(row, "snapshot_index")
        loss_model = str(row.get("loss_model", ""))
        frequency = _float(row, "frequency_ghz")
        key = (index, loss_model, frequency)
        if key in seen:
            raise ValueError(f"duplicate radio row: {key}")
        seen.add(key)
        fluid_time = _float(row, "fluid_time_myr")
        particle_time = _float(row, "particle_time_myr")
        offset = _float(row, "particle_time_offset_myr")
        if particle_time > fluid_time + 1.0e-9:
            raise ValueError(f"future particle information used at snapshot {index}")
        if not math.isclose(fluid_time - particle_time, offset, rel_tol=0.0, abs_tol=1.0e-8):
            raise ValueError(f"particle time offset drift at snapshot {index}")
        luminosity = _float(row, "luminosity_w_hz")
        effective_field = _float(row, "effective_magnetic_field_ug")
        if luminosity <= 0.0 or effective_field <= 0.0:
            raise ValueError("radio luminosity and effective field must be positive")
        normalized.append(
            dict(row)
            | {
                "snapshot_index": index,
                "frequency_ghz": frequency,
                "fluid_time_myr": fluid_time,
                "particle_time_myr": particle_time,
                "particle_time_offset_myr": offset,
                "luminosity_w_hz": luminosity,
                "effective_magnetic_field_ug": effective_field,
            }
        )
    expected = set(product(RADIO_SNAPSHOT_INDICES, RADIO_LOSS_MODELS, RADIO_FREQUENCIES_GHZ))
    if seen != expected:
        missing = sorted(expected - seen)
        extra = sorted(seen - expected)
        raise ValueError(f"radio surface mismatch: missing={missing} extra={extra}")
    for index, loss_model in product(RADIO_SNAPSHOT_INDICES, RADIO_LOSS_MODELS):
        group = [row for row in normalized if row["snapshot_index"] == index and row["loss_model"] == loss_model]
        times = {row["fluid_time_myr"] for row in group}
        fields = np.asarray([row["effective_magnetic_field_ug"] for row in group])
        if len(times) != 1 or not np.allclose(fields, fields[0], rtol=1.0e-10, atol=0.0):
            raise ValueError(f"radio time or effective-field drift at {index}/{loss_model}")
    return sorted(normalized, key=lambda row: (row["snapshot_index"], row["loss_model"], row["frequency_ghz"]))


def validate_radio_view_surface(
    rows: Sequence[Mapping[str, Any]], *, case: str
) -> list[dict[str, Any]]:
    """Validate the exact three-view radio surface using the primary contract."""
    grouped: dict[str, list[Mapping[str, Any]]] = {view: [] for view in XRAY_VIEWS}
    for row in rows:
        view = str(row.get("view", ""))
        if view not in grouped:
            raise ValueError(f"invalid radio view: {view}")
        grouped[view].append(row)

    normalized: list[dict[str, Any]] = []
    for view in XRAY_VIEWS:
        validated = validate_radio_surface(grouped[view], case=case)
        normalized.extend(dict(row) | {"view": view} for row in validated)
    return sorted(
        normalized,
        key=lambda row: (
            row["snapshot_index"],
            row["view"],
            row["loss_model"],
            row["frequency_ghz"],
        ),
    )


def select_cavity_surface(
    rows: Sequence[Mapping[str, Any]], *, case: str
) -> list[dict[str, Any]]:
    """Select the accepted geometric-depth bipolar cavity rows."""
    selected: list[dict[str, Any]] = []
    seen: set[tuple[int, str, str]] = set()
    for row in rows:
        if (
            row.get("case") != case
            or row.get("side") != "bipolar_total"
            or row.get("volume_depth_assumption") != "geometric_depth"
            or row.get("view") not in XRAY_VIEWS
            or row.get("energy_model") not in CAVITY_ENERGY_MODELS
        ):
            continue
        index = _int(row, "nominal_age_myr")
        key = (index, str(row["view"]), str(row["energy_model"]))
        if key in seen:
            raise ValueError(f"duplicate cavity row: {key}")
        seen.add(key)
        selected.append(
            dict(row)
            | {
                "nominal_age_myr": index,
                "actual_time_myr": _float(row, "actual_time_myr"),
                "volume_kpc3": _float(row, "volume_kpc3"),
                "energy_erg": _float(row, "energy_erg"),
                "quantitative_energy_valid": _bool(row, "quantitative_energy_valid"),
            }
        )
    expected = set(product(RADIO_SNAPSHOT_INDICES, XRAY_VIEWS, CAVITY_ENERGY_MODELS))
    if seen != expected:
        raise ValueError(f"cavity surface mismatch: missing={sorted(expected - seen)}")
    return sorted(selected, key=lambda row: (row["nominal_age_myr"], row["view"], row["energy_model"]))


def build_radio_power_surface(
    radio_rows: Sequence[Mapping[str, Any]], *, known_bipolar_power_erg_s: float = KNOWN_BIPOLAR_POWER_ERG_S
) -> list[dict[str, Any]]:
    known_power = float(known_bipolar_power_erg_s)
    if not math.isfinite(known_power) or known_power <= 0.0:
        raise ValueError("known bipolar power must be finite and positive")
    relations = (
        ("kokotanekov_2017_150mhz_approx", 0.15, 0.85, kokotanekov_2017_power_w),
        ("cavagnolo_2010_1p4ghz", 1.4, 0.70, cavagnolo_2010_power_w),
    )
    output: list[dict[str, Any]] = []
    lookup = {
        (int(row["snapshot_index"]), str(row["loss_model"]), float(row["frequency_ghz"])): row
        for row in radio_rows
    }
    for index, loss_model, relation in product(RADIO_SNAPSHOT_INDICES, RADIO_LOSS_MODELS, relations):
        relation_name, frequency, scatter_dex, function = relation
        source = lookup[(index, loss_model, frequency)]
        inferred_w = function(float(source["luminosity_w_hz"]))
        inferred_erg_s = inferred_w * 1.0e7
        factor = 10.0**scatter_dex
        output.append(
            {
                "case": source["case"],
                "snapshot_index": index,
                "actual_time_myr": source["fluid_time_myr"],
                "loss_model": loss_model,
                "relation": relation_name,
                "frequency_ghz": frequency,
                "luminosity_w_hz": source["luminosity_w_hz"],
                "intrinsic_scatter_dex": scatter_dex,
                "inferred_power_erg_s": inferred_erg_s,
                "inferred_power_lower_erg_s": inferred_erg_s / factor,
                "inferred_power_upper_erg_s": inferred_erg_s * factor,
                "known_bipolar_power_erg_s": known_power,
                "inferred_to_known_ratio": inferred_erg_s / known_power,
            }
        )
    return output


def fit_spectral_surface(radio_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for index in RADIO_SNAPSHOT_INDICES:
        lossless = [row for row in radio_rows if row["snapshot_index"] == index and row["loss_model"] == "lossless"]
        full_loss = [row for row in radio_rows if row["snapshot_index"] == index and row["loss_model"] == "full_loss"]
        frequencies = np.asarray([row["frequency_ghz"] for row in lossless], dtype=float)
        alpha = fit_injection_index(frequencies, [row["luminosity_w_hz"] for row in lossless])
        fit = fit_continuous_injection_spectrum(
            frequencies,
            [row["luminosity_w_hz"] for row in full_loss],
            alpha_injection=alpha,
        )
        output.append(
            {
                "case": lossless[0]["case"],
                "snapshot_index": index,
                "actual_time_myr": lossless[0]["fluid_time_myr"],
                "spectral_model": SPECTRAL_MODEL,
                **fit.as_dict(),
            }
        )
    return output


def build_spectral_cavity_power_surface(
    *,
    radio_rows: Sequence[Mapping[str, Any]],
    cavity_rows: Sequence[Mapping[str, Any]],
    spectral_rows: Sequence[Mapping[str, Any]],
    redshift: float = 0.05,
    known_bipolar_power_erg_s: float = KNOWN_BIPOLAR_POWER_ERG_S,
) -> list[dict[str, Any]]:
    spectral = {int(row["snapshot_index"]): row for row in spectral_rows}
    radio = {
        (int(row["snapshot_index"]), str(row["loss_model"]), float(row["frequency_ghz"])): row
        for row in radio_rows
    }
    output: list[dict[str, Any]] = []
    for cavity in cavity_rows:
        index = int(cavity["nominal_age_myr"])
        fit = spectral[index]
        radio_1p4 = radio[(index, "full_loss", 1.4)]
        valid = bool(cavity["quantitative_energy_valid"]) and float(cavity["energy_erg"]) > 0.0 and float(cavity["volume_kpc3"]) > 0.0
        if valid:
            fields = {
                "observer_delta_equipartition": equipartition_field_ug_delta(
                    float(radio_1p4["luminosity_w_hz"]),
                    frequency_ghz=1.4,
                    volume_kpc3=float(cavity["volume_kpc3"]),
                    alpha_injection=float(fit["alpha_injection"]),
                ),
                "matched_praise_effective": float(radio_1p4["effective_magnetic_field_ug"]),
                "maximum_age": maximum_age_field_ug(redshift),
            }
        else:
            fields = {name: None for name in FIELD_TREATMENTS}
        for treatment, field in fields.items():
            if field is None:
                age = power = ratio = true_age_ratio = ""
                status = "cavity_energy_not_quantitatively_valid"
            else:
                age = spectral_age_myr(float(fit["reported_break_ghz"]), field, redshift=redshift)
                power = float(cavity["energy_erg"]) / (age * SECONDS_PER_MYR)
                ratio = power / known_bipolar_power_erg_s
                true_age_ratio = age / float(cavity["actual_time_myr"])
                status = "quantitative_with_spectral_censoring_carried" if fit["spectral_age_limit_direction"] != "none" else "quantitative"
            output.append(
                {
                    "case": cavity["case"],
                    "snapshot_index": index,
                    "actual_time_myr": cavity["actual_time_myr"],
                    "view": cavity["view"],
                    "topology_status": cavity["topology_status"],
                    "cavity_energy_model": cavity["energy_model"],
                    "cavity_energy_erg": cavity["energy_erg"],
                    "cavity_volume_kpc3": cavity["volume_kpc3"],
                    "quantitative_energy_valid": cavity["quantitative_energy_valid"],
                    "spectral_model": fit["spectral_model"],
                    "break_status": fit["break_status"],
                    "spectral_age_limit_direction": fit["spectral_age_limit_direction"],
                    "reported_break_ghz": fit["reported_break_ghz"],
                    "field_treatment": treatment,
                    "magnetic_field_ug": field if field is not None else "",
                    "spectral_age_myr": age,
                    "spectral_to_true_age_ratio": true_age_ratio,
                    "inferred_cavity_power_erg_s": power,
                    "known_bipolar_power_erg_s": known_bipolar_power_erg_s,
                    "inferred_to_known_ratio": ratio,
                    "status": status,
                }
            )
    return output


def method_contract(*, known_bipolar_power_erg_s: float = KNOWN_BIPOLAR_POWER_ERG_S) -> dict[str, Any]:
    known_power = float(known_bipolar_power_erg_s)
    if not math.isfinite(known_power) or known_power <= 0.0:
        raise ValueError("known bipolar power must be finite and positive")
    return {
        "snapshot_indices": list(SNAPSHOT_INDICES),
        "radio_snapshot_indices": list(RADIO_SNAPSHOT_INDICES),
        "radio_frequencies_ghz": list(RADIO_FREQUENCIES_GHZ),
        "radio_primary": "corrected PRAiSE2 full-loss",
        "radio_control": "corrected PRAiSE2 lossless",
        "spectral_model": SPECTRAL_MODEL,
        "equipartition_method": "minimum particle-plus-field energy under isotropic delta-kernel power-law electrons",
        "equipartition_assumptions": {
            "filling_factor": 1.0,
            "non_radiating_energy_ratio": 0.0,
            "gamma_min": 500.0,
            "gamma_max": 1.0e5,
            "mean_pitch_sine": math.pi / 4.0,
        },
        "xray_primary_depth": "geometric_depth",
        "cavity_energy_models": list(CAVITY_ENERGY_MODELS),
        "known_power_convention": f"bipolar {known_power:.12g} erg/s",
        "cross_case_claims": False,
    }
