import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import score_four_case_midplane_slabs as score
from compare_compressive_front import Grid


def grid_from_edges(x, z):
    x, z = np.array(x, dtype=float), np.array(z, dtype=float)
    return Grid((x[1:] + x[:-1]) / 2, x, (z[1:] + z[:-1]) / 2, z)


def test_coverage_splits_weighted_overlap_null_dimmed_and_unknown():
    grid = grid_from_edges([-3, -1, 2, 6], [-1, 0, 3])
    # Native sky areas are 2, 3, 4 and 6, 9, 12 kpc².
    path = np.array([[4, 0, 3], [1, 5, 2]])
    outline = np.array([[1, 1, 1], [0, 1, 1]], dtype=bool)
    control = np.array([[1, 0, 1], [0, 1, 0]], dtype=bool)
    physical = np.array([[.05, .1, .07], [.5, np.nan, -.1]])
    rows = {r["hemisphere"]: r for r in score.coverage_split(grid, outline, control, path, physical)}
    expect = {"lobe_kpc2": 33, "overlap_kpc2": 27, "lobe_in_control_outline_kpc2": 15,
              "overlap_in_control_outline_kpc2": 15, "overlap_outside_control_outline_kpc2": 12,
              "overlap_dimmed_kpc2": 4, "overlap_not_dimmed_kpc2": 14,
              "overlap_invalid_initial_kpc2": 9, "dimmed_on_lobe_kpc2": 10,
              "dimmed_on_lobe_missed_kpc2": 6}
    for k, v in expect.items():
        assert rows["both"][k] == rows["negative_z"][k] + rows["positive_z"][k] == v
    assert rows["both"]["control_coverage"] == 15 / 33
    assert rows["both"]["coverage"] == 27 / 33


@pytest.mark.parametrize(("positive", "invalid", "expected"), [(0.075, False, .08), (.25, False, None),
                                                                  (.075, True, None)])
def test_first_empty_sensitivity_requires_supported_empty_control_on_both_sides(positive, invalid, expected):
    grid = grid_from_edges(np.arange(-20, 22, 2), np.arange(-20, 22, 2))
    zero = np.ones(grid.area.shape)
    zero[4:8, 7:13] -= .055
    zero[12:16, 7:13] -= positive
    background = np.ones_like(zero)
    if invalid:
        background[11, 11] = np.nan
    outline = score.ladder.deficit_threshold(zero, grid.u, grid.z, background=background,
                                               background_label="observer_radial", threshold=.05)
    cut, rows = score.null_ladder(grid, zero, background, outline)
    assert cut == expected
    assert len(rows) == len(score.CUTS) * 3
    statuses = {(r["hemisphere"], r["cut"]): r["time_zero_status"] for r in rows}
    assert statuses["both", .05] == "failed_nonempty" and statuses["negative_z", .06] == "empty"
    if invalid:
        assert statuses["positive_z", .2] == "unscorable"
    if cut is None:
        result = score.sensitivity_scores(grid, {}, None, cut, "failed_nonempty", [
            {"hemisphere": "both", "target": "full_lobe", "lobe_kpc2": 25, "lobe_outside_aperture_kpc2": 1}],
            None, None)[0]
        assert result["first_clean_status"] == "none_tested"
        assert all(result[k] is None for k in ("first_clean_cut", "purity", "completeness", "false_kpc2",
                                                "selection_touches_aperture"))


def test_fixed_sightlines_bind_overflow_empty_bins_and_signed_dilution_by_depth():
    grid = grid_from_edges([-2, 0, 3], [-2, 0, 1])
    path = np.array([[5., 0.], [101., 10.]])
    fields, measured = {}, {}
    for depth, before, now in (("full", 20., 17.), ("slab30", 10., 5.), ("slab10", 4., 1.)):
        image = np.full_like(path, before)
        fields[depth] = {"initial": image, "current": np.full_like(path, now),
                         "current_lobe": np.where(path > 0, -0.1, 0.) * now,
                         "initial_on_current_lobe": .1 * image, "tracer_path": path}
        measured[depth] = {"mask": path > 5}
    layers, depths = score.layer_scores(grid, fields, measured)
    values = {(r["sightlines"], r["hemisphere"], r["layer"]): r for r in layers}
    assert values["path_0_5_kpc", "both", "whole_sightline"]["area_kpc2"] == 4
    assert values["path_5_10_kpc", "both", "whole_sightline"]["area_kpc2"] == 3
    assert values["path_over_100_kpc", "both", "whole_sightline"]["area_kpc2"] == 2
    empty = values["path_60_100_kpc", "both", "within_10_kpc"]
    assert empty["area_kpc2"] == empty["initial_flux"] == 0
    assert empty["fractional_change"] is None and empty["share_of_initial_flux"] is None
    outer = values["lobe", "both", "beyond_30_kpc"]
    assert outer["share_of_initial_flux"] == .5 and outer["fractional_change"] == .2
    for k in ("initial_flux", "current_flux", "current_lobe_flux", "initial_lobe_flux"):
        assert sum(values["lobe", "both", layer][k] for layer in
                   ("within_10_kpc", "10_to_30_kpc", "beyond_30_kpc")) == pytest.approx(
                       values["lobe", "both", "whole_sightline"][k])
    row = next(r for r in depths if (r["sightlines"], r["hemisphere"], r["depth"]) == ("lobe", "both", "slab30"))
    assert row["matched_deficit"] == .5 and row["full_deficit"] == .15
    assert row["dilution_by_initial_outer_light"] == .25
    assert row["change_due_to_outer_brightening"] == pytest.approx(.1)
    assert row["ambient_change_flux"] + row["tracer_change_flux"] == pytest.approx(
        row["current_flux"] - row["initial_flux"])


def test_native_volume_rejects_a_compensating_side_swap():
    grid = grid_from_edges([-1, 0, 1], [-1, 0, 1])
    maps = {d: {"tracer_path": np.array([[1., 0.], [0., 2.]])} for d in score.DEPTHS}
    native = {d: {"both": 3., "negative_z": 1., "positive_z": 2.} for d in score.DEPTHS}
    assert len(score.volume_closure(grid, maps, native)) == 9
    native["slab30"]["negative_z"], native["slab30"]["positive_z"] = 2., 1.
    with pytest.raises(ValueError, match="slab30/negative_z"):
        score.volume_closure(grid, maps, native)


def test_untrusted_or_relabelled_pilot_receipt_is_rejected_before_loading_rasters(tmp_path):
    historical = json.loads((score.ASSETS / "ghi20_midplane_slabs_2026-11-25/native_completion.json").read_text())
    seen = tmp_path / "completion.json"
    historical["case"], historical["snapshot_index"] = "C-LO", 20
    seen.write_text(json.dumps(historical))
    with pytest.raises(ValueError, match="supplied SHA-256"):
        score.read_projection(tmp_path, score.PILOT_COMPLETION_SHA)
    with pytest.raises(ValueError, match="prebound native science output"):
        score.read_projection(tmp_path, score.front.HASH(seen))
