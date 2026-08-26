#!/usr/bin/env python3
"""Checkpointed Goal 049 retained-history radio value workflow.

The heavy history cache remains outside Git. Compact endpoint emissivities,
ray maps, manifests, metrics, and the final decision are restartable products
whose completion markers bind the inputs and exact output hashes.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import resource
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

import h5py
import numpy as np
from astropy import units as u
from astropy.cosmology import Planck18
from scipy.ndimage import gaussian_filter

from scripts.science.g_lo_particle_history import (
    HistoryError,
    audit_roots,
    build_history_cache,
    endpoint_ids_from_final,
    validate_presence_lifecycle,
)
from scripts.science.g_lo_radio_method_value import (
    calculate_praise_pair,
    compare_loss_maps,
    derive_support_bound,
    raytrace_radio,
)


EXPECTED_PLUTOKORE_COMMIT = "e80252cf35ff5a06166240e2867d3d485aaf6956"
KPC_TO_M = 3.0856775814913673e19
SPEED_OF_LIGHT_M_S = 299792458.0
DENSITY_UNIT_KG_M3 = (0.60364 * u.u / u.cm**3).to_value(u.kg / u.m**3)
PRESSURE_UNIT_PA = DENSITY_UNIT_KG_M3 * SPEED_OF_LIGHT_M_S**2
TIME_UNIT_S = KPC_TO_M / SPEED_OF_LIGHT_M_S
EMISSIVITY_UNIT = u.W / (u.Hz * u.m**3 * u.sr)
INTENSITY_UNIT = u.W / (u.Hz * u.m**2 * u.sr)

PRIMARY_CONTRACT = {
    "frequencies_GHz": [0.15, 1.4],
    "redshift": 0.05,
    "s": 2.2,
    "eta": 0.03,
    "gmin": 500.0,
    "gmax": 1.0e5,
    "pressure_mode": {
        "name": "unsmoothed",
        "transform": "identity",
        "smoothing": False,
        "linear_savgol_available": False,
    },
    "singleton_policy": "instantaneous_recent_shock",
    "pixel_size_kpc": 1.8,
    "ray_steps_kpc": [0.05, 0.1, 0.2],
    "views_deg": [0.0, 45.0, 90.0],
    "beam_fwhm_kpc": [2.5, 5.0, 10.0],
    "primary_beam_fwhm_kpc": 5.0,
    "threshold_mjy_beam": [0.05 / 3.0, 0.05, 0.15],
    "primary_threshold_mjy_beam": 0.05,
    "kd_jobs": 16,
}
MATERIALITY_THRESHOLDS = {
    "log10_luminosity_ratio": 0.10,
    "area_fraction_change": 0.20,
    "extent_fraction_change": 0.20,
    "spectral_index_change": 0.10,
    "dice_change": 0.10,
}
DECISION_LABELS = {
    "green": "G_LO_FULL_HISTORY_VALUE_GREEN_REGENERATION_REVIEW_JUSTIFIED",
    "low": "G_LO_FULL_HISTORY_VALUE_LOW_MATCHED_LOSSLESS_SCOPE_PREFERRED",
    "history": "G_LO_HISTORY_BLOCKED",
    "method": "G_LO_RADIO_METHOD_BLOCKED",
    "compute": "G_LO_RADIO_COMPUTE_BLOCKED",
}
PRESSURE_TREATMENT_CONTRACT = {
    "version": 3,
    "primary": (
        "convert exactly one joint pressure-density-tracer initialization zero "
        "at first presence to a trimmed pre-injection record; use the explicit "
        "instantaneous recent-shock convention for an exact one-record history"
    ),
    "excluded": "exclude no-positive histories from PRAiSE and raytracing",
    "conservative_comparator": (
        "exclude every trim-affected, no-positive, and single-record history"
    ),
    "single_record_policy": (
        "instantaneous_recent_shock: p_inj=p_endpoint, "
        "gamma_inj=gamma_current, full=lossless"
    ),
    "single_record_scope": "effective positive history after the approved trim",
    "pressure_floor": False,
    "interpolation": False,
    "preserve_tinj": True,
    "minimum_history_records": 2,
    "expected_trim_rows": 10_030,
    "expected_no_positive_rows": 2,
    "expected_single_record_rows": 48,
    "expected_trim_single_record_overlap_rows": 2,
}


class WorkflowError(RuntimeError):
    """Raised when an integration, restart, unit, or packaging gate fails."""


class PressureTreatmentError(WorkflowError):
    """Raised when the immutable history violates the approved treatment gate."""


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, u.Quantity):
        return {"value": np.asarray(value.value).tolist(), "unit": str(value.unit)}
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _canonical_json(value: Any) -> bytes:
    return json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":")).encode("utf-8")


def _payload_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_write_bytes(path: Path, payload: bytes) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _atomic_write_json(path: Path, value: Any) -> None:
    _atomic_write_bytes(path, json.dumps(_jsonable(value), indent=2, sort_keys=True).encode() + b"\n")


def _atomic_savez(path: Path, **arrays: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            np.savez_compressed(handle, **arrays)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def write_stage_checkpoint(
    marker: Path,
    *,
    stage: str,
    input_contract: Mapping[str, Any],
    outputs: Sequence[Path],
    details: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    records = []
    for output in outputs:
        path = Path(output)
        if not path.is_file() or path.is_symlink():
            raise WorkflowError(f"checkpoint output is not a regular file: {path}")
        records.append({"path": str(path), "bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    payload = {
        "checkpoint_version": 1,
        "completed": True,
        "stage": stage,
        "input_identity_sha256": _payload_sha256(input_contract),
        "input_contract": input_contract,
        "outputs": records,
        "details": details or {},
    }
    payload["restart_identity_sha256"] = _payload_sha256(payload)
    _atomic_write_json(marker, payload)
    return payload


def validate_stage_checkpoint(
    marker: Path,
    *,
    stage: str,
    input_contract: Mapping[str, Any],
) -> dict[str, Any]:
    marker = Path(marker)
    if not marker.is_file() or marker.is_symlink():
        raise WorkflowError(f"completion marker is missing: {marker}")
    payload = json.loads(marker.read_text())
    expected = _payload_sha256(input_contract)
    if payload.get("stage") != stage or payload.get("completed") is not True:
        raise WorkflowError(f"invalid completion marker for stage {stage}")
    if payload.get("input_identity_sha256") != expected:
        raise WorkflowError(f"{stage} restart input identity mismatch")
    stored_identity = payload.get("restart_identity_sha256")
    check_payload = dict(payload)
    check_payload.pop("restart_identity_sha256", None)
    if stored_identity != _payload_sha256(check_payload):
        raise WorkflowError(f"{stage} completion marker identity hash mismatch")
    for record in payload.get("outputs", []):
        output = Path(record["path"])
        if not output.is_file() or output.is_symlink():
            raise WorkflowError(f"{stage} checkpoint output is missing: {output}")
        if output.stat().st_size != record["bytes"] or _sha256_file(output) != record["sha256"]:
            raise WorkflowError(f"{stage} checkpoint output hash mismatch: {output}")
    payload["reused"] = True
    return payload


def _checkpoint_if_valid(marker: Path, stage: str, contract: Mapping[str, Any]) -> dict[str, Any] | None:
    if not Path(marker).exists():
        return None
    return validate_stage_checkpoint(marker, stage=stage, input_contract=contract)


def peak_rss_bytes() -> int:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(rss if sys.platform == "darwin" else rss * 1024)


def convert_code_cache_to_physical(
    raw: Mapping[str, Any],
    *,
    shock_threshold: float,
    shock_component: int,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    if not np.isclose(float(shock_threshold), 5.0, rtol=0.0, atol=1e-12):
        raise WorkflowError("strong-shock history must be selected by exact PLUTO shk_thresh=5 provenance")
    if not isinstance(shock_component, (int, np.integer)) or int(shock_component) < 0:
        raise WorkflowError("shock component provenance must be a non-negative integer")
    required = ("physical_ids", "time", "pressure", "density", "tracer", "last_shock_time", "position", "velocity")
    missing = [name for name in required if name not in raw]
    if missing:
        raise WorkflowError(f"cache conversion is missing: {', '.join(missing)}")
    ids = np.asarray(raw["physical_ids"])
    if ids.ndim != 1 or ids.size == 0 or not np.all(np.isfinite(ids)):
        raise WorkflowError("physical IDs must be a finite one-dimensional array")
    if not np.all(ids == np.floor(ids)) or len(np.unique(ids)) != len(ids):
        raise WorkflowError("physical IDs must be unique integers")
    ids = ids.astype(np.int64, copy=True)
    time_values = np.asarray(raw["time"], dtype=np.float64)
    if time_values.ndim != 1 or time_values.size < 2 or not np.all(np.diff(time_values) > 0):
        raise WorkflowError("code times must be finite and strictly increasing")
    n, nt = len(ids), len(time_values)
    converted: dict[str, np.ndarray] = {
        "physical_ids": ids,
        "time": time_values * TIME_UNIT_S,
        "pressure": np.asarray(raw["pressure"], dtype=np.float64) * PRESSURE_UNIT_PA,
        "density": np.asarray(raw["density"], dtype=np.float64) * DENSITY_UNIT_KG_M3,
        "tracer": np.asarray(raw["tracer"], dtype=np.float64).copy(),
        "last_shock_time": np.asarray(raw["last_shock_time"], dtype=np.float64) * TIME_UNIT_S,
        "position": np.asarray(raw["position"], dtype=np.float64).copy(),
        "velocity": np.asarray(raw["velocity"], dtype=np.float64).copy(),
    }
    for field in ("pressure", "density", "tracer", "last_shock_time"):
        if converted[field].shape[:2] != (n, nt):
            raise WorkflowError(f"{field} cache shape does not match IDs and times")
    if converted["position"].shape != (n, 3) or converted["velocity"].shape != (n, 3):
        raise WorkflowError("endpoint position and velocity must have shape (particle, 3)")
    if not np.all(np.isfinite(converted["position"])):
        raise WorkflowError("endpoint positions are non-finite")
    beta_norm = np.linalg.norm(converted["velocity"], axis=1)
    if not np.all(np.isfinite(beta_norm)) or np.any(beta_norm >= 1.0):
        raise WorkflowError("endpoint velocity must be a finite beta vector with norm < 1")
    if "tinj" in raw:
        converted["tinj"] = np.asarray(raw["tinj"], dtype=np.float64) * TIME_UNIT_S
    provenance = {
        "length_unit": "1 kpc",
        "length_unit_m": KPC_TO_M,
        "speed_unit": "c",
        "speed_unit_m_s": SPEED_OF_LIGHT_M_S,
        "endpoint_velocity_representation": "dimensionless beta vector",
        "time_unit": "kpc/c in seconds",
        "time_unit_s": TIME_UNIT_S,
        "density_unit": "0.60364 u cm^-3",
        "density_unit_kg_m3": DENSITY_UNIT_KG_M3,
        "pressure_unit": "density_unit * c^2",
        "pressure_unit_Pa": PRESSURE_UNIT_PA,
        "history_dtype": "float64",
        "physical_ids": "unmodified raw PLUTO IDs",
        "shock_threshold": 5.0,
        "shock_component": int(shock_component),
        "shock_component_semantics": "selected by g_lo_particle_history from PLUTO shk_thresh",
    }
    return converted, provenance


def _cache_identity(cache_path: Path) -> dict[str, Any]:
    cache_path = Path(cache_path)
    with h5py.File(cache_path, "r") as h5:
        ids = h5["endpoint_ids"][:]
        times = h5["times"][:]
        return {
            "cache_path": str(cache_path),
            "cache_sha256": _sha256_file(cache_path),
            "source_identity_sha256": str(h5.attrs.get("source_identity_sha256", "")),
            "endpoint_ids_sha256": hashlib.sha256(ids.tobytes()).hexdigest(),
            "times_sha256": hashlib.sha256(times.tobytes()).hexdigest(),
            "endpoint_count": int(len(ids)),
            "output_count": int(len(times)),
            "shock_threshold": float(h5.attrs["shock_threshold"]),
            "shock_component": int(h5.attrs["shock_component"]),
        }


def _validate_completed_cache(h5: h5py.File) -> dict[str, Any]:
    required = (
        "endpoint_ids", "times", "output_indices", "pressure", "density", "tracer",
        "last_shock_time", "presence", "position", "velocity", "tinj",
    )
    missing = [name for name in required if name not in h5]
    if missing:
        raise WorkflowError(f"history cache is missing datasets: {', '.join(missing)}")
    n, nt = h5["presence"].shape
    if int(h5.attrs.get("next_output", -1)) != nt:
        raise WorkflowError("history cache is not complete")
    try:
        lifecycle = validate_presence_lifecycle(
            h5["presence"],
            h5["times"][:],
            h5["tinj"][:],
            h5["endpoint_ids"][:],
            h5["output_indices"][:],
        )
    except HistoryError as exc:
        raise WorkflowError(str(exc)) from exc
    if h5["pressure"].dtype != np.dtype("float64"):
        raise WorkflowError("history cache must retain float64 histories")
    return {
        "endpoint_count": int(n),
        "output_count": int(nt),
        **lifecycle,
    }


def build_pressure_treatment_plan(
    h5: h5py.File,
    *,
    expected_trim_rows: int = PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
    expected_no_positive_rows: int = PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
    expected_single_record_rows: int = PRESSURE_TREATMENT_CONTRACT[
        "expected_single_record_rows"
    ],
    expected_trim_single_record_overlap_rows: int | None = None,
    row_chunk: int = 512,
    enforce_expected_counts: bool = True,
) -> dict[str, Any]:
    """Classify the immutable cache and fail closed before PRAiSE is called."""
    if (
        row_chunk <= 0
        or expected_trim_rows < 0
        or expected_no_positive_rows < 0
        or expected_single_record_rows < 0
        or (
            expected_trim_single_record_overlap_rows is not None
            and expected_trim_single_record_overlap_rows < 0
        )
    ):
        raise WorkflowError("pressure-treatment counts and row_chunk must be non-negative/positive")
    if expected_trim_single_record_overlap_rows is None and (
        expected_trim_rows,
        expected_no_positive_rows,
        expected_single_record_rows,
    ) == (
        PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
        PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
        PRESSURE_TREATMENT_CONTRACT["expected_single_record_rows"],
    ):
        expected_trim_single_record_overlap_rows = PRESSURE_TREATMENT_CONTRACT[
            "expected_trim_single_record_overlap_rows"
        ]
    required = (
        "endpoint_ids", "times", "output_indices", "pressure", "density", "tracer",
        "last_shock_time", "presence", "tinj",
    )
    missing = [name for name in required if name not in h5]
    if missing:
        raise WorkflowError(f"pressure-treatment cache is missing: {', '.join(missing)}")
    ids = np.asarray(h5["endpoint_ids"][:], dtype=np.int64)
    times = np.asarray(h5["times"][:], dtype=np.float64)
    outputs = np.asarray(h5["output_indices"][:], dtype=np.int64)
    tinj = np.asarray(h5["tinj"][:], dtype=np.float64)
    n, nt = h5["presence"].shape
    if ids.shape != (n,) or times.shape != (nt,) or outputs.shape != (nt,) or tinj.shape != (n,):
        raise WorkflowError("pressure-treatment metadata shapes are inconsistent")
    if not np.all(np.isfinite(times)) or not np.all(np.diff(times) > 0):
        raise WorkflowError("pressure-treatment times must be finite and strictly increasing")
    if not np.all(np.isfinite(tinj)):
        raise WorkflowError("pressure-treatment tinj values must be finite")

    # 0 unchanged, 1 trim one init record, 2 no-positive exclusion,
    # 3 untrimmed single-record instantaneous convention. Effective singleton
    # status is orthogonal because a trimmed history can also become singleton.
    kinds = np.zeros(n, dtype=np.int8)
    trim_columns = np.full(n, -1, dtype=np.int64)
    effective_history_records = np.full(n, -1, dtype=np.int64)
    single_record_effective_mask = np.zeros(n, dtype=bool)
    records: list[dict[str, Any]] = []
    for start in range(0, n, row_chunk):
        stop = min(start + row_chunk, n)
        presence = np.asarray(h5["presence"][start:stop, :], dtype=bool)
        pressure = np.asarray(h5["pressure"][start:stop, :], dtype=np.float64)
        density = np.asarray(h5["density"][start:stop, :], dtype=np.float64)
        tracer = np.asarray(h5["tracer"][start:stop, :], dtype=np.float64)
        last = np.asarray(h5["last_shock_time"][start:stop, ...], dtype=np.float64)
        if last.ndim == 3:
            if last.shape[2] < 1:
                raise WorkflowError("last_shock_time has no components")
            last = last[:, :, 0]
        expected_shape = presence.shape
        if any(array.shape != expected_shape for array in (pressure, density, tracer, last)):
            raise WorkflowError("pressure-treatment field shapes are inconsistent")
        present_count = np.count_nonzero(presence, axis=1)
        if np.any(present_count == 0):
            raise WorkflowError("pressure-treatment found an endpoint particle with no presence")
        first = np.argmax(presence, axis=1)
        columns = np.arange(nt)[None, :]
        gaps = (~presence) & (columns >= first[:, None])
        if np.any(gaps):
            raise WorkflowError("pressure-treatment presence lifecycle has an internal gap")

        pressure_finite = np.isfinite(pressure)
        if np.any(presence & ~pressure_finite):
            raise WorkflowError("pressure-treatment found non-finite pressure in the present suffix")
        if np.any(presence & (pressure < 0)):
            raise WorkflowError("pressure-treatment found negative pressure")
        for name, values in (("density", density), ("tracer", tracer), ("last_shock_time", last)):
            if np.any(presence & ~np.isfinite(values)):
                raise WorkflowError(f"pressure-treatment found non-finite {name} in the present suffix")
        if np.any(presence & (density < 0)):
            raise WorkflowError("pressure-treatment found negative density")
        if np.any(presence & (last > times[None, :])):
            raise WorkflowError("pressure-treatment found a future last_shock_time")

        zero = presence & (pressure == 0)
        positive = presence & (pressure > 0)
        zero_count = np.count_nonzero(zero, axis=1)
        positive_count = np.count_nonzero(positive, axis=1)
        trim = (
            (positive_count > 0)
            & (zero_count == 1)
            & (positive_count == present_count - 1)
            & zero[np.arange(stop - start), first]
        )
        no_positive = (positive_count == 0) & (zero_count == present_count)
        unchanged = positive_count == present_count
        category_count = (
            trim.astype(np.int8)
            + no_positive.astype(np.int8)
            + unchanged.astype(np.int8)
        )
        invalid = category_count != 1
        if np.any(invalid):
            raise WorkflowError(
                "pressure-treatment found internal/multiple leading zero pressure records"
            )
        if np.any(zero & ((density != 0) | (tracer != 0))):
            raise WorkflowError("pressure-treatment zero pressure is not a joint pressure-density-tracer initialization zero")
        if np.any(positive & (density <= 0)):
            raise WorkflowError("pressure-treatment positive-pressure history has non-positive density")

        effective = np.where(trim, first + 1, first)
        if np.any(trim & (effective >= nt)):
            raise WorkflowError("pressure-treatment trim reaches beyond the endpoint")
        effective_count = np.where(no_positive, 0, present_count - trim.astype(np.int64))
        single_record = (
            ~no_positive
            & (
                effective_count
                < PRESSURE_TREATMENT_CONTRACT["minimum_history_records"]
            )
        )
        if np.any(single_record & (effective_count != 1)):
            raise WorkflowError(
                "pressure-treatment effective singleton has an invalid record count"
            )
        comparable_start = np.where(no_positive, first, effective)
        local_tinj = tinj[start:stop]
        if np.any(local_tinj > times[comparable_start]):
            raise WorkflowError("pressure-treatment tinj follows the effective/presence start")

        for local in np.flatnonzero(trim | no_positive | single_record):
            row = start + int(local)
            is_trim = bool(trim[local])
            is_no_positive = bool(no_positive[local])
            is_single_record = bool(single_record[local])
            kinds[row] = 1 if is_trim else (2 if is_no_positive else 3)
            trim_columns[row] = int(first[local]) if is_trim else -1
            effective_history_records[row] = int(effective_count[local])
            single_record_effective_mask[row] = is_single_record
            first_col = int(first[local])
            last_col = int(nt - 1)
            effective_col = None if is_no_positive else int(effective[local])
            reason = (
                "joint_initialization_zero_trim"
                if is_trim
                else (
                    "no_positive_pressure"
                    if is_no_positive
                    else "single_record_instantaneous_convention"
                )
            )
            treatment_reasons = [reason]
            if is_single_record and reason != "single_record_instantaneous_convention":
                treatment_reasons.append("single_record_instantaneous_convention")
            records.append({
                "cache_row": row,
                "endpoint_id": int(ids[row]),
                "reason": reason,
                "treatment_reasons": treatment_reasons,
                "trim_affected": is_trim,
                "instantaneous_after_treatment": is_single_record,
                "tinj": float(tinj[row]),
                "first_present_column": first_col,
                "first_present_output_index": int(outputs[first_col]),
                "first_present_time": float(times[first_col]),
                "last_present_column": last_col,
                "last_present_output_index": int(outputs[last_col]),
                "last_present_time": float(times[last_col]),
                "present_count": int(present_count[local]),
                "effective_history_records": int(effective_count[local]),
                "minimum_history_records": int(
                    PRESSURE_TREATMENT_CONTRACT["minimum_history_records"]
                ),
                "effective_start_column": effective_col,
                "effective_start_output_index": (
                    int(outputs[effective_col]) if effective_col is not None else None
                ),
                "effective_start_time": (
                    float(times[effective_col]) if effective_col is not None else None
                ),
                "effective_start_delay": (
                    float(times[effective_col] - tinj[row]) if effective_col is not None else None
                ),
                "first_pressure": float(pressure[local, first_col]),
                "first_density": float(density[local, first_col]),
                "first_tracer": float(tracer[local, first_col]),
                "first_last_shock_time": float(last[local, first_col]),
                "last_pressure": float(pressure[local, last_col]),
                "last_density": float(density[local, last_col]),
                "last_tracer": float(tracer[local, last_col]),
                "last_last_shock_time": float(last[local, last_col]),
                "source_exact_match_status": "not_supplied_to_runner",
            })
        effective_history_records[start:stop] = effective_count
        single_record_effective_mask[start:stop] = single_record

    trim_rows = np.flatnonzero(kinds == 1)
    no_positive_rows = np.flatnonzero(kinds == 2)
    single_record_rows = np.flatnonzero(single_record_effective_mask)
    trim_single_record_overlap_rows = np.flatnonzero(
        (kinds == 1) & single_record_effective_mask
    )
    excluded_rows = no_positive_rows
    if (
        len(trim_rows) != expected_trim_rows
        or len(no_positive_rows) != expected_no_positive_rows
        or len(single_record_rows) != expected_single_record_rows
        or (
            expected_trim_single_record_overlap_rows is not None
            and len(trim_single_record_overlap_rows)
            != expected_trim_single_record_overlap_rows
        )
    ) and enforce_expected_counts:
        raise WorkflowError(
            "pressure-treatment aggregate mismatch: "
            f"trim={len(trim_rows)} expected={expected_trim_rows}; "
            f"no_positive={len(no_positive_rows)} expected={expected_no_positive_rows}; "
            f"single_record={len(single_record_rows)} "
            f"expected={expected_single_record_rows}; "
            f"trim_single_record_overlap={len(trim_single_record_overlap_rows)} "
            f"expected={expected_trim_single_record_overlap_rows}"
        )
    active_mask = kinds != 2
    conservative_active_mask = active_mask & (kinds != 1) & ~single_record_effective_mask
    trim_affected_active_mask = kinds[active_mask] == 1
    identity = {
        "contract": {
            **PRESSURE_TREATMENT_CONTRACT,
            "expected_trim_rows": (
                expected_trim_rows if enforce_expected_counts else None
            ),
            "expected_no_positive_rows": (
                expected_no_positive_rows if enforce_expected_counts else None
            ),
            "expected_single_record_rows": (
                expected_single_record_rows if enforce_expected_counts else None
            ),
            "expected_trim_single_record_overlap_rows": (
                expected_trim_single_record_overlap_rows
                if enforce_expected_counts
                else None
            ),
            "aggregate_count_gate": (
                "predeclared_exact_counts"
                if enforce_expected_counts
                else "case_specific_counts_recorded_after_structural_validation"
            ),
        },
        "endpoint_ids_sha256": hashlib.sha256(ids.tobytes()).hexdigest(),
        "kinds_sha256": hashlib.sha256(kinds.tobytes()).hexdigest(),
        "trim_columns_sha256": hashlib.sha256(trim_columns.tobytes()).hexdigest(),
        "effective_history_records_sha256": hashlib.sha256(
            effective_history_records.tobytes()
        ).hexdigest(),
        "single_record_effective_mask_sha256": hashlib.sha256(
            single_record_effective_mask.tobytes()
        ).hexdigest(),
        "trim_row_count": int(len(trim_rows)),
        "excluded_no_positive_row_count": int(len(no_positive_rows)),
        "single_record_instantaneous_row_count": int(len(single_record_rows)),
        "trim_single_record_overlap_row_count": int(
            len(trim_single_record_overlap_rows)
        ),
        "excluded_total_row_count": int(len(excluded_rows)),
        "active_rows": int(np.count_nonzero(active_mask)),
        "conservative_active_rows": int(np.count_nonzero(conservative_active_mask)),
        "source_exact_match": "not claimed; external wrapper preflight required",
    }
    identity["identity_sha256"] = _payload_sha256(identity)
    return {
        **identity,
        "kinds": kinds,
        "trim_columns": trim_columns,
        "effective_history_records": effective_history_records,
        "single_record_effective_mask": single_record_effective_mask,
        "trim_rows": trim_rows,
        "no_positive_rows": no_positive_rows,
        "single_record_rows": single_record_rows,
        "trim_single_record_overlap_rows": trim_single_record_overlap_rows,
        "excluded_rows": excluded_rows,
        "active_mask": active_mask,
        "conservative_active_mask": conservative_active_mask,
        "trim_affected_active_mask": trim_affected_active_mask,
        "single_record_active_mask": single_record_effective_mask[active_mask],
        "records": records,
    }


def _pressure_treatment_report(plan: Mapping[str, Any]) -> dict[str, Any]:
    array_keys = {
        "kinds", "trim_columns", "effective_history_records",
        "single_record_effective_mask", "trim_rows", "no_positive_rows",
        "single_record_rows", "trim_single_record_overlap_rows",
        "excluded_rows", "active_mask",
        "conservative_active_mask", "trim_affected_active_mask",
        "single_record_active_mask",
    }
    return {key: value for key, value in plan.items() if key not in array_keys}


def apply_pressure_treatment(
    raw: Mapping[str, np.ndarray],
    *,
    row_offset: int,
    plan: Mapping[str, Any],
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Subset excluded rows and trim only the approved joint init record."""
    ids = np.asarray(raw["physical_ids"])
    stop = row_offset + len(ids)
    kinds = np.asarray(plan["kinds"])[row_offset:stop]
    trim_columns = np.asarray(plan["trim_columns"])[row_offset:stop]
    single_record_effective = np.asarray(
        plan["single_record_effective_mask"], dtype=bool
    )[row_offset:stop]
    select = kinds != 2
    per_particle = {
        "physical_ids", "pressure", "density", "tracer", "last_shock_time",
        "position", "velocity", "tinj",
    }
    treated = {
        key: np.array(value[select], copy=True)
        if key in per_particle
        else np.array(value, copy=True)
        for key, value in raw.items()
    }
    selected_kinds = kinds[select]
    selected_columns = trim_columns[select]
    selected_single_record = single_record_effective[select]
    for local in np.flatnonzero(selected_kinds == 1):
        column = int(selected_columns[local])
        for field in ("pressure", "density", "tracer", "last_shock_time"):
            treated[field][local, column, ...] = np.nan
    active_cache_rows = (row_offset + np.flatnonzero(select)).astype(np.int64)
    metadata = {
        "active_cache_rows": active_cache_rows.tolist(),
        "trim_affected": (selected_kinds == 1).tolist(),
        "instantaneous_history": selected_single_record.tolist(),
        "excluded_cache_rows": (row_offset + np.flatnonzero(~select)).astype(np.int64).tolist(),
        "excluded_no_positive_cache_rows": (
            row_offset + np.flatnonzero(kinds == 2)
        ).astype(np.int64).tolist(),
        "tinj_preserved": True,
        "pressure_floor": False,
        "interpolation": False,
    }
    return treated, metadata


def _load_treatment_aligned_support(
    h5: h5py.File,
    emissivity: Mapping[str, Any],
) -> dict[str, np.ndarray]:
    required = (
        "physical_ids", "cache_row_indices", "trim_affected", "instantaneous_history",
        "primary_active_mask", "conservative_active_mask", "full", "none",
    )
    missing = [name for name in required if name not in emissivity]
    if missing:
        raise WorkflowError(f"emissivity treatment support is missing: {', '.join(missing)}")
    cache_ids = np.asarray(h5["endpoint_ids"][:], dtype=np.int64)
    rows = np.asarray(emissivity["cache_row_indices"], dtype=np.int64)
    ids = np.asarray(emissivity["physical_ids"], dtype=np.int64)
    primary_mask = np.asarray(emissivity["primary_active_mask"], dtype=bool)
    conservative_mask = np.asarray(emissivity["conservative_active_mask"], dtype=bool)
    trim = np.asarray(emissivity["trim_affected"], dtype=bool)
    instantaneous = np.asarray(emissivity["instantaneous_history"], dtype=bool)
    if primary_mask.shape != cache_ids.shape or conservative_mask.shape != cache_ids.shape:
        raise WorkflowError("treatment support masks do not align with the history cache")
    if (
        rows.ndim != 1
        or ids.shape != rows.shape
        or trim.shape != rows.shape
        or instantaneous.shape != rows.shape
    ):
        raise WorkflowError("active treatment support arrays have incompatible shapes")
    if not np.array_equal(rows, np.flatnonzero(primary_mask)):
        raise WorkflowError("active cache-row alignment differs from the primary support mask")
    if np.any(rows < 0) or np.any(rows >= len(cache_ids)) or not np.array_equal(ids, cache_ids[rows]):
        raise WorkflowError("physical-ID alignment differs between cache and emissivity support")
    comparator_select = conservative_mask[rows]
    if not np.array_equal(comparator_select, ~(trim | instantaneous)):
        raise WorkflowError(
            "conservative comparator alignment differs from pressure-treatment support"
        )
    return {
        "cache_rows": rows,
        "primary_ids": ids,
        "trim_affected": trim,
        "instantaneous_history": instantaneous,
        "comparator_select": comparator_select,
        "comparator_ids": ids[comparator_select],
        "position": np.asarray(h5["position"][rows, :], dtype=np.float64),
        "velocity": np.asarray(h5["velocity"][rows, :], dtype=np.float64),
        "full": np.asarray(emissivity["full"][:], dtype=np.float64),
        "none": np.asarray(emissivity["none"][:], dtype=np.float64),
        "primary_active_mask": primary_mask,
        "conservative_active_mask": conservative_mask,
    }


def _raw_cache_chunk(h5: h5py.File, start: int, stop: int) -> dict[str, np.ndarray]:
    return {
        "physical_ids": h5["endpoint_ids"][start:stop],
        "time": h5["times"][:],
        "pressure": h5["pressure"][start:stop, :],
        "density": h5["density"][start:stop, :],
        "tracer": h5["tracer"][start:stop, :],
        "last_shock_time": h5["last_shock_time"][start:stop, :],
        "position": h5["position"][start:stop, :],
        "velocity": h5["velocity"][start:stop, :],
        "tinj": h5["tinj"][start:stop],
    }


def run_emissivity_stage(
    cache_path: Path,
    work_root: Path,
    *,
    id_chunk_size: int = 4096,
    expected_trim_rows: int = PRESSURE_TREATMENT_CONTRACT["expected_trim_rows"],
    expected_no_positive_rows: int = PRESSURE_TREATMENT_CONTRACT["expected_no_positive_rows"],
    expected_single_record_rows: int = PRESSURE_TREATMENT_CONTRACT[
        "expected_single_record_rows"
    ],
    expected_trim_single_record_overlap_rows: int | None = None,
) -> dict[str, Any]:
    if id_chunk_size <= 0:
        raise WorkflowError("id_chunk_size must be positive")
    cache_path, work_root = Path(cache_path), Path(work_root)
    stage_dir = work_root / "compact" / "emissivity"
    checkpoints = work_root / ".checkpoints"
    stage_dir.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    cache_identity = _cache_identity(cache_path)
    with h5py.File(cache_path, "r") as h5:
        completeness = _validate_completed_cache(h5)
        n = completeness["endpoint_count"]
        expected_ids = h5["endpoint_ids"][:]
        try:
            treatment = build_pressure_treatment_plan(
                h5,
                expected_trim_rows=expected_trim_rows,
                expected_no_positive_rows=expected_no_positive_rows,
                expected_single_record_rows=expected_single_record_rows,
                expected_trim_single_record_overlap_rows=(
                    expected_trim_single_record_overlap_rows
                ),
            )
        except WorkflowError as exc:
            raise PressureTreatmentError(str(exc)) from exc
        treatment_report = stage_dir / "pressure_treatment.json"
        _atomic_write_json(treatment_report, _pressure_treatment_report(treatment))
        active_ids = expected_ids[treatment["active_mask"]]
        chunk_paths: list[Path] = []
        chunk_markers: list[Path] = []
        reused = 0
        for start in range(0, n, id_chunk_size):
            stop = min(start + id_chunk_size, n)
            output = stage_dir / f"emissivity_{start:09d}_{stop:09d}.npz"
            metadata_path = stage_dir / f"emissivity_{start:09d}_{stop:09d}.json"
            marker = checkpoints / f"emissivity_{start:09d}_{stop:09d}.json"
            contract = {
                "cache": cache_identity,
                "pressure_treatment_identity_sha256": treatment["identity_sha256"],
                "row_range": [start, stop],
                "physical_ids_sha256": hashlib.sha256(
                    expected_ids[start:stop][treatment["active_mask"][start:stop]].tobytes()
                ).hexdigest(),
                "praise": PRIMARY_CONTRACT,
                "pressure_mode": "unsmoothed",
                "code_units": {
                    "density_unit_kg_m3": DENSITY_UNIT_KG_M3,
                    "pressure_unit_Pa": PRESSURE_UNIT_PA,
                    "time_unit_s": TIME_UNIT_S,
                },
            }
            checkpoint = _checkpoint_if_valid(marker, "emissivity_chunk", contract)
            if checkpoint is not None:
                reused += 1
            else:
                treated_raw, treatment_chunk = apply_pressure_treatment(
                    _raw_cache_chunk(h5, start, stop),
                    row_offset=start,
                    plan=treatment,
                )
                physical, unit_provenance = convert_code_cache_to_physical(
                    treated_raw,
                    shock_threshold=cache_identity["shock_threshold"],
                    shock_component=cache_identity["shock_component"],
                )
                result = calculate_praise_pair(
                    physical,
                    frequencies=PRIMARY_CONTRACT["frequencies_GHz"],
                    z=PRIMARY_CONTRACT["redshift"],
                    s=PRIMARY_CONTRACT["s"],
                    eta=PRIMARY_CONTRACT["eta"],
                    gmin=PRIMARY_CONTRACT["gmin"],
                    gmax=PRIMARY_CONTRACT["gmax"],
                    lst_index=0,
                    pressure_mode="unsmoothed",
                    singleton_policy="instantaneous_recent_shock",
                )
                praise_metadata = result.get("metadata", {})
                expected_singleton_mask = np.asarray(
                    treatment_chunk["instantaneous_history"], dtype=bool
                )
                expected_singleton_ids = np.asarray(
                    physical["physical_ids"], dtype=np.int64
                )[expected_singleton_mask]
                actual_singleton_count = int(
                    praise_metadata.get("single_record_instantaneous_count", 0)
                )
                actual_singleton_ids = np.asarray(
                    praise_metadata.get("single_record_instantaneous_ids", []),
                    dtype=np.int64,
                )
                if (
                    actual_singleton_count != len(expected_singleton_ids)
                    or not np.array_equal(actual_singleton_ids, expected_singleton_ids)
                ):
                    raise WorkflowError(
                        "PRAiSE singleton provenance differs from the "
                        "pressure-treatment plan"
                    )
                ids = np.asarray(result["ids"], dtype=np.int64)
                full = np.asarray(getattr(result["full"], "value", result["full"]), dtype=np.float64)
                none = np.asarray(getattr(result["none"], "value", result["none"]), dtype=np.float64)
                expected_chunk_ids = expected_ids[start:stop][treatment["active_mask"][start:stop]]
                if not np.array_equal(ids, expected_chunk_ids):
                    raise WorkflowError("PRAiSE changed physical ID order")
                if full.shape != (len(expected_chunk_ids), 2) or none.shape != full.shape:
                    raise WorkflowError("PRAiSE returned an unexpected emissivity shape")
                if not np.all(np.isfinite(full)) or not np.all(np.isfinite(none)):
                    raise WorkflowError("PRAiSE returned non-finite endpoint emissivity")
                _atomic_savez(
                    output,
                    physical_ids=ids,
                    cache_row_indices=np.asarray(treatment_chunk["active_cache_rows"], dtype=np.int64),
                    trim_affected=np.asarray(treatment_chunk["trim_affected"], dtype=bool),
                    instantaneous_history=np.asarray(
                        treatment_chunk["instantaneous_history"], dtype=bool
                    ),
                    full=full,
                    none=none,
                )
                metadata = {
                    "row_range": [start, stop],
                    "unit_provenance": unit_provenance,
                    "praise_metadata": praise_metadata,
                    "emissivity_units": "W Hz^-1 m^-3 sr^-1",
                    "losses": ["full", "none"],
                    "final_index_handling": "calculate_praise_pair explicit final column",
                    "synchrotron_age_claim": False,
                    "pressure_treatment": treatment_chunk,
                    "pressure_treatment_identity_sha256": treatment["identity_sha256"],
                    "pressure_mode": "unsmoothed",
                }
                _atomic_write_json(metadata_path, metadata)
                write_stage_checkpoint(
                    marker,
                    stage="emissivity_chunk",
                    input_contract=contract,
                    outputs=[output, metadata_path],
                )
            chunk_paths.append(output)
            chunk_markers.append(marker)

    aggregate = stage_dir / "endpoint_emissivity.npz"
    manifest = stage_dir / "endpoint_emissivity_manifest.json"
    aggregate_marker = checkpoints / "emissivity_aggregate.json"
    aggregate_contract = {
        "cache": cache_identity,
        "pressure_treatment_identity_sha256": treatment["identity_sha256"],
        "chunk_markers": [_sha256_file(path) for path in chunk_markers],
        "row_order": "active rows in history cache endpoint_ids order",
    }
    aggregate_checkpoint = _checkpoint_if_valid(aggregate_marker, "emissivity_aggregate", aggregate_contract)
    if aggregate_checkpoint is None:
        ids_parts, row_parts, trim_parts, instantaneous_parts = [], [], [], []
        full_parts, none_parts = [], []
        for path in chunk_paths:
            with np.load(path) as chunk:
                ids_parts.append(chunk["physical_ids"])
                row_parts.append(chunk["cache_row_indices"])
                trim_parts.append(chunk["trim_affected"])
                instantaneous_parts.append(chunk["instantaneous_history"])
                full_parts.append(chunk["full"])
                none_parts.append(chunk["none"])
        ids = np.concatenate(ids_parts)
        cache_rows = np.concatenate(row_parts).astype(np.int64)
        trim_affected = np.concatenate(trim_parts).astype(bool)
        instantaneous_history = np.concatenate(instantaneous_parts).astype(bool)
        if not np.array_equal(ids, active_ids):
            raise WorkflowError("emissivity chunks do not reconstruct deterministic physical-ID order")
        if not np.array_equal(cache_rows, np.flatnonzero(treatment["active_mask"])):
            raise WorkflowError("emissivity chunks do not reconstruct deterministic active cache rows")
        if not np.array_equal(trim_affected, treatment["trim_affected_active_mask"]):
            raise WorkflowError("emissivity chunks do not reconstruct the treatment mask")
        if not np.array_equal(
            instantaneous_history, treatment["single_record_active_mask"]
        ):
            raise WorkflowError(
                "emissivity chunks do not reconstruct the singleton convention mask"
            )
        _atomic_savez(
            aggregate,
            physical_ids=ids,
            cache_row_indices=cache_rows,
            trim_affected=trim_affected,
            instantaneous_history=instantaneous_history,
            primary_active_mask=np.asarray(treatment["active_mask"], dtype=bool),
            conservative_active_mask=np.asarray(treatment["conservative_active_mask"], dtype=bool),
            full=np.concatenate(full_parts),
            none=np.concatenate(none_parts),
            frequencies_GHz=np.asarray(PRIMARY_CONTRACT["frequencies_GHz"]),
        )
        _atomic_write_json(
            manifest,
            {
                "cache_identity": cache_identity,
                "endpoint_count": int(len(ids)),
                "source_endpoint_count": int(len(expected_ids)),
                "id_chunk_size": int(id_chunk_size),
                "chunk_count": len(chunk_paths),
                "row_order": "active rows in unmodified history-cache endpoint ID order",
                "pressure_treatment": _pressure_treatment_report(treatment),
                "pressure_treatment_report": str(treatment_report),
                "contract": PRIMARY_CONTRACT,
                "actual_function": "plutokore.radio.praise.calculate_praise_emissivity_numba",
                "loss_treatments": ["full", "none"],
                "synchrotron_age_claim": False,
            },
        )
        aggregate_checkpoint = write_stage_checkpoint(
            aggregate_marker,
            stage="emissivity_aggregate",
            input_contract=aggregate_contract,
            outputs=[aggregate, manifest, treatment_report],
        )
    return {
        "emissivity_path": str(aggregate),
        "manifest_path": str(manifest),
        "chunk_count": len(chunk_paths),
        "reused_chunks": reused,
        "restart_identity_sha256": aggregate_checkpoint["restart_identity_sha256"],
        "pressure_treatment_path": str(treatment_report),
        "pressure_treatment_identity_sha256": treatment["identity_sha256"],
        "active_count": int(np.count_nonzero(treatment["active_mask"])),
        "conservative_active_count": int(np.count_nonzero(treatment["conservative_active_mask"])),
        "single_record_instantaneous_count": int(
            len(treatment["single_record_rows"])
        ),
    }


def derive_observables(
    emitted_intensity: Any,
    *,
    pixel_size_kpc: float,
    redshift: float,
    beam_fwhm_kpc: float,
    angular_diameter_distance_m: float,
) -> dict[str, Any]:
    values = np.asarray(getattr(emitted_intensity, "value", emitted_intensity), dtype=np.float64)
    if values.ndim == 2:
        values = values[:, :, None]
    if values.ndim != 3 or not np.all(np.isfinite(values)) or np.any(values < 0):
        raise WorkflowError("emitted intensity must be a finite non-negative (x, z, frequency) cube")
    if pixel_size_kpc <= 0 or beam_fwhm_kpc <= 0 or angular_diameter_distance_m <= 0:
        raise WorkflowError("pixel, beam, and angular-diameter distance must be positive")
    dimming = (1.0 + float(redshift)) ** -3
    observed = values * dimming
    sigma_pixels = beam_fwhm_kpc / (2.0 * math.sqrt(2.0 * math.log(2.0)) * pixel_size_kpc)
    beam_smoothed = np.stack(
        [gaussian_filter(observed[:, :, index], sigma=sigma_pixels, mode="constant", cval=0.0)
         for index in range(observed.shape[2])],
        axis=2,
    )
    theta = beam_fwhm_kpc * KPC_TO_M / angular_diameter_distance_m
    omega = math.pi * theta**2 / (4.0 * math.log(2.0))
    mjy_per_beam = beam_smoothed * 1.0e29 * omega
    pixel_area_m2 = (pixel_size_kpc * KPC_TO_M) ** 2
    luminosity = 4.0 * math.pi * np.sum(values, axis=(0, 1)) * pixel_area_m2
    return {
        "observed_intensity": observed,
        "mjy_per_beam": mjy_per_beam,
        "luminosity_W_Hz": luminosity,
        "dimming_factor": dimming,
        "beam_solid_angle_sr": omega,
        "beam_fwhm_kpc": float(beam_fwhm_kpc),
        "pixel_area_m2": pixel_area_m2,
        "luminosity_formula": "4*pi*sum(I_emit*pixel_area)",
        "specific_intensity_dimming": "(1+z)^-3 applied exactly once",
    }


def _rotation_matrix(view_deg: float) -> np.ndarray:
    angle = math.radians(float(view_deg))
    return np.array(
        [[1.0, 0.0, 0.0], [0.0, math.cos(angle), -math.sin(angle)], [0.0, math.sin(angle), math.cos(angle)]],
        dtype=float,
    )


def _component_labels_from_original_z(position_kpc: np.ndarray) -> tuple[np.ndarray, dict[str, Any]]:
    labels = (np.asarray(position_kpc)[:, 2] >= 0.0).astype(np.int64)
    unique, counts = np.unique(labels, return_counts=True)
    if np.any(counts < 4):
        raise WorkflowError("original-z support partition has fewer than four particles in a component")
    return labels, {
        "rule": "endpoint original-coordinate z sign; z>=0 and z<0",
        "component_counts": {str(int(k)): int(v) for k, v in zip(unique, counts, strict=True)},
        "interpretation": "deterministic support partition only; not an inferred radio topology",
        "bridging": "components raytraced separately and never bridged",
    }


def _raytrace_component_cropped(
    *,
    coords: np.ndarray,
    velocity: np.ndarray,
    emissivity: u.Quantity,
    labels: np.ndarray,
    view_deg: float,
    delta_r: float,
    pixel_size: float,
    support_bound: float,
    kd_jobs: int,
    grid_override: tuple[np.ndarray, np.ndarray] | None = None,
) -> tuple[u.Quantity, dict[str, Any]]:
    rot = _rotation_matrix(view_deg)
    ray_frame = coords @ rot.T
    margin = max(support_bound, pixel_size, max(PRIMARY_CONTRACT["beam_fwhm_kpc"]))
    # Rotation is around x. These invariant bounds enforce one physical
    # observing grid for all 0/45/90 degree views.
    x_limit = float(np.max(np.abs(coords[:, 0])) + margin)
    yz_limit = float(np.max(np.linalg.norm(coords[:, 1:3], axis=1)) + margin)
    if grid_override is None:
        x_grid = np.arange(-math.ceil(x_limit / pixel_size) * pixel_size,
                           math.ceil(x_limit / pixel_size) * pixel_size + pixel_size * 0.5,
                           pixel_size)
        z_grid = np.arange(-math.ceil(yz_limit / pixel_size) * pixel_size,
                           math.ceil(yz_limit / pixel_size) * pixel_size + pixel_size * 0.5,
                           pixel_size)
    else:
        x_grid, z_grid = (np.asarray(axis, dtype=np.float64) for axis in grid_override)
        if (
            x_grid.ndim != 1 or z_grid.ndim != 1
            or len(x_grid) < 2 or len(z_grid) < 2
            or not np.all(np.diff(x_grid) > 0) or not np.all(np.diff(z_grid) > 0)
        ):
            raise WorkflowError("fixed comparator observing grid is invalid")
    total = np.zeros((len(x_grid), len(z_grid), emissivity.shape[1]), dtype=np.float64) * INTENSITY_UNIT
    component_records = []
    for component in sorted(np.unique(labels).tolist()):
        select = labels == component
        projected = ray_frame[select]
        x_idx = np.flatnonzero((x_grid >= projected[:, 0].min() - margin) & (x_grid <= projected[:, 0].max() + margin))
        z_idx = np.flatnonzero((z_grid >= projected[:, 2].min() - margin) & (z_grid <= projected[:, 2].max() + margin))
        if not len(x_idx) or not len(z_idx):
            raise WorkflowError("component crop produced an empty observing grid")
        depth = (float(projected[:, 1].min() - margin), float(projected[:, 1].max() + margin))
        result = raytrace_radio(
            coords=coords[select],
            vel_vec=velocity[select],
            particle_emissivities=emissivity[select],
            grid=(x_grid[x_idx], z_grid[z_idx]),
            ray_depth_lim=depth,
            rot_mat=rot,
            s=PRIMARY_CONTRACT["s"],
            delta_r=delta_r,
            pixel_size_kpc=pixel_size,
            support_bound=support_bound,
            component_labels=np.zeros(np.count_nonzero(select), dtype=int),
            view_rotation_deg=view_deg,
            kd_jobs=kd_jobs,
        )
        total[np.ix_(x_idx, z_idx, np.arange(emissivity.shape[1]))] += result["map"]
        component_records.append({
            "component": int(component),
            "particles": int(np.count_nonzero(select)),
            "grid_shape": [len(x_idx), len(z_idx)],
            "ray_depth_lim_kpc": list(depth),
        })
    return total, {
        "grid_x_kpc": x_grid.tolist(),
        "grid_z_kpc": z_grid.tolist(),
        "grid_shape": [len(x_grid), len(z_grid)],
        "component_crops": component_records,
        "view_deg": float(view_deg),
        "delta_r_kpc": float(delta_r),
        "pixel_size_kpc": float(pixel_size),
        "support_bound_kpc": float(support_bound),
        "kd_jobs": int(kd_jobs),
        "path_conversion": "performed once by g_lo_radio_method_value.raytrace_radio",
        "grid_contract": "primary_active_support" if grid_override is None else "fixed_to_primary_active_support",
    }


def run_raytrace_stage(
    cache_path: Path,
    emissivity_path: Path,
    work_root: Path,
    *,
    kd_jobs: int = 16,
) -> dict[str, Any]:
    cache_path, emissivity_path, work_root = map(Path, (cache_path, emissivity_path, work_root))
    stage_dir = work_root / "compact" / "raytrace"
    checkpoints = work_root / ".checkpoints"
    stage_dir.mkdir(parents=True, exist_ok=True)
    checkpoints.mkdir(parents=True, exist_ok=True)
    with h5py.File(cache_path, "r") as h5, np.load(emissivity_path) as emis:
        support = _load_treatment_aligned_support(h5, emis)
        ids = support["primary_ids"]
        shock_threshold = float(h5.attrs["shock_threshold"])
        shock_component = int(h5.attrs["shock_component"])
        if not np.isclose(shock_threshold, 5.0, rtol=0.0, atol=1e-12):
            raise WorkflowError("raytrace cache is not bound to PLUTO shk_thresh=5")
        position = support["position"]
        velocity = support["velocity"]
        if position.shape != (len(ids), 3) or velocity.shape != position.shape:
            raise WorkflowError("endpoint position/velocity cache shape is invalid")
        beta_norm = np.linalg.norm(velocity, axis=1)
        if not np.all(np.isfinite(position)) or not np.all(np.isfinite(beta_norm)) or np.any(beta_norm >= 1.0):
            raise WorkflowError("endpoint coordinates or beta vectors are invalid")
        physical = {"position": position, "velocity": velocity}
        units = {
            "length_unit": "1 kpc",
            "speed_unit": "c",
            "endpoint_velocity_representation": "dimensionless beta vector",
            "shock_threshold": shock_threshold,
            "shock_component": shock_component,
        }
        full, none = support["full"], support["none"]
    if not np.all(np.isfinite(full)) or not np.all(np.isfinite(none)):
        raise WorkflowError("non-finite emissivity cannot be raytraced")
    labels, component_provenance = _component_labels_from_original_z(physical["position"])
    support_bound = derive_support_bound(physical["position"], multiplier=2.0)
    combined = np.column_stack((full, none)) * EMISSIVITY_UNIT
    source_contract = {
        "cache_sha256": _sha256_file(cache_path),
        "emissivity_sha256": _sha256_file(emissivity_path),
        "units": units,
        "components": component_provenance,
        "support_bound_kpc": support_bound,
        "kd_jobs": kd_jobs,
        "primary_active_ids_sha256": hashlib.sha256(ids.tobytes()).hexdigest(),
        "trim_affected_sha256": hashlib.sha256(support["trim_affected"].tobytes()).hexdigest(),
        "instantaneous_history_sha256": hashlib.sha256(
            support["instantaneous_history"].tobytes()
        ).hexdigest(),
        "conservative_active_ids_sha256": hashlib.sha256(
            support["comparator_ids"].tobytes()
        ).hexdigest(),
        "pressure_treatment": PRESSURE_TREATMENT_CONTRACT,
    }
    products: dict[str, Any] = {}
    comparator_products: dict[str, Any] = {}
    for view in PRIMARY_CONTRACT["views_deg"]:
        for step in PRIMARY_CONTRACT["ray_steps_kpc"]:
            key = f"view_{int(view):03d}_step_{step:.2f}"
            output = stage_dir / f"{key}.npz"
            metadata_path = stage_dir / f"{key}.json"
            marker = checkpoints / f"raytrace_{key}.json"
            contract = {**source_contract, "view_deg": view, "ray_step_kpc": step}
            checkpoint = _checkpoint_if_valid(marker, "raytrace", contract)
            if checkpoint is None:
                started = time.perf_counter()
                ray_map, metadata = _raytrace_component_cropped(
                    coords=physical["position"],
                    velocity=physical["velocity"],
                    emissivity=combined,
                    labels=labels,
                    view_deg=view,
                    delta_r=step,
                    pixel_size=PRIMARY_CONTRACT["pixel_size_kpc"],
                    support_bound=support_bound,
                    kd_jobs=kd_jobs,
                )
                values = ray_map.to_value(INTENSITY_UNIT)
                full_map, none_map = values[:, :, :2], values[:, :, 2:]
                if not np.all(np.isfinite(values)) or np.any(values < 0):
                    raise WorkflowError("raytracing returned non-finite or negative intensity")
                repeat_max_abs = None
                if np.isclose(step, 0.1):
                    repeat, _ = _raytrace_component_cropped(
                        coords=physical["position"],
                        velocity=physical["velocity"],
                        emissivity=combined,
                        labels=labels,
                        view_deg=view,
                        delta_r=step,
                        pixel_size=PRIMARY_CONTRACT["pixel_size_kpc"],
                        support_bound=support_bound,
                        kd_jobs=kd_jobs,
                    )
                    repeat_max_abs = float(np.max(np.abs(repeat.to_value(INTENSITY_UNIT) - values)))
                    if repeat_max_abs != 0.0:
                        raise WorkflowError("raytrace exact-repeat determinism failed")
                _atomic_savez(
                    output,
                    full=full_map,
                    none=none_map,
                    frequencies_GHz=np.asarray(PRIMARY_CONTRACT["frequencies_GHz"]),
                )
                metadata.update({
                    "component_provenance": component_provenance,
                    "intensity_units": "W Hz^-1 m^-2 sr^-1 emitted frame",
                    "repeat_max_abs": repeat_max_abs,
                    "elapsed_seconds": time.perf_counter() - started,
                    "peak_rss_bytes": peak_rss_bytes(),
                    "actual_function": "plutokore.radio.raytracing.raytrace_particles_multiple_freq",
                })
                _atomic_write_json(metadata_path, metadata)
                checkpoint = write_stage_checkpoint(
                    marker,
                    stage="raytrace",
                    input_contract=contract,
                    outputs=[output, metadata_path],
                )
            products[key] = {
                "path": str(output),
                "metadata": str(metadata_path),
                "restart_identity_sha256": checkpoint["restart_identity_sha256"],
            }
            if np.isclose(step, 0.1):
                comparator_key = f"{key}_conservative"
                comparator_output = stage_dir / f"{comparator_key}.npz"
                comparator_metadata_path = stage_dir / f"{comparator_key}.json"
                comparator_marker = checkpoints / f"raytrace_{comparator_key}.json"
                comparator_contract = {
                    **source_contract,
                    "view_deg": view,
                    "ray_step_kpc": step,
                    "support": "exclude_all_pressure_treatment_affected_histories",
                }
                comparator_checkpoint = _checkpoint_if_valid(
                    comparator_marker,
                    "raytrace_pressure_treatment_comparator",
                    comparator_contract,
                )
                if comparator_checkpoint is None:
                    primary_metadata = json.loads(metadata_path.read_text())
                    comparator_select = support["comparator_select"]
                    comparator_position = physical["position"][comparator_select]
                    comparator_velocity = physical["velocity"][comparator_select]
                    comparator_emissivity = combined[comparator_select]
                    comparator_labels, comparator_component_provenance = (
                        _component_labels_from_original_z(comparator_position)
                    )
                    comparator_map, comparator_metadata = _raytrace_component_cropped(
                        coords=comparator_position,
                        velocity=comparator_velocity,
                        emissivity=comparator_emissivity,
                        labels=comparator_labels,
                        view_deg=view,
                        delta_r=step,
                        pixel_size=PRIMARY_CONTRACT["pixel_size_kpc"],
                        support_bound=support_bound,
                        kd_jobs=kd_jobs,
                        grid_override=(
                            np.asarray(primary_metadata["grid_x_kpc"], dtype=np.float64),
                            np.asarray(primary_metadata["grid_z_kpc"], dtype=np.float64),
                        ),
                    )
                    comparator_values = comparator_map.to_value(INTENSITY_UNIT)
                    if (
                        not np.all(np.isfinite(comparator_values))
                        or np.any(comparator_values < 0)
                    ):
                        raise WorkflowError(
                            "pressure-treatment comparator raytrace is non-finite or negative"
                        )
                    _atomic_savez(
                        comparator_output,
                        full=comparator_values[:, :, :2],
                        none=comparator_values[:, :, 2:],
                        frequencies_GHz=np.asarray(PRIMARY_CONTRACT["frequencies_GHz"]),
                    )
                    comparator_metadata.update({
                        "support": "exclude_all_pressure_treatment_affected_histories",
                        "primary_active_count": int(len(ids)),
                        "comparator_active_count": int(np.count_nonzero(comparator_select)),
                        "excluded_trim_affected_count": int(
                            np.count_nonzero(support["trim_affected"])
                        ),
                        "excluded_single_record_instantaneous_count": int(
                            np.count_nonzero(support["instantaneous_history"])
                        ),
                        "component_provenance": comparator_component_provenance,
                        "physical_ids_sha256": hashlib.sha256(
                            support["comparator_ids"].tobytes()
                        ).hexdigest(),
                    })
                    _atomic_write_json(comparator_metadata_path, comparator_metadata)
                    comparator_checkpoint = write_stage_checkpoint(
                        comparator_marker,
                        stage="raytrace_pressure_treatment_comparator",
                        input_contract=comparator_contract,
                        outputs=[comparator_output, comparator_metadata_path],
                    )
                comparator_products[comparator_key] = {
                    "path": str(comparator_output),
                    "metadata": str(comparator_metadata_path),
                    "restart_identity_sha256": comparator_checkpoint[
                        "restart_identity_sha256"
                    ],
                }
    manifest = stage_dir / "raytrace_manifest.json"
    _atomic_write_json(
        manifest,
        {
            "contract": PRIMARY_CONTRACT,
            "component_provenance": component_provenance,
            "support_bound_kpc": support_bound,
            "products": products,
            "pressure_treatment_comparator_products": comparator_products,
            "source_contract": source_contract,
        },
    )
    return {
        "manifest_path": str(manifest),
        "products": products,
        "pressure_treatment_comparator_products": comparator_products,
    }


def _signed_persistent_evidence(
    primary: Sequence[Mapping[str, Any]],
    adjacent: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, Any] | None:
    for key, threshold in MATERIALITY_THRESHOLDS.items():
        for sign in (-1.0, 1.0):
            qualifying = [
                index for index, metrics in enumerate(primary)
                if key in metrics and np.isfinite(float(metrics[key]))
                and np.sign(float(metrics[key])) == sign and abs(float(metrics[key])) >= threshold
            ]
            if len(qualifying) < 2:
                continue
            for name, group in adjacent.items():
                adjacent_count = sum(
                    key in metrics and np.isfinite(float(metrics[key]))
                    and np.sign(float(metrics[key])) == sign and abs(float(metrics[key])) >= threshold
                    for metrics in group
                )
                if adjacent_count >= 2:
                    effect = max(abs(float(primary[index][key])) for index in qualifying)
                    return {
                        "metric": key,
                        "effect": effect,
                        "sign": int(sign),
                        "same_direction_views": len(qualifying),
                        "persistent_adjacent_sensitivity": name,
                    }
    topology_views = sum(bool(metrics.get("component_change", False)) for metrics in primary)
    if topology_views >= 2:
        for name, group in adjacent.items():
            if sum(bool(metrics.get("component_change", False)) for metrics in group) >= 2:
                return {
                    "metric": "component_change",
                    "effect": 1.0,
                    "sign": 0,
                    "same_direction_views": topology_views,
                    "persistent_adjacent_sensitivity": name,
                }
    return None


def decide_value_gate(
    *,
    gates: Mapping[str, bool],
    primary_view_metrics: Sequence[Mapping[str, Any]],
    adjacent_sensitivity_metrics: Mapping[str, Sequence[Mapping[str, Any]]],
    numerical_error: float = 0.0,
    stress_envelope_nonmaterial: bool = False,
) -> dict[str, Any]:
    for gate, label in (("history", DECISION_LABELS["history"]),
                        ("method", DECISION_LABELS["method"]),
                        ("compute", DECISION_LABELS["compute"])):
        if gates.get(gate) is not True:
            return {"decision_label": label, "blocked_gate": gate, "gates": dict(gates)}
    if not np.isfinite(numerical_error) or numerical_error < 0:
        return {"decision_label": DECISION_LABELS["method"], "blocked_gate": "numerical_error"}
    evidence = _signed_persistent_evidence(primary_view_metrics, adjacent_sensitivity_metrics)
    allowed_error = evidence["effect"] / 4.0 if evidence else min(MATERIALITY_THRESHOLDS.values()) / 4.0
    if numerical_error > allowed_error:
        return {
            "decision_label": DECISION_LABELS["method"],
            "blocked_gate": "numerical_convergence",
            "numerical_error": float(numerical_error),
            "maximum_allowed_numerical_error": float(allowed_error),
        }
    if evidence is not None:
        return {
            "decision_label": DECISION_LABELS["green"],
            **evidence,
            "numerical_error": float(numerical_error),
            "maximum_allowed_numerical_error": float(allowed_error),
            "materiality_thresholds": MATERIALITY_THRESHOLDS,
            "new_production_status": "review justified; not authorised or submitted",
        }
    scope = (
        "PARAMETER_PRESSURE_STRESS_ENVELOPE_ALSO_NON_MATERIAL"
        if stress_envelope_nonmaterial
        else "INSUFFICIENT_BY_ITSELF_TO_RULE_OUT_C_HI_C_LO_HISTORIES"
    )
    return {
        "decision_label": DECISION_LABELS["low"],
        "history_regeneration_scope": scope,
        "stress_envelope_nonmaterial": bool(stress_envelope_nonmaterial),
        "numerical_error": float(numerical_error),
        "maximum_allowed_numerical_error": float(allowed_error),
        "materiality_thresholds": MATERIALITY_THRESHOLDS,
    }


def assess_treatment_decision_stability(
    primary_decision: Mapping[str, Any],
    conservative_decision: Mapping[str, Any],
) -> dict[str, Any]:
    primary_label = str(primary_decision.get("decision_label", ""))
    conservative_label = str(conservative_decision.get("decision_label", ""))
    return {
        "stable": bool(primary_label and primary_label == conservative_label),
        "primary_decision_label": primary_label,
        "conservative_decision_label": conservative_label,
        "comparator": "exclude all trim-affected plus no-positive histories",
    }


def _integrated_map_spectrum(values: np.ndarray) -> dict[str, Any]:
    values = np.asarray(values, dtype=np.float64)
    if values.ndim != 3 or values.shape[2] != 2:
        raise WorkflowError("treatment comparison requires two-frequency map cubes")
    luminosity = (
        4.0
        * math.pi
        * np.sum(values, axis=(0, 1))
        * (PRIMARY_CONTRACT["pixel_size_kpc"] * KPC_TO_M) ** 2
    )
    if np.any(luminosity <= 0) or not np.all(np.isfinite(luminosity)):
        spectral_index = float("nan")
    else:
        spectral_index = float(
            -np.log(luminosity[1] / luminosity[0])
            / np.log(
                PRIMARY_CONTRACT["frequencies_GHz"][1]
                / PRIMARY_CONTRACT["frequencies_GHz"][0]
            )
        )
    return {
        "integrated_luminosity_W_Hz": luminosity.tolist(),
        "integrated_spectral_index": spectral_index,
    }


def _compare_pressure_treatment_maps(
    primary: np.ndarray,
    conservative: np.ndarray,
) -> dict[str, Any]:
    primary = np.asarray(primary, dtype=np.float64)
    conservative = np.asarray(conservative, dtype=np.float64)
    if primary.shape != conservative.shape or primary.ndim != 3 or primary.shape[2] != 2:
        raise WorkflowError("primary and conservative treatment maps do not align")
    bands = {}
    for index, frequency in enumerate(PRIMARY_CONTRACT["frequencies_GHz"]):
        denominator = max(float(np.sum(np.abs(primary[:, :, index]))), np.finfo(float).tiny)
        maximum = max(float(np.max(np.abs(primary[:, :, index]))), np.finfo(float).tiny)
        established = compare_loss_maps(
            primary[:, :, index],
            conservative[:, :, index],
            threshold=0.0,
        )
        bands[str(frequency)] = {
            "normalised_l1_map_difference": float(
                np.sum(np.abs(primary[:, :, index] - conservative[:, :, index]))
                / denominator
            ),
            "normalised_max_map_difference": float(
                np.max(np.abs(primary[:, :, index] - conservative[:, :, index]))
                / maximum
            ),
            "support_area_fraction_change": established["area_fraction_change"],
            "support_extent_fraction_change": established["extent_fraction_change"],
            "support_dice": established["mask_dice"],
            "support_component_change": established["component_change"],
            "support_components_primary": established["components_full"],
            "support_components_conservative": established["components_none"],
        }
    return {
        "primary": _integrated_map_spectrum(primary),
        "conservative": _integrated_map_spectrum(conservative),
        "per_frequency": bands,
    }


def _aggregate_metric_cube(full: np.ndarray, none: np.ndarray, threshold: float) -> dict[str, Any]:
    per_band = [
        compare_loss_maps(full[:, :, index], none[:, :, index], threshold=threshold)
        for index in range(full.shape[2])
    ]
    spectral = compare_loss_maps(
        full,
        none,
        threshold=threshold,
        frequencies=PRIMARY_CONTRACT["frequencies_GHz"],
    )["spectral_index_change"]
    collapsed: dict[str, Any] = {"spectral_index_change": spectral}
    for key in ("log10_luminosity_ratio", "area_fraction_change", "extent_fraction_change", "dice_change"):
        finite = [float(metrics[key]) for metrics in per_band if np.isfinite(float(metrics[key]))]
        collapsed[key] = max(finite, key=abs) if finite else float("nan")
    collapsed["component_change"] = int(any(bool(metrics["component_change"]) for metrics in per_band))
    collapsed["per_band"] = {
        str(freq): metrics
        for freq, metrics in zip(PRIMARY_CONTRACT["frequencies_GHz"], per_band, strict=True)
    }
    return collapsed


def run_metrics_stage(
    work_root: Path,
    *,
    angular_diameter_distance_m: float | None = None,
    stress_envelope_nonmaterial: bool = False,
    requested_memory_gb: float = 128.0,
) -> dict[str, Any]:
    work_root = Path(work_root)
    ray_dir = work_root / "compact" / "raytrace"
    output_dir = work_root / "compact" / "metrics"
    beam_map_dir = work_root / "compact" / "beam_maps"
    output_dir.mkdir(parents=True, exist_ok=True)
    beam_map_dir.mkdir(parents=True, exist_ok=True)
    if angular_diameter_distance_m is None:
        angular_diameter_distance_m = Planck18.angular_diameter_distance(
            PRIMARY_CONTRACT["redshift"]
        ).to_value(u.m)
        distance_provenance = "astropy.cosmology.Planck18"
    else:
        distance_provenance = "explicit override"
    all_metrics: dict[str, Any] = {}
    primary: list[dict[str, Any]] = []
    adjacent: dict[str, list[dict[str, Any]]] = {}
    conservative_primary: list[dict[str, Any]] = []
    conservative_adjacent: dict[str, list[dict[str, Any]]] = {}
    treatment_sensitivity: dict[str, Any] = {}
    convergence_errors = []
    for view in PRIMARY_CONTRACT["views_deg"]:
        step_maps = {}
        for step in PRIMARY_CONTRACT["ray_steps_kpc"]:
            path = ray_dir / f"view_{int(view):03d}_step_{step:.2f}.npz"
            if not path.is_file():
                raise WorkflowError(f"missing raytrace product: {path}")
            with np.load(path) as data:
                step_maps[step] = (data["full"], data["none"])
        primary_full, primary_none = step_maps[0.1]
        comparator_path = ray_dir / f"view_{int(view):03d}_step_0.10_conservative.npz"
        if not comparator_path.is_file():
            raise WorkflowError(
                f"missing pressure-treatment comparator raytrace product: {comparator_path}"
            )
        with np.load(comparator_path) as comparator_data:
            conservative_full = comparator_data["full"]
            conservative_none = comparator_data["none"]
        treatment_sensitivity[str(int(view))] = {
            "view_deg": float(view),
            "full_loss": _compare_pressure_treatment_maps(
                primary_full,
                conservative_full,
            ),
            "lossless": _compare_pressure_treatment_maps(
                primary_none,
                conservative_none,
            ),
        }
        for comparison_step in (0.05, 0.2):
            comparison_full, comparison_none = step_maps[comparison_step]
            denominator = max(
                float(np.sum(np.abs(comparison_full))) + float(np.sum(np.abs(comparison_none))),
                np.finfo(float).tiny,
            )
            convergence_errors.append(
                (float(np.sum(np.abs(primary_full - comparison_full))) +
                 float(np.sum(np.abs(primary_none - comparison_none)))) / denominator
            )
        for beam in PRIMARY_CONTRACT["beam_fwhm_kpc"]:
            obs_full = derive_observables(
                primary_full * INTENSITY_UNIT,
                pixel_size_kpc=PRIMARY_CONTRACT["pixel_size_kpc"],
                redshift=PRIMARY_CONTRACT["redshift"],
                beam_fwhm_kpc=beam,
                angular_diameter_distance_m=angular_diameter_distance_m,
            )
            obs_none = derive_observables(
                primary_none * INTENSITY_UNIT,
                pixel_size_kpc=PRIMARY_CONTRACT["pixel_size_kpc"],
                redshift=PRIMARY_CONTRACT["redshift"],
                beam_fwhm_kpc=beam,
                angular_diameter_distance_m=angular_diameter_distance_m,
            )
            conservative_obs_full = derive_observables(
                conservative_full * INTENSITY_UNIT,
                pixel_size_kpc=PRIMARY_CONTRACT["pixel_size_kpc"],
                redshift=PRIMARY_CONTRACT["redshift"],
                beam_fwhm_kpc=beam,
                angular_diameter_distance_m=angular_diameter_distance_m,
            )
            conservative_obs_none = derive_observables(
                conservative_none * INTENSITY_UNIT,
                pixel_size_kpc=PRIMARY_CONTRACT["pixel_size_kpc"],
                redshift=PRIMARY_CONTRACT["redshift"],
                beam_fwhm_kpc=beam,
                angular_diameter_distance_m=angular_diameter_distance_m,
            )
            _atomic_savez(
                beam_map_dir / f"view_{int(view):03d}_beam_{beam:g}_mjy_beam.npz",
                full=obs_full["mjy_per_beam"],
                none=obs_none["mjy_per_beam"],
                frequencies_GHz=np.asarray(PRIMARY_CONTRACT["frequencies_GHz"]),
                view_deg=np.asarray([view]),
                beam_fwhm_kpc=np.asarray([beam]),
                pixel_size_kpc=np.asarray([PRIMARY_CONTRACT["pixel_size_kpc"]]),
            )
            for threshold in PRIMARY_CONTRACT["threshold_mjy_beam"]:
                key = f"view_{int(view):03d}_beam_{beam:g}_threshold_{threshold:.8g}"
                metrics = _aggregate_metric_cube(
                    obs_full["mjy_per_beam"],
                    obs_none["mjy_per_beam"],
                    threshold,
                )
                metrics.update({
                    "view_deg": view,
                    "beam_fwhm_kpc": beam,
                    "threshold_mjy_beam": threshold,
                    "luminosity_full_W_Hz": obs_full["luminosity_W_Hz"],
                    "luminosity_none_W_Hz": obs_none["luminosity_W_Hz"],
                })
                conservative_metrics = _aggregate_metric_cube(
                    conservative_obs_full["mjy_per_beam"],
                    conservative_obs_none["mjy_per_beam"],
                    threshold,
                )
                conservative_metrics.update({
                    "view_deg": view,
                    "beam_fwhm_kpc": beam,
                    "threshold_mjy_beam": threshold,
                    "luminosity_full_W_Hz": conservative_obs_full["luminosity_W_Hz"],
                    "luminosity_none_W_Hz": conservative_obs_none["luminosity_W_Hz"],
                })
                all_metrics[key] = metrics
                if beam == 5.0 and np.isclose(threshold, 0.05):
                    primary.append(metrics)
                    conservative_primary.append(conservative_metrics)
                elif (
                    (beam in (2.5, 10.0) and np.isclose(threshold, 0.05))
                    or (beam == 5.0 and not np.isclose(threshold, 0.05))
                ):
                    sensitivity = f"beam_{beam:g}_threshold_{threshold:.8g}"
                    adjacent.setdefault(sensitivity, []).append(metrics)
                    conservative_adjacent.setdefault(sensitivity, []).append(
                        conservative_metrics
                    )
    peak = peak_rss_bytes()
    compute_gate = peak < requested_memory_gb * (1024**3) * 0.5
    primary_decision = decide_value_gate(
        gates={"history": True, "method": True, "compute": compute_gate},
        primary_view_metrics=primary,
        adjacent_sensitivity_metrics=adjacent,
        numerical_error=max(convergence_errors),
        stress_envelope_nonmaterial=stress_envelope_nonmaterial,
    )
    conservative_decision = decide_value_gate(
        gates={"history": True, "method": True, "compute": compute_gate},
        primary_view_metrics=conservative_primary,
        adjacent_sensitivity_metrics=conservative_adjacent,
        numerical_error=max(convergence_errors),
        stress_envelope_nonmaterial=stress_envelope_nonmaterial,
    )
    stability = assess_treatment_decision_stability(
        primary_decision,
        conservative_decision,
    )
    if stability["stable"]:
        decision = {**primary_decision, "pressure_treatment_decision_stability": stability}
    else:
        decision = {
            "decision_label": DECISION_LABELS["method"],
            "blocked_gate": "pressure_treatment_decision_stability",
            "pressure_treatment_decision_stability": stability,
            "primary_decision": primary_decision,
            "conservative_decision": conservative_decision,
        }
    report = {
        "decision": decision,
        "primary_decision_before_treatment_sensitivity": primary_decision,
        "conservative_decision": conservative_decision,
        "pressure_treatment_decision_stability": stability,
        "pressure_treatment_sensitivity": treatment_sensitivity,
        "comparator_numerical_error_assumption": (
            "the conservative 0.1-kpc comparator inherits the primary treatment's "
            "0.05/0.1/0.2 ray-step convergence error; it does not claim an "
            "independent comparator step sweep"
        ),
        "primary_view_metrics": primary,
        "sensitivity_metrics": adjacent,
        "all_metrics": all_metrics,
        "ray_convergence_fractional_l1": convergence_errors,
        "angular_diameter_distance_m": angular_diameter_distance_m,
        "angular_diameter_distance_provenance": distance_provenance,
        "observed_intensity_dimming": "(1+z)^-3",
        "luminosity_formula": "4*pi*sum(I_emit*pixel_area); no extra 4pi division",
        "synchrotron_age_claim": False,
        "beam_map_products": sorted(
            str(path.relative_to(work_root / "compact"))
            for path in beam_map_dir.glob("*.npz")
        ),
        "beam_map_purpose": "compact radio surface retained for later accepted X-ray/truth overlap without rerunning",
        "peak_rss_bytes": peak,
        "requested_memory_bytes": int(requested_memory_gb * 1024**3),
        "rss_below_half_requested": compute_gate,
    }
    decision_path = output_dir / "decision.json"
    metrics_path = output_dir / "metrics.json"
    csv_path = output_dir / "view_metrics.csv"
    treatment_path = output_dir / "pressure_treatment_sensitivity.json"
    treatment_csv_path = output_dir / "pressure_treatment_sensitivity.csv"
    _atomic_write_json(decision_path, decision)
    _atomic_write_json(metrics_path, report)
    _atomic_write_json(
        treatment_path,
        {
            "contract": PRESSURE_TREATMENT_CONTRACT,
            "decision_stability": stability,
            "primary_decision": primary_decision,
            "conservative_decision": conservative_decision,
            "views": treatment_sensitivity,
        },
    )
    with tempfile.NamedTemporaryFile(
        "w",
        newline="",
        dir=output_dir,
        prefix=".pressure_treatment_sensitivity.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow((
            "view_deg", "loss_treatment", "frequency_GHz",
            "primary_luminosity_W_Hz", "conservative_luminosity_W_Hz",
            "primary_integrated_spectral_index", "conservative_integrated_spectral_index",
            "normalised_l1_map_difference", "normalised_max_map_difference",
            "support_area_fraction_change", "support_extent_fraction_change",
            "support_dice", "support_component_change",
        ))
        for view_record in treatment_sensitivity.values():
            for loss_name in ("full_loss", "lossless"):
                comparison = view_record[loss_name]
                for index, frequency in enumerate(PRIMARY_CONTRACT["frequencies_GHz"]):
                    band = comparison["per_frequency"][str(frequency)]
                    writer.writerow((
                        view_record["view_deg"],
                        loss_name,
                        frequency,
                        comparison["primary"]["integrated_luminosity_W_Hz"][index],
                        comparison["conservative"]["integrated_luminosity_W_Hz"][index],
                        comparison["primary"]["integrated_spectral_index"],
                        comparison["conservative"]["integrated_spectral_index"],
                        band["normalised_l1_map_difference"],
                        band["normalised_max_map_difference"],
                        band["support_area_fraction_change"],
                        band["support_extent_fraction_change"],
                        band["support_dice"],
                        band["support_component_change"],
                    ))
        treatment_temporary = handle.name
    os.replace(treatment_temporary, treatment_csv_path)
    with tempfile.NamedTemporaryFile("w", newline="", dir=output_dir, prefix=".view_metrics.", suffix=".tmp", delete=False) as handle:
        writer = csv.writer(handle)
        writer.writerow(("view_deg", "beam_fwhm_kpc", "threshold_mjy_beam", *MATERIALITY_THRESHOLDS, "component_change"))
        for metrics in all_metrics.values():
            writer.writerow((
                metrics["view_deg"], metrics["beam_fwhm_kpc"], metrics["threshold_mjy_beam"],
                *(metrics.get(key) for key in MATERIALITY_THRESHOLDS),
                metrics["component_change"],
            ))
        temporary = handle.name
    os.replace(temporary, csv_path)
    return {
        "decision_path": str(decision_path),
        "metrics_path": str(metrics_path),
        "csv_path": str(csv_path),
        "pressure_treatment_sensitivity_path": str(treatment_path),
        "pressure_treatment_sensitivity_csv_path": str(treatment_csv_path),
        **decision,
    }


def project_cache_bytes(endpoint_count: int, output_count: int) -> int:
    histories = 4 * endpoint_count * output_count * 8
    presence = endpoint_count * output_count
    endpoint = endpoint_count * (8 + 3 * 8 + 3 * 8 + 8)
    axes = output_count * 16
    return int((histories + presence + endpoint + axes) * 1.10)


def storage_preflight(
    cache_root: Path,
    *,
    endpoint_count: int,
    output_count: int,
    minimum_free_reserve_gb: float = 130.0,
    max_projected_free_fraction: float = 0.70,
) -> dict[str, Any]:
    usage = shutil.disk_usage(Path(cache_root))
    projected = project_cache_bytes(endpoint_count, output_count)
    reserve = int(minimum_free_reserve_gb * 1024**3)
    if usage.free < reserve:
        raise WorkflowError(f"free storage reserve is below {minimum_free_reserve_gb:g} GB")
    if projected > usage.free * max_projected_free_fraction:
        raise WorkflowError("projected cache use exceeds 70% of verified free storage")
    return {
        "free_bytes": usage.free,
        "projected_cache_bytes": projected,
        "minimum_free_reserve_bytes": reserve,
        "max_projected_free_fraction": max_projected_free_fraction,
        "passed": True,
    }


def verify_plutokore_source(source: Path) -> dict[str, Any]:
    source = Path(source)
    pre_purge_commit = os.environ.get("GOAL049_VERIFIED_PLUTOKORE_COMMIT")
    try:
        commit = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        verification = "live_git"
        if pre_purge_commit is not None and commit != pre_purge_commit:
            raise WorkflowError("live plutokore commit differs from the pre-purge verified commit")
    except FileNotFoundError as exc:
        if pre_purge_commit is None:
            raise WorkflowError(
                "git is unavailable and no pre-purge plutokore commit was exported"
            ) from exc
        commit = pre_purge_commit
        verification = "exported_pre_purge_commit_git_unavailable"
    except subprocess.CalledProcessError as exc:
        raise WorkflowError(f"cannot verify staged plutokore source: {source}") from exc
    if commit != EXPECTED_PLUTOKORE_COMMIT:
        raise WorkflowError(f"plutokore commit mismatch: {commit}")
    files = {
        "praise.py": source / "src/plutokore/radio/praise.py",
        "raytracing.py": source / "src/plutokore/radio/raytracing.py",
    }
    if any(not path.is_file() for path in files.values()):
        raise WorkflowError("staged plutokore implementation files are missing")
    return {
        "commit": commit,
        "commit_verification": verification,
        "pre_purge_commit": pre_purge_commit,
        "source": str(source),
        "implementation_sha256": {
            name: _sha256_file(path) for name, path in files.items()
        },
    }


def run_audit_stage(initial_root: Path, guarded_root: Path, work_root: Path) -> dict[str, Any]:
    work_root = Path(work_root)
    output = work_root / "compact" / "manifests" / "source_audit.json"
    marker = work_root / ".checkpoints" / "audit.json"
    contract = {
        "initial_root": str(Path(initial_root).resolve()),
        "guarded_root": str(Path(guarded_root).resolve()),
        "initial_outputs": [0, 1499],
        "guarded_outputs": [1000, 5000],
        "restart_anchor": 1000,
        "canonical_rule": "initial 0000..0999 plus guarded 1000..5000",
    }
    checkpoint = _checkpoint_if_valid(marker, "audit", contract)
    if checkpoint is not None:
        return json.loads(output.read_text())
    report = audit_roots(Path(initial_root), Path(guarded_root), restart_anchor_index=1000)
    if report["n_outputs"] != 5001 or report["canonical_switch"]["validated"] is not True:
        raise WorkflowError("source audit did not establish the 5001-output canonical history")
    if report["restart_anchor"]["validated_exact"] is not True:
        raise WorkflowError("source audit did not establish exact output-1000 restart identity")
    _atomic_write_json(output, report)
    write_stage_checkpoint(marker, stage="audit", input_contract=contract, outputs=[output])
    return report


def run_cache_stage(
    audit_report: Mapping[str, Any],
    work_root: Path,
    *,
    shock_threshold: float = 5.0,
    particle_chunk_rows: int = 4096,
    time_chunk: int = 32,
) -> dict[str, Any]:
    work_root = Path(work_root)
    cache_dir = work_root / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / "g_lo_history.h5"
    inprogress = cache_dir / "g_lo_history.h5.inprogress"
    manifest = work_root / "compact" / "manifests" / "cache_manifest.json"
    marker = work_root / ".checkpoints" / "cache.json"
    source_identity = _payload_sha256({
        "canonical_paths": audit_report["canonical_paths"],
        "source_sha256": audit_report["source_sha256"],
        "restart_anchor": audit_report["restart_anchor"],
        "canonical_switch": audit_report["canonical_switch"],
    })
    contract = {
        "source_identity_sha256": source_identity,
        "endpoint_count": audit_report["endpoint_count"],
        "output_count": audit_report["n_outputs"],
        "dtype": "float64",
        "shock_threshold": shock_threshold,
        "particle_chunk_rows": particle_chunk_rows,
        "time_chunk": time_chunk,
    }
    checkpoint = _checkpoint_if_valid(marker, "cache", contract)
    if checkpoint is not None:
        return json.loads(manifest.read_text())
    if cache.exists():
        raise WorkflowError("completed cache exists without a valid completion marker")
    endpoint_ids = endpoint_ids_from_final(Path(audit_report["canonical_paths"][-1]))
    with h5py.File(inprogress, "a") as h5:
        existing_source = h5.attrs.get("source_identity_sha256")
        if existing_source is not None and str(existing_source) != source_identity:
            raise WorkflowError("in-progress cache source identity mismatch")
        h5.attrs["source_identity_sha256"] = source_identity
        h5.attrs["cache_contract_sha256"] = _payload_sha256(contract)
        h5.flush()
    build_report = build_history_cache(
        [Path(path) for path in audit_report["canonical_paths"]],
        inprogress,
        endpoint_ids=endpoint_ids,
        particle_chunk_rows=particle_chunk_rows,
        time_chunk=time_chunk,
        dtype="float64",
        shock_threshold=shock_threshold,
    )
    with h5py.File(inprogress, "a") as h5:
        completeness = _validate_completed_cache(h5)
        h5.attrs["source_identity_sha256"] = source_identity
        h5.attrs["unit_state"] = "PLUTO code units; convert only at PRAiSE/raytrace boundary"
        h5.flush()
    os.replace(inprogress, cache)
    report = {
        **build_report,
        **completeness,
        "cache": str(cache),
        "cache_bytes": cache.stat().st_size,
        "source_identity_sha256": source_identity,
        "restartable_inprogress_path": str(inprogress),
        "history_cache_in_git": False,
    }
    _atomic_write_json(manifest, report)
    write_stage_checkpoint(marker, stage="cache", input_contract=contract, outputs=[cache, manifest])
    return report


def create_compact_package(
    products_dir: Path,
    archive: Path,
    *,
    max_file_bytes: int = 2 * 1024**3,
    max_total_bytes: int = 4 * 1024**3,
) -> dict[str, Any]:
    products_dir, archive = Path(products_dir), Path(archive)
    if archive.exists() or archive.is_symlink():
        raise WorkflowError(f"refusing to overwrite compact archive: {archive}")
    generated = {
        "archive_content_file_list.txt", "archive_checksums.sha256",
        "archive_manifest.tsv", "archive_file_list.txt", "package_manifest.json",
    }
    selected: list[Path] = []
    for path in sorted(products_dir.rglob("*")):
        if path.is_symlink():
            raise WorkflowError(f"compact package refuses symlink: {path}")
        if not path.is_file():
            continue
        relative = path.relative_to(products_dir)
        if relative.as_posix() in generated or path.name in generated:
            continue
        lower = path.name.lower()
        if lower.endswith((".h5", ".hdf5", ".dbl", ".flt", ".xmf")) or lower.startswith(("particles.", "data.")):
            continue
        if path.stat().st_size > max_file_bytes:
            raise WorkflowError(f"compact product exceeds per-file guard: {relative}")
        selected.append(relative)
    total = sum((products_dir / path).stat().st_size for path in selected)
    if total > max_total_bytes:
        raise WorkflowError("compact product total exceeds payload guard")
    content_list = products_dir / "archive_content_file_list.txt"
    checksums = products_dir / "archive_checksums.sha256"
    archive_manifest = products_dir / "archive_manifest.tsv"
    file_list = products_dir / "archive_file_list.txt"
    package_manifest = products_dir / "package_manifest.json"
    _atomic_write_bytes(content_list, ("".join(f"{path.as_posix()}\n" for path in selected)).encode())
    records = [
        {
            "relative_path": path.as_posix(),
            "bytes": (products_dir / path).stat().st_size,
            "sha256": _sha256_file(products_dir / path),
        }
        for path in selected
    ]
    _atomic_write_bytes(
        checksums,
        ("".join(f"{record['sha256']}  {record['relative_path']}\n" for record in records)).encode(),
    )
    _atomic_write_bytes(
        archive_manifest,
        ("relative_path\tbytes\tsha256\n" + "".join(
            f"{record['relative_path']}\t{record['bytes']}\t{record['sha256']}\n" for record in records
        )).encode(),
    )
    _atomic_write_json(
        package_manifest,
        {
            "manifest_scope": "explicit compact files plus stable archive metadata",
            "files": records,
            "content_bytes": total,
            "contains_history_cache": False,
            "contains_raw_particles": False,
        },
    )
    archive_files = sorted(selected + [path.relative_to(products_dir) for path in (
        content_list, checksums, archive_manifest, package_manifest, file_list
    )])
    _atomic_write_bytes(file_list, ("".join(f"{path.as_posix()}\n" for path in archive_files)).encode())
    archive.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{archive.name}.", suffix=".tmp", dir=archive.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with tarfile.open(fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT) as tar:
                    for relative in archive_files:
                        source = products_dir / relative
                        info = tar.gettarinfo(str(source), arcname=relative.as_posix())
                        info.uid = info.gid = 0
                        info.uname = info.gname = ""
                        info.mtime = 0
                        with source.open("rb") as handle:
                            tar.addfile(info, handle)
        with tarfile.open(temporary, "r:gz") as tar:
            names = tar.getnames()
        if names != [path.as_posix() for path in archive_files]:
            raise WorkflowError("compact archive file list validation failed")
        try:
            os.link(temporary, archive)
        except FileExistsError as exc:
            raise WorkflowError(f"refusing to overwrite compact archive: {archive}") from exc
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
    return {
        "archive": str(archive),
        "archive_sha256": _sha256_file(archive),
        "archive_bytes": archive.stat().st_size,
        "file_count": len(archive_files),
        "contains_history_cache": False,
        "contains_raw_particles": False,
    }


def _write_block(work_root: Path, label: str, error: Exception) -> None:
    _atomic_write_json(
        Path(work_root) / "compact" / "metrics" / "decision.json",
        {"decision_label": label, "error_type": type(error).__name__, "error": str(error)},
    )


def run_all(args: argparse.Namespace) -> dict[str, Any]:
    work_root = Path(args.work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        implementation = verify_plutokore_source(args.plutokore_source)
    except (OSError, WorkflowError, ValueError) as exc:
        _write_block(work_root, DECISION_LABELS["method"], exc)
        raise
    try:
        storage = storage_preflight(
            work_root,
            endpoint_count=args.expected_endpoint_count,
            output_count=5001,
            minimum_free_reserve_gb=args.minimum_free_reserve_gb,
            max_projected_free_fraction=args.max_projected_free_fraction,
        )
    except (OSError, WorkflowError, ValueError) as exc:
        _write_block(work_root, DECISION_LABELS["compute"], exc)
        raise
    try:
        audit = run_audit_stage(args.initial_root, args.guarded_root, work_root)
        if audit["endpoint_count"] != args.expected_endpoint_count:
            raise HistoryError(
                f"endpoint count {audit['endpoint_count']} != expected {args.expected_endpoint_count}"
            )
        cache = run_cache_stage(audit, work_root, shock_threshold=args.shock_threshold)
    except (HistoryError, OSError, WorkflowError, ValueError) as exc:
        _write_block(work_root, DECISION_LABELS["history"], exc)
        raise
    try:
        emissivity = run_emissivity_stage(
            cache["cache"], work_root, id_chunk_size=args.id_chunk_size
        )
        raytrace = run_raytrace_stage(
            cache["cache"], emissivity["emissivity_path"], work_root, kd_jobs=args.kd_jobs
        )
        metrics = run_metrics_stage(
            work_root,
            angular_diameter_distance_m=args.angular_diameter_distance_m,
            stress_envelope_nonmaterial=args.stress_envelope_nonmaterial,
            requested_memory_gb=args.requested_memory_gb,
        )
    except PressureTreatmentError as exc:
        _write_block(work_root, DECISION_LABELS["history"], exc)
        raise
    except (OSError, WorkflowError, ValueError, FloatingPointError) as exc:
        _write_block(work_root, DECISION_LABELS["method"], exc)
        raise
    runtime = {
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_bytes": peak_rss_bytes(),
        "cache_bytes": Path(cache["cache"]).stat().st_size,
        "compact_output_bytes": sum(
            path.stat().st_size for path in (work_root / "compact").rglob("*") if path.is_file()
        ),
        "storage_preflight": storage,
        "plutokore": implementation,
        "implementation_sha256": {
            "run_g_lo_radio_history_value.py": _sha256_file(Path(__file__)),
            "g_lo_particle_history.py": _sha256_file(
                Path(sys.modules[audit_roots.__module__].__file__)
            ),
            "g_lo_radio_method_value.py": _sha256_file(
                Path(sys.modules[calculate_praise_pair.__module__].__file__)
            ),
        },
        "restart_identity": {
            "emissivity": emissivity["restart_identity_sha256"],
            "raytrace_manifest_sha256": _sha256_file(Path(raytrace["manifest_path"])),
        },
    }
    _atomic_write_json(work_root / "compact" / "manifests" / "runtime_manifest.json", runtime)
    result = {"audit": audit, "cache": cache, "emissivity": emissivity, "raytrace": raytrace, "metrics": metrics, "runtime": runtime}
    if not args.no_package:
        result["package"] = create_compact_package(work_root / "compact", args.archive)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument("--initial-root", type=Path, required=True)
    audit.add_argument("--guarded-root", type=Path, required=True)
    audit.add_argument("--work-root", type=Path, required=True)
    cache = subparsers.add_parser("cache")
    cache.add_argument("--audit-json", type=Path, required=True)
    cache.add_argument("--work-root", type=Path, required=True)
    cache.add_argument("--shock-threshold", type=float, default=5.0)
    emissivity = subparsers.add_parser("emissivity")
    emissivity.add_argument("--cache", type=Path, required=True)
    emissivity.add_argument("--work-root", type=Path, required=True)
    emissivity.add_argument("--id-chunk-size", type=int, default=4096)
    raytrace = subparsers.add_parser("raytrace")
    raytrace.add_argument("--cache", type=Path, required=True)
    raytrace.add_argument("--emissivity", type=Path, required=True)
    raytrace.add_argument("--work-root", type=Path, required=True)
    raytrace.add_argument("--kd-jobs", type=int, default=16)
    metrics = subparsers.add_parser("metrics")
    metrics.add_argument("--work-root", type=Path, required=True)
    metrics.add_argument("--angular-diameter-distance-m", type=float)
    metrics.add_argument("--stress-envelope-nonmaterial", action="store_true")
    metrics.add_argument("--requested-memory-gb", type=float, default=128.0)
    package = subparsers.add_parser("package")
    package.add_argument("--products-dir", type=Path, required=True)
    package.add_argument("--archive", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--initial-root", type=Path, required=True)
    run.add_argument("--guarded-root", type=Path, required=True)
    run.add_argument("--work-root", type=Path, required=True)
    run.add_argument("--plutokore-source", type=Path, required=True)
    run.add_argument("--archive", type=Path)
    run.add_argument("--no-package", action="store_true")
    run.add_argument("--expected-endpoint-count", type=int, default=197568)
    run.add_argument("--shock-threshold", type=float, default=5.0)
    run.add_argument("--id-chunk-size", type=int, default=4096)
    run.add_argument("--kd-jobs", type=int, default=16)
    run.add_argument("--requested-memory-gb", type=float, default=128.0)
    run.add_argument("--minimum-free-reserve-gb", type=float, default=130.0)
    run.add_argument("--max-projected-free-fraction", type=float, default=0.70)
    run.add_argument("--angular-diameter-distance-m", type=float)
    run.add_argument("--stress-envelope-nonmaterial", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.mode == "audit":
            result = run_audit_stage(args.initial_root, args.guarded_root, args.work_root)
        elif args.mode == "cache":
            result = run_cache_stage(
                json.loads(args.audit_json.read_text()),
                args.work_root,
                shock_threshold=args.shock_threshold,
            )
        elif args.mode == "emissivity":
            result = run_emissivity_stage(args.cache, args.work_root, id_chunk_size=args.id_chunk_size)
        elif args.mode == "raytrace":
            result = run_raytrace_stage(args.cache, args.emissivity, args.work_root, kd_jobs=args.kd_jobs)
        elif args.mode == "metrics":
            result = run_metrics_stage(
                args.work_root,
                angular_diameter_distance_m=args.angular_diameter_distance_m,
                stress_envelope_nonmaterial=args.stress_envelope_nonmaterial,
                requested_memory_gb=args.requested_memory_gb,
            )
        elif args.mode == "package":
            result = create_compact_package(args.products_dir, args.archive)
        else:
            if not args.no_package and args.archive is None:
                raise WorkflowError("--archive is required unless --no-package is set")
            result = run_all(args)
    except (HistoryError, WorkflowError, OSError, ValueError) as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(_jsonable(result), indent=2, sort_keys=True))
    if args.mode == "run":
        label = result["metrics"]["decision_label"]
        if label in (DECISION_LABELS["history"], DECISION_LABELS["method"], DECISION_LABELS["compute"]):
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
