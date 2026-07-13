from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


RECOVERY_SCRIPT = Path("scripts/science/three_case_cavity_recovery.py")
BUILDER_SCRIPT = Path("scripts/science/build_three_case_cavity_recovery.py")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_analyse_loaded_map_keeps_observer_and_truth_layers_separate() -> None:
    recovery = load_module("three_case_cavity_recovery", RECOVERY_SCRIPT)
    builder = load_module("build_three_case_cavity_recovery", BUILDER_SCRIPT)
    axis = np.linspace(-140.0, 140.0, 281)
    xx, zz = np.meshgrid(axis, axis)
    radius = np.hypot(xx, zz)
    xray = 1000.0 / (1.0 + (radius / 60.0) ** 2)
    cavity = ((xx / 16.0) ** 2 + ((zz - 45.0) / 22.0) ** 2 <= 1.0) | (
        (xx / 16.0) ** 2 + ((zz + 45.0) / 22.0) ** 2 <= 1.0
    )
    xray[cavity] *= 0.5
    tracer_a = cavity.astype(float)
    tracer_b = np.zeros_like(tracer_a)
    spec = recovery.MapSpec("TEST", "0deg", "xray", "tracer", "x", "z", "synthetic")
    loaded_a = recovery.LoadedMap(spec, xray, tracer_a, axis, axis)
    loaded_b = recovery.LoadedMap(spec, xray, tracer_b, axis, axis)

    result_a = builder.analyse_loaded_map(loaded_a)
    result_b = builder.analyse_loaded_map(loaded_b)

    np.testing.assert_array_equal(result_a.observer_mask, result_b.observer_mask)
    assert result_a.summary_row["component_count"] == 2
    assert len(result_a.component_rows) == 2
    assert len(result_a.tracer_rows) == 3
    assert result_a.tracer_rows != result_b.tracer_rows
    assert result_a.summary_row["topology_class"] == "two_separate_components"


def test_sensitivity_grid_is_complete_and_declares_base_protocol() -> None:
    builder = load_module("build_three_case_cavity_recovery", BUILDER_SCRIPT)

    grid = builder.sensitivity_protocols()

    assert len(grid) == 15
    assert sum(row["is_base"] for row in grid) == 1
    base = next(row for row in grid if row["is_base"])
    assert base["radial_bin_kpc"] == 5.0
    assert base["radial_smoothing_kpc"] == 10.0
    assert base["candidate_fraction_percent"] == 1.0
