#!/usr/bin/env python3
"""Read-only pressure-smoothing diagnostics for the Goal 049 history cache.

The immutable HDF5 cache is classified with the approved pressure-treatment
plan, then streamed in row chunks.  No PRAiSE call, pressure floor, or
interpolation is performed.  Only a compact JSON summary and CSV records for
rows with invalid smoothed values are written.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import h5py
import numpy as np
from scipy.signal import savgol_filter

from scripts.science import run_g_lo_radio_history_value as workflow


SMOOTH_WINDOW = 5
SMOOTH_POLYORDER = 3
NEIGHBOUR_RADIUS = 2
TRIANGULAR_KERNEL = np.asarray([1.0, 2.0, 3.0, 2.0, 1.0], dtype=np.float64) / 9.0
RATE_SAMPLE_CAP = 100_000
CSV_FIELDS = [
    "cache_row", "physical_id", "first_present_column", "first_present_output_index",
    "first_present_time", "endpoint_column", "endpoint_output_index", "endpoint_time",
    "present_count", "trim_affected", "linear_first_offending_column",
    "linear_first_offending_output_index", "linear_first_offending_raw_value",
    "linear_first_offending_value", "log_first_offending_column",
    "log_first_offending_output_index", "log_first_offending_raw_value",
    "log_first_offending_value", "linear_nonpositive_count", "linear_nonfinite_count",
    "log_nonpositive_count", "log_nonfinite_count", "min_linear_value", "min_log_value",
    "min_linear_to_raw_ratio", "min_log_to_raw_ratio", "linear_endpoint_relative_difference",
    "log_endpoint_relative_difference", "raw_local_neighborhood_json",
]


class SmoothingDiagnosticError(RuntimeError):
    """Raised when the immutable cache cannot satisfy the diagnostic contract."""


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(item) for item in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(_json_safe(value), indent=2, sort_keys=True) + "\n")


class _ScalarAccumulator:
    """Streaming finite scalar statistics with constant retained state."""

    def __init__(self) -> None:
        self.count = 0
        self.minimum = math.inf
        self.maximum = -math.inf
        self.total = 0.0

    def add(self, values: np.ndarray | float) -> None:
        finite = np.asarray(values, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        if finite.size == 0:
            return
        self.count += int(finite.size)
        self.minimum = min(self.minimum, float(np.min(finite)))
        self.maximum = max(self.maximum, float(np.max(finite)))
        self.total += float(np.sum(finite, dtype=np.float64))

    def summary(self) -> dict[str, float | int | None]:
        if self.count == 0:
            return {"count": 0, "min": None, "max": None, "mean": None, "max_abs": None}
        return {
            "count": int(self.count), "min": float(self.minimum), "max": float(self.maximum),
            "mean": float(self.total / self.count),
            "max_abs": float(max(abs(self.minimum), abs(self.maximum))),
        }


def _neighbourhood(raw: np.ndarray, start: int, offending_column: int) -> str:
    """Return a deterministic, compact raw-value neighbourhood as JSON."""
    if offending_column < 0:
        return "[]"
    position = offending_column - start
    lo = max(0, position - NEIGHBOUR_RADIUS)
    hi = min(raw.size, position + NEIGHBOUR_RADIUS + 1)
    records = [
        {"column": int(start + column), "raw_value": float(raw[column])}
        for column in range(lo, hi)
    ]
    return json.dumps(records, separators=(",", ":"), sort_keys=True)


def _smooth_segment(segment: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    if segment.size < SMOOTH_WINDOW:
        return None, None
    linear = np.asarray(
        savgol_filter(segment, SMOOTH_WINDOW, SMOOTH_POLYORDER, mode="nearest"),
        dtype=np.float64,
    )
    log = np.asarray(
        np.exp(savgol_filter(np.log(segment), SMOOTH_WINDOW, SMOOTH_POLYORDER, mode="nearest")),
        dtype=np.float64,
    )
    return linear, log


def _triangular_smooth(segment: np.ndarray) -> np.ndarray:
    """Apply the positivity-preserving [1,2,3,2,1]/9 comparator."""
    padded = np.pad(segment, (2, 2), mode="edge")
    return np.asarray(np.convolve(padded, TRIANGULAR_KERNEL, mode="valid"), dtype=np.float64)


class _RateSample:
    """Deterministic bounded sample for cache-wide pressure-rate summaries."""

    def __init__(self, cap: int = RATE_SAMPLE_CAP) -> None:
        self.cap = int(cap)
        self.values: list[float] = []
        self.seen = 0

    def add(self, values: np.ndarray) -> None:
        finite = np.asarray(values, dtype=np.float64)
        finite = finite[np.isfinite(finite)]
        self.seen += int(finite.size)
        if finite.size == 0 or len(self.values) >= self.cap:
            return
        remaining = self.cap - len(self.values)
        take = min(remaining, finite.size)
        positions = np.linspace(0, finite.size - 1, take, dtype=np.int64)
        self.values.extend(finite[positions].tolist())

    def summary(self) -> dict[str, Any]:
        values = np.asarray(self.values, dtype=np.float64)
        if values.size == 0:
            quantiles = [None] * 5
        else:
            quantiles = np.quantile(values, [0.01, 0.05, 0.50, 0.95, 0.99]).tolist()
        return {
            "finite_pair_count": int(self.seen),
            "sample_count": int(values.size),
            "sample_cap": int(self.cap),
            "quantile_method": "deterministic evenly spaced chunk sample",
            "q01": quantiles[0], "q05": quantiles[1], "q50": quantiles[2],
            "q95": quantiles[3], "q99": quantiles[4],
        }


def _pressure_rate(values: np.ndarray, time_values: np.ndarray) -> np.ndarray:
    """Return a_p = log(p[t+1]/p[t]) / dt for valid positive adjacent pairs."""
    out = np.full(max(0, values.size - 1), np.nan, dtype=np.float64)
    positive = (values[:-1] > 0) & (values[1:] > 0) & np.isfinite(values[:-1]) & np.isfinite(values[1:])
    dt = np.diff(time_values)
    valid = positive & np.isfinite(dt) & (dt > 0)
    out[valid] = np.log(values[1:][valid] / values[:-1][valid]) / dt[valid]
    return out


def _rate_summary_with_tail_differences(samples: dict[str, _RateSample]) -> dict[str, Any]:
    raw = samples["unsmoothed"].summary()
    result: dict[str, Any] = {"quantile_definition": "a_p = log(p[t+1]/p[t]) / dt", "methods": {"unsmoothed": raw}}
    for name, sample in samples.items():
        if name == "unsmoothed":
            continue
        current = sample.summary()
        for quantile in ("q01", "q05", "q50", "q95", "q99"):
            current[f"{quantile}_minus_unsmoothed"] = (
                None if current[quantile] is None or raw[quantile] is None
                else float(current[quantile] - raw[quantile])
            )
        current["lower_tail_difference"] = current["q01_minus_unsmoothed"]
        current["upper_tail_difference"] = current["q99_minus_unsmoothed"]
        result["methods"][name] = current
    return result


def _first_offending(values: np.ndarray, raw: np.ndarray, start: int, *, output_indices: np.ndarray) -> tuple[int, int, float | None, float | None]:
    bad = ~np.isfinite(values) | (values <= 0)
    positions = np.flatnonzero(bad)
    if positions.size == 0:
        return -1, -1, None, None
    position = int(positions[0])
    column = start + position
    raw_value = float(raw[position])
    value = float(values[position])
    return column, int(output_indices[column]), raw_value, value


def diagnose_pressure_smoothing(
    cache: Path,
    output_dir: Path,
    *,
    row_chunk: int = 4096,
    expected_trim_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
    expected_no_positive_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
    expected_single_record_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
) -> dict[str, Any]:
    """Compare unsmoothed, linear-SG, and log-SG treated pressure histories."""
    cache = Path(cache).resolve()
    output_dir = Path(output_dir).resolve()
    if not cache.is_file() or cache.is_symlink():
        raise SmoothingDiagnosticError(f"cache must be a regular file: {cache}")
    if row_chunk <= 0:
        raise SmoothingDiagnosticError("row_chunk must be positive")
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise SmoothingDiagnosticError(f"refusing to overwrite non-empty output directory: {output_dir}")
    else:
        output_dir.mkdir(parents=True)

    affected: list[dict[str, Any]] = []
    endpoint_linear = _ScalarAccumulator()
    endpoint_log = _ScalarAccumulator()
    endpoint_triangular = _ScalarAccumulator()
    all_linear_ratios = _ScalarAccumulator()
    all_log_ratios = _ScalarAccumulator()
    all_triangular_ratios = _ScalarAccumulator()
    min_linear_values = _ScalarAccumulator()
    min_log_values = _ScalarAccumulator()
    min_triangular_values = _ScalarAccumulator()
    rate_samples = {name: _RateSample() for name in ("unsmoothed", "linear_sg", "log_sg", "triangular")}
    counts = {
        "cache_rows": 0, "active_rows": 0, "excluded_rows": 0, "short_rows": 0,
        "smoothed_rows": 0, "linear_nonpositive_output_count": 0,
        "linear_nonfinite_output_count": 0, "log_nonpositive_output_count": 0,
        "log_nonfinite_output_count": 0,
    }

    with h5py.File(cache, "r") as h5:
        try:
            workflow._validate_completed_cache(h5)
            plan = workflow.build_pressure_treatment_plan(
                h5,
                expected_trim_rows=expected_trim_rows,
                expected_no_positive_rows=expected_no_positive_rows,
                expected_single_record_rows=expected_single_record_rows,
                row_chunk=row_chunk,
            )
        except workflow.WorkflowError as exc:
            raise SmoothingDiagnosticError(str(exc)) from exc

        n, nt = h5["pressure"].shape
        ids = np.asarray(h5["endpoint_ids"][:], dtype=np.int64)
        times = np.asarray(h5["times"][:], dtype=np.float64)
        outputs = np.asarray(h5["output_indices"][:], dtype=np.int64)
        counts["cache_rows"] = int(n)
        counts["excluded_rows"] = int(len(plan["excluded_rows"]))
        counts["active_rows"] = int(np.count_nonzero(plan["active_mask"]))
        for start in range(0, n, row_chunk):
            stop = min(start + row_chunk, n)
            raw = workflow._raw_cache_chunk(h5, start, stop)
            treated, treatment_metadata = workflow.apply_pressure_treatment(
                raw, row_offset=start, plan=plan
            )
            treated_pressure = np.asarray(treated["pressure"], dtype=np.float64)
            active_rows = np.asarray(treatment_metadata["active_cache_rows"], dtype=np.int64)
            trim_flags = np.asarray(treatment_metadata["trim_affected"], dtype=bool)
            for local, row in enumerate(active_rows):
                row_values = treated_pressure[local]
                finite_columns = np.flatnonzero(np.isfinite(row_values))
                if finite_columns.size == 0:
                    raise SmoothingDiagnosticError(f"active row {row} has no treated pressure values")
                first = int(finite_columns[0])
                raw_segment = np.asarray(row_values[first:], dtype=np.float64)
                if not np.all(np.isfinite(raw_segment)) or np.any(raw_segment <= 0):
                    raise SmoothingDiagnosticError(f"active row {row} has non-positive/nonfinite treated values")
                linear, log = _smooth_segment(raw_segment)
                if linear is None or log is None:
                    counts["short_rows"] += 1
                    continue
                counts["smoothed_rows"] += 1
                triangular = _triangular_smooth(raw_segment)
                linear_bad = ~np.isfinite(linear) | (linear <= 0)
                log_bad = ~np.isfinite(log) | (log <= 0)
                counts["linear_nonpositive_output_count"] += int(np.count_nonzero(np.isfinite(linear) & (linear <= 0)))
                counts["linear_nonfinite_output_count"] += int(np.count_nonzero(~np.isfinite(linear)))
                counts["log_nonpositive_output_count"] += int(np.count_nonzero(np.isfinite(log) & (log <= 0)))
                counts["log_nonfinite_output_count"] += int(np.count_nonzero(~np.isfinite(log)))
                finite_linear = linear[np.isfinite(linear)]
                finite_log = log[np.isfinite(log)]
                min_linear_values.add(finite_linear)
                min_log_values.add(finite_log)
                min_triangular_values.add(triangular)
                linear_ratio = linear / raw_segment
                log_ratio = log / raw_segment
                triangular_ratio = triangular / raw_segment
                all_linear_ratios.add(linear_ratio)
                all_log_ratios.add(log_ratio)
                all_triangular_ratios.add(triangular_ratio)
                rate_times = times[first:first + raw_segment.size]
                for name, values in (("unsmoothed", raw_segment), ("linear_sg", linear), ("log_sg", log), ("triangular", triangular)):
                    rate_samples[name].add(_pressure_rate(values, rate_times))
                endpoint_col = nt - 1
                endpoint_raw = float(raw_segment[-1])
                endpoint_linear_value = float(linear[-1])
                endpoint_log_value = float(log[-1])
                endpoint_linear.add(endpoint_linear_value / endpoint_raw - 1.0)
                endpoint_log.add(endpoint_log_value / endpoint_raw - 1.0)
                endpoint_triangular.add(float(triangular[-1] / endpoint_raw - 1.0))
                if np.any(linear_bad) or np.any(log_bad):
                    linear_col, linear_output, linear_raw, linear_value = _first_offending(
                        linear, raw_segment, first, output_indices=outputs
                    )
                    log_col, log_output, log_raw, log_value = _first_offending(
                        log, raw_segment, first, output_indices=outputs
                    )
                    all_bad_cols = [col for col in (linear_col, log_col) if col >= 0]
                    neighbourhood_col = min(all_bad_cols) if all_bad_cols else -1
                    affected.append({
                        "cache_row": int(row), "physical_id": int(ids[row]),
                        "first_present_column": first,
                        "first_present_output_index": int(outputs[first]),
                        "first_present_time": float(times[first]),
                        "endpoint_column": endpoint_col,
                        "endpoint_output_index": int(outputs[endpoint_col]),
                        "endpoint_time": float(times[endpoint_col]),
                        "present_count": int(raw_segment.size), "trim_affected": bool(trim_flags[local]),
                        "linear_first_offending_column": linear_col,
                        "linear_first_offending_output_index": linear_output,
                        "linear_first_offending_raw_value": linear_raw,
                        "linear_first_offending_value": linear_value,
                        "log_first_offending_column": log_col,
                        "log_first_offending_output_index": log_output,
                        "log_first_offending_raw_value": log_raw,
                        "log_first_offending_value": log_value,
                        "linear_nonpositive_count": int(np.count_nonzero(np.isfinite(linear) & (linear <= 0))),
                        "linear_nonfinite_count": int(np.count_nonzero(~np.isfinite(linear))),
                        "log_nonpositive_count": int(np.count_nonzero(np.isfinite(log) & (log <= 0))),
                        "log_nonfinite_count": int(np.count_nonzero(~np.isfinite(log))),
                        "min_linear_value": None if finite_linear.size == 0 else float(np.min(finite_linear)),
                        "min_log_value": None if finite_log.size == 0 else float(np.min(finite_log)),
                        "min_linear_to_raw_ratio": float(np.nanmin(linear_ratio)),
                        "min_log_to_raw_ratio": float(np.nanmin(log_ratio)),
                        "linear_endpoint_relative_difference": float(endpoint_linear_value / endpoint_raw - 1.0),
                        "log_endpoint_relative_difference": float(endpoint_log_value / endpoint_raw - 1.0),
                        "raw_local_neighborhood_json": _neighbourhood(raw_segment, first, neighbourhood_col),
                    })

    summary: dict[str, Any] = {
        "status": "diagnostic_complete",
        "cache_identity": workflow._cache_identity(cache),
        "cache_shape": [int(n), int(nt)],
        "smoothing_contract": {
            "algorithm": "Savitzky-Golay", "window": SMOOTH_WINDOW,
            "polyorder": SMOOTH_POLYORDER, "mode": "nearest",
            "linear_domain": "raw treated positive pressure",
            "log_domain": "natural_log(raw treated positive pressure)",
            "pressure_floor": False, "interpolation": False,
        },
        "treatment_identity_sha256": str(plan["identity_sha256"]),
        "row_chunk": int(row_chunk),
        "counts": counts,
        "affected_row_count": len(affected),
        "linear_min_value": min_linear_values.summary()["min"],
        "log_min_value": min_log_values.summary()["min"],
        "linear_min_smoothed_to_raw_ratio": all_linear_ratios.summary()["min"],
        "log_min_smoothed_to_raw_ratio": all_log_ratios.summary()["min"],
        "triangular_smoothing": {
            "kernel": [1, 2, 3, 2, 1], "normalization": 9,
            "min_value": min_triangular_values.summary()["min"],
            "min_smoothed_to_raw_ratio": all_triangular_ratios.summary()["min"],
            "nonpositive_output_count": 0,
            "nonfinite_output_count": 0,
            "endpoint_relative_difference": endpoint_triangular.summary(),
        },
        "endpoint_relative_difference": {
            "linear": endpoint_linear.summary(),
            "log": endpoint_log.summary(),
        },
        "adiabatic_pressure_rate_proxy": _rate_summary_with_tail_differences(rate_samples),
        "excluded_cache_rows": np.asarray(plan["excluded_rows"], dtype=np.int64).tolist(),
        "active_cache_rows": int(np.count_nonzero(plan["active_mask"])),
        "short_smoothing_rows": counts["short_rows"],
        "smoothed_rows": counts["smoothed_rows"],
        "output_csv": "pressure_smoothing_affected_rows.csv",
    }
    with (output_dir / "pressure_smoothing_affected_rows.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(affected)
    _write_json(output_dir / "pressure_smoothing_diagnostic.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--row-chunk", type=int, default=4096)
    parser.add_argument("--expected-trim-rows", type=int, default=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"])
    parser.add_argument("--expected-no-positive-rows", type=int, default=workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"])
    parser.add_argument("--expected-single-record-rows", type=int, default=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"])
    args = parser.parse_args()
    summary = diagnose_pressure_smoothing(
        args.cache, args.output_dir, row_chunk=args.row_chunk,
        expected_trim_rows=args.expected_trim_rows,
        expected_no_positive_rows=args.expected_no_positive_rows,
        expected_single_record_rows=args.expected_single_record_rows,
    )
    print(f"status={summary['status']}")
    print(f"active_rows={summary['counts']['active_rows']} smoothed_rows={summary['counts']['smoothed_rows']}")
    print(f"affected_rows={summary['affected_row_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
