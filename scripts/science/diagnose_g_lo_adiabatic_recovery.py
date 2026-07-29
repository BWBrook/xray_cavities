#!/usr/bin/env python3
"""Bounded numerical-recovery gate for the archived Goal 049 adiabatic failure.

The archived failure was confined to the adiabatic branch when the upstream
implementation evaluated two absolute-time powers separately.  This module is
diagnostic-only: it evaluates the same recurrence as a ratio in log space,
checks it against an independent high-precision calculation, and audits the
full branch's relevant (endpoint-to-assigned-shock) interval.  It never turns a
non-finite value into zero and never modifies the completed history cache.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import mpmath
import numpy as np
from astropy import units as u

from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.diagnose_g_lo_pressure_method_value import (
    _read_treated_sample as _read_treated_sample_increasing,
)
from plutokore.radio.praise import (
    get_a2_numba,
    get_ap_numba,
    get_c1,
    get_gamma_larmor_numba,
    get_gamma_numba,
    get_adiabatic_eff,
    get_emissivity_numba,
    get_K,
)


FREQUENCIES_GHZ = (0.15, 1.4)
Z = 0.05
ETA = 0.03
S = 2.2
GMIN = 500.0
GMAX = 1e5
GAMMA_INF = 1e50
HP_DPS = 80
STABLE_RTOL = 1e-11
STABLE_ATOL = 1e-12
UPSTREAM_RTOL = 1e-10
UPSTREAM_ATOL = 1e-12
TRACE_LIMIT = 64
ADIABATIC_RECOVERY_GATE_NAMES = (
    "archived_failure_reproduction",
    "finite_injection_gamma_emissivity",
    "high_precision_agreement",
    "stable_endpoint_trajectory",
)
FULL_METHOD_GATE_NAMES = (
    "zero_relevant_full_dynamics_nonfinite",
    "zero_relevant_silent_gamma_fallbacks",
)


class RecoveryDiagnosticError(RuntimeError):
    """Raised when the diagnostic contract cannot be evaluated safely."""


def _read_treated_sample(
    h5: h5py.File,
    rows: np.ndarray,
    plan: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    """Read arbitrary cache-row order while satisfying h5py index ordering."""
    requested = np.asarray(rows)
    if requested.ndim != 1 or not np.issubdtype(requested.dtype, np.integer):
        raise RecoveryDiagnosticError("sample rows must be a one-dimensional integer array")
    requested = requested.astype(np.int64, copy=False)
    increasing_rows, restore_order = np.unique(requested, return_inverse=True)
    sample = _read_treated_sample_increasing(h5, increasing_rows, plan)
    restored: dict[str, np.ndarray] = {}
    for field, values in sample.items():
        array = np.asarray(values)
        if field == "time":
            restored[field] = array
        else:
            if array.ndim == 0 or array.shape[0] != increasing_rows.size:
                raise RecoveryDiagnosticError(
                    f"treated sample field {field!r} is not aligned to cache rows"
                )
            restored[field] = array[restore_order, ...]
    return restored


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
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def separate_power_ratio(gamma: Any, t_n: Any, t_nm1: Any, q: Any) -> np.ndarray:
    """Reference to the unstable upstream expression (for stress diagnostics)."""
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        return np.asarray(gamma, dtype=float) * np.power(t_n, q) / np.power(t_nm1, q)


def stable_ratio_power(gamma: Any, t_n: Any, t_nm1: Any, q: Any) -> np.ndarray:
    """Evaluate ``gamma * (t_n / t_nm1)**q`` without separate powers."""
    gamma_a, tn_a, tm_a, q_a = np.broadcast_arrays(
        np.asarray(gamma, dtype=float), np.asarray(t_n, dtype=float),
        np.asarray(t_nm1, dtype=float), np.asarray(q, dtype=float),
    )
    if np.any(~np.isfinite(gamma_a)) or np.any(gamma_a <= 0):
        raise RecoveryDiagnosticError("stable ratio requires finite positive gamma")
    if np.any(~np.isfinite(tn_a)) or np.any(~np.isfinite(tm_a)) or np.any(tn_a <= 0) or np.any(tm_a <= 0):
        raise RecoveryDiagnosticError("stable ratio requires finite positive times")
    if np.any(~np.isfinite(q_a)):
        raise RecoveryDiagnosticError("stable ratio requires finite exponents")
    with np.errstate(over="raise", under="ignore", invalid="raise", divide="raise"):
        return gamma_a * np.exp(q_a * (np.log(tn_a) - np.log(tm_a)))


def stable_pressure_ratio(gamma: Any, p_n: Any, p_nm1: Any, gamma_c: Any) -> np.ndarray:
    """Primary stable form using the pressure-ratio/log-difference recurrence."""
    gamma_a, pn_a, pm_a, gc_a = np.broadcast_arrays(
        np.asarray(gamma, dtype=float), np.asarray(p_n, dtype=float),
        np.asarray(p_nm1, dtype=float), np.asarray(gamma_c, dtype=float),
    )
    if (np.any(~np.isfinite(gamma_a)) or np.any(gamma_a <= 0)
            or np.any(~np.isfinite(pn_a)) or np.any(~np.isfinite(pm_a))
            or np.any(pn_a <= 0) or np.any(pm_a <= 0)
            or np.any(~np.isfinite(gc_a)) or np.any(gc_a <= 0)):
        raise RecoveryDiagnosticError("stable pressure ratio requires finite positive inputs")
    with np.errstate(over="raise", under="ignore", invalid="raise", divide="raise"):
        # log1p is materially more accurate when neighbouring pressures are
        # nearly equal, while the log-difference remains the explicit fallback.
        delta = np.log1p((pn_a - pm_a) / pm_a)
        return gamma_a * np.exp(delta / (3.0 * gc_a))


def high_precision_ratio_power(gamma: float, t_n: float, t_nm1: float, q: float) -> float:
    """Independent mpmath reference for one ratio-power update."""
    with mpmath.workdps(HP_DPS):
        result = mpmath.mpf(str(gamma)) * mpmath.power(
            mpmath.mpf(str(t_n)) / mpmath.mpf(str(t_nm1)), mpmath.mpf(str(q))
        )
        return float(result)


def stable_adiabatic_trajectory(
    endpoint_gamma: Any,
    times: Any,
    ap_arr: Any,
    gamma_c: Any,
    shock_index: Any,
    *,
    pressure: Any | None = None,
    gamma_inf: float = GAMMA_INF,
) -> dict[str, Any]:
    """Compute stable adiabatic trajectories and classify interval failures.

    ``shock_index`` is relative to ``times``.  Intervals ``i >= shock_index``
    are the relevant endpoint-to-assigned-shock window; earlier intervals are
    retained as pre-shock evidence but do not fail the endpoint gate alone.
    """
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    times_a = np.asarray(times, dtype=float)
    ap = np.asarray(ap_arr, dtype=float)
    gc = np.asarray(gamma_c, dtype=float)
    shocks = np.asarray(shock_index, dtype=int)
    if endpoint.ndim != 2 or times_a.ndim != 1 or ap.ndim != 2:
        raise RecoveryDiagnosticError("trajectory inputs have invalid dimensions")
    n, nf = endpoint.shape
    if ap.shape != (n, times_a.size - 1) or shocks.shape != (n,):
        raise RecoveryDiagnosticError("trajectory shapes do not match time history")
    if gc.shape == (n, times_a.size):
        gc_steps = gc[:, :-1]
    elif gc.shape == ap.shape:
        gc_steps = gc
    else:
        raise RecoveryDiagnosticError("gamma_c must be (particle,time) or interval-shaped")
    if pressure is not None:
        pressure_a = np.asarray(pressure, dtype=float)
        if pressure_a.shape != (n, times_a.size):
            raise RecoveryDiagnosticError("pressure must have shape (particle,time)")
    else:
        pressure_a = None
    if np.any(shocks < 0) or np.any(shocks >= times_a.size):
        raise RecoveryDiagnosticError("shock indices are outside the history")
    trajectory = np.full((n, times_a.size, nf), np.nan, dtype=float)
    trajectory[:, -1, :] = endpoint
    relevant_nonfinite = 0
    preshock_nonfinite = 0
    relevant_fallback = 0
    preshock_fallback = 0
    algebraic_disagreement = 0
    relevant_algebraic_disagreement = 0
    preshock_algebraic_disagreement = 0
    relevant_nonpositive_time = 0
    preshock_nonpositive_time = 0
    for i in range(times_a.size - 2, -1, -1):
        relevant = i >= shocks
        q = ap[:, i] / (3.0 * gc_steps[:, i])
        previous = trajectory[:, i + 1, :]
        valid_input = (
            np.isfinite(q) & np.isfinite(ap[:, i]) & np.isfinite(gc_steps[:, i])
            & (gc_steps[:, i] > 0) & np.all(np.isfinite(previous), axis=1)
            & np.all(previous > 0, axis=1)
        )
        positive_time = np.isfinite(times_a[i]) and np.isfinite(times_a[i + 1]) and times_a[i] > 0 and times_a[i + 1] > 0
        if positive_time:
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                time_candidate = previous * np.exp(q[:, None] * (np.log(times_a[i]) - np.log(times_a[i + 1])))
        else:
            time_candidate = np.full_like(previous, np.nan)
        if pressure_a is not None:
            try:
                pressure_candidate = stable_pressure_ratio(
                    previous, pressure_a[:, i, None], pressure_a[:, i + 1, None], gc_steps[:, i, None]
                )
            except RecoveryDiagnosticError:
                pressure_candidate = np.full_like(previous, np.nan)
        else:
            pressure_candidate = time_candidate
        candidate = pressure_candidate
        disagreement = np.isfinite(time_candidate) & np.isfinite(pressure_candidate) & (
            np.abs(time_candidate - pressure_candidate) > STABLE_ATOL + STABLE_RTOL * np.abs(time_candidate)
        )
        algebraic_disagreement += int(np.count_nonzero(disagreement))
        relevant_algebraic_disagreement += int(np.count_nonzero(disagreement & relevant[:, None]))
        preshock_algebraic_disagreement += int(np.count_nonzero(disagreement & ~relevant[:, None]))
        good = valid_input & np.all(np.isfinite(candidate), axis=1) & np.all(candidate > 0, axis=1)
        too_large = np.any(candidate >= gamma_inf, axis=1) | ~np.all(np.isfinite(candidate), axis=1)
        relevant_nonfinite += int(np.count_nonzero(relevant & ~good))
        preshock_nonfinite += int(np.count_nonzero(~relevant & ~good))
        if not positive_time:
            relevant_nonpositive_time += int(np.count_nonzero(relevant))
            preshock_nonpositive_time += int(np.count_nonzero(~relevant))
        relevant_fallback += int(np.count_nonzero(relevant & (too_large | ~good)))
        preshock_fallback += int(np.count_nonzero(~relevant & (too_large | ~good)))
        trajectory[:, i, :] = np.where(good[:, None], candidate, np.nan)
    relevant_mask = np.zeros((n, times_a.size), dtype=bool)
    for row, shock in enumerate(shocks):
        relevant_mask[row, shock:] = True
    relevant_values = trajectory[relevant_mask]
    endpoint_gate = bool(
        relevant_values.size
        and np.all(np.isfinite(relevant_values))
        and np.all(relevant_values > 0)
        and np.all(relevant_values < gamma_inf)
        and np.all(np.isfinite(trajectory[np.arange(n), shocks, :]))
        and relevant_nonpositive_time == 0
    )
    return {
        "trajectory": trajectory,
        "relevant_mask": relevant_mask,
        "relevant_nonfinite_count": relevant_nonfinite,
        "preshock_nonfinite_count": preshock_nonfinite,
        "relevant_fallback_count": relevant_fallback,
        "preshock_fallback_count": preshock_fallback,
        "algebraic_disagreement_count": algebraic_disagreement,
        "relevant_algebraic_disagreement_count": relevant_algebraic_disagreement,
        "preshock_algebraic_disagreement_count": preshock_algebraic_disagreement,
        "relevant_nonpositive_time_count": relevant_nonpositive_time,
        "preshock_nonpositive_time_count": preshock_nonpositive_time,
        "endpoint_gate_passed": endpoint_gate,
    }


def high_precision_adiabatic_trajectory(
    endpoint_gamma: Any, times: Any, ap_arr: Any, gamma_c: Any, shock_index: Any
) -> np.ndarray:
    """Independent high-precision recurrence for every retained trace."""
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    times_a = np.asarray(times, dtype=float)
    ap = np.asarray(ap_arr, dtype=float)
    gc = np.asarray(gamma_c, dtype=float)
    shocks = np.asarray(shock_index, dtype=int)
    n, nf = endpoint.shape
    gc_steps = gc[:, :-1] if gc.shape == (n, times_a.size) else gc
    result = np.full((n, times_a.size, nf), np.nan, dtype=float)
    with mpmath.workdps(HP_DPS):
        for row in range(n):
            for freq in range(nf):
                current = mpmath.mpf(str(float(endpoint[row, freq])))
                result[row, -1, freq] = float(current)
                for i in range(times_a.size - 2, int(shocks[row]) - 1, -1):
                    if times_a[i] <= 0 or times_a[i + 1] <= 0:
                        continue
                    q = mpmath.mpf(str(float(ap[row, i]))) / (
                        mpmath.mpf(3) * mpmath.mpf(str(float(gc_steps[row, i])))
                    )
                    current = current * mpmath.power(
                        mpmath.mpf(str(float(times_a[i])))
                        / mpmath.mpf(str(float(times_a[i + 1]))), q
                    )
                    result[row, i, freq] = float(current)
    return result


def compare_recovery_to_high_precision(
    stable: np.ndarray, reference: np.ndarray, relevant_mask: np.ndarray, *,
    rtol: float = STABLE_RTOL, atol: float = STABLE_ATOL,
) -> dict[str, Any]:
    """Compare stable and high-precision values only on the relevant window."""
    if stable.shape != reference.shape or relevant_mask.shape != stable.shape[:2]:
        raise RecoveryDiagnosticError("high-precision comparison shapes do not match")
    mask = np.broadcast_to(relevant_mask[:, :, None], stable.shape)
    left, right = stable[mask], reference[mask]
    if left.size == 0 or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        return {"compared_count": int(left.size), "max_abs_difference": None,
                "max_relative_difference": None, "passed": False}
    diff = np.abs(left - right)
    rel = diff / np.maximum(np.abs(right), np.finfo(float).tiny)
    passed = bool(np.all(diff <= atol + rtol * np.abs(right)))
    return {"compared_count": int(left.size), "max_abs_difference": float(np.max(diff)),
            "max_relative_difference": float(np.max(rel)), "passed": passed}


def classify_relevant_windows(
    values: Any, shock_index: Any, *, interval_axis: int = 1
) -> dict[str, int]:
    """Count non-finites in relevant and pre-shock intervals.

    ``values`` is shaped ``(particle, interval)`` (or can have extra trailing
    dimensions, such as frequency); interval ``i`` is relevant when
    ``i >= shock_index``.
    """
    arr = np.asarray(values)
    if interval_axis != 1:
        arr = np.moveaxis(arr, interval_axis, 1)
    shocks = np.asarray(shock_index, dtype=int)
    if arr.ndim < 2 or shocks.shape != (arr.shape[0],):
        raise RecoveryDiagnosticError("window-classification shapes do not match")
    interval = np.arange(arr.shape[1])[None, :]
    relevant = interval >= shocks[:, None]
    bad = ~np.isfinite(arr)
    while relevant.ndim < bad.ndim:
        relevant = relevant[..., None]
    return {
        "relevant_nonfinite_count": int(np.count_nonzero(bad & relevant)),
        "preshock_nonfinite_count": int(np.count_nonzero(bad & ~relevant)),
        "relevant_cell_count": int(np.count_nonzero(np.broadcast_to(relevant, bad.shape))),
        "preshock_cell_count": int(np.count_nonzero(np.broadcast_to(~relevant, bad.shape))),
    }


def classify_gamma_fallbacks(
    endpoint_gamma: Any, times: Any, gamma_c: Any, ap_arr: Any,
    a2_arr: Any, shock_index: Any,
) -> dict[str, Any]:
    """Replay upstream gamma updates and count silent fallback events by window."""
    endpoint = np.asarray(endpoint_gamma, dtype=float)
    times_a = np.asarray(times, dtype=float)
    gc = np.asarray(gamma_c, dtype=float)
    ap = np.asarray(ap_arr, dtype=float)
    a2 = np.asarray(a2_arr, dtype=float)
    shocks = np.asarray(shock_index, dtype=int)
    if endpoint.ndim != 2 or ap.shape != a2.shape or ap.shape[0] != endpoint.shape[0]:
        raise RecoveryDiagnosticError("gamma fallback inputs have incompatible shapes")
    gc_steps = gc[:, :-1] if gc.shape == (endpoint.shape[0], times_a.size) else gc
    if ap.shape[1] != times_a.size - 1 or gc_steps.shape != ap.shape:
        raise RecoveryDiagnosticError("gamma fallback interval shapes are invalid")
    current = endpoint.copy()
    relevant_count = pre_count = 0
    relevant_nonfinite = pre_nonfinite = 0
    records: list[dict[str, int]] = []
    for i in range(times_a.size - 2, -1, -1):
        with np.errstate(all="ignore"):
            new_gamma = get_gamma_numba(
                g_nm1=current, t_n=times_a[i], t_nm1=times_a[i + 1],
                gamma_c=gc_steps[:, i], a_p=ap[:, i], a_2=a2[:, i],
            )
        fallback = np.isnan(new_gamma) | (np.abs(new_gamma) < 1)
        relevant = i >= shocks
        relevant_events = fallback & relevant[:, None]
        pre_events = fallback & ~relevant[:, None]
        relevant_count += int(np.count_nonzero(relevant_events))
        pre_count += int(np.count_nonzero(pre_events))
        relevant_nonfinite += int(np.count_nonzero(np.isnan(new_gamma) & relevant[:, None]))
        pre_nonfinite += int(np.count_nonzero(np.isnan(new_gamma) & ~relevant[:, None]))
        for row, freq in np.argwhere(fallback):
            records.append({"row": int(row), "frequency_index": int(freq),
                            "interval_index": int(i),
                            "relevant": int(relevant[row])})
        # Match the pinned fallback state machine for subsequent intervals.
        current = np.where(fallback, current, new_gamma)
    return {
        "relevant_fallback_count": relevant_count,
        "preshock_fallback_count": pre_count,
        "relevant_gamma_nonfinite_count": relevant_nonfinite,
        "preshock_gamma_nonfinite_count": pre_nonfinite,
        "records": records,
    }


def _read_selection(path: Path, h5: h5py.File) -> list[dict[str, Any]]:
    required = {"cache_row", "physical_id"}
    rows: list[dict[str, Any]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RecoveryDiagnosticError("selection CSV must contain cache_row and physical_id")
        for index, raw in enumerate(reader):
            row = int(raw["cache_row"])
            if row < 0 or row >= h5["pressure"].shape[0]:
                raise RecoveryDiagnosticError(f"selection row {row} is outside cache")
            physical_id = int(raw["physical_id"])
            actual = int(h5["endpoint_ids"][row])
            if physical_id != actual:
                raise RecoveryDiagnosticError(f"selection ID mismatch at cache row {row}")
            rows.append({**raw, "sample_index": int(raw.get("sample_index", index)),
                         "cache_row": row, "physical_id": physical_id})
    if not rows or len({r["cache_row"] for r in rows}) != len(rows):
        raise RecoveryDiagnosticError("selection CSV is empty or has duplicate cache rows")
    return sorted(rows, key=lambda r: (int(r["sample_index"]), r["cache_row"]))


def _read_nonfinite_records(path: Path) -> list[dict[str, Any]]:
    """Read archived branch/mode/frequency failure evidence immutably."""
    required = {"pressure_mode", "physical_id", "frequency_GHz"}
    records: list[dict[str, Any]] = []
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RecoveryDiagnosticError(
                "nonfinite-record CSV must contain pressure_mode, physical_id, and frequency_GHz"
            )
        for raw in reader:
            try:
                record = {
                    **raw,
                    "pressure_mode": str(raw["pressure_mode"]),
                    "physical_id": int(raw["physical_id"]),
                    "frequency_GHz": float(raw["frequency_GHz"]),
                }
            except (TypeError, ValueError) as exc:
                raise RecoveryDiagnosticError("nonfinite-record CSV contains malformed values") from exc
            if record["pressure_mode"] not in ("unsmoothed", "log_savgol"):
                raise RecoveryDiagnosticError("nonfinite-record CSV contains an unknown pressure mode")
            records.append(record)
    if not records:
        raise RecoveryDiagnosticError("nonfinite-record CSV is empty")
    return records


def _hash_key(*values: Any) -> str:
    return hashlib.sha256(":".join(str(value) for value in values).encode()).hexdigest()


def choose_trace_selection(
    selection: Sequence[Mapping[str, Any]],
    nonfinite_records: Sequence[Mapping[str, Any]],
    *,
    trace_limit: int,
) -> list[dict[str, Any]]:
    """Choose bounded affected traces plus explicitly labelled finite controls."""
    if trace_limit <= 0:
        raise RecoveryDiagnosticError("trace_limit must be positive")
    by_id = {int(row["physical_id"]): row for row in selection}
    if len(by_id) != len(selection):
        raise RecoveryDiagnosticError("selection contains duplicate physical IDs")
    affected_keys = {
        (str(record["pressure_mode"]), float(record["frequency_GHz"]), int(record["physical_id"]))
        for record in nonfinite_records
    }
    affected_ids = {physical_id for _, _, physical_id in affected_keys}
    missing = sorted(affected_ids - set(by_id))
    if missing:
        raise RecoveryDiagnosticError(
            f"archived nonfinite records reference IDs absent from exact selection: {missing[:5]}"
        )
    chosen: list[dict[str, Any]] = []
    for mode in ("unsmoothed", "log_savgol"):
        for frequency in FREQUENCIES_GHZ:
            candidates = sorted(
                {
                    physical_id
                    for current_mode, current_frequency, physical_id in affected_keys
                    if current_mode == mode and np.isclose(current_frequency, frequency)
                },
                key=lambda physical_id: _hash_key("affected", mode, frequency, physical_id),
            )
            if candidates:
                physical_id = candidates[0]
                row = dict(by_id[physical_id])
                row.update({"trace_class": "archived_nonfinite", "trace_mode": mode,
                            "trace_frequency_GHz": float(frequency),
                            "trace_strata": [f"{mode}/{frequency:g}"],
                            "trace_selection_rule": "one deterministic hash-minimum archived failure ID per pressure-mode/frequency stratum"})
                existing = next((current for current in chosen if int(current["physical_id"]) == physical_id), None)
                if existing is None:
                    chosen.append(row)
                else:
                    existing["trace_strata"].append(f"{mode}/{frequency:g}")
    if len(chosen) > trace_limit:
        raise RecoveryDiagnosticError(
            "trace_limit is smaller than the required archived mode/frequency failure strata"
        )
    controls = [row for row in selection if int(row["physical_id"]) not in affected_ids]
    controls = sorted(
        controls,
        key=lambda row: (
            0 if "extreme" in str(row.get("selection_reason", "")) else 1,
            _hash_key("control", row["cache_row"], row["physical_id"]),
        ),
    )
    for row in controls:
        if len(chosen) >= trace_limit:
            break
        current = dict(row)
        current.update({"trace_class": "finite_control", "trace_mode": "both",
                        "trace_frequency_GHz": "both",
                        "trace_strata": ["finite_control"],
                        "trace_selection_rule": "deterministic hash-ranked finite control/extreme after archived-failure strata"})
        chosen.append(current)
    if not chosen:
        raise RecoveryDiagnosticError("trace selection produced no archived failures or finite controls")
    return chosen


def assess_archived_failure_reproduction(
    selected: Sequence[Mapping[str, Any]],
    original_adiabatic_values: Mapping[str, Any],
    *,
    frequencies: Sequence[float] = FREQUENCIES_GHZ,
) -> dict[str, Any]:
    """Require each selected archived failure stratum to reproduce upstream."""
    expected: set[tuple[str, float, int]] = set()
    for row in selected:
        if str(row.get("trace_class")) != "archived_nonfinite":
            continue
        strata = row.get("trace_strata", [])
        for item in strata:
            mode, frequency = str(item).split("/", 1)
            expected.add((mode, float(frequency), int(row["physical_id"])))
    by_mode: dict[str, dict[str, Any]] = {}
    reproduced: set[tuple[str, float, int]] = set()
    for mode in ("unsmoothed", "log_savgol"):
        values = np.asarray(original_adiabatic_values[mode], dtype=float)
        ids = np.asarray(original_adiabatic_values[f"{mode}_ids"], dtype=np.int64)
        index = {int(physical_id): i for i, physical_id in enumerate(ids.tolist())}
        mode_expected = {key for key in expected if key[0] == mode}
        for key in mode_expected:
            _, frequency, physical_id = key
            if physical_id not in index:
                continue
            frequency_index = int(np.argmin(np.abs(np.asarray(frequencies) - frequency)))
            if not np.isfinite(values[index[physical_id], frequency_index]):
                reproduced.add(key)
        missing = sorted(mode_expected - reproduced)
        by_mode[mode] = {
            "expected_count": len(mode_expected),
            "reproduced_count": len(mode_expected) - len(missing),
            "missing_count": len(missing),
            "missing_strata": [
                {"pressure_mode": mode, "frequency_GHz": frequency, "physical_id": physical_id}
                for _, frequency, physical_id in missing
            ],
        }
    missing_overall = sorted(expected - reproduced)
    return {
        "expected_count": len(expected),
        "reproduced_count": len(expected) - len(missing_overall),
        "missing_count": len(missing_overall),
        "by_pressure_mode": by_mode,
        "gate_passed": bool(expected and not missing_overall),
    }


def reconstruct_stable_injection_emissivity(
    endpoint_gamma: np.ndarray,
    injection_gamma: np.ndarray,
    gamma_c: np.ndarray,
    pressure: np.ndarray,
    shock_index: int,
    tracer_endpoint: float,
) -> np.ndarray:
    """Reconstruct finite emissivity with pinned endpoint gamma_c semantics."""
    endpoint_gamma = np.asarray(endpoint_gamma, dtype=float)
    injection_gamma = np.asarray(injection_gamma, dtype=float)
    gamma_endpoint = float(np.asarray(gamma_c, dtype=float)[-1])
    return get_emissivity_numba(
        s=S, freq=(np.asarray(FREQUENCIES_GHZ) * u.GHz).si.value * (1 + Z),
        eta=ETA, gamma_c=np.asarray([gamma_endpoint]),
        p=np.asarray([pressure[-1]]), p_inj=np.asarray([pressure[shock_index]]),
        gm=endpoint_gamma[None, :], gm_inj=injection_gamma[None, :],
        tracer=np.asarray([tracer_endpoint]),
        K=get_K(S, gamma_endpoint, GMIN, GMAX),
    )


def classify_recovery_decisions(gates: Mapping[str, bool]) -> dict[str, Any]:
    """Separate the adiabatic recovery verdict from the full-loss method gate."""
    required = set(ADIABATIC_RECOVERY_GATE_NAMES) | set(FULL_METHOD_GATE_NAMES)
    missing = sorted(required - set(gates))
    if missing:
        raise RecoveryDiagnosticError(
            f"recovery decision is missing required gates: {missing}"
        )
    recovery_passed = all(bool(gates[name]) for name in ADIABATIC_RECOVERY_GATE_NAMES)
    full_method_passed = recovery_passed and all(
        bool(gates[name]) for name in FULL_METHOD_GATE_NAMES
    )
    return {
        "decision": "PASS" if full_method_passed else "FAIL",
        "decision_scope": "full_loss_method_readiness",
        "adiabatic_recovery_decision": "PASS" if recovery_passed else "FAIL",
        "decision_gate_names": list(ADIABATIC_RECOVERY_GATE_NAMES),
        "full_method_decision": "PASS" if full_method_passed else "BLOCKED",
        "full_method_gate_names": list(FULL_METHOD_GATE_NAMES),
    }


def _audit_mode_result(
    pressure_mode: str,
    result: Mapping[str, Any],
    physical: Mapping[str, np.ndarray],
    selected: Sequence[Mapping[str, Any]],
    trace_rows: list[dict[str, Any]],
    hp_checks: list[dict[str, Any]],
    full_ap_counts: dict[str, int],
    full_a2_counts: dict[str, int],
    gamma_counts: dict[str, int],
    stable_form_counts: dict[str, int],
    units: Mapping[str, Any],
) -> tuple[bool, bool, int, bool]:
    """Audit one actual-PRAiSE pressure mode over bounded selected traces."""
    groups = result.get("full_info")
    if not isinstance(groups, list) or not groups:
        raise RecoveryDiagnosticError(f"{pressure_mode} result lacks grouped full provenance")
    adiabatic_values = np.asarray(getattr(result["adiabatic"], "value", result["adiabatic"]), dtype=float)
    stable_pass = True
    stable_emissivity_pass = True
    upstream_pass = True
    original_nonfinite_count = int(np.count_nonzero(~np.isfinite(adiabatic_values)))
    if result.get("metadata", {}).get("singleton_policy") != "instantaneous_recent_shock":
        raise RecoveryDiagnosticError(
            f"{pressure_mode} did not declare the approved instantaneous_recent_shock singleton policy"
        )
    for group in groups:
        rows = np.asarray(group.get("rows"), dtype=np.int64)
        info = group.get("info")
        if not isinstance(info, Mapping) or rows.ndim != 1 or rows.size == 0:
            raise RecoveryDiagnosticError(f"{pressure_mode} grouped provenance is malformed")
        times = np.asarray(info.get("particle_times"), dtype=float)
        endpoint = np.asarray(info.get("current_lorentz"), dtype=float)
        ap = np.asarray(info.get("ap_arr"), dtype=float)
        a2 = np.asarray(info.get("a2_arr"), dtype=float)
        pressure = np.asarray(info.get("particle_pressure"), dtype=float)
        gamma_c = np.asarray(group.get("adiabatic_eff"), dtype=float)
        shocks = np.asarray(group.get("shock_index"), dtype=np.int64)
        if times.ndim != 1 or endpoint.ndim != 2 or pressure.ndim != 2 or gamma_c.ndim != 2 or shocks.shape != (rows.size,):
            raise RecoveryDiagnosticError(f"{pressure_mode} grouped dynamics shapes are malformed")
        if times.size == 1 and info.get("singleton_convention") != "instantaneous_recent_shock":
            raise RecoveryDiagnosticError(
                f"{pressure_mode} singleton trace lacks instantaneous_recent_shock provenance"
            )
        stable = stable_adiabatic_trajectory(
            endpoint, times, ap, gamma_c, shocks, pressure=pressure, gamma_inf=GAMMA_INF,
        )
        hp = high_precision_adiabatic_trajectory(endpoint, times, ap, gamma_c, shocks)
        hp_check = compare_recovery_to_high_precision(stable["trajectory"], hp, stable["relevant_mask"])
        hp_checks.append(hp_check)
        time_stable = stable_adiabatic_trajectory(endpoint, times, ap, gamma_c, shocks, gamma_inf=GAMMA_INF)
        for key in stable_form_counts:
            stable_form_counts[key] += stable[key]
        stable_pass = stable_pass and bool(
            stable["endpoint_gate_passed"] and hp_check["passed"]
            and stable["relevant_nonpositive_time_count"] == 0
        )
        for current, target in ((ap, full_ap_counts), (a2, full_a2_counts)):
            counts = classify_relevant_windows(current, shocks)
            for key in target:
                target[key] += counts[key]
        fallback = classify_gamma_fallbacks(endpoint, times, gamma_c, ap, a2, shocks)
        for key in gamma_counts:
            fallback_key = {
                "relevant_nonfinite_count": "relevant_gamma_nonfinite_count",
                "preshock_nonfinite_count": "preshock_gamma_nonfinite_count",
            }.get(key, key)
            gamma_counts[key] += fallback[fallback_key]
        upstream = np.full_like(stable["trajectory"], np.nan)
        current_gamma = endpoint.copy()
        upstream[:, -1, :] = current_gamma
        for i in range(times.size - 2, -1, -1):
            with np.errstate(all="ignore"):
                current_gamma = get_gamma_numba(
                    g_nm1=current_gamma, t_n=times[i], t_nm1=times[i + 1],
                    gamma_c=gamma_c[:, i], a_p=ap[:, i], a_2=np.zeros_like(ap[:, i]),
                )
            upstream[:, i, :] = current_gamma
        compare_mask = stable["relevant_mask"] & np.isfinite(upstream).all(axis=2) & np.isfinite(stable["trajectory"]).all(axis=2)
        if np.any(compare_mask):
            upstream_pass = upstream_pass and bool(np.all(
                np.abs(upstream[compare_mask] - stable["trajectory"][compare_mask])
                <= UPSTREAM_ATOL + UPSTREAM_RTOL * np.abs(stable["trajectory"][compare_mask])
            ))
        for local_row, global_row in enumerate(rows.tolist()):
            shock = int(shocks[local_row])
            injection = stable["trajectory"][local_row, shock, :]
            try:
                stable_emissivity = reconstruct_stable_injection_emissivity(
                    endpoint[local_row], injection, gamma_c[local_row],
                    pressure[local_row], shock, float(physical["tracer"][global_row, -1]),
                )
                stable_emissivity_pass = stable_emissivity_pass and bool(np.all(np.isfinite(stable_emissivity)))
            except Exception:
                stable_emissivity_pass = False
            stable_pass = stable_pass and bool(
                np.all(np.isfinite(injection)) and np.all(injection > 0)
            )
            selection = selected[global_row]
            for interval in range(times.size - 1):
                if interval < shock:
                    continue
                for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                    trace_rows.append({
                        "sample_index": int(selection["sample_index"]),
                        "cache_row": int(selection["cache_row"]),
                        "physical_id": int(selection["physical_id"]),
                        "trace_class": str(selection["trace_class"]),
                        "trace_selection_rule": str(selection["trace_selection_rule"]),
                        "source_history_start": int(group.get("start_index", 0)),
                        "shock_index": shock, "interval_index": interval,
                        "pressure_mode": pressure_mode, "frequency_GHz": float(frequency),
                        "mode": "adiabatic_pressure_ratio_primary",
                        "ap_value": float(ap[local_row, interval]), "a2_value": float(a2[local_row, interval]),
                        "endpoint_gamma": float(endpoint[local_row, frequency_index]),
                        "stable_gamma": float(stable["trajectory"][local_row, interval, frequency_index]),
                        "stable_time_ratio_gamma": float(time_stable["trajectory"][local_row, interval, frequency_index]),
                        "high_precision_gamma": float(hp[local_row, interval, frequency_index]),
                        "upstream_gamma_zero_a2": float(upstream[local_row, interval, frequency_index]),
                        "gamma_class": _value_class(float(stable["trajectory"][local_row, interval, frequency_index])),
                        "window": "relevant", "units": "SI physical cache after approved treatment",
                    })
    return bool(stable_pass), bool(stable_emissivity_pass), original_nonfinite_count, bool(upstream_pass)


def diagnose_recovery(
    cache: Path, selection_csv: Path, nonfinite_records_csv: Path, output_dir: Path, *,
    trace_limit: int = TRACE_LIMIT, expected_cache_sha256: str | None = None,
    expected_selection_sha256: str | None = None,
    expected_nonfinite_records_sha256: str | None = None,
) -> dict[str, Any]:
    """Run the bounded recovery gate and write compact CSV/JSON evidence."""
    if trace_limit <= 0:
        raise RecoveryDiagnosticError("trace_limit must be positive")
    output_dir.mkdir(parents=True, exist_ok=False)
    cache_hash, selection_hash = _sha256(cache), _sha256(selection_csv)
    records_hash = _sha256(nonfinite_records_csv)
    if expected_cache_sha256 and cache_hash != expected_cache_sha256:
        raise RecoveryDiagnosticError("cache SHA-256 does not match the declared immutable input")
    if expected_selection_sha256 and selection_hash != expected_selection_sha256:
        raise RecoveryDiagnosticError("selection SHA-256 does not match the declared immutable input")
    if expected_nonfinite_records_sha256 and records_hash != expected_nonfinite_records_sha256:
        raise RecoveryDiagnosticError("nonfinite-record SHA-256 does not match the declared immutable input")
    trace_rows: list[dict[str, Any]] = []
    hp_checks: list[dict[str, Any]] = []
    full_ap_counts = {"relevant_nonfinite_count": 0, "preshock_nonfinite_count": 0}
    full_a2_counts = {"relevant_nonfinite_count": 0, "preshock_nonfinite_count": 0}
    gamma_counts = {"relevant_nonfinite_count": 0, "preshock_nonfinite_count": 0,
                    "relevant_fallback_count": 0, "preshock_fallback_count": 0}
    stable_form_counts = {"algebraic_disagreement_count": 0,
                          "relevant_algebraic_disagreement_count": 0,
                          "preshock_algebraic_disagreement_count": 0,
                          "relevant_nonpositive_time_count": 0,
                          "preshock_nonpositive_time_count": 0}
    stable_gate = True
    emissivity_gate = True
    upstream_gate = True
    mode_gate = True
    original_adiabatic_nonfinite = {"unsmoothed": 0, "log_savgol": 0}
    original_adiabatic_values: dict[str, Any] = {}
    source_identity_sha256: str | None = None
    with h5py.File(cache, "r") as h5:
        raw_identity = h5.attrs.get("source_identity_sha256")
        if raw_identity is not None:
            source_identity_sha256 = raw_identity.decode() if isinstance(raw_identity, bytes) else str(raw_identity)
        workflow._validate_completed_cache(h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            expected_trim_single_record_overlap_rows=workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_single_record_overlap_rows"],
        )
        selections = _read_selection(selection_csv, h5)
        archived_records = _read_nonfinite_records(nonfinite_records_csv)
        selected = choose_trace_selection(selections, archived_records, trace_limit=trace_limit)
        selected_rows = np.asarray([int(row["cache_row"]) for row in selected], dtype=np.int64)
        raw = _read_treated_sample(h5, selected_rows, plan)
        physical, units = workflow.convert_code_cache_to_physical(
            raw, shock_threshold=float(h5.attrs["shock_threshold"]),
            shock_component=int(h5.attrs["shock_component"]),
        )
        for pressure_mode in ("unsmoothed", "log_savgol"):
            result = workflow.calculate_praise_pair(
                physical, frequencies=FREQUENCIES_GHZ, z=Z, s=S, eta=ETA,
                gmin=GMIN, gmax=GMAX, lst_index=0, pressure_mode=pressure_mode,
                singleton_policy="instantaneous_recent_shock", diagnostic=True,
                include_adiabatic=True,
            )
            stable_pass, stable_emissivity_pass, original_nonfinite_count, upstream_pass = _audit_mode_result(
                pressure_mode, result, physical, selected, trace_rows,
                hp_checks, full_ap_counts, full_a2_counts, gamma_counts,
                stable_form_counts, units,
            )
            mode_gate = mode_gate and stable_pass
            emissivity_gate = emissivity_gate and stable_emissivity_pass
            upstream_gate = upstream_gate and upstream_pass
            original_adiabatic_nonfinite[pressure_mode] = original_nonfinite_count
            original_adiabatic_values[pressure_mode] = np.asarray(
                getattr(result["adiabatic"], "value", result["adiabatic"]), dtype=float
            )
            original_adiabatic_values[f"{pressure_mode}_ids"] = np.asarray(
                result["ids"], dtype=np.int64
            )
            stable_gate = stable_gate and stable_pass
    failure_reproduction = assess_archived_failure_reproduction(
        selected, original_adiabatic_values
    )
    hp_max_abs = max((float(c["max_abs_difference"]) for c in hp_checks if c["max_abs_difference"] is not None), default=None)
    hp_max_rel = max((float(c["max_relative_difference"]) for c in hp_checks if c["max_relative_difference"] is not None), default=None)
    gates = {
        "high_precision_agreement": bool(hp_checks and all(c["passed"] for c in hp_checks)),
        "stable_endpoint_trajectory": bool(stable_gate),
        "finite_injection_gamma_emissivity": bool(emissivity_gate),
        "stable_pressure_time_form_agreement": bool(
            stable_form_counts["relevant_algebraic_disagreement_count"] == 0
        ),
        "zero_relevant_full_dynamics_nonfinite": bool(full_ap_counts["relevant_nonfinite_count"] == 0 and full_a2_counts["relevant_nonfinite_count"] == 0),
        "zero_relevant_silent_gamma_fallbacks": bool(gamma_counts["relevant_fallback_count"] == 0),
        "upstream_stable_finite_overlap_agreement": bool(upstream_gate),
        "archived_failure_reproduction": bool(failure_reproduction["gate_passed"]),
    }
    decisions = classify_recovery_decisions(gates)
    summary = {
        "status": "diagnostic_complete", **decisions,
        "cache_sha256": cache_hash, "selection_sha256": selection_hash,
        "nonfinite_records_sha256": records_hash,
        "source_identity_sha256": source_identity_sha256,
        "selection_count": len(selections), "trace_count": len(selected),
        "pressure_mode": "unsmoothed",
        "pressure_modes_checked": ["unsmoothed", "log_savgol"],
        "pressure_treatment_contract": {
            "expected_trim_rows": workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
            "expected_no_positive_rows": workflow.PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
            "expected_single_record_rows": workflow.PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
            "expected_trim_single_record_overlap_rows": workflow.PRESSURE_TREATMENT_CONTRACT["expected_trim_single_record_overlap_rows"],
            "units": "workflow.convert_code_cache_to_physical SI conversion",
            "singleton_policy": "instantaneous_recent_shock; endpoint gamma is accepted as injection only under this explicit convention",
        },
        "trace_limit": int(trace_limit), "frequencies_GHz": list(FREQUENCIES_GHZ),
        "gamma_inf": GAMMA_INF, "tolerances": {"high_precision_rtol": STABLE_RTOL, "high_precision_atol": STABLE_ATOL, "upstream_rtol": UPSTREAM_RTOL, "upstream_atol": UPSTREAM_ATOL},
        "high_precision": {"trace_count": len(hp_checks), "max_abs_difference": hp_max_abs, "max_relative_difference": hp_max_rel},
        "full_ap_arr": full_ap_counts, "full_a2_arr": full_a2_counts,
        "gamma": gamma_counts, "gates": gates,
        "stable_forms": stable_form_counts,
        "original_pinned_adiabatic_nonfinite_count": original_adiabatic_nonfinite,
        "archived_failure_reproduction": failure_reproduction,
        "scope": "bounded archived-failure strata plus explicitly labelled finite controls; no claim that all 4096 trajectories were checked; no 4096-row full comparison or raytrace",
        "trace_selection_rule": "one deterministic hash-minimum archived failure physical ID per pressure-mode/frequency stratum, then deterministic hash-ranked finite controls/extremes",
        "scientific_policy": "stable ratio/log-difference is diagnostic/reference only; pinned PRAiSE defaults unchanged; pre-shock anomalies are evidence, not endpoint failures",
    }
    fields = ["sample_index", "cache_row", "physical_id", "source_history_start", "shock_index", "interval_index", "pressure_mode", "frequency_GHz", "mode", "ap_value", "a2_value", "endpoint_gamma", "stable_gamma", "stable_time_ratio_gamma", "high_precision_gamma", "upstream_gamma_zero_a2", "gamma_class", "window"]
    _write_csv(output_dir / "adiabatic_recovery_traces.csv", fields, trace_rows)
    summary_fields = ["gate", "passed", "value"]
    _write_csv(output_dir / "adiabatic_recovery_summary.csv", summary_fields, [{"gate": k, "passed": v, "value": json.dumps(v)} for k, v in gates.items()])
    (output_dir / "adiabatic_recovery_summary.json").write_text(json.dumps(_json_safe(summary), indent=2, sort_keys=True) + "\n")
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--nonfinite-records-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--trace-limit", type=int, default=TRACE_LIMIT)
    parser.add_argument("--expected-cache-sha256")
    parser.add_argument("--expected-selection-sha256")
    parser.add_argument("--expected-nonfinite-records-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = diagnose_recovery(
            args.cache, args.selection_csv, args.nonfinite_records_csv, args.output_dir,
            trace_limit=args.trace_limit,
            expected_cache_sha256=args.expected_cache_sha256,
            expected_selection_sha256=args.expected_selection_sha256,
            expected_nonfinite_records_sha256=args.expected_nonfinite_records_sha256,
        )
    except (OSError, ValueError, RecoveryDiagnosticError) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(_json_safe(summary), indent=2, sort_keys=True))
    return 0 if summary["decision"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
