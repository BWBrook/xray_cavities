from __future__ import annotations

import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.diagnose_g_lo_pressure_smoothing import _RateSample, diagnose_pressure_smoothing


def _write_cache(path: Path, pressure: np.ndarray, *, ids: np.ndarray | None = None, presence: np.ndarray | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    n, nt = pressure.shape
    ids = np.arange(100, 100 + n, dtype=np.int64) if ids is None else ids
    if presence is None:
        presence = np.isfinite(pressure)
    density = np.where(presence, np.where(pressure == 0, 0.0, 2.0), np.nan)
    tracer = np.where(presence, np.where(pressure == 0, 0.0, 0.8), np.nan)
    last = np.where(presence, 0.0, np.nan)
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=ids)
        h5.create_dataset("times", data=np.arange(nt, dtype=np.float64))
        h5.create_dataset("output_indices", data=np.arange(nt, dtype=np.int64))
        h5.create_dataset("pressure", data=np.asarray(pressure, dtype=np.float64))
        h5.create_dataset("density", data=density)
        h5.create_dataset("tracer", data=tracer)
        h5.create_dataset("last_shock_time", data=last)
        h5.create_dataset("position", data=np.zeros((n, 3), dtype=np.float64))
        h5.create_dataset("velocity", data=np.zeros((n, 3), dtype=np.float64))
        first_present = np.argmax(presence, axis=1).astype(np.float64)
        h5.create_dataset("tinj", data=first_present)
        h5.create_dataset("presence", data=presence)
        h5.attrs["next_output"] = nt
        h5.attrs["shock_threshold"] = 5.0
        h5.attrs["shock_component"] = 2
        h5.attrs["source_identity_sha256"] = "a" * 64


def _run(tmp_path: Path, pressure: np.ndarray, *, presence: np.ndarray | None = None) -> tuple[dict, Path]:
    cache = tmp_path / "cache.h5"
    output = tmp_path / "out"
    _write_cache(cache, pressure, presence=presence)
    summary = diagnose_pressure_smoothing(
        cache, output, row_chunk=1,
        expected_trim_rows=0,
        expected_no_positive_rows=0,
        expected_single_record_rows=0,
    )
    return summary, output


def test_positive_raw_input_can_have_negative_linear_overshoot_but_log_stays_positive(tmp_path: Path) -> None:
    pressure = np.array([[1.0, 1.0, 1.0, 1.0, 20.0, 1.0, 1.0]], dtype=float)
    summary, output = _run(tmp_path, pressure)
    assert summary["counts"]["smoothed_rows"] == 1
    assert summary["counts"]["linear_nonpositive_output_count"] > 0
    assert summary["counts"]["log_nonpositive_output_count"] == 0
    assert summary["affected_row_count"] == 1
    assert summary["triangular_smoothing"]["nonpositive_output_count"] == 0
    methods = summary["adiabatic_pressure_rate_proxy"]["methods"]
    assert methods["unsmoothed"]["finite_pair_count"] > 0
    assert methods["log_sg"]["finite_pair_count"] > 0
    assert "upper_tail_difference" in methods["triangular"]
    rows = list(__import__("csv").DictReader((output / "pressure_smoothing_affected_rows.csv").open()))
    assert rows[0]["physical_id"] == "100"
    assert rows[0]["raw_local_neighborhood_json"]


def test_leading_nan_prefix_and_excluded_rows_are_respected(tmp_path: Path) -> None:
    pressure = np.array([
        [np.nan, np.nan, 1.0, 1.0, 2.0, 1.0, 1.0],
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    ])
    presence = np.array([
        [False, False, True, True, True, True, True],
        [True, True, True, True, True, True, True],
    ])
    cache = tmp_path / "cache.h5"
    output = tmp_path / "out"
    _write_cache(cache, pressure, presence=presence)
    summary = diagnose_pressure_smoothing(
        cache, output, row_chunk=1,
        expected_trim_rows=0,
        expected_no_positive_rows=1,
        expected_single_record_rows=0,
    )
    assert summary["counts"]["active_rows"] == 1
    assert summary["counts"]["excluded_rows"] == 1
    assert summary["counts"]["smoothed_rows"] == 1
    assert summary["excluded_cache_rows"] == [1]
    assert summary["affected_row_count"] == 0


def test_short_histories_are_left_unsmoothed(tmp_path: Path) -> None:
    pressure = np.array([[1.0, 2.0, 3.0, 4.0]])
    summary, output = _run(tmp_path, pressure)
    assert summary["counts"]["short_rows"] == 1
    assert summary["counts"]["smoothed_rows"] == 0
    assert json.loads((output / "pressure_smoothing_diagnostic.json").read_text())["status"] == "diagnostic_complete"


def test_output_is_deterministic_and_schema_valid(tmp_path: Path) -> None:
    pressure = np.array([[1.0, 1.1, 1.2, 1.3, 1.4, 1.5]])
    cache = tmp_path / "cache.h5"
    _write_cache(cache, pressure)
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    first = diagnose_pressure_smoothing(cache, first_dir, row_chunk=1, expected_trim_rows=0, expected_no_positive_rows=0, expected_single_record_rows=0)
    second = diagnose_pressure_smoothing(cache, second_dir, row_chunk=1, expected_trim_rows=0, expected_no_positive_rows=0, expected_single_record_rows=0)
    assert first == second
    assert (first_dir / "pressure_smoothing_affected_rows.csv").read_bytes() == (second_dir / "pressure_smoothing_affected_rows.csv").read_bytes()
    assert (first_dir / "pressure_smoothing_diagnostic.json").read_bytes() == (second_dir / "pressure_smoothing_diagnostic.json").read_bytes()


def test_rate_sample_state_remains_capped_across_chunks() -> None:
    sample = _RateSample(cap=7)
    for chunk in range(20):
        sample.add(np.arange(100, dtype=np.float64) + chunk)
        assert len(sample.values) <= 7
    summary = sample.summary()
    assert summary["sample_count"] == 7
    assert summary["finite_pair_count"] == 2000
