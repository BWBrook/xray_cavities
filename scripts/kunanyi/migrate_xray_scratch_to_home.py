#!/usr/bin/env python3
"""Bounded, resumable migration of explicitly planned scratch trees.

The command is deliberately conservative.  A plan names every source and
destination; the command never discovers additional roots and never removes a
path unless it is present in the immutable source manifest for that unit.
"""

from __future__ import annotations

import argparse
import base64
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any


SCHEMA = 2
METADATA_POLICY = "private_archive"
LARGE_HASH_BYTES = 64 * 1024 * 1024
SIGNATURE_FIELDS = ("dev", "ino", "size", "mtime_ns", "ctime_ns", "mode", "uid", "gid")


class MigrationError(RuntimeError):
    pass


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _plan_hash(plan: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(plan).encode()).hexdigest()


def _fsync_parent(path: Path) -> None:
    try:
        fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        try:
            os.fsync(fd)
        except OSError:
            # Some network filesystems expose an open directory but do not
            # support directory fsync.  File contents and ledger records are
            # still fsynced; use the strongest operation the filesystem offers.
            pass
    finally:
        os.close(fd)


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(_canonical(value) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        _fsync_parent(path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _append_json(path: Path, value: Any) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(_canonical(value) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _lexical_absolute(value: str, label: str) -> Path:
    if not isinstance(value, str):
        raise MigrationError(f"{label} must be a string")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise MigrationError(f"{label} must be absolute: {value!r}")
    return Path(os.path.normpath(str(path)))


def _restore_xattrs(path: Path, expected: dict[str, str | None]) -> None:
    listxattr = getattr(os, "listxattr", None)
    setxattr = getattr(os, "setxattr", None)
    removexattr = getattr(os, "removexattr", None)
    if listxattr is None or setxattr is None or removexattr is None:
        if expected:
            raise MigrationError(f"cannot preserve xattrs on this Python/filesystem: {path}")
        return
    try:
        current = set(listxattr(path, follow_symlinks=False))
        wanted = set(expected)
        for name in current - wanted:
            removexattr(path, name, follow_symlinks=False)
        for name, encoded in expected.items():
            if encoded is None:
                # NFS may advertise this virtual name while its server rejects
                # GETXATTR. Keep the unavailability explicit in both inventories.
                continue
            setxattr(path, name, base64.b64decode(encoded), follow_symlinks=False)
    except OSError as exc:
        raise MigrationError(f"cannot restore xattrs for {path}: {exc}") from exc


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _kind(mode: int) -> str:
    if stat.S_ISREG(mode):
        return "file"
    if stat.S_ISDIR(mode):
        return "dir"
    if stat.S_ISLNK(mode):
        return "symlink"
    raise MigrationError(f"unsupported special file at migration path (mode {oct(mode)})")


def _sig(st: os.stat_result) -> dict[str, int]:
    return {field: int(getattr(st, f"st_{field}")) for field in SIGNATURE_FIELDS}


def _xattrs(path: Path) -> dict[str, str | None]:
    """Capture xattrs, including POSIX ACL xattrs where exposed by the filesystem."""
    listxattr = getattr(os, "listxattr", None)
    getxattr = getattr(os, "getxattr", None)
    if listxattr is None or getxattr is None:
        return {}
    try:
        names = listxattr(path, follow_symlinks=False)
    except OSError as exc:
        if exc.errno in {errno.ENOTSUP, errno.EOPNOTSUPP, errno.ENODATA, errno.ENOENT}:
            return {}
        raise MigrationError(f"cannot list xattrs for {path}: {exc}") from exc
    result: dict[str, str | None] = {}
    for name in sorted(names):
        try:
            value = getxattr(path, name, follow_symlinks=False)
        except OSError as exc:
            if name == "system.nfs4_acl" and exc.errno in {errno.ENOTSUP, errno.EOPNOTSUPP}:
                result[name] = None
                continue
            raise MigrationError(f"cannot read xattr {name} for {path}: {exc}") from exc
        result[name] = base64.b64encode(value).decode("ascii")
    return result


def _validate_source_policy(entries: dict[str, dict[str, Any]], source: Path) -> None:
    """Gate source ownership/readability before any copy is attempted."""
    effective_uid = os.geteuid()
    for relative, entry in entries.items():
        signature = entry["signature"]
        path = _path_for(source, relative)
        if signature["uid"] != effective_uid:
            raise MigrationError(f"source object is not owned by current user: {path}")
        if entry["kind"] == "file" and not (signature["mode"] & stat.S_IRUSR):
            raise MigrationError(f"source regular file is not owner-readable: {path}")
        for name, value in entry.get("xattrs", {}).items():
            is_acl_or_security = (name.startswith("security.") or
                                  name.startswith("system.posix_acl") or
                                  name in {"system.nfs4_acl", "system.richacl"})
            if is_acl_or_security and not (name == "system.nfs4_acl" and value is None):
                raise MigrationError(f"source has readable ACL/security xattr {name}: {path}")


def _same_sig(left: dict[str, int], right: dict[str, int]) -> bool:
    return all(int(left[field]) == int(right[field]) for field in SIGNATURE_FIELDS)


def _lstat(path: Path, context: str) -> os.stat_result:
    try:
        return path.lstat()
    except FileNotFoundError as exc:
        raise MigrationError(f"missing {context}: {path}") from exc
    except OSError as exc:
        raise MigrationError(f"cannot lstat {context} {path}: {exc}") from exc


def _chmod_nofollow(path: Path, mode: int, expected_kind: str | None = None) -> None:
    """Change mode through an O_NOFOLLOW descriptor for Linux/NFS portability."""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    if expected_kind == "dir":
        flags |= getattr(os, "O_DIRECTORY", 0)
    try:
        fd = os.open(path, flags)
        try:
            observed = os.fstat(fd)
            kind = _kind(observed.st_mode)
            if expected_kind is not None and kind != expected_kind:
                raise MigrationError(f"destination type changed while chmod-ing {path}")
            os.fchmod(fd, mode)
        finally:
            os.close(fd)
    except MigrationError:
        raise
    except OSError as exc:
        raise MigrationError(f"cannot safely chmod {path}: {exc}") from exc


def _inventory(root: Path, *, allow_root_missing: bool = False) -> dict[str, dict[str, Any]]:
    """Return a non-following inventory, failing on unsupported file types."""
    try:
        root_st = root.lstat()
    except FileNotFoundError:
        if allow_root_missing:
            return {}
        raise MigrationError(f"source root does not exist: {root}")
    except OSError as exc:
        raise MigrationError(f"cannot inspect root {root}: {exc}") from exc
    root_kind = _kind(root_st.st_mode)
    if root_kind != "dir":
        raise MigrationError(f"source root must be a directory: {root}")
    entries: dict[str, dict[str, Any]] = {
        ".": {"kind": "dir", "signature": _sig(root_st), "xattrs": _xattrs(root)}
    }

    def visit(directory: Path, relative: str) -> None:
        try:
            children = sorted(os.scandir(directory), key=lambda entry: entry.name)
        except OSError as exc:
            raise MigrationError(f"cannot scan {directory}: {exc}") from exc
        for child in children:
            child_rel = child.name if relative == "." else f"{relative}/{child.name}"
            child_path = Path(child.path)
            try:
                child_st = child.stat(follow_symlinks=False)
            except OSError as exc:
                raise MigrationError(f"cannot inspect {child_path}: {exc}") from exc
            kind = _kind(child_st.st_mode)
            if kind == "file" and child_st.st_nlink > 1:
                raise MigrationError(f"hard-linked regular file is unsupported: {child_path}")
            entry: dict[str, Any] = {"kind": kind, "signature": _sig(child_st), "xattrs": _xattrs(child_path)}
            if kind == "symlink":
                try:
                    entry["linktarget"] = os.readlink(child_path)
                except OSError as exc:
                    raise MigrationError(f"cannot read symlink {child_path}: {exc}") from exc
            entries[child_rel] = entry
            if kind == "dir":
                visit(child_path, child_rel)

    visit(root, ".")
    return entries


def _validate_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MigrationError("plan must be a JSON object")
    if set(raw) != {"archive_root", "units", "authority", "metadata_policy"}:
        raise MigrationError("plan keys must be exactly archive_root, units, authority, metadata_policy")
    if raw["metadata_policy"] != METADATA_POLICY:
        raise MigrationError(f"metadata_policy must be exactly {METADATA_POLICY!r}")
    if not isinstance(raw["authority"], str) or not raw["authority"].strip():
        raise MigrationError("authority must be a non-empty string")
    archive_root = _lexical_absolute(raw["archive_root"], "archive_root")
    if not archive_root.exists() or not archive_root.is_dir():
        raise MigrationError(f"archive_root must be an existing directory: {archive_root}")
    archive_stat = _lstat(archive_root, "archive_root")
    if archive_stat.st_uid != os.geteuid():
        raise MigrationError("archive_root must be owned by the current user")
    if stat.S_IMODE(archive_stat.st_mode) & 0o077:
        raise MigrationError("archive_root must have no group/other permission bits")
    archive_real = archive_root.resolve()
    if not isinstance(raw["units"], list) or not raw["units"]:
        raise MigrationError("units must be a non-empty list")
    units: list[dict[str, str]] = []
    sources: list[Path] = []
    destinations: list[Path] = []
    for index, unit in enumerate(raw["units"]):
        if not isinstance(unit, dict) or set(unit) != {"source", "destination"}:
            raise MigrationError(f"unit {index} must contain exactly source and destination")
        source = _lexical_absolute(unit["source"], f"unit {index} source")
        destination = _lexical_absolute(unit["destination"], f"unit {index} destination")
        if destination == archive_root or not _under(destination, archive_root):
            raise MigrationError(f"destination must be below archive_root: {destination}")
        if not _under(destination.resolve(strict=False), archive_real):
            raise MigrationError(f"destination escapes archive_root through a symlink: {destination}")
        if source == destination or _under(source, destination) or _under(destination, source):
            raise MigrationError(f"source and destination overlap in unit {index}")
        if any(_under(source, other) or _under(other, source) for other in sources):
            raise MigrationError(f"source units overlap at unit {index}")
        if any(_under(destination, other) or _under(other, destination) for other in destinations):
            raise MigrationError(f"destination units overlap at unit {index}")
        sources.append(source)
        destinations.append(destination)
        units.append({"source": str(source), "destination": str(destination)})
    return {"schema": SCHEMA, "archive_root": str(archive_root), "authority": raw["authority"],
            "metadata_policy": METADATA_POLICY, "units": units}


def _unit_id(unit: dict[str, str]) -> str:
    return hashlib.sha256(f"{unit['source']}\0{unit['destination']}".encode()).hexdigest()[:20]


def _planned_target(linktarget: str, units: list[dict[str, str]]) -> str | None:
    if not os.path.isabs(linktarget):
        return None
    target = Path(os.path.normpath(linktarget))
    for unit in units:
        source = Path(unit["source"])
        if _under(target, source):
            relative = target.relative_to(source)
            return str(Path(unit["destination"]) / relative)
    return None


def _link_context(root: Path, relative: str, linktarget: str) -> str:
    """Resolve a link lexically from its containing directory, never following it."""
    parent = _path_for(root, relative).parent
    if os.path.isabs(linktarget):
        return os.path.normpath(linktarget)
    return os.path.normpath(str(parent / linktarget))


def _manifest_value(unit: dict[str, str], entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"schema": SCHEMA, "metadata_policy": METADATA_POLICY,
            "source": unit["source"], "destination": unit["destination"], "entries": entries}


def _load_json(path: Path) -> Any:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read state file {path}: {exc}") from exc


def _ensure_immutable(path: Path, value: Any) -> None:
    if path.exists():
        if _load_json(path) != value:
            raise MigrationError(f"immutable state mismatch: {path}")
    else:
        _atomic_json(path, value)


def _read_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError("record is not an object")
                    records.append(value)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise MigrationError(f"invalid ledger {path}: {exc}") from exc
    return records


def _path_for(root: Path, relative: str) -> Path:
    return root if relative == "." else root / relative


def _open_regular_nofollow(path: Path, expected: dict[str, int], context: str) -> tuple[int, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        before = os.fstat(fd)
    except OSError as exc:
        raise MigrationError(f"cannot open {context} safely {path}: {exc}") from exc
    if not stat.S_ISREG(before.st_mode) or not _same_sig(_sig(before), expected):
        os.close(fd)
        raise MigrationError(f"{context} changed before hashing: {path}")
    return fd, before


def _hash_regular(path: Path, expected: dict[str, int], context: str) -> str:
    fd, before = _open_regular_nofollow(path, expected, context)
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "rb", closefd=True) as handle:
            while True:
                block = handle.read(1024 * 1024)
                if not block:
                    break
                digest.update(block)
            try:
                os.fsync(handle.fileno())
            except OSError as exc:
                if exc.errno not in {errno.EINVAL, errno.ENOTSUP, errno.EOPNOTSUPP}:
                    raise MigrationError(f"cannot fsync {context} {path}: {exc}") from exc
            after = os.fstat(handle.fileno())
    except OSError as exc:
        raise MigrationError(f"cannot hash {context} {path}: {exc}") from exc
    if not _same_sig(_sig(before), _sig(after)) or not _same_sig(_sig(after), expected):
        raise MigrationError(f"{context} changed while hashing: {path}")
    return digest.hexdigest()


def _dest_inventory(root: Path) -> dict[str, dict[str, Any]]:
    return _inventory(root)


class Unit:
    def __init__(self, manager: "Migration", index: int, plan_unit: dict[str, str]):
        self.manager = manager
        self.index = index
        self.unit = plan_unit
        self.source = Path(plan_unit["source"])
        self.destination = Path(plan_unit["destination"])
        self.unit_id = _unit_id(plan_unit)
        self.prefix = f"unit-{self.unit_id}"
        self.unit_dir = manager.state_dir / self.prefix
        self.manifest_path = self.unit_dir / "manifest.json"
        self.status_path = self.unit_dir / "status.json"
        self.ledger_path = self.unit_dir / "ledger.jsonl"
        self.event_path = self.unit_dir / "events.jsonl"
        self.tombstone = self.source.with_name(f".{self.source.name}.xray-migration-{self.unit_id}.tombstone")

    def status(self) -> dict[str, Any]:
        if not self.status_path.exists():
            return {"stage": "new", "plan_hash": self.manager.plan_hash, "unit_id": self.unit_id}
        value = _load_json(self.status_path)
        if value.get("plan_hash") != self.manager.plan_hash or value.get("unit_id") != self.unit_id:
            raise MigrationError(f"status binding mismatch for {self.source}")
        return value

    def set_status(self, stage: str, **extra: Any) -> None:
        value = {"schema": SCHEMA, "plan_hash": self.manager.plan_hash, "unit_id": self.unit_id,
                 "source": str(self.source), "destination": str(self.destination), "tombstone": str(self.tombstone),
                 "stage": stage, "updated_at": time.time()}
        value.update(extra)
        _atomic_json(self.status_path, value)

    def event(self, event: str, **extra: Any) -> None:
        value = {"schema": SCHEMA, "plan_hash": self.manager.plan_hash, "unit_id": self.unit_id,
                 "event": event, "time": time.time()}
        value.update(extra)
        _append_json(self.event_path, value)
        print(f"unit={self.index} {event} flushed", flush=True)

    def ledger(self, event: str, **extra: Any) -> None:
        value = {"schema": SCHEMA, "plan_hash": self.manager.plan_hash, "unit_id": self.unit_id,
                 "event": event, "time": time.time()}
        value.update(extra)
        _append_json(self.ledger_path, value)

    def manifest(self) -> dict[str, Any]:
        return _load_json(self.manifest_path)

    def prepare_manifest(self, status: dict[str, Any]) -> dict[str, Any]:
        if self.manifest_path.exists():
            manifest = self.manifest()
            expected = _manifest_value(self.unit, manifest["entries"])
            if (manifest.get("plan_hash") != self.manager.plan_hash or
                    manifest.get("unit_id") != self.unit_id or
                    manifest.get("metadata_policy") != METADATA_POLICY):
                raise MigrationError(f"manifest binding mismatch for {self.source}")
            if manifest.get("source") != expected["source"] or manifest.get("destination") != expected["destination"]:
                raise MigrationError(f"manifest path mismatch for {self.source}")
            return manifest
        entries = _inventory(self.source)
        _validate_source_policy(entries, self.source)
        manifest = _manifest_value(self.unit, entries)
        manifest["plan_hash"] = self.manager.plan_hash
        manifest["unit_id"] = self.unit_id
        _ensure_immutable(self.manifest_path, manifest)
        self.set_status("inventory", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("inventory", entries=len(entries) - 1, bytes=self.bytes(entries))
        return manifest

    @staticmethod
    def bytes(entries: dict[str, dict[str, Any]]) -> int:
        return sum(int(entry["signature"]["size"]) for entry in entries.values() if entry["kind"] == "file")

    def check_source_unchanged(self, entries: dict[str, dict[str, Any]]) -> None:
        current = _inventory(self.source)
        _validate_source_policy(current, self.source)
        if set(current) != set(entries):
            raise MigrationError(f"source tree changed (entry set) before promotion: {self.source}")
        for relative, expected in entries.items():
            actual = current[relative]
            # This NFS server reports asynchronously updated recursive bytes as
            # directory st_size. Directory membership is checked above; compare
            # its stable identity/metadata, not that accounting value.
            fields = tuple(field for field in SIGNATURE_FIELDS
                           if expected["kind"] != "dir" or field != "size")
            unchanged = all(actual["signature"][field] == expected["signature"][field]
                            for field in fields)
            if actual["kind"] != expected["kind"] or not unchanged:
                raise MigrationError(f"source tree changed at {self.source / relative}")
            if expected["kind"] == "symlink" and actual["linktarget"] != expected["linktarget"]:
                raise MigrationError(f"source symlink changed at {self.source / relative}")

    def check_destination_empty_or_resume(self, *, initial: bool) -> None:
        if os.path.lexists(self.destination):
            if initial:
                raise MigrationError(f"destination must be absent at initial execution: {self.destination}")
            try:
                if not self.destination.is_dir() or self.destination.is_symlink():
                    raise MigrationError(f"destination is not an empty directory root: {self.destination}")
            except OSError as exc:
                raise MigrationError(f"cannot inspect destination {self.destination}: {exc}") from exc
        else:
            self.destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.mkdir(self.destination, 0o700)
            _fsync_parent(self.destination)

    def rewrite_symlinks(self, entries: dict[str, dict[str, Any]]) -> None:
        for relative, entry in entries.items():
            if entry["kind"] != "symlink":
                continue
            original = entry["linktarget"]
            mapped = _planned_target(original, self.manager.plan["units"])
            expected = mapped or original
            destination_path = _path_for(self.destination, relative)
            actual_st = _lstat(destination_path, "destination symlink")
            if not stat.S_ISLNK(actual_st.st_mode):
                raise MigrationError(f"destination symlink missing or wrong type: {destination_path}")
            actual_target = os.readlink(destination_path)
            if actual_target == expected:
                continue
            if mapped is None or actual_target != original:
                raise MigrationError(f"unexpected destination symlink target at {destination_path}")
            temporary = destination_path.with_name(f".{destination_path.name}.rewrite-{self.unit_id}")
            try:
                if os.path.lexists(temporary):
                    os.unlink(temporary)
                os.symlink(mapped, temporary)
                _restore_xattrs(temporary, entry.get("xattrs", {}))
                signature = entry["signature"]
                os.utime(temporary, ns=(signature["mtime_ns"], signature["mtime_ns"]), follow_symlinks=False)
                os.replace(temporary, destination_path)
                _fsync_parent(destination_path)
            except OSError as exc:
                try:
                    if os.path.lexists(temporary):
                        os.unlink(temporary)
                except OSError:
                    pass
                raise MigrationError(f"cannot rewrite symlink {destination_path}: {exc}") from exc
            self.ledger("symlink_rewritten", path=relative, original=original, mapped=mapped)

    @staticmethod
    def private_mode(relative: str, entry: dict[str, Any]) -> int | None:
        if entry["kind"] == "symlink":
            return None
        if entry["kind"] == "dir":
            return 0o700
        return stat.S_IMODE(entry["signature"]["mode"]) & 0o700

    def normalize_destination(self, entries: dict[str, dict[str, Any]]) -> None:
        """Apply private_archive metadata without needless receipt churn."""
        effective_uid = os.geteuid()
        effective_gid = os.getgid()
        for relative, entry in sorted(entries.items(), key=lambda item: item[0].count("/"), reverse=True):
            path = _path_for(self.destination, relative)
            st = _lstat(path, "destination entry")
            if _kind(st.st_mode) != entry["kind"]:
                raise MigrationError(f"destination type changed at {relative}")
            desired_mode = self.private_mode(relative, entry)
            try:
                if desired_mode is not None and stat.S_IMODE(st.st_mode) != desired_mode:
                    _chmod_nofollow(path, desired_mode, entry["kind"])
                if st.st_uid != effective_uid or st.st_gid != effective_gid:
                    os.chown(path, effective_uid, effective_gid, follow_symlinks=False)
                if st.st_mtime_ns != entry["signature"]["mtime_ns"]:
                    os.utime(path, ns=(entry["signature"]["mtime_ns"], entry["signature"]["mtime_ns"]),
                             follow_symlinks=False)
            except OSError as exc:
                raise MigrationError(f"cannot normalize destination metadata at {relative}: {exc}") from exc
            expected_xattrs = entry.get("xattrs", {})
            if _xattrs(path) != expected_xattrs:
                _restore_xattrs(path, expected_xattrs)

    def write_policy_receipt(self, entries: dict[str, dict[str, Any]]) -> None:
        source_modes: dict[str, int] = {}
        destination_modes: dict[str, int] = {}
        source_gids: dict[str, int] = {}
        destination_gids: dict[str, int] = {}
        for relative, entry in entries.items():
            source_mode = stat.S_IMODE(entry["signature"]["mode"])
            destination_mode = self.private_mode(relative, entry)
            source_modes[oct(source_mode)] = source_modes.get(oct(source_mode), 0) + 1
            if destination_mode is not None:
                destination_modes[oct(destination_mode)] = destination_modes.get(oct(destination_mode), 0) + 1
            else:
                destination_modes["symlink"] = destination_modes.get("symlink", 0) + 1
            source_gid = str(entry["signature"]["gid"])
            destination_gid = str(os.getgid())
            source_gids[source_gid] = source_gids.get(source_gid, 0) + 1
            destination_gids[destination_gid] = destination_gids.get(destination_gid, 0) + 1
        _ensure_immutable(self.unit_dir / "policy-receipt.json", {
            "schema": SCHEMA, "plan_hash": self.manager.plan_hash, "unit_id": self.unit_id,
            "metadata_policy": METADATA_POLICY,
            "source_uid": os.geteuid(), "destination_uid": os.geteuid(),
            "destination_gid": os.getgid(), "source_modes": source_modes,
            "destination_modes": destination_modes, "source_gids": source_gids,
            "destination_gids": destination_gids,
        })

    def verify_tree(self, entries: dict[str, dict[str, Any]], *, root_metadata: bool = True) -> dict[str, dict[str, Any]]:
        actual = _dest_inventory(self.destination)
        if set(actual) != set(entries):
            missing = sorted(set(entries) - set(actual))
            extra = sorted(set(actual) - set(entries))
            raise MigrationError(f"destination tree differs; missing={missing[:3]} extra={extra[:3]}")
        for relative, expected in entries.items():
            got = actual[relative]
            if got["kind"] != expected["kind"]:
                raise MigrationError(f"destination type mismatch at {relative}")
            if relative == ".":
                if not root_metadata:
                    continue
                expected_root = {"mode": 0o700, "mtime_ns": expected["signature"]["mtime_ns"],
                                 "uid": os.geteuid(), "gid": os.getgid()}
                for field, value in expected_root.items():
                    if (stat.S_IMODE(got["signature"][field]) if field == "mode" else got["signature"][field]) != value:
                        raise MigrationError(f"destination root metadata mismatch: {field}")
                if got.get("xattrs", {}) != expected.get("xattrs", {}):
                    raise MigrationError("destination root xattr/ACL mismatch")
                continue
            if expected["kind"] in {"file", "dir"}:
                expected_meta = {"mode": self.private_mode(relative, expected),
                                 "mtime_ns": expected["signature"]["mtime_ns"],
                                 "uid": os.geteuid(), "gid": os.getgid()}
                for field, value in expected_meta.items():
                    actual_value = stat.S_IMODE(got["signature"][field]) if field == "mode" else got["signature"][field]
                    if actual_value != value:
                        raise MigrationError(f"destination metadata mismatch at {relative}: {field}")
                if expected["kind"] == "file" and got["signature"]["size"] != expected["signature"]["size"]:
                    raise MigrationError(f"destination size mismatch at {relative}")
                if got.get("xattrs", {}) != expected.get("xattrs", {}):
                    raise MigrationError(f"destination xattr/ACL mismatch at {relative}")
            else:
                expected_target = _planned_target(expected["linktarget"], self.manager.plan["units"]) or expected["linktarget"]
                actual_linktarget = got.get("linktarget")
                if os.path.isabs(expected["linktarget"]):
                    expected_linktarget = expected_target
                else:
                    expected_linktarget = expected["linktarget"]
                if actual_linktarget != expected_linktarget:
                    raise MigrationError(f"destination symlink mismatch at {relative}")
                original_context = _link_context(self.source, relative, expected["linktarget"])
                expected_context = _planned_target(original_context, self.manager.plan["units"]) or original_context
                actual_context = _link_context(self.destination, relative, actual_linktarget)
                if actual_context != expected_context:
                    raise MigrationError(f"destination symlink context mismatch at {relative}")
                try:
                    source_kind = _kind(_path_for(self.source, relative).stat().st_mode)
                except FileNotFoundError:
                    try:
                        _path_for(self.destination, relative).stat()
                    except FileNotFoundError:
                        source_kind = None
                    except OSError as exc:
                        raise MigrationError(f"unresolved destination symlink target at {relative}: {exc}") from exc
                    else:
                        raise MigrationError(f"dangling source symlink became resolved at {relative}")
                except OSError as exc:
                    raise MigrationError(f"unresolved source symlink target at {relative}: {exc}") from exc
                if source_kind is None:
                    destination_kind = None
                else:
                    try:
                        destination_kind = _kind(_path_for(self.destination, relative).stat().st_mode)
                    except OSError as exc:
                        raise MigrationError(f"unresolved destination symlink target at {relative}: {exc}") from exc
                if source_kind != destination_kind:
                    raise MigrationError(f"symlink target type mismatch at {relative}")
                for field, value in (("uid", os.geteuid()), ("gid", os.getgid()),
                                     ("mtime_ns", expected["signature"]["mtime_ns"])):
                    if got["signature"][field] != value:
                        raise MigrationError(f"destination symlink metadata mismatch at {relative}: {field}")
                if got.get("xattrs", {}) != expected.get("xattrs", {}):
                    raise MigrationError(f"destination symlink xattr/ACL mismatch at {relative}")
        return actual

    def verify_files(self, entries: dict[str, dict[str, Any]], *, force_hash: bool) -> int:
        records = _read_ledger(self.ledger_path)
        prior = {record.get("path"): record for record in records if record.get("event") == "file_verified"}
        verified_bytes = 0
        for relative, expected in entries.items():
            if expected["kind"] != "file":
                continue
            source_path = _path_for(self.source, relative)
            destination_path = _path_for(self.destination, relative)
            source_sig = _sig(_lstat(source_path, "source file"))
            destination_sig = _sig(_lstat(destination_path, "destination file"))
            previous = prior.get(relative)
            reusable = (not force_hash and previous is not None and
                        _same_sig(source_sig, previous["source_signature"]) and
                        _same_sig(destination_sig, previous["destination_signature"]))
            if reusable:
                digest = previous["sha256"]
            else:
                source_digest = _hash_regular(source_path, expected["signature"], "source file")
                destination_digest = _hash_regular(destination_path, destination_sig, "destination file")
                if source_digest != destination_digest:
                    raise MigrationError(f"content mismatch at {relative}")
                digest = source_digest
                self.ledger("file_verified", path=relative, source_signature=source_sig,
                            destination_signature=destination_sig, sha256=digest)
                if expected["signature"]["size"] >= LARGE_HASH_BYTES:
                    self.event("largehash", path=relative, bytes=expected["signature"]["size"])
            verified_bytes += expected["signature"]["size"]
        return verified_bytes

    def verify_complete(self, manifest: dict[str, Any]) -> None:
        entries = manifest["entries"]
        self.check_source_unchanged(entries)
        self.rewrite_symlinks(entries)
        self.normalize_destination(entries)
        self.verify_tree(entries, root_metadata=False)
        self.verify_files(entries, force_hash=False)
        self.check_source_unchanged(entries)
        # A second exact-tree check catches any metadata or link change during hashing.
        self.verify_tree(entries)
        self.write_policy_receipt(entries)

    def verify_destination_payload(self, manifest: dict[str, Any]) -> None:
        """Verify the promoted destination using durable source/destination receipts."""
        policy_path = self.unit_dir / "policy-receipt.json"
        if not policy_path.exists():
            raise MigrationError(f"missing durable metadata policy receipt: {policy_path}")
        policy = _load_json(policy_path)
        if (policy.get("schema") != SCHEMA or policy.get("plan_hash") != self.manager.plan_hash or
                policy.get("unit_id") != self.unit_id or policy.get("metadata_policy") != METADATA_POLICY):
            raise MigrationError(f"metadata policy receipt binding mismatch: {policy_path}")
        self.verify_tree(manifest["entries"])
        records = {record.get("path"): record for record in _read_ledger(self.ledger_path)
                   if record.get("event") == "file_verified"}
        for relative, entry in manifest["entries"].items():
            if entry["kind"] != "file":
                continue
            record = records.get(relative)
            if record is None:
                raise MigrationError(f"missing durable file receipt at {relative}")
            destination_path = _path_for(self.destination, relative)
            destination_sig = _sig(_lstat(destination_path, "destination file"))
            if not _same_sig(destination_sig, record["destination_signature"]):
                raise MigrationError(f"destination file signature changed at {relative}")
            # The receipt was created only after a complete O_NOFOLLOW hash;
            # unchanged source/destination signatures make it reusable on a
            # crash resume without rereading the full archive.

    def verify_destination_receipt(self, relative: str, record: dict[str, Any]) -> None:
        path = _path_for(self.destination, relative)
        destination_sig = _sig(_lstat(path, "destination file"))
        if not _same_sig(destination_sig, record["destination_signature"]):
            raise MigrationError(f"destination file signature changed at {relative}")

    def copy_and_verify(self, manifest: dict[str, Any], status: dict[str, Any]) -> None:
        entries = manifest["entries"]
        self.check_source_unchanged(entries)
        self.check_destination_empty_or_resume(initial=status["stage"] in {"new", "inventory"})
        self.set_status("copy-start", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("copy-start", source=str(self.source), destination=str(self.destination))
        try:
            subprocess.run(["rsync", "-rltHXS", "--ignore-existing", f"{self.source}/", f"{self.destination}/"], check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            raise MigrationError(f"rsync failed for {self.source}: {exc}") from exc
        self.set_status("copied", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("copied", bytes=self.bytes(entries))
        self.verify_complete(manifest)
        self.set_status("verified", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("verified", bytes=self.bytes(entries))

    def verify_promoted_link(self) -> None:
        st = _lstat(self.source, "promoted source link")
        if not stat.S_ISLNK(st.st_mode) or os.readlink(self.source) != str(self.destination):
            raise MigrationError(f"promoted source is not the expected link: {self.source}")

    def promote(self, manifest: dict[str, Any]) -> None:
        status = self.status()
        stage = status["stage"]
        if stage == "verified":
            if os.path.lexists(self.tombstone):
                raise MigrationError(f"unexpected pre-existing tombstone: {self.tombstone}")
            os.rename(self.source, self.tombstone)
            _fsync_parent(self.source)
            self.set_status("renamed", entries=len(manifest["entries"]) - 1, bytes=self.bytes(manifest["entries"]))
            self.event("renamed", tombstone=str(self.tombstone))
            stage = "renamed"
        elif stage == "renamed":
            if os.path.lexists(self.source) and not (self.source.is_symlink() and os.readlink(self.source) == str(self.destination)):
                raise MigrationError(f"source unexpectedly exists during rename recovery: {self.source}")
            if not os.path.lexists(self.tombstone) and not os.path.islink(self.source):
                raise MigrationError(f"tombstone missing during rename recovery: {self.tombstone}")
        if stage == "renamed" and not os.path.islink(self.source):
            if os.path.lexists(self.source):
                raise MigrationError(f"cannot create promotion link over existing path: {self.source}")
            os.symlink(self.destination, self.source)
            _fsync_parent(self.source)
            self.set_status("promoted", entries=len(manifest["entries"]) - 1, bytes=self.bytes(manifest["entries"]))
            self.event("promoted", source=str(self.source), destination=str(self.destination))
        self.verify_promoted_link()

    def cleanup(self, manifest: dict[str, Any]) -> None:
        status = self.status()
        if status["stage"] == "promoted":
            self.set_status("cleaning", entries=len(manifest["entries"]) - 1, bytes=self.bytes(manifest["entries"]))
            self.event("cleaning")
        elif status["stage"] not in {"cleaning", "cleaned", "complete"}:
            raise MigrationError(f"cannot clean unit at stage {status['stage']}")
        self.verify_promoted_link()
        self.verify_destination_payload(manifest)
        if self.status()["stage"] in {"cleaned", "complete"}:
            if os.path.lexists(self.tombstone):
                raise MigrationError(f"tombstone remains after cleanup stage: {self.tombstone}")
            return
        records = _read_ledger(self.ledger_path)
        verified = {record["path"]: record for record in records
                    if record.get("event") == "file_verified"}
        deleted = {record["path"] for record in records if record.get("event") == "deleted"}
        intents = {record["path"] for record in records if record.get("event") == "delete-intent"}
        entries = manifest["entries"]
        if not os.path.lexists(self.tombstone):
            if "." not in deleted and "." not in intents:
                raise MigrationError(f"tombstone missing without durable cleanup ledger: {self.tombstone}")
            if "." in intents and "." not in deleted:
                self.ledger("deleted", path=".", recovered=True)
                deleted.add(".")
        else:
            current = _inventory(self.tombstone)
            expected_paths = set(entries)
            if not set(current).issubset(expected_paths):
                raise MigrationError(f"unknown tombstone entries: {sorted(set(current) - expected_paths)[:3]}")
            # A durable delete-intent makes a missing path recoverable: the
            # process may have crashed after unlink/rmdir but before appending
            # the completion record.  Any other missing path is fatal.
            missing = expected_paths - set(current) - deleted - intents
            if missing:
                raise MigrationError(f"tombstone entries missing without delete ledger: {sorted(missing)[:3]}")
            for relative in sorted(entries, key=lambda item: (item.count("/"), item), reverse=True):
                path = _path_for(self.tombstone, relative)
                if relative in deleted:
                    continue
                entry = entries[relative]
                if not os.path.lexists(path):
                    if relative in intents:
                        if entry["kind"] == "file":
                            record = verified.get(relative)
                            if record is None:
                                raise MigrationError(f"missing destination receipt for interrupted deletion: {relative}")
                            self.verify_destination_receipt(relative, record)
                        self.ledger("deleted", path=relative, recovered=True)
                        deleted.add(relative)
                        continue
                    raise MigrationError(f"tombstone path unexpectedly missing: {path}")
                st = _lstat(path, "tombstone entry")
                if _kind(st.st_mode) != entry["kind"]:
                    raise MigrationError(f"tombstone type changed at {relative}")
                if entry["kind"] in {"file", "symlink"} and not _same_sig(_sig(st), entry["signature"]):
                    raise MigrationError(f"tombstone file changed at {relative}")
                if entry["kind"] == "symlink" and os.readlink(path) != entry["linktarget"]:
                    raise MigrationError(f"tombstone symlink changed at {relative}")
                if _xattrs(path) != entry.get("xattrs", {}):
                    raise MigrationError(f"tombstone xattr/ACL changed at {relative}")
                if entry["kind"] == "file":
                    record = verified.get(relative)
                    if record is None:
                        raise MigrationError(f"missing destination receipt before deleting {relative}")
                    self.verify_destination_receipt(relative, record)
                self.ledger("delete-intent", path=relative)
                try:
                    if entry["kind"] == "dir":
                        os.rmdir(path)
                    else:
                        os.unlink(path)
                except OSError as exc:
                    raise MigrationError(f"cannot delete enumerated tombstone path {path}: {exc}") from exc
                self.ledger("deleted", path=relative)
        self.verify_promoted_link()
        if os.path.lexists(self.tombstone):
            raise MigrationError(f"tombstone was not fully removed: {self.tombstone}")
        self.set_status("cleaned", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("cleaned")
        self.set_status("complete", entries=len(entries) - 1, bytes=self.bytes(entries))
        self.event("complete")

    def run(self) -> None:
        status = self.status()
        stage = status["stage"]
        if stage in {"complete", "cleaned"}:
            self.verify_promoted_link()
            self.verify_destination_payload(self.prepare_manifest(status))
            return
        manifest = self.prepare_manifest(status)
        if stage in {"new", "inventory", "copy-start", "copied"}:
            self.copy_and_verify(manifest, status)
        elif stage == "verified":
            # Recheck every source and destination byte before promotion.
            # A crash can leave the source renamed while the status file still
            # says verified.  The durable tombstone is the explicit recovery
            # marker for that narrow window.
            if os.path.lexists(self.tombstone) and not os.path.lexists(self.source):
                self.set_status("renamed", entries=len(manifest["entries"]) - 1, bytes=self.bytes(manifest["entries"]))
                self.event("renamed-recovered", tombstone=str(self.tombstone))
            else:
                self.verify_complete(manifest)
        elif stage in {"renamed", "promoted", "cleaning"}:
            if stage == "renamed" and os.path.islink(self.source):
                self.set_status("promoted", entries=len(manifest["entries"]) - 1, bytes=self.bytes(manifest["entries"]))
                self.event("promoted-recovered")
        else:
            raise MigrationError(f"unknown unit stage {stage!r}")
        stage = self.status()["stage"]
        if stage == "verified":
            self.promote(manifest)
        elif stage in {"renamed"}:
            self.promote(manifest)
        if self.status()["stage"] in {"promoted", "cleaning"}:
            self.cleanup(manifest)


class Migration:
    def __init__(self, plan: dict[str, Any], state_dir: Path):
        self.plan = plan
        self.plan_hash = _plan_hash(plan)
        self.state_dir = state_dir

    def plan_only(self) -> dict[str, Any]:
        units = []
        for index, unit in enumerate(self.plan["units"]):
            entries = _inventory(Path(unit["source"]))
            _validate_source_policy(entries, Path(unit["source"]))
            destination = Path(unit["destination"])
            if os.path.lexists(destination):
                raise MigrationError(f"destination must be absent for plan validation: {destination}")
            units.append({"index": index, "source": unit["source"], "destination": unit["destination"],
                          "entries": len(entries) - 1, "bytes": Unit.bytes(entries)})
        return {"schema": SCHEMA, "plan_hash": self.plan_hash, "authority": self.plan["authority"], "units": units}

    def execute(self) -> None:
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        _chmod_nofollow(self.state_dir, 0o700, "dir")
        lock_path = self.state_dir / "migration.lock"
        with lock_path.open("a+") as lock:
            _chmod_nofollow(lock_path, 0o600, "file")
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise MigrationError(f"another migration is using {self.state_dir}") from exc
            binding = {"schema": SCHEMA, "plan_hash": self.plan_hash, "plan": self.plan}
            _ensure_immutable(self.state_dir / "plan-binding.json", binding)
            self.plan_hash = binding["plan_hash"]
            _append_json(self.state_dir / "events.jsonl", {"event": "execute-start", "plan_hash": self.plan_hash, "time": time.time()})
            for index, plan_unit in enumerate(self.plan["units"]):
                Unit(self, index, plan_unit).run()
            _atomic_json(self.state_dir / "verified-manifest.json", {
                "schema": SCHEMA, "plan_hash": self.plan_hash, "units": [
                    {"unit_id": _unit_id(unit), "source": unit["source"], "destination": unit["destination"], "stage": "complete"}
                    for unit in self.plan["units"]
                ]
            })
            _append_json(self.state_dir / "events.jsonl", {"event": "execute-complete", "plan_hash": self.plan_hash, "time": time.time()})


def _load_plan(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationError(f"cannot read plan {path}: {exc}") from exc
    return _validate_plan(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--execute", action="store_true", help="perform copy, promotion, and cleanup")
    args = parser.parse_args(argv)
    try:
        plan = _load_plan(args.plan)
        migration = Migration(plan, args.state_dir)
        if not args.execute:
            print(_canonical(migration.plan_only()))
        else:
            migration.execute()
            print(_canonical({"status": "complete", "plan_hash": migration.plan_hash}))
        return 0
    except (MigrationError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
