#!/usr/bin/env python3
"""Stable G-LO pressure-method value comparison for Goal 051.

The diagnostic reuses the immutable Goal 049 cache and exact 4096-row
selection.  Pinned PRAiSE full-loss values are retained only as provenance:
the comparison uses stable full-loss and stable adiabatic reconstructions plus
the matched actual ``losses='none'`` branch.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import h5py
import numpy as np

from scripts.science import diagnose_g_lo_adiabatic_recovery as adiabatic
from scripts.science import diagnose_g_lo_full_loss_recurrence as full_loss
from scripts.science import diagnose_g_lo_pressure_method_value as pressure_method
from scripts.science import run_g_lo_radio_history_value as workflow
from scripts.science.g_lo_radio_method_value import calculate_praise_pair


SAMPLE_SIZE = 4096
FREQUENCIES_GHZ = (0.15, 1.4)
PRESSURE_MODES = ("unsmoothed", "log_savgol")
PASS_LABEL = "G_LO_STABLE_METHOD_VALUE_PASS"
HOLD_LABEL = "G_LO_STABLE_METHOD_VALUE_HOLD_FOR_CUTOFF_REVIEW"
FAIL_LABEL = "G_LO_STABLE_METHOD_VALUE_FAIL"
VERIFIED_COMMIT_ENV = "GOAL051_VERIFIED_PLUTOKORE_COMMIT"

SELECTION_NAME = "stable_method_value_selection.csv"
PARTICLE_NAME = "stable_method_value_particle_comparison.csv"
ORDERING_NAME = "stable_method_value_ordering.csv"
CUTOFF_NAME = "stable_method_value_cutoff_records.csv"
GATE_NAME = "stable_method_value_gate_summary.csv"
SUMMARY_NAME = "stable_method_value_summary.json"

CUTOFF_FIELDS = (
    "pressure_mode",
    "sample_index",
    "cache_row",
    "physical_id",
    "interval_index",
    "frequency_GHz",
    "classification",
    "reference_classification",
    "reference_classification_match",
    "ulp_classification_stable",
    "explicit_zero_emissivity",
    "log_loss_fraction",
    "conditioning_tolerance",
)


class StableMethodDiagnosticError(RuntimeError):
    """Raised when the diagnostic input or output contract is invalid."""


class StableMethodScientificFailure(RuntimeError):
    """Raised when valid inputs produce a scientifically invalid branch."""

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.details = dict(details or {})


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(_json_safe(value), indent=2, sort_keys=True) + "\n"
    )


def _write_csv(
    path: Path,
    fieldnames: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def _npy_payload(value: Any) -> bytes:
    buffer = io.BytesIO()
    np.save(buffer, np.asarray(value), allow_pickle=False)
    return buffer.getvalue()


def _write_deterministic_npz(path: Path, arrays: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for name, value in arrays.items():
            info = zipfile.ZipInfo(
                filename=f"{name}.npy",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, _npy_payload(value), compress_type=zipfile.ZIP_DEFLATED)
    temporary.replace(path)


def _prepare_output_dir(path: Path) -> Path:
    output_dir = Path(path).resolve()
    if output_dir.exists():
        if (
            output_dir.is_symlink()
            or not output_dir.is_dir()
            or any(output_dir.iterdir())
        ):
            raise StableMethodDiagnosticError(
                f"refusing to overwrite non-empty output directory: {output_dir}"
            )
    else:
        output_dir.mkdir(parents=True)
    return output_dir


def read_exact_selection(
    path: Path,
    h5: h5py.File,
    *,
    expected_count: int = SAMPLE_SIZE,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Use the existing selection reader and enforce its exact file order."""
    if expected_count <= 0:
        raise StableMethodDiagnosticError("expected selection count must be positive")
    raw_rows: list[dict[str, str]] = []
    with Path(path).open(newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "sample_index",
            "cache_row",
            "physical_id",
            "analysis_weight",
        }
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            missing = sorted(required - set(reader.fieldnames or ()))
            raise StableMethodDiagnosticError(
                f"selection CSV is missing required columns: {missing}"
            )
        raw_rows = list(reader)
    if len(raw_rows) != expected_count:
        raise StableMethodDiagnosticError(
            f"selection must contain exactly {expected_count} rows, "
            f"found {len(raw_rows)}"
        )
    try:
        file_indices = [int(row["sample_index"]) for row in raw_rows]
    except (TypeError, ValueError) as exc:
        raise StableMethodDiagnosticError(
            "selection sample_index values are malformed"
        ) from exc
    if file_indices != list(range(expected_count)):
        raise StableMethodDiagnosticError(
            "selection CSV sample_index order must be exactly 0..n-1"
        )
    try:
        selected = adiabatic._read_selection(Path(path), h5)
    except (adiabatic.RecoveryDiagnosticError, OSError, TypeError, ValueError) as exc:
        raise StableMethodDiagnosticError(str(exc)) from exc
    if len(selected) != expected_count:
        raise StableMethodDiagnosticError(
            "existing selection reader changed the exact selection count"
        )
    normalised: list[dict[str, Any]] = []
    for expected_index, row in enumerate(selected):
        try:
            sample_index = int(row["sample_index"])
            weight = float(row["analysis_weight"])
        except (KeyError, TypeError, ValueError) as exc:
            raise StableMethodDiagnosticError(
                "selection contains a malformed sample index or analysis weight"
            ) from exc
        if sample_index != expected_index:
            raise StableMethodDiagnosticError(
                "selection sample_index order changed during validation"
            )
        if not math.isfinite(weight) or weight <= 0:
            raise StableMethodDiagnosticError(
                "selection analysis weights must be finite and positive"
            )
        normalised.append({
            **row,
            "sample_index": sample_index,
            "cache_row": int(row["cache_row"]),
            "physical_id": int(row["physical_id"]),
            "analysis_weight": weight,
        })
    physical_ids = [row["physical_id"] for row in normalised]
    if len(set(physical_ids)) != expected_count:
        raise StableMethodDiagnosticError(
            "selection physical IDs must be unique"
        )
    cache_rows = np.asarray(
        [row["cache_row"] for row in normalised],
        dtype=np.int64,
    )
    return cache_rows, normalised


def _validate_group_coverage(
    groups: Any,
    particle_count: int,
    *,
    label: str,
) -> list[tuple[Mapping[str, Any], np.ndarray]]:
    if not isinstance(groups, list) or not groups:
        raise StableMethodDiagnosticError(
            f"{label} grouped provenance is missing"
        )
    covered = np.zeros(particle_count, dtype=bool)
    validated: list[tuple[Mapping[str, Any], np.ndarray]] = []
    for group in groups:
        if not isinstance(group, Mapping):
            raise StableMethodDiagnosticError(
                f"{label} grouped provenance is malformed"
            )
        rows = np.asarray(group.get("rows"), dtype=np.int64)
        if (
            rows.ndim != 1
            or rows.size == 0
            or np.unique(rows).size != rows.size
            or np.any(rows < 0)
            or np.any(rows >= particle_count)
        ):
            raise StableMethodDiagnosticError(
                f"{label} grouped provenance rows are invalid"
            )
        if np.any(covered[rows]):
            raise StableMethodDiagnosticError(
                f"{label} grouped provenance rows overlap"
            )
        covered[rows] = True
        validated.append((group, rows))
    if not np.all(covered):
        raise StableMethodDiagnosticError(
            f"{label} grouped provenance does not cover every selected row"
        )
    return validated


def _branch_fingerprint(
    ids: np.ndarray,
    branches: Mapping[str, np.ndarray],
) -> str:
    digest = hashlib.sha256()
    digest.update(b"g-lo-stable-method-value-branches-v1\0")
    for label, value in (
        ("ids", np.asarray(ids, dtype="<i8")),
        ("frequencies_GHz", np.asarray(FREQUENCIES_GHZ, dtype="<f8")),
        ("full", np.asarray(branches["full"], dtype="<f8")),
        ("adiabatic", np.asarray(branches["adiabatic"], dtype="<f8")),
        ("none", np.asarray(branches["none"], dtype="<f8")),
    ):
        digest.update(label.encode("ascii") + b"\0")
        digest.update(str(value.shape).encode("ascii") + b"\0")
        digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def _validate_branch(
    values: Any,
    particle_count: int,
    *,
    label: str,
) -> np.ndarray:
    array = np.asarray(getattr(values, "value", values), dtype=np.float64)
    if (
        array.shape != (particle_count, len(FREQUENCIES_GHZ))
        or not np.all(np.isfinite(array))
        or np.any(array < 0)
    ):
        raise StableMethodDiagnosticError(
            f"{label} branch must be finite nonnegative (n,2)"
        )
    return array


def _actual_none_value_class(value: float) -> str:
    if np.isnan(value):
        return "nan"
    if np.isposinf(value):
        return "+inf"
    if np.isneginf(value):
        return "-inf"
    if value < 0:
        return "negative"
    raise StableMethodDiagnosticError(
        "actual-none anomaly classifier received a valid value"
    )


def _actual_none_raw_value(value: float) -> str:
    value_class = _actual_none_value_class(value)
    if value_class in ("nan", "+inf", "-inf"):
        return value_class
    return format(float(value), ".17g")


def _validate_actual_none_branch(
    values: Any,
    selection: Sequence[Mapping[str, Any]],
    *,
    pressure_mode: str,
) -> np.ndarray:
    particle_count = len(selection)
    try:
        array = np.asarray(
            getattr(values, "value", values),
            dtype=np.float64,
        )
    except (TypeError, ValueError) as exc:
        raise StableMethodDiagnosticError(
            f"{pressure_mode}/none branch shape cannot be evaluated"
        ) from exc
    expected_shape = (particle_count, len(FREQUENCIES_GHZ))
    if array.shape != expected_shape:
        raise StableMethodDiagnosticError(
            f"{pressure_mode}/none branch shape must be {expected_shape}"
        )
    anomaly_mask = ~np.isfinite(array) | (array < 0)
    if not np.any(anomaly_mask):
        return array
    records: list[dict[str, Any]] = []
    for row_index, frequency_index in np.argwhere(anomaly_mask):
        value = float(array[row_index, frequency_index])
        selection_row = selection[int(row_index)]
        records.append({
            "pressure_mode": pressure_mode,
            "sample_index": int(selection_row["sample_index"]),
            "cache_row": int(selection_row["cache_row"]),
            "physical_id": int(selection_row["physical_id"]),
            "frequency_GHz": float(FREQUENCIES_GHZ[frequency_index]),
            "value_class": _actual_none_value_class(value),
            "raw_value": _actual_none_raw_value(value),
        })
    raise StableMethodScientificFailure(
        "actual none branch contains non-finite or negative values",
        details={
            "failed_gate": "actual_none_finite_nonnegative",
            "branch_shape": list(array.shape),
            "anomaly_count": len(records),
            "actual_none_anomalies": records,
        },
    )


def _group_inputs(
    group: Mapping[str, Any],
    rows: np.ndarray,
    *,
    pressure_mode: str,
) -> dict[str, np.ndarray]:
    info = group.get("info")
    if not isinstance(info, Mapping):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} grouped dynamics are missing"
        )
    times = np.asarray(info.get("particle_times"), dtype=np.float64)
    endpoint = np.asarray(info.get("current_lorentz"), dtype=np.float64)
    pressure = np.asarray(info.get("particle_pressure"), dtype=np.float64)
    gamma_c = np.asarray(group.get("adiabatic_eff"), dtype=np.float64)
    shocks = np.asarray(group.get("shock_index"), dtype=np.int64)
    ap_arr = np.asarray(info.get("ap_arr"), dtype=np.float64)
    expected_endpoint = (rows.size, len(FREQUENCIES_GHZ))
    expected_history = (rows.size, times.size)
    expected_intervals = (rows.size, max(0, times.size - 1))
    if (
        times.ndim != 1
        or times.size == 0
        or not np.all(np.isfinite(times))
        or np.any(times <= 0)
        or (times.size > 1 and np.any(np.diff(times) <= 0))
        or endpoint.shape != expected_endpoint
        or pressure.shape != expected_history
        or gamma_c.shape != expected_history
        or shocks.shape != (rows.size,)
        or ap_arr.shape != expected_intervals
        or not np.all(np.isfinite(endpoint))
        or np.any(endpoint <= 0)
        or not np.all(np.isfinite(pressure))
        or np.any(pressure <= 0)
        or not np.all(np.isfinite(gamma_c))
        or np.any(gamma_c <= 0)
        or not np.all(np.isfinite(ap_arr))
        or np.any(shocks < 0)
        or np.any(shocks >= times.size)
    ):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} grouped stable-recurrence inputs are invalid"
        )
    if times.size == 1 and (
        info.get("singleton_convention") != "instantaneous_recent_shock"
        or np.any(shocks != 0)
    ):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} singleton provenance is not the approved "
            "instantaneous_recent_shock convention"
        )
    if np.any(endpoint >= full_loss.GAMMA_INF):
        raise StableMethodScientificFailure(
            f"{pressure_mode} endpoint gamma reaches gamma_inf"
        )
    return {
        "times": times,
        "endpoint": endpoint,
        "pressure": pressure,
        "gamma_c": gamma_c,
        "shock_index": shocks,
        "ap_arr": ap_arr,
    }


def _conditioning_and_cutoff_audit(
    stable: Mapping[str, Any],
    inputs: Mapping[str, np.ndarray],
    rows: np.ndarray,
    selection: Sequence[Mapping[str, Any]],
    *,
    pressure_mode: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    trajectory = np.asarray(stable["trajectory"], dtype=np.float64)
    states = np.asarray(stable["state"])
    times = inputs["times"]
    pressure = inputs["pressure"]
    gamma_c = inputs["gamma_c"]
    shocks = inputs["shock_index"]
    near_boundary_count = 0
    boundary_audit_count = 0
    instability_count = 0
    relevant_interval_frequency_count = 0
    minimum_abs_log_margin: float | None = None
    cutoff_records: list[dict[str, Any]] = []
    for local_row, global_row in enumerate(rows.tolist()):
        for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
            for interval in range(int(shocks[local_row]), times.size - 1):
                if (
                    states[local_row, interval + 1, frequency_index]
                    != full_loss.STATE_FINITE
                ):
                    continue
                gamma_later = float(
                    trajectory[local_row, interval + 1, frequency_index]
                )
                parameters = {
                    "gamma_later": gamma_later,
                    "t0": float(times[interval]),
                    "t1": float(times[interval + 1]),
                    "p0": float(pressure[local_row, interval]),
                    "p1": float(pressure[local_row, interval + 1]),
                    "gamma_c": float(gamma_c[local_row, interval]),
                    "eta": float(workflow.PRIMARY_CONTRACT["eta"]),
                    "z": float(workflow.PRIMARY_CONTRACT["redshift"]),
                }
                loss = full_loss.stable_scaled_loss(
                    t0=parameters["t0"],
                    t1=parameters["t1"],
                    p0=parameters["p0"],
                    p1=parameters["p1"],
                    gamma_c=parameters["gamma_c"],
                    eta=parameters["eta"],
                    z=parameters["z"],
                )
                log_margin = math.log(gamma_later) + float(loss["log_lambda"])
                tolerance = 8.0 * np.finfo(float).eps * max(
                    1.0,
                    abs(math.log(gamma_later)),
                    abs(float(loss["log_lambda"])),
                )
                absolute_margin = abs(log_margin)
                minimum_abs_log_margin = (
                    absolute_margin
                    if minimum_abs_log_margin is None
                    else min(minimum_abs_log_margin, absolute_margin)
                )
                relevant_interval_frequency_count += 1
                classification = str(
                    states[local_row, interval, frequency_index]
                )
                is_cutoff = classification in (
                    full_loss.STATE_PHYSICAL_CUTOFF,
                    full_loss.STATE_GAMMA_INF_CUTOFF,
                )
                near_boundary = absolute_margin <= tolerance
                near_boundary_count += int(near_boundary)
                boundary = None
                if near_boundary or is_cutoff:
                    boundary_audit_count += 1
                    boundary = full_loss.interval_boundary_stability(**parameters)
                    instability_count += int(not bool(boundary["stable"]))
                if not is_cutoff:
                    continue
                reference = full_loss.high_precision_full_loss_interval(
                    **parameters
                )
                reference_classification = str(reference["classification"])
                reconstructed = (
                    full_loss.reconstruct_full_loss_injection_emissivity(
                        np.asarray([inputs["endpoint"][
                            local_row, frequency_index
                        ]]),
                        np.asarray([np.nan]),
                        gamma_c[local_row],
                        pressure[local_row],
                        int(shocks[local_row]),
                        0.0,
                        classification=classification,
                        frequencies=(frequency,),
                    )
                )
                explicit_zero = bool(
                    reconstructed.shape == (1,)
                    and np.all(np.isfinite(reconstructed))
                    and np.array_equal(reconstructed, np.zeros(1))
                )
                record = {
                    "pressure_mode": pressure_mode,
                    "sample_index": int(selection[global_row]["sample_index"]),
                    "cache_row": int(selection[global_row]["cache_row"]),
                    "physical_id": int(selection[global_row]["physical_id"]),
                    "interval_index": int(interval),
                    "frequency_GHz": float(frequency),
                    "classification": classification,
                    "reference_classification": reference_classification,
                    "reference_classification_match": (
                        classification == reference_classification
                    ),
                    "ulp_classification_stable": bool(
                        boundary is not None and boundary["stable"]
                    ),
                    "explicit_zero_emissivity": explicit_zero,
                    "log_loss_fraction": log_margin,
                    "conditioning_tolerance": tolerance,
                }
                cutoff_records.append(record)
    cutoff_audit_passed = all(
        row["reference_classification_match"]
        and row["ulp_classification_stable"]
        and row["explicit_zero_emissivity"]
        for row in cutoff_records
    )
    audit = {
        "relevant_interval_frequency_count": relevant_interval_frequency_count,
        "near_boundary_candidate_count": near_boundary_count,
        "boundary_audit_count": boundary_audit_count,
        "instability_count": instability_count,
        "minimum_absolute_log_loss_fraction_margin": minimum_abs_log_margin,
        "cutoff_audit_count": len(cutoff_records),
        "cutoff_audit_passed": bool(cutoff_audit_passed),
        "audit_policy": (
            "track every relevant log-loss-fraction margin; run one-ULP "
            "classification checks only for every conditioning candidate and "
            "every cutoff; run 80-digit state checks only for cutoffs"
        ),
        "goal050_reference_policy": (
            "all-row high-precision recurrence validation is inherited from "
            "Goal 050 and is not repeated here"
        ),
    }
    if instability_count:
        raise StableMethodScientificFailure(
            f"{pressure_mode} has a near-boundary classification instability",
            details={"conditioning": audit, "cutoff_records": cutoff_records},
        )
    if not cutoff_audit_passed:
        raise StableMethodScientificFailure(
            f"{pressure_mode} cutoff audit failed",
            details={"conditioning": audit, "cutoff_records": cutoff_records},
        )
    return audit, cutoff_records


def reconstruct_stable_mode(
    result: Mapping[str, Any],
    physical: Mapping[str, np.ndarray],
    selection: Sequence[Mapping[str, Any]],
    *,
    pressure_mode: str,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Reconstruct one pressure mode from grouped actual-PRAiSE provenance."""
    if pressure_mode not in PRESSURE_MODES:
        raise StableMethodDiagnosticError(
            f"pressure mode must be one of {PRESSURE_MODES}"
        )
    particle_count = len(selection)
    expected_ids = np.asarray(
        [int(row["physical_id"]) for row in selection],
        dtype=np.int64,
    )
    actual_ids = np.asarray(result.get("ids"), dtype=np.int64)
    if not np.array_equal(actual_ids, expected_ids):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} PRAiSE IDs do not exactly match selection IDs/order"
        )
    if (
        result.get("metadata", {}).get("singleton_policy")
        != "instantaneous_recent_shock"
    ):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} did not retain the approved singleton policy"
        )
    groups = _validate_group_coverage(
        result.get("full_info"),
        particle_count,
        label=f"{pressure_mode}/full",
    )
    _validate_group_coverage(
        result.get("none_info"),
        particle_count,
        label=f"{pressure_mode}/none",
    )
    none = _validate_actual_none_branch(
        result.get("none"),
        selection,
        pressure_mode=pressure_mode,
    )
    tracer = np.asarray(physical.get("tracer"), dtype=np.float64)
    if (
        tracer.ndim != 2
        or tracer.shape[0] != particle_count
        or tracer.shape[1] == 0
        or not np.all(np.isfinite(tracer[:, -1]))
        or np.any(tracer[:, -1] < 0)
    ):
        raise StableMethodDiagnosticError(
            f"{pressure_mode} endpoint tracer contract is invalid"
        )
    stable_full_values = np.full_like(none, np.nan)
    stable_adiabatic_values = np.full_like(none, np.nan)
    state_counts: Counter[str] = Counter()
    silent_fallback_count = 0
    subrelativistic_count = 0
    full_repeat_passed = True
    adiabatic_repeat_passed = True
    singleton_count = 0
    conditioning_summaries: list[dict[str, Any]] = []
    cutoff_records: list[dict[str, Any]] = []
    adiabatic_counts: Counter[str] = Counter()
    for group, rows in groups:
        inputs = _group_inputs(group, rows, pressure_mode=pressure_mode)
        times = inputs["times"]
        endpoint = inputs["endpoint"]
        pressure = inputs["pressure"]
        gamma_c = inputs["gamma_c"]
        shocks = inputs["shock_index"]
        singleton_count += int(rows.size if times.size == 1 else 0)
        try:
            stable_full = full_loss.stable_full_loss_trajectory(
                endpoint,
                times,
                pressure,
                gamma_c,
                shocks,
                eta=float(workflow.PRIMARY_CONTRACT["eta"]),
                z=float(workflow.PRIMARY_CONTRACT["redshift"]),
                gamma_inf=full_loss.GAMMA_INF,
            )
            full_repeat = full_loss.stable_full_loss_trajectory(
                endpoint,
                times,
                pressure,
                gamma_c,
                shocks,
                eta=float(workflow.PRIMARY_CONTRACT["eta"]),
                z=float(workflow.PRIMARY_CONTRACT["redshift"]),
                gamma_inf=full_loss.GAMMA_INF,
            )
        except (full_loss.FullLossDiagnosticError, ValueError, OverflowError) as exc:
            raise StableMethodScientificFailure(
                f"{pressure_mode} stable full-loss recurrence failed: {exc}"
            ) from exc
        group_repeat = bool(
            np.array_equal(
                stable_full["trajectory"],
                full_repeat["trajectory"],
                equal_nan=True,
            )
            and np.array_equal(stable_full["state"], full_repeat["state"])
        )
        full_repeat_passed = full_repeat_passed and group_repeat
        states = np.asarray(stable_full["state"])
        relevant = np.zeros(states.shape, dtype=bool)
        for local_row, shock in enumerate(shocks.tolist()):
            relevant[local_row, shock:, :] = True
        state_counts.update(str(value) for value in states[relevant].tolist())
        silent_fallback_count += int(stable_full["silent_fallback_count"])
        subrelativistic_count += int(
            np.count_nonzero(
                relevant & (states == full_loss.STATE_SUBRELATIVISTIC)
            )
        )
        if silent_fallback_count:
            raise StableMethodScientificFailure(
                f"{pressure_mode} stable full-loss recurrence used a silent fallback"
            )
        if subrelativistic_count:
            raise StableMethodScientificFailure(
                f"{pressure_mode} produced a subrelativistic stable full-loss state"
            )
        if not group_repeat:
            raise StableMethodScientificFailure(
                f"{pressure_mode} stable full-loss recurrence is not deterministic"
            )
        conditioning, group_cutoffs = _conditioning_and_cutoff_audit(
            stable_full,
            inputs,
            rows,
            selection,
            pressure_mode=pressure_mode,
        )
        conditioning_summaries.append(conditioning)
        cutoff_records.extend(group_cutoffs)
        try:
            stable_ad = adiabatic.stable_adiabatic_trajectory(
                endpoint,
                times,
                inputs["ap_arr"],
                gamma_c,
                shocks,
                pressure=pressure,
                gamma_inf=adiabatic.GAMMA_INF,
            )
            ad_repeat = adiabatic.stable_adiabatic_trajectory(
                endpoint,
                times,
                inputs["ap_arr"],
                gamma_c,
                shocks,
                pressure=pressure,
                gamma_inf=adiabatic.GAMMA_INF,
            )
        except (adiabatic.RecoveryDiagnosticError, ValueError, OverflowError) as exc:
            raise StableMethodScientificFailure(
                f"{pressure_mode} stable adiabatic recurrence failed: {exc}"
            ) from exc
        group_ad_repeat = bool(
            np.array_equal(
                stable_ad["trajectory"],
                ad_repeat["trajectory"],
                equal_nan=True,
            )
        )
        adiabatic_repeat_passed = (
            adiabatic_repeat_passed and group_ad_repeat
        )
        for key in (
            "relevant_nonfinite_count",
            "relevant_fallback_count",
            "relevant_algebraic_disagreement_count",
            "relevant_nonpositive_time_count",
        ):
            adiabatic_counts[key] += int(stable_ad[key])
        adiabatic_group_gate = bool(
            stable_ad["endpoint_gate_passed"]
            and group_ad_repeat
            and all(
                int(stable_ad[key]) == 0
                for key in (
                    "relevant_nonfinite_count",
                    "relevant_fallback_count",
                    "relevant_nonpositive_time_count",
                )
            )
        )
        if not adiabatic_group_gate:
            raise StableMethodScientificFailure(
                f"{pressure_mode} stable adiabatic gate failed",
                details={
                    key: stable_ad[key]
                    for key in (
                        "endpoint_gate_passed",
                        "relevant_nonfinite_count",
                        "relevant_fallback_count",
                        "relevant_algebraic_disagreement_count",
                        "relevant_nonpositive_time_count",
                    )
                },
            )
        for local_row, global_row in enumerate(rows.tolist()):
            shock = int(shocks[local_row])
            for frequency_index, frequency in enumerate(FREQUENCIES_GHZ):
                classification = str(
                    stable_full["state"][
                        local_row, shock, frequency_index
                    ]
                )
                injection = np.asarray([
                    stable_full["trajectory"][
                        local_row, shock, frequency_index
                    ]
                ])
                reconstructed = (
                    full_loss.reconstruct_full_loss_injection_emissivity(
                        np.asarray([endpoint[local_row, frequency_index]]),
                        injection,
                        gamma_c[local_row],
                        pressure[local_row],
                        shock,
                        float(tracer[global_row, -1]),
                        eta=float(workflow.PRIMARY_CONTRACT["eta"]),
                        z=float(workflow.PRIMARY_CONTRACT["redshift"]),
                        s=float(workflow.PRIMARY_CONTRACT["s"]),
                        gmin=float(workflow.PRIMARY_CONTRACT["gmin"]),
                        gmax=float(workflow.PRIMARY_CONTRACT["gmax"]),
                        classification=classification,
                        frequencies=(frequency,),
                    )
                )
                stable_full_values[global_row, frequency_index] = float(
                    reconstructed[0]
                )
            ad_injection = np.asarray(
                stable_ad["trajectory"][local_row, shock, :],
                dtype=np.float64,
            )
            raw_ad = adiabatic.reconstruct_stable_injection_emissivity(
                endpoint[local_row],
                ad_injection,
                gamma_c[local_row],
                pressure[local_row],
                shock,
                float(tracer[global_row, -1]),
            )
            reconstructed_ad = np.asarray(
                getattr(raw_ad, "value", raw_ad),
                dtype=np.float64,
            ).reshape(-1)
            if reconstructed_ad.shape != (len(FREQUENCIES_GHZ),):
                raise StableMethodScientificFailure(
                    f"{pressure_mode} stable adiabatic emissivity shape is invalid"
                )
            stable_adiabatic_values[global_row] = reconstructed_ad
    branches = {
        "ids": expected_ids,
        "full": _validate_branch(
            stable_full_values,
            particle_count,
            label=f"{pressure_mode}/stable-full",
        ),
        "adiabatic": _validate_branch(
            stable_adiabatic_values,
            particle_count,
            label=f"{pressure_mode}/stable-adiabatic",
        ),
        "none": none,
    }
    fingerprint = _branch_fingerprint(expected_ids, branches)
    conditioning = {
        "relevant_interval_frequency_count": sum(
            row["relevant_interval_frequency_count"]
            for row in conditioning_summaries
        ),
        "near_boundary_candidate_count": sum(
            row["near_boundary_candidate_count"]
            for row in conditioning_summaries
        ),
        "boundary_audit_count": sum(
            row["boundary_audit_count"] for row in conditioning_summaries
        ),
        "instability_count": sum(
            row["instability_count"] for row in conditioning_summaries
        ),
        "minimum_absolute_log_loss_fraction_margin": min(
            (
                row["minimum_absolute_log_loss_fraction_margin"]
                for row in conditioning_summaries
                if row["minimum_absolute_log_loss_fraction_margin"] is not None
            ),
            default=None,
        ),
        "cutoff_audit_count": len(cutoff_records),
        "cutoff_audit_passed": all(
            row["cutoff_audit_passed"] for row in conditioning_summaries
        ),
        "audit_policy": (
            conditioning_summaries[0]["audit_policy"]
            if conditioning_summaries
            else ""
        ),
        "goal050_reference_policy": (
            conditioning_summaries[0]["goal050_reference_policy"]
            if conditioning_summaries
            else ""
        ),
    }
    ordered_states = (
        full_loss.STATE_FINITE,
        full_loss.STATE_PHYSICAL_CUTOFF,
        full_loss.STATE_GAMMA_INF_CUTOFF,
        full_loss.STATE_SUBRELATIVISTIC,
        full_loss.STATE_POST_CUTOFF,
    )
    summary = {
        "pressure_mode": pressure_mode,
        "particle_count": particle_count,
        "group_count": len(groups),
        "singleton_particle_count": singleton_count,
        "grouped_provenance_complete": True,
        "stable_full": {
            "state_counts": {
                state: int(state_counts[state]) for state in ordered_states
            },
            "silent_fallback_count": silent_fallback_count,
            "subrelativistic_count": subrelativistic_count,
            "deterministic_repeat": full_repeat_passed,
            "conditioning": conditioning,
        },
        "stable_adiabatic": {
            **{key: int(value) for key, value in adiabatic_counts.items()},
            "deterministic_repeat": adiabatic_repeat_passed,
            "gate_passed": bool(
                adiabatic_repeat_passed
                and all(
                    adiabatic_counts[key] == 0
                    for key in (
                        "relevant_nonfinite_count",
                        "relevant_fallback_count",
                        "relevant_nonpositive_time_count",
                    )
                )
            ),
        },
        "cutoff_review_required": bool(cutoff_records),
        "branch_contract_passed": True,
        "branch_fingerprint_sha256": fingerprint,
    }
    cutoff_records.sort(
        key=lambda row: (
            row["sample_index"],
            row["interval_index"],
            row["frequency_GHz"],
        )
    )
    return branches, summary, cutoff_records


def summarise_stable_comparison(
    selection: Sequence[Mapping[str, Any]],
    modes: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Apply the existing method-value gates to the reconstructed branches."""
    missing = [mode for mode in PRESSURE_MODES if mode not in modes]
    if missing:
        raise StableMethodDiagnosticError(
            f"stable comparison is missing pressure modes: {missing}"
        )
    try:
        return pressure_method.summarise_method_comparison(
            selection,
            modes["unsmoothed"],
            modes["log_savgol"],
        )
    except pressure_method.PressureMethodDiagnosticError:
        raise


def classify_stable_decision(
    comparison_decision: str,
    *,
    cutoff_count: int,
) -> tuple[str, str]:
    """Classify the tri-state outcome without treating a hold as a pass."""
    if comparison_decision not in ("PASS", "FAIL") or cutoff_count < 0:
        raise StableMethodDiagnosticError(
            "stable decision requires PASS/FAIL comparison and nonnegative cutoffs"
        )
    if comparison_decision == "FAIL":
        return "FAIL", FAIL_LABEL
    if cutoff_count:
        return "HOLD_FOR_CUTOFF_REVIEW", HOLD_LABEL
    return "PASS", PASS_LABEL


def _write_checkpoint(
    path: Path,
    branches: Mapping[str, Any],
    fingerprint: str,
) -> None:
    _write_deterministic_npz(path, {
        "physical_ids": np.asarray(branches["ids"], dtype=np.int64),
        "frequencies_GHz": np.asarray(FREQUENCIES_GHZ, dtype=np.float64),
        "full": np.asarray(branches["full"], dtype=np.float64),
        "adiabatic": np.asarray(branches["adiabatic"], dtype=np.float64),
        "none": np.asarray(branches["none"], dtype=np.float64),
        "branch_fingerprint_sha256": np.asarray(fingerprint),
    })


def _runtime_provenance() -> dict[str, Any]:
    verified_env = VERIFIED_COMMIT_ENV
    verified = os.environ.get(verified_env)
    if verified is None:
        verified_env = "GOAL050_VERIFIED_PLUTOKORE_COMMIT"
        verified = os.environ.get(verified_env)
    expected = workflow.EXPECTED_PLUTOKORE_COMMIT
    if verified is not None and verified != expected:
        raise StableMethodDiagnosticError(
            "verified plutokore commit differs from the pinned runtime contract"
        )
    return {
        "expected_plutokore_commit": expected,
        "verified_plutokore_commit": verified,
        "commit_verification": (
            "wrapper_export"
            if verified is not None
            else "not_available_in_process"
        ),
        "verified_commit_environment_variable": (
            verified_env if verified is not None else None
        ),
        "goal050_validation_dependency": (
            "Goal 050 exhaustive stable-full recurrence/high-precision gate; "
            "Goal 051 repeats the float recurrence and bounds high precision "
            "to observed cutoffs"
        ),
    }


def _gate_rows(
    mode_summaries: Mapping[str, Mapping[str, Any]],
    comparison: Mapping[str, Any],
    *,
    cutoff_count: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for mode in PRESSURE_MODES:
        summary = mode_summaries[mode]
        full = summary["stable_full"]
        ad_summary = summary["stable_adiabatic"]
        entries = (
            ("grouped_provenance_complete", summary["grouped_provenance_complete"]),
            ("branch_contract", summary["branch_contract_passed"]),
            ("stable_full_deterministic_repeat", full["deterministic_repeat"]),
            ("stable_full_zero_silent_fallbacks", full["silent_fallback_count"] == 0),
            ("stable_full_no_subrelativistic_states", full["subrelativistic_count"] == 0),
            ("stable_full_boundary_conditioning", full["conditioning"]["instability_count"] == 0),
            ("stable_full_cutoff_audit", full["conditioning"]["cutoff_audit_passed"]),
            ("stable_adiabatic_gate", ad_summary["gate_passed"]),
        )
        rows.extend({
            "scope": mode,
            "gate": gate,
            "passed": bool(passed),
            "value": json.dumps(_json_safe(passed), sort_keys=True),
        } for gate, passed in entries)
    for gate, passed in comparison["gate_results"].items():
        rows.append({
            "scope": "comparison",
            "gate": gate,
            "passed": bool(passed),
            "value": json.dumps(_json_safe(passed), sort_keys=True),
        })
    rows.append({
        "scope": "decision",
        "gate": "no_cutoffs_requiring_review",
        "passed": cutoff_count == 0,
        "value": str(cutoff_count),
    })
    return rows


def _stable_gate_mapping(
    mode_summaries: Mapping[str, Mapping[str, Any]],
    comparison: Mapping[str, Any],
) -> dict[str, bool]:
    gates: dict[str, bool] = {}
    for mode in PRESSURE_MODES:
        summary = mode_summaries[mode]
        stable_full = summary["stable_full"]
        conditioning = stable_full["conditioning"]
        gates.update({
            f"{mode}_grouped_provenance": bool(
                summary["grouped_provenance_complete"]
            ),
            f"{mode}_branch_contract": bool(
                summary["branch_contract_passed"]
            ),
            f"{mode}_stable_full_repeat": bool(
                stable_full["deterministic_repeat"]
            ),
            f"{mode}_zero_silent_fallbacks": bool(
                stable_full["silent_fallback_count"] == 0
            ),
            f"{mode}_no_subrelativistic_states": bool(
                stable_full["subrelativistic_count"] == 0
            ),
            f"{mode}_boundary_conditioning": bool(
                conditioning["instability_count"] == 0
            ),
            f"{mode}_cutoff_audit": bool(
                conditioning["cutoff_audit_passed"]
            ),
            f"{mode}_stable_adiabatic": bool(
                summary["stable_adiabatic"]["gate_passed"]
            ),
        })
    gates.update({
        f"comparison_{name}": bool(passed)
        for name, passed in comparison["gate_results"].items()
    })
    return gates


def _write_scientific_failure(
    output_dir: Path,
    base_summary: Mapping[str, Any],
    failure: StableMethodScientificFailure,
) -> dict[str, Any]:
    cutoff_records = list(failure.details.get("cutoff_records", []))
    _write_csv(output_dir / CUTOFF_NAME, CUTOFF_FIELDS, cutoff_records)
    failed_gate = str(
        failure.details.get(
            "failed_gate",
            "stable_branch_reconstruction",
        )
    )
    gate_rows = [{
        "scope": "scientific_reconstruction",
        "gate": failed_gate,
        "passed": False,
        "value": str(failure),
    }]
    _write_csv(
        output_dir / GATE_NAME,
        ("scope", "gate", "passed", "value"),
        gate_rows,
    )
    summary = {
        **base_summary,
        "status": "diagnostic_complete",
        "decision": "FAIL",
        "decision_label": FAIL_LABEL,
        "stable_gates": {
            failed_gate: False,
        },
        "scientific_failure": {
            "message": str(failure),
            "details": failure.details,
        },
    }
    _write_json(output_dir / SUMMARY_NAME, summary)
    return {
        "status": "diagnostic_complete",
        "decision": "FAIL",
        "decision_label": FAIL_LABEL,
        "summary_json": str(output_dir / SUMMARY_NAME),
        "summary_csv": str(output_dir / GATE_NAME),
        "cutoff_records_path": str(output_dir / CUTOFF_NAME),
    }


def diagnose_stable_method_value(
    cache: Path,
    selection_csv: Path,
    output_dir: Path,
    *,
    expected_cache_sha256: str | None = None,
    expected_selection_sha256: str | None = None,
    expected_selection_count: int = SAMPLE_SIZE,
) -> dict[str, Any]:
    """Run the deterministic stable-branch method-value comparison."""
    cache = Path(cache).resolve()
    selection_csv = Path(selection_csv).resolve()
    if not cache.is_file() or cache.is_symlink():
        raise StableMethodDiagnosticError(
            f"cache must be a regular file: {cache}"
        )
    if not selection_csv.is_file() or selection_csv.is_symlink():
        raise StableMethodDiagnosticError(
            f"selection CSV must be a regular file: {selection_csv}"
        )
    cache_hash = _sha256_file(cache)
    selection_hash = _sha256_file(selection_csv)
    if expected_cache_sha256 and cache_hash != expected_cache_sha256:
        raise StableMethodDiagnosticError(
            "cache SHA-256 does not match declared immutable input"
        )
    if expected_selection_sha256 and selection_hash != expected_selection_sha256:
        raise StableMethodDiagnosticError(
            "selection SHA-256 does not match declared immutable input"
        )
    output_dir = _prepare_output_dir(output_dir)
    runtime = _runtime_provenance()
    with h5py.File(cache, "r") as h5:
        cache_validation = workflow._validate_completed_cache(h5)
        plan = workflow.build_pressure_treatment_plan(
            h5,
            expected_trim_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_trim_rows"
            ],
            expected_no_positive_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_no_positive_rows"
            ],
            expected_single_record_rows=workflow.PRESSURE_TREATMENT_CONTRACT[
                "expected_single_record_rows"
            ],
            expected_trim_single_record_overlap_rows=(
                workflow.PRESSURE_TREATMENT_CONTRACT[
                    "expected_trim_single_record_overlap_rows"
                ]
            ),
        )
        selected_rows, selection = read_exact_selection(
            selection_csv,
            h5,
            expected_count=expected_selection_count,
        )
        raw = adiabatic._read_treated_sample(h5, selected_rows, plan)
        physical, unit_provenance = workflow.convert_code_cache_to_physical(
            raw,
            shock_threshold=float(h5.attrs["shock_threshold"]),
            shock_component=int(h5.attrs["shock_component"]),
        )
        source_identity = h5.attrs.get("source_identity_sha256")
        if isinstance(source_identity, bytes):
            source_identity = source_identity.decode()
        endpoint_ids_sha256 = hashlib.sha256(
            np.asarray(h5["endpoint_ids"][:], dtype="<i8").tobytes()
        ).hexdigest()
        times_sha256 = hashlib.sha256(
            np.asarray(h5["times"][:], dtype="<f8").tobytes()
        ).hexdigest()
    shutil.copyfile(selection_csv, output_dir / SELECTION_NAME)
    base_summary = {
        "cache_sha256": cache_hash,
        "selection_sha256": selection_hash,
        "source_identity_sha256": (
            None if source_identity is None else str(source_identity)
        ),
        "endpoint_ids_sha256": endpoint_ids_sha256,
        "times_sha256": times_sha256,
        "cache_validation": cache_validation,
        "selection_count": len(selection),
        "selection_order": (
            f"source CSV sample_index order 0..{len(selection) - 1}"
        ),
        "pressure_treatment_identity_sha256": plan["identity_sha256"],
        "pressure_treatment_counts": {
            "trim_rows": int(len(plan["trim_rows"])),
            "excluded_rows": int(len(plan["excluded_rows"])),
            "single_record_rows": int(len(plan["single_record_rows"])),
            "trim_single_record_overlap_rows": int(
                len(plan["trim_single_record_overlap_rows"])
            ),
        },
        "unit_provenance": unit_provenance,
        "runtime_provenance": runtime,
        "infrastructure_gates": {
            "immutable_input_hashes_recorded": bool(
                len(cache_hash) == 64 and len(selection_hash) == 64
            ),
            "completed_cache": True,
            "exact_selection_identity_and_order": True,
            "pressure_treatment_contract": True,
            "treated_sample_conversion": True,
            "source_identity_recorded": bool(source_identity),
            "runtime_provenance_recorded": True,
        },
        "frequencies_GHz": list(FREQUENCIES_GHZ),
        "pressure_modes": list(PRESSURE_MODES),
        "singleton_policy": "instantaneous_recent_shock",
        "pinned_branch_policy": {
            "full": "ignored; replaced by stable full-loss recurrence",
            "adiabatic": (
                "not calculated; stable adiabatic recurrence uses full_info.ap_arr"
            ),
            "none": "actual lossless comparator after exact branch validation",
        },
    }
    calculate_kwargs = {
        "frequencies": FREQUENCIES_GHZ,
        "z": workflow.PRIMARY_CONTRACT["redshift"],
        "s": workflow.PRIMARY_CONTRACT["s"],
        "eta": workflow.PRIMARY_CONTRACT["eta"],
        "gmin": workflow.PRIMARY_CONTRACT["gmin"],
        "gmax": workflow.PRIMARY_CONTRACT["gmax"],
        "lst_index": 0,
        "diagnostic": True,
        "include_adiabatic": False,
        "singleton_policy": "instantaneous_recent_shock",
    }
    modes: dict[str, dict[str, Any]] = {}
    mode_summaries: dict[str, dict[str, Any]] = {}
    cutoff_records: list[dict[str, Any]] = []
    try:
        for mode in PRESSURE_MODES:
            actual = calculate_praise_pair(
                physical,
                pressure_mode=mode,
                **calculate_kwargs,
            )
            branches, mode_summary, mode_cutoffs = reconstruct_stable_mode(
                actual,
                physical,
                selection,
                pressure_mode=mode,
            )
            modes[mode] = branches
            mode_summaries[mode] = mode_summary
            cutoff_records.extend(mode_cutoffs)
            _write_checkpoint(
                output_dir / f"stable_method_value_{mode}_branches.npz",
                branches,
                mode_summary["branch_fingerprint_sha256"],
            )
    except StableMethodScientificFailure as failure:
        return _write_scientific_failure(
            output_dir,
            base_summary,
            failure,
        )
    try:
        particle_rows, comparison = summarise_stable_comparison(
            selection,
            modes,
        )
    except pressure_method.PressureMethodDiagnosticError as exc:
        return _write_scientific_failure(
            output_dir,
            base_summary,
            StableMethodScientificFailure(
                f"stable method comparison is scientifically undefined: {exc}"
            ),
        )
    cutoff_records.sort(
        key=lambda row: (
            PRESSURE_MODES.index(row["pressure_mode"]),
            row["sample_index"],
            row["interval_index"],
            row["frequency_GHz"],
        )
    )
    cutoff_count = len(cutoff_records)
    decision, decision_label = classify_stable_decision(
        comparison["decision"],
        cutoff_count=cutoff_count,
    )
    ordering_rows = pressure_method._ordering_csv_rows(comparison)
    _write_csv(
        output_dir / PARTICLE_NAME,
        list(particle_rows[0]) if particle_rows else tuple(selection[0]),
        particle_rows,
    )
    _write_csv(
        output_dir / ORDERING_NAME,
        list(ordering_rows[0]) if ordering_rows else (
            "pressure_mode",
            "reference_branch",
            "frequency_GHz",
        ),
        ordering_rows,
    )
    _write_csv(output_dir / CUTOFF_NAME, CUTOFF_FIELDS, cutoff_records)
    gate_rows = _gate_rows(
        mode_summaries,
        comparison,
        cutoff_count=cutoff_count,
    )
    _write_csv(
        output_dir / GATE_NAME,
        ("scope", "gate", "passed", "value"),
        gate_rows,
    )
    branch_fingerprint = hashlib.sha256(_canonical_json({
        mode: mode_summaries[mode]["branch_fingerprint_sha256"]
        for mode in PRESSURE_MODES
    })).hexdigest()
    summary = {
        **base_summary,
        "status": "diagnostic_complete",
        "decision": decision,
        "decision_label": decision_label,
        "stable_gates": _stable_gate_mapping(
            mode_summaries,
            comparison,
        ),
        "decision_semantics": {
            "PASS": "all stable reconstruction and method-value gates pass with zero cutoffs",
            "HOLD_FOR_CUTOFF_REVIEW": (
                "all gates pass but at least one fully audited cutoff requires "
                "scientific prevalence/interpretation review"
            ),
            "FAIL": "at least one reconstruction, cutoff-audit, or comparison gate fails",
        },
        "mode_summaries": mode_summaries,
        "cutoff_count": cutoff_count,
        "cutoff_counts_by_class": {
            state: sum(
                row["classification"] == state for row in cutoff_records
            )
            for state in (
                full_loss.STATE_PHYSICAL_CUTOFF,
                full_loss.STATE_GAMMA_INF_CUTOFF,
            )
        },
        "comparison": comparison,
        "branch_output_fingerprint_sha256": branch_fingerprint,
        "output_contract": {
            "full_vs_adiabatic": (
                "directional radiative-suppression comparison"
            ),
            "full_vs_none": (
                "descriptive lossless comparison; not an upper-bound assertion"
            ),
            "cutoff_policy": (
                "nonzero audited cutoff count yields HOLD_FOR_CUTOFF_REVIEW; "
                "no prevalence threshold is asserted"
            ),
        },
    }
    _write_json(output_dir / SUMMARY_NAME, summary)
    return {
        "status": "diagnostic_complete",
        "decision": decision,
        "decision_label": decision_label,
        "selection_path": str(output_dir / SELECTION_NAME),
        "unsmoothed_checkpoint": str(
            output_dir / "stable_method_value_unsmoothed_branches.npz"
        ),
        "log_savgol_checkpoint": str(
            output_dir / "stable_method_value_log_savgol_branches.npz"
        ),
        "particle_comparison_path": str(output_dir / PARTICLE_NAME),
        "ordering_path": str(output_dir / ORDERING_NAME),
        "cutoff_records_path": str(output_dir / CUTOFF_NAME),
        "summary_csv": str(output_dir / GATE_NAME),
        "summary_json": str(output_dir / SUMMARY_NAME),
        "branch_output_fingerprint_sha256": branch_fingerprint,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--selection-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-cache-sha256")
    parser.add_argument("--expected-selection-sha256")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = diagnose_stable_method_value(
            args.cache,
            args.selection_csv,
            args.output_dir,
            expected_cache_sha256=args.expected_cache_sha256,
            expected_selection_sha256=args.expected_selection_sha256,
        )
    except StableMethodScientificFailure as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 3
    except (
        OSError,
        TypeError,
        ValueError,
        workflow.WorkflowError,
        adiabatic.RecoveryDiagnosticError,
        full_loss.FullLossDiagnosticError,
        pressure_method.PressureMethodDiagnosticError,
        StableMethodDiagnosticError,
    ) as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 2
    print(json.dumps(_json_safe(result), indent=2, sort_keys=True))
    return 0 if result.get("decision") == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())
