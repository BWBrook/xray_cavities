from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest


SCRIPT = Path("scripts/science/diagnose_praise2_coefficient_correction.py")
sys.path.insert(0, str(Path(__file__).parents[1]))


def load_module():
    spec = importlib.util.spec_from_file_location("diagnose_praise2_coefficient_correction", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_weighted_change_reports_material_and_class_changes() -> None:
    module = load_module()
    baseline = np.asarray([[1.0, 0.0], [2.0, 4.0]])
    corrected = np.asarray([[0.9, 1.0], [2.2, 4.0]])
    rows = module.summarise_weighted_change(
        baseline, corrected, np.asarray([1.0, 3.0]), [0.15, 1.4], time_myr=50.0
    )
    assert rows[0]["corrected_over_uncorrected"] == pytest.approx(7.5 / 7.0)
    assert rows[0]["material_weight_fraction"] == 1.0
    assert rows[1]["class_change_count"] == 1


def test_weighted_change_rejects_shape_mismatch() -> None:
    module = load_module()
    with pytest.raises(module.CoefficientDiagnosticError, match="shapes"):
        module.summarise_weighted_change(
            np.ones((2, 2)), np.ones((2, 1)), np.ones(2), [0.15, 1.4], time_myr=50.0
        )


def test_endpoint_maps_preserve_matched_grid_and_totals() -> None:
    module = load_module()
    positions = np.asarray([[-1.0, 0.0, -1.0], [1.0, 0.0, 1.0]])
    weights = np.asarray([2.0, 3.0])
    baseline = np.asarray([[1.0], [2.0]])
    corrected = np.asarray([[1.5], [1.0]])
    arrays, rows = module.build_endpoint_maps(
        positions, weights, baseline, corrected, [1.4], bins=4
    )
    assert arrays["uncorrected_1p4GHz"].sum() == pytest.approx(8.0)
    assert arrays["corrected_1p4GHz"].sum() == pytest.approx(6.0)
    assert rows[0]["map_bins_per_axis"] == 4
    assert rows[0]["finite_ratio_pixels"] == 2


def test_endpoint_map_log_range_ignores_finite_zero_ratios() -> None:
    module = load_module()
    positions = np.asarray([[-1.0, 0.0, -1.0], [1.0, 0.0, 1.0]])
    arrays, rows = module.build_endpoint_maps(
        positions,
        np.ones(2),
        np.asarray([[1.0], [1.0]]),
        np.asarray([[0.0], [0.5]]),
        [15.0],
        bins=4,
    )
    assert np.count_nonzero(np.isfinite(arrays["ratio_15p0GHz"])) == 2
    assert rows[0]["max_abs_log10_ratio"] == pytest.approx(np.log10(2.0))
