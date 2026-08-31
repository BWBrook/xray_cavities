from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/xray_pressure_deprojection.py")


def load_module():
    spec = importlib.util.spec_from_file_location("xray_pressure_deprojection", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_spherical_path_matrix_recovers_exact_positive_shell_profile() -> None:
    module = load_module()
    edges = np.array([0.0, 10.0, 20.0, 30.0])
    matrix = module.spherical_shell_path_matrix(edges)
    truth = np.array([4.0, 2.0, 1.0]) * 1.0e-48
    projected = matrix @ truth

    recovered, residual = module.nonnegative_deproject(
        matrix,
        projected,
        regularization=0.0,
    )

    np.testing.assert_allclose(recovered, truth, rtol=1.0e-8)
    assert residual < 1.0e-10


def test_annular_means_exclude_only_requested_pixels() -> None:
    module = load_module()
    axis = np.array([-1.5, -0.5, 0.5, 1.5])
    values = np.ones((4, 4), dtype=float)
    values[1, 1] = 100.0
    mask = np.zeros_like(values, dtype=bool)
    mask[1, 1] = True

    means, counts, fractions = module.annular_means(
        values,
        axis,
        axis,
        np.array([0.0, 1.0, 2.5]),
        exclude_mask=mask,
    )

    np.testing.assert_allclose(means, [1.0, 1.0])
    assert counts.tolist() == [3, 12]
    assert fractions[0] == pytest.approx(0.75)
    assert fractions[1] == pytest.approx(1.0)


def test_pressure_deprojection_recovers_synthetic_constant_temperature_profile() -> None:
    module = load_module()
    radial_edges = np.arange(0.0, 51.0, 10.0)
    matrix = module.spherical_shell_path_matrix(radial_edges)
    rho = np.array([5.0, 4.0, 3.0, 2.0, 1.0]) * 1.0e-24
    temperature = 2.0e7
    emissivity = np.array([5.0, 4.0, 3.0, 2.0, 1.0]) * 1.0e-13
    emission_measure_profile = matrix @ np.square(rho)
    corrected_profile = matrix @ emissivity
    temperature_profile = corrected_profile * temperature

    axis = np.arange(-49.5, 50.0, 1.0)
    xx, zz = np.meshgrid(axis, axis)
    radius = np.hypot(xx, zz)
    shell_index = np.clip(np.searchsorted(radial_edges, radius, side="right") - 1, 0, 4)
    in_domain = radius < radial_edges[-1]
    maps = []
    for profile in (emission_measure_profile, corrected_profile, temperature_profile):
        values = np.zeros_like(radius)
        values[in_domain] = profile[shell_index[in_domain]]
        maps.append(values)
    # Use the same piecewise-constant annular values that the deprojection consumes.
    result = module.deproject_pressure(
        emission_measure_rho2_kg2_m5=maps[0],
        corrected_xray_mjy_sr=maps[1],
        corrected_temperature_numerator_mjy_k_sr=maps[2],
        horizontal_kpc=axis,
        vertical_kpc=axis,
        radial_edges_kpc=radial_edges,
        cavity_mask=np.zeros_like(radius, dtype=bool),
        effective_mean_molecular_weight=0.62,
        regularization=module.DEFAULT_REGULARIZATION,
    )

    np.testing.assert_allclose(result.density_rms_kg_m3, rho, rtol=2.0e-4)
    np.testing.assert_allclose(result.temperature_k, temperature, rtol=2.0e-4)
    assert np.all(result.pressure_dyn_cm2 > 0.0)


def test_temperature_support_mismatch_is_interpolated_not_treated_as_cold_gas() -> None:
    module = load_module()
    temperature, direct = module.stabilize_deprojected_temperature(
        np.array([2.0e7, 1.0e-20, 6.0e7]),
        np.array([1.0, 1.0, 3.0]),
        np.array([5.0, 10.0, 15.0]),
    )

    assert direct.tolist() == [True, False, True]
    np.testing.assert_allclose(temperature, 2.0e7)


def test_ellipsoid_average_preserves_constant_pressure() -> None:
    module = load_module()
    average = module.ellipsoid_average_pressure(
        centroid_horizontal_kpc=12.0,
        centroid_vertical_kpc=-25.0,
        major_semiaxis_kpc=8.0,
        minor_semiaxis_kpc=4.0,
        los_semiaxis_kpc=6.0,
        orientation_rad=0.7,
        radial_centres_kpc=np.array([5.0, 25.0, 50.0, 100.0]),
        pressure_dyn_cm2=np.full(4, 3.5e-11),
        sobol_power=9,
    )

    assert average == pytest.approx(3.5e-11)
