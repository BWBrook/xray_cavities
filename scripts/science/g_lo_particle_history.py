#!/usr/bin/env python3
"""Strict, field-selective recovery of PLUTO particle output histories.

The reader intentionally streams rows from each output.  It is suitable for
the retained G-LO surface and does not construct an all-field history cube.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Mapping, Sequence

import numpy as np


class HistoryError(RuntimeError):
    """Raised when a source/history gate fails closed."""


@dataclass(frozen=True)
class ParticleHeader:
    output_index: int
    header_offset: int
    endianity: str
    precision: str
    field_names: tuple[str, ...]
    field_dimensions: tuple[int, ...]
    nparticles: int
    time: float
    shock_thresholds: tuple[float, ...] | None
    payload_width: int
    payload_size: int
    file_size: int

    @property
    def field_dim(self) -> tuple[int, ...]:
        return self.field_dimensions

    @property
    def field_dims(self) -> tuple[int, ...]:
        return self.field_dimensions

    @property
    def payload_offset(self) -> int:
        return self.header_offset

    @property
    def nelem(self) -> int:
        return sum(self.field_dimensions)


@dataclass(frozen=True)
class ParticleData:
    path: Path
    header: ParticleHeader
    ids: np.ndarray
    fields: dict[str, np.ndarray]

    @property
    def data(self) -> dict[str, np.ndarray]:
        return self.fields


@dataclass(frozen=True)
class RootResolution:
    canonical_paths: tuple[Path, ...]
    overlap_indices: tuple[int, ...]
    hashes: dict[int, str]
    restart_anchor_index: int
    restart_anchor_sha256: str
    superseded_overlap_indices: tuple[int, ...]


@dataclass(frozen=True)
class Completeness:
    valid_pre_injection_absence: set[tuple[int, int]]
    missing_post_injection: set[tuple[int, int]]


_FILE_RE = re.compile(r"^particles\.(\d+)\.(?:dbl|flt)$")
_META_ALIASES = {
    "nparticles": "nparticles", "nfields": "nfields", "nelem": "nelem",
    "field_names": "field_names", "field_dim": "field_dim", "field_dimensions": "field_dim",
    "endianity": "endianity", "precision": "precision", "time": "time",
    "shock_thresholds": "shock_thresholds", "shock_threshold": "shock_thresholds", "shk_thresh": "shock_thresholds",
}


def _metadata(path: Path) -> tuple[dict[str, str], int]:
    values: dict[str, str] = {}
    with path.open("rb") as fh:
        while True:
            offset = fh.tell()
            marker = fh.read(1)
            if marker != b"#":
                return values, offset
            line = marker + fh.readline(65536)
            if not line.endswith(b"\n"):
                raise HistoryError(f"{path}: unterminated particle header line")
            try:
                parts = line.decode("ascii").split()
            except UnicodeDecodeError as exc:
                raise HistoryError(f"{path}: non-ASCII particle header") from exc
            if len(parts) < 3:
                continue
            key = "PLUTO_version" if parts[1] == "PLUTO" else parts[1]
            canonical = _META_ALIASES.get(key, key)
            if canonical in values and canonical in _META_ALIASES.values():
                raise HistoryError(f"{path}: duplicate metadata {canonical}")
            values[canonical] = " ".join(parts[2:])


def _output_index(path: Path) -> int:
    match = _FILE_RE.match(path.name)
    if not match:
        raise HistoryError(f"{path}: expected particles.NNNN.dbl/flt filename")
    return int(match.group(1))


def parse_particle_header(path: Path) -> ParticleHeader:
    meta, offset = _metadata(path)
    required = ("nparticles", "nfields", "nelem", "field_names", "field_dim", "endianity", "precision", "time")
    missing = [key for key in required if key not in meta]
    if missing:
        raise HistoryError(f"{path}: missing particle metadata: {', '.join(missing)}")
    try:
        nparticles = int(meta["nparticles"]); nfields = int(meta["nfields"]); nelem = int(meta["nelem"])
        time_value = float(meta["time"])
    except ValueError as exc:
        raise HistoryError(f"{path}: malformed numeric metadata") from exc
    if nparticles <= 0 or nfields <= 0 or nelem <= 0 or not math.isfinite(time_value):
        raise HistoryError(f"{path}: invalid particle metadata values")
    names = tuple(meta["field_names"].split())
    try:
        dims = tuple(int(x) for x in meta["field_dim"].split())
    except ValueError as exc:
        raise HistoryError(f"{path}: malformed field_dim") from exc
    if len(names) != nfields or len(dims) != nfields or sum(dims) != nelem or any(x <= 0 for x in dims):
        raise HistoryError(f"{path}: field schema does not match nfields/nelem")
    endian = meta["endianity"].lower()
    if endian in {"le", "little-endian"}: endian = "little"
    if endian in {"be", "big-endian"}: endian = "big"
    if endian not in {"little", "big"}: raise HistoryError(f"{path}: unsupported endianity {endian}")
    precision = meta["precision"].lower()
    if precision in {"float", "single", "float32"}: precision = "single"
    if precision in {"double", "float64"}: precision = "double"
    if precision not in {"single", "double"}: raise HistoryError(f"{path}: unsupported precision {precision}")
    thresholds = None
    if "shock_thresholds" in meta:
        try: thresholds = tuple(float(x) for x in meta["shock_thresholds"].split())
        except ValueError as exc: raise HistoryError(f"{path}: malformed shock thresholds") from exc
        if any(not math.isfinite(x) for x in thresholds): raise HistoryError(f"{path}: non-finite shock threshold")
    itemsize = 4 if precision == "single" else 8
    payload_width = nelem * itemsize
    file_size = path.stat().st_size
    payload_size = nparticles * payload_width
    if file_size != offset + payload_size:
        raise HistoryError(f"{path}: exact file-size mismatch; expected {offset + payload_size}, found {file_size}")
    return ParticleHeader(_output_index(path), offset, endian, precision, names, dims, nparticles, time_value,
                          thresholds, payload_width, payload_size, file_size)


def _layout(header: ParticleHeader) -> dict[str, tuple[int, int]]:
    out = {}; offset = 0
    for name, dim in zip(header.field_names, header.field_dimensions, strict=True):
        if name in out: raise HistoryError(f"duplicate field name {name}")
        out[name] = (offset, dim); offset += dim
    return out


def parse_particle_file(path: Path, *, fields: Sequence[str] = (), vector_components: Mapping[str, int] | None = None,
                        chunk_rows: int = 8192) -> ParticleData:
    path = Path(path); header = parse_particle_header(path); layout = _layout(header)
    vector_components = dict(vector_components or {})
    requested = tuple(dict.fromkeys(("id",) + tuple(fields) + tuple(vector_components)))
    if "id" not in layout: raise HistoryError(f"{path}: particle ID field is absent")
    for name in requested:
        if name not in layout: raise HistoryError(f"{path}: requested field absent: {name}")
    for name, component in vector_components.items():
        dim = layout[name][1]
        if not isinstance(component, int) or component < 0 or component >= dim: raise HistoryError(f"{path}: invalid component {component} for {name}")
    dtype = np.dtype(("<" if header.endianity == "little" else ">") + ("f4" if header.precision == "single" else "f8"))
    offsets = {name: (layout[name][0], layout[name][1]) for name in requested}
    result: dict[str, np.ndarray] = {}
    for name, (_, dim) in offsets.items():
        if name == "id": continue
        selected_dim = 1 if name in vector_components else dim
        result[name] = np.empty((header.nparticles,) if selected_dim == 1 else (header.nparticles, selected_dim), dtype=np.float64)
    ids = np.empty(header.nparticles, dtype=np.int64)
    with path.open("rb") as fh:
        fh.seek(header.header_offset)
        for start in range(0, header.nparticles, chunk_rows):
            count = min(chunk_rows, header.nparticles - start)
            raw = fh.read(count * header.payload_width)
            if len(raw) != count * header.payload_width: raise HistoryError(f"{path}: truncated payload")
            rows = np.frombuffer(raw, dtype=dtype).reshape(count, header.nelem)
            id_offset, id_dim = layout["id"]
            if id_dim != 1: raise HistoryError(f"{path}: id must be scalar")
            id_values = rows[:, id_offset].astype(np.float64)
            if np.any(~np.isfinite(id_values)) or np.any(id_values <= 0) or np.any(id_values != np.floor(id_values)):
                raise HistoryError(f"{path}: IDs must be finite positive integers")
            ids[start:start + count] = id_values.astype(np.int64)
            for name, (off, dim) in offsets.items():
                if name == "id": continue
                vals = rows[:, off] if dim == 1 else rows[:, off:off + dim]
                if name in vector_components:
                    vals = vals[:, vector_components[name]]
                result[name][start:start + count] = vals
    if len(np.unique(ids)) != len(ids): raise HistoryError(f"{path}: duplicate particle IDs")
    if any(np.any(~np.isfinite(v)) for v in result.values()): raise HistoryError(f"{path}: non-finite particle payload")
    return ParticleData(path, header, ids, result)


def _file_for(root: Path, index: int) -> Path:
    matches = sorted(root.glob(f"particles.{index:04d}.*"))
    matches = [p for p in matches if _FILE_RE.match(p.name)]
    if len(matches) != 1: raise HistoryError(f"{root}: expected exactly one particle file for output {index}, found {len(matches)}")
    return matches[0]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def resolve_roots(
    initial_root: Path,
    guarded_root: Path,
    *,
    initial_range=range(0, 1500),
    guarded_range=range(1000, 5001),
    restart_anchor_index: int = 1000,
) -> RootResolution:
    initial_root = Path(initial_root); guarded_root = Path(guarded_root)
    initial = {i: _file_for(initial_root, i) for i in initial_range}; guarded = {i: _file_for(guarded_root, i) for i in guarded_range}
    if restart_anchor_index not in initial or restart_anchor_index not in guarded:
        raise HistoryError(f"restart anchor {restart_anchor_index} must exist in both roots")
    anchor_initial = initial[restart_anchor_index]
    anchor_guarded = guarded[restart_anchor_index]
    initial_header = parse_particle_header(anchor_initial)
    guarded_header = parse_particle_header(anchor_guarded)
    anchor_initial_hash = _sha256(anchor_initial)
    anchor_guarded_hash = _sha256(anchor_guarded)
    if (
        initial_header.field_names,
        initial_header.field_dimensions,
        initial_header.endianity,
        initial_header.precision,
        initial_header.nparticles,
        initial_header.time,
        initial_header.file_size,
        initial_header.shock_thresholds,
        anchor_initial_hash,
    ) != (
        guarded_header.field_names,
        guarded_header.field_dimensions,
        guarded_header.endianity,
        guarded_header.precision,
        guarded_header.nparticles,
        guarded_header.time,
        guarded_header.file_size,
        guarded_header.shock_thresholds,
        anchor_guarded_hash,
    ):
        raise HistoryError(f"restart anchor output {restart_anchor_index} mismatch")
    hashes: dict[int, str] = {}; canonical: list[Path] = []
    for i in sorted(set(initial) | set(guarded)):
        if i < restart_anchor_index:
            if i not in initial:
                raise HistoryError(f"initial root is missing canonical output {i}")
            path = initial[i]
        else:
            if i not in guarded:
                raise HistoryError(f"guarded root is missing canonical output {i}")
            path = guarded[i]
        canonical.append(path)
        hashes[i] = _sha256(path)
    overlap = tuple(sorted(set(initial) & set(guarded)))
    return RootResolution(
        tuple(canonical),
        overlap,
        hashes,
        restart_anchor_index,
        anchor_initial_hash,
        tuple(i for i in overlap if i > restart_anchor_index),
    )


def validate_seam(times: Sequence[float], *, seam: tuple[int, int] = (1499, 1500), relative_tolerance: float = 0.05) -> bool:
    vals = [float(x) for x in times]
    if len(vals) < 3 or any(not math.isfinite(x) for x in vals) or any(b <= a for a, b in zip(vals, vals[1:])): raise HistoryError("times must be finite and strictly increasing")
    diffs = np.diff(vals); cadence = float(median(diffs));
    if cadence <= 0 or relative_tolerance < 0: raise HistoryError("invalid cadence tolerance")
    left, right = seam
    if isinstance(left, int) and isinstance(right, int) and 0 <= left < len(vals) and right == left + 1: gap = vals[right] - vals[left]
    else: gap = float(right) - float(left)
    if abs(gap - cadence) / cadence > relative_tolerance: raise HistoryError(f"1499/1500 seam cadence mismatch: gap {gap} vs robust median {cadence}")
    return True


def validate_times(times: Sequence[float]) -> float:
    """Validate strict time ordering and return the robust median cadence."""
    vals = [float(x) for x in times]
    if len(vals) < 2 or any(not math.isfinite(x) for x in vals):
        raise HistoryError("times must contain at least two finite values")
    if any(b <= a for a, b in zip(vals, vals[1:])):
        raise HistoryError("particle times are not strictly increasing")
    return float(median(np.diff(vals)))


def classify_endpoint_completeness(endpoint_ids: Sequence[int], records: Mapping[int, Sequence[int]], *, injection_time: float | None = None, injection_times: Mapping[int, float] | None = None, output_times: Mapping[int, float] | None = None) -> Completeness:
    endpoints = {int(x) for x in endpoint_ids};
    if any(x <= 0 for x in endpoints): raise HistoryError("endpoint IDs must be positive")
    pre: set[tuple[int, int]] = set(); missing: set[tuple[int, int]] = set()
    for output, present_values in records.items():
        present = {int(x) for x in present_values}; time = float(output_times[output]) if output_times and output in output_times else float(output)
        for pid in endpoints - present:
            threshold = float(injection_times[pid]) if injection_times and pid in injection_times else injection_time
            if threshold is None:
                raise HistoryError("an injection_time or injection_times mapping is required")
            (pre if time < threshold else missing).add((int(output), pid))
    return Completeness(pre, missing)


def validate_presence_lifecycle(
    presence,
    output_times: Sequence[float],
    injection_times: Sequence[float],
    endpoint_ids: Sequence[int],
    output_indices: Sequence[int],
    *,
    particle_chunk_rows: int = 4096,
) -> dict[str, object]:
    """Validate a leading absence prefix followed by uninterrupted presence."""
    output_times = np.asarray(output_times, dtype=np.float64)
    injection_times = np.asarray(injection_times, dtype=np.float64)
    endpoint_ids = np.asarray(endpoint_ids, dtype=np.int64)
    output_indices = np.asarray(output_indices, dtype=np.int64)
    n, nt = presence.shape
    if particle_chunk_rows <= 0:
        raise HistoryError("particle_chunk_rows must be positive")
    if (
        output_times.shape != (nt,)
        or output_indices.shape != (nt,)
        or injection_times.shape != (n,)
        or endpoint_ids.shape != (n,)
    ):
        raise HistoryError("presence lifecycle arrays have incompatible shapes")
    if (
        np.any(~np.isfinite(output_times))
        or np.any(np.diff(output_times) <= 0)
        or np.any(~np.isfinite(injection_times))
    ):
        raise HistoryError("presence lifecycle times must be finite and ordered")

    cadence = float(median(np.diff(output_times)))
    injection32 = injection_times.astype(np.float32)
    next32 = np.nextafter(injection32, np.float32(np.inf))
    representation_tolerance = (
        np.abs(next32.astype(np.float64) - injection32.astype(np.float64)) / 2.0
    )
    float64_tolerance = (
        8.0
        * np.finfo(np.float64).eps
        * np.maximum(1.0, np.abs(injection_times))
    )
    tolerance = np.maximum(representation_tolerance, float64_tolerance)
    max_tolerance = float(np.max(tolerance, initial=0.0))
    if max_tolerance >= 0.01 * cadence:
        raise HistoryError("injection-boundary tolerance is too large relative to output cadence")

    pre_injection_absence_records = 0
    injection_boundary_roundoff_records = 0
    columns = np.arange(nt)
    for start in range(0, n, particle_chunk_rows):
        stop = min(start + particle_chunk_rows, n)
        present = np.asarray(presence[start:stop, :], dtype=bool)
        endpoint_missing = np.flatnonzero(~present[:, -1])
        if endpoint_missing.size:
            row = start + int(endpoint_missing[0])
            raise HistoryError(
                f"endpoint particle is absent: particle_id={int(endpoint_ids[row])}"
            )
        first_present = np.argmax(present, axis=1)
        gaps = (~present) & (columns[None, :] >= first_present[:, None])
        if np.any(gaps):
            row, column = np.argwhere(gaps)[0]
            raise HistoryError(
                "internal/post-injection particle gap: "
                f"output={int(output_indices[column])}, "
                f"particle_id={int(endpoint_ids[start + row])}"
            )

        thresholds = injection_times[start:stop]
        tolerances = tolerance[start:stop]
        first_times = output_times[first_present]
        early = first_times < thresholds - tolerances
        if np.any(early):
            row = int(np.flatnonzero(early)[0])
            column = int(first_present[row])
            raise HistoryError(
                "particle record precedes injection time: "
                f"output={int(output_indices[column])}, "
                f"particle_id={int(endpoint_ids[start + row])}"
            )

        has_previous = first_present > 0
        previous_columns = np.maximum(first_present - 1, 0)
        previous_times = output_times[previous_columns]
        missing_post = has_previous & (previous_times > thresholds + tolerances)
        if np.any(missing_post):
            row = int(np.flatnonzero(missing_post)[0])
            column = int(previous_columns[row])
            raise HistoryError(
                "missing post-injection particle record: "
                f"output={int(output_indices[column])}, "
                f"particle_id={int(endpoint_ids[start + row])}"
            )
        boundary_roundoff = (
            has_previous
            & (previous_times > thresholds)
            & (~missing_post)
        )
        injection_boundary_roundoff_records += int(np.count_nonzero(boundary_roundoff))
        pre_injection_absence_records += int(np.sum(first_present))

    return {
        "pre_injection_absence_records": pre_injection_absence_records,
        "injection_boundary_roundoff_records": injection_boundary_roundoff_records,
        "missing_post_injection_records": 0,
        "presence_contract": "single contiguous suffix per endpoint particle",
        "injection_boundary_tolerance": (
            "max(half float32 ULP at tinj, 8 float64 epsilon-scaled units)"
        ),
        "max_injection_boundary_tolerance": max_tolerance,
        "max_injection_boundary_tolerance_cadence_fraction": (
            max_tolerance / cadence
        ),
    }


# Descriptive aliases used by wrappers and downstream notebooks.
read_particle_output = parse_particle_file
parse_header = parse_particle_header
resolve_two_roots = resolve_roots


def audit_roots(
    initial_root: Path,
    guarded_root: Path,
    *,
    initial_range=range(0, 1500),
    guarded_range=range(1000, 5001),
    restart_anchor_index: int = 1000,
    relative_tolerance: float = 0.05,
) -> dict[str, object]:
    """Resolve roots and run the complete source continuity audit."""
    resolved = resolve_roots(
        initial_root,
        guarded_root,
        initial_range=initial_range,
        guarded_range=guarded_range,
        restart_anchor_index=restart_anchor_index,
    )
    headers = [parse_particle_header(path) for path in resolved.canonical_paths]
    schema_key = (
        headers[0].field_names,
        headers[0].field_dimensions,
        headers[0].endianity,
        headers[0].precision,
        headers[0].shock_thresholds,
    )
    if any(
        (
            header.field_names,
            header.field_dimensions,
            header.endianity,
            header.precision,
            header.shock_thresholds,
        )
        != schema_key
        for header in headers[1:]
    ):
        raise HistoryError("particle schema changes across outputs")
    times = [header.time for header in headers]
    cadence = validate_times(times)
    by_index = {header.output_index: i for i, header in enumerate(headers)}
    switch_pair = (restart_anchor_index - 1, restart_anchor_index)
    if switch_pair[0] not in by_index or switch_pair[1] not in by_index:
        raise HistoryError(f"{switch_pair[0]}/{switch_pair[1]} restart-switch outputs are required for audit")
    validate_seam(
        times,
        seam=(by_index[switch_pair[0]], by_index[switch_pair[1]]),
        relative_tolerance=relative_tolerance,
    )
    if 1499 not in by_index or 1500 not in by_index:
        raise HistoryError("1499/1500 seam outputs are required for audit")
    seam_positions = (by_index[1499], by_index[1500])
    validate_seam(times, seam=seam_positions, relative_tolerance=relative_tolerance)
    endpoint = parse_particle_file(resolved.canonical_paths[-1], fields=())
    return {
        "canonical_paths": [str(path) for path in resolved.canonical_paths],
        "overlap_indices": list(resolved.overlap_indices),
        "superseded_overlap_indices": list(resolved.superseded_overlap_indices),
        "n_outputs": len(headers),
        "endpoint_count": int(len(endpoint.ids)),
        "schema": {"field_names": list(headers[-1].field_names), "field_dimensions": list(headers[-1].field_dimensions), "endianity": headers[-1].endianity, "precision": headers[-1].precision},
        "source_sha256": {str(index): digest for index, digest in sorted(resolved.hashes.items())},
        "cadence": cadence,
        "restart_anchor": {
            "output": resolved.restart_anchor_index,
            "sha256": resolved.restart_anchor_sha256,
            "validated_exact": True,
        },
        "canonical_switch": {
            "initial_through": restart_anchor_index - 1,
            "guarded_from": restart_anchor_index,
            "validated": True,
        },
        "switch_seam": {
            "left_output": switch_pair[0],
            "right_output": switch_pair[1],
            "relative_tolerance": relative_tolerance,
            "validated": True,
        },
        "seam": {"left_output": 1499, "right_output": 1500, "relative_tolerance": relative_tolerance, "validated": True},
    }


def endpoint_ids_from_final(path: Path) -> list[int]:
    """Read only the final output IDs for dense cache-row selection."""
    return parse_particle_file(Path(path), fields=()).ids.tolist()


def build_history_cache(
    paths: Sequence[Path],
    cache_path: Path,
    *,
    endpoint_ids: Sequence[int],
    particle_chunk_rows: int = 4096,
    time_chunk: int = 32,
    write_batch_outputs: int | None = None,
    dtype: str = "float64",
    injection_time: float | None = None,
    shock_threshold: float = 5.0,
) -> dict[str, object]:
    paths = tuple(Path(p) for p in paths); endpoint_ids = np.asarray(endpoint_ids, dtype=np.int64)
    if not paths: raise HistoryError("at least one particle output is required")
    if len(endpoint_ids) == 0 or len(np.unique(endpoint_ids)) != len(endpoint_ids) or np.any(endpoint_ids <= 0): raise HistoryError("endpoint IDs must be unique and positive")
    if dtype not in {"float32", "float64"}: raise HistoryError("dtype must be float32 or float64")
    # PLUTO stores Cartesian coordinates and velocities as six scalar fields.
    # The cache presents the stable endpoint-only position/velocity vectors.
    first_header = parse_particle_header(paths[0])
    first_names = set(first_header.field_names)
    if first_header.shock_thresholds is None:
        raise HistoryError("particle schema does not declare shk_thresh")
    matches = np.flatnonzero(np.isclose(first_header.shock_thresholds, shock_threshold, rtol=0, atol=1e-12))
    if len(matches) != 1:
        raise HistoryError(f"expected exactly one last-shock component for threshold {shock_threshold:g}")
    shock_component = int(matches[0])
    endpoint_fields = ("position", "velocity") if {"position", "velocity"}.issubset(first_names) else ("x1", "x2", "x3", "vx1", "vx2", "vx3")
    required = ("pressure", "density", "tracer", "last_shock_time", "tinj")
    selected = required
    missing = [name for name in required if name not in first_names]
    if missing: raise HistoryError(f"particle schema missing required fields: {', '.join(missing)}")
    n, m = len(endpoint_ids), len(paths); cache_path = Path(cache_path); cache_path.parent.mkdir(parents=True, exist_ok=True)
    write_batch_outputs = time_chunk if write_batch_outputs is None else write_batch_outputs
    if particle_chunk_rows <= 0 or time_chunk <= 0 or write_batch_outputs <= 0:
        raise HistoryError("particle_chunk_rows, time_chunk, and write_batch_outputs must be positive")
    cache_chunks = (min(particle_chunk_rows, n), min(time_chunk, m))
    with __import__("h5py").File(cache_path, "a") as h5:
        if "endpoint_ids" not in h5:
            h5.create_dataset("endpoint_ids", data=endpoint_ids, dtype="i8")
            h5.create_dataset("times", shape=(m,), dtype="f8")
            h5.create_dataset("output_indices", shape=(m,), dtype="i8")
            for name in selected[:4]: h5.create_dataset(name, shape=(n, m), dtype=dtype, chunks=cache_chunks, fillvalue=np.nan)
            h5.create_dataset("presence", shape=(n, m), dtype="bool", chunks=cache_chunks, fillvalue=False)
            for name, dim in (("position", 3), ("velocity", 3)): h5.create_dataset(name, shape=(n, dim), dtype=dtype, fillvalue=np.nan)
            h5.create_dataset("tinj", shape=(n,), dtype=dtype, fillvalue=np.nan)
            h5.attrs["next_output"] = 0
            h5.attrs["dtype"] = dtype
            h5.attrs["shock_threshold"] = shock_threshold
            h5.attrs["shock_component"] = shock_component
        if not np.array_equal(h5["endpoint_ids"][:], endpoint_ids): raise HistoryError("cache endpoint IDs mismatch")
        if not np.isclose(float(h5.attrs["shock_threshold"]), shock_threshold, rtol=0, atol=1e-12):
            raise HistoryError("cache shock-threshold contract mismatch")
        if int(h5.attrs["shock_component"]) != shock_component:
            raise HistoryError("cache shock-component contract mismatch")
        next_output = int(h5.attrs.get("next_output", 0))
        if next_output > m: raise HistoryError("cache checkpoint exceeds requested outputs")
        pending_start = h5.attrs.get("pending_batch_start")
        pending_stop = h5.attrs.get("pending_batch_stop")
        if (pending_start is None) != (pending_stop is None):
            raise HistoryError("cache has an incomplete pending-batch checkpoint")
        if pending_start is not None:
            pending_start, pending_stop = int(pending_start), int(pending_stop)
            if pending_stop <= next_output:
                del h5.attrs["pending_batch_start"]
                del h5.attrs["pending_batch_stop"]
                h5.flush()
            elif pending_start != next_output or not (pending_start < pending_stop <= m):
                raise HistoryError("cache pending-batch checkpoint is inconsistent")
        if "batched_writer_start_output" not in h5.attrs:
            h5.attrs["batched_writer_start_output"] = next_output
        batched_start = int(h5.attrs["batched_writer_start_output"])
        helper_sha256 = _sha256(Path(__file__))
        h5.attrs["batched_writer_sha256"] = helper_sha256
        legacy_helper_sha256 = os.environ.get("GOAL049_LEGACY_HISTORY_HELPER_SHA256")
        if batched_start > 0 and legacy_helper_sha256 is not None:
            if re.fullmatch(r"[0-9a-f]{64}", legacy_helper_sha256) is None:
                raise HistoryError("legacy history-helper SHA-256 is malformed")
            h5.attrs["legacy_writer_sha256"] = legacy_helper_sha256
        h5.attrs["cache_writer_current"] = "sequential_chunk_batched_v2"
        h5.flush()
        # A sorted lookup allows O(N log N) matching per output instead of an
        # O(N_endpoint * N_particle) flatnonzero loop.
        sorted_ids_order = np.argsort(endpoint_ids)
        sorted_ids = endpoint_ids[sorted_ids_order]
        while next_output < m:
            batch_stop = min(m, ((next_output // write_batch_outputs) + 1) * write_batch_outputs)
            batch_width = batch_stop - next_output
            field_buffers = {
                name: np.full((n, batch_width), np.nan, dtype=dtype)
                for name in selected[:4]
            }
            presence_buffer = np.zeros((n, batch_width), dtype=bool)
            time_buffer = np.empty(batch_width, dtype=np.float64)
            output_buffer = np.empty(batch_width, dtype=np.int64)
            final_position = final_velocity = final_tinj = None
            prior_time = float(h5["times"][next_output - 1]) if next_output else None

            h5.attrs["pending_batch_start"] = next_output
            h5.attrs["pending_batch_stop"] = batch_stop
            h5.flush()
            for offset, i in enumerate(range(next_output, batch_stop)):
                header = parse_particle_header(paths[i])
                names = set(header.field_names)
                if header.shock_thresholds != first_header.shock_thresholds:
                    raise HistoryError(f"{paths[i]}: shk_thresh changed across outputs")
                fields = required + endpoint_fields
                if not set(fields).issubset(names):
                    raise HistoryError(f"{paths[i]}: schema changed or required fields missing")
                parsed = parse_particle_file(
                    paths[i],
                    fields=fields,
                    vector_components={"last_shock_time": shock_component},
                )
                if prior_time is not None and float(parsed.header.time) <= prior_time:
                    raise HistoryError("particle times are not strictly increasing")
                prior_time = float(parsed.header.time)
                time_buffer[offset] = parsed.header.time
                output_buffer[offset] = parsed.header.output_index
                positions = np.searchsorted(sorted_ids, parsed.ids)
                matches = (
                    (positions < len(sorted_ids))
                    & (sorted_ids[np.minimum(positions, len(sorted_ids) - 1)] == parsed.ids)
                )
                endpoint_rows = sorted_ids_order[positions[matches]]
                particle_rows = np.flatnonzero(matches)
                row_order = np.argsort(endpoint_rows)
                endpoint_rows = endpoint_rows[row_order]
                particle_rows = particle_rows[row_order]
                for name in selected[:4]:
                    field_buffers[name][endpoint_rows, offset] = parsed.fields[name][particle_rows]
                presence_buffer[endpoint_rows, offset] = True
                if i == m - 1:
                    if endpoint_fields == ("position", "velocity"):
                        position_values = parsed.fields["position"][particle_rows]
                        velocity_values = parsed.fields["velocity"][particle_rows]
                    else:
                        position_values = np.column_stack(
                            [parsed.fields[field][particle_rows] for field in ("x1", "x2", "x3")]
                        )
                        velocity_values = np.column_stack(
                            [parsed.fields[field][particle_rows] for field in ("vx1", "vx2", "vx3")]
                        )
                    final_position = np.full((n, 3), np.nan, dtype=dtype)
                    final_velocity = np.full((n, 3), np.nan, dtype=dtype)
                    final_tinj = np.full(n, np.nan, dtype=dtype)
                    final_position[endpoint_rows] = position_values
                    final_velocity[endpoint_rows] = velocity_values
                    final_tinj[endpoint_rows] = parsed.fields["tinj"][particle_rows]

            column_slice = slice(next_output, batch_stop)
            h5["times"][column_slice] = time_buffer
            h5["output_indices"][column_slice] = output_buffer
            for name in selected[:4]:
                h5[name][:, column_slice] = field_buffers[name]
            h5["presence"][:, column_slice] = presence_buffer
            if final_position is not None:
                h5["position"][:] = final_position
                h5["velocity"][:] = final_velocity
                h5["tinj"][:] = final_tinj
            h5.flush()
            h5.attrs["next_output"] = batch_stop
            h5.flush()
            del h5.attrs["pending_batch_start"]
            del h5.attrs["pending_batch_stop"]
            h5.flush()
            next_output = batch_stop
        tinj = h5["tinj"][:]
        thresholds = (
            np.full(n, float(injection_time), dtype=np.float64)
            if injection_time is not None
            else tinj
        )
        lifecycle = validate_presence_lifecycle(
            h5["presence"],
            h5["times"][:],
            thresholds,
            endpoint_ids,
            h5["output_indices"][:],
            particle_chunk_rows=particle_chunk_rows,
        )
        writer_segments = []
        if batched_start > 0:
            writer_segments.append(
                {
                    "start_output_inclusive": 0,
                    "stop_output_exclusive": batched_start,
                    "writer": "serial_column_v1",
                    "helper_sha256": str(h5.attrs.get("legacy_writer_sha256", "not_recorded")),
                }
            )
        if next_output > batched_start:
            writer_segments.append(
                {
                    "start_output_inclusive": batched_start,
                    "stop_output_exclusive": next_output,
                    "writer": "sequential_chunk_batched_v2",
                    "helper_sha256": helper_sha256,
                }
            )
        return {
            "cache": str(cache_path),
            "outputs": m,
            "processed_outputs": int(h5.attrs["next_output"]),
            "endpoint_count": n,
            "dtype": dtype,
            "chunks": list(cache_chunks),
            "write_batch_outputs": write_batch_outputs,
            "batched_writer_start_output": batched_start,
            "writer_segments": writer_segments,
            "checkpoint_commit_order": "pending marker; data flush; next_output flush; pending marker removal",
            "shock_threshold": shock_threshold,
            "shock_component": shock_component,
            **lifecycle,
        }


def _cli() -> int:
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest="mode", required=True)
    audit = sub.add_parser("audit"); audit.add_argument("--initial-root", type=Path, required=True); audit.add_argument("--guarded-root", type=Path, required=True); audit.add_argument("--json-output", type=Path); audit.add_argument("--csv-output", type=Path); audit.add_argument("--relative-tolerance", type=float, default=0.05)
    extract = sub.add_parser("extract"); extract.add_argument("--paths-json", type=Path, required=True); extract.add_argument("--cache", type=Path, required=True); extract.add_argument("--endpoint-id", type=int, action="append", default=[]); extract.add_argument("--ids-file", type=Path); extract.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "audit":
            report = audit_roots(args.initial_root, args.guarded_root, relative_tolerance=args.relative_tolerance)
            csv_path = args.csv_output
            if csv_path is None: csv_path = args.json_output.with_suffix(".csv") if args.json_output is not None else Path("audit_manifest.csv")
            if csv_path is not None:
                csv_path.parent.mkdir(parents=True, exist_ok=True)
                with csv_path.open("w", newline="") as handle:
                    writer = csv.writer(handle); writer.writerow(["metric", "value"])
                    for key in ("n_outputs", "endpoint_count", "cadence"):
                        writer.writerow([key, report[key]])
                    writer.writerow(["seam_validated", report["seam"]["validated"]])
        else:
            paths = [Path(p) for p in json.loads(args.paths_json.read_text())]
            ids = list(args.endpoint_id)
            if args.ids_file is not None:
                ids.extend(int(line.split(",")[0]) for line in args.ids_file.read_text().splitlines() if line.strip() and not line.lower().startswith("id"))
            if not ids: ids = endpoint_ids_from_final(paths[-1])
            report = build_history_cache(paths, args.cache, endpoint_ids=ids)
        text = json.dumps(report, indent=2, sort_keys=True); (args.json_output.write_text(text + "\n") if args.json_output else print(text))
    except (HistoryError, OSError, ValueError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__": raise SystemExit(_cli())
