import math
from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.snapshot_inference import (
    cavagnolo_2010_power_w,
    cmb_field_ug,
    continuous_injection_delta_shape,
    equipartition_field_ug_delta,
    fit_continuous_injection_spectrum,
    fit_injection_index,
    kokotanekov_2017_power_w,
    maximum_age_field_ug,
    model_magnetic_field_ug,
    spectral_age_myr,
)


FREQUENCIES = np.asarray([0.15, 0.5, 1.4, 4.5, 15.0])


def test_published_radio_power_relations_recover_their_normalisations() -> None:
    assert cavagnolo_2010_power_w(1.0e24) == pytest.approx(7.3e36)
    assert kokotanekov_2017_power_w(1.0e24) == pytest.approx(1.0e35 * 10**1.4)
    with pytest.raises(ValueError):
        cavagnolo_2010_power_w(0)


def test_magnetic_field_and_spectral_age_contract() -> None:
    assert cmb_field_ug(0.05) == pytest.approx(3.25 * 1.05**2)
    assert maximum_age_field_ug(0.05) == pytest.approx(cmb_field_ug(0.05) / math.sqrt(3))
    assert model_magnetic_field_ug(1.0e-12) > 0
    assert spectral_age_myr(1.4, 5.0, redshift=0.05) > 0


def test_delta_equipartition_field_is_positive_and_has_expected_scaling() -> None:
    field = equipartition_field_ug_delta(
        1.0e24,
        frequency_ghz=1.4,
        volume_kpc3=5.0e3,
        alpha_injection=0.6,
    )
    brighter = equipartition_field_ug_delta(
        4.0e24,
        frequency_ghz=1.4,
        volume_kpc3=5.0e3,
        alpha_injection=0.6,
    )
    larger = equipartition_field_ug_delta(
        1.0e24,
        frequency_ghz=1.4,
        volume_kpc3=2.0e4,
        alpha_injection=0.6,
    )
    assert 0.01 < field < 1.0e3
    assert brighter > field
    assert larger < field


def test_delta_equipartition_field_rejects_unphysical_assumptions() -> None:
    with pytest.raises(ValueError):
        equipartition_field_ug_delta(
            1.0e24,
            frequency_ghz=1.4,
            volume_kpc3=5.0e3,
            alpha_injection=0.6,
            filling_factor=1.1,
        )


def test_lossless_spectrum_recovers_injection_index() -> None:
    luminosity = 2.5e25 * FREQUENCIES**-0.6
    assert fit_injection_index(FREQUENCIES, luminosity) == pytest.approx(0.6)


def test_continuous_injection_fit_recovers_an_in_band_break() -> None:
    shape = continuous_injection_delta_shape(
        FREQUENCIES, alpha_injection=0.6, break_ghz=2.0
    )
    fit = fit_continuous_injection_spectrum(
        FREQUENCIES, 3.0e25 * shape, alpha_injection=0.6
    )
    assert fit.break_status == "break_detected_in_band"
    assert fit.fitted_break_ghz == pytest.approx(2.0, rel=1e-5)
    assert fit.log_rms < 1e-8


@pytest.mark.parametrize(
    ("break_ghz", "expected_status", "expected_limit"),
    [
        (0.01, "break_below_observed_band", "spectral_age_lower_limit"),
        (100.0, "break_above_observed_band", "spectral_age_upper_limit"),
    ],
)
def test_continuous_injection_fit_censors_out_of_band_breaks(
    break_ghz: float, expected_status: str, expected_limit: str
) -> None:
    shape = continuous_injection_delta_shape(
        FREQUENCIES, alpha_injection=0.6, break_ghz=break_ghz
    )
    fit = fit_continuous_injection_spectrum(
        FREQUENCIES, 1.0e25 * shape, alpha_injection=0.6
    )
    assert fit.break_status == expected_status
    assert fit.spectral_age_limit_direction == expected_limit
