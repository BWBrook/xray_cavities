#!/usr/bin/env python3
"""Actual-PRAiSE pressure-method sensitivity diagnostic for Goal 049.

The diagnostic applies the approved fail-closed pressure treatment, selects a
deterministic 4096-row sample from the immutable cache, then compares actual
PRAiSE endpoint emissivities under unsmoothed and log-domain Savitzky-Golay
pressure histories.  It does not floor, clip, censor, or interpolate pressure.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np
from plutokore.radio.praise import get_gamma_numba
from scipy.signal import savgol_filter

from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.g_lo_radio_method_value import (
    LOG_SAVGOL_POLYORDER,
    LOG_SAVGOL_WINDOW,
    calculate_praise_pair,
)


SAMPLE_SIZE = 4096
FIXED_SEED = "goal049-pressure-method-value-v1"
EXTREME_COUNT_PER_TAIL = 16
FREQUENCIES_GHZ = (0.15, 1.4)
GATES = {
    "max_abs_aggregate_difference_dex": 0.10,
    "max_abs_spectral_index_difference": 0.10,
    "require_same_full_vs_lossless_direction": True,
    "require_full_not_above_adiabatic": True,
    "max_top_one_percent_discrepancy_fraction": 0.50,
}
ORDERING_RTOL = 1e-10
ORDERING_ULP_MULTIPLIER = 8.0
SELECTION_FIELDS = [
    "sample_index", "cache_row", "physical_id", "selection_reason", "stratum",
    "inclusion_probability", "analysis_weight", "affected_linear_sg",
    "trim_affected", "short_history", "history_length", "injection_age",
    "pressure_dynamic_range_log10", "shock_age", "shock_relative_state",
    "log_endpoint_relative_difference", "min_log_to_raw_ratio",
]
GAMMA_FALLBACK_RECORD_FIELDS = [
    "pressure_mode", "loss_branch", "sample_index", "cache_row",
    "physical_id", "frequency_GHz", "fallback_event_count", "shock_index",
    "history_columns", "trim_affected", "short_history", "selection_reason",
    "stratum",
]
GAMMA_FALLBACK_SUMMARY_FIELDS = [
    "pressure_mode", "loss_branch", "selected_particle_count",
    "fallback_event_count", "affected_particle_frequency_count",
    "affected_particle_count", "replay_verified", "gate_passed",
    "fallback_definition", "audit_error",
]
NONFINITE_SUMMARY_FIELDS = [
    "pressure_mode", "loss_branch", "selected_particle_count",
    "finite_value_count", "nonfinite_value_count", "nan_count",
    "positive_inf_count", "negative_inf_count",
    "proven_full_loss_cutoff_count", "unresolved_nonfinite_count",
]
NONFINITE_RECORD_FIELDS = [
    "pressure_mode", "loss_branch", "start_index", "dense_row",
    "physical_id", "frequency_GHz", "output_class",
    "matched_lossless_output_class", "replay_verified",
    "finite_inputs_dynamics", "shock_assignment_valid", "shock_index",
    "no_emission_index", "no_emission", "endpoint_pressure_Pa",
    "injection_pressure_Pa", "endpoint_tracer", "current_lorentz",
    "injection_lorentz", "classification",
]


class PressureMethodDiagnosticError(RuntimeError):
    """Raised when the diagnostic evidence cannot satisfy its contract."""


def _value_class(value: float) -> str:
    if np.isnan(value):
        return "nan"
    if np.isposinf(value):
        return "+inf"
    if np.isneginf(value):
        return "-inf"
    return "finite"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
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


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_emissivity_checkpoint(
    path: Path,
    result: Mapping[str, Any],
) -> None:
    ids = np.asarray(result["ids"], dtype=np.int64)
    arrays = {
        branch: np.asarray(
            getattr(result[branch], "value", result[branch]),
            dtype=np.float64,
        )
        for branch in ("full", "adiabatic", "none")
    }
    expected = (len(ids), len(FREQUENCIES_GHZ))
    if (
        len(ids) == 0
        or ids.ndim != 1
        or np.unique(ids).size != len(ids)
        or any(values.shape != expected for values in arrays.values())
    ):
        raise PressureMethodDiagnosticError(
            "emissivity checkpoint requires non-empty matched branch shapes"
        )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as handle:
        np.savez_compressed(
            handle,
            physical_ids=ids,
            frequencies_GHz=np.asarray(FREQUENCIES_GHZ, dtype=np.float64),
            full=arrays["full"],
            adiabatic=arrays["adiabatic"],
            none=arrays["none"],
        )
    temporary.replace(path)


def _read_affected_rows(path: Path) -> dict[int, dict[str, Any]]:
    required = {
        "cache_row", "physical_id", "log_endpoint_relative_difference",
        "min_log_to_raw_ratio",
    }
    result: dict[int, dict[str, Any]] = {}
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise PressureMethodDiagnosticError(
                f"affected-row CSV is missing columns: {sorted(required - set(reader.fieldnames or []))}"
            )
        for raw in reader:
            row = int(raw["cache_row"])
            if row in result:
                raise PressureMethodDiagnosticError("affected-row CSV has duplicate cache rows")
            result[row] = {
                "physical_id": int(raw["physical_id"]),
                "log_endpoint_relative_difference": float(
                    raw["log_endpoint_relative_difference"]
                ),
                "min_log_to_raw_ratio": float(raw["min_log_to_raw_ratio"]),
            }
    if not result:
        raise PressureMethodDiagnosticError("affected-row CSV is empty")
    return result


def _nonfinite_evidence(
    results: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Build deterministic branch-level evidence without altering raw values."""
    summaries: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    branch_counts: dict[str, dict[str, int]] = {}
    coverage_errors: list[str] = []
    for mode in ("unsmoothed", "log_savgol"):
        result = results[mode]
        all_records = list(result.get("nonfinite_diagnostics", {}).get("records", []))
        expected_records: dict[tuple[str, int, float], str] = {}
        for branch in ("full", "adiabatic", "none"):
            values_for_coverage = np.asarray(
                getattr(result[branch], "value", result[branch]),
                dtype=np.float64,
            )
            ids_for_coverage = np.asarray(result["ids"], dtype=np.int64)
            for row_index, physical_id in enumerate(ids_for_coverage):
                for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                    expected_records[(branch, int(physical_id), float(frequency))] = (
                        _value_class(values_for_coverage[row_index, frequency_index])
                    )
        observed_records: dict[tuple[str, int, float], list[str]] = defaultdict(list)
        for record in all_records:
            try:
                key = (
                    str(record.get("loss_branch")),
                    int(record.get("physical_id")),
                    float(record.get("frequency_GHz")),
                )
            except (TypeError, ValueError):
                coverage_errors.append(f"{mode}:malformed_forensic_record")
                continue
            observed_records[key].append(str(record.get("output_class")))
        for key in sorted(expected_records):
            observed = observed_records.get(key, [])
            expected_class = expected_records[key]
            if len(observed) != 1:
                coverage_errors.append(
                    f"{mode}:coverage:{key[0]}:{key[1]}:{key[2]}:"
                    f"expected_one_record_observed_{len(observed)}"
                )
            elif observed[0] != expected_class:
                coverage_errors.append(
                    f"{mode}:class:{key[0]}:{key[1]}:{key[2]}:"
                    f"expected_{expected_class}_observed_{observed[0]}"
                )
        for key in sorted(set(observed_records) - set(expected_records)):
            coverage_errors.append(
                f"{mode}:unexpected:{key[0]}:{key[1]}:{key[2]}"
            )
        records.extend(
            row for row in all_records if row.get("output_class") != "finite"
        )
        for branch in ("full", "adiabatic", "none"):
            values = np.asarray(
                getattr(result[branch], "value", result[branch]),
                dtype=np.float64,
            )
            classes = np.vectorize(_value_class)(values)
            finite_count = int(np.count_nonzero(classes == "finite"))
            nan_count = int(np.count_nonzero(classes == "nan"))
            posinf_count = int(np.count_nonzero(classes == "+inf"))
            neginf_count = int(np.count_nonzero(classes == "-inf"))
            nonfinite_count = nan_count + posinf_count + neginf_count
            branch_key = f"{mode}/{branch}"
            branch_counts[branch_key] = {
                "finite_value_count": finite_count,
                "nonfinite_value_count": nonfinite_count,
                "nan_count": nan_count,
                "positive_inf_count": posinf_count,
                "negative_inf_count": neginf_count,
            }
            branch_records = [
                row for row in all_records
                if row.get("loss_branch") == branch
                and row.get("output_class") != "finite"
            ]
            summaries.append({
                "pressure_mode": mode,
                "loss_branch": branch,
                "selected_particle_count": int(values.shape[0]),
                **branch_counts[branch_key],
                "proven_full_loss_cutoff_count": int(sum(
                    row.get("classification") == "proven_full_loss_cutoff"
                    for row in branch_records
                )),
                "unresolved_nonfinite_count": int(sum(
                    row.get("classification") == "unresolved_nonfinite"
                    for row in branch_records
                )),
            })
    summary = {
        "branch_count": len(summaries),
        "nonfinite_branch_count": int(sum(
            row["nonfinite_value_count"] > 0 for row in summaries
        )),
        "nonfinite_record_count": len(records),
        "finite_only_comparison_allowed": not any(
            row["nonfinite_value_count"] > 0 for row in summaries
        ),
        "coverage_valid": not coverage_errors,
        "coverage_error_count": len(coverage_errors),
        "coverage_errors": coverage_errors,
    }
    return summaries, records, summary


def _quantile_bin(values: np.ndarray, *, bins: int = 4) -> np.ndarray:
    finite = np.asarray(values, dtype=np.float64)
    if finite.ndim != 1 or not np.all(np.isfinite(finite)):
        raise PressureMethodDiagnosticError("stratification features must be finite")
    edges = np.unique(np.quantile(finite, np.linspace(0, 1, bins + 1)[1:-1]))
    return np.searchsorted(edges, finite, side="right").astype(np.int16)


def _hash_order(seed: str, row: int, physical_id: int) -> str:
    return hashlib.sha256(f"{seed}:{row}:{physical_id}".encode()).hexdigest()


def _feature_table(
    h5: h5py.File,
    plan: Mapping[str, Any],
    affected: Mapping[int, Mapping[str, Any]],
    *,
    row_chunk: int,
) -> dict[str, np.ndarray]:
    n, nt = h5["pressure"].shape
    ids = np.asarray(h5["endpoint_ids"][:], dtype=np.int64)
    times = np.asarray(h5["times"][:], dtype=np.float64)
    tinj = np.asarray(h5["tinj"][:], dtype=np.float64)
    active = np.asarray(plan["active_mask"], dtype=bool)
    trim_columns = np.asarray(plan["trim_columns"], dtype=np.int64)
    history_length = np.zeros(n, dtype=np.int32)
    dynamic_range = np.full(n, np.nan, dtype=np.float64)
    shock_age = np.full(n, np.nan, dtype=np.float64)
    log_endpoint = np.full(n, np.nan, dtype=np.float64)
    min_log_ratio = np.full(n, np.nan, dtype=np.float64)
    for start in range(0, n, row_chunk):
        stop = min(start + row_chunk, n)
        presence = np.asarray(h5["presence"][start:stop, :], dtype=bool)
        pressure = np.asarray(h5["pressure"][start:stop, :], dtype=np.float64)
        last = np.asarray(h5["last_shock_time"][start:stop, ...], dtype=np.float64)
        if last.ndim == 3:
            last = last[:, :, 0]
        for local in range(stop - start):
            row = start + local
            if not active[row]:
                continue
            first = int(np.argmax(presence[local]))
            if trim_columns[row] >= 0:
                first = int(trim_columns[row] + 1)
            segment = pressure[local, first:]
            if segment.size == 0 or not np.all(np.isfinite(segment)) or np.any(segment <= 0):
                raise PressureMethodDiagnosticError(
                    f"treated pressure segment is invalid at cache row {row}"
                )
            history_length[row] = int(segment.size)
            dynamic_range[row] = float(np.log10(np.max(segment) / np.min(segment)))
            shock_age[row] = float(times[-1] - last[local, -1])
            if segment.size < LOG_SAVGOL_WINDOW:
                log_smoothed = segment
            else:
                log_smoothed = np.exp(
                    savgol_filter(
                        np.log(segment),
                        LOG_SAVGOL_WINDOW,
                        LOG_SAVGOL_POLYORDER,
                        mode="nearest",
                    )
                )
            log_endpoint[row] = float(
                (log_smoothed[-1] - segment[-1]) / segment[-1]
            )
            min_log_ratio[row] = float(np.min(log_smoothed / segment))
    active_rows = np.flatnonzero(active)
    if np.any(history_length[active_rows] <= 0):
        raise PressureMethodDiagnosticError("active history length is not positive")
    if not np.all(np.isfinite(dynamic_range[active_rows])):
        raise PressureMethodDiagnosticError("pressure dynamic range is non-finite")
    if not np.all(np.isfinite(shock_age[active_rows])):
        raise PressureMethodDiagnosticError("shock age is non-finite")
    injection_age = times[-1] - tinj
    if np.any(~np.isfinite(injection_age[active_rows])) or np.any(injection_age[active_rows] < 0):
        raise PressureMethodDiagnosticError("injection age is invalid")
    affected_flag = np.zeros(n, dtype=bool)
    for row, record in affected.items():
        if row < 0 or row >= n or not active[row]:
            raise PressureMethodDiagnosticError(
                f"affected-row CSV references inactive/out-of-range row {row}"
            )
        if ids[row] != record["physical_id"]:
            raise PressureMethodDiagnosticError(
                f"affected-row physical ID mismatch at cache row {row}"
            )
        affected_flag[row] = True
    if not np.all(np.isfinite(log_endpoint[active_rows])):
        raise PressureMethodDiagnosticError(
            "full-cache log-SG endpoint perturbation is non-finite"
        )
    if (
        not np.all(np.isfinite(min_log_ratio[active_rows]))
        or np.any(min_log_ratio[active_rows] <= 0)
    ):
        raise PressureMethodDiagnosticError(
            "full-cache log-SG/raw ratio is non-finite or non-positive"
        )
    return {
        "physical_id": ids,
        "active": active,
        "trim": np.asarray(plan["kinds"], dtype=np.int8) == 1,
        "history_length": history_length,
        "injection_age": injection_age,
        "dynamic_range": dynamic_range,
        "shock_age": shock_age,
        "short": active & (history_length < 5),
        "affected": affected_flag,
        "log_endpoint": log_endpoint,
        "min_log_ratio": min_log_ratio,
    }


def construct_deterministic_sample(
    h5: h5py.File,
    plan: Mapping[str, Any],
    affected_rows: Mapping[int, Mapping[str, Any]],
    *,
    sample_size: int = SAMPLE_SIZE,
    seed: str = FIXED_SEED,
    row_chunk: int = 512,
    extreme_count_per_tail: int = EXTREME_COUNT_PER_TAIL,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    """Build a deterministic certainty-plus-stratified active-row sample."""
    if sample_size <= 0 or extreme_count_per_tail <= 0:
        raise PressureMethodDiagnosticError("sample size and extreme count must be positive")
    features = _feature_table(h5, plan, affected_rows, row_chunk=row_chunk)
    active_rows = np.flatnonzero(features["active"])
    target = min(sample_size, len(active_rows))
    reasons: dict[int, set[str]] = defaultdict(set)
    for row in np.flatnonzero(features["short"]):
        reasons[int(row)].add("all_short_histories")
    affected = np.flatnonzero(features["affected"])
    extrema_universe = active_rows
    by_endpoint = sorted(
        extrema_universe,
        key=lambda row: (-abs(features["log_endpoint"][row]), int(row)),
    )[:extreme_count_per_tail]
    by_ratio = sorted(
        extrema_universe,
        key=lambda row: (features["min_log_ratio"][row], int(row)),
    )[:extreme_count_per_tail]
    for row in by_endpoint:
        reasons[int(row)].add("extreme_abs_log_endpoint_perturbation")
    for row in by_ratio:
        reasons[int(row)].add("extreme_min_log_raw_ratio")
    if len(reasons) > target:
        raise PressureMethodDiagnosticError(
            "mandatory short/extreme rows exceed the requested sample size"
        )

    selected_features = active_rows
    length_bin = _quantile_bin(features["history_length"][selected_features])
    injection_bin = _quantile_bin(features["injection_age"][selected_features])
    range_bin = _quantile_bin(features["dynamic_range"][selected_features])
    post_shock = features["shock_age"][selected_features] < features["injection_age"][selected_features]
    post_shock_age = features["shock_age"][selected_features][post_shock]
    shock_cut = float(np.median(post_shock_age)) if post_shock_age.size else 0.0
    strata: dict[int, str] = {}
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row_value in enumerate(selected_features):
        row = int(row_value)
        if not post_shock[index]:
            shock_state = "pre_or_at_injection"
        elif features["shock_age"][row] <= shock_cut:
            shock_state = "post_injection_recent"
        else:
            shock_state = "post_injection_older"
        stratum = (
            f"affected={int(features['affected'][row])}|trim={int(features['trim'][row])}"
            f"|length_q={int(length_bin[index])}|injection_q={int(injection_bin[index])}"
            f"|range_q={int(range_bin[index])}|shock={shock_state}"
        )
        strata[row] = stratum
        groups[stratum].append(row)

    mandatory = set(reasons)
    remaining_capacity = target - len(mandatory)
    eligible: dict[str, list[int]] = {}
    for stratum, rows in groups.items():
        eligible[stratum] = sorted(
            (row for row in rows if row not in mandatory),
            key=lambda row: _hash_order(seed, row, int(features["physical_id"][row])),
        )
    allocation = {stratum: 0 for stratum in groups}
    nonempty = [stratum for stratum, rows in eligible.items() if rows]
    if remaining_capacity < len(nonempty):
        ordered = sorted(
            nonempty,
            key=lambda value: hashlib.sha256(f"{seed}:{value}".encode()).hexdigest(),
        )
        for stratum in ordered[:remaining_capacity]:
            allocation[stratum] = 1
    else:
        for stratum in nonempty:
            allocation[stratum] = 1
        left = remaining_capacity - len(nonempty)
        while left > 0:
            candidates = [
                stratum for stratum in nonempty
                if allocation[stratum] < len(eligible[stratum])
            ]
            if not candidates:
                break
            stratum = max(
                candidates,
                key=lambda value: (
                    len(eligible[value]) / (allocation[value] + 1),
                    hashlib.sha256(f"{seed}:{value}".encode()).hexdigest(),
                ),
            )
            allocation[stratum] += 1
            left -= 1
    selected = set(mandatory)
    for stratum, count in allocation.items():
        for row in eligible[stratum][:count]:
            selected.add(row)
            reasons[row].add("deterministic_stratified_hash_sample")
    if len(selected) != target:
        raise PressureMethodDiagnosticError(
            f"deterministic selection produced {len(selected)} rows, expected {target}"
        )

    records: list[dict[str, Any]] = []
    for sample_index, row in enumerate(sorted(selected)):
        stratum = strata[row]
        mandatory_row = "deterministic_stratified_hash_sample" not in reasons[row]
        eligible_count = len(eligible[stratum])
        selected_count = allocation[stratum]
        if mandatory_row:
            probability, weight = 1.0, 1.0
        else:
            if selected_count <= 0 or eligible_count <= 0:
                raise PressureMethodDiagnosticError("invalid stratum allocation")
            probability = selected_count / eligible_count
            weight = 1.0 / probability
        records.append({
            "sample_index": sample_index,
            "cache_row": row,
            "physical_id": int(features["physical_id"][row]),
            "selection_reason": ";".join(sorted(reasons[row])),
            "stratum": stratum,
            "inclusion_probability": probability,
            "analysis_weight": weight,
            "affected_linear_sg": bool(features["affected"][row]),
            "trim_affected": bool(features["trim"][row]),
            "short_history": bool(features["short"][row]),
            "history_length": int(features["history_length"][row]),
            "injection_age": float(features["injection_age"][row]),
            "pressure_dynamic_range_log10": float(features["dynamic_range"][row]),
            "shock_age": float(features["shock_age"][row]),
            "shock_relative_state": stratum.rsplit("shock=", 1)[1],
            "log_endpoint_relative_difference": float(features["log_endpoint"][row]),
            "min_log_to_raw_ratio": float(features["min_log_ratio"][row]),
        })
    metadata = {
        "sample_size_requested": int(sample_size),
        "sample_size_selected": int(target),
        "active_population_size": int(len(active_rows)),
        "fixed_seed": seed,
        "ordering": "sha256(seed:cache_row:physical_id) within predeclared strata",
        "mandatory_short_count": int(np.count_nonzero(features["short"])),
        "mandatory_selected_count": int(len(mandatory)),
        "stratum_count": int(len(groups)),
        "affected_population_count": int(len(affected)),
        "log_savgol_extrema_universe": "all active treated cache rows",
        "weighting": (
            "certainty rows weight 1; remaining rows use inverse within-stratum "
            "hash-sample fraction after certainty-row removal"
        ),
        "scope": "sample evidence; not a full-population estimate without sampling assumptions",
    }
    return np.asarray(sorted(selected), dtype=np.int64), records, metadata


def _read_treated_sample(
    h5: h5py.File,
    rows: np.ndarray,
    plan: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    raw = {
        "physical_ids": np.asarray(h5["endpoint_ids"][rows], dtype=np.int64),
        "time": np.asarray(h5["times"][:], dtype=np.float64),
        "pressure": np.asarray(h5["pressure"][rows, :], dtype=np.float64),
        "density": np.asarray(h5["density"][rows, :], dtype=np.float64),
        "tracer": np.asarray(h5["tracer"][rows, :], dtype=np.float64),
        "last_shock_time": np.asarray(h5["last_shock_time"][rows, ...], dtype=np.float64),
        "position": np.asarray(h5["position"][rows, :], dtype=np.float64),
        "velocity": np.asarray(h5["velocity"][rows, :], dtype=np.float64),
        "tinj": np.asarray(h5["tinj"][rows], dtype=np.float64),
    }
    for local, row in enumerate(rows):
        column = int(plan["trim_columns"][row])
        if column >= 0:
            for field in ("pressure", "density", "tracer", "last_shock_time"):
                raw[field][local, column] = np.nan
    return raw


def _direction(value: float, *, tolerance: float = 1e-12) -> str:
    if value < -tolerance:
        return "full_below_lossless"
    if value > tolerance:
        return "full_above_lossless"
    return "equivalent"


def _full_reference_ordering(
    full: np.ndarray,
    reference: np.ndarray,
    weights: np.ndarray,
    *,
    reference_label: str,
) -> list[dict[str, Any]]:
    """Describe full-evolution ordering without assuming a universal direction."""
    full = np.asarray(full, dtype=np.float64)
    reference = np.asarray(reference, dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    if (
        full.shape != reference.shape
        or full.ndim != 2
        or full.shape[1] != len(FREQUENCIES_GHZ)
        or weights.shape != (full.shape[0],)
        or not np.all(np.isfinite(full))
        or not np.all(np.isfinite(reference))
        or np.any(full < 0)
        or np.any(reference < 0)
        or not np.all(np.isfinite(weights))
        or np.any(weights <= 0)
    ):
        raise PressureMethodDiagnosticError(
            "full/reference ordering requires finite nonnegative (n,2) arrays "
            "and positive finite weights"
        )
    ulp = np.maximum(
        np.abs(np.spacing(full)),
        np.abs(np.spacing(reference)),
    )
    tolerance = (
        np.abs(reference) * ORDERING_RTOL
        + ORDERING_ULP_MULTIPLIER * ulp
    )
    difference = full - reference
    above = difference > tolerance
    below = -difference > tolerance
    equivalent = ~(above | below)
    total_weight = float(np.sum(weights))
    rows: list[dict[str, Any]] = []
    for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
        both_positive = (
            (full[:, frequency_index] > 0)
            & (reference[:, frequency_index] > 0)
        )
        ratio = np.divide(
            full[:, frequency_index],
            reference[:, frequency_index],
            out=np.full(full.shape[0], np.nan, dtype=np.float64),
            where=both_positive,
        )
        finite_ratio = ratio[np.isfinite(ratio)]
        weighted_full = float(np.sum(weights * full[:, frequency_index]))
        weighted_reference = float(
            np.sum(weights * reference[:, frequency_index])
        )
        if weighted_full <= 0 or weighted_reference <= 0:
            raise PressureMethodDiagnosticError(
                "weighted full/reference aggregates must be positive"
            )
        aggregate_ratio = weighted_full / weighted_reference
        aggregate_log_ratio = float(np.log10(aggregate_ratio))
        label = (
            f"full_above_{reference_label}"
            if aggregate_log_ratio > 1e-12
            else (
                f"full_below_{reference_label}"
                if aggregate_log_ratio < -1e-12
                else "equivalent"
            )
        )
        current_above = above[:, frequency_index]
        current_below = below[:, frequency_index]
        current_equivalent = equivalent[:, frequency_index]
        rows.append({
            "frequency_GHz": float(frequency),
            f"full_above_{reference_label}_count": int(
                np.count_nonzero(current_above)
            ),
            f"full_below_{reference_label}_count": int(
                np.count_nonzero(current_below)
            ),
            "equivalent_count": int(np.count_nonzero(current_equivalent)),
            f"full_above_{reference_label}_represented_weight_fraction": float(
                np.sum(weights[current_above]) / total_weight
            ),
            f"full_below_{reference_label}_represented_weight_fraction": float(
                np.sum(weights[current_below]) / total_weight
            ),
            "both_zero_count": int(np.count_nonzero(
                (full[:, frequency_index] == 0)
                & (reference[:, frequency_index] == 0)
            )),
            "full_only_positive_count": int(np.count_nonzero(
                (full[:, frequency_index] > 0)
                & (reference[:, frequency_index] == 0)
            )),
            f"{reference_label}_only_positive_count": int(np.count_nonzero(
                (full[:, frequency_index] == 0)
                & (reference[:, frequency_index] > 0)
            )),
            "both_positive_count": int(np.count_nonzero(both_positive)),
            "positive_ratio_min": (
                float(np.min(finite_ratio)) if finite_ratio.size else None
            ),
            "positive_ratio_q50": (
                float(np.quantile(finite_ratio, 0.50))
                if finite_ratio.size else None
            ),
            "positive_ratio_q95": (
                float(np.quantile(finite_ratio, 0.95))
                if finite_ratio.size else None
            ),
            "positive_ratio_q99": (
                float(np.quantile(finite_ratio, 0.99))
                if finite_ratio.size else None
            ),
            "positive_ratio_max": (
                float(np.max(finite_ratio)) if finite_ratio.size else None
            ),
            "maximum_absolute_difference": float(
                np.max(np.abs(difference[:, frequency_index]))
            ),
            "comparison_absolute_tolerance_max": float(
                np.max(tolerance[:, frequency_index])
            ),
            "comparison_relative_tolerance": ORDERING_RTOL,
            "comparison_ulp_multiplier": ORDERING_ULP_MULTIPLIER,
            "weighted_full_emissivity": weighted_full,
            f"weighted_{reference_label}_emissivity": weighted_reference,
            f"aggregate_full_over_{reference_label}_ratio": aggregate_ratio,
            f"aggregate_log10_full_over_{reference_label}": aggregate_log_ratio,
            "aggregate_direction": label,
        })
    return rows


def summarise_actual_praise_dynamics(
    result: Mapping[str, Any],
    *,
    sample_cap: int = 100_000,
) -> dict[str, Any]:
    """Reduce actual upstream ``ap_arr``/``a2_arr`` outputs without persisting them."""
    groups = result.get("full_info")
    if not isinstance(groups, list) or not groups:
        raise PressureMethodDiagnosticError(
            "actual PRAiSE result is missing grouped full-loss diagnostics"
        )
    summary: dict[str, Any] = {}
    for field in ("ap_arr", "a2_arr"):
        count = 0
        nonfinite = 0
        minimum = math.inf
        maximum = -math.inf
        samples: list[np.ndarray] = []
        per_group_cap = max(1, sample_cap // len(groups))
        for group in groups:
            info = group.get("info")
            if not isinstance(info, Mapping) or field not in info:
                raise PressureMethodDiagnosticError(
                    f"actual PRAiSE full-loss diagnostics are missing {field}"
                )
            values = np.asarray(info[field], dtype=np.float64).ravel()
            finite = values[np.isfinite(values)]
            count += int(finite.size)
            nonfinite += int(values.size - finite.size)
            if finite.size:
                minimum = min(minimum, float(np.min(finite)))
                maximum = max(maximum, float(np.max(finite)))
                take = min(per_group_cap, finite.size)
                positions = np.linspace(0, finite.size - 1, take, dtype=np.int64)
                samples.append(finite[positions])
        if count == 0 or nonfinite:
            raise PressureMethodDiagnosticError(
                f"actual PRAiSE {field} contains no finite values or has non-finite values"
            )
        sample = np.concatenate(samples)[:sample_cap]
        quantiles = np.quantile(sample, [0.01, 0.05, 0.5, 0.95, 0.99])
        summary[field] = {
            "finite_count": count,
            "nonfinite_count": nonfinite,
            "minimum": minimum,
            "maximum": maximum,
            "quantile_sample_count": int(sample.size),
            "quantile_sample_cap": int(sample_cap),
            "quantile_sampling": (
                "deterministic evenly spaced finite values within each injection group"
            ),
            "q01": float(quantiles[0]),
            "q05": float(quantiles[1]),
            "q50": float(quantiles[2]),
            "q95": float(quantiles[3]),
            "q99": float(quantiles[4]),
        }
    return summary


def summarise_gamma_fallbacks(
    result: Mapping[str, Any],
    selection: Sequence[Mapping[str, Any]],
    *,
    pressure_mode: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Replay the pinned PRAiSE gamma loop and count silent fallback events."""
    expected_ids = np.asarray(
        [int(row["physical_id"]) for row in selection],
        dtype=np.int64,
    )
    if not np.array_equal(
        np.asarray(result["ids"], dtype=np.int64),
        expected_ids,
    ):
        raise PressureMethodDiagnosticError(
            f"{pressure_mode} gamma-fallback IDs do not match selection"
        )
    summaries: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for branch in ("full", "adiabatic", "none"):
        groups = result.get(f"{branch}_info")
        if not isinstance(groups, list) or not groups:
            raise PressureMethodDiagnosticError(
                f"{pressure_mode}/{branch} is missing grouped PRAiSE diagnostics"
            )
        covered = np.zeros(len(expected_ids), dtype=bool)
        branch_event_count = 0
        branch_affected_cells: set[tuple[int, int]] = set()
        branch_affected_rows: set[int] = set()
        replay_verified = True
        for group in groups:
            rows = np.asarray(group.get("rows"), dtype=np.int64)
            info = group.get("info")
            if (
                rows.ndim != 1
                or rows.size == 0
                or np.any(rows < 0)
                or np.any(rows >= len(expected_ids))
                or np.any(covered[rows])
                or not isinstance(info, Mapping)
            ):
                raise PressureMethodDiagnosticError(
                    f"{pressure_mode}/{branch} has invalid grouped row provenance"
                )
            covered[rows] = True
            times = np.asarray(info.get("particle_times"), dtype=np.float64)
            current = np.asarray(
                info.get("current_lorentz"),
                dtype=np.float64,
            ).copy()
            actual_injection = np.asarray(
                info.get("injection_lorentz"),
                dtype=np.float64,
            )
            ap_arr = np.asarray(info.get("ap_arr"), dtype=np.float64)
            a2_arr = np.asarray(info.get("a2_arr"), dtype=np.float64)
            gamma_c = np.asarray(group.get("adiabatic_eff"), dtype=np.float64)
            shock_index = np.asarray(group.get("shock_index"), dtype=np.int64)
            expected_shape = (len(rows), len(FREQUENCIES_GHZ))
            if (
                times.ndim != 1
                or times.size == 0
                or not np.all(np.isfinite(times))
                or current.shape != expected_shape
                or actual_injection.shape != expected_shape
                or gamma_c.shape != (len(rows), times.size)
                or shock_index.shape != (len(rows),)
                or ap_arr.shape != (len(rows), max(0, times.size - 1))
                or a2_arr.shape != ap_arr.shape
                or not np.all(np.isfinite(current))
                or not np.all(np.isfinite(gamma_c))
                or not np.all(np.isfinite(ap_arr))
                or not np.all(np.isfinite(a2_arr))
            ):
                raise PressureMethodDiagnosticError(
                    f"{pressure_mode}/{branch} gamma-fallback inputs are invalid"
                )
            fallback_counts = np.zeros(expected_shape, dtype=np.int64)
            if times.size == 1:
                replayed_injection = current.copy()
                if np.any(shock_index != 0):
                    raise PressureMethodDiagnosticError(
                        f"{pressure_mode}/{branch} singleton shock index is invalid"
                    )
            else:
                if np.any(shock_index < 0) or np.any(
                    shock_index >= times.size - 1
                ):
                    raise PressureMethodDiagnosticError(
                        f"{pressure_mode}/{branch} shock index is not replayable"
                    )
                replayed_injection = np.full_like(current, np.nan)
                for time_index in range(times.size - 2, -1, -1):
                    new_gamma = get_gamma_numba(
                        g_nm1=current,
                        t_n=times[time_index],
                        t_nm1=times[time_index + 1],
                        gamma_c=gamma_c[:, time_index],
                        a_p=ap_arr[:, time_index],
                        a_2=a2_arr[:, time_index],
                    )
                    fallback = np.isnan(new_gamma) | (
                        np.abs(new_gamma) < 1
                    )
                    relevant = (
                        time_index >= shock_index
                    )[:, None]
                    fallback_counts += fallback & relevant
                    new_gamma[fallback] = current[fallback]
                    current = new_gamma
                    at_shock = shock_index == time_index
                    replayed_injection[at_shock] = current[at_shock]
            current_replay_verified = bool(np.array_equal(
                replayed_injection,
                actual_injection,
                equal_nan=True,
            ))
            replay_verified = replay_verified and current_replay_verified
            if not current_replay_verified:
                raise PressureMethodDiagnosticError(
                    f"{pressure_mode}/{branch} gamma replay does not match PRAiSE"
                )
            for local_row, frequency_index in np.argwhere(
                fallback_counts > 0
            ):
                global_row = int(rows[local_row])
                count = int(fallback_counts[local_row, frequency_index])
                branch_event_count += count
                branch_affected_cells.add(
                    (global_row, int(frequency_index))
                )
                branch_affected_rows.add(global_row)
                base = selection[global_row]
                records.append({
                    "pressure_mode": pressure_mode,
                    "loss_branch": branch,
                    "sample_index": int(base["sample_index"]),
                    "cache_row": int(base["cache_row"]),
                    "physical_id": int(base["physical_id"]),
                    "frequency_GHz": float(
                        FREQUENCIES_GHZ[frequency_index]
                    ),
                    "fallback_event_count": count,
                    "shock_index": int(shock_index[local_row]),
                    "history_columns": int(times.size),
                    "trim_affected": bool(base["trim_affected"]),
                    "short_history": bool(base["short_history"]),
                    "selection_reason": str(base["selection_reason"]),
                    "stratum": str(base["stratum"]),
                })
        if not np.all(covered):
            raise PressureMethodDiagnosticError(
                f"{pressure_mode}/{branch} gamma-fallback groups omit selected rows"
            )
        summaries.append({
            "pressure_mode": pressure_mode,
            "loss_branch": branch,
            "selected_particle_count": int(len(expected_ids)),
            "fallback_event_count": int(branch_event_count),
            "affected_particle_frequency_count": int(
                len(branch_affected_cells)
            ),
            "affected_particle_count": int(len(branch_affected_rows)),
            "replay_verified": bool(replay_verified),
            "gate_passed": bool(
                branch_event_count == 0 and replay_verified
            ),
            "audit_error": "",
            "fallback_definition": (
                "pinned PRAiSE intermediate gamma is NaN or abs(gamma)<1 "
                "on an interval from endpoint back through the assigned shock"
            ),
        })
    return summaries, records


def _spectral_index(low: float, high: float) -> float:
    if low <= 0 or high <= 0:
        raise PressureMethodDiagnosticError("aggregate spectral index requires positive luminosities")
    return float(-np.log(high / low) / np.log(FREQUENCIES_GHZ[1] / FREQUENCIES_GHZ[0]))


def represented_population_discrepancy_concentration(
    per_particle_discrepancy: np.ndarray,
    analysis_weights: np.ndarray,
    *,
    population_fraction: float = 0.01,
) -> dict[str, Any]:
    """Measure discrepancy in the highest-discrepancy population mass.

    Rows are ranked by their unweighted per-particle discrepancy.  Analysis
    weights then define represented population mass.  A fractional boundary
    row is used so the selected mass is exactly ``population_fraction`` of the
    total represented population.
    """
    discrepancy = np.asarray(per_particle_discrepancy, dtype=np.float64)
    weights = np.asarray(analysis_weights, dtype=np.float64)
    if (
        discrepancy.ndim != 1
        or weights.shape != discrepancy.shape
        or discrepancy.size == 0
        or not np.all(np.isfinite(discrepancy))
        or np.any(discrepancy < 0)
        or not np.all(np.isfinite(weights))
        or np.any(weights <= 0)
        or not 0 < population_fraction <= 1
    ):
        raise PressureMethodDiagnosticError(
            "discrepancy concentration requires finite nonnegative discrepancies, "
            "positive weights, and a population fraction in (0,1]"
        )
    total_weight = float(np.sum(weights))
    target_weight = float(population_fraction * total_weight)
    denominator = float(np.sum(weights * discrepancy))
    order = np.lexsort((np.arange(discrepancy.size), -discrepancy))
    remaining = target_weight
    numerator = 0.0
    boundary_index: int | None = None
    boundary_weight_fraction = 0.0
    full_rows = 0
    for index in order:
        if remaining <= 0:
            break
        represented = float(weights[index])
        used = min(represented, remaining)
        numerator += used * float(discrepancy[index])
        remaining -= used
        if used == represented:
            full_rows += 1
        else:
            boundary_index = int(index)
            boundary_weight_fraction = used / represented
            break
    concentration = 0.0 if denominator == 0 else numerator / denominator
    return {
        "fraction": float(concentration),
        "represented_population_weight": total_weight,
        "target_population_weight": target_weight,
        "population_fraction": float(population_fraction),
        "fully_included_rows": int(full_rows),
        "fractional_boundary_row_index": boundary_index,
        "fractional_boundary_row_weight_fraction": float(boundary_weight_fraction),
        "ranking": "descending unweighted per-particle absolute method discrepancy",
        "boundary_behavior": (
            "fractional boundary-row analysis weight is used to reach exactly "
            "the target represented-population mass"
        ),
        "numerator": float(numerator),
        "denominator": float(denominator),
    }


def summarise_method_comparison(
    selection: Sequence[Mapping[str, Any]],
    unsmoothed: Mapping[str, Any],
    log_savgol: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    ids = np.asarray([int(row["physical_id"]) for row in selection], dtype=np.int64)
    weights = np.asarray([float(row["analysis_weight"]) for row in selection])
    if not np.array_equal(np.asarray(unsmoothed["ids"], dtype=np.int64), ids):
        raise PressureMethodDiagnosticError("unsmoothed PRAiSE IDs do not match selection")
    if not np.array_equal(np.asarray(log_savgol["ids"], dtype=np.int64), ids):
        raise PressureMethodDiagnosticError("log-SG PRAiSE IDs do not match selection")
    arrays: dict[str, np.ndarray] = {}
    for mode, result in (("unsmoothed", unsmoothed), ("log_savgol", log_savgol)):
        for losses in ("full", "adiabatic", "none"):
            if losses not in result:
                raise PressureMethodDiagnosticError(
                    f"{mode} PRAiSE result is missing {losses!r} branch"
                )
            values = np.asarray(getattr(result[losses], "value", result[losses]), dtype=np.float64)
            if values.shape != (len(ids), 2) or not np.all(np.isfinite(values)) or np.any(values < 0):
                raise PressureMethodDiagnosticError(
                    f"{mode}/{losses} emissivity is not finite nonnegative (n,2)"
                )
            arrays[f"{mode}_{losses}"] = values

    full_vs_none_ordering: dict[str, list[dict[str, Any]]] = {}
    full_vs_adiabatic_ordering: dict[str, list[dict[str, Any]]] = {}
    particle_rows: list[dict[str, Any]] = []
    ordering_class: dict[tuple[str, str], np.ndarray] = {}
    for mode in ("unsmoothed", "log_savgol"):
        full_vs_none_ordering[mode] = _full_reference_ordering(
            arrays[f"{mode}_full"],
            arrays[f"{mode}_none"],
            weights,
            reference_label="none",
        )
        full_vs_adiabatic_ordering[mode] = _full_reference_ordering(
            arrays[f"{mode}_full"],
            arrays[f"{mode}_adiabatic"],
            weights,
            reference_label="adiabatic",
        )
        for reference in ("none", "adiabatic"):
            full = arrays[f"{mode}_full"]
            other = arrays[f"{mode}_{reference}"]
            ulp = np.maximum(
                np.abs(np.spacing(full)),
                np.abs(np.spacing(other)),
            )
            tolerance = (
                np.abs(other) * ORDERING_RTOL
                + ORDERING_ULP_MULTIPLIER * ulp
            )
            difference = full - other
            ordering_class[(mode, reference)] = np.where(
                difference > tolerance,
                f"full_above_{reference}",
                np.where(
                    -difference > tolerance,
                    f"full_below_{reference}",
                    "equivalent",
                ),
            )
    for index, base in enumerate(selection):
        row = dict(base)
        for mode in ("unsmoothed", "log_savgol"):
            for losses in ("full", "adiabatic", "none"):
                for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                    row[f"{mode}_{losses}_{frequency:g}GHz"] = float(
                        arrays[f"{mode}_{losses}"][index, frequency_index]
                    )
            for reference in ("none", "adiabatic"):
                for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                    reference_value = arrays[f"{mode}_{reference}"][
                        index, frequency_index
                    ]
                    row[
                        f"{mode}_full_vs_{reference}_{frequency:g}GHz"
                    ] = str(ordering_class[(mode, reference)][
                        index, frequency_index
                    ])
                    row[
                        f"{mode}_full_over_{reference}_{frequency:g}GHz"
                    ] = (
                        float(
                            arrays[f"{mode}_full"][index, frequency_index]
                            / reference_value
                        )
                        if reference_value > 0
                        else ""
                    )
        particle_rows.append(row)

    aggregate: dict[str, Any] = {}
    for mode in ("unsmoothed", "log_savgol"):
        aggregate[mode] = {}
        for losses in ("full", "adiabatic", "none"):
            values = np.sum(weights[:, None] * arrays[f"{mode}_{losses}"], axis=0)
            aggregate[mode][losses] = {
                "weighted_emissivity": values.tolist(),
                "spectral_index": _spectral_index(float(values[0]), float(values[1])),
            }
    aggregate_difference_dex = [
        float(np.log10(
            aggregate["log_savgol"]["full"]["weighted_emissivity"][index]
            / aggregate["unsmoothed"]["full"]["weighted_emissivity"][index]
        ))
        for index in range(2)
    ]
    spectral_difference = float(
        aggregate["log_savgol"]["full"]["spectral_index"]
        - aggregate["unsmoothed"]["full"]["spectral_index"]
    )
    directions: dict[str, list[str]] = {}
    for mode in ("unsmoothed", "log_savgol"):
        directions[mode] = []
        for index in range(2):
            full = aggregate[mode]["full"]["weighted_emissivity"][index]
            none = aggregate[mode]["none"]["weighted_emissivity"][index]
            directions[mode].append(_direction(float(np.log10(full / none))))
    direction_stable = directions["unsmoothed"] == directions["log_savgol"]
    radiative_suppression = all(
        row["full_above_adiabatic_count"] == 0
        and row["aggregate_direction"] != "full_above_adiabatic"
        for mode in ("unsmoothed", "log_savgol")
        for row in full_vs_adiabatic_ordering[mode]
    )
    discrepancies = np.abs(
        arrays["log_savgol_full"] - arrays["unsmoothed_full"]
    )
    per_row_discrepancy = np.sum(discrepancies, axis=1)
    concentration = represented_population_discrepancy_concentration(
        per_row_discrepancy,
        weights,
        population_fraction=0.01,
    )
    top_fraction = concentration["fraction"]
    gate_results = {
        "aggregate_difference": all(
            abs(value) <= GATES["max_abs_aggregate_difference_dex"]
            for value in aggregate_difference_dex
        ),
        "spectral_index_difference": (
            abs(spectral_difference) <= GATES["max_abs_spectral_index_difference"]
        ),
        "full_vs_lossless_direction": direction_stable,
        "radiative_suppression": radiative_suppression,
        "discrepancy_concentration": (
            top_fraction <= GATES["max_top_one_percent_discrepancy_fraction"]
        ),
    }
    summary = {
        "decision": "PASS" if all(gate_results.values()) else "FAIL",
        "inference_scope": (
            "deterministic weighted sample evidence; not proof of full-population equivalence"
        ),
        "frequencies_GHz": list(FREQUENCIES_GHZ),
        "gates": GATES,
        "gate_results": gate_results,
        "comparison_semantics": {
            "none_branch": (
                "losses='none' disables both adiabatic and radiative evolution"
            ),
            "none_branch_is_upper_bound": False,
            "full_above_none_interpretation": (
                "possible net adiabatic-compression enhancement; not by itself "
                "a numerical or radiative-loss failure"
            ),
            "radiative_discriminator": (
                "losses='adiabatic' retains pressure-work evolution while "
                "disabling radiative losses"
            ),
        },
        "weighted_aggregate": aggregate,
        "full_vs_none_ordering": full_vs_none_ordering,
        "full_vs_adiabatic_ordering": full_vs_adiabatic_ordering,
        "aggregate_log_savgol_minus_unsmoothed_dex": aggregate_difference_dex,
        "full_loss_spectral_index_difference": spectral_difference,
        "full_vs_lossless_direction": directions,
        "top_one_percent_represented_population": concentration,
        "top_one_percent_absolute_discrepancy_fraction": top_fraction,
        "discrepancy_definition": (
            "rows ranked by sum_frequency(abs(log_savgol_full - unsmoothed_full)); "
            "represented-weighted discrepancy accumulated through exactly 1% "
            "of total represented population weight with a fractional boundary row"
        ),
    }
    return particle_rows, summary


def _ordering_csv_rows(comparison: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for reference, summary_key in (
        ("none", "full_vs_none_ordering"),
        ("adiabatic", "full_vs_adiabatic_ordering"),
    ):
        ordering = comparison[summary_key]
        for mode in ("unsmoothed", "log_savgol"):
            for record in ordering[mode]:
                rows.append({
                    "pressure_mode": mode,
                    "reference_branch": reference,
                    "frequency_GHz": record["frequency_GHz"],
                    "full_above_reference_count": record[
                        f"full_above_{reference}_count"
                    ],
                    "full_below_reference_count": record[
                        f"full_below_{reference}_count"
                    ],
                    "equivalent_count": record["equivalent_count"],
                    "full_above_reference_represented_weight_fraction": record[
                        f"full_above_{reference}_represented_weight_fraction"
                    ],
                    "full_below_reference_represented_weight_fraction": record[
                        f"full_below_{reference}_represented_weight_fraction"
                    ],
                    "both_zero_count": record["both_zero_count"],
                    "full_only_positive_count": record[
                        "full_only_positive_count"
                    ],
                    "reference_only_positive_count": record[
                        f"{reference}_only_positive_count"
                    ],
                    "both_positive_count": record["both_positive_count"],
                    "positive_ratio_min": record["positive_ratio_min"],
                    "positive_ratio_q50": record["positive_ratio_q50"],
                    "positive_ratio_q95": record["positive_ratio_q95"],
                    "positive_ratio_q99": record["positive_ratio_q99"],
                    "positive_ratio_max": record["positive_ratio_max"],
                    "maximum_absolute_difference": record[
                        "maximum_absolute_difference"
                    ],
                    "comparison_absolute_tolerance_max": record[
                        "comparison_absolute_tolerance_max"
                    ],
                    "comparison_relative_tolerance": record[
                        "comparison_relative_tolerance"
                    ],
                    "comparison_ulp_multiplier": record[
                        "comparison_ulp_multiplier"
                    ],
                    "weighted_full_emissivity": record[
                        "weighted_full_emissivity"
                    ],
                    "weighted_reference_emissivity": record[
                        f"weighted_{reference}_emissivity"
                    ],
                    "aggregate_full_over_reference_ratio": record[
                        f"aggregate_full_over_{reference}_ratio"
                    ],
                    "aggregate_log10_full_over_reference": record[
                        f"aggregate_log10_full_over_{reference}"
                    ],
                    "aggregate_direction": record["aggregate_direction"],
                })
    return rows


def diagnose_pressure_method_value(
    cache: Path,
    affected_rows_csv: Path,
    output_dir: Path,
    *,
    sample_size: int = SAMPLE_SIZE,
    row_chunk: int = 512,
    expected_trim_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
    expected_no_positive_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
    expected_single_record_rows: int = workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
    expected_trim_single_record_overlap_rows: int | None = None,
) -> dict[str, Any]:
    cache = Path(cache).resolve()
    affected_rows_csv = Path(affected_rows_csv).resolve()
    output_dir = Path(output_dir).resolve()
    if not cache.is_file() or cache.is_symlink():
        raise PressureMethodDiagnosticError(f"cache must be a regular file: {cache}")
    if not affected_rows_csv.is_file() or affected_rows_csv.is_symlink():
        raise PressureMethodDiagnosticError(
            f"affected-row evidence must be a regular file: {affected_rows_csv}"
        )
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise PressureMethodDiagnosticError(
                f"refusing to overwrite non-empty output directory: {output_dir}"
            )
    else:
        output_dir.mkdir(parents=True)
    affected = _read_affected_rows(affected_rows_csv)
    with h5py.File(cache, "r") as h5:
        workflow._validate_completed_cache(h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=expected_trim_rows,
            expected_no_positive_rows=expected_no_positive_rows,
            expected_single_record_rows=expected_single_record_rows,
            expected_trim_single_record_overlap_rows=(
                expected_trim_single_record_overlap_rows
            ),
            row_chunk=row_chunk,
        )
        selected_rows, selection, selection_metadata = construct_deterministic_sample(
            h5,
            plan,
            affected,
            sample_size=sample_size,
            row_chunk=row_chunk,
        )
        raw = _read_treated_sample(h5, selected_rows, plan)
        physical, units = workflow.convert_code_cache_to_physical(
            raw,
            shock_threshold=float(h5.attrs["shock_threshold"]),
            shock_component=int(h5.attrs["shock_component"]),
        )
        cache_identity = workflow._cache_identity(cache)
    selection_path = output_dir / "pressure_method_selection.csv"
    _write_csv(selection_path, SELECTION_FIELDS, selection)
    kwargs = {
        "frequencies": FREQUENCIES_GHZ,
        "z": workflow.PRIMARY_CONTRACT["redshift"],
        "s": workflow.PRIMARY_CONTRACT["s"],
        "eta": workflow.PRIMARY_CONTRACT["eta"],
        "gmin": workflow.PRIMARY_CONTRACT["gmin"],
        "gmax": workflow.PRIMARY_CONTRACT["gmax"],
        "lst_index": 0,
        "diagnostic": True,
        "include_adiabatic": True,
    }
    unsmoothed = calculate_praise_pair(
        physical, pressure_mode="unsmoothed", singleton_policy="instantaneous_recent_shock", **kwargs
    )
    unsmoothed_checkpoint = (
        output_dir / "pressure_method_unsmoothed_emissivity_checkpoint.npz"
    )
    _write_emissivity_checkpoint(unsmoothed_checkpoint, unsmoothed)
    log_savgol = calculate_praise_pair(
        physical, pressure_mode="log_savgol", singleton_policy="instantaneous_recent_shock", **kwargs
    )
    log_savgol_checkpoint = (
        output_dir / "pressure_method_log_savgol_emissivity_checkpoint.npz"
    )
    _write_emissivity_checkpoint(log_savgol_checkpoint, log_savgol)
    # Persist raw branch values and reconcile forensic coverage before any
    # secondary audit can fail. This guarantees non-finite evidence survives
    # an audit exception and can be archived by the PBS wrapper.
    nonfinite_summary_rows, nonfinite_records, nonfinite_summary = (
        _nonfinite_evidence({
            "unsmoothed": unsmoothed,
            "log_savgol": log_savgol,
        })
    )
    nonfinite_summary_path = (
        output_dir / "pressure_method_nonfinite_emissivity_summary.csv"
    )
    nonfinite_records_path = (
        output_dir / "pressure_method_nonfinite_emissivity_records.csv"
    )
    _write_csv(
        nonfinite_summary_path,
        NONFINITE_SUMMARY_FIELDS,
        nonfinite_summary_rows,
    )
    _write_csv(
        nonfinite_records_path,
        NONFINITE_RECORD_FIELDS,
        nonfinite_records,
    )
    def _fallback_audit(mode: str, result: Mapping[str, Any]):
        try:
            return summarise_gamma_fallbacks(
                result, selection, pressure_mode=mode,
            )
        except Exception as exc:  # preserve the audit failure in the archive
            message = f"{type(exc).__name__}: {exc}"
            return ([
                {
                    "pressure_mode": mode,
                    "loss_branch": branch,
                    "selected_particle_count": int(len(selection)),
                    "fallback_event_count": 0,
                    "affected_particle_frequency_count": 0,
                    "affected_particle_count": 0,
                    "replay_verified": False,
                    "gate_passed": False,
                    "fallback_definition": (
                        "pinned PRAiSE intermediate gamma is NaN or abs(gamma)<1 "
                        "on an interval from endpoint back through the assigned shock"
                    ),
                    "audit_error": message,
                }
                for branch in ("full", "adiabatic", "none")
            ], [])
    unsmoothed_fallback_summary, unsmoothed_fallback_records = _fallback_audit(
        "unsmoothed", unsmoothed
    )
    log_savgol_fallback_summary, log_savgol_fallback_records = _fallback_audit(
        "log_savgol", log_savgol
    )
    fallback_summary = (
        unsmoothed_fallback_summary + log_savgol_fallback_summary
    )
    fallback_records = (
        unsmoothed_fallback_records + log_savgol_fallback_records
    )
    fallback_summary_path = (
        output_dir / "pressure_method_gamma_fallback_summary.csv"
    )
    fallback_records_path = (
        output_dir / "pressure_method_gamma_fallback_records.csv"
    )
    _write_csv(
        fallback_summary_path,
        GAMMA_FALLBACK_SUMMARY_FIELDS,
        fallback_summary,
    )
    _write_csv(
        fallback_records_path,
        GAMMA_FALLBACK_RECORD_FIELDS,
        fallback_records,
    )
    if nonfinite_summary["nonfinite_branch_count"]:
        # Do not run finite-only comparisons on a branch containing NaN/Inf.
        # Preserve the checkpoints and emit a standard diagnostic FAIL instead.
        particle_rows = []
        comparison = {
            "decision": "FAIL",
            "inference_scope": (
                "non-finite branch evidence; finite-only method comparison suppressed"
            ),
            "gates": GATES,
            "gate_results": {
                "aggregate_difference": False,
                "spectral_index_difference": False,
                "full_vs_lossless_direction": False,
                "radiative_suppression": False,
                "discrepancy_concentration": False,
            },
            "comparison_semantics": {
                "none_branch_is_upper_bound": False,
                "finite_only_comparison_suppressed": True,
                "nonfinite_evidence": nonfinite_summary,
            },
            "weighted_aggregate": {},
            "full_vs_none_ordering": {},
            "full_vs_adiabatic_ordering": {},
            "aggregate_log_savgol_minus_unsmoothed_dex": [None, None],
            "full_loss_spectral_index_difference": None,
            "full_vs_lossless_direction": {},
            "top_one_percent_represented_population": {},
            "top_one_percent_absolute_discrepancy_fraction": None,
            "discrepancy_definition": "suppressed because at least one branch is non-finite",
        }
    else:
        particle_rows, comparison = summarise_method_comparison(
            selection, unsmoothed, log_savgol
        )
    comparison["forensic_coverage"] = nonfinite_summary
    comparison["gate_results"]["forensic_coverage"] = bool(
        nonfinite_summary["coverage_valid"]
    )
    fallback_gate = all(row["gate_passed"] for row in fallback_summary)
    comparison["gamma_fallback"] = {
        "gate_passed": bool(fallback_gate),
        "summary": fallback_summary,
        "record_count": int(len(fallback_records)),
        "records_csv": fallback_records_path.name,
    }
    comparison["gate_results"]["gamma_fallback"] = bool(fallback_gate)
    comparison["decision"] = (
        "PASS"
        if all(comparison["gate_results"].values())
        else "FAIL"
    )
    def _dynamics_audit(mode: str, result: Mapping[str, Any]):
        try:
            return summarise_actual_praise_dynamics(result)
        except Exception as exc:  # preserve the audit failure in the archive
            return {
                "audit_error": f"{type(exc).__name__}: {exc}",
                "gate_passed": False,
            }
    dynamics_summary = {
        "unsmoothed": _dynamics_audit("unsmoothed", unsmoothed),
        "log_savgol": _dynamics_audit("log_savgol", log_savgol),
    }
    dynamics_gate = all(
        not isinstance(value, Mapping) or "audit_error" not in value
        for value in dynamics_summary.values()
    )
    comparison["gate_results"]["actual_dynamics"] = bool(dynamics_gate)
    comparison["actual_dynamics"] = dynamics_summary
    comparison["decision"] = (
        "PASS"
        if all(comparison["gate_results"].values())
        else "FAIL"
    )
    particle_path = output_dir / "pressure_method_particle_comparison.csv"
    ordering_path = output_dir / "pressure_method_full_reference_ordering.csv"
    summary_json = output_dir / "pressure_method_summary.json"
    summary_csv = output_dir / "pressure_method_summary.csv"
    particle_fields = list(particle_rows[0]) if particle_rows else list(SELECTION_FIELDS)
    _write_csv(particle_path, particle_fields, particle_rows)
    ordering_rows = _ordering_csv_rows(comparison) if not nonfinite_summary["nonfinite_branch_count"] else []
    ordering_fields = (
        list(ordering_rows[0]) if ordering_rows else [
            "pressure_mode", "reference_branch", "frequency_GHz",
            "full_above_reference_count", "full_below_reference_count",
            "equivalent_count", "full_above_reference_represented_weight_fraction",
            "full_below_reference_represented_weight_fraction", "both_zero_count",
            "full_only_positive_count", "reference_only_positive_count",
            "maximum_absolute_difference", "comparison_absolute_tolerance_max",
            "comparison_relative_tolerance", "comparison_ulp_multiplier",
            "weighted_full_emissivity", "weighted_reference_emissivity",
            "aggregate_full_over_reference_ratio", "aggregate_log10_full_over_reference",
            "aggregate_direction",
        ]
    )
    _write_csv(ordering_path, ordering_fields, ordering_rows)
    summary = {
        "status": "diagnostic_complete",
        "decision": comparison["decision"],
        "cache_identity": cache_identity,
        "affected_rows_csv_sha256": workflow._sha256_file(affected_rows_csv),
        "pressure_treatment_identity_sha256": plan["identity_sha256"],
        "pressure_treatment_counts": {
            "trim_rows": int(len(plan["trim_rows"])),
            "excluded_rows": int(len(plan["excluded_rows"])),
            "single_record_rows": int(len(plan["single_record_rows"])),
            "trim_single_record_overlap_rows": int(
                len(plan["trim_single_record_overlap_rows"])
            ),
        },
        "selection": selection_metadata,
        "pressure_modes": {
            "primary": {
                **unsmoothed["metadata"],
                "actual_praise_dynamics": dynamics_summary["unsmoothed"],
            },
            "comparator": {
                **log_savgol["metadata"],
                "actual_praise_dynamics": dynamics_summary["log_savgol"],
            },
        },
        "unit_provenance": units,
        "nonfinite_evidence": {
            **nonfinite_summary,
            "summary_csv": nonfinite_summary_path.name,
            "records_csv": nonfinite_records_path.name,
        },
        "comparison": comparison,
    }
    _write_json(summary_json, summary)
    summary_rows = [
        {
            "metric": "aggregate_log_savgol_minus_unsmoothed_dex",
            "frequency_GHz": frequency,
            "value": comparison["aggregate_log_savgol_minus_unsmoothed_dex"][index],
            "threshold": GATES["max_abs_aggregate_difference_dex"],
            "passed": comparison["gate_results"]["aggregate_difference"],
        }
        for index, frequency in enumerate(FREQUENCIES_GHZ)
    ]
    summary_rows.extend([
        {
            "metric": "full_loss_spectral_index_difference",
            "frequency_GHz": "",
            "value": comparison["full_loss_spectral_index_difference"],
            "threshold": GATES["max_abs_spectral_index_difference"],
            "passed": comparison["gate_results"]["spectral_index_difference"],
        },
        {
            "metric": "top_one_percent_absolute_discrepancy_fraction",
            "frequency_GHz": "",
            "value": comparison["top_one_percent_absolute_discrepancy_fraction"],
            "threshold": GATES["max_top_one_percent_discrepancy_fraction"],
            "passed": comparison["gate_results"]["discrepancy_concentration"],
        },
        {
            "metric": "full_vs_lossless_direction_stability",
            "frequency_GHz": "",
            "value": int(comparison["gate_results"]["full_vs_lossless_direction"]),
            "threshold": 1,
            "passed": comparison["gate_results"]["full_vs_lossless_direction"],
        },
        {
            "metric": "full_not_above_adiabatic",
            "frequency_GHz": "",
            "value": int(comparison["gate_results"]["radiative_suppression"]),
            "threshold": 1,
            "passed": comparison["gate_results"]["radiative_suppression"],
        },
        {
            "metric": "gamma_fallback_free",
            "frequency_GHz": "",
            "value": int(comparison["gate_results"]["gamma_fallback"]),
            "threshold": 1,
            "passed": comparison["gate_results"]["gamma_fallback"],
        },
        {
            "metric": "actual_praise_dynamics_audit",
            "frequency_GHz": "",
            "value": int(comparison["gate_results"]["actual_dynamics"]),
            "threshold": 1,
            "passed": comparison["gate_results"]["actual_dynamics"],
        },
    ])
    _write_csv(
        summary_csv,
        ("metric", "frequency_GHz", "value", "threshold", "passed"),
        summary_rows,
    )
    return {
        "status": "diagnostic_complete",
        "decision": comparison["decision"],
        "selection_path": str(selection_path),
        "unsmoothed_checkpoint": str(unsmoothed_checkpoint),
        "log_savgol_checkpoint": str(log_savgol_checkpoint),
        "particle_comparison_path": str(particle_path),
        "ordering_path": str(ordering_path),
        "gamma_fallback_summary_path": str(fallback_summary_path),
        "gamma_fallback_records_path": str(fallback_records_path),
        "summary_json": str(summary_json),
        "summary_csv": str(summary_csv),
        "nonfinite_summary_path": str(nonfinite_summary_path),
        "nonfinite_records_path": str(nonfinite_records_path),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--affected-rows-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=SAMPLE_SIZE)
    parser.add_argument("--row-chunk", type=int, default=512)
    parser.add_argument("--expected-trim-rows", type=int, default=10_030)
    parser.add_argument("--expected-no-positive-rows", type=int, default=2)
    parser.add_argument("--expected-single-record-rows", type=int, default=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"])
    parser.add_argument(
        "--expected-trim-single-record-overlap-rows",
        type=int,
        default=workflow.PRESSURE_TREATMENT_CONTRACT[
            "expected_trim_single_record_overlap_rows"
        ],
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = diagnose_pressure_method_value(
            args.cache,
            args.affected_rows_csv,
            args.output_dir,
            sample_size=args.sample_size,
            row_chunk=args.row_chunk,
            expected_trim_rows=args.expected_trim_rows,
            expected_no_positive_rows=args.expected_no_positive_rows,
            expected_single_record_rows=args.expected_single_record_rows,
            expected_trim_single_record_overlap_rows=(
                args.expected_trim_single_record_overlap_rows
            ),
        )
    except (OSError, ValueError, workflow.WorkflowError, PressureMethodDiagnosticError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
