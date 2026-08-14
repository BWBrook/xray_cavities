from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.snapshot_inference import continuous_injection_delta_shape
from scripts.science.snapshot_synthesis import (
    CAVITY_ENERGY_MODELS,
    RADIO_FREQUENCIES_GHZ,
    RADIO_LOSS_MODELS,
    RADIO_SNAPSHOT_INDICES,
    XRAY_VIEWS,
    build_radio_power_surface,
    build_spectral_cavity_power_surface,
    fit_spectral_surface,
    select_cavity_surface,
    validate_radio_surface,
    validate_radio_view_surface,
)


def radio_rows() -> list[dict[str, object]]:
    rows = []
    frequencies = np.asarray(RADIO_FREQUENCIES_GHZ)
    for index in RADIO_SNAPSHOT_INDICES:
        break_ghz = 6.0 / (index / 10.0)
        for loss_model in RADIO_LOSS_MODELS:
            shape = frequencies**-0.6 if loss_model == "lossless" else continuous_injection_delta_shape(
                frequencies, alpha_injection=0.6, break_ghz=break_ghz
            )
            for frequency, luminosity in zip(frequencies, 2.0e24 * shape, strict=True):
                rows.append(
                    {
                        "case": "G-LO",
                        "snapshot_index": index,
                        "fluid_time_myr": index - 1.0e-4,
                        "particle_output_index": index * 100,
                        "particle_time_myr": index - 2.0e-4,
                        "particle_time_offset_myr": 1.0e-4,
                        "frequency_ghz": frequency,
                        "loss_model": loss_model,
                        "luminosity_w_hz": luminosity,
                        "effective_magnetic_field_ug": 4.5,
                        "method": "corrected_praise2",
                    }
                )
    return rows


def cavity_rows() -> list[dict[str, object]]:
    rows = []
    for index in RADIO_SNAPSHOT_INDICES:
        for view in XRAY_VIEWS:
            for energy_model in CAVITY_ENERGY_MODELS:
                rows.append(
                    {
                        "case": "G-LO",
                        "nominal_age_myr": index,
                        "actual_time_myr": index - 1.0e-4,
                        "view": view,
                        "side": "bipolar_total",
                        "volume_depth_assumption": "geometric_depth",
                        "energy_model": energy_model,
                        "topology_status": "two_separate_components",
                        "volume_kpc3": 5.0e3,
                        "energy_erg": 2.0e58 if energy_model == "2.5pV" else 3.2e58,
                        "quantitative_energy_valid": "true",
                    }
                )
    return rows


def test_radio_surface_rejects_future_particle_information() -> None:
    rows = radio_rows()
    rows[0]["particle_time_myr"] = rows[0]["fluid_time_myr"] + 0.01
    with pytest.raises(ValueError, match="future particle"):
        validate_radio_surface(rows, case="G-LO")


def test_radio_view_surface_requires_each_exact_view() -> None:
    rows = [dict(row) | {"view": view} for view in XRAY_VIEWS for row in radio_rows()]
    validated = validate_radio_view_surface(rows, case="G-LO")
    assert len(validated) == 5 * 3 * 2 * 5
    rows[-1] = dict(rows[0])
    with pytest.raises(ValueError, match="duplicate radio row|radio surface mismatch"):
        validate_radio_view_surface(rows, case="G-LO")


def test_radio_and_cavity_surfaces_are_exact_and_complete() -> None:
    radio = validate_radio_surface(radio_rows(), case="G-LO")
    cavity = select_cavity_surface(cavity_rows(), case="G-LO")
    assert len(radio) == 5 * 2 * 5
    assert len(cavity) == 5 * 3 * 2
    assert len(build_radio_power_surface(radio)) == 5 * 2 * 2


def test_spectral_cavity_power_surface_carries_three_field_treatments() -> None:
    radio = validate_radio_surface(radio_rows(), case="G-LO")
    cavity = select_cavity_surface(cavity_rows(), case="G-LO")
    spectral = fit_spectral_surface(radio)
    power = build_spectral_cavity_power_surface(
        radio_rows=radio,
        cavity_rows=cavity,
        spectral_rows=spectral,
    )
    assert len(spectral) == 5
    assert len(power) == 5 * 3 * 2 * 3
    assert {row["field_treatment"] for row in power} == {
        "observer_delta_equipartition",
        "matched_praise_effective",
        "maximum_age",
    }
    assert all(float(row["inferred_to_known_ratio"]) > 0 for row in power)


def test_invalid_cavity_is_retained_without_quantitative_power() -> None:
    rows = cavity_rows()
    rows[0]["quantitative_energy_valid"] = "false"
    rows[0]["energy_erg"] = 0.0
    rows[0]["volume_kpc3"] = 0.0
    radio = validate_radio_surface(radio_rows(), case="G-LO")
    cavity = select_cavity_surface(rows, case="G-LO")
    power = build_spectral_cavity_power_surface(
        radio_rows=radio,
        cavity_rows=cavity,
        spectral_rows=fit_spectral_surface(radio),
    )
    invalid = [row for row in power if row["snapshot_index"] == 10 and row["view"] == "0deg" and row["cavity_energy_model"] == "2.5pV"]
    assert len(invalid) == 3
    assert {row["status"] for row in invalid} == {"cavity_energy_not_quantitatively_valid"}
    assert all(row["inferred_cavity_power_erg_s"] == "" for row in invalid)
