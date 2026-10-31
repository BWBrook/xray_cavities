#!/usr/bin/env python3
"""Resume the frozen migration after the audited C-HI NFS device transition."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import importlib.util
import os
from pathlib import Path
import socket
import stat
import subprocess
import sys
import time
from typing import Any


STAGE = Path(__file__).resolve().parents[2]
STATE = STAGE / "state"
PLAN = STAGE / "migration_plan.json"
INSPECTION = STAGE / "source_signature_inspection_n001_20261031.json"
EVIDENCE = STAGE / "device_transition_20261031"
RECEIPT = EVIDENCE / "transition-receipt.json"
UNIT_INDEX = 8
UNIT_ID = "e9730c61823192c5937f"
OLD_DEVICE_FROM_MANIFEST = 46
CURRENT_DEVICE = 45
EXPECTED_ENTRIES = 7129
VERIFICATION_EPOCH = "c-hi-device-rebind-20261031"
SCRATCH_MOUNT = {
    "source": "<private-ip>:/hpc-kunanyi/scratch/bwbrook",
    "target": "/scratch/bwbrook",
    "fstype": "nfs4",
    "fsroot": "/",
}
HOME_MOUNT = {
    "source": "<private-ip>:/hpc-kunanyi/home/bwbrook",
    "target": "/u/bwbrook",
    "fstype": "nfs4",
    "fsroot": "/",
}

sys.dont_write_bytecode = True


class TransitionError(RuntimeError):
    pass


def _load_frozen_module():
    path = STAGE / "scripts/kunanyi/migrate_xray_scratch_to_home.py"
    spec = importlib.util.spec_from_file_location("frozen_xray_migration", path)
    if spec is None or spec.loader is None:
        raise TransitionError(f"cannot import frozen migration module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


frozen = _load_frozen_module()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_regular_file(path: Path, *, mode: int | None = None) -> None:
    observed = path.lstat()
    if not stat.S_ISREG(observed.st_mode) or path.is_symlink() or observed.st_uid != os.geteuid():
        raise TransitionError(f"unsafe evidence file identity: {path}")
    if mode is not None and stat.S_IMODE(observed.st_mode) != mode:
        raise TransitionError(f"unsafe evidence file mode at {path}: {oct(stat.S_IMODE(observed.st_mode))}")


def _require_evidence_dir() -> None:
    EVIDENCE.mkdir(mode=0o700, parents=False, exist_ok=True)
    observed = EVIDENCE.lstat()
    if (not stat.S_ISDIR(observed.st_mode) or EVIDENCE.is_symlink() or observed.st_uid != os.geteuid() or
            stat.S_IMODE(observed.st_mode) & 0o077):
        raise TransitionError(f"unsafe transition evidence directory: {EVIDENCE}")


def _canonical_hash(value: Any) -> str:
    return hashlib.sha256(frozen._canonical(value).encode()).hexdigest()


def _parse_findmnt_output(output: str, path: Path) -> dict[str, str]:
    lines = [line for line in output.splitlines() if line.strip()]
    if len(lines) != 1:
        raise TransitionError(f"findmnt returned {len(lines)} records for {path}")
    fields = lines[0].split()
    if len(fields) != 4:
        raise TransitionError(f"findmnt returned {len(fields)} fields for {path}")
    return dict(zip(("source", "target", "fstype", "fsroot"), fields, strict=True))


def _find_mount(path: Path) -> dict[str, str]:
    result = subprocess.run(
        ["findmnt", "-n", "-r", "-T", str(path), "-o", "SOURCE,TARGET,FSTYPE,FSROOT"],
        text=True,
        capture_output=True,
    )
    if result.returncode:
        raise TransitionError(f"findmnt failed for {path}: {result.stderr.strip()}")
    return _parse_findmnt_output(result.stdout, path)


def _require_mounts(source: Path, destination: Path) -> dict[str, dict[str, str]]:
    observed = {"scratch": _find_mount(source), "home": _find_mount(destination)}
    if observed["scratch"] != SCRATCH_MOUNT:
        raise TransitionError(f"scratch mount identity mismatch: {observed['scratch']}")
    if observed["home"] != HOME_MOUNT:
        raise TransitionError(f"home mount identity mismatch: {observed['home']}")
    return observed


def _stable_inventory(entries: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    stable = copy.deepcopy(entries)
    for entry in stable.values():
        if entry["kind"] == "dir":
            entry["signature"].pop("size", None)
    return stable


def _validate_transition(
    expected: dict[str, dict[str, Any]],
    actual: dict[str, dict[str, Any]],
    *,
    after_rename: bool = False,
) -> None:
    if len(expected) != EXPECTED_ENTRIES:
        raise TransitionError(f"unexpected manifest entry count: {len(expected)}")
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        added = sorted(set(actual) - set(expected))
        raise TransitionError(f"source entry set changed; missing={missing[:3]} added={added[:3]}")
    for relative, wanted in expected.items():
        got = actual[relative]
        if wanted["kind"] != got["kind"]:
            raise TransitionError(f"source type changed at {relative}")
        if wanted.get("xattrs", {}) != got.get("xattrs", {}):
            raise TransitionError(f"source xattrs changed at {relative}")
        if wanted["kind"] == "symlink" and wanted.get("linktarget") != got.get("linktarget"):
            raise TransitionError(f"source symlink changed at {relative}")
        wanted_sig = wanted["signature"]
        got_sig = got["signature"]
        if wanted_sig["dev"] != OLD_DEVICE_FROM_MANIFEST or got_sig["dev"] != CURRENT_DEVICE:
            raise TransitionError(
                f"source device transition mismatch at {relative}: {wanted_sig['dev']} -> {got_sig['dev']}"
            )
        if after_rename and wanted["kind"] == "dir":
            fields: tuple[str, ...] = ()
        else:
            fields = tuple(
                field for field in frozen.SIGNATURE_FIELDS
                if field != "dev" and not (wanted["kind"] == "dir" and field == "size")
            )
        changed = [field for field in fields if wanted_sig[field] != got_sig[field]]
        if changed:
            raise TransitionError(f"source non-device signature changed at {relative}: {changed}")


def _adjust_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    adjusted = copy.deepcopy(manifest)
    for relative, entry in adjusted["entries"].items():
        if entry["signature"]["dev"] != OLD_DEVICE_FROM_MANIFEST:
            raise TransitionError(f"manifest device is not uniformly 46 at {relative}")
        entry["signature"]["dev"] = CURRENT_DEVICE
    return adjusted


def _receipt_core(
    unit: Any,
    manifest: dict[str, Any],
    actual: dict[str, dict[str, Any]],
    mounts: dict[str, dict[str, str]],
) -> dict[str, Any]:
    _require_regular_file(INSPECTION)
    return {
        "schema": 1,
        "scope": "exact-c-hi-unit-device-transition",
        "plan_hash": unit.manager.plan_hash,
        "unit_index": UNIT_INDEX,
        "unit_id": unit.unit_id,
        "source": str(unit.source),
        "destination": str(unit.destination),
        "manifest_sha256": _sha256(unit.manifest_path),
        "inspection_sha256": _sha256(INSPECTION),
        "old_device_from_manifest": OLD_DEVICE_FROM_MANIFEST,
        "current_device_observed": CURRENT_DEVICE,
        "entry_count": len(actual),
        "stable_source_inventory_sha256": _canonical_hash(_stable_inventory(actual)),
        "directory_size_excluded_as_in_frozen_policy": True,
        "mounts": mounts,
        "verification_epoch": VERIFICATION_EPOCH,
    }


def _load_or_create_receipt(core: dict[str, Any]) -> dict[str, Any]:
    _require_evidence_dir()
    if RECEIPT.exists():
        _require_regular_file(RECEIPT, mode=0o600)
        receipt = frozen._load_json(RECEIPT)
        observed_core = {key: receipt.get(key) for key in core}
        if observed_core != core or receipt.get("core_sha256") != _canonical_hash(core):
            raise TransitionError("immutable device-transition receipt does not match live evidence")
        return receipt
    receipt = dict(core)
    receipt.update({"core_sha256": _canonical_hash(core), "created_at": time.time(),
                    "allocation_host": socket.gethostname()})
    frozen._ensure_immutable(RECEIPT, receipt)
    return receipt


def _require_receipt_binding(unit: Any, manifest: dict[str, Any]) -> dict[str, Any]:
    if not RECEIPT.exists():
        raise TransitionError("device-transition receipt is missing")
    _require_regular_file(RECEIPT, mode=0o600)
    _require_regular_file(INSPECTION)
    receipt = frozen._load_json(RECEIPT)
    required = {
        "plan_hash": unit.manager.plan_hash,
        "unit_id": UNIT_ID,
        "source": str(unit.source),
        "destination": str(unit.destination),
        "old_device_from_manifest": OLD_DEVICE_FROM_MANIFEST,
        "current_device_observed": CURRENT_DEVICE,
        "verification_epoch": VERIFICATION_EPOCH,
        "manifest_sha256": _sha256(unit.manifest_path),
        "inspection_sha256": _sha256(INSPECTION),
        "entry_count": EXPECTED_ENTRIES,
        "mounts": {"scratch": SCRATCH_MOUNT, "home": HOME_MOUNT},
        "scope": "exact-c-hi-unit-device-transition",
        "unit_index": UNIT_INDEX,
        "directory_size_excluded_as_in_frozen_policy": True,
    }
    if any(receipt.get(key) != value for key, value in required.items()):
        raise TransitionError("device-transition receipt binding mismatch")
    if receipt.get("stable_source_inventory_sha256") is None:
        raise TransitionError("device-transition receipt lacks its stable inventory digest")
    core = {key: value for key, value in receipt.items()
            if key not in {"core_sha256", "created_at", "allocation_host"}}
    if receipt.get("core_sha256") != _canonical_hash(core):
        raise TransitionError("device-transition receipt core hash mismatch")
    return receipt


class ReboundDeviceUnit(frozen.Unit):
    def __init__(self, manager: Any, index: int, plan_unit: dict[str, str]):
        super().__init__(manager, index, plan_unit)
        if index != UNIT_INDEX or self.unit_id != UNIT_ID:
            raise TransitionError(f"device-transition unit binding mismatch: index={index} id={self.unit_id}")
        self.transition_receipt_sha256: str | None = None

    def _evidence_root(self, status: dict[str, Any]) -> Path | None:
        stage = status["stage"]
        if stage in {"new", "inventory", "copy-start", "copied", "verified"}:
            if os.path.lexists(self.tombstone) and not os.path.lexists(self.source):
                return self.tombstone
            return self.source
        if stage in {"renamed", "promoted", "cleaning"}:
            return self.tombstone
        if stage in {"cleaned", "complete"}:
            return None
        raise TransitionError(f"unsupported transition stage: {stage}")

    def prepare_manifest(self, status: dict[str, Any]) -> dict[str, Any]:
        manifest = super().prepare_manifest(status)
        if (manifest.get("plan_hash") != self.manager.plan_hash or manifest.get("unit_id") != UNIT_ID or
                len(manifest["entries"]) != EXPECTED_ENTRIES):
            raise TransitionError("C-HI immutable manifest binding mismatch")
        root = self._evidence_root(status)
        renamed_evidence = root == self.tombstone and root is not None and os.path.lexists(root)
        if status["stage"] == "cleaning":
            receipt = _require_receipt_binding(self, manifest)
            _require_mounts(self.source.parent, self.destination)
        elif renamed_evidence or status["stage"] in {"renamed", "promoted"}:
            if root is None or not os.path.lexists(root):
                raise TransitionError("post-rename tombstone evidence is missing")
            actual = frozen._inventory(root)
            frozen._validate_source_policy(actual, root)
            _validate_transition(manifest["entries"], actual, after_rename=True)
            _require_mounts(root, self.destination)
            receipt = _require_receipt_binding(self, manifest)
        elif status["stage"] in {"new", "inventory", "copy-start", "copied", "verified"}:
            if root is None:
                raise TransitionError("pre-promotion source evidence is missing")
            actual = frozen._inventory(root)
            frozen._validate_source_policy(actual, root)
            _validate_transition(manifest["entries"], actual)
            mounts = _require_mounts(root, self.destination)
            receipt = _load_or_create_receipt(_receipt_core(self, manifest, actual, mounts))
        else:
            receipt = _require_receipt_binding(self, manifest)
            _require_mounts(self.source.parent, self.destination)
        self.transition_receipt_sha256 = _sha256(RECEIPT)
        return _adjust_manifest(manifest)

    def verify_files(self, entries: dict[str, dict[str, Any]], *, force_hash: bool) -> int:
        if self.transition_receipt_sha256 is None:
            raise TransitionError("device-transition receipt was not established before hashing")
        records = frozen._read_ledger(self.ledger_path)
        prior = {
            record.get("path"): record
            for record in records
            if (record.get("event") == "file_verified" and
                record.get("verification_epoch") == VERIFICATION_EPOCH and
                record.get("transition_receipt_sha256") == self.transition_receipt_sha256)
        }
        verified_bytes = 0
        for relative, expected in entries.items():
            if expected["kind"] != "file":
                continue
            source_path = frozen._path_for(self.source, relative)
            destination_path = frozen._path_for(self.destination, relative)
            source_sig = frozen._sig(frozen._lstat(source_path, "source file"))
            destination_sig = frozen._sig(frozen._lstat(destination_path, "destination file"))
            previous = prior.get(relative)
            reusable = (
                previous is not None and
                frozen._same_sig(source_sig, previous["source_signature"]) and
                frozen._same_sig(destination_sig, previous["destination_signature"])
            )
            if not reusable:
                source_digest = frozen._hash_regular(source_path, expected["signature"], "source file")
                destination_digest = frozen._hash_regular(destination_path, destination_sig, "destination file")
                if source_digest != destination_digest:
                    raise frozen.MigrationError(f"content mismatch at {relative}")
                self.ledger(
                    "file_verified",
                    path=relative,
                    source_signature=source_sig,
                    destination_signature=destination_sig,
                    sha256=source_digest,
                    verification_epoch=VERIFICATION_EPOCH,
                    transition_receipt_sha256=self.transition_receipt_sha256,
                )
                if expected["signature"]["size"] >= frozen.LARGE_HASH_BYTES:
                    self.event("largehash", path=relative, bytes=expected["signature"]["size"])
            verified_bytes += expected["signature"]["size"]
        return verified_bytes

    def verify_complete(self, manifest: dict[str, Any]) -> None:
        entries = manifest["entries"]
        self.check_source_unchanged(entries)
        self.rewrite_symlinks(entries)
        self.normalize_destination(entries)
        self.verify_tree(entries, root_metadata=False)
        self.verify_files(entries, force_hash=True)
        self.check_source_unchanged(entries)
        self.verify_tree(entries)
        self.write_policy_receipt(entries)


class DeviceTransitionMigration(frozen.Migration):
    def execute(self) -> None:
        self.state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        frozen._chmod_nofollow(self.state_dir, 0o700, "dir")
        lock_path = self.state_dir / "migration.lock"
        with lock_path.open("a+") as lock:
            frozen._chmod_nofollow(lock_path, 0o600, "file")
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise frozen.MigrationError(f"another migration is using {self.state_dir}") from exc
            binding = {"schema": frozen.SCHEMA, "plan_hash": self.plan_hash, "plan": self.plan}
            frozen._ensure_immutable(self.state_dir / "plan-binding.json", binding)
            self.plan_hash = binding["plan_hash"]
            frozen._append_json(
                self.state_dir / "events.jsonl",
                {"event": "device-transition-execute-start", "plan_hash": self.plan_hash, "time": time.time()},
            )
            for index, plan_unit in enumerate(self.plan["units"]):
                unit_class = ReboundDeviceUnit if index == UNIT_INDEX else frozen.Unit
                unit_class(self, index, plan_unit).run()
            frozen._atomic_json(
                self.state_dir / "verified-manifest.json",
                {
                    "schema": frozen.SCHEMA,
                    "plan_hash": self.plan_hash,
                    "units": [
                        {
                            "unit_id": frozen._unit_id(unit),
                            "source": unit["source"],
                            "destination": unit["destination"],
                            "stage": "complete",
                        }
                        for unit in self.plan["units"]
                    ],
                },
            )
            frozen._append_json(
                self.state_dir / "events.jsonl",
                {"event": "device-transition-execute-complete", "plan_hash": self.plan_hash, "time": time.time()},
            )


def main() -> int:
    try:
        plan = frozen._load_plan(PLAN)
        migration = DeviceTransitionMigration(plan, STATE)
        migration.execute()
        print(frozen._canonical({"status": "complete", "plan_hash": migration.plan_hash}))
        return 0
    except (TransitionError, frozen.MigrationError, OSError, subprocess.SubprocessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
