#!/usr/bin/env python3
"""X-ray-only spherical pressure deprojection and cavity-volume averaging."""

from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from scipy.optimize import lsq_linear
from scipy.stats import qmc


KPC_M = 3.0856775814913673e19
BOLTZMANN_J_K = 1.380649e-23
PROTON_MASS_KG = 1.67262192369e-27
DEFAULT_REGULARIZATION = 1.0e-6
TEMPERATURE_SUPPORT_RELATIVE_FLOOR = 1.0e-12


@dataclass(frozen=True)
class DeprojectedPressure:
    radial_edges_kpc: np.ndarray
    radial_centres_kpc: np.ndarray
    density_rms_kg_m3: np.ndarray
    temperature_k: np.ndarray
    temperature_direct_shell_mask: np.ndarray
    temperature_support_relative_floor: float
    pressure_dyn_cm2: np.ndarray
    annular_emission_measure_kg2_m5: np.ndarray
    annular_corrected_xray_mjy_sr: np.ndarray
    annular_temperature_numerator_mjy_k_sr: np.ndarray
    annular_pixel_counts: np.ndarray
    annular_unmasked_fractions: np.ndarray
    emission_measure_relative_residual: float
    corrected_xray_relative_residual: float
    temperature_numerator_relative_residual: float


def widths_from_centres(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or values.size < 2 or np.any(np.diff(values) <= 0.0):
        raise ValueError("coordinate centres must be a strictly increasing one-dimensional array")
    edges = np.empty(values.size + 1, dtype=float)
    edges[1:-1] = 0.5 * (values[:-1] + values[1:])
    edges[0] = values[0] - (edges[1] - values[0])
    edges[-1] = values[-1] + (values[-1] - edges[-2])
    return np.diff(edges)


def annular_means(
    values: np.ndarray,
    horizontal_kpc: np.ndarray,
    vertical_kpc: np.ndarray,
    radial_edges_kpc: np.ndarray,
    *,
    exclude_mask: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return area-weighted annular means after an optional X-ray-only exclusion."""

    data = np.asarray(values, dtype=float)
    horizontal = np.asarray(horizontal_kpc, dtype=float)
    vertical = np.asarray(vertical_kpc, dtype=float)
    radial_edges = np.asarray(radial_edges_kpc, dtype=float)
    expected_shape = (vertical.size, horizontal.size)
    if data.shape != expected_shape:
        raise ValueError("map shape does not match supplied axes")
    if radial_edges.ndim != 1 or radial_edges.size < 2 or np.any(np.diff(radial_edges) <= 0.0):
        raise ValueError("radial edges must be strictly increasing")
    excluded = np.zeros(expected_shape, dtype=bool) if exclude_mask is None else np.asarray(exclude_mask, dtype=bool)
    if excluded.shape != expected_shape:
        raise ValueError("exclude mask shape does not match map")

    xx, zz = np.meshgrid(horizontal, vertical)
    radius = np.hypot(xx, zz)
    area = widths_from_centres(vertical)[:, np.newaxis] * widths_from_centres(horizontal)[np.newaxis, :]
    means = np.empty(radial_edges.size - 1, dtype=float)
    counts = np.empty(radial_edges.size - 1, dtype=int)
    fractions = np.empty(radial_edges.size - 1, dtype=float)
    for index, (low, high) in enumerate(zip(radial_edges[:-1], radial_edges[1:], strict=True)):
        annulus = (radius >= low) & (radius < high)
        valid = annulus & ~excluded & np.isfinite(data)
        counts[index] = int(np.count_nonzero(valid))
        total_area = float(np.sum(area[annulus]))
        valid_area = float(np.sum(area[valid]))
        fractions[index] = valid_area / total_area if total_area > 0.0 else 0.0
        if valid_area <= 0.0:
            raise ValueError(f"annulus {low:g}-{high:g} kpc has no valid unmasked area")
        means[index] = float(np.sum(data[valid] * area[valid]) / valid_area)
    return means, counts, fractions


def _radial_chord_integral(radius: float, low: float, high: float) -> float:
    """Return integral_low^high R sqrt(radius^2-R^2)_+ dR."""

    low_term = max(radius * radius - low * low, 0.0) ** 1.5
    high_term = max(radius * radius - high * high, 0.0) ** 1.5
    return (low_term - high_term) / 3.0


def spherical_shell_path_matrix(radial_edges_kpc: np.ndarray) -> np.ndarray:
    """Area-average spherical shell chord lengths through matching annuli."""

    edges = np.asarray(radial_edges_kpc, dtype=float)
    if edges.ndim != 1 or edges.size < 2 or edges[0] < 0.0 or np.any(np.diff(edges) <= 0.0):
        raise ValueError("radial edges must be non-negative and strictly increasing")
    count = edges.size - 1
    matrix = np.zeros((count, count), dtype=float)
    for annulus_index, (projected_low, projected_high) in enumerate(
        zip(edges[:-1], edges[1:], strict=True)
    ):
        projected_area_factor = projected_high**2 - projected_low**2
        for shell_index, (shell_low, shell_high) in enumerate(zip(edges[:-1], edges[1:], strict=True)):
            outer = _radial_chord_integral(shell_high, projected_low, projected_high)
            inner = _radial_chord_integral(shell_low, projected_low, projected_high)
            matrix[annulus_index, shell_index] = 4.0 * (outer - inner) / projected_area_factor
    return matrix * KPC_M


def nonnegative_deproject(
    path_matrix_m: np.ndarray,
    projected_values: np.ndarray,
    *,
    regularization: float = DEFAULT_REGULARIZATION,
) -> tuple[np.ndarray, float]:
    """Solve a lightly regularized non-negative spherical onion inversion."""

    matrix = np.asarray(path_matrix_m, dtype=float)
    projected = np.asarray(projected_values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != projected.size or matrix.shape[1] < 1:
        raise ValueError("path matrix and projected profile shapes are incompatible")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(projected)) or np.any(projected < 0.0):
        raise ValueError("deprojection inputs must be finite and non-negative")
    if regularization < 0.0 or not math.isfinite(regularization):
        raise ValueError("regularization must be finite and non-negative")
    matrix_scale = float(np.max(matrix))
    projected_scale = float(np.max(projected))
    if matrix_scale <= 0.0 or projected_scale <= 0.0:
        raise ValueError("deprojection requires positive path lengths and projected signal")
    scaled_matrix = matrix / matrix_scale
    scaled_projected = projected / projected_scale
    if regularization > 0.0 and matrix.shape[1] > 1:
        difference = np.diff(np.eye(matrix.shape[1]), axis=0)
        design = np.vstack([scaled_matrix, math.sqrt(regularization) * difference])
        response = np.concatenate([scaled_projected, np.zeros(difference.shape[0])])
    else:
        design = scaled_matrix
        response = scaled_projected
    fit = lsq_linear(design, response, bounds=(0.0, np.inf), method="trf", lsmr_tol="auto")
    if not fit.success:
        raise ValueError(f"non-negative deprojection failed: {fit.message}")
    shell_values = fit.x * projected_scale / matrix_scale
    model = matrix @ shell_values
    residual = float(np.linalg.norm(model - projected) / np.linalg.norm(projected))
    return shell_values, residual


def stabilize_deprojected_temperature(
    temperature_emissivity: np.ndarray,
    emissivity: np.ndarray,
    radial_centres_kpc: np.ndarray,
    *,
    support_relative_floor: float = TEMPERATURE_SUPPORT_RELATIVE_FLOOR,
) -> tuple[np.ndarray, np.ndarray]:
    """Interpolate shells where independent inversions have no shared support."""

    numerator = np.asarray(temperature_emissivity, dtype=float)
    denominator = np.asarray(emissivity, dtype=float)
    centres = np.asarray(radial_centres_kpc, dtype=float)
    if numerator.shape != denominator.shape or numerator.shape != centres.shape:
        raise ValueError("temperature numerator, emissivity, and radial centres must align")
    if (
        not math.isfinite(support_relative_floor)
        or support_relative_floor <= 0.0
        or support_relative_floor >= 1.0
    ):
        raise ValueError("temperature support floor must lie strictly between zero and one")
    numerator_scale = float(np.max(numerator))
    denominator_scale = float(np.max(denominator))
    if numerator_scale <= 0.0 or denominator_scale <= 0.0:
        raise ValueError("temperature inversion requires positive numerator and emissivity")
    direct = (
        np.isfinite(numerator)
        & np.isfinite(denominator)
        & (numerator > numerator_scale * support_relative_floor)
        & (denominator > denominator_scale * support_relative_floor)
    )
    if np.count_nonzero(direct) < 2:
        raise ValueError("deprojected temperature has fewer than two directly supported shells")
    temperature = np.divide(
        numerator,
        denominator,
        out=np.full_like(numerator, np.nan),
        where=direct,
    )
    temperature = np.interp(centres, centres[direct], temperature[direct])
    if np.any(~np.isfinite(temperature)) or np.any(temperature <= 0.0):
        raise ValueError("stabilized deprojected temperature is not finite and positive")
    return temperature, direct


def deproject_pressure(
    *,
    emission_measure_rho2_kg2_m5: np.ndarray,
    corrected_xray_mjy_sr: np.ndarray,
    corrected_temperature_numerator_mjy_k_sr: np.ndarray,
    horizontal_kpc: np.ndarray,
    vertical_kpc: np.ndarray,
    radial_edges_kpc: np.ndarray,
    cavity_mask: np.ndarray,
    effective_mean_molecular_weight: float,
    regularization: float = DEFAULT_REGULARIZATION,
    temperature_support_relative_floor: float = TEMPERATURE_SUPPORT_RELATIVE_FLOOR,
) -> DeprojectedPressure:
    """Infer a spherical ambient pressure profile using X-ray products only."""

    if not math.isfinite(effective_mean_molecular_weight) or effective_mean_molecular_weight <= 0.0:
        raise ValueError("effective mean molecular weight must be finite and positive")
    profiles = []
    counts = fractions = None
    for values in (
        emission_measure_rho2_kg2_m5,
        corrected_xray_mjy_sr,
        corrected_temperature_numerator_mjy_k_sr,
    ):
        profile, current_counts, current_fractions = annular_means(
            values,
            horizontal_kpc,
            vertical_kpc,
            radial_edges_kpc,
            exclude_mask=cavity_mask,
        )
        profiles.append(profile)
        if counts is None:
            counts, fractions = current_counts, current_fractions
    path_matrix = spherical_shell_path_matrix(radial_edges_kpc)
    rho2, rho2_residual = nonnegative_deproject(path_matrix, profiles[0], regularization=regularization)
    emissivity, emissivity_residual = nonnegative_deproject(
        path_matrix, profiles[1], regularization=regularization
    )
    temperature_emissivity, temperature_residual = nonnegative_deproject(
        path_matrix, profiles[2], regularization=regularization
    )
    centres = 0.5 * (np.asarray(radial_edges_kpc[:-1]) + np.asarray(radial_edges_kpc[1:]))
    temperature, direct_temperature = stabilize_deprojected_temperature(
        temperature_emissivity,
        emissivity,
        centres,
        support_relative_floor=temperature_support_relative_floor,
    )
    density = np.sqrt(np.maximum(rho2, 0.0))
    pressure_pa = (
        density
        * BOLTZMANN_J_K
        * temperature
        / (effective_mean_molecular_weight * PROTON_MASS_KG)
    )
    if np.any(~np.isfinite(pressure_pa)) or np.any(pressure_pa <= 0.0):
        raise ValueError("deprojected pressure is not finite and positive in every shell")
    assert counts is not None and fractions is not None
    return DeprojectedPressure(
        radial_edges_kpc=np.asarray(radial_edges_kpc, dtype=float),
        radial_centres_kpc=centres,
        density_rms_kg_m3=density,
        temperature_k=temperature,
        temperature_direct_shell_mask=direct_temperature,
        temperature_support_relative_floor=temperature_support_relative_floor,
        pressure_dyn_cm2=pressure_pa * 10.0,
        annular_emission_measure_kg2_m5=profiles[0],
        annular_corrected_xray_mjy_sr=profiles[1],
        annular_temperature_numerator_mjy_k_sr=profiles[2],
        annular_pixel_counts=counts,
        annular_unmasked_fractions=fractions,
        emission_measure_relative_residual=rho2_residual,
        corrected_xray_relative_residual=emissivity_residual,
        temperature_numerator_relative_residual=temperature_residual,
    )


def component_orientation_rad(
    mask: np.ndarray,
    horizontal_kpc: np.ndarray,
    vertical_kpc: np.ndarray,
) -> float:
    """Return the projected major-axis angle from an area-weighted mask covariance."""

    selected = np.asarray(mask, dtype=bool)
    horizontal = np.asarray(horizontal_kpc, dtype=float)
    vertical = np.asarray(vertical_kpc, dtype=float)
    if selected.shape != (vertical.size, horizontal.size) or np.count_nonzero(selected) < 2:
        raise ValueError("component mask is incompatible with axes or too small")
    xx, zz = np.meshgrid(horizontal, vertical)
    area = widths_from_centres(vertical)[:, np.newaxis] * widths_from_centres(horizontal)[np.newaxis, :]
    weights = area[selected]
    x_values = xx[selected]
    z_values = zz[selected]
    centroid = np.array([np.average(x_values, weights=weights), np.average(z_values, weights=weights)])
    centered = np.column_stack([x_values - centroid[0], z_values - centroid[1]])
    covariance = (centered * weights[:, np.newaxis]).T @ centered / np.sum(weights)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    major_vector = eigenvectors[:, int(np.argmax(eigenvalues))]
    return float(math.atan2(major_vector[1], major_vector[0]))


def pressure_at_radius(
    radius_kpc: np.ndarray | float,
    radial_centres_kpc: np.ndarray,
    pressure_dyn_cm2: np.ndarray,
) -> np.ndarray:
    return np.interp(
        np.asarray(radius_kpc, dtype=float),
        np.asarray(radial_centres_kpc, dtype=float),
        np.asarray(pressure_dyn_cm2, dtype=float),
    )


def ellipsoid_average_pressure(
    *,
    centroid_horizontal_kpc: float,
    centroid_vertical_kpc: float,
    major_semiaxis_kpc: float,
    minor_semiaxis_kpc: float,
    los_semiaxis_kpc: float,
    orientation_rad: float,
    radial_centres_kpc: np.ndarray,
    pressure_dyn_cm2: np.ndarray,
    sobol_power: int = 13,
) -> float:
    """Deterministically integrate a spherical pressure profile over an ellipsoid."""

    dimensions = (major_semiaxis_kpc, minor_semiaxis_kpc, los_semiaxis_kpc)
    if any(not math.isfinite(value) or value <= 0.0 for value in dimensions):
        raise ValueError("ellipsoid semiaxes must be finite and positive")
    if sobol_power < 8:
        raise ValueError("sobol_power must be at least 8")
    unit = qmc.Sobol(d=3, scramble=False).random_base2(sobol_power)
    radius = np.cbrt(unit[:, 0])
    cos_polar = 2.0 * unit[:, 1] - 1.0
    sin_polar = np.sqrt(np.maximum(1.0 - cos_polar * cos_polar, 0.0))
    azimuth = 2.0 * np.pi * unit[:, 2]
    major_coord = major_semiaxis_kpc * radius * sin_polar * np.cos(azimuth)
    minor_coord = minor_semiaxis_kpc * radius * sin_polar * np.sin(azimuth)
    los_coord = los_semiaxis_kpc * radius * cos_polar
    cosine = math.cos(orientation_rad)
    sine = math.sin(orientation_rad)
    horizontal = centroid_horizontal_kpc + cosine * major_coord - sine * minor_coord
    vertical = centroid_vertical_kpc + sine * major_coord + cosine * minor_coord
    spherical_radius = np.sqrt(horizontal * horizontal + vertical * vertical + los_coord * los_coord)
    sampled_pressure = pressure_at_radius(spherical_radius, radial_centres_kpc, pressure_dyn_cm2)
    if np.any(~np.isfinite(sampled_pressure)) or np.any(sampled_pressure <= 0.0):
        raise ValueError("ellipsoid pressure sample contains non-positive values")
    return float(np.mean(sampled_pressure))
