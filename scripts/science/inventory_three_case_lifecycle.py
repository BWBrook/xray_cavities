#!/usr/bin/env python3
"""Read-only, contract-driven inventory for the three-case data estate.

The scanner deliberately has no mutation primitive other than creating the
requested output directory and its four report files.  It inventories only
the roots named by the root contract, never follows symlinks, and refuses
ambiguous or changing inputs rather than producing a deletion proposal.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT_COLUMNS = {
    "case_id",
    "root_id",
    "root_path",
    "root_kind",
    "purpose",
    "expected_presence",
    "source_evidence",
}
PROTECTED_COLUMNS = {
    "path",
    "protection_class",
    "dependency",
    "source_evidence",
    "existing_sha256",
}
PROTECTED_EXPECTED_COLUMNS = {
    "expected_timestep", "expected_time_code", "expected_time_myr",
    "expected_shape", "expected_datasets",
}
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
PARTICLE_RE = re.compile(r"^particles(?:\.|$)", re.I)
PROTECTED_HASH_MAX_BYTES = 64 * 1024 * 1024

PAYLOAD_COLUMNS = [
    "case_id",
    "root_id",
    "root_path",
    "root_kind",
    "path",
    "relative_path",
    "resolved_path",
    "file_type",
    "link_target",
    "symlink_target_status",
    "device",
    "inode",
    "apparent_bytes",
    "allocated_bytes",
    "mtime_ns",
    "data_class",
    "contract_protection",
    "dependency",
    "source_evidence",
    "hash_policy",
    "sha256",
    "sha256_status",
    "hash_provenance",
    "identity_method",
    "identity_status",
    "hdf5_status",
    "hdf5_timestep",
    "hdf5_time_code",
    "hdf5_time_myr",
    "hdf5_shape",
    "hdf5_datasets",
]


class InventoryError(RuntimeError):
    """Raised for an unsafe or incomplete inventory operation."""


def _absolute(path: str | Path) -> Path:
    return Path(path).expanduser().absolute()


def _normalise_bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "y", "present", "required"}:
        return True
    if lowered in {"0", "false", "no", "n", "absent", "optional"}:
        return False
    raise InventoryError(f"invalid expected_presence value: {value!r}")


def _read_contract(path: Path, required: set[str], *, allow_empty: bool = False) -> list[dict[str, str]]:
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise InventoryError(f"empty contract header: {path}")
            if len(reader.fieldnames) != len(set(reader.fieldnames)):
                raise InventoryError(f"duplicate contract columns: {path}")
            missing = required - set(reader.fieldnames)
            if missing:
                raise InventoryError(f"missing contract columns {sorted(missing)}: {path}")
            rows = []
            for number, row in enumerate(reader, start=2):
                if None in row:
                    raise InventoryError(f"unexpected contract columns at line {number}: {path}")
                if any(value is None for value in row.values()):
                    raise InventoryError(f"missing contract value at line {number}: {path}")
                rows.append({key: (value or "").strip() for key, value in row.items()})
    except OSError as exc:
        raise InventoryError(f"cannot read contract {path}: {exc}") from exc
    if not rows and not allow_empty:
        raise InventoryError(f"contract has no rows: {path}")
    return rows


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _stat_signature(st: os.stat_result) -> tuple[int, int, int, int, int]:
    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_mode)


def _snapshot_signature(st: os.stat_result) -> tuple[int, ...]:
    """Return stable tree identity, excluding unreliable directory size."""

    if stat.S_ISDIR(st.st_mode):
        return (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_mode)
    return _stat_signature(st)


def _sha256_file(path: Path, before: os.stat_result | None = None) -> str:
    """Hash a regular file, refusing a file changed during the read."""

    before = before or path.stat()
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise InventoryError(f"hash failed for {path}: {exc}") from exc
    try:
        after = path.stat()
    except OSError as exc:
        raise InventoryError(f"post-hash stat failed for {path}: {exc}") from exc
    if _stat_signature(before) != _stat_signature(after):
        raise InventoryError(f"file changed during hash: {path}")
    return digest.hexdigest()


def _contract_digest(root_contract: Path, protected_contract: Path) -> str:
    digest = hashlib.sha256()
    for path in (root_contract, protected_contract):
        digest.update(path.name.encode())
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            raise InventoryError(f"cannot read contract for digest: {path}: {exc}") from exc
    return digest.hexdigest()


def _is_particle(path: Path) -> bool:
    return bool(PARTICLE_RE.search(path.name))


def _hdf5_metadata(path: Path, expected: dict[str, str] | None = None) -> dict[str, str]:
    """Read lightweight HDF5 metadata without touching the file for write."""

    fields = {
        "hdf5_status": "not_hdf5",
        "hdf5_timestep": "",
        "hdf5_time_code": "",
        "hdf5_time_myr": "",
        "hdf5_shape": "",
        "hdf5_datasets": "",
    }
    expected = expected or {}
    if path.suffix.lower() not in {".h5", ".hdf5"}:
        return fields
    try:
        import h5py  # type: ignore
    except ImportError:
        if any(expected.get(key, "") for key in ("expected_timestep", "expected_time_code", "expected_shape", "expected_datasets")):
            raise InventoryError(f"required HDF5 metadata unavailable: {path}")
        fields["hdf5_status"] = "unavailable"
        return fields
    try:
        with h5py.File(path, "r") as handle:
            fields["hdf5_status"] = "read"
            names = sorted(name for name in handle.keys() if name.startswith("Timestep_"))
            expected_timestep = expected.get("expected_timestep", "")
            if expected_timestep:
                if expected_timestep not in names:
                    raise InventoryError(
                        f"required HDF5 timestep mismatch: {path}: expected {expected_timestep}, found {names}"
                    )
                selected_name = expected_timestep
            else:
                selected_name = names[0] if names else ""
            if selected_name:
                fields["hdf5_timestep"] = selected_name
            datasets: list[str] = []
            shapes: list[str] = []

            def visitor(name: str, obj: Any) -> None:
                if hasattr(obj, "shape"):
                    datasets.append(name)
                    shapes.append(f"{name}:{tuple(obj.shape)}")

            handle.visititems(visitor)
            fields["hdf5_datasets"] = ";".join(sorted(datasets))
            fields["hdf5_shape"] = ";".join(sorted(shapes))
            selected_group = handle[selected_name] if selected_name else handle
            attrs = dict(selected_group.attrs.items())
            attrs.update({key: value for key, value in handle.attrs.items() if key not in attrs})
            for key in ("Time", "time_code", "time", "t"):
                if key in attrs:
                    fields["hdf5_time_code"] = str(attrs[key])
                    break
            for key in ("time_myr", "time_Myr"):
                if key in attrs:
                    fields["hdf5_time_myr"] = str(attrs[key])
                    break
            expected_datasets = {
                item for item in expected.get("expected_datasets", "").split(";") if item
            }
            expected_dataset_paths: dict[str, str] = {}
            if selected_name and expected_datasets:
                dataset_paths_by_basename: dict[str, list[str]] = {}
                for name in datasets:
                    if not name.startswith(selected_name + "/"):
                        continue
                    dataset_paths_by_basename.setdefault(name.rsplit("/", 1)[-1], []).append(name)
                actual_datasets = set(dataset_paths_by_basename)
                if not expected_datasets.issubset(actual_datasets):
                    raise InventoryError(
                        f"required HDF5 datasets mismatch: {path}: expected {sorted(expected_datasets)}, found {sorted(actual_datasets)}"
                    )
                ambiguous = {
                    name: sorted(dataset_paths_by_basename[name])
                    for name in expected_datasets
                    if len(dataset_paths_by_basename[name]) != 1
                }
                if ambiguous:
                    raise InventoryError(
                        f"ambiguous HDF5 dataset basename: {path}: {ambiguous}"
                    )
                expected_dataset_paths = {
                    name: dataset_paths_by_basename[name][0]
                    for name in expected_datasets
                }
            expected_shape = expected.get("expected_shape", "")
            if selected_name and expected_shape:
                try:
                    shape = tuple(int(value) for value in expected_shape.lower().split("x"))
                except ValueError as exc:
                    raise InventoryError(f"invalid expected HDF5 shape for {path}: {expected_shape}") from exc
                mismatched = []
                for dataset in expected_datasets:
                    dataset_path = expected_dataset_paths.get(dataset, "")
                    obj = handle[dataset_path] if dataset_path else None
                    if obj is None or tuple(obj.shape) != shape:
                        mismatched.append(dataset)
                if mismatched:
                    raise InventoryError(
                        f"required HDF5 shape mismatch: {path}: expected {shape}, datasets {mismatched}"
                    )
            expected_time = expected.get("expected_time_code", "")
            if selected_name and expected_time:
                try:
                    observed = float(fields["hdf5_time_code"])
                    wanted = float(expected_time)
                except ValueError as exc:
                    raise InventoryError(f"invalid HDF5 time metadata for {path}") from exc
                if abs(observed - wanted) > max(1e-8, abs(wanted) * 1e-10):
                    raise InventoryError(
                        f"required HDF5 time mismatch: {path}: expected {wanted}, found {observed}"
                    )
            expected_time_myr = expected.get("expected_time_myr", "")
            if selected_name and expected_time_myr:
                if not fields["hdf5_time_myr"]:
                    raise InventoryError(f"required HDF5 Myr metadata unavailable: {path}")
                if abs(float(fields["hdf5_time_myr"]) - float(expected_time_myr)) > max(1e-8, abs(float(expected_time_myr)) * 1e-8):
                    raise InventoryError(f"required HDF5 Myr time mismatch: {path}")
    except (OSError, ValueError, RuntimeError) as exc:
        raise InventoryError(f"required candidate HDF5 unreadable: {path}: {exc}") from exc
    return fields


def _validate_contracts(
    root_rows: list[dict[str, str]],
    protected_rows: list[dict[str, str]],
    output_dir: Path,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, str]]]:
    roots: list[dict[str, Any]] = []
    root_by_id: dict[str, dict[str, Any]] = {}
    root_paths: dict[str, Path] = {}
    for row in root_rows:
        root_id = row["root_id"]
        if not root_id or root_id in root_by_id:
            raise InventoryError(f"duplicate/empty root_id: {root_id!r}")
        root_path = _absolute(row["root_path"])
        try:
            st = root_path.lstat()
        except OSError as exc:
            if _normalise_bool(row["expected_presence"]):
                raise InventoryError(f"expected root missing: {root_path}") from exc
            roots.append({**row, "root_path": str(root_path), "exists": False, "root_type": "missing"})
            root_by_id[root_id] = roots[-1]
            continue
        if not stat.S_ISDIR(st.st_mode):
            raise InventoryError(f"root is not a directory: {root_path}")
        canonical = root_path.resolve()
        entry = {**row, "root_path": str(root_path), "exists": True, "root_type": "directory"}
        roots.append(entry)
        root_by_id[root_id] = entry
        root_paths[root_id] = canonical
    ordered = sorted(root_paths.items(), key=lambda item: str(item[1]))
    for index, (left_id, left) in enumerate(ordered):
        for right_id, right in ordered[index + 1 :]:
            if _is_within(left, right) or _is_within(right, left):
                raise InventoryError(f"overlapping allowlisted roots: {left_id}, {right_id}")
    for root in root_paths.values():
        if _is_within(output_dir, root) or output_dir == root:
            raise InventoryError(f"output directory lies inside inventoried root: {output_dir}")

    protected: dict[str, dict[str, str]] = {}
    for row in protected_rows:
        path = _absolute(row["path"])
        key = str(path)
        if key in protected:
            raise InventoryError(f"duplicate protected contract path: {path}")
        if not any(_is_within(path, root) for root in root_paths.values()):
            raise InventoryError(f"protected path outside allowlisted roots: {path}")
        declared = row.get("existing_sha256", "")
        if declared and not SHA256_RE.fullmatch(declared):
            raise InventoryError(f"invalid existing_sha256 for {path}")
        try:
            st = path.lstat()
        except FileNotFoundError as exc:
            raise InventoryError(f"protected path missing: {path}") from exc
        except OSError as exc:
            raise InventoryError(f"cannot lstat protected path {path}: {exc}") from exc
        if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
            raise InventoryError(f"unexpected protected path type: {path}")
        if stat.S_ISLNK(st.st_mode):
            raise InventoryError(f"protected symlink target is not permitted: {path}")
        resolved = path.resolve(strict=True)
        if not any(_is_within(resolved, root) for root in root_paths.values()):
            raise InventoryError(f"protected path resolves outside allowlisted roots: {path} -> {resolved}")
        for column in PROTECTED_EXPECTED_COLUMNS:
            row.setdefault(column, "")
        protected[key] = row
    return roots, protected


def _record_file(
    path: Path,
    root: dict[str, Any],
    root_path: Path,
    protected: dict[str, dict[str, str]],
    read_hdf5: bool,
) -> dict[str, Any]:
    st = path.lstat()
    relative = path.relative_to(root_path).as_posix()
    contract = protected.get(str(path))
    is_link = stat.S_ISLNK(st.st_mode)
    is_regular = stat.S_ISREG(st.st_mode)
    if not is_link and not is_regular:
        raise InventoryError(f"unexpected path type while walking: {path}")
    link_target = os.readlink(path) if is_link else ""
    if contract is not None:
        data_class = contract["protection_class"]
        contract_protection = "PROTECTED"
        dependency = contract["dependency"]
        source_evidence = contract["source_evidence"]
    elif is_link:
        data_class = "HOLD_AMBIGUOUS"
        contract_protection = "UNPROTECTED"
        dependency = source_evidence = ""
    elif _is_particle(path):
        data_class = "HOLD_RADIO_UNRESOLVED"
        contract_protection = "UNPROTECTED"
        dependency = source_evidence = ""
    elif path.suffix.lower() in {".h5", ".hdf5", ".xmf", ".h5.xmf"} or "analysis" in root["root_kind"].lower() or "analysis" in root["purpose"].lower():
        data_class = "CANDIDATE_REVIEW"
        contract_protection = "UNPROTECTED"
        dependency = source_evidence = ""
    else:
        data_class = "RETAIN_COMPACT"
        contract_protection = "UNPROTECTED"
        dependency = source_evidence = ""

    row: dict[str, Any] = {
        "case_id": root["case_id"],
        "root_id": root["root_id"],
        "root_path": root["root_path"],
        "root_kind": root["root_kind"],
        "path": str(path),
        "relative_path": relative,
        "resolved_path": "" if is_link else str(path),
        "file_type": "symlink" if is_link else "regular",
        "link_target": link_target,
        "symlink_target_status": "pending" if is_link else "not_applicable",
        "device": str(st.st_dev),
        "inode": str(st.st_ino),
        "apparent_bytes": str(st.st_size),
        "allocated_bytes": str(getattr(st, "st_blocks", 0) * 512),
        "mtime_ns": str(st.st_mtime_ns),
        "data_class": data_class,
        "contract_protection": contract_protection,
        "dependency": dependency,
        "source_evidence": source_evidence,
        "hash_policy": "none",
        "sha256": "",
        "sha256_status": "not_hashed",
        "hash_provenance": "none",
        "identity_method": "lstat_pre_and_post_read",
        "identity_status": "pending",
    }
    trusted = contract and contract.get("existing_sha256", "")
    if is_link:
        if trusted:
            row["hash_policy"] = "protected_existing_sha256"
            row["sha256"] = trusted.lower()
            row["sha256_status"] = "trusted_contract_hash"
            row["hash_provenance"] = "contract_existing_sha256"
        else:
            row["hash_policy"] = "no_hash_symlink"
            row["sha256_status"] = "held_symlink"
            row["hash_provenance"] = "none_symlink_identity"
    elif data_class == "HOLD_RADIO_UNRESOLVED" and not trusted:
        row["hash_policy"] = "no_hash_particle"
        row["sha256_status"] = "held_particle"
        row["hash_provenance"] = "none_radio_hold"
    elif contract is not None and not trusted and st.st_size > PROTECTED_HASH_MAX_BYTES and all(
        contract.get(key, "")
        for key in ("expected_timestep", "expected_time_code", "expected_shape", "expected_datasets")
    ):
        row["hash_policy"] = "protected_stable_identity"
        row["sha256_status"] = "protected_identity_only"
        row["hash_provenance"] = "none_protected_stable_identity"
    else:
        row["hash_policy"] = "full_sha256" if not trusted else "protected_existing_sha256"
        digest = _sha256_file(path, before=st)
        if trusted and digest.lower() != trusted.lower():
            raise InventoryError(f"protected hash mismatch: {path}")
        row["sha256"] = digest
        row["sha256_status"] = "verified" if trusted else "hashed"
        row["hash_provenance"] = (
            "contract_existing_sha256_verified"
            if trusted
            else "fresh_inventory_sha256"
        )
    expected_hdf5 = contract is not None and all(
        contract.get(key, "")
        for key in ("expected_timestep", "expected_time_code", "expected_shape", "expected_datasets")
    )
    row.update(
        _hdf5_metadata(path, contract)
        if path.suffix.lower() in {".h5", ".hdf5"} and (
            (read_hdf5 and (data_class == "CANDIDATE_REVIEW" or contract is not None))
            or expected_hdf5
        )
        else {
            "hdf5_status": "not_requested" if path.suffix.lower() in {".h5", ".hdf5"} else "not_hdf5",
            "hdf5_timestep": "",
            "hdf5_time_code": "",
            "hdf5_time_myr": "",
            "hdf5_shape": "",
            "hdf5_datasets": "",
        }
    )
    try:
        after = path.lstat()
    except OSError as exc:
        raise InventoryError(f"post-read lstat failed for {path}: {exc}") from exc
    if _stat_signature(st) != _stat_signature(after):
        raise InventoryError(f"path changed during inventory: {path}")
    row["identity_status"] = "stable"
    return row


def _validate_symlink_targets(
    payloads: list[dict[str, Any]],
    roots: list[dict[str, Any]],
) -> None:
    """Classify link targets without following them during traversal."""

    allowed = [Path(root["root_path"]) for root in roots if root["exists"]]
    for row in payloads:
        if row["file_type"] != "symlink":
            continue
        link = Path(row["path"])
        target = Path(row["link_target"])
        if not target.is_absolute():
            target = link.parent / target
        try:
            target = target.resolve(strict=True)
        except FileNotFoundError:
            target = target.absolute()
        row["resolved_path"] = str(target)
        target_in_allowlist = any(_is_within(target, root) for root in allowed)
        try:
            target_st = target.lstat()
            target_exists = True
        except FileNotFoundError:
            target_exists = False
        except OSError as exc:
            raise InventoryError(f"cannot lstat symlink target {target}: {exc}") from exc
        if not target_exists:
            row["symlink_target_status"] = "missing"
            row["identity_status"] = "unresolved_symlink"
            row["data_class"] = "HOLD_AMBIGUOUS"
        elif not target_in_allowlist:
            row["symlink_target_status"] = "outside_allowlist"
            row["identity_status"] = "unresolved_symlink"
            row["data_class"] = "HOLD_AMBIGUOUS"
        elif not stat.S_ISREG(target_st.st_mode):
            row["symlink_target_status"] = "target_not_regular"
            row["identity_status"] = "unresolved_symlink"
            row["data_class"] = "HOLD_AMBIGUOUS"
        else:
            row["symlink_target_status"] = "exists_in_allowlist"
        if (
            row["contract_protection"] == "PROTECTED"
            and row["symlink_target_status"] != "exists_in_allowlist"
        ):
            raise InventoryError(
                "protected symlink target is missing or outside allowlist: "
                f"{link} -> {target}"
            )


def _walk_root(root: dict[str, Any], protected: dict[str, dict[str, str]], read_hdf5: bool) -> list[dict[str, Any]]:
    root_path = Path(root["root_path"])
    if not root["exists"]:
        return []
    found: list[dict[str, Any]] = []
    stack = [root_path]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda entry: entry.name)
        except OSError as exc:
            raise InventoryError(f"cannot scan {current}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            st = path.lstat()
            if stat.S_ISDIR(st.st_mode):
                stack.append(path)
            else:
                found.append(_record_file(path, root, root_path, protected, read_hdf5))
    return sorted(found, key=lambda row: (row["root_id"], row["relative_path"]))


def _tree_snapshot(root: dict[str, Any]) -> dict[str, tuple[int, ...] | None]:
    """Capture directory entries and lstat identities without following links."""
    root_path = Path(root["root_path"])
    snapshot: dict[str, tuple[int, int, int, int, int] | None] = {}
    try:
        root_path.lstat()
    except FileNotFoundError:
        return {str(root_path): None}
    except OSError as exc:
        raise InventoryError(f"cannot snapshot {root_path}: {exc}") from exc
    stack = [root_path]
    while stack:
        current = stack.pop()
        try:
            current_st = current.lstat()
            snapshot[str(current)] = _snapshot_signature(current_st)
            entries = sorted(os.scandir(current), key=lambda entry: entry.name)
        except OSError as exc:
            raise InventoryError(f"cannot snapshot {current}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            st = path.lstat()
            snapshot[str(path)] = _snapshot_signature(st)
            if stat.S_ISDIR(st.st_mode):
                stack.append(path)
    return snapshot


def _assert_snapshot_stable(
    before: dict[str, tuple[int, ...] | None],
    after: dict[str, tuple[int, ...] | None],
    root: dict[str, Any],
) -> None:
    if before != after:
        added = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
        changed_details = [
            f"{path}:before={before[path]} after={after[path]}"
            for path in changed[:3]
        ]
        raise InventoryError(
            f"inventory-wide identity drift in {root['root_id']}: "
            f"added={added[:3]} removed={removed[:3]} changed={changed_details}"
        )


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], columns: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def run_inventory(
    root_contract: Path,
    protected_contract: Path,
    output_dir: Path,
    *,
    contract_metadata: Path | None = None,
    read_hdf5_metadata: bool = False,
    max_workers: int = 1,
) -> dict[str, Any]:
    if max_workers < 1:
        raise InventoryError("max_workers must be >= 1")
    root_rows = _read_contract(root_contract, ROOT_COLUMNS)
    protected_rows = _read_contract(protected_contract, PROTECTED_COLUMNS, allow_empty=True)
    if contract_metadata is not None:
        try:
            metadata = json.loads(contract_metadata.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise InventoryError(f"cannot read contract metadata: {contract_metadata}") from exc
        expected_files = metadata.get("contract_files")
        if expected_files != [root_contract.name, protected_contract.name]:
            raise InventoryError(f"contract metadata files mismatch: {expected_files!r}")
        expected_digest = metadata.get("contract_digest_sha256")
        actual_digest = _contract_digest(root_contract, protected_contract)
        if not isinstance(expected_digest, str) or expected_digest != actual_digest:
            raise InventoryError(
                f"contract digest mismatch: expected {expected_digest!r}, found {actual_digest}"
            )
    output_dir = _absolute(output_dir)
    roots, protected = _validate_contracts(root_rows, protected_rows, output_dir)
    if output_dir.exists():
        raise InventoryError(f"output directory reservation already exists: {output_dir}")
    try:
        output_dir.parent.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir()
    except FileExistsError as exc:
        raise InventoryError(f"output directory reservation already exists: {output_dir}") from exc
    except OSError as exc:
        raise InventoryError(f"cannot reserve output directory: {output_dir}: {exc}") from exc
    payloads: list[dict[str, Any]] = []
    ordered_roots = sorted(roots, key=lambda item: item["root_id"])
    snapshots = {root["root_id"]: _tree_snapshot(root) for root in ordered_roots}
    if max_workers > 1 and len(ordered_roots) > 1:
        # Each worker is confined to one exact allowlisted root.  Results are
        # sorted below, so concurrency cannot alter the report bytes.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            batches = executor.map(
                lambda root: _walk_root(root, protected, read_hdf5_metadata),
                ordered_roots,
            )
            for batch in batches:
                payloads.extend(batch)
    else:
        for root in ordered_roots:
            payloads.extend(_walk_root(root, protected, read_hdf5_metadata))
    for root in ordered_roots:
        _assert_snapshot_stable(snapshots[root["root_id"]], _tree_snapshot(root), root)
    present = {row["path"] for row in payloads}
    missing_protected = sorted(set(protected) - present)
    if missing_protected:
        raise InventoryError(
            "protected paths absent from inventory: " + ", ".join(missing_protected)
        )
    _validate_symlink_targets(payloads, roots)
    payloads.sort(key=lambda row: (row["root_id"], row["relative_path"], row["file_type"]))
    root_inventory: list[dict[str, Any]] = []
    for root in sorted(roots, key=lambda item: item["root_id"]):
        rows = [row for row in payloads if row["root_id"] == root["root_id"]]
        root_inventory.append(
            {
                "case_id": root["case_id"],
                "root_id": root["root_id"],
                "root_path": root["root_path"],
                "root_kind": root["root_kind"],
                "purpose": root["purpose"],
                "expected_presence": root["expected_presence"],
                "source_evidence": root["source_evidence"],
                "exists": str(root["exists"]).lower(),
                "root_type": root["root_type"],
                "payload_count": str(len(rows)),
                "apparent_bytes": str(sum(int(row["apparent_bytes"] or 0) for row in rows)),
                "allocated_bytes": str(sum(int(row["allocated_bytes"] or 0) for row in rows)),
            }
        )
    summary = [
        {"metric": "root_count", "value": str(len(roots))},
        {"metric": "payload_count", "value": str(len(payloads))},
        {"metric": "regular_count", "value": str(sum(row["file_type"] == "regular" for row in payloads))},
        {"metric": "symlink_count", "value": str(sum(row["file_type"] == "symlink" for row in payloads))},
        {"metric": "particle_hold_count", "value": str(sum(row["data_class"] == "HOLD_RADIO_UNRESOLVED" for row in payloads))},
        {"metric": "candidate_review_count", "value": str(sum(row["data_class"] == "CANDIDATE_REVIEW" for row in payloads))},
        {"metric": "protected_count", "value": str(sum(row["contract_protection"] == "PROTECTED" for row in payloads))},
        {"metric": "apparent_bytes", "value": str(sum(int(row["apparent_bytes"] or 0) for row in payloads))},
        {"metric": "allocated_bytes", "value": str(sum(int(row["allocated_bytes"] or 0) for row in payloads))},
    ]
    canonical = json.dumps({"roots": root_inventory, "payloads": payloads, "summary": summary}, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    _write_csv(output_dir / "remote_root_inventory.csv", root_inventory, list(root_inventory[0]) if root_inventory else ["root_id"])
    _write_csv(output_dir / "payload_inventory.csv", payloads, PAYLOAD_COLUMNS)
    _write_csv(output_dir / "inventory_summary.csv", summary, ["metric", "value"])
    metadata = {
        "schema_version": "1.0",
        "root_contract": str(_absolute(root_contract)),
        "protected_contract": str(_absolute(protected_contract)),
        "contract_metadata": str(_absolute(contract_metadata)) if contract_metadata else "",
        "contract_digest_sha256": _contract_digest(root_contract, protected_contract),
        "read_hdf5_metadata": read_hdf5_metadata,
        "max_workers": max_workers,
        "manifest_digest_sha256": digest,
        "verified_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": {row["metric"]: int(row["value"]) for row in summary if row["value"].isdigit()},
        "read_only": True,
        "follow_symlinks": False,
        "deletion_capability": False,
    }
    (output_dir / "inventory_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return metadata


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root-contract", type=Path, required=True)
    parser.add_argument("--protected-contract", type=Path, required=True)
    parser.add_argument("--contract-metadata", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--read-hdf5-metadata", action="store_true")
    parser.add_argument("--max-workers", type=int, default=1)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        metadata = run_inventory(
            args.root_contract,
            args.protected_contract,
            args.output_dir,
            contract_metadata=args.contract_metadata,
            read_hdf5_metadata=args.read_hdf5_metadata,
            max_workers=args.max_workers,
        )
    except InventoryError as exc:
        print(f"inventory_error: {exc}", file=sys.stderr)
        return 2
    print(f"manifest_digest_sha256={metadata['manifest_digest_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
