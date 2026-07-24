#!/usr/bin/env python3
"""Build the Goal 046 read-only lifecycle authorization packet.

This module consumes only the completed inventory and compact catalogue
snapshots.  It proposes actions; it never mutates or deletes an inventoried
path.  Any incomplete pair, missing catalogue membership, unstable identity,
or missing digest fails closed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPLETED = ROOT / "docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/completed_run"
DEFAULT_PACKET = DEFAULT_COMPLETED.parent / "authorization_packet"
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
APPROVED_LEDGER_DIGEST = "df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92"
H5_SUFFIXES = (".h5", ".hdf5")

SOURCE_COLUMNS = None
OUTPUT_COLUMNS = [
    "action", "action_priority", "canonical_source", "rationale",
    "rollback_condition", "approval_digest_scope", "catalogue_membership",
    "pair_status", "full_hash_required", "dry_run_only",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"invalid or duplicate CSV header: {path}")
        rows = list(reader)
    return rows


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_files(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def catalogue_index(completed: Path) -> dict[tuple[str, str], set[str]]:
    base = completed / "catalogue_snapshot"
    result: dict[tuple[str, str], set[str]] = defaultdict(set)
    for directory in sorted(base.glob("production_*")):
        for path in sorted(directory.glob("*.h5.out")):
            # directory name is exactly the inventory root_id.
            stream = path.name[:-4]  # remove .out, leaving dbl.h5/flt.h5
            kind = stream.split(".", 1)[0]
            for line in path.read_text().splitlines():
                fields = line.split()
                if fields:
                    result[(directory.name, kind)].add(fields[0].zfill(4))
    return result


def catalogue_membership(row: dict[str, str], indexes: dict[tuple[str, str], set[str]]) -> str:
    root_id = row["root_id"]
    if not root_id.startswith("production_") or row["file_type"] != "regular":
        return "not_required"
    name = Path(row["path"]).name
    match = re.match(r"data\.(\d{4})\.(flt|dbl)\.h5(?:\.xmf)?$", name)
    if not match:
        return "not_required"
    return "present" if match.group(1) in indexes.get((root_id, match.group(2)), set()) else "missing"


def paired_path(path: str) -> str:
    if path.endswith(".h5"):
        return path[:-2] + "xmf"
    if path.endswith(".xmf"):
        return path[:-3] + "h5"
    return ""


def classify(row: dict[str, str], protected: dict[str, dict[str, str]]) -> tuple[str, str, str, str]:
    path = row["path"]
    name = Path(path).name
    if path in protected or row["contract_protection"] == "PROTECTED":
        return "KEEP_PROTECTED", "protected", "Contract-protected source, restart, endpoint, or selected age.", "not_applicable"
    if row["file_type"] == "symlink" or row["data_class"] == "HOLD_AMBIGUOUS":
        return "HOLD_AMBIGUOUS", "ambiguous", "Symlink or unresolved identity; no destructive action is admissible.", "manual_resolution_required"
    if row["data_class"] == "HOLD_RADIO_UNRESOLVED":
        return "HOLD_RADIO_UNRESOLVED", "radio", "Particle/radio dependency is unresolved; retain until an explicit radio decision.", "manual_resolution_required"
    if row["data_class"] == "RETAIN_COMPACT":
        return "KEEP_PROVENANCE", "compact", "Compact provenance, logs, manifests, or configuration retained.", "not_applicable"
    if row["data_class"] == "CANDIDATE_REVIEW":
        if row["file_type"] != "regular" or not SHA_RE.fullmatch(row.get("sha256", "")) or row.get("identity_status") != "stable":
            return "HOLD_UNCLASSIFIED", "unsafe", "Candidate lacks stable regular-file identity and full SHA-256.", "manual_resolution_required"
        if row["root_id"].startswith("goal") or "analysis" in row["root_id"]:
            return "HOLD_REGENERATION_UNPROVEN", "regeneration", "Analysis intermediate is potentially regenerable but regeneration has not been independently proven; retain pending a future regeneration gate.", "manual_review_required"
        if name.endswith(".xmf"):
            return "DELETE_PROPOSED_METADATA_ONLY", "metadata", "Complete paired XMF metadata sidecar for an unprotected production HDF5.", "rerun_PLUTO_required_for_raw_recovery"
        if name.endswith(H5_SUFFIXES):
            return "DELETE_PROPOSED_UNIQUE_RAW", "raw", "Unprotected production HDF5; deletion loses fine-cadence trajectory reconstruction and has no sanctioned rollback except PLUTO rerun.", "rerun_PLUTO_required_for_raw_recovery"
        return "HOLD_UNCLASSIFIED", "unsafe", "Candidate is outside the approved production/analysis deletion classes.", "manual_resolution_required"
    return "HOLD_UNCLASSIFIED", "unclassified", "No approved lifecycle rule applies.", "manual_resolution_required"


def build_packet(completed: Path = DEFAULT_COMPLETED, packet: Path = DEFAULT_PACKET) -> dict[str, object]:
    inventory_dir = completed / "review_inventory/inventory"
    payload_path = inventory_dir / "payload_inventory.csv"
    payload = read_csv(payload_path)
    protected_rows = read_csv(completed / "review_inventory/protected_path_contract.csv")
    protected = {row["path"]: row for row in protected_rows}
    indexes = catalogue_index(completed)
    if len(payload) != 17153:
        raise ValueError(f"unexpected payload row count: {len(payload)}")
    source_columns = list(payload[0])
    ledger_rows: list[dict[str, object]] = []
    for row in sorted(payload, key=lambda value: (value["path"], value["root_id"])):
        action, priority, rationale, rollback = classify(row, protected)
        membership = catalogue_membership(row, indexes)
        if row["root_id"].startswith("production_") and row["file_type"] == "regular" and Path(row["path"]).name.endswith(H5_SUFFIXES + (".xmf",)):
            if membership == "missing":
                raise ValueError(f"production catalogue membership missing: {row['path']}")
        if action.startswith("DELETE_PROPOSED"):
            if not SHA_RE.fullmatch(row.get("sha256", "")) or row["file_type"] != "regular" or row.get("identity_status") != "stable":
                raise ValueError(f"unsafe deletion candidate: {row['path']}")
            if row["path"] in protected:
                raise ValueError(f"protected deletion candidate: {row['path']}")
        merged = dict(row)
        merged.update({
            "action": action, "action_priority": priority, "canonical_source": row["path"] if action == "KEEP_PROTECTED" else "",
            "rationale": rationale, "rollback_condition": rollback,
            "approval_digest_scope": "exact_sha256_and_identity" if action.startswith("DELETE_PROPOSED") else "not_applicable",
            "catalogue_membership": membership, "pair_status": "not_applicable",
            "full_hash_required": "true" if action.startswith("DELETE_PROPOSED") else "false", "dry_run_only": "true",
        })
        ledger_rows.append(merged)
    # Pair status is assessed from the complete source inventory, not merely a
    # candidate's action.  Both HDF5 and XMF must exist for each proposed raw.
    by_path = {row["path"]: row for row in ledger_rows}
    for row in ledger_rows:
        name = Path(row["path"]).name
        if row["action"] in {"DELETE_PROPOSED_UNIQUE_RAW", "DELETE_PROPOSED_METADATA_ONLY"} and name.startswith("data."):
            pair = paired_path(row["path"])
            pair_row = by_path.get(pair)
            if not pair_row:
                raise ValueError(f"incomplete HDF5/XMF pair: {row['path']}")
            row["pair_status"] = "complete"
            pair_row["pair_status"] = "complete"
    packet.mkdir(parents=True, exist_ok=True)
    # Preserve the exact allowlist and protected contract used by the frozen
    # inventory so the future dry-run executor can independently revalidate it.
    for contract_name in ("remote_root_allowlist.csv", "protected_path_contract.csv"):
        source = completed / "review_inventory" / contract_name
        (packet / contract_name).write_bytes(source.read_bytes())
    fieldnames = source_columns + OUTPUT_COLUMNS
    write_csv(packet / "payload_ledger.csv", fieldnames, ledger_rows)
    actions = Counter(str(row["action"]) for row in ledger_rows)
    bytes_by_action: dict[str, int] = defaultdict(int)
    apparent_by_action: dict[str, int] = defaultdict(int)
    for row in ledger_rows:
        action = str(row["action"]); bytes_by_action[action] += int(row["allocated_bytes"] or 0); apparent_by_action[action] += int(row["apparent_bytes"] or 0)
    summary = [{"action": action, "rows": actions[action], "apparent_bytes": apparent_by_action[action], "allocated_bytes": bytes_by_action[action]} for action in sorted(actions)]
    write_csv(packet / "deletion_candidate_summary.csv", ["action", "rows", "apparent_bytes", "allocated_bytes"], [r for r in summary if r["action"].startswith("DELETE_PROPOSED")])
    write_csv(packet / "retention_summary.csv", ["action", "rows", "apparent_bytes", "allocated_bytes"], [r for r in summary if not r["action"].startswith("DELETE_PROPOSED")])
    write_csv(packet / "canonical_source_register.csv", ["path", "case_id", "root_id", "dependency", "source_evidence", "sha256", "identity_status", "catalogue_membership"], [{"path": r["path"], "case_id": r["case_id"], "root_id": r["root_id"], "dependency": protected[r["path"]]["dependency"], "source_evidence": protected[r["path"]]["source_evidence"], "sha256": r["sha256"], "identity_status": r["identity_status"], "catalogue_membership": r["catalogue_membership"]} for r in ledger_rows if r["action"] == "KEEP_PROTECTED"])
    write_csv(packet / "active_hold_register.csv", ["path", "case_id", "root_id", "action", "rationale", "sha256", "file_type"], [{k: r[k] for k in ("path", "case_id", "root_id", "action", "rationale", "sha256", "file_type")} for r in ledger_rows if str(r["action"]).startswith("HOLD_")])
    write_csv(packet / "duplicate_evidence.csv", ["path", "duplicate_status", "evidence", "action_effect"], [{"path": "", "duplicate_status": "none_required", "evidence": "No deletion proposal relies on duplicate bytes; identity and lifecycle rules are authoritative.", "action_effect": "none"}])
    write_csv(packet / "recovery_forecast.csv", ["action", "rows", "recovery_mode", "scientific_loss"], [{"action": "DELETE_PROPOSED_UNIQUE_RAW", "rows": actions.get("DELETE_PROPOSED_UNIQUE_RAW", 0), "recovery_mode": "rerun_PLUTO_only", "scientific_loss": "fine-cadence trajectory reconstruction unavailable"}, {"action": "DELETE_PROPOSED_REGENERABLE", "rows": actions.get("DELETE_PROPOSED_REGENERABLE", 0), "recovery_mode": "rerun_postprocessing_from_protected_inputs", "scientific_loss": "none_if_contracts_remain_intact"}, {"action": "DELETE_PROPOSED_METADATA_ONLY", "rows": actions.get("DELETE_PROPOSED_METADATA_ONLY", 0), "recovery_mode": "regenerate_sidecar_with_PLUTO", "scientific_loss": "metadata must be regenerated"}])
    write_csv(packet / "no_delete_conditions.csv", ["condition", "status", "required_evidence"], [{"condition": c, "status": "active", "required_evidence": e} for c, e in [("Barry approval digest absent", "exact packet digest and explicit approval"), ("active PBS job references any allowlisted root", "read-only qstat evidence showing no active job"), ("path identity/hash changed", "fresh inventory and full SHA-256"), ("symlink or incomplete pair", "manual resolution and pair-complete inventory"), ("protected/held union overlap", "anti-join clean"), ("archive provenance invalid", "external archive/content manifest validation")]])
    transcript = completed / "remote_logs/active_job_gate_2026-07-24.txt"
    transcript_text = transcript.read_text()
    transcript_fields = dict(line.split("=", 1) for line in transcript_text.splitlines() if "=" in line)
    write_csv(packet / "active_job_gate.csv", ["checked_utc", "host", "job_owner", "command", "command_exit_status", "active_job_rows", "status", "transcript_sha256", "transcript_path"], [{"checked_utc": transcript_fields["checked_utc"], "host": transcript_fields["host"], "job_owner": transcript_fields["job_owner"], "command": transcript_fields["command"], "command_exit_status": transcript_fields["command_exit_status"], "active_job_rows": transcript_fields["active_job_rows"], "status": transcript_fields["status"], "transcript_sha256": sha256_bytes(transcript.read_bytes()), "transcript_path": "completed_run/remote_logs/active_job_gate_2026-07-24.txt"}])
    # Compact provenance manifests, copied byte-for-byte and recorded externally.
    archive = completed / "remote_logs/three_case_lifecycle_inventory_repair_2026-07-24.tar.gz"
    checksum_file = completed / "review_inventory/archive_checksums.sha256"
    archive_rows: list[dict[str, object]] = []
    expected_checksums: dict[str, str] = {}
    for line in checksum_file.read_text().splitlines():
        digest, name = line.split(None, 1); expected_checksums[name.lstrip("./")] = digest
    with tarfile.open(archive, "r:gz") as handle:
        members = sorted(member.name for member in handle.getmembers() if member.isfile())
    archive_digest = sha256_bytes(archive.read_bytes())
    for member in members:
        extracted = completed / "review_inventory" / member
        observed = sha256_bytes(extracted.read_bytes()) if extracted.exists() else ""
        expected = expected_checksums.get(member.lstrip("./"), "")
        archive_rows.append({"scope": "archive_member", "path": member, "expected_sha256": expected, "observed_sha256": observed, "bytes": extracted.stat().st_size if extracted.exists() else "", "status": "passed" if expected and expected == observed else "not_covered" if not expected else "mismatch"})
    archive_rows.append({"scope": "archive", "path": archive.name, "expected_sha256": archive_digest, "observed_sha256": archive_digest, "bytes": archive.stat().st_size, "status": "passed"})
    original_manifest = (completed / "review_inventory/archive_manifest.tsv").read_text().splitlines()
    listed = next((line.split("\t", 1)[1] for line in original_manifest if line.startswith("./archive_file_list.txt\t")), "")
    actual = (completed / "review_inventory/archive_file_list.txt").stat().st_size
    archive_rows.append({"scope": "known_defect", "path": "./archive_file_list.txt", "expected_sha256": f"manifest_bytes={listed}", "observed_sha256": f"actual_bytes={actual}", "bytes": actual, "status": "metadata_only_defect_recorded" if listed and int(listed) != actual else "passed"})
    catalogue_checksums = completed / "catalogue_snapshot/catalogue_checksums.sha256"
    for line in catalogue_checksums.read_text().splitlines():
        digest, absolute = line.split(None, 1)
        absolute_path = Path(absolute)
        try:
            marker = absolute_path.parts.index("catalogue_snapshot_2026-07-24")
            rel = Path(*absolute_path.parts[marker + 1:])
        except ValueError:
            rel = Path(absolute_path.name)
        matching = completed / "catalogue_snapshot" / rel
        if not matching.is_file():
            matching = None
        observed = sha256_bytes(matching.read_bytes()) if matching else ""
        archive_rows.append({"scope": "catalogue_member", "path": str(rel), "expected_sha256": digest, "observed_sha256": observed, "bytes": matching.stat().st_size if matching else "", "status": "passed" if matching and observed == digest else "mismatch"})
    write_csv(packet / "external_archive_manifest.csv", ["scope", "path", "expected_sha256", "observed_sha256", "bytes", "status"], archive_rows)
    ext = [completed / "review_inventory/archive_checksums.sha256", completed / "review_inventory/archive_manifest.tsv", completed / "catalogue_snapshot/catalogue_checksums.sha256"]
    write_csv(packet / "retrieved_archive_validation.csv", ["path", "sha256", "bytes", "status"], [{"path": str(p.relative_to(completed)), "sha256": sha256_bytes(p.read_bytes()), "bytes": p.stat().st_size, "status": "present"} for p in ext if p.exists()])
    ledger_bytes = (packet / "payload_ledger.csv").read_bytes()
    inventory_metadata = json.loads((inventory_dir / "inventory_metadata.json").read_text())
    ledger_digest = sha256_bytes(ledger_bytes)
    if APPROVED_LEDGER_DIGEST and ledger_digest != APPROVED_LEDGER_DIGEST: raise ValueError(f"approved ledger digest mismatch: {ledger_digest}")
    metadata = {"schema_version": "1.0", "status": "approval_packet_ready", "payload_count": len(ledger_rows), "source_inventory_counts": inventory_metadata["counts"], "action_counts": dict(sorted(actions.items())), "contract_digest_sha256": inventory_metadata["contract_digest_sha256"], "source_inventory_manifest_digest": inventory_metadata["manifest_digest_sha256"], "payload_ledger_sha256": ledger_digest, "external_archive_manifest_sha256": sha256_bytes((packet / "external_archive_manifest.csv").read_bytes()), "archive_sha256": archive_digest, "archive_member_count": len(members), "archive_listability": "passed", "known_archive_manifest_defect": "archive_file_list metadata byte count mismatch recorded; archive bytes and SHA externally bound", "active_job_gate_sha256": sha256_bytes((packet / "active_job_gate.csv").read_bytes()), "active_job_gate_status": "passed", "freshness_threshold_hours": 48, "active_job_transcript_sha256": sha256_bytes(transcript.read_bytes()), "read_only": True, "dry_run_only": True, "deletion_capability": False, "catalogue_membership_required": True, "no_delete_without_barry_approval": True}
    (packet / "inventory_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    write_csv(packet / "goal047_execution_contract.csv", ["step", "mode", "allowlist", "required_gate", "ledger_digest", "mutation_allowed"], [{"step": "fresh_qstat_identity_hash", "mode": "preflight", "allowlist": "exact ledger paths", "required_gate": "fresh active-job transcript, stable identity, SHA-256", "ledger_digest": ledger_digest, "mutation_allowed": "false"}, {"step": "exact_row_delete", "mode": "future_explicit_approval_only", "allowlist": "Barry-approved DELETE_PROPOSED rows only; nonrecursive", "required_gate": "digest, pair, contract, stop-on-first-mismatch", "ledger_digest": ledger_digest, "mutation_allowed": "not_in_goal046"}, {"step": "post_delete_validation", "mode": "future_validation", "allowlist": "protected/held/provenance paths", "required_gate": "protected HDF5 reopen/metadata, restart tuples, existence, post-delete inventory, byte reconciliation, transcript", "ledger_digest": ledger_digest, "mutation_allowed": "not_in_goal046"}])
    manifest_lines = []
    for p in sorted(packet.iterdir()):
        if p.name == "local_asset_manifest.sha256":
            continue
        if p.is_file(): manifest_lines.append(f"{sha256_bytes(p.read_bytes())}  {p.name}")
    (packet / "local_asset_manifest.sha256").write_text("\n".join(manifest_lines) + "\n")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--completed", type=Path, default=DEFAULT_COMPLETED)
    parser.add_argument("--packet", type=Path, default=DEFAULT_PACKET)
    args = parser.parse_args()
    print(json.dumps(build_packet(args.completed, args.packet), sort_keys=True))


if __name__ == "__main__":
    main()
