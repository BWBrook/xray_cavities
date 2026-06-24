from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/xraise_grid_smoke.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("xraise_grid_smoke", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def legacy_center_bin_raw_path(
    module,
    *,
    x: np.ndarray,
    y: np.ndarray,
    u_edges: np.ndarray,
    view_angle_deg: float,
) -> np.ndarray:
    theta = math.radians(view_angle_deg)
    x_widths = module.widths_from_centres(x)
    y_widths = module.widths_from_centres(y)
    u_widths = np.diff(u_edges)
    u_coord = x[np.newaxis, :] * math.cos(theta) - y[:, np.newaxis] * math.sin(theta)
    bins = np.searchsorted(u_edges, u_coord, side="right") - 1
    valid = (bins >= 0) & (bins < len(u_widths))
    flat_bins = bins[valid].astype(np.int64)
    cell_weights = x_widths[np.newaxis, :] * y_widths[:, np.newaxis]
    weights = cell_weights[valid] / u_widths[flat_bins]
    return np.bincount(flat_bins, weights=weights, minlength=len(u_widths))


def test_projected_axis_expands_for_45_degree_view() -> None:
    module = load_script_module()
    x = np.array([-1.0, 1.0])
    y = np.array([-1.0, 1.0])

    u, edges = module.projected_axis(x, y, view_angle_deg=45.0, projected_u_bins=4)

    assert len(u) == 4
    assert len(edges) == 5
    assert edges[0] == pytest.approx(-2.0 * math.sqrt(2.0), rel=1.0e-12)
    assert edges[-1] == pytest.approx(2.0 * math.sqrt(2.0), rel=1.0e-12)


def test_projected_accumulation_matches_y_projection_at_zero_degrees() -> None:
    module = load_script_module()
    raw = np.ones((1, 2, 2), dtype=float)
    corrected = raw * 2.0
    tracer = np.array([[[0.1, 0.2], [0.3, 0.4]]], dtype=float)
    x = np.array([-0.5, 0.5])
    y = np.array([-0.5, 0.5])
    u_edges = np.array([-1.0, 0.0, 1.0])
    raw_path = np.zeros((1, 2), dtype=float)
    corrected_path = np.zeros((1, 2), dtype=float)
    tracer_max = np.zeros((1, 2), dtype=float)

    module.accumulate_projected_chunk(
        raw_path=raw_path,
        corrected_path=corrected_path,
        tracer_max=tracer_max,
        raw=raw,
        corrected=corrected,
        tracer=tracer,
        x=x,
        y_chunk=y,
        x_widths=np.array([1.0, 1.0]),
        y_widths_chunk=np.array([1.0, 1.0]),
        u_edges=u_edges,
        view_angle_deg=0.0,
    )

    np.testing.assert_allclose(raw_path, [[2.0, 2.0]])
    np.testing.assert_allclose(corrected_path, [[4.0, 4.0]])
    np.testing.assert_allclose(tracer_max, [[0.3, 0.4]])


def test_projected_accumulation_conserves_integrated_path_weight() -> None:
    module = load_script_module()
    raw = np.ones((1, 2, 2), dtype=float)
    corrected = raw.copy()
    tracer = np.zeros_like(raw)
    x = np.array([-0.5, 0.5])
    y = np.array([-0.5, 0.5])
    _u, u_edges = module.projected_axis(x, y, view_angle_deg=45.0, projected_u_bins=4)
    raw_path = np.zeros((1, 4), dtype=float)
    corrected_path = np.zeros((1, 4), dtype=float)
    tracer_max = np.zeros((1, 4), dtype=float)

    module.accumulate_projected_chunk(
        raw_path=raw_path,
        corrected_path=corrected_path,
        tracer_max=tracer_max,
        raw=raw,
        corrected=corrected,
        tracer=tracer,
        x=x,
        y_chunk=y,
        x_widths=np.array([1.0, 1.0]),
        y_widths_chunk=np.array([1.0, 1.0]),
        u_edges=u_edges,
        view_angle_deg=45.0,
    )

    projected_widths = np.diff(u_edges)
    assert np.all(raw_path[0] > 0.0)
    assert float(np.sum(raw_path[0] * projected_widths)) == pytest.approx(4.0)


def test_projected_overlap_accumulation_removes_90_degree_center_bin_empty_stripes() -> None:
    module = load_script_module()
    x = np.array([-1.0, 1.0])
    y = np.array([-3.0, -1.7, -0.4, 0.35, 1.4, 3.0])
    raw = np.ones((1, len(y), len(x)), dtype=float)
    corrected = raw * 2.0
    tracer = np.ones_like(raw)
    _u, u_edges = module.projected_axis(x, y, view_angle_deg=90.0, projected_u_bins=24)

    legacy_path = legacy_center_bin_raw_path(module, x=x, y=y, u_edges=u_edges, view_angle_deg=90.0)
    assert np.count_nonzero(legacy_path == 0.0) >= 12

    raw_path = np.zeros((1, len(u_edges) - 1), dtype=float)
    corrected_path = np.zeros_like(raw_path)
    tracer_max = np.zeros_like(raw_path)
    x_edges = module.centres_to_edges(x)
    y_edges = module.centres_to_edges(y)

    module.accumulate_projected_chunk(
        raw_path=raw_path,
        corrected_path=corrected_path,
        tracer_max=tracer_max,
        raw=raw,
        corrected=corrected,
        tracer=tracer,
        x=x,
        y_chunk=y,
        x_widths=module.widths_from_centres(x),
        y_widths_chunk=module.widths_from_centres(y),
        u_edges=u_edges,
        view_angle_deg=90.0,
        x_edges=x_edges,
        y_edges_chunk=y_edges,
    )

    projected_widths = np.diff(u_edges)
    source_area = float(np.sum(np.diff(y_edges)[:, np.newaxis] * np.diff(x_edges)[np.newaxis, :]))
    assert np.count_nonzero(raw_path[0] == 0.0) == 0
    assert np.count_nonzero(corrected_path[0] == 0.0) == 0
    assert float(np.sum(raw_path[0] * projected_widths)) == pytest.approx(source_area)
    assert float(np.sum(corrected_path[0] * projected_widths)) == pytest.approx(2.0 * source_area)
    assert np.all(tracer_max[0] > 0.0)
