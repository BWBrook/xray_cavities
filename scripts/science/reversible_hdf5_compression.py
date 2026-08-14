#!/usr/bin/env python3
"""Create and validate a reversible, no-overwrite HDF5 copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import time
from typing import Any, Iterator

import h5py
import hdf5plugin
import numpy as np


TARGET_CHUNK_BYTES = 8 * 1024 * 1024


class CompressionError(RuntimeError):
    """Raised when reversible compression or validation fails."""


def choose_chunk_shape(
    shape: tuple[int, ...], dtype: np.dtype[Any], *, target_bytes: int = TARGET_CHUNK_BYTES
) -> tuple[int, ...] | None:
    """Choose a bounded chunk shape without changing dimensionality."""
    if not shape:
        return None
    chunk = [max(1, int(value)) for value in shape]
    itemsize = max(1, int(np.dtype(dtype).itemsize))
    while math.prod(chunk) * itemsize > target_bytes:
        axis = max(range(len(chunk)), key=chunk.__getitem__)
        chunk[axis] = max(1, (chunk[axis] + 1) // 2)
    return tuple(chunk)


def _copy_attrs(source: h5py.AttributeManager, target: h5py.AttributeManager) -> None:
    for name, value in source.items():
        target[name] = value


def _dataset_kind(path: str, dataset: h5py.Dataset) -> str:
    if dataset.shape == () or not np.issubdtype(dataset.dtype, np.number):
        return "uncompressed"
    parts = Path(path).parts
    is_coordinate = any(part == "coords" or part.endswith("_coords") for part in parts)
    if is_coordinate or not np.issubdtype(dataset.dtype, np.floating):
        return "gzip_shuffle"
    return "zfp_reversible"


def _create_dataset(target: h5py.File, path: str, source: h5py.Dataset) -> tuple[h5py.Dataset, str]:
    kind = _dataset_kind(path, source)
    kwargs: dict[str, Any] = {}
    chunks = choose_chunk_shape(source.shape, source.dtype)
    if chunks is not None:
        kwargs["chunks"] = chunks
        if kind == "gzip_shuffle":
            kwargs.update(compression="gzip", shuffle=True)
        elif kind == "zfp_reversible":
            kwargs.update(hdf5plugin.Zfp(reversible=True))
    destination = target.create_dataset(path, shape=source.shape, dtype=source.dtype, **kwargs)
    _copy_attrs(source.attrs, destination.attrs)
    return destination, kind


def _copy_dataset(source: h5py.Dataset, target: h5py.Dataset) -> None:
    if source.shape == ():
        target[()] = source[()]
        return
    for selection in target.iter_chunks():
        target[selection] = source[selection]


def _attribute_value_equal(left: Any, right: Any) -> bool:
    left_array, right_array = np.asarray(left), np.asarray(right)
    return (
        left_array.dtype == right_array.dtype
        and left_array.shape == right_array.shape
        and left_array.tobytes() == right_array.tobytes()
    )


def _validate_attrs(left: h5py.AttributeManager, right: h5py.AttributeManager, path: str) -> None:
    if set(left) != set(right):
        raise CompressionError(f"attribute names differ at {path}")
    for name in left:
        if not _attribute_value_equal(left[name], right[name]):
            raise CompressionError(f"attribute {name!r} differs at {path}")


def _object_inventory(handle: h5py.File) -> dict[str, str]:
    inventory = {"/": "group"}

    def record(path: str, obj: h5py.Group | h5py.Dataset) -> None:
        inventory[path] = "dataset" if isinstance(obj, h5py.Dataset) else "group"

    handle.visititems(record)
    return inventory


def validate_reversible_copy(source_path: Path, compressed_path: Path) -> list[dict[str, Any]]:
    """Validate hierarchy, metadata, dtypes, shapes, and bitwise values."""
    rows: list[dict[str, Any]] = []
    with h5py.File(source_path, "r") as source, h5py.File(compressed_path, "r") as compressed:
        if _object_inventory(source) != _object_inventory(compressed):
            raise CompressionError("HDF5 group/dataset inventory differs")
        _validate_attrs(source.attrs, compressed.attrs, "/")

        def validate(path: str, obj: h5py.Group | h5py.Dataset) -> None:
            other = compressed[path]
            _validate_attrs(obj.attrs, other.attrs, path)
            if isinstance(obj, h5py.Group):
                return
            if obj.shape != other.shape or obj.dtype != other.dtype:
                raise CompressionError(f"dataset schema differs at {path}")
            digest_source = hashlib.sha256()
            digest_compressed = hashlib.sha256()
            if obj.shape == ():
                digest_source.update(np.asarray(obj[()]).tobytes())
                digest_compressed.update(np.asarray(other[()]).tobytes())
            else:
                for selection in other.iter_chunks():
                    left = np.ascontiguousarray(obj[selection])
                    right = np.ascontiguousarray(other[selection])
                    digest_source.update(left.tobytes())
                    digest_compressed.update(right.tobytes())
            if digest_source.digest() != digest_compressed.digest():
                raise CompressionError(f"dataset values differ at {path}")
            rows.append({
                "dataset": path,
                "shape": list(obj.shape),
                "dtype": str(obj.dtype),
                "compression_kind": _dataset_kind(path, obj),
                "value_sha256": digest_source.hexdigest(),
                "bitwise_identical": True,
            })

        source.visititems(validate)
    return rows


def compress_reversibly(source_path: Path, output_path: Path, report_path: Path) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    output_path = Path(output_path).resolve()
    report_path = Path(report_path).resolve()
    temporary = output_path.with_name(output_path.name + ".partial")
    for forbidden in (output_path, report_path, temporary):
        if forbidden.exists() or forbidden.is_symlink():
            raise CompressionError(f"refusing to overwrite existing path: {forbidden}")
    if source_path == output_path or not source_path.is_file():
        raise CompressionError("source must be an existing file distinct from output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    dataset_kinds: dict[str, str] = {}
    try:
        with h5py.File(source_path, "r") as source, h5py.File(temporary, "x") as target:
            _copy_attrs(source.attrs, target.attrs)

            def copy(path: str, obj: h5py.Group | h5py.Dataset) -> None:
                if isinstance(obj, h5py.Group):
                    group = target.create_group(path)
                    _copy_attrs(obj.attrs, group.attrs)
                    return
                destination, kind = _create_dataset(target, path, obj)
                dataset_kinds[path] = kind
                _copy_dataset(obj, destination)

            source.visititems(copy)
            target.flush()
        validation = validate_reversible_copy(source_path, temporary)
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    source_bytes = source_path.stat().st_size
    output_bytes = output_path.stat().st_size
    result = {
        "status": "complete_reversible_copy",
        "source": str(source_path),
        "output": str(output_path),
        "source_bytes": source_bytes,
        "compressed_bytes": output_bytes,
        "source_over_compressed_ratio": source_bytes / output_bytes,
        "space_reduction_fraction": 1 - output_bytes / source_bytes,
        "elapsed_seconds": time.monotonic() - start,
        "dataset_count": len(validation),
        "compression_counts": {
            kind: sum(value == kind for value in dataset_kinds.values())
            for kind in sorted(set(dataset_kinds.values()))
        },
        "validation": validation,
        "gates": {
            "no_overwrite": True,
            "hierarchy_and_metadata_preserved": True,
            "dtype_and_shape_preserved": True,
            "bitwise_values_preserved": True,
            "reopen_with_hdf5plugin": True,
        },
    }
    report_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compress_reversibly(args.source, args.output, args.report)
    except (CompressionError, OSError, ValueError) as exc:
        print(f"compression_error={exc}")
        return 2
    print(f"compression_ratio={result['source_over_compressed_ratio']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
