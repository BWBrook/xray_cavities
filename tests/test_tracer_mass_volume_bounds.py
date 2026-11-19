import itertools
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
from build_tracer_mass_budget import finite_volume_difference, volume_bounds
from pluto_h5_level3_ambient_extract import derive_widths


def test_volume_bounds_allow_tracer_to_move_between_cells(tmp_path):
    axes = {}
    ratios = []
    for axis, nodes in zip("xyz", ([0., 1., 2., 4.], [0., 2., 6.], [0., 1., 4., 6.]), strict=True):
        nodes = np.array(nodes)
        centres = (nodes[:-1] + nodes[1:]) / 2
        axes[axis], axes[axis + "_edges"] = centres, nodes
        ratios.append(np.diff(nodes) / derive_widths(centres))
    path = tmp_path / "axes.npz"
    np.savez(path, **axes)
    lo, hi = volume_bounds(path)
    all_volumes = [np.prod(c) for c in itertools.product(*ratios)]
    # A fixed mass can occupy entirely different cells in the two snapshots.
    actual_changes = [17 * after - 12 * before for after, before in itertools.product(all_volumes, repeat=2)]
    assert finite_volume_difference(17, 12, lo, hi) == pytest.approx((min(actual_changes), max(actual_changes)))
