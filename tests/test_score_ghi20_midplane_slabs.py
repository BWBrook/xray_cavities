import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from compare_compressive_front import Grid
from score_ghi20_midplane_slabs import area_scores, filling_scores, fit_image
import xray_cavity_method_ladder as ladder


def stretched_grid():
    x = np.array([-3., -1., 2., 6.])
    z = np.array([-1., 0., 3.])
    return Grid((x[:-1] + x[1:]) / 2, x, (z[:-1] + z[1:]) / 2, z)


def test_same_outline_has_different_full_and_slab_overlaps_on_a_stretched_grid():
    grid = stretched_grid()
    full = np.array([[5, 0, 4], [2, 0, 5]])
    slab = np.array([[2, 0, 0], [.5, 0, 4]])
    selected = np.array([[1, 0, 1], [1, 1, 0]], dtype=bool)
    reference = np.array([[0, 0, 1], [0, 1, 1]], dtype=bool)
    rows = {(r["hemisphere"], r["target"]): r for r in area_scores(grid, selected, reference, full, slab)}
    full_row, slab_row = (rows["both", target] for target in ("full_lobe", "slab_lobe"))
    measures = ("selected_kpc2", "lobe_kpc2", "overlap_kpc2", "missed_kpc2", "false_kpc2", "native_lobe_kpc3")
    assert [full_row[k] for k in measures] == [21, 24, 12, 12, 9, 98]
    assert [slab_row[k] for k in measures] == [21, 20, 8, 12, 13, 55]
    for row in (full_row, slab_row):
        assert row["slab_area_retained_fraction"] == 20 / 24
        assert row["slab_volume_retained_fraction"] == 55 / 98
        assert row["overlap_gained_vs_full_kpc2"] == 8 and row["overlap_lost_vs_full_kpc2"] == 12
        for k in measures:
            assert rows["negative_z", row["target"]][k] + rows["positive_z", row["target"]][k] == row[k]
    assert slab_row["purity"] == 8 / 21 and slab_row["completeness"] == 8 / 20
    for row in area_scores(grid, np.zeros_like(selected), reference, full, np.zeros_like(slab)):
        assert row["purity"] is None
        if row["target"] == "slab_lobe":
            assert row["completeness"] is None


def test_fixed_sightlines_separate_ambient_change_from_the_fitted_baseline():
    grid = stretched_grid()
    full_path = np.array([[1, 0, 1], [0, 0, 0]])
    mask = np.array([[1, 0, 0], [0, 0, 0]], dtype=bool)
    fields = {
        "current": np.array([[8, 9, 11], [9, 15, 12]]), "initial": np.full((2, 3), 10),
        "current_lobe": np.array([[1, 0, 2], [0, 0, 0]]),
        "initial_on_current_lobe": np.array([[6, 0, 4], [0, 0, 0]]),
    }
    background = np.array([[8, 10, 14], [10, 10, 10]])
    deficit = ladder.recovery.compute_fractional_deficit
    rows = {(r["region"], r["hemisphere"]): r for r in filling_scores(
        grid, fields, background, deficit(fields["current"], background),
        deficit(fields["current"], fields["initial"]), full_path, mask)}
    whole = rows["full_lobe", "both"]
    assert whole["current_flux"] == whole["initial_flux"] == 60
    assert whole["lobe_brightness_decrement"] == whole["ambient_brightness_change"] == 18
    assert whole["ambient_offset_fraction"] == 1 and whole["physical_deficit_fraction"] == 0
    assert whole["fitted_deficit_fraction"] == 1 / 6
    assert whole["initial_only_dimmed_kpc2"] == 2 and whole["fitted_only_dimmed_kpc2"] == 4
    missed = rows["missed_by_full_depth_detector", "both"]
    assert missed["area_kpc2"] == 4 and missed["physical_deficit_fraction"] == -.1
    assert rows["full_lobe", "positive_z"]["physical_deficit_fraction"] is None


def test_unmasked_profiles_match_the_original_fitter_and_record_an_unsupported_annulus():
    edges = np.arange(-182., 184., 2.)
    centers = (edges[:-1] + edges[1:]) / 2
    grid = Grid(centers, edges, centers, edges)
    r = np.hypot(centers[:, None], centers[None, :])
    image = np.exp(-r / 100)
    image[(r >= 25) & (r < 30)] = 0
    fit, rows = fit_image(image, grid, "full", "current")
    np.testing.assert_allclose(fit, ladder.observer_radial_background(image, centers, centers))
    gap = next(row for row in rows if row["r_inner_kpc"] == 25)
    assert gap["valid_pixels"] == gap["positive_area_kpc2"] == 0
    assert gap["support"] == "interpolated" and gap["median_mjy_sr"] is None
    assert gap["smoothed_mjy_sr"] > 0
    scaled, _ = fit_image(0.4 * image, grid, "slab10", "current")
    np.testing.assert_allclose(0.4 * fit, scaled)
