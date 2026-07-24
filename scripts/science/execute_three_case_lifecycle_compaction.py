#!/usr/bin/env python3
"""Fail-closed executor for the approved Goal 047 lifecycle compaction.

The production command is deliberately frozen to one approved Goal 046
ledger.  Library-level policy injection exists only so the safety properties
can be tested against small synthetic trees; the CLI cannot weaken counts,
hashes, job gates, locking, or post-delete validation.

Guarantees are conditional on the recorded single-owner/no-out-of-band-writer
assumption.  Within that boundary the executor uses no-follow descriptors,
holds every candidate open through hashing and unlink, and performs no
mutation until all global gates have passed.
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import datetime as dt
import errno
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence


APPROVED_LEDGER_SHA256 = (
    "df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92"
)
APPROVED_HDF5_COUNT = 148
APPROVED_XMF_COUNT = 148
APPROVED_ROW_COUNT = 296
APPROVED_ALLOCATED_BYTES = 6_845_659_111_424
CONFIRMATION_TOKEN = (
    "BARRY_APPROVED_GOAL047_"
    f"{APPROVED_LEDGER_SHA256}_DELETE_EXACT_296_ROWS_"
    "6845659111424_ALLOCATED_BYTES"
)
PRODUCTION_STAGE_ROOT = Path(
    "/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction_retry1"
)
PRODUCTION_EVIDENCE_ROOT = Path(
    "/scratch/bwbrook/xray_cavities_analysis/"
    "2026-07-24-three-case-lifecycle-compaction-execution-retry1"
)
PRODUCTION_PACKET_DIR = PRODUCTION_STAGE_ROOT / "authorization_packet"
PRODUCTION_COMPLETED_EVIDENCE_DIR = PRODUCTION_STAGE_ROOT / "completed_run"
PRODUCTION_LEDGER_PATH = PRODUCTION_PACKET_DIR / "payload_ledger.csv"
PRODUCTION_PACKET_MANIFEST = PRODUCTION_PACKET_DIR / "local_asset_manifest.sha256"
PRODUCTION_COMPLETED_EVIDENCE_MANIFEST = (
    PRODUCTION_STAGE_ROOT / "goal046_completed_evidence_manifest.sha256"
)
PRODUCTION_STAGED_INPUT_MANIFEST = (
    PRODUCTION_STAGE_ROOT / "goal047_staged_input_manifest.sha256"
)
PRODUCTION_APPROVAL_RECEIPT = PRODUCTION_STAGE_ROOT / "approval_receipt.json"
PRODUCTION_STAGE_TRANSCRIPT = (
    PRODUCTION_STAGE_ROOT / "three_case_lifecycle_compaction_transcript.jsonl"
)
PRODUCTION_STATUS_JSON = PRODUCTION_EVIDENCE_ROOT / "execution_status.json"
PRODUCTION_EVIDENCE_FILE_LIST = (
    PRODUCTION_EVIDENCE_ROOT / "compact_evidence_file_list.txt"
)
PRODUCTION_LOCK_PATH = (
    PRODUCTION_STAGE_ROOT / "three_case_lifecycle_compaction.lock"
)
PRODUCTION_HASH_WORKERS = 8

DELETE_HDF5 = "DELETE_PROPOSED_UNIQUE_RAW"
DELETE_XMF = "DELETE_PROPOSED_METADATA_ONLY"
DELETE_ACTIONS = {DELETE_HDF5, DELETE_XMF}
TERMINAL_STATUSES = {
    "FAILED_CLOSED_NO_MUTATION",
    "FAILED_CLOSED_PARTIAL_MUTATION",
    "FAILED_CLOSED_POSTCHECK",
    "DELETION_COMPLETE_POSTCHECK_GREEN",
}
DRY_RUN_STATUS = "DRY_RUN_VALIDATED_NO_MUTATION"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATA_RE = re.compile(r"^data\.(\d{4})\.(flt|dbl)\.(h5|xmf)$")
QSTAT_JOB_RE = re.compile(
    r"^\s*(?P<job_id>(?P<number>\d+)"
    r"(?P<array>\[[0-9,-]*\])?"
    r"(?:\.[A-Za-z0-9_.-]+)?)\s+"
)
QSTAT_JOB_ID_RE = re.compile(
    r"^(?P<number>\d+)(?P<array>\[[0-9,-]*\])?"
    r"(?:\.[A-Za-z0-9_.-]+)?$"
)
SOURCE_COLUMNS = [
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
REQUIRED_PACKET_FILES = {
    "active_hold_register.csv",
    "active_job_gate.csv",
    "canonical_source_register.csv",
    "deletion_candidate_summary.csv",
    "duplicate_evidence.csv",
    "external_archive_manifest.csv",
    "goal047_execution_contract.csv",
    "inventory_metadata.json",
    "no_delete_conditions.csv",
    "payload_ledger.csv",
    "protected_path_contract.csv",
    "recovery_forecast.csv",
    "remote_root_allowlist.csv",
    "retention_summary.csv",
    "retrieved_archive_validation.csv",
}
SINGLE_OWNER_ASSUMPTION = (
    "All allowlisted roots have one administrative owner; no process other "
    "than this PBS job will create, replace, relink, rename, or modify any "
    "allowlisted entry between the two qstat gates and the post-scan."
)


class CompactionError(RuntimeError):
    """A fail-closed lifecycle error with an explicit terminal state."""

    def __init__(
        self,
        message: str,
        status: str = "FAILED_CLOSED_NO_MUTATION",
        *,
        mutation_outcome_unknown: bool = False,
    ):
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"invalid failure status: {status}")
        super().__init__(message)
        self.status = status
        self.mutation_outcome_unknown = mutation_outcome_unknown


@dataclasses.dataclass(frozen=True)
class ExecutionPolicy:
    ledger_sha256: str
    confirmation_token: str
    hdf5_count: int
    xmf_count: int
    allocated_bytes: int
    payload_count: int | None
    hash_workers: int
    lock_path: Path
    production_frozen: bool = False
    trusted_stage_root: Path | None = None
    trusted_evidence_root: Path | None = None

    @property
    def deletion_count(self) -> int:
        return self.hdf5_count + self.xmf_count


PRODUCTION_POLICY = ExecutionPolicy(
    ledger_sha256=APPROVED_LEDGER_SHA256,
    confirmation_token=CONFIRMATION_TOKEN,
    hdf5_count=APPROVED_HDF5_COUNT,
    xmf_count=APPROVED_XMF_COUNT,
    allocated_bytes=APPROVED_ALLOCATED_BYTES,
    payload_count=17_153,
    hash_workers=PRODUCTION_HASH_WORKERS,
    lock_path=PRODUCTION_LOCK_PATH,
    production_frozen=True,
    trusted_stage_root=PRODUCTION_STAGE_ROOT,
    trusted_evidence_root=PRODUCTION_EVIDENCE_ROOT,
)


@dataclasses.dataclass(frozen=True)
class ExecutionPaths:
    approved_ledger: Path
    packet_manifest: Path
    completed_evidence_dir: Path
    completed_evidence_manifest: Path
    staged_input_manifest: Path
    approval_receipt: Path
    evidence_root: Path
    stage_transcript: Path
    status_json: Path
    compact_evidence_file_list: Path
    lock_path: Path


@dataclasses.dataclass
class HeldCandidate:
    row: dict[str, str]
    fd: int
    before: os.stat_result
    observed_sha256: str = ""
    path_removed: bool = False
    closed: bool = False


@dataclasses.dataclass
class Services:
    qstat_runner: Callable[[str], subprocess.CompletedProcess[str]]
    unlinker: Callable[[int, str, dict[str, str]], None]
    before_postscan: Callable[[], None] = lambda: None


def _default_qstat_runner(owner: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["qstat", "-u", owner],
        text=True,
        capture_output=True,
        check=False,
    )


def _default_unlinker(parent_fd: int, name: str, row: dict[str, str]) -> None:
    del row
    os.unlink(name, dir_fd=parent_fd)


DEFAULT_SERVICES = Services(_default_qstat_runner, _default_unlinker)


def _read_csv(path: Path, required: Iterable[str] = ()) -> list[dict[str, str]]:
    try:
        with path.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            if not fields or len(fields) != len(set(fields)):
                raise CompactionError(f"invalid or duplicate CSV header: {path}")
            missing = set(required) - set(fields)
            if missing:
                raise CompactionError(
                    f"missing CSV columns {sorted(missing)}: {path}"
                )
            result = []
            for number, row in enumerate(reader, 2):
                if None in row or any(value is None for value in row.values()):
                    raise CompactionError(
                        f"malformed CSV row {number}: {path}"
                    )
                result.append({key: (value or "").strip() for key, value in row.items()})
            return result
    except OSError as exc:
        raise CompactionError(f"cannot read CSV {path}: {exc}") from exc


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            while chunk := handle.read(4 * 1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise CompactionError(f"cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def _canonical_record(record: Mapping[str, Any]) -> bytes:
    return json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _write_json_exclusive(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
        try:
            os.write(fd, data.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise CompactionError(f"cannot create evidence file {path}: {exc}") from exc


class HashChainTranscript:
    """Append-only, fsynced JSONL with a SHA-256 chain."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_APPEND
        try:
            self.fd = os.open(path, flags, 0o600)
        except OSError as exc:
            raise CompactionError(
                f"cannot create authoritative transcript {path}: {exc}"
            ) from exc
        self.path = path
        self.sequence = 0
        self.previous = "0" * 64
        self.closed = False

    def append(self, event: str, **values: Any) -> str:
        if self.closed:
            raise RuntimeError("transcript is closed")
        self.sequence += 1
        record: dict[str, Any] = {
            "sequence": self.sequence,
            "previous_record_sha256": self.previous,
            "recorded_utc": dt.datetime.now(dt.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
            "event": event,
            **values,
        }
        record_hash = _sha256_bytes(_canonical_record(record))
        record["record_sha256"] = record_hash
        os.write(self.fd, _canonical_record(record) + b"\n")
        os.fsync(self.fd)
        self.previous = record_hash
        return record_hash

    def close(self) -> None:
        if not self.closed:
            os.fsync(self.fd)
            os.close(self.fd)
            self.closed = True


class AtomicCompactionLock:
    """Directory lock held from the first qstat gate through postcheck."""

    def __init__(self, path: Path, job_id: str):
        self.path = path
        self.job_id = job_id
        self.acquired = False

    def __enter__(self) -> "AtomicCompactionLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.mkdir(self.path, 0o700)
        except FileExistsError as exc:
            raise CompactionError(f"compaction lock already exists: {self.path}") from exc
        except OSError as exc:
            raise CompactionError(f"cannot acquire compaction lock {self.path}: {exc}") from exc
        self.acquired = True
        owner = self.path / "owner.json"
        try:
            _write_json_exclusive(
                owner,
                {
                    "pbs_job_id": self.job_id,
                    "pid": os.getpid(),
                    "acquired_utc": dt.datetime.now(dt.timezone.utc)
                    .isoformat()
                    .replace("+00:00", "Z"),
                },
            )
        except Exception:
            self.path.rmdir()
            self.acquired = False
            raise
        directory_fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if not self.acquired:
            return
        try:
            (self.path / "owner.json").unlink()
            self.path.rmdir()
        except OSError as release_error:
            if exc is None:
                raise CompactionError(
                    f"cannot release compaction lock {self.path}: {release_error}",
                    "FAILED_CLOSED_POSTCHECK",
                ) from release_error
        finally:
            self.acquired = False


def _manifest_entries(manifest: Path) -> dict[str, str]:
    entries: dict[str, str] = {}
    try:
        lines = manifest.read_text().splitlines()
    except OSError as exc:
        raise CompactionError(f"cannot read manifest {manifest}: {exc}") from exc
    if not lines:
        raise CompactionError(f"empty manifest: {manifest}")
    for number, line in enumerate(lines, 1):
        try:
            digest, relative = line.split("  ", 1)
        except ValueError as exc:
            raise CompactionError(
                f"malformed manifest line {number}: {manifest}"
            ) from exc
        if not SHA256_RE.fullmatch(digest):
            raise CompactionError(f"invalid manifest digest at line {number}: {manifest}")
        canonical = relative[2:] if relative.startswith("./") else relative
        normalized = os.path.normpath(canonical)
        if (
            not canonical
            or os.path.isabs(canonical)
            or normalized != canonical
            or canonical == ".."
            or canonical.startswith("../")
        ):
            raise CompactionError(f"unsafe manifest path {relative!r}: {manifest}")
        if canonical in entries:
            raise CompactionError(f"duplicate manifest path {canonical}: {manifest}")
        entries[canonical] = digest
    return entries


def _validate_manifest(
    manifest: Path,
    base: Path,
    *,
    exact_tree: bool,
    required_paths: Iterable[Path] = (),
) -> dict[str, str]:
    entries = _manifest_entries(manifest)
    base_abs = base.absolute()
    for relative, expected in entries.items():
        path = base / relative
        if not path.is_file() or _sha256_path(path) != expected:
            raise CompactionError(f"manifest mismatch: {path}")
    required_relatives = set()
    for required in required_paths:
        try:
            required_relatives.add(str(required.absolute().relative_to(base_abs)))
        except ValueError as exc:
            raise CompactionError(
                f"required manifest input outside base: {required}"
            ) from exc
    omitted = required_relatives - set(entries)
    if omitted:
        raise CompactionError(f"manifest omitted required inputs: {sorted(omitted)}")
    if exact_tree:
        actual = {
            str(path.relative_to(base))
            for path in base.rglob("*")
            if path.is_file() and path != manifest
        }
        expected_names = set(entries)
        if manifest.is_relative_to(base):
            expected_names.discard(str(manifest.relative_to(base)))
        if actual != expected_names:
            raise CompactionError(
                "manifest file-set mismatch: "
                f"missing={sorted(actual - expected_names)}, "
                f"extra={sorted(expected_names - actual)}"
            )
    return entries


def _validate_receipt(
    path: Path,
    policy: ExecutionPolicy,
    confirmation_token: str,
) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CompactionError(f"invalid approval receipt {path}: {exc}") from exc
    required = {
        "approval_status": "approved",
        "approved_payload_ledger_sha256": policy.ledger_sha256,
        "approved_row_count": policy.deletion_count,
        "approved_hdf5_count": policy.hdf5_count,
        "approved_xmf_count": policy.xmf_count,
        "approved_allocated_bytes": policy.allocated_bytes,
        "confirmation_token": policy.confirmation_token,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise CompactionError(
                f"approval receipt mismatch for {key}: "
                f"expected {expected!r}, found {receipt.get(key)!r}"
            )
    if confirmation_token != policy.confirmation_token:
        raise CompactionError("explicit confirmation token mismatch")
    return receipt


def _lexically_within(path: str, root: str) -> bool:
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        return False
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def _validate_roots(rows: Sequence[dict[str, str]]) -> list[str]:
    roots: list[str] = []
    seen_ids: set[str] = set()
    for row in rows:
        root = row["root_path"]
        if (
            not os.path.isabs(root)
            or os.path.normpath(root) != root
            or row["root_id"] in seen_ids
        ):
            raise CompactionError(f"invalid allowlisted root: {row}")
        seen_ids.add(row["root_id"])
        roots.append(root)
    for index, left in enumerate(roots):
        for right in roots[index + 1 :]:
            if _lexically_within(left, right) or _lexically_within(right, left):
                raise CompactionError(f"overlapping allowlisted roots: {left}, {right}")
    return roots


def _paired_path(path: str) -> str:
    if path.endswith(".h5"):
        return path[:-2] + "xmf"
    if path.endswith(".xmf"):
        return path[:-3] + "h5"
    raise CompactionError(f"approved path is not HDF5/XMF: {path}")


def _catalogue_members(completed: Path) -> dict[tuple[str, str], set[str]]:
    root = completed / "catalogue_snapshot"
    if not root.is_dir():
        raise CompactionError(f"catalogue snapshot missing: {root}")
    members: dict[tuple[str, str], set[str]] = {}
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        for stream in sorted(directory.iterdir()):
            if not stream.is_file() or stream.name not in {"flt.h5.out", "dbl.h5.out"}:
                continue
            kind = stream.name.split(".", 1)[0]
            ids: set[str] = set()
            for line in stream.read_text().splitlines():
                fields = line.split()
                if fields and fields[0].isdigit():
                    ids.add(fields[0].zfill(4))
            members[(directory.name, kind)] = ids
    return members


def _validate_packet_and_ledger(
    paths: ExecutionPaths,
    policy: ExecutionPolicy,
) -> tuple[
    list[dict[str, str]],
    list[dict[str, str]],
    list[dict[str, str]],
    list[str],
]:
    packet = paths.approved_ledger.parent
    if paths.approved_ledger.name != "payload_ledger.csv":
        raise CompactionError("approved ledger must be payload_ledger.csv")
    if paths.packet_manifest != packet / "local_asset_manifest.sha256":
        raise CompactionError("packet manifest must be the packet local asset manifest")
    packet_entries = _validate_manifest(
        paths.packet_manifest,
        packet,
        exact_tree=True,
        required_paths=[packet / name for name in REQUIRED_PACKET_FILES],
    )
    if set(packet_entries) != REQUIRED_PACKET_FILES:
        raise CompactionError(
            "packet manifest expected-name coverage mismatch: "
            f"{sorted(set(packet_entries) ^ REQUIRED_PACKET_FILES)}"
        )
    ledger_digest = _sha256_path(paths.approved_ledger)
    if ledger_digest != policy.ledger_sha256:
        raise CompactionError(
            f"approved ledger digest mismatch: {ledger_digest}"
        )
    ledger = _read_csv(paths.approved_ledger, SOURCE_COLUMNS + ["action"])
    if policy.payload_count is not None and len(ledger) != policy.payload_count:
        raise CompactionError(
            f"frozen payload count mismatch: {len(ledger)} != {policy.payload_count}"
        )
    if len({row["path"] for row in ledger}) != len(ledger):
        raise CompactionError("duplicate ledger path")
    try:
        metadata = json.loads((packet / "inventory_metadata.json").read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise CompactionError(f"invalid packet metadata: {exc}") from exc
    action_counts: dict[str, int] = {}
    for row in ledger:
        action_counts[row["action"]] = action_counts.get(row["action"], 0) + 1
    if (
        metadata.get("payload_ledger_sha256") != ledger_digest
        or metadata.get("payload_count") != len(ledger)
        or metadata.get("dry_run_only") is not True
        or metadata.get("deletion_capability") is not False
        or metadata.get("action_counts") != action_counts
    ):
        raise CompactionError("packet metadata does not bind the frozen ledger")
    execution_contract = _read_csv(
        packet / "goal047_execution_contract.csv",
        {"step", "ledger_digest", "mutation_allowed"},
    )
    if (
        not execution_contract
        or any(
            row["ledger_digest"] != policy.ledger_sha256
            for row in execution_contract
        )
        or any(
            row["mutation_allowed"].lower() == "true"
            for row in execution_contract
        )
    ):
        raise CompactionError("Goal 047 execution contract binding mismatch")

    source_path = (
        paths.completed_evidence_dir
        / "review_inventory/inventory/payload_inventory.csv"
    )
    root_inventory_path = (
        paths.completed_evidence_dir
        / "review_inventory/inventory/remote_root_inventory.csv"
    )
    allowlist_completed = (
        paths.completed_evidence_dir / "review_inventory/remote_root_allowlist.csv"
    )
    protected_completed = (
        paths.completed_evidence_dir / "review_inventory/protected_path_contract.csv"
    )
    required_completed = [
        source_path,
        root_inventory_path,
        allowlist_completed,
        protected_completed,
    ]
    required_completed.extend(
        sorted(
            path
            for path in (paths.completed_evidence_dir / "catalogue_snapshot").rglob("*")
            if path.is_file()
        )
    )
    _validate_manifest(
        paths.completed_evidence_manifest,
        paths.completed_evidence_dir,
        exact_tree=True,
        required_paths=required_completed,
    )
    source = _read_csv(source_path, SOURCE_COLUMNS)
    if len(source) != len(ledger):
        raise CompactionError("ledger/source inventory row count mismatch")
    source_map = {row["path"]: row for row in source}
    if len(source_map) != len(source):
        raise CompactionError("duplicate frozen source path")
    for row in ledger:
        observed = source_map.get(row["path"])
        if observed is None or {key: row[key] for key in SOURCE_COLUMNS} != observed:
            raise CompactionError(f"ledger source-row reconciliation failed: {row['path']}")

    aliases: dict[tuple[str, str], list[str]] = {}
    for row in source:
        if row["file_type"] == "regular":
            aliases.setdefault((row["device"], row["inode"]), []).append(row["path"])
    duplicate_aliases = [items for items in aliases.values() if len(items) != 1]
    if duplicate_aliases:
        raise CompactionError(f"duplicate inode aliases in frozen inventory: {duplicate_aliases[:3]}")

    allowlist_packet = packet / "remote_root_allowlist.csv"
    protected_packet = packet / "protected_path_contract.csv"
    if allowlist_packet.read_bytes() != allowlist_completed.read_bytes():
        raise CompactionError("allowlist differs from frozen completed evidence")
    if protected_packet.read_bytes() != protected_completed.read_bytes():
        raise CompactionError("protected contract differs from frozen completed evidence")
    allowlist = _read_csv(
        allowlist_packet,
        {"case_id", "root_id", "root_path", "expected_presence"},
    )
    roots = _validate_roots(allowlist)
    for row in ledger:
        containing = [root for root in roots if _lexically_within(row["path"], root)]
        if len(containing) != 1:
            raise CompactionError(f"ledger path outside exactly one allowlisted root: {row['path']}")

    candidates = [row for row in ledger if row["action"] in DELETE_ACTIONS]
    hdf5 = [row for row in candidates if row["action"] == DELETE_HDF5]
    xmf = [row for row in candidates if row["action"] == DELETE_XMF]
    if len(hdf5) != policy.hdf5_count or len(xmf) != policy.xmf_count:
        raise CompactionError(
            f"approved action counts mismatch: hdf5={len(hdf5)}, xmf={len(xmf)}"
        )
    if sum(int(row["allocated_bytes"]) for row in candidates) != policy.allocated_bytes:
        raise CompactionError("approved allocated-byte total mismatch")
    candidate_paths = {row["path"] for row in candidates}

    protected_rows = _read_csv(protected_packet, {"path", "protection_class"})
    protected_paths = {row["path"] for row in protected_rows}
    hold_rows = _read_csv(packet / "active_hold_register.csv", {"path", "action"})
    hold_paths = {row["path"] for row in hold_rows}
    ledger_holds = {
        row["path"]: row["action"]
        for row in ledger
        if row["action"].startswith("HOLD_")
    }
    if ledger_holds != {row["path"]: row["action"] for row in hold_rows}:
        raise CompactionError("hold register differs from ledger hold union")
    if candidate_paths & (protected_paths | hold_paths):
        raise CompactionError("approved deletion intersects protected/held union")

    by_path = {row["path"]: row for row in ledger}
    catalogues = _catalogue_members(paths.completed_evidence_dir)
    for row in candidates:
        if (
            row["file_type"] != "regular"
            or row["identity_status"] != "stable"
            or row["contract_protection"] != "UNPROTECTED"
            or row["full_hash_required"] != "true"
            or row["dry_run_only"] != "true"
            or not SHA256_RE.fullmatch(row["sha256"])
            or row["pair_status"] != "complete"
        ):
            raise CompactionError(f"unsafe approved row fields: {row['path']}")
        pair = by_path.get(_paired_path(row["path"]))
        expected_pair_action = DELETE_XMF if row["action"] == DELETE_HDF5 else DELETE_HDF5
        if pair is None or pair["action"] != expected_pair_action:
            raise CompactionError(f"approved pair mismatch: {row['path']}")
        match = DATA_RE.match(Path(row["path"]).name)
        if not match:
            raise CompactionError(f"approved production filename mismatch: {row['path']}")
        if row["root_id"].startswith("production_") and row["action"] == DELETE_HDF5:
            if (
                row["catalogue_membership"] != "present"
                or match.group(1)
                not in catalogues.get((row["root_id"], match.group(2)), set())
            ):
                raise CompactionError(f"catalogue membership mismatch: {row['path']}")
        if row["action"] == DELETE_XMF and row["catalogue_membership"] != "not_required":
            raise CompactionError(f"unexpected XMF catalogue status: {row['path']}")
    return ledger, source, protected_rows, roots


def _lstat_signature(st: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        st.st_dev,
        st.st_ino,
        st.st_size,
        st.st_blocks * 512,
        st.st_mtime_ns,
        stat.S_IFMT(st.st_mode),
    )


def _cross_node_signature(st: os.stat_result) -> tuple[int, int, int, int]:
    return (
        st.st_ino,
        st.st_size,
        st.st_blocks * 512,
        st.st_mtime_ns,
    )


def _expected_cross_node_signature(
    row: Mapping[str, str],
) -> tuple[int, int, int, int]:
    return (
        int(row["inode"]),
        int(row["apparent_bytes"]),
        int(row["allocated_bytes"]),
        int(row["mtime_ns"]),
    )


def _expected_live_signature(
    row: Mapping[str, str],
) -> tuple[int, int, int, int, int, int]:
    file_types = {
        "regular": stat.S_IFREG,
        "symlink": stat.S_IFLNK,
    }
    try:
        file_type = file_types[row["file_type"]]
    except KeyError as exc:
        raise CompactionError(
            f"unsupported live file type: {row.get('file_type', '')}"
        ) from exc
    return (
        int(row["device"]),
        int(row["inode"]),
        int(row["apparent_bytes"]),
        int(row["allocated_bytes"]),
        int(row["mtime_ns"]),
        file_type,
    )


def _live_rows_for_root(root_row: Mapping[str, str]) -> list[dict[str, str]]:
    root = Path(root_row["root_path"])
    result: list[dict[str, str]] = []
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_dirs: list[str] = []
        for name in sorted(dirnames):
            path = current_path / name
            st = os.lstat(path)
            if stat.S_ISLNK(st.st_mode):
                result.append(_live_row(root_row, path, st))
            elif stat.S_ISDIR(st.st_mode):
                kept_dirs.append(name)
            else:
                raise CompactionError(f"unexpected directory-entry type: {path}")
        dirnames[:] = kept_dirs
        for name in sorted(filenames):
            path = current_path / name
            st = os.lstat(path)
            if not (stat.S_ISREG(st.st_mode) or stat.S_ISLNK(st.st_mode)):
                raise CompactionError(f"unexpected file-entry type: {path}")
            result.append(_live_row(root_row, path, st))
    return result


def _live_row(
    root_row: Mapping[str, str], path: Path, st: os.stat_result
) -> dict[str, str]:
    is_link = stat.S_ISLNK(st.st_mode)
    link_target = os.readlink(path) if is_link else ""
    resolved = str(path.resolve(strict=False)) if is_link else str(path)
    return {
        "case_id": root_row["case_id"],
        "root_id": root_row["root_id"],
        "root_path": root_row["root_path"],
        "root_kind": root_row["root_kind"],
        "path": str(path),
        "relative_path": str(path.relative_to(root_row["root_path"])),
        "resolved_path": resolved,
        "file_type": "symlink" if is_link else "regular",
        "link_target": link_target,
        "device": str(st.st_dev),
        "inode": str(st.st_ino),
        "apparent_bytes": str(st.st_size),
        "allocated_bytes": str(st.st_blocks * 512),
        "mtime_ns": str(st.st_mtime_ns),
    }


def _snapshot_and_compare(
    packet: Path,
    completed: Path,
    source: Sequence[dict[str, str]],
    *,
    after_delete_paths: set[str] | None = None,
) -> list[dict[str, str]]:
    allowlist = _read_csv(packet / "remote_root_allowlist.csv")
    root_inventory = {
        row["root_id"]: row
        for row in _read_csv(
            completed / "review_inventory/inventory/remote_root_inventory.csv",
            {"root_id", "root_path", "exists"},
        )
    }
    live: list[dict[str, str]] = []
    for root_row in allowlist:
        root_path = Path(root_row["root_path"])
        frozen_root = root_inventory.get(root_row["root_id"])
        if frozen_root is None or frozen_root["root_path"] != root_row["root_path"]:
            raise CompactionError(f"root inventory mismatch: {root_row['root_id']}")
        exists = root_path.exists()
        if exists != (frozen_root["exists"].lower() == "true"):
            raise CompactionError(f"root presence changed: {root_path}")
        if exists:
            st = os.lstat(root_path)
            if not stat.S_ISDIR(st.st_mode) or stat.S_ISLNK(st.st_mode):
                raise CompactionError(f"allowlisted root is not a real directory: {root_path}")
            live.extend(_live_rows_for_root(root_row))
    live_map = {row["path"]: row for row in live}
    if len(live_map) != len(live):
        raise CompactionError("duplicate live path")
    deleted = after_delete_paths or set()
    expected_paths = {row["path"] for row in source} - deleted
    if set(live_map) != expected_paths:
        missing = sorted(expected_paths - set(live_map))
        added = sorted(set(live_map) - expected_paths)
        raise CompactionError(
            f"live/frozen path-set mismatch: missing={missing[:5]}, added={added[:5]}"
        )
    for frozen in source:
        if frozen["path"] in deleted:
            continue
        observed = live_map[frozen["path"]]
        keys = (
            "case_id",
            "root_id",
            "root_path",
            "root_kind",
            "path",
            "relative_path",
            "resolved_path",
            "file_type",
            "link_target",
            "inode",
            "apparent_bytes",
            "allocated_bytes",
            "mtime_ns",
        )
        if any(observed[key] != frozen[key] for key in keys):
            differences = {
                key: (frozen[key], observed[key])
                for key in keys
                if observed[key] != frozen[key]
            }
            raise CompactionError(
                f"live/frozen identity mismatch: {frozen['path']}: {differences}"
            )
    return sorted(live, key=lambda row: row["path"])


def _device_namespace_mappings(
    frozen_rows: Sequence[Mapping[str, str]],
    live_rows: Sequence[Mapping[str, str]],
) -> list[dict[str, str | int]]:
    live_by_path = {row["path"]: row for row in live_rows}
    counts: dict[tuple[str, str], int] = {}
    for frozen in frozen_rows:
        observed = live_by_path.get(frozen["path"])
        if observed is None:
            continue
        key = (frozen["device"], observed["device"])
        counts[key] = counts.get(key, 0) + 1
    return [
        {
            "frozen_device": frozen_device,
            "live_device": live_device,
            "row_count": row_count,
        }
        for (frozen_device, live_device), row_count in sorted(counts.items())
    ]


def _compare_pre_and_post_live_rows(
    pre_rows: Sequence[Mapping[str, str]],
    post_rows: Sequence[Mapping[str, str]],
    deleted_paths: set[str],
) -> None:
    pre_by_path = {row["path"]: row for row in pre_rows}
    post_by_path = {row["path"]: row for row in post_rows}
    expected_paths = set(pre_by_path) - deleted_paths
    if set(post_by_path) != expected_paths:
        missing = sorted(expected_paths - set(post_by_path))
        added = sorted(set(post_by_path) - expected_paths)
        raise CompactionError(
            "pre/post live path-set mismatch: "
            f"missing={missing[:5]}, added={added[:5]}",
            "FAILED_CLOSED_POSTCHECK",
        )
    keys = (
        "case_id",
        "root_id",
        "root_path",
        "root_kind",
        "path",
        "relative_path",
        "resolved_path",
        "file_type",
        "link_target",
        "device",
        "inode",
        "apparent_bytes",
        "allocated_bytes",
        "mtime_ns",
    )
    for path in sorted(expected_paths):
        before = pre_by_path[path]
        after = post_by_path[path]
        differences = {
            key: (before[key], after[key])
            for key in keys
            if before[key] != after[key]
        }
        if differences:
            raise CompactionError(
                f"pre/post live identity mismatch: {path}: {differences}",
                "FAILED_CLOSED_POSTCHECK",
            )


def _open_candidates(
    candidates: Sequence[dict[str, str]],
    pre_rows: Sequence[Mapping[str, str]],
) -> list[HeldCandidate]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    pre_by_path = {row["path"]: row for row in pre_rows}
    held: list[HeldCandidate] = []
    try:
        for row in sorted(candidates, key=lambda item: item["path"]):
            pre_row = pre_by_path.get(row["path"])
            if pre_row is None:
                raise CompactionError(
                    f"candidate absent from predelete live snapshot: {row['path']}"
                )
            try:
                fd = os.open(row["path"], flags)
            except OSError as exc:
                raise CompactionError(f"cannot open approved candidate: {row['path']}: {exc}") from exc
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode):
                os.close(fd)
                raise CompactionError(f"candidate is not regular: {row['path']}")
            if before.st_nlink != 1:
                os.close(fd)
                raise CompactionError(
                    f"candidate hardlink count is not one: {row['path']}: {before.st_nlink}"
                )
            if _lstat_signature(before) != _expected_live_signature(pre_row):
                os.close(fd)
                raise CompactionError(
                    f"candidate changed since predelete live snapshot: {row['path']}"
                )
            if _cross_node_signature(before) != _expected_cross_node_signature(row):
                os.close(fd)
                raise CompactionError(f"candidate descriptor identity mismatch: {row['path']}")
            held.append(HeldCandidate(row=row, fd=fd, before=before))
    except Exception:
        _close_held(held)
        raise
    identities = {(item.before.st_dev, item.before.st_ino) for item in held}
    if len(identities) != len(held):
        _close_held(held)
        raise CompactionError("duplicate candidate descriptor inode")
    return held


def _hash_fd(candidate: HeldCandidate) -> str:
    digest = hashlib.sha256()
    offset = 0
    try:
        while True:
            chunk = os.pread(candidate.fd, 4 * 1024 * 1024, offset)
            if not chunk:
                break
            digest.update(chunk)
            offset += len(chunk)
    except OSError as exc:
        raise CompactionError(
            f"candidate hash read failed: {candidate.row['path']}: {exc}"
        ) from exc
    after = os.fstat(candidate.fd)
    if _lstat_signature(after) != _lstat_signature(candidate.before) or after.st_nlink != 1:
        raise CompactionError(f"candidate changed during hash: {candidate.row['path']}")
    observed = digest.hexdigest()
    if observed != candidate.row["sha256"]:
        raise CompactionError(
            f"candidate hash mismatch: {candidate.row['path']}: {observed}"
        )
    candidate.observed_sha256 = observed
    return observed


def _hash_candidates(held: Sequence[HeldCandidate], workers: int) -> None:
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_hash_fd, held))
    except CompactionError:
        raise
    except Exception as exc:
        raise CompactionError(f"candidate hashing failed: {exc}") from exc


def _close_candidate(candidate: HeldCandidate) -> None:
    if not candidate.closed:
        try:
            os.close(candidate.fd)
        except OSError as exc:
            raise CompactionError(
                f"candidate close failed: {candidate.row['path']}: {exc}",
                "FAILED_CLOSED_PARTIAL_MUTATION",
            ) from exc
        candidate.closed = True


def _close_held(held: Iterable[HeldCandidate]) -> None:
    for candidate in held:
        if not candidate.closed:
            try:
                os.close(candidate.fd)
            except OSError:
                pass
            candidate.closed = True


def _qstat_gate(
    services: Services,
    owner: str,
    pbs_job_id: str,
    output_path: Path,
    phase: str,
    transcript: HashChainTranscript,
) -> None:
    result = services.qstat_runner(owner)
    raw = (
        f"checked_utc={dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00', 'Z')}\n"
        f"host={os.uname().nodename}\n"
        f"command=qstat -u {owner}\n"
        f"exit_status={result.returncode}\n"
        "--- stdout ---\n"
        f"{result.stdout}"
        "\n--- stderr ---\n"
        f"{result.stderr}"
    )
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(output_path, flags, 0o600)
        try:
            os.write(fd, raw.encode())
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise CompactionError(f"cannot preserve qstat evidence: {output_path}: {exc}") from exc
    if result.returncode != 0:
        raise CompactionError(f"qstat gate {phase} failed with {result.returncode}")
    observed_matches = [
        match
        for line in result.stdout.splitlines()
        if (match := QSTAT_JOB_RE.match(line))
    ]
    observed = [match.group("job_id") for match in observed_matches]
    own_job = QSTAT_JOB_ID_RE.fullmatch(pbs_job_id)
    if own_job is None or own_job.group("array") is not None:
        raise CompactionError(f"invalid scalar PBS job id: {pbs_job_id}")
    own_number = own_job.group("number")
    own_matches = [
        match.group("job_id")
        for match in observed_matches
        if match.group("number") == own_number
        and match.group("array") is None
    ]
    other = [
        match.group("job_id")
        for match in observed_matches
        if not (
            match.group("number") == own_number
            and match.group("array") is None
        )
    ]
    if len(own_matches) != 1 or other:
        raise CompactionError(
            f"qstat gate {phase} rejected jobs: own={own_matches}, other={other}"
        )
    transcript.append(
        "qstat_gate_passed",
        phase=phase,
        pbs_job_id=pbs_job_id,
        observed_jobs=observed,
        evidence_path=str(output_path),
        evidence_sha256=_sha256_path(output_path),
    )


def _open_parent_componentwise(path: str, root: str) -> tuple[int, str]:
    relative = os.path.relpath(path, root)
    if relative == ".." or relative.startswith("../") or os.path.isabs(relative):
        raise CompactionError(f"mutation path escaped root: {path}")
    parts = Path(root).parts
    fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_NOFOLLOW", 0)
    try:
        for component in parts[1:]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        relative_parts = Path(relative).parts
        for component in relative_parts[:-1]:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd, relative_parts[-1]
    except Exception:
        os.close(fd)
        raise


def _delete_one(
    candidate: HeldCandidate,
    roots: Sequence[str],
    services: Services,
    transcript: HashChainTranscript,
) -> int:
    path = candidate.row["path"]
    containing = [root for root in roots if _lexically_within(path, root)]
    if len(containing) != 1:
        raise CompactionError(
            f"mutation path outside exactly one root: {path}",
            "FAILED_CLOSED_PARTIAL_MUTATION",
        )
    parent_fd, name = _open_parent_componentwise(path, containing[0])
    try:
        entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        current_fd = os.fstat(candidate.fd)
        if (
            _lstat_signature(entry) != _lstat_signature(current_fd)
            or current_fd.st_nlink != 1
            or candidate.observed_sha256 != candidate.row["sha256"]
        ):
            raise CompactionError(
                f"immediate path/descriptor identity mismatch: {path}",
                "FAILED_CLOSED_PARTIAL_MUTATION",
            )
        transcript.append(
            "unlink_attempt",
            path=path,
            action=candidate.row["action"],
            device=current_fd.st_dev,
            inode=current_fd.st_ino,
            apparent_bytes=current_fd.st_size,
            allocated_bytes=current_fd.st_blocks * 512,
            mtime_ns=current_fd.st_mtime_ns,
            expected_sha256=candidate.row["sha256"],
            observed_sha256=candidate.observed_sha256,
        )
        try:
            services.unlinker(parent_fd, name, candidate.row)
        except OSError as exc:
            try:
                os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                candidate.path_removed = True
                transcript.append(
                    "unlink_outcome_ambiguous_or_removed",
                    path=path,
                    errno=exc.errno,
                    error=str(exc),
                    original_path_absent=True,
                )
                raise CompactionError(
                    f"unlink reported an error but removed {path}: {exc}",
                    "FAILED_CLOSED_PARTIAL_MUTATION",
                ) from exc
            except OSError as probe_exc:
                transcript.append(
                    "unlink_outcome_unknown",
                    path=path,
                    unlink_errno=exc.errno,
                    unlink_error=str(exc),
                    probe_errno=probe_exc.errno,
                    probe_error=str(probe_exc),
                    reconciliation_required=True,
                )
                raise CompactionError(
                    f"unlink mutation outcome unknown for {path}: "
                    f"unlink={exc}; absence_probe={probe_exc}; "
                    "full reconciliation required",
                    "FAILED_CLOSED_PARTIAL_MUTATION",
                    mutation_outcome_unknown=True,
                ) from probe_exc
            else:
                transcript.append(
                    "unlink_failed",
                    path=path,
                    errno=exc.errno,
                    error=str(exc),
                    original_path_present=True,
                )
                raise CompactionError(
                    f"unlink failed for {path}: {exc}",
                    "FAILED_CLOSED_PARTIAL_MUTATION",
                ) from exc
        try:
            os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            candidate.path_removed = True
        except OSError as exc:
            raise CompactionError(
                f"cannot verify original path absence after unlink: {path}: {exc}",
                "FAILED_CLOSED_PARTIAL_MUTATION",
            ) from exc
        else:
            raise CompactionError(
                f"original path remains after unlink: {path}",
                "FAILED_CLOSED_PARTIAL_MUTATION",
            )
        after = os.fstat(candidate.fd)
        # NFS may silly-rename an open unlinked file to .nfs* and retain
        # st_nlink == 1 until the descriptor closes.  Requiring zero here would
        # turn a successful first unlink into a false partial failure.  The
        # original name is proven absent above; close happens immediately; the
        # complete postscan rejects every residual/new .nfs* entry.
        preclose_nlink = after.st_nlink
        allocated = candidate.before.st_blocks * 512
        _close_candidate(candidate)
        transcript.append(
            "unlink_complete",
            path=path,
            action=candidate.row["action"],
            recovered_allocated_bytes=allocated,
            descriptor_closed=True,
            preclose_nlink=preclose_nlink,
            original_path_absent=True,
        )
        return allocated
    finally:
        os.close(parent_fd)


def _validate_protected_hdf5(
    rows: Sequence[dict[str, str]],
    ledger: Sequence[dict[str, str]],
) -> int:
    ledger_by_path = {row["path"]: row for row in ledger}
    hdf5_rows = [
        row
        for row in rows
        if row["path"].endswith((".h5", ".hdf5"))
    ]
    if not hdf5_rows:
        return 0
    try:
        import h5py  # type: ignore
    except ImportError as exc:
        raise CompactionError(
            "h5py unavailable for protected HDF5 postcheck",
            "FAILED_CLOSED_POSTCHECK",
        ) from exc
    for row in hdf5_rows:
        path = Path(row["path"])
        frozen = ledger_by_path.get(row["path"])
        if frozen is None:
            raise CompactionError(
                f"protected HDF5 absent from frozen ledger: {path}",
                "FAILED_CLOSED_POSTCHECK",
            )
        try:
            with h5py.File(path, "r") as handle:
                timestep = (
                    row.get("expected_timestep", "")
                    or frozen.get("hdf5_timestep", "")
                )
                if timestep and timestep not in handle:
                    raise ValueError(f"missing timestep {timestep}")
                group = handle[timestep] if timestep else handle
                vars_group = group["vars"] if "vars" in group else group
                frozen_datasets = {
                    name
                    for name in frozen.get("hdf5_datasets", "").split(";")
                    if name
                }
                missing_frozen = {
                    name for name in frozen_datasets if name not in handle
                }
                if missing_frozen:
                    raise ValueError(
                        f"missing frozen datasets {sorted(missing_frozen)}"
                    )
                frozen_shapes = {}
                for item in frozen.get("hdf5_shape", "").split(";"):
                    if ":" not in item:
                        continue
                    name, shape = item.split(":", 1)
                    frozen_shapes[name] = shape
                for name in frozen_datasets:
                    expected = frozen_shapes.get(name)
                    if expected and str(tuple(handle[name].shape)) != expected:
                        raise ValueError(
                            f"frozen shape mismatch for {name}"
                        )
                required = {
                    item for item in row.get("expected_datasets", "").split(";") if item
                }
                if not required:
                    required = {
                        name.rsplit("/", 1)[-1]
                        for name in frozen.get("hdf5_datasets", "").split(";")
                        if timestep and name.startswith(f"{timestep}/vars/")
                    }
                missing = required - set(vars_group)
                if missing:
                    raise ValueError(f"missing datasets {sorted(missing)}")
                shape_text = row.get("expected_shape", "")
                if shape_text:
                    expected_shape = tuple(int(value) for value in shape_text.split("x"))
                    for name in required:
                        if tuple(vars_group[name].shape) != expected_shape:
                            raise ValueError(f"shape mismatch for {name}")
                else:
                    for name in required:
                        frozen_name = f"{timestep}/vars/{name}" if timestep else name
                        expected = frozen_shapes.get(frozen_name)
                        if expected and str(tuple(vars_group[name].shape)) != expected:
                            raise ValueError(f"frozen shape mismatch for {name}")
                expected_time = (
                    row.get("expected_time_code", "")
                    or frozen.get("hdf5_time_code", "")
                )
                if expected_time:
                    attrs = dict(group.attrs)
                    attrs.update({key: value for key, value in handle.attrs.items() if key not in attrs})
                    observed_value = next(
                        (
                            attrs[key]
                            for key in ("Time", "time_code", "time", "t")
                            if key in attrs
                        ),
                        None,
                    )
                    if observed_value is None:
                        raise ValueError("missing time attribute")
                    observed = float(observed_value)
                    wanted = float(expected_time)
                    if abs(observed - wanted) > max(1e-8, abs(wanted) * 1e-10):
                        raise ValueError(f"time mismatch {observed} != {wanted}")
        except (OSError, ValueError, KeyError, RuntimeError) as exc:
            raise CompactionError(
                f"protected HDF5 validation failed: {path}: {exc}",
                "FAILED_CLOSED_POSTCHECK",
            ) from exc
    return len(hdf5_rows)


def _validate_restart_tuples(
    ledger: Sequence[dict[str, str]],
    protected_rows: Sequence[dict[str, str]],
) -> int:
    by_path = {row["path"]: row for row in ledger}
    groups: dict[tuple[str, str, str], list[str]] = {}
    for protected in protected_rows:
        if "restart" not in protected.get("dependency", ""):
            continue
        source = by_path.get(protected["path"])
        if source is None:
            raise CompactionError(
                f"protected restart absent from ledger: {protected['path']}",
                "FAILED_CLOSED_POSTCHECK",
            )
        key = (source["case_id"], source["root_id"], protected["dependency"])
        groups.setdefault(key, []).append(protected["path"])
    for key, members in groups.items():
        suffixes = {
            "h5" if path.endswith(".h5") else
            "xmf" if path.endswith(".xmf") else
            "particle" if Path(path).name.startswith("particles.") else
            "other"
            for path in members
        }
        if suffixes != {"h5", "xmf", "particle"} or len(members) != 3:
            raise CompactionError(
                f"protected restart tuple incomplete: {key}: {members}",
                "FAILED_CLOSED_POSTCHECK",
            )
        h5 = next(path for path in members if path.endswith(".h5"))
        if _paired_path(h5) not in members:
            raise CompactionError(
                f"protected restart HDF5/XMF pair mismatch: {key}",
                "FAILED_CLOSED_POSTCHECK",
            )
        if any(not Path(path).is_file() for path in members):
            raise CompactionError(
                f"protected restart tuple path missing: {key}",
                "FAILED_CLOSED_POSTCHECK",
            )
    return len(groups)


def _scratch_probe(evidence_root: Path, roots: Sequence[str]) -> dict[str, Any]:
    scratch = evidence_root / "scratch_probe"
    scratch_abs = str(scratch.absolute())
    if any(_lexically_within(scratch_abs, root) for root in roots):
        raise CompactionError(
            "scratch probe is inside an allowlisted root",
            "FAILED_CLOSED_POSTCHECK",
        )
    scratch.mkdir(parents=True, exist_ok=False)
    path = scratch / "probe.bin"
    payload = b"goal047-scratch-write-read-remove-probe\n"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, payload)
            os.fsync(fd)
        finally:
            os.close(fd)
        if path.read_bytes() != payload:
            raise CompactionError(
                "scratch probe readback mismatch",
                "FAILED_CLOSED_POSTCHECK",
            )
        path.unlink()
        directory_fd = os.open(scratch, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
        scratch.rmdir()
    except OSError as exc:
        raise CompactionError(
            f"scratch probe failed: {exc}",
            "FAILED_CLOSED_POSTCHECK",
        ) from exc
    return {
        "status": "passed",
        "bytes": len(payload),
        "scratch_path": scratch_abs,
    }


def _write_inventory(path: Path, rows: Sequence[dict[str, str]]) -> None:
    fields = [
        "case_id",
        "root_id",
        "root_path",
        "root_kind",
        "path",
        "relative_path",
        "resolved_path",
        "file_type",
        "link_target",
        "device",
        "inode",
        "apparent_bytes",
        "allocated_bytes",
        "mtime_ns",
    ]
    try:
        with path.open("x", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows({field: row[field] for field in fields} for row in rows)
            handle.flush()
            os.fsync(handle.fileno())
    except OSError as exc:
        raise CompactionError(
            f"cannot write post-delete inventory: {path}: {exc}",
            "FAILED_CLOSED_POSTCHECK",
        ) from exc


def _write_status(
    path: Path,
    *,
    status: str,
    policy: ExecutionPolicy,
    deleted: Sequence[dict[str, str]],
    recovered: int,
    error: str = "",
    transcript: HashChainTranscript | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "approved_payload_ledger_sha256": policy.ledger_sha256,
        "approved_row_count": policy.deletion_count,
        "approved_hdf5_count": policy.hdf5_count,
        "approved_xmf_count": policy.xmf_count,
        "approved_allocated_bytes": policy.allocated_bytes,
        "deleted_row_count": len(deleted),
        "deleted_hdf5_count": sum(row["action"] == DELETE_HDF5 for row in deleted),
        "deleted_xmf_count": sum(row["action"] == DELETE_XMF for row in deleted),
        "recovered_allocated_bytes": recovered,
        "single_owner_assumption": SINGLE_OWNER_ASSUMPTION,
        "error": error,
        "transcript_final_sha256": transcript.previous if transcript else "",
    }
    _write_json_exclusive(path, payload)
    return payload


def _write_evidence_file_list(
    path: Path,
    files: Iterable[Path],
    *,
    planned_files: Iterable[Path] = (),
) -> None:
    evidence_root = path.parent.absolute()
    planned = {item.absolute() for item in planned_files}
    unique: list[str] = []
    for item in files:
        absolute_item = item.absolute()
        if not item.exists() and absolute_item not in planned:
            continue
        try:
            relative = absolute_item.relative_to(evidence_root)
        except ValueError as exc:
            raise CompactionError(
                f"compact evidence is outside evidence root: {item}"
            ) from exc
        unique.append(relative.as_posix())
    unique = sorted(set(unique))
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.write(fd, ("\n".join(unique) + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)
    except OSError as exc:
        raise CompactionError(f"cannot write compact evidence file list: {exc}") from exc


def _require_absolute_normal_path(path: Path, label: str) -> None:
    raw = os.fspath(path)
    if not os.path.isabs(raw) or os.path.normpath(raw) != raw:
        raise CompactionError(f"{label} must be absolute and normalized: {path}")


def _require_directory_without_symlinks(
    path: Path,
    label: str,
    *,
    create_leaf: bool = False,
) -> None:
    """Validate an absolute directory path componentwise without following links."""

    _require_absolute_normal_path(path, label)
    parts = path.parts
    current = Path(parts[0])
    for index, component in enumerate(parts[1:], 1):
        current /= component
        is_leaf = index == len(parts) - 1
        try:
            observed = os.lstat(current)
        except FileNotFoundError:
            if not (create_leaf and is_leaf):
                raise CompactionError(
                    f"{label} component does not exist: {current}"
                ) from None
            try:
                os.mkdir(current, 0o700)
                observed = os.lstat(current)
            except OSError as exc:
                raise CompactionError(
                    f"cannot create trusted {label} directory {current}: {exc}"
                ) from exc
        except OSError as exc:
            raise CompactionError(
                f"cannot inspect {label} component {current}: {exc}"
            ) from exc
        if stat.S_ISLNK(observed.st_mode):
            raise CompactionError(f"{label} contains symlink component: {current}")
        if not stat.S_ISDIR(observed.st_mode):
            raise CompactionError(
                f"{label} contains non-directory component: {current}"
            )


def _validate_safe_output_contract(
    paths: ExecutionPaths,
    policy: ExecutionPolicy,
) -> None:
    """Establish immutable output locations before any evidence is written."""

    if policy.production_frozen and policy != PRODUCTION_POLICY:
        raise CompactionError("production policy was modified")
    stage_root = policy.trusted_stage_root
    evidence_root = policy.trusted_evidence_root
    if stage_root is None or evidence_root is None:
        raise CompactionError("trusted stage/evidence roots are required")
    for label, path in (
        ("trusted stage root", stage_root),
        ("trusted evidence root", evidence_root),
    ):
        _require_absolute_normal_path(path, label)
    if paths.evidence_root != evidence_root:
        raise CompactionError(
            f"evidence root differs from trusted contract: {paths.evidence_root}"
        )
    if _lexically_within(str(stage_root), str(evidence_root)) or _lexically_within(
        str(evidence_root), str(stage_root)
    ):
        raise CompactionError("trusted stage and evidence roots overlap")

    expected_paths = {
        "stage transcript": stage_root
        / "three_case_lifecycle_compaction_transcript.jsonl",
        "status JSON": evidence_root / "execution_status.json",
        "compact evidence file list": evidence_root
        / "compact_evidence_file_list.txt",
    }
    observed_paths = {
        "stage transcript": paths.stage_transcript,
        "status JSON": paths.status_json,
        "compact evidence file list": paths.compact_evidence_file_list,
    }
    for label, expected in expected_paths.items():
        observed = observed_paths[label]
        _require_absolute_normal_path(observed, label)
        if observed != expected:
            raise CompactionError(
                f"{label} differs from trusted contract: "
                f"expected {expected}, found {observed}"
            )
    _require_absolute_normal_path(paths.lock_path, "compaction lock")
    if paths.lock_path != policy.lock_path or paths.lock_path.parent != stage_root:
        raise CompactionError(
            f"compaction lock differs from trusted contract: {paths.lock_path}"
        )

    _require_directory_without_symlinks(stage_root, "trusted stage root")
    _require_directory_without_symlinks(
        evidence_root,
        "trusted evidence root",
        create_leaf=True,
    )


def _validate_trusted_input_path_contract(
    paths: ExecutionPaths,
    policy: ExecutionPolicy,
) -> None:
    """Validate all staged input locations after recovery evidence is live."""

    stage_root = policy.trusted_stage_root
    if stage_root is None:
        raise CompactionError("trusted stage root is required")
    expected_paths = {
        "approved ledger": stage_root
        / "authorization_packet/payload_ledger.csv",
        "packet manifest": stage_root
        / "authorization_packet/local_asset_manifest.sha256",
        "completed evidence directory": stage_root / "completed_run",
        "completed evidence manifest": stage_root
        / "goal046_completed_evidence_manifest.sha256",
        "staged input manifest": stage_root
        / "goal047_staged_input_manifest.sha256",
        "approval receipt": stage_root / "approval_receipt.json",
    }
    observed_paths = {
        "approved ledger": paths.approved_ledger,
        "packet manifest": paths.packet_manifest,
        "completed evidence directory": paths.completed_evidence_dir,
        "completed evidence manifest": paths.completed_evidence_manifest,
        "staged input manifest": paths.staged_input_manifest,
        "approval receipt": paths.approval_receipt,
    }
    for label, expected in expected_paths.items():
        observed = observed_paths[label]
        _require_absolute_normal_path(observed, label)
        if observed != expected:
            raise CompactionError(
                f"{label} differs from trusted contract: "
                f"expected {expected}, found {observed}"
            )


def _validate_path_layout(paths: ExecutionPaths, roots: Sequence[str]) -> None:
    output_paths = (
        paths.evidence_root,
        paths.stage_transcript,
        paths.status_json,
        paths.compact_evidence_file_list,
        paths.lock_path,
    )
    for path in output_paths:
        absolute = str(path.absolute())
        if any(_lexically_within(absolute, root) for root in roots):
            raise CompactionError(f"executor output/lock inside allowlisted root: {path}")
    if paths.stage_transcript.name != "three_case_lifecycle_compaction_transcript.jsonl":
        raise CompactionError(
            "authoritative stage transcript must be "
            "three_case_lifecycle_compaction_transcript.jsonl"
        )
    if paths.stage_transcript.parent != paths.staged_input_manifest.parent:
        raise CompactionError("authoritative transcript must live directly at stage root")
    if paths.status_json.parent != paths.evidence_root:
        raise CompactionError("status JSON must live directly under evidence root")
    if paths.compact_evidence_file_list.parent != paths.evidence_root:
        raise CompactionError("compact evidence file list must live under evidence root")


def execute_compaction(
    paths: ExecutionPaths,
    *,
    mode: str,
    expected_ledger_sha256: str,
    confirmation_token: str,
    pbs_job_id: str,
    policy: ExecutionPolicy = PRODUCTION_POLICY,
    services: Services = DEFAULT_SERVICES,
) -> dict[str, Any]:
    """Validate and optionally execute one exact lifecycle compaction."""

    _validate_safe_output_contract(paths, policy)
    transcript: HashChainTranscript | None = None
    held: list[HeldCandidate] = []
    deleted: list[dict[str, str]] = []
    recovered = 0
    evidence_files: list[Path] = []
    phase = "validation"
    try:
        transcript = HashChainTranscript(paths.stage_transcript)
        transcript.append(
            "execution_initialized",
            mode=mode,
            pbs_job_id=pbs_job_id,
            approved_payload_ledger_sha256=policy.ledger_sha256,
            approved_row_count=policy.deletion_count,
            approved_allocated_bytes=policy.allocated_bytes,
            single_owner_assumption=SINGLE_OWNER_ASSUMPTION,
        )
        if mode not in {"dry-run", "execute"}:
            raise CompactionError(f"unsupported mode: {mode}")
        if expected_ledger_sha256 != policy.ledger_sha256:
            raise CompactionError("expected ledger SHA-256 mismatch")
        if not pbs_job_id:
            raise CompactionError("PBS job id is required")
        _validate_trusted_input_path_contract(paths, policy)
        if mode == "execute":
            _validate_receipt(paths.approval_receipt, policy, confirmation_token)
        elif confirmation_token and confirmation_token != policy.confirmation_token:
            raise CompactionError(
                "dry-run confirmation token, if supplied, must be exact"
            )

        packet = paths.approved_ledger.parent
        ledger, source, protected_rows, roots = _validate_packet_and_ledger(
            paths, policy
        )
        _validate_path_layout(paths, roots)
        staged_required = [
            paths.approved_ledger,
            paths.packet_manifest,
            paths.completed_evidence_manifest,
            paths.approval_receipt,
            paths.staged_input_manifest.parent
            / "execute_three_case_lifecycle_compaction.py",
            paths.staged_input_manifest.parent
            / "three_case_lifecycle_compaction.pbs",
        ]
        _validate_manifest(
            paths.staged_input_manifest,
            paths.staged_input_manifest.parent,
            exact_tree=False,
            required_paths=staged_required,
        )
        transcript.append(
            "authorization_packet_and_staged_inputs_validated",
            packet_dir=str(packet),
            completed_evidence_dir=str(paths.completed_evidence_dir),
        )
        candidates = [row for row in ledger if row["action"] in DELETE_ACTIONS]
        with AtomicCompactionLock(paths.lock_path, pbs_job_id):
            transcript.append("compaction_lock_acquired", lock_path=str(paths.lock_path))
            qstat_start = paths.evidence_root / "qstat_start.txt"
            evidence_files.append(qstat_start)
            _qstat_gate(
                services,
                "bwbrook",
                pbs_job_id,
                qstat_start,
                "start",
                transcript,
            )
            pre_rows = _snapshot_and_compare(
                packet, paths.completed_evidence_dir, source
            )
            transcript.append(
                "frozen_estate_snapshot_passed",
                payload_rows=len(source),
                candidate_rows=len(candidates),
                device_namespace_mappings=_device_namespace_mappings(
                    source, pre_rows
                ),
            )
            protected_hdf5_preflight_count = _validate_protected_hdf5(
                protected_rows, ledger
            )
            restart_tuple_preflight_count = _validate_restart_tuples(
                ledger, protected_rows
            )
            transcript.append(
                "protected_and_restart_preflight_passed",
                protected_hdf5_validated=protected_hdf5_preflight_count,
                restart_tuples_validated=restart_tuple_preflight_count,
            )
            held = _open_candidates(candidates, pre_rows)
            _hash_candidates(held, policy.hash_workers)
            transcript.append(
                "all_candidates_open_and_hashed",
                candidate_rows=len(held),
                held_descriptor_count=len(held),
            )
            qstat_preunlink = paths.evidence_root / "qstat_preunlink.txt"
            evidence_files.append(qstat_preunlink)
            _qstat_gate(
                services,
                "bwbrook",
                pbs_job_id,
                qstat_preunlink,
                "preunlink",
                transcript,
            )
            if mode == "dry-run":
                _close_held(held)
                held = []
                transcript.append("dry_run_complete_no_mutation")
                phase = "evidence_finalization"
                _write_evidence_file_list(
                    paths.compact_evidence_file_list,
                    [*evidence_files, paths.status_json],
                    planned_files=[paths.status_json],
                )
                transcript.append(
                    "completion_evidence_durable",
                    compact_evidence_file_list=str(
                        paths.compact_evidence_file_list
                    ),
                )
                transcript.close()
                status = _write_status(
                    paths.status_json,
                    status=DRY_RUN_STATUS,
                    policy=policy,
                    deleted=[],
                    recovered=0,
                    transcript=transcript,
                )
                return status

            phase = "mutation"
            by_path = {candidate.row["path"]: candidate for candidate in held}
            hdf5_rows = sorted(
                (row for row in candidates if row["action"] == DELETE_HDF5),
                key=lambda row: row["path"],
            )
            ordered: list[dict[str, str]] = []
            for hdf5_row in hdf5_rows:
                ordered.extend([hdf5_row, by_path[_paired_path(hdf5_row["path"])].row])
            for row in ordered:
                candidate = by_path[row["path"]]
                try:
                    allocated = _delete_one(
                        candidate, roots, services, transcript
                    )
                except Exception:
                    if candidate.path_removed:
                        recovered += candidate.before.st_blocks * 512
                        deleted.append(row)
                    raise
                recovered += allocated
                deleted.append(row)
            held = []
            phase = "postcheck"
            if recovered != policy.allocated_bytes:
                raise CompactionError(
                    f"recovered allocated-byte reconciliation failed: {recovered}",
                    "FAILED_CLOSED_POSTCHECK",
                )
            services.before_postscan()
            try:
                post_rows = _snapshot_and_compare(
                    packet,
                    paths.completed_evidence_dir,
                    source,
                    after_delete_paths={row["path"] for row in deleted},
                )
                _compare_pre_and_post_live_rows(
                    pre_rows,
                    post_rows,
                    {row["path"] for row in deleted},
                )
            except CompactionError as exc:
                raise CompactionError(
                    f"postdelete estate reconciliation failed: {exc}",
                    "FAILED_CLOSED_POSTCHECK",
                ) from exc
            if any(Path(row["path"]).name.startswith(".nfs") for row in post_rows):
                raise CompactionError(
                    "postscan found .nfs remnant",
                    "FAILED_CLOSED_POSTCHECK",
                )
            post_inventory = paths.evidence_root / "postdelete_inventory.csv"
            _write_inventory(post_inventory, post_rows)
            evidence_files.append(post_inventory)
            protected_hdf5_count = _validate_protected_hdf5(
                protected_rows, ledger
            )
            restart_tuple_count = _validate_restart_tuples(ledger, protected_rows)
            if (
                protected_hdf5_count != protected_hdf5_preflight_count
                or restart_tuple_count != restart_tuple_preflight_count
            ):
                raise CompactionError(
                    "protected/restart preflight and postcheck counts differ",
                    "FAILED_CLOSED_POSTCHECK",
                )
            scratch = _scratch_probe(paths.evidence_root, roots)
            scratch_summary = paths.evidence_root / "scratch_probe_summary.json"
            _write_json_exclusive(scratch_summary, scratch)
            evidence_files.append(scratch_summary)
            post_summary = paths.evidence_root / "postdelete_summary.json"
            _write_json_exclusive(
                post_summary,
                {
                    "status": "passed",
                    "deleted_row_count": len(deleted),
                    "retained_row_count": len(post_rows),
                    "protected_hdf5_validated": protected_hdf5_count,
                    "restart_tuples_validated": restart_tuple_count,
                    "recovered_allocated_bytes": recovered,
                    "unexpected_nfs_rows": 0,
                },
            )
            evidence_files.append(post_summary)
            transcript.append(
                "postdelete_validation_passed",
                deleted_row_count=len(deleted),
                retained_row_count=len(post_rows),
                protected_hdf5_validated=protected_hdf5_count,
                restart_tuples_validated=restart_tuple_count,
                recovered_allocated_bytes=recovered,
                device_namespace_mappings=_device_namespace_mappings(
                    source, post_rows
                ),
            )
        phase = "evidence_finalization"
        _write_evidence_file_list(
            paths.compact_evidence_file_list,
            [*evidence_files, paths.status_json],
            planned_files=[paths.status_json],
        )
        transcript.append(
            "completion_evidence_durable",
            compact_evidence_file_list=str(paths.compact_evidence_file_list),
        )
        transcript.close()
        status = _write_status(
            paths.status_json,
            status="DELETION_COMPLETE_POSTCHECK_GREEN",
            policy=policy,
            deleted=deleted,
            recovered=recovered,
            transcript=transcript,
        )
        return status
    except Exception as exc:
        _close_held(held)
        mutation_outcome_unknown = (
            isinstance(exc, CompactionError)
            and exc.mutation_outcome_unknown
        )
        if mutation_outcome_unknown:
            failure_status = "FAILED_CLOSED_PARTIAL_MUTATION"
        elif not deleted:
            failure_status = "FAILED_CLOSED_NO_MUTATION"
        elif phase == "mutation" and len(deleted) < policy.deletion_count:
            failure_status = "FAILED_CLOSED_PARTIAL_MUTATION"
        else:
            failure_status = "FAILED_CLOSED_POSTCHECK"
        if transcript is not None and not transcript.closed:
            try:
                transcript.append(
                    "terminal_failure",
                    status=failure_status,
                    error=f"{type(exc).__name__}: {exc}",
                    deleted_row_count=len(deleted),
                    recovered_allocated_bytes=recovered,
                    mutation_outcome_unknown=mutation_outcome_unknown,
                )
            except Exception:
                pass
        if transcript is not None and not transcript.closed:
            try:
                transcript.close()
            except Exception:
                pass
        if not paths.status_json.exists():
            try:
                _write_status(
                    paths.status_json,
                    status=failure_status,
                    policy=policy,
                    deleted=deleted,
                    recovered=recovered,
                    error=f"{type(exc).__name__}: {exc}",
                    transcript=transcript,
                )
                evidence_files.append(paths.status_json)
            except Exception:
                pass
        try:
            if not paths.compact_evidence_file_list.exists():
                _write_evidence_file_list(
                    paths.compact_evidence_file_list,
                    evidence_files,
                )
        except Exception:
            pass
        if isinstance(exc, CompactionError):
            if exc.status != failure_status:
                raise CompactionError(str(exc), failure_status) from exc
            raise
        raise CompactionError(str(exc), failure_status) from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Execute the one frozen Goal 047 compaction ledger"
    )
    parser.add_argument("--mode", choices=("dry-run", "execute"), default="dry-run")
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--approved-ledger", type=Path, required=True)
    parser.add_argument("--expected-ledger-sha256", required=True)
    parser.add_argument("--confirmation-token", default="")
    parser.add_argument("--approval-receipt", type=Path, required=True)
    parser.add_argument("--completed-evidence-dir", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, required=True)
    parser.add_argument("--stage-transcript", type=Path, required=True)
    parser.add_argument("--pbs-job-id", required=True)
    parser.add_argument("--max-workers", type=int, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--status-json", type=Path, required=True)
    parser.add_argument("--compact-evidence-file-list", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.max_workers != PRODUCTION_HASH_WORKERS:
        print(
            f"ERROR: production --max-workers must equal {PRODUCTION_HASH_WORKERS}",
            file=sys.stderr,
        )
        return 2
    pbs_env = os.environ.get("PBS_JOBID", "")
    if args.mode == "execute" and (not pbs_env or pbs_env != args.pbs_job_id):
        print("ERROR: --pbs-job-id must exactly match PBS_JOBID", file=sys.stderr)
        return 2
    paths = ExecutionPaths(
        approved_ledger=args.approved_ledger,
        packet_manifest=args.packet_dir / "local_asset_manifest.sha256",
        completed_evidence_dir=args.completed_evidence_dir,
        completed_evidence_manifest=(
            args.approval_receipt.parent
            / "goal046_completed_evidence_manifest.sha256"
        ),
        staged_input_manifest=(
            args.approval_receipt.parent / "goal047_staged_input_manifest.sha256"
        ),
        approval_receipt=args.approval_receipt,
        evidence_root=args.evidence_root,
        stage_transcript=args.stage_transcript,
        status_json=args.status_json,
        compact_evidence_file_list=args.compact_evidence_file_list,
        lock_path=args.lock_path,
    )
    if args.packet_dir != args.approved_ledger.parent:
        print("ERROR: --packet-dir must be the approved-ledger parent", file=sys.stderr)
        return 2
    try:
        result = execute_compaction(
            paths,
            mode=args.mode,
            expected_ledger_sha256=args.expected_ledger_sha256,
            confirmation_token=args.confirmation_token,
            pbs_job_id=args.pbs_job_id,
        )
    except CompactionError as exc:
        print(f"{exc.status}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
