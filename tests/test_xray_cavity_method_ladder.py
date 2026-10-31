from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import numpy as np
import pytest

import build_three_case_cavity_recovery as legacy_builder
import three_case_cavity_recovery as recovery
import xray_cavity_method_ladder as ladder
import xray_cavity_synthetic as synthetic

AXES = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products")
STRIDE = 4
APERTURE_AREA_KPC2 = np.pi * recovery.CANDIDATE_RADIUS_KPC**2


@lru_cache(maxsize=None)
def axes(view: str) -> tuple[np.ndarray, np.ndarray]:
    horizontal_name = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
    horizontal = np.loadtxt(AXES / f"xraise_grid_{view}" / horizontal_name)[::STRIDE]
    vertical = np.loadtxt(AXES / f"xraise_grid_{view}" / "z_kpc.tsv")[::STRIDE]
    return horizontal, vertical


@lru_cache(maxsize=None)
def rendered(view: str, along: float, across: float) -> synthetic.SyntheticMap:
    horizontal, vertical = axes(view)
    cavities = (
        synthetic.bipolar_pair(semiaxis_along_jet_kpc=along, semiaxis_across_jet_kpc=across)
        if along
        else ()
    )
    return synthetic.render_map(
        synthetic.load_atmosphere("cluster"), horizontal, vertical, cavities,
        view_deg=float(view.removesuffix("deg")),
    )


def test_legacy_rung_reproduces_the_production_observer_mask() -> None:
    image = rendered("45deg", 40.0, 25.0)
    loaded = recovery.LoadedMap(
        recovery.MapSpec("SYN", "45deg", "", "", "", "", "synthetic"),
        image.surface_brightness, image.cavity_mask.astype(float),
        image.horizontal_axis_kpc, image.z_axis_kpc,
    )
    production = legacy_builder.analyse_loaded_map(loaded, time_myr=30.0)
    rung = ladder.legacy_area_fraction(
        image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc
    )
    np.testing.assert_array_equal(rung.mask, production.observer_mask)
    assert rung.topology_class == production.summary_row["topology_class"]


@pytest.mark.parametrize(("along", "across"), [(15.0, 10.0), (40.0, 25.0), (80.0, 45.0)])
def test_legacy_retained_area_is_fixed_by_the_aperture_not_the_cavity(along: float, across: float) -> None:
    image = rendered("0deg", along, across)
    result = ladder.legacy_area_fraction(
        image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc
    )
    area = recovery._cell_area_grid(image.horizontal_axis_kpc, image.z_axis_kpc)
    assert area[result.mask].sum() == pytest.approx(0.01 * APERTURE_AREA_KPC2, rel=0.05)


def test_legacy_reports_a_cavity_in_a_cavity_free_atmosphere() -> None:
    image = rendered("45deg", 0.0, 0.0)
    result = ladder.legacy_area_fraction(
        image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc
    )
    assert result.topology_class != "no_significant_component"


@pytest.mark.parametrize("view", ["0deg", "45deg"])
def test_seed_grow_observer_rung_detects_nothing_in_a_null_map(view: str) -> None:
    image = rendered(view, 0.0, 0.0)
    result = ladder.seed_grow(image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc)
    assert result.topology_class == "no_significant_component"


def test_oracle_background_recovers_the_full_projected_cavity() -> None:
    image = rendered("45deg", 40.0, 25.0)
    null = rendered("45deg", 0.0, 0.0)
    result = ladder.seed_grow(
        image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc,
        background=null.surface_brightness, background_label="oracle",
    )
    rows = ladder.score_rows(
        result, image.horizontal_axis_kpc, image.z_axis_kpc,
        truth_masks={side: length > 0.0 for side, length in image.cavity_path_length_kpc.items()},
        truth_volumes=image.cavity_volume_kpc3,
    )
    for row in rows:
        assert row["completeness"] > 0.97
        assert row["purity"] > 0.99
        assert row["volume_ratio_revolution"] == pytest.approx(1.0, abs=0.05)


def test_revolution_volume_is_exact_for_a_projected_spheroid() -> None:
    image = rendered("0deg", 40.0, 25.0)
    for side, length in image.cavity_path_length_kpc.items():
        volumes = ladder.side_volumes(length > 0.0, image.horizontal_axis_kpc, image.z_axis_kpc)
        assert volumes["revolution"] == pytest.approx(image.cavity_volume_kpc3[side], rel=0.03)
        assert volumes["minor_depth"] == pytest.approx(image.cavity_volume_kpc3[side], rel=0.05)


def test_threshold_rung_requires_a_positive_threshold() -> None:
    image = rendered("0deg", 0.0, 0.0)
    with pytest.raises(ValueError, match="threshold"):
        ladder.deficit_threshold(
            image.surface_brightness, image.horizontal_axis_kpc, image.z_axis_kpc,
            background=image.surface_brightness, background_label="oracle", threshold=0.0,
        )
