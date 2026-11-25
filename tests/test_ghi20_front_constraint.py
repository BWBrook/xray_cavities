import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from compare_compressive_front import Grid
from measure_ghi20_front_constraint import area_scores, front_interior


def test_an_open_or_ambiguous_front_is_unscored():
    edges = np.arange(-5, 6)
    centres = (edges[:-1] + edges[1:]) / 2
    grid = Grid(centres, edges, centres, edges)
    ring = np.zeros((10, 10))
    ring[1:9, [1, 8]] = 1
    ring[[1, 8], 1:9] = 1
    inside, record = front_interior(ring, grid, False)
    assert record["status"] == "closed" and record["filled_hole_pixels"] == 36
    assert inside.sum() == 64 and inside[1, 1]
    assert front_interior(ring, grid, True)[0] is None
    opened = ring.copy()
    opened[1, 3] = 0
    assert front_interior(opened, grid, False)[1]["reason"] == "source open to exterior sky"
    corner = ring.copy()
    corner[1, 1] = 0
    assert "ambiguous diagonal enclosure" in front_interior(corner, grid, False)[1]["reason"]
    touching = ring.copy()
    touching[0, 1] = 1
    assert "boundary" in front_interior(touching, grid, False)[1]["reason"]


def test_open_sky_in_an_indentation_is_preserved():
    edges = np.arange(-4, 5)
    centres = (edges[:-1] + edges[1:]) / 2
    grid = Grid(centres, edges, centres, edges)
    path = np.zeros((8, 8))
    path[1:7, 1:7] = 1
    path[2, 1:3] = 0
    inside, record = front_interior(path, grid, False)
    assert record["status"] == "closed"
    np.testing.assert_array_equal(inside, path > 0)


def test_physical_area_partitions_selected_and_unselected_lobe_separately():
    area = np.outer([1, 3], [2, 5, 7])
    seen = np.array([[1, 1, 1], [1, 0, 1]], dtype=bool)
    truth = np.array([[1, 1, 0], [0, 1, 1]], dtype=bool)
    front = np.array([[1, 0, 0], [1, 0, 1]], dtype=bool)
    row = area_scores(seen, truth, front, area)
    assert (row["false_before_kpc2"], row["false_removed_kpc2"], row["false_after_kpc2"]) == (13, 7, 6)
    assert (row["true_before_kpc2"], row["true_lost_kpc2"], row["true_after_kpc2"]) == (28, 5, 23)
    assert row["lobe_outside_front_kpc2"] == 20 and row["lobe_area_kpc2"] == 43
    assert row["fraction_selected_true_lost"] == 5/28 and row["fraction_full_lobe_lost"] == 5/43
    empty = area_scores(np.zeros_like(seen), truth, front, area)
    assert empty["fraction_false_removed"] is None and empty["fraction_selected_true_lost"] is None
