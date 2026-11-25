import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import xray_cavity_method_ladder as ladder
from fit_source_excluded_background import prepare_radial_fit


def sky():
    ue = np.arange(-180.0, 181.0, 2.0)
    ze = 180.0 * np.sign(ue) * (np.abs(ue) / 180.0)**1.3
    u, z = (ue[:-1] + ue[1:]) / 2, (ze[:-1] + ze[1:]) / 2
    radius = np.hypot(u[None, :], z[:, None])
    return (u, z, ue, ze), radius


def test_control_and_sparse_positive_bins_match_frozen_background_and_detector():
    axes, radius = sky()
    u, z, _, _ = axes
    roi, _ = ladder._rois(u, z)
    bins = np.floor(radius / 5).astype(int)
    image = np.exp(-bins / 10)
    image[bins == 4] = 0
    image[bins >= 28] = 0
    sparse = np.argwhere(roi & (bins == 30))[0]
    image[tuple(sparse)] = .025
    fit = prepare_radial_fit(image, *axes)
    expected = ladder.observer_radial_background(image, u, z)
    for mask in (np.zeros(image.shape, bool), (image == 0), (z[:, None] < 0) & (bins == 7)):
        result = fit.fit(mask)
        assert result.status == {"flat": "ok", "log_slope": "ok"}
        assert result.rows[30]["valid_pixels"] == result.rows[30]["required_pixels"] == 1
        assert result.rows[30]["support_class"] == "direct"
        assert result.rows[4]["support_class"] == "interpolated"
        assert result.rows[-1]["support_class"] == "outer_extrapolated"
        for name, background in result.backgrounds.items():
            np.testing.assert_array_equal(background, expected)
            profile = np.array([row[f"{name}_profile"] for row in result.rows])
            centres = np.array([row["r_center_kpc"] for row in result.rows])
            np.testing.assert_array_equal(np.interp(radius[roi], centres, profile), expected[roi])
        control = ladder.deficit_threshold(image, u, z, background=expected, background_label="baseline", threshold=.05)
        repeated = ladder.deficit_threshold(image, u, z, background=result.backgrounds["flat"],
                                            background_label="flat", threshold=.05)
        assert control.mask.any()
        np.testing.assert_array_equal(repeated.mask, control.mask)


def test_excluded_brightness_does_not_enter_fit_and_exact_areas_are_reported():
    axes, radius = sky()
    u, z, ue, ze = axes
    selected = (radius < 20) | ((u[None, :] < 0) & (z[:, None] > 0))
    areas = np.diff(ze)[:, None] * np.diff(ue)[None, :]
    raw = np.where(selected, 1000., 3.)
    saved = raw.copy()
    first = prepare_radial_fit(raw, *axes).fit(selected)
    second = prepare_radial_fit(np.where(selected, .15, raw), *axes).fit(selected)
    for name in first.backgrounds:
        np.testing.assert_array_equal(first.backgrounds[name], second.backgrounds[name])
        np.testing.assert_allclose(first.backgrounds[name][radius < 120], 3., rtol=3e-15)
    row = first.rows[8]
    ring = (radius >= row["r_inner_kpc"]) & (radius < row["r_outer_kpc"])
    assert row["valid_sectors"] == 12 and row["retained_sectors"] == 9
    assert row["retained_area_kpc2"] == pytest.approx(areas[ring & ~selected].sum())
    assert row["retained_area_fraction"] == pytest.approx(areas[ring & ~selected].sum() / areas[ring].sum())
    np.testing.assert_array_equal(raw, saved)


def test_bracketed_gaps_and_each_extrapolation_have_distinct_support_records():
    axes, radius = sky()
    rings = np.floor(radius / 5).astype(int)
    image = np.exp(-.2 * rings)
    excluded = (rings < 4) | ((rings >= 8) & (rings <= 10)) | (rings >= 24)
    result = prepare_radial_fit(image, *axes).fit(excluded)
    assert result.status == {"flat": "ok", "log_slope": "ok"}
    assert result.rows[0]["support_class"] == "inner_extrapolated"
    assert result.rows[5]["support_class"] == "direct"
    assert result.rows[9]["support_class"] == "interpolated"
    assert result.rows[25]["support_class"] == "outer_extrapolated"
    assert result.rows[0]["flat_unsmoothed"] == np.exp(-.2 * 4)
    assert result.rows[0]["log_slope_unsmoothed"] == pytest.approx(1.)
    assert result.rows[9]["flat_unsmoothed"] == pytest.approx((np.exp(-.2 * 7) + np.exp(-.2 * 11)) / 2)
    assert result.rows[25]["flat_unsmoothed"] == result.rows[23]["retained_median"]
    assert result.rows[0]["flat_profile"] < result.rows[0]["log_slope_profile"]


def test_one_retained_sector_is_recorded_but_does_not_supply_a_ring():
    axes, radius = sky()
    u, z, _, _ = axes
    ring = (radius >= 60) & (radius < 65)
    angle = np.arctan2(z[:, None], u[None, :])
    sliver = (angle > .02) & (angle < .48)
    result = prepare_radial_fit(np.where(ring, 10., 2.), *axes).fit(ring & ~sliver)
    row = result.rows[12]
    assert row["retained_pixels"] >= row["required_pixels"]
    assert row["retained_sectors"] == 1 < row["required_sectors"]
    assert row["support_class"] == "interpolated" and row["retained_median"] == 10.
    assert row["flat_unsmoothed"] == 2.


@pytest.mark.parametrize("one_ring", [False, True])
def test_insufficient_support_retains_all_radial_rows_without_scoring_a_fit(one_ring):
    axes, radius = sky()
    mask = (np.floor(radius / 5) != 10) if one_ring else np.ones(radius.shape, dtype=bool)
    result = prepare_radial_fit(np.ones_like(radius), *axes).fit(mask)
    reason = "one_supported_annulus" if one_ring else "no_supported_annuli"
    assert set(result.status.values()) == {reason}
    assert result.backgrounds == {"flat": None, "log_slope": None}
    assert sum(row["support_class"] == "direct" for row in result.rows) == int(one_ring)
    assert all(row["flat_profile"] is None and row["log_slope_profile"] is None for row in result.rows)


def test_overflow_only_holds_the_inward_sensitivity():
    axes, radius = sky()
    rings = np.floor(radius / 5)
    image = np.ones_like(radius)
    for ring, value in ((10, 1e250), (11, 1e175), (12, 1e100)):
        image[rings == ring] = value
    fit = prepare_radial_fit(image, *axes).fit(rings < 10)
    assert fit.status == {"flat": "ok", "log_slope": "nonfinite_inward_continuation"}
    assert fit.backgrounds["log_slope"] is None
    assert np.all(np.isfinite(fit.backgrounds["flat"][radius < 120]))


def test_bad_exclusion_or_native_edges_stop_the_fit():
    axes, radius = sky()
    fit = prepare_radial_fit(np.ones_like(radius), *axes)
    with pytest.raises(ValueError, match="Boolean"):
        fit.fit(np.ones(radius.shape, dtype=int))
    u, z, ue, ze = axes
    with pytest.raises(ValueError, match="native edges"):
        prepare_radial_fit(np.ones_like(radius), u, z, ue[:-1], ze)
