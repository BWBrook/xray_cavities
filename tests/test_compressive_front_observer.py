import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import compare_compressive_front as c


def grid(ue, ze):
    ue = np.asarray(ue, dtype=float)
    ze = np.asarray(ze, dtype=float)
    return c.Grid((ue[1:] + ue[:-1]) / 2, ue, (ze[1:] + ze[:-1]) / 2, ze)


def test_rectilinear_distance_uses_segment_not_nearest_centre_and_marks_enclosed_hole():
    g = grid([-7, -4, -2, -1, 1, 4, 10], [-5, -3, -1, 1, 3, 5])
    m = np.zeros((5, 6), bool)
    m[1:4, 1:5] = True
    m[2, 2] = False
    cdist = c.ContourDistance(m, g)
    pts = np.array([[-1.7, 0.25], [-6, 0], [3, 2], [4.5, 3.5], [-4, -1], [0, 0]])
    signed, at = cdist.signed(pts)
    np.testing.assert_allclose(signed, [0.3, 2, -1, 0.5**0.5, 0, -1])
    assert not cdist.edges.exterior[at[0]]
    assert cdist.edges.exterior[at[1]]
    # Every rectangular interface has its physical length, including the island hole.
    assert cdist.edges.length.sum() == 34
    rng = np.random.default_rng(17)
    points = rng.uniform((-8, -5), (11, 5), (150, 2))
    d, _nearest = cdist.signed(points)
    clamped = np.clip(points[:, None, :], cdist.edges.lo, cdist.edges.hi)
    brute = np.linalg.norm(clamped - points[:, None, :], axis=2).min(axis=1)
    np.testing.assert_allclose(abs(d), brute)
    e = c.ContourDistance(np.zeros_like(m), g)
    assert np.isnan(e.signed(pts)[0]).all()


def test_lateral_pixels_exclude_holes_and_lobeless_rows_and_profiles_use_projected_widths():
    g = grid([-10, -5, -3, -1, 1, 3, 5, 10], [-4, -2, 0, 2, 4])
    orange = np.ones((4, 7), bool)
    tracer = np.zeros_like(orange)
    tracer[0, [1, 2, 4, 5]] = True
    tracer[1, [1, 5]] = True
    tracer[3, 4] = True
    arc = c.lateral_pixels(orange, tracer, g.u)
    assert np.flatnonzero(arc[1]).tolist() == [0, 6]
    assert not arc[2].any() and np.flatnonzero(arc[3]).tolist() == [5, 6]
    chosen = c.profile_indices(g, arc, tracer.astype(float))
    assert chosen == [
        ("negative_z", "lateral_arc", 0),
        ("negative_z", "lobe", 0),
        ("positive_z", "lateral_arc", 3),
        ("positive_z", "lobe", 3),
    ]


def test_emission_partition_must_close_with_a_separate_remainder_and_signed_brightening():
    values = np.array([[5.0, 10.0], [8.0, 12.0]])
    grid2 = grid([-1, 0, 2], [-2, 0, 1])
    source = {}
    new = {}
    for epoch, amp in [("initial", 1.0), ("current", 2.0)]:
        source[f"brightness_{epoch}_retained_linear_whole"] = values * amp
        source[f"brightness_{epoch}_retained_linear_C"] = 0.2 * values * amp
        new[f"front_{epoch}_brightness"] = 0.3 * values * amp
        new[f"rest_{epoch}_brightness"] = 0.5 * values * amp
    fields, checks = c.emission_partition(source, new)
    assert checks["current"]["max_per_pixel_relative_error"] < 1e-13
    rows = c.region_rows(
        0, grid2, fields, {"sample": np.ones_like(values, bool)}, 4 * values
    )
    assert rows[0]["front_current_minus_initial"] == pytest.approx(15)
    assert rows[0]["front_gain_over_lobe_deficit"] is None
    new["rest_current_brightness"][0, 0] += 0.1
    with pytest.raises(ValueError, match="closure failed"):
        c.emission_partition(source, new)


def test_separation_summary_represents_absent_front_and_keeps_missed_regions():
    g = grid([-3, -1, 1, 3], [-3, -1, 1, 3])
    orange = np.zeros((3, 3), bool)
    orange[1:, 1] = True
    native = np.zeros_like(orange)
    ref = {"absent": (native, None)}
    r = c.separation_rows(45, g, orange, orange, orange, ref)
    assert len(r) == 6 and all(
        row["reference_segments"] == 0 and row["signed_median_kpc"] is None for row in r
    )
