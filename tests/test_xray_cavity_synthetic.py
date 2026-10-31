from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import numpy as np
import pytest

import three_case_cavity_recovery as recovery
import xray_cavity_synthetic as synthetic

AXES = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products")
STRIDE = 6


@lru_cache(maxsize=None)
def axes(view: str) -> tuple[np.ndarray, np.ndarray]:
    horizontal_name = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
    horizontal = np.loadtxt(AXES / f"xraise_grid_{view}" / horizontal_name)[::STRIDE]
    vertical = np.loadtxt(AXES / f"xraise_grid_{view}" / "z_kpc.tsv")[::STRIDE]
    return horizontal, vertical


@lru_cache(maxsize=None)
def cluster() -> synthetic.Atmosphere:
    return synthetic.load_atmosphere("cluster")


def test_box_chord_matches_production_view_geometry() -> None:
    u = np.array([0.0, 100.0, 250.0])
    lower, upper = synthetic._box_chord(u, 0.0)
    assert upper[:2] - lower[:2] == pytest.approx([400.0, 400.0])
    assert upper[2] == lower[2]
    lower, upper = synthetic._box_chord(np.array([0.0]), 45.0)
    assert upper[0] - lower[0] == pytest.approx(400.0 * np.sqrt(2.0))


def test_null_map_is_mirror_symmetric_at_zero_degrees() -> None:
    horizontal, vertical = np.linspace(-199.0, 199.0, 81), np.linspace(-249.0, 249.0, 101)
    image = synthetic.render_map(cluster(), horizontal, vertical).surface_brightness
    assert np.all(image > 0.0)
    np.testing.assert_allclose(image, image[:, ::-1], rtol=1.0e-9)
    np.testing.assert_allclose(image, image[::-1, :], rtol=1.0e-9)


def test_projected_path_length_integrates_to_true_volume() -> None:
    horizontal, vertical = axes("0deg")
    cavities = synthetic.bipolar_pair(semiaxis_along_jet_kpc=40.0, semiaxis_across_jet_kpc=25.0)
    rendered = synthetic.render_map(cluster(), horizontal, vertical, cavities)
    area = recovery._cell_area_grid(horizontal, vertical)
    for side, length in rendered.cavity_path_length_kpc.items():
        assert np.sum(length * area) == pytest.approx(rendered.cavity_volume_kpc3[side], rel=0.02)


def test_evacuated_cavity_removes_exactly_its_chord_emission() -> None:
    horizontal, vertical = axes("0deg")
    cavity = synthetic.Spheroid(60.0, 40.0, 25.0, density_factor=1.0e-6)
    null = synthetic.render_map(cluster(), horizontal, vertical).surface_brightness
    image = synthetic.render_map(cluster(), horizontal, vertical, (cavity,)).surface_brightness
    row = int(np.argmin(np.abs(vertical - 60.0)))
    column = int(np.argmin(np.abs(horizontal)))
    u = np.array([horizontal[column]])
    z = np.array([vertical[row]])
    chord = cavity.half_chord(u, z)
    removed = synthetic._segment_integral(cluster(), u, z, -chord, chord, 1.0, 256)[0]
    assert null[row, column] - image[row, column] == pytest.approx(removed, rel=1.0e-4)


def test_rim_brightens_only_outside_the_cavity() -> None:
    horizontal, vertical = axes("0deg")
    plain = synthetic.bipolar_pair(semiaxis_along_jet_kpc=30.0, semiaxis_across_jet_kpc=20.0)
    rimmed = synthetic.bipolar_pair(
        semiaxis_along_jet_kpc=30.0, semiaxis_across_jet_kpc=20.0,
        rim_width_kpc=5.0, rim_density_factor=2.0,
    )
    a = synthetic.render_map(cluster(), horizontal, vertical, plain)
    b = synthetic.render_map(cluster(), horizontal, vertical, rimmed)
    assert np.all(b.surface_brightness >= a.surface_brightness * (1.0 - 1.0e-12))
    assert np.any(b.surface_brightness > a.surface_brightness * 1.01)


def test_cavities_must_fit_inside_the_production_box() -> None:
    horizontal, vertical = axes("0deg")
    with pytest.raises(ValueError, match="z boundary"):
        synthetic.render_map(cluster(), horizontal, vertical, (synthetic.Spheroid(200.0, 60.0, 30.0),))


def test_rim_temperature_convention_is_explicit() -> None:
    radius = np.array([5.0, 50.0, 150.0])
    ambient = cluster().emissivity(radius)
    np.testing.assert_allclose(cluster().emissivity(radius, 2.0, 1.0), 4.0 * ambient, rtol=1.0e-12)
    np.testing.assert_allclose(cluster().emissivity(radius, 2.0), cluster().emissivity(radius, 2.0, 0.5), rtol=1.0e-12)


def test_rankine_hugoniot_limits() -> None:
    assert synthetic.rankine_hugoniot(1.0) == pytest.approx((1.0, 1.0))
    density, temperature = synthetic.rankine_hugoniot(1.5)
    assert density == pytest.approx(12.0 / 7.0)
    assert density * temperature == pytest.approx((5.0 * 2.25 - 1.0) / 4.0)
    assert synthetic.rankine_hugoniot(1.0e4)[0] == pytest.approx(4.0, rel=1.0e-6)


def test_rim_mass_budget_matches_uniform_geometry_and_mass_matching() -> None:
    atmosphere = cluster()
    uniform = synthetic.Atmosphere(atmosphere.radius_kpc, np.ones_like(atmosphere.density_g_cm3), atmosphere.temperature_k)
    cavity = synthetic.Spheroid(40.0, 40.0, 24.0, 0.01, 6.0, 2.0)
    assert synthetic.rim_mass_budget(uniform, cavity)["rim_over_displaced"] == pytest.approx(0.796875 / 0.99, rel=1.0e-6)
    shock = synthetic.Spheroid(40.0, 40.0, 24.0, 0.01, 0.0, *synthetic.rankine_hugoniot(1.5))
    width = synthetic.mass_matched_rim_width(atmosphere, shock)
    matched = synthetic.Spheroid(**{**shock.__dict__, "rim_width_kpc": width})
    assert synthetic.rim_mass_budget(atmosphere, matched)["rim_over_displaced"] == pytest.approx(1.0, abs=1.0e-3)
