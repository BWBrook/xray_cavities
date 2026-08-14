#!/usr/bin/env python3
"""Small, reusable inference functions for per-snapshot jet diagnostics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Sequence

import numpy as np
from scipy.optimize import minimize_scalar


MU0_SI = 4.0e-7 * math.pi
SPEED_OF_LIGHT_M_S = 299_792_458.0
ELECTRON_MASS_KG = 9.109_383_701_5e-31
ELEMENTARY_CHARGE_C = 1.602_176_634e-19
THOMSON_CROSS_SECTION_M2 = 6.652_458_732_1e-29
KPC_M = 3.085_677_581_491_367e19


@dataclass(frozen=True)
class ContinuousInjectionFit:
    alpha_injection: float
    amplitude: float
    fitted_break_ghz: float
    reported_break_ghz: float
    break_status: str
    spectral_age_limit_direction: str
    log_rms: float

    def as_dict(self) -> dict[str, float | str]:
        return asdict(self)


def _positive_finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return value


def cavagnolo_2010_power_w(luminosity_1p4_w_hz: float) -> float:
    """Return the Cavagnolo et al. (2010) 1.4-GHz jet-power estimate."""
    luminosity = _positive_finite(luminosity_1p4_w_hz, "1.4-GHz luminosity")
    return 7.3e36 * (luminosity / 1.0e24) ** 0.70


def kokotanekov_2017_power_w(luminosity_150_w_hz: float) -> float:
    """Return the 150-MHz approximation to the Kokotanekov 148-MHz relation."""
    luminosity = _positive_finite(luminosity_150_w_hz, "150-MHz luminosity")
    return 1.0e35 * 10.0**1.4 * (luminosity / 1.0e24) ** 0.51


def cmb_field_ug(redshift: float) -> float:
    redshift = float(redshift)
    if not math.isfinite(redshift) or redshift < 0:
        raise ValueError("redshift must be finite and non-negative")
    return 3.25 * (1.0 + redshift) ** 2


def maximum_age_field_ug(redshift: float) -> float:
    return cmb_field_ug(redshift) / math.sqrt(3.0)


def model_magnetic_field_ug(
    pressure_pa: float,
    *,
    eta: float = 0.03,
    gamma_c: float = 5.0 / 3.0,
) -> float:
    """Map the PRAiSE pressure/equipartition convention to magnetic field."""
    pressure = _positive_finite(pressure_pa, "pressure")
    eta = _positive_finite(eta, "eta")
    gamma_c = float(gamma_c)
    if not math.isfinite(gamma_c) or gamma_c <= 1:
        raise ValueError("gamma_c must be finite and greater than one")
    magnetic_energy_density = eta * pressure / ((gamma_c - 1.0) * (eta + 1.0))
    return math.sqrt(2.0 * MU0_SI * magnetic_energy_density) * 1.0e10


def equipartition_field_ug_delta(
    luminosity_w_hz: float,
    *,
    frequency_ghz: float,
    volume_kpc3: float,
    alpha_injection: float,
    filling_factor: float = 1.0,
    non_radiating_energy_ratio: float = 0.0,
    gamma_min: float = 500.0,
    gamma_max: float = 1.0e5,
    mean_pitch_sine: float = math.pi / 4.0,
) -> float:
    """Estimate an observer-like equipartition field with a delta kernel.

    The observed monochromatic luminosity normalises an isotropic power-law
    electron population. The returned field minimises particle plus magnetic
    energy in the X-ray cavity volume. The approximation is intentionally
    explicit: it is a reproducible field sensitivity, not a hidden classical
    ``c12`` convention.
    """
    luminosity = _positive_finite(luminosity_w_hz, "luminosity")
    frequency_hz = _positive_finite(frequency_ghz, "frequency") * 1.0e9
    volume_m3 = _positive_finite(volume_kpc3, "volume") * KPC_M**3
    alpha = _positive_finite(alpha_injection, "injection index")
    filling = _positive_finite(filling_factor, "filling factor")
    if filling > 1.0:
        raise ValueError("filling factor cannot exceed one")
    non_radiating = float(non_radiating_energy_ratio)
    if not math.isfinite(non_radiating) or non_radiating < 0.0:
        raise ValueError("non-radiating energy ratio must be finite and non-negative")
    gamma_low = _positive_finite(gamma_min, "gamma_min")
    gamma_high = _positive_finite(gamma_max, "gamma_max")
    if gamma_high <= gamma_low:
        raise ValueError("gamma_max must exceed gamma_min")
    pitch = _positive_finite(mean_pitch_sine, "mean pitch-angle sine")
    if pitch > 1.0:
        raise ValueError("mean pitch-angle sine cannot exceed one")

    electron_index = 2.0 * alpha + 1.0
    synchrotron_frequency_coefficient = (
        3.0 * ELEMENTARY_CHARGE_C * pitch / (4.0 * math.pi * ELECTRON_MASS_KG)
    )
    if math.isclose(electron_index, 2.0, rel_tol=0.0, abs_tol=1.0e-12):
        electron_energy_integral = math.log(gamma_high / gamma_low)
    else:
        electron_energy_integral = (
            gamma_high ** (2.0 - electron_index)
            - gamma_low ** (2.0 - electron_index)
        ) / (2.0 - electron_index)

    def total_energy(log_field_t: float) -> float:
        field_t = math.exp(log_field_t)
        gamma_reference = math.sqrt(
            frequency_hz / (synchrotron_frequency_coefficient * field_t)
        )
        if not gamma_low <= gamma_reference <= gamma_high:
            return math.inf
        luminosity_per_normalisation = (
            filling
            * volume_m3
            * THOMSON_CROSS_SECTION_M2
            * SPEED_OF_LIGHT_M_S
            * field_t
            / (3.0 * MU0_SI * synchrotron_frequency_coefficient)
            * gamma_reference ** (1.0 - electron_index)
        )
        electron_normalisation_m3 = luminosity / luminosity_per_normalisation
        electron_energy_j = (
            filling
            * volume_m3
            * electron_normalisation_m3
            * ELECTRON_MASS_KG
            * SPEED_OF_LIGHT_M_S**2
            * electron_energy_integral
        )
        magnetic_energy_j = filling * volume_m3 * field_t**2 / (2.0 * MU0_SI)
        return (1.0 + non_radiating) * electron_energy_j + magnetic_energy_j

    result = minimize_scalar(
        total_energy,
        bounds=(math.log(1.0e-12), math.log(1.0e-7)),
        method="bounded",
        options={"xatol": 1.0e-12},
    )
    if not result.success or not math.isfinite(float(result.fun)):
        raise ValueError("equipartition-field minimisation did not converge")
    return math.exp(float(result.x)) * 1.0e10


def spectral_age_myr(break_ghz: float, field_ug: float, *, redshift: float = 0.05) -> float:
    break_frequency = _positive_finite(break_ghz, "break frequency")
    field = _positive_finite(field_ug, "magnetic field")
    background = cmb_field_ug(redshift)
    return (
        1590.0
        * math.sqrt(field)
        / (field * field + background * background)
        / math.sqrt((1.0 + redshift) * break_frequency)
    )


def fit_injection_index(
    frequencies_ghz: Sequence[float], lossless_luminosity_w_hz: Sequence[float]
) -> float:
    """Fit the controlled lossless spectrum S_nu proportional to nu^-alpha."""
    frequencies, luminosity = _validated_spectrum(
        frequencies_ghz, lossless_luminosity_w_hz
    )
    slope, _intercept = np.polyfit(np.log(frequencies), np.log(luminosity), 1)
    alpha = -float(slope)
    if not math.isfinite(alpha) or alpha <= 0:
        raise ValueError("lossless spectrum does not define a positive injection index")
    return alpha


def continuous_injection_delta_shape(
    frequencies_ghz: Sequence[float], *, alpha_injection: float, break_ghz: float
) -> np.ndarray:
    """Dimensionless continuous-injection spectrum in the delta-kernel limit.

    This is the time-integrated solution for continuous power-law electron
    injection under quadratic radiative losses. It approaches spectral index
    ``alpha_injection`` below the break and steepens continuously by 0.5.
    """
    frequencies = np.asarray(frequencies_ghz, dtype=float)
    if frequencies.ndim != 1 or frequencies.size < 2:
        raise ValueError("frequencies must contain at least two values")
    if np.any(~np.isfinite(frequencies)) or np.any(frequencies <= 0):
        raise ValueError("frequencies must be finite and positive")
    alpha = _positive_finite(alpha_injection, "injection index")
    break_frequency = _positive_finite(break_ghz, "break frequency")
    electron_index = 2.0 * alpha + 1.0
    x = np.sqrt(frequencies / break_frequency)
    accumulated = np.ones_like(x)
    below = x < 1.0
    accumulated[below] = 1.0 - (1.0 - x[below]) ** (electron_index - 1.0)
    return frequencies ** (-electron_index / 2.0) * accumulated


def fit_continuous_injection_spectrum(
    frequencies_ghz: Sequence[float],
    full_loss_luminosity_w_hz: Sequence[float],
    *,
    alpha_injection: float,
    observed_band_ghz: tuple[float, float] = (0.15, 15.0),
    search_band_ghz: tuple[float, float] = (1.0e-4, 1.0e5),
) -> ContinuousInjectionFit:
    """Fit amplitude and break frequency, then censor out-of-band breaks."""
    frequencies, luminosity = _validated_spectrum(
        frequencies_ghz, full_loss_luminosity_w_hz
    )
    alpha = _positive_finite(alpha_injection, "injection index")
    observed_low, observed_high = map(float, observed_band_ghz)
    search_low, search_high = map(float, search_band_ghz)
    if not (0 < search_low < observed_low < observed_high < search_high):
        raise ValueError("search and observed frequency bands are inconsistent")
    log_luminosity = np.log(luminosity)

    def objective(log_break: float) -> float:
        shape = continuous_injection_delta_shape(
            frequencies, alpha_injection=alpha, break_ghz=math.exp(log_break)
        )
        log_shape = np.log(shape)
        log_amplitude = float(np.mean(log_luminosity - log_shape))
        residual = log_luminosity - (log_amplitude + log_shape)
        return float(np.mean(residual * residual))

    result = minimize_scalar(
        objective,
        bounds=(math.log(search_low), math.log(search_high)),
        method="bounded",
        options={"xatol": 1.0e-10},
    )
    if not result.success or not math.isfinite(float(result.fun)):
        raise ValueError("continuous-injection fit did not converge")
    fitted_break = math.exp(float(result.x))
    shape = continuous_injection_delta_shape(
        frequencies, alpha_injection=alpha, break_ghz=fitted_break
    )
    log_amplitude = float(np.mean(log_luminosity - np.log(shape)))
    amplitude = math.exp(log_amplitude)
    if fitted_break < observed_low:
        reported_break = observed_low
        status = "break_below_observed_band"
        limit_direction = "spectral_age_lower_limit"
    elif fitted_break > observed_high:
        reported_break = observed_high
        status = "break_above_observed_band"
        limit_direction = "spectral_age_upper_limit"
    else:
        reported_break = fitted_break
        status = "break_detected_in_band"
        limit_direction = "none"
    return ContinuousInjectionFit(
        alpha_injection=alpha,
        amplitude=amplitude,
        fitted_break_ghz=fitted_break,
        reported_break_ghz=reported_break,
        break_status=status,
        spectral_age_limit_direction=limit_direction,
        log_rms=math.sqrt(float(result.fun)),
    )


def _validated_spectrum(
    frequencies_ghz: Sequence[float], luminosity_w_hz: Sequence[float]
) -> tuple[np.ndarray, np.ndarray]:
    frequencies = np.asarray(frequencies_ghz, dtype=float)
    luminosity = np.asarray(luminosity_w_hz, dtype=float)
    if frequencies.ndim != 1 or frequencies.size < 3 or luminosity.shape != frequencies.shape:
        raise ValueError("spectrum must contain aligned one-dimensional arrays of at least three points")
    if (
        np.any(~np.isfinite(frequencies))
        or np.any(frequencies <= 0)
        or np.any(np.diff(frequencies) <= 0)
        or np.any(~np.isfinite(luminosity))
        or np.any(luminosity <= 0)
    ):
        raise ValueError("spectrum frequencies and luminosities must be ordered, finite, and positive")
    return frequencies, luminosity
