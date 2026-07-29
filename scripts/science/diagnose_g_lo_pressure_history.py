#!/usr/bin/env python3
"""Read-only, bounded-memory pressure-history diagnostics for Goal 049.

The cache is treated as immutable.  Only compact JSON/CSV reports are written
to a new output directory; source particle files are streamed for a bounded
representative cross-check when roots are supplied.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Iterable

import h5py
import numpy as np

from scripts.science.g_lo_particle_history import HistoryError, _layout, parse_particle_header


REQUIRED_DATASETS = ("endpoint_ids", "times", "output_indices", "pressure", "density", "tracer", "presence", "tinj")


def _sha256_file(path: Path, *, max_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = max_bytes
    with path.open("rb") as handle:
        while True:
            size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            if size <= 0:
                break
            block = handle.read(size)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    return digest.hexdigest()


def _identity(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {"path": str(path), "bytes": stat.st_size, "mtime_ns": stat.st_mtime_ns, "sha256_head_1MiB": _sha256_file(path, max_bytes=1024 * 1024)}


def _source_path(root: Path, output_index: int) -> Path | None:
    matches = sorted(root.glob(f"particles.{int(output_index):04d}.*"))
    matches = [path for path in matches if path.is_file() and not path.is_symlink() and path.suffix in {".dbl", ".flt"}]
    return matches[0] if len(matches) == 1 else None


def _canonical_source_path(initial_root: Path, guarded_root: Path, output_index: int) -> tuple[Path | None, str]:
    """Select the canonical raw lineage: initial <1000, guarded >=1000."""
    if int(output_index) < 1000:
        return _source_path(initial_root, output_index), "initial"
    return _source_path(guarded_root, output_index), "guarded"


def _stream_source_records(path: Path, requested: set[int], *, chunk_rows: int) -> dict[int, dict[str, float]]:
    """Read only requested IDs from one particle file, bounded by chunk_rows."""
    header = parse_particle_header(path)
    layout = _layout(header)
    required = ("id", "pressure", "density", "tracer")
    if any(name not in layout for name in required):
        return {}
    dtype = np.dtype(("<" if header.endianity == "little" else ">") + ("f4" if header.precision == "single" else "f8"))
    offsets = {name: layout[name][0] for name in required}
    found: dict[int, dict[str, float]] = {}
    with path.open("rb") as handle:
        handle.seek(header.header_offset)
        for start in range(0, header.nparticles, chunk_rows):
            count = min(chunk_rows, header.nparticles - start)
            raw = handle.read(count * header.payload_width)
            if len(raw) != count * header.payload_width:
                raise HistoryError(f"{path}: truncated payload during diagnostic cross-check")
            rows = np.frombuffer(raw, dtype=dtype).reshape(count, header.nelem)
            ids = rows[:, offsets["id"]].astype(np.int64)
            for pos in np.flatnonzero(np.isin(ids, list(requested))):
                pid = int(ids[pos])
                found[pid] = {
                    "pressure": float(rows[pos, offsets["pressure"]]),
                    "density": float(rows[pos, offsets["density"]]),
                    "tracer": float(rows[pos, offsets["tracer"]]),
                    "source_time": float(header.time),
                }
            if len(found) == len(requested):
                break
    return found


def _exact_value_match(cache_value: float, source_value: float) -> bool:
    """Compare scalar cache/source values while treating paired NaNs as equal."""
    if math.isnan(cache_value) and math.isnan(source_value):
        return True
    return cache_value == source_value


def diagnose_pressure_history(
    cache: Path,
    output_dir: Path,
    *,
    source_roots: Iterable[Path] = (),
    initial_source_root: Path | None = None,
    guarded_source_root: Path | None = None,
    row_chunk: int = 4096,
    representative_limit: int = 100,
    source_crosscheck_limit: int = 32,
) -> dict[str, object]:
    cache = Path(cache).resolve()
    output_dir = Path(output_dir).resolve()
    if not cache.is_file() or cache.is_symlink():
        raise HistoryError(f"cache must be a regular file: {cache}")
    if row_chunk <= 0 or representative_limit <= 0 or source_crosscheck_limit < 0:
        raise HistoryError("diagnostic limits must be positive, except source_crosscheck_limit may be zero")
    if output_dir.exists():
        if output_dir.is_symlink() or not output_dir.is_dir() or any(output_dir.iterdir()):
            raise HistoryError(f"refusing to overwrite non-empty output directory: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=False)
    per_output_rows: list[dict[str, object]] = []
    bad_records: list[dict[str, object]] = []
    source_requests: dict[tuple[int, int], dict[str, object]] = {}
    exceptional_rows: list[dict[str, object]] = []
    exceptional_source_requests: dict[tuple[int, int], dict[str, object]] = {}
    lifecycle_violations = 0
    counts = {key: 0 for key in ("finite_positive", "zero", "negative", "nonfinite")}
    first_present_bad = 0
    later_bad = 0
    affected_rows: set[int] = set()
    affected_outputs: set[int] = set()
    min_pressure = math.inf
    min_positive = math.inf
    per_output: list[dict[str, object]] | None = None
    pattern_counts = {"leading_zero_only_prefix_rows": 0, "leading_zero_only_prefix_records": 0,
                      "internal_nonpositive_after_positive_rows": 0, "internal_nonpositive_after_positive_records": 0,
                      "no_positive_record_rows": 0, "no_positive_record_records": 0,
                      "nonpositive_endpoint_rows": 0, "nonpositive_endpoint_records": 0}

    with h5py.File(cache, "r") as h5:
        missing = [name for name in REQUIRED_DATASETS if name not in h5]
        if missing:
            raise HistoryError(f"cache missing datasets: {', '.join(missing)}")
        ids = np.asarray(h5["endpoint_ids"][:], dtype=np.int64)
        times = np.asarray(h5["times"][:], dtype=np.float64)
        output_indices = np.asarray(h5["output_indices"][:], dtype=np.int64)
        tinj = np.asarray(h5["tinj"][:], dtype=np.float64)
        pressure = h5["pressure"]
        presence = h5["presence"]
        density = h5["density"]
        tracer = h5["tracer"]
        n, nt = pressure.shape
        if presence.shape != (n, nt) or density.shape != (n, nt) or tracer.shape != (n, nt):
            raise HistoryError("cache field shapes are inconsistent")
        if ids.shape != (n,) or times.shape != (nt,) or output_indices.shape != (nt,) or tinj.shape != (n,):
            raise HistoryError("cache metadata shapes are inconsistent")
        if np.any(~np.isfinite(times)) or np.any(np.diff(times) <= 0):
            raise HistoryError("cache times must be finite and strictly increasing")
        per_output = [
            {"output_index": int(output_indices[col]), "output_time": float(times[col]), "present_count": 0,
             "finite_positive_count": 0, "zero_count": 0, "negative_count": 0, "nonfinite_count": 0}
            for col in range(nt)
        ]
        for start in range(0, n, row_chunk):
            stop = min(start + row_chunk, n)
            present = np.asarray(presence[start:stop, :], dtype=bool)
            values = np.asarray(pressure[start:stop, :], dtype=np.float64)
            rows_in_chunk = stop - start
            absent_all = ~np.any(present, axis=1)
            lifecycle_violations += int(np.count_nonzero(absent_all))
            safe_first = np.argmax(present, axis=1)
            columns = np.arange(nt)[None, :]
            gaps = (~present) & (columns >= safe_first[:, None]) & (~absent_all[:, None])
            lifecycle_violations += int(np.count_nonzero(np.any(gaps, axis=1)))
            finite = np.isfinite(values)
            finite_positive = finite & (values > 0)
            zero = present & finite & (values == 0)
            negative = present & finite & (values < 0)
            nonfinite = present & ~finite
            bad = zero | negative | nonfinite
            positive = present & finite_positive
            counts["finite_positive"] += int(np.count_nonzero(positive))
            counts["zero"] += int(np.count_nonzero(zero))
            counts["negative"] += int(np.count_nonzero(negative))
            counts["nonfinite"] += int(np.count_nonzero(nonfinite))
            finite_present = values[present & finite]
            if finite_present.size:
                min_pressure = min(min_pressure, float(np.min(finite_present)))
            positive_values = values[positive]
            if positive_values.size:
                min_positive = min(min_positive, float(np.min(positive_values)))
            affected_rows.update((start + np.flatnonzero(np.any(bad, axis=1))).tolist())
            affected_outputs.update(output_indices[np.flatnonzero(np.any(bad, axis=0))].tolist())
            first_bad = bad[np.arange(rows_in_chunk), safe_first]
            first_present_bad += int(np.count_nonzero(first_bad & ~absent_all))
            later_bad += int(np.count_nonzero(bad) - np.count_nonzero(first_bad & ~absent_all))
            has_positive = np.any(positive, axis=1)
            first_positive = np.argmax(positive, axis=1)
            leading_mask = present & (columns < first_positive[:, None]) & has_positive[:, None]
            leading_zero_only = has_positive & np.any(leading_mask, axis=1) & np.all((~leading_mask) | zero, axis=1)
            internal_mask = bad & (columns > first_positive[:, None]) & has_positive[:, None]
            internal_rows = np.any(internal_mask, axis=1)
            no_positive = (~has_positive) & (~absent_all)
            last_present = nt - 1 - np.argmax(present[:, ::-1], axis=1)
            endpoint_bad = bad[np.arange(rows_in_chunk), last_present] & ~absent_all
            # Leading zero-only prefixes followed by a valid positive history
            # are eligible for the separately reviewed trim repair and stay
            # out of the escalation/source-cross-check table.  Every other
            # pressure anomaly is retained for explicit review.
            exceptional = (
                no_positive
                | endpoint_bad
                | internal_rows
                | np.any(negative | nonfinite, axis=1)
            ) & ~absent_all
            pattern_counts["leading_zero_only_prefix_rows"] += int(np.count_nonzero(leading_zero_only))
            pattern_counts["leading_zero_only_prefix_records"] += int(np.count_nonzero(leading_mask & zero & leading_zero_only[:, None]))
            pattern_counts["internal_nonpositive_after_positive_rows"] += int(np.count_nonzero(internal_rows))
            pattern_counts["internal_nonpositive_after_positive_records"] += int(np.count_nonzero(internal_mask))
            pattern_counts["no_positive_record_rows"] += int(np.count_nonzero(no_positive))
            pattern_counts["no_positive_record_records"] += int(np.count_nonzero(bad & no_positive[:, None]))
            pattern_counts["nonpositive_endpoint_rows"] += int(np.count_nonzero(endpoint_bad))
            pattern_counts["nonpositive_endpoint_records"] += int(np.count_nonzero(endpoint_bad))
            for local in np.flatnonzero(exceptional):
                row = start + int(local)
                first_col = int(safe_first[local])
                last_col = int(last_present[local])
                row_present = present[local]
                row_values = values[local, row_present]
                row_density = np.asarray(density[row, :], dtype=np.float64)[row_present]
                row_tracer = np.asarray(tracer[row, :], dtype=np.float64)[row_present]

                def finite_min_max(array: np.ndarray) -> tuple[float, float]:
                    finite_values = array[np.isfinite(array)]
                    if finite_values.size == 0:
                        return math.nan, math.nan
                    return float(np.min(finite_values)), float(np.max(finite_values))

                pressure_min, pressure_max = finite_min_max(row_values)
                density_min, density_max = finite_min_max(row_density)
                tracer_min, tracer_max = finite_min_max(row_tracer)
                exceptional_record = {
                    "endpoint_id": int(ids[row]),
                    "first_present_column": first_col,
                    "first_present_output_index": int(output_indices[first_col]),
                    "first_present_output_time": float(times[first_col]),
                    "last_present_column": last_col,
                    "last_present_output_index": int(output_indices[last_col]),
                    "last_present_output_time": float(times[last_col]),
                    "tinj": float(tinj[row]),
                    "present_count": int(np.count_nonzero(row_present)),
                    "bad_count": int(np.count_nonzero(bad[local, :])),
                    "finite_positive_count": int(np.count_nonzero(positive[local, :])),
                    "zero_count": int(np.count_nonzero(zero[local, :])),
                    "negative_count": int(np.count_nonzero(negative[local, :])),
                    "nonfinite_count": int(np.count_nonzero(nonfinite[local, :])),
                    "pressure_min": pressure_min,
                    "pressure_max": pressure_max,
                    "density_min": density_min,
                    "density_max": density_max,
                    "tracer_min": tracer_min,
                    "tracer_max": tracer_max,
                    "first_pressure": float(values[local, first_col]),
                    "last_pressure": float(values[local, last_col]),
                    "first_density": float(density[row, first_col]),
                    "last_density": float(density[row, last_col]),
                    "first_tracer": float(tracer[row, first_col]),
                    "last_tracer": float(tracer[row, last_col]),
                    "endpoint_bad": bool(endpoint_bad[local]),
                }
                exceptional_rows.append(exceptional_record)
                for col in (first_col, last_col):
                    key = (int(ids[row]), int(output_indices[col]))
                    exceptional_source_requests.setdefault(
                        key,
                        {
                            "endpoint_id": int(ids[row]),
                            "output_index": int(output_indices[col]),
                            "output_time": float(times[col]),
                            "pressure": float(values[local, col]),
                            "density": float(density[row, col]),
                            "tracer": float(tracer[row, col]),
                        },
                    )
            for col in range(nt):
                col_present = present[:, col]
                per_output[col]["present_count"] += int(np.count_nonzero(col_present))
                per_output[col]["finite_positive_count"] += int(np.count_nonzero(positive[:, col]))
                per_output[col]["zero_count"] += int(np.count_nonzero(zero[:, col]))
                per_output[col]["negative_count"] += int(np.count_nonzero(negative[:, col]))
                per_output[col]["nonfinite_count"] += int(np.count_nonzero(nonfinite[:, col]))
            remaining = representative_limit - len(bad_records)
            bad_flat = np.flatnonzero(bad.ravel())[:remaining]
            bad_positions = np.column_stack(np.unravel_index(bad_flat, bad.shape))
            for local, col in bad_positions:
                row = start + int(local)
                value = float(values[local, col])
                category = "nonfinite" if nonfinite[local, col] else ("zero" if zero[local, col] else "negative")
                first_col = int(safe_first[local])
                if has_positive[local] and col < first_positive[local]:
                    position = "leading_prefix"
                elif has_positive[local] and col > first_positive[local]:
                    position = "internal_after_positive"
                else:
                    position = "first_present" if col == first_col else "later_nonpositive"
                next_pressure = float(values[local, col + 1]) if col + 1 < nt and present[local, col + 1] else math.nan
                record = {
                    "endpoint_id": int(ids[row]), "output_index": int(output_indices[col]), "output_time": float(times[col]),
                    "first_present_column": first_col, "first_present_output_index": int(output_indices[first_col]),
                    "first_present_output_time": float(times[first_col]), "tinj": float(tinj[row]),
                    "pressure": value, "density": float(density[row, col]), "tracer": float(tracer[row, col]),
                    "class": category, "position": position, "next_pressure": next_pressure,
                }
                bad_records.append(record)
                source_requests.setdefault((int(ids[row]), int(output_indices[col])), record.copy())

        source_results: dict[tuple[int, int], dict[str, object]] = {}
        roots = [Path(root).resolve() for root in source_roots]
        if initial_source_root is not None or guarded_source_root is not None:
            if initial_source_root is None or guarded_source_root is None:
                raise HistoryError("both initial_source_root and guarded_source_root are required")
            roots = [Path(initial_source_root).resolve(), Path(guarded_source_root).resolve()]
        if roots and len(roots) != 2:
            raise HistoryError("source_roots must contain initial and guarded roots")
        selected_requests = list(source_requests.items())[:source_crosscheck_limit]
        exceptional_selected_requests = list(exceptional_source_requests.items())
        request_by_key = dict(source_requests)
        request_by_key.update(exceptional_source_requests)
        all_selected_requests: list[tuple[tuple[int, int], dict[str, object]]] = []
        seen_request_keys: set[tuple[int, int]] = set()
        for key, request in selected_requests + exceptional_selected_requests:
            if key not in seen_request_keys:
                seen_request_keys.add(key)
                all_selected_requests.append((key, request))
        grouped: dict[Path, set[int]] = {}
        key_selection: dict[tuple[int, int], tuple[Path | None, str]] = {}
        for key, request in all_selected_requests:
            pid, output = key
            source_path, segment = (None, "unavailable") if not roots else _canonical_source_path(roots[0], roots[1], output)
            key_selection[key] = (source_path, segment)
            if source_path is not None:
                grouped.setdefault(source_path, set()).add(pid)
        for source_path, requested_ids in grouped.items():
            found = _stream_source_records(source_path, requested_ids, chunk_rows=row_chunk)
            for key, (selected_path, segment) in key_selection.items():
                if selected_path != source_path:
                    continue
                pid, _output = key
                if pid not in found:
                    source_results[key] = {"source_status": "id_not_found", "source_segment": segment, "source_path": str(source_path), "source_identity": _identity(source_path)}
                else:
                    matched = found[pid]
                    cache_pressure = float(request_by_key[key]["pressure"])
                    cache_density = float(request_by_key[key]["density"])
                    cache_tracer = float(request_by_key[key]["tracer"])
                    source_pressure = float(matched["pressure"])
                    source_density = float(matched["density"])
                    source_tracer = float(matched["tracer"])
                    pressure_match = _exact_value_match(cache_pressure, source_pressure)
                    density_match = _exact_value_match(cache_density, source_density)
                    tracer_match = _exact_value_match(cache_tracer, source_tracer)
                    source_results[key] = {
                        "source_status": "matched", "source_segment": segment, "source_path": str(source_path), "source_identity": _identity(source_path),
                        "source_time": matched["source_time"], "source_pressure": source_pressure,
                        "source_density": source_density, "source_tracer": source_tracer,
                        "cache_source_pressure_match": pressure_match,
                        "cache_source_density_match": density_match,
                        "cache_source_tracer_match": tracer_match,
                        "cache_source_all_match": pressure_match and density_match and tracer_match,
                    }
        for key, request in all_selected_requests:
            if key in source_results:
                continue
            _selected_path, segment = key_selection.get(key, (None, "unavailable"))
            source_results[key] = {"source_status": "not_found", "source_segment": segment}
        for row in bad_records:
            key = (int(row["endpoint_id"]), int(row["output_index"]))
            row.update(source_results.get(key, {"source_status": "not_crosschecked"}))

        for row in exceptional_rows:
            for label, output_index_key in (("first", "first_present_output_index"), ("last", "last_present_output_index")):
                key = (int(row["endpoint_id"]), int(row[output_index_key]))
                result = source_results.get(key, {"source_status": "not_crosschecked"})
                for field in ("source_status", "source_segment", "source_path", "source_time", "source_pressure", "source_density", "source_tracer", "cache_source_pressure_match", "cache_source_density_match", "cache_source_tracer_match", "cache_source_all_match"):
                    row[f"{label}_{field}"] = result.get(field, "")

        source_identities = []
        seen_source_paths: set[str] = set()
        for result in source_results.values():
            path = result.get("source_path")
            if path and path not in seen_source_paths:
                seen_source_paths.add(str(path))
                source_identities.append(result.get("source_identity", {"path": path}))
        source_status_counts = {status: sum(1 for result in source_results.values() if result.get("source_status") == status) for status in ("matched", "not_found", "id_not_found")}

        summary = {
            "status": "diagnostic_complete",
            "cache_identity": _identity(cache), "cache_shape": [n, nt],
            "cache_attrs": {str(k): (v.item() if isinstance(v, np.generic) else v) for k, v in h5.attrs.items()},
            "source_roots": [{"path": str(root), "exists": root.is_dir()} for root in roots],
            "source_crosscheck": {"requested": len(source_results), "status_counts": source_status_counts, "file_identities": source_identities},
            "row_chunk": row_chunk, "representative_limit": representative_limit, "source_crosscheck_limit": source_crosscheck_limit,
            "counts_over_present_suffix": counts, "total_present_records": int(sum(counts.values())),
            "affected_row_count": len(affected_rows), "affected_output_count": len(affected_outputs),
            "pattern_counts": pattern_counts,
            "first_present_bad_records": first_present_bad, "later_bad_records": later_bad,
            "lifecycle_violation_rows": lifecycle_violations,
            "min_finite_pressure": None if min_pressure == math.inf else min_pressure,
            "min_positive_pressure": None if min_positive == math.inf else min_positive,
            "representative_bad_record_count": len(bad_records),
            "exceptional_row_count": len(exceptional_rows),
            "exceptional_source_crosscheck_request_count": len(exceptional_source_requests),
        }

    per_output_rows = per_output or []
    with (output_dir / "pressure_nonpositive_by_output.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["output_index", "output_time", "present_count", "finite_positive_count", "zero_count", "negative_count", "nonfinite_count"])
        writer.writeheader(); writer.writerows(per_output_rows)
    fields = ["endpoint_id", "output_index", "output_time", "first_present_column", "first_present_output_index", "first_present_output_time", "tinj", "pressure", "density", "tracer", "class", "position", "next_pressure", "source_status", "source_segment", "source_path", "source_time", "source_pressure", "source_density", "source_tracer", "cache_source_pressure_match"]
    with (output_dir / "representative_bad_records.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore"); writer.writeheader(); writer.writerows(bad_records)
    exceptional_fields = [
        "endpoint_id", "first_present_column", "first_present_output_index", "first_present_output_time",
        "last_present_column", "last_present_output_index", "last_present_output_time", "tinj",
        "present_count", "bad_count", "finite_positive_count", "zero_count", "negative_count", "nonfinite_count",
        "pressure_min", "pressure_max", "density_min", "density_max", "tracer_min", "tracer_max",
        "first_pressure", "last_pressure", "first_density", "last_density", "first_tracer", "last_tracer", "endpoint_bad",
    ]
    for label in ("first", "last"):
        exceptional_fields.extend(
            f"{label}_{field}" for field in (
                "source_status", "source_segment", "source_path", "source_time", "source_pressure", "source_density",
                "source_tracer", "cache_source_pressure_match", "cache_source_density_match", "cache_source_tracer_match",
                "cache_source_all_match",
            )
        )
    with (output_dir / "exceptional_pressure_rows.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=exceptional_fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(exceptional_rows)
    (output_dir / "pressure_history_diagnostic.json").write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, action="append", default=[])
    parser.add_argument("--initial-source-root", type=Path)
    parser.add_argument("--guarded-source-root", type=Path)
    parser.add_argument("--row-chunk", type=int, default=4096)
    parser.add_argument("--representative-limit", type=int, default=100)
    parser.add_argument("--source-crosscheck-limit", type=int, default=32)
    args = parser.parse_args()
    summary = diagnose_pressure_history(args.cache, args.output_dir, source_roots=args.source_root, initial_source_root=args.initial_source_root, guarded_source_root=args.guarded_source_root, row_chunk=args.row_chunk, representative_limit=args.representative_limit, source_crosscheck_limit=args.source_crosscheck_limit)
    print(f"status={summary['status']}")
    print(f"affected_rows={summary['affected_row_count']} affected_outputs={summary['affected_output_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
