#!/usr/bin/env python3
"""Preflight and submit the one authorised X-ray migration resume."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from typing import Any


STAGE = Path("/u/bwbrook/codex_kunanyi/scratch_home_migration_2026-10-16")
ARCHIVE = Path("/u/bwbrook/xray_cavities_scratch_archive_2026-10-16")
STATE = STAGE / "state"
RESUME_DIR = STAGE / "resume_20261031"
PLAN_HASH = "698d01634ade85df5fac6d42716c5463af56118230b085021ba7b205739c8900"
FROZEN_HASHES = {
    "scripts/kunanyi/migrate_xray_scratch_to_home.py": "c70a56abf22e071da63a8c51a7eac80742b14f3d9bcbddeec3e2915a0ad4db6e",
    "scripts/kunanyi/xray_scratch_home_migration.pbs": "aec4fdb4a2ea906820a59a0ce204b91dafad76b9d3258580a0983dcb57ddfad0",
    "tests/test_migrate_xray_scratch_to_home.py": "a44d5861ee26c1321aecf01895a1e6b3681b694acb3ff74586926099e7edae26",
    "migration_plan.json": "59f4e7e6a6977f09dc259b89294ab0adb349b01af43087482fc5b873419746eb",
}
OLD_LOGS = ("migration.out", "migration.err", "migration.live.out", "tests.out")
JOB_NAME_RE = re.compile(r"^[ \t]*Job_Name[ \t]*=[ \t]*(\S+)", re.MULTILINE)
JOB_ID_RE = re.compile(r"^[0-9]+(?:\.[A-Za-z0-9_.-]+)?$")
sys.dont_write_bytecode = True


class ResumeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def atomic_json(path: Path, value: Any) -> None:
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        parent_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def durable_text(path: Path, value: str) -> None:
    with path.open("x", encoding="utf-8") as handle:
        os.fchmod(handle.fileno(), 0o600)
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def durable_copy(source: Path, destination: Path) -> None:
    shutil.copy2(source, destination, follow_symlinks=False)
    with destination.open("rb") as handle:
        os.fsync(handle.fileno())


def walltime_seconds(value: str) -> int:
    fields = value.split(":")
    if len(fields) != 3 or any(not field.isdigit() for field in fields):
        raise ResumeError(f"unrecognised PBS walltime: {value!r}")
    hours, minutes, seconds = map(int, fields)
    if minutes >= 60 or seconds >= 60:
        raise ResumeError(f"invalid PBS walltime: {value!r}")
    return hours * 3600 + minutes * 60 + seconds


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise ResumeError(f"command failed ({result.returncode}): {' '.join(command)}\n{result.stderr.strip()}")
    return result


def load_migration_module():
    path = STAGE / "scripts/kunanyi/migrate_xray_scratch_to_home.py"
    spec = importlib.util.spec_from_file_location("frozen_xray_migration", path)
    if spec is None or spec.loader is None:
        raise ResumeError(f"cannot import frozen migration module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def require_plain_dir(path: Path, owner: int, modes: tuple[int, ...] | None = None) -> int:
    observed = path.lstat()
    if not stat.S_ISDIR(observed.st_mode) or path.is_symlink():
        raise ResumeError(f"expected ordinary directory: {path}")
    if observed.st_uid != owner:
        raise ResumeError(f"owner mismatch: {path}")
    observed_mode = stat.S_IMODE(observed.st_mode)
    if modes is not None and observed_mode not in modes:
        raise ResumeError(f"mode mismatch at {path}: {oct(stat.S_IMODE(observed.st_mode))}")
    return observed_mode


def unit_common(module: Any, manager: Any, index: int) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    unit = module.Unit(manager, index, manager.plan["units"][index])
    status = unit.status()
    if (status.get("plan_hash") != PLAN_HASH or status.get("unit_id") != unit.unit_id or
            status.get("source") != str(unit.source) or status.get("destination") != str(unit.destination) or
            status.get("tombstone") != str(unit.tombstone)):
        raise ResumeError(f"unit {index} status binding mismatch")
    manifest = unit.manifest()
    if (manifest.get("plan_hash") != PLAN_HASH or manifest.get("unit_id") != unit.unit_id or
            manifest.get("source") != str(unit.source) or manifest.get("destination") != str(unit.destination)):
        raise ResumeError(f"unit {index} manifest binding mismatch")
    return unit, status, manifest


def preflight() -> tuple[dict[str, Any], str, str]:
    if RESUME_DIR.exists() or RESUME_DIR.is_symlink():
        raise ResumeError(f"resume attempt already exists: {RESUME_DIR}")
    if os.geteuid() != 145812 or os.getegid() != 1003:
        raise ResumeError(f"unexpected execution identity: euid={os.geteuid()} egid={os.getegid()}")

    observed_hashes = {relative: sha256(STAGE / relative) for relative in FROZEN_HASHES}
    if observed_hashes != FROZEN_HASHES:
        raise ResumeError(f"frozen stage checksum mismatch: {observed_hashes}")
    # Kunanyi inherited SGID on this dated root; with group/other bits zero it
    # changes child-group inheritance without granting access.
    archive_mode = require_plain_dir(ARCHIVE, os.geteuid(), (0o700, 0o2700))
    state_mode = require_plain_dir(STATE, os.geteuid(), (0o700,))

    module = load_migration_module()
    plan = module._load_plan(STAGE / "migration_plan.json")
    manager = module.Migration(plan, STATE)
    if manager.plan_hash != PLAN_HASH:
        raise ResumeError(f"validated plan hash mismatch: {manager.plan_hash}")
    expected_binding = {"schema": module.SCHEMA, "plan_hash": PLAN_HASH, "plan": plan}
    if load_json(STATE / "plan-binding.json") != expected_binding:
        raise ResumeError("immutable plan binding mismatch")

    qstat = run(["qstat", "-f", "-u", "bwbrook"]).stdout
    active_names = JOB_NAME_RE.findall(qstat)
    forbidden = [name for name in active_names if name.startswith("xray_home_move") or name == "xray_home_r2"]
    if forbidden:
        raise ResumeError(f"active X-ray migration job exists: {forbidden}")
    queue = run(["qstat", "-Qf", "copy"]).stdout
    maxima = re.findall(r"resources_max\.walltime[ \t]*=[ \t]*(\S+)", queue)
    if maxima and any(walltime_seconds(value) < 72 * 3600 for value in maxima):
        raise ResumeError(f"copy queue walltime maximum is below 72 hours: {maxima}")

    lock_path = STATE / "migration.lock"
    lock_stat = lock_path.lstat()
    if (not stat.S_ISREG(lock_stat.st_mode) or lock_path.is_symlink() or lock_stat.st_uid != os.geteuid() or
            stat.S_IMODE(lock_stat.st_mode) != 0o600):
        raise ResumeError("migration lock identity, owner, or mode mismatch")
    with lock_path.open("r+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            detail = exc.strerror or str(exc)
            raise ResumeError(f"migration state lock unavailable: errno={exc.errno} {detail}") from exc
        finally:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass

    units: list[dict[str, Any]] = []
    for index in range(8):
        unit, status, manifest = unit_common(module, manager, index)
        if status.get("stage") != "complete":
            raise ResumeError(f"unit {index} is not complete")
        if not unit.source.is_symlink() or os.readlink(unit.source) != str(unit.destination):
            raise ResumeError(f"unit {index} compatibility link mismatch")
        if os.path.lexists(unit.tombstone):
            raise ResumeError(f"unit {index} tombstone exists")
        unit.verify_destination_payload(manifest)
        units.append({"index": index, "stage": "complete", "unit_id": unit.unit_id,
                      "bytes": status["bytes"], "entries": status["entries"]})

    unit, status, manifest = unit_common(module, manager, 8)
    if status.get("stage") != "copied":
        raise ResumeError(f"unit 8 is not at copied checkpoint: {status.get('stage')}")
    require_plain_dir(unit.source, os.geteuid())
    require_plain_dir(unit.destination, os.geteuid())
    if os.path.lexists(unit.tombstone) or (unit.unit_dir / "policy-receipt.json").exists():
        raise ResumeError("unit 8 has an unexpected tombstone or policy receipt")
    unit.check_source_unchanged(manifest["entries"])
    unit.verify_tree(manifest["entries"], root_metadata=False)
    records = {record.get("path"): record for record in module._read_ledger(unit.ledger_path)
               if record.get("event") == "file_verified"}
    reusable_files = reusable_bytes = total_files = total_bytes = 0
    for relative, entry in manifest["entries"].items():
        if entry["kind"] != "file":
            continue
        total_files += 1
        total_bytes += entry["signature"]["size"]
        record = records.get(relative)
        if record is None:
            continue
        source_sig = module._sig(module._lstat(module._path_for(unit.source, relative), "source file"))
        destination_sig = module._sig(module._lstat(module._path_for(unit.destination, relative), "destination file"))
        if (module._same_sig(source_sig, record["source_signature"]) and
                module._same_sig(destination_sig, record["destination_signature"])):
            reusable_files += 1
            reusable_bytes += entry["signature"]["size"]
    units.append({"index": 8, "stage": "copied", "unit_id": unit.unit_id,
                  "bytes": status["bytes"], "entries": status["entries"],
                  "reusable_receipt_files": reusable_files, "reusable_receipt_bytes": reusable_bytes,
                  "total_files": total_files, "total_file_bytes": total_bytes})

    final = module.Unit(manager, 9, manager.plan["units"][9])
    if final.status()["stage"] != "new" or os.path.lexists(final.unit_dir):
        raise ResumeError("unit 9 state is not untouched")
    require_plain_dir(final.source, os.geteuid())
    if os.path.lexists(final.destination) or os.path.lexists(final.tombstone):
        raise ResumeError("unit 9 destination or tombstone unexpectedly exists")
    if (STATE / "verified-manifest.json").exists():
        raise ResumeError("final verified manifest exists before all units are complete")
    units.append({"index": 9, "stage": "new", "unit_id": final.unit_id})

    for name in OLD_LOGS:
        path = STAGE / name
        if not path.is_file() or path.is_symlink():
            raise ResumeError(f"original log missing or unsafe: {path}")

    result = {
        "schema": 1,
        "checked_at": time.time(),
        "stage": str(STAGE),
        "plan_hash": PLAN_HASH,
        "frozen_hashes": observed_hashes,
        "identity": {"euid": os.geteuid(), "egid": os.getegid()},
        "archive_mode": oct(archive_mode),
        "state_mode": oct(state_mode),
        "active_job_names": active_names,
        "copy_queue_walltime_max": maxima or None,
        "units": units,
        "resume_directory_absent": True,
        "migration_lock_available": True,
    }
    return result, qstat, queue


def submit() -> dict[str, Any]:
    report, qstat, queue = preflight()
    os.mkdir(RESUME_DIR, 0o700)
    for name in OLD_LOGS:
        durable_copy(STAGE / name, RESUME_DIR / f"820961.{name}")
    atomic_json(RESUME_DIR / "preflight.json", report)
    durable_text(RESUME_DIR / "qstat-active.txt", qstat)
    durable_text(RESUME_DIR / "qstat-copy-queue.txt", queue)
    command = ["qsub", "-N", "xray_home_r2", "-l", "walltime=72:00:00",
               "-o", str(RESUME_DIR / "pbs.out"), "-e", str(RESUME_DIR / "pbs.err"),
               str(STAGE / "scripts/kunanyi/xray_scratch_home_migration.pbs")]
    try:
        atomic_json(RESUME_DIR / "submission-start.json", {"schema": 1, "started_at": time.time(),
                                                            "command": command})
        completed = run(command)
        durable_text(RESUME_DIR / "qsub.stdout.txt", completed.stdout)
        durable_text(RESUME_DIR / "qsub.stderr.txt", completed.stderr)
        job_id = completed.stdout.strip()
        if not JOB_ID_RE.fullmatch(job_id):
            raise ResumeError(f"qsub returned an invalid job id: {job_id!r}")
        receipt = {"schema": 1, "submitted_at": time.time(), "job_id": job_id, "command": command,
                   "preflight_sha256": sha256(RESUME_DIR / "preflight.json")}
        atomic_json(RESUME_DIR / "jobid.json", receipt)
        return receipt
    except BaseException as exc:
        atomic_json(RESUME_DIR / "submission-failed.json", {"schema": 1, "failed_at": time.time(),
                                                             "command": command, "error": str(exc)})
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--submit", action="store_true", help="preserve logs and make the one permitted submission")
    parser.add_argument("--output", type=Path, help="write the read-only preflight report to this new file")
    args = parser.parse_args()
    try:
        if args.submit and args.output:
            raise ResumeError("--output cannot be combined with --submit")
        if args.submit:
            result = submit()
        else:
            result, _, _ = preflight()
            if args.output:
                if args.output.exists() or args.output.is_symlink():
                    raise ResumeError(f"output already exists: {args.output}")
                args.output.parent.mkdir(parents=True, exist_ok=True)
                atomic_json(args.output, result)
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except (OSError, ResumeError, subprocess.SubprocessError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
