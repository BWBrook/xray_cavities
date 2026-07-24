#!/usr/bin/env python3
"""Fail-closed validator for the Goal 046 lifecycle proposal.

There is intentionally no execute mode or deletion primitive in this module.
"""
from __future__ import annotations
import argparse, csv, hashlib, json, re, datetime
from pathlib import Path

SHA_RE = re.compile(r"^[0-9a-f]{64}$")
DELETES = {"DELETE_PROPOSED_UNIQUE_RAW", "DELETE_PROPOSED_METADATA_ONLY", "DELETE_PROPOSED_REGENERABLE"}
FROZEN_CONTRACT_DIGEST = "706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d"

def rows(path: Path):
    with path.open(newline="") as h:
        reader = csv.DictReader(h)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)): raise ValueError(f"bad header: {path}")
        return list(reader)

def paired(path: str) -> str:
    return path[:-2] + "xmf" if path.endswith(".h5") else path[:-3] + "h5"

def validate(packet: Path, expected_digest: str, completed: Path, now: datetime.datetime | None = None) -> dict[str, object]:
    ledger = rows(packet / "payload_ledger.csv")
    if len(ledger) != 17153: raise ValueError(f"payload count {len(ledger)}")
    seen = set(); counts = {}
    expected_actions = {"DELETE_PROPOSED_METADATA_ONLY": 148, "DELETE_PROPOSED_UNIQUE_RAW": 148, "HOLD_AMBIGUOUS": 3, "HOLD_RADIO_UNRESOLVED": 5501, "HOLD_REGENERATION_UNPROVEN": 968, "KEEP_PROTECTED": 65, "KEEP_PROVENANCE": 10320}
    for r in ledger:
        if r["path"] in seen: raise ValueError(f"duplicate path: {r['path']}")
        seen.add(r["path"]); action = r["action"]; counts[action] = counts.get(action, 0) + 1
        if action in DELETES:
            if not SHA_RE.fullmatch(r.get("sha256", "")): raise ValueError(f"missing deletion hash: {r['path']}")
            if r["file_type"] != "regular" or r["identity_status"] != "stable": raise ValueError(f"unsafe deletion identity: {r['path']}")
            if r["dry_run_only"] != "true": raise ValueError(f"non-dry-run row: {r['path']}")
            if r["catalogue_membership"] == "missing": raise ValueError(f"missing catalogue: {r['path']}")
        if action == "HOLD_RADIO_UNRESOLVED" and not Path(r["path"]).name.startswith("particles") and r["data_class"] != "HOLD_RADIO_UNRESOLVED": raise ValueError("radio hold mismatch")
        if action in {"DELETE_PROPOSED_UNIQUE_RAW", "DELETE_PROPOSED_METADATA_ONLY"} and r["root_id"].startswith("production_") and r["pair_status"] != "complete": raise ValueError(f"incomplete pair status: {r['path']}")
        if action in DELETES and r["catalogue_membership"] == "missing": raise ValueError(f"missing catalogue: {r['path']}")
        if action in DELETES:
            if r["contract_protection"] != "UNPROTECTED": raise ValueError(f"protected deletion row: {r['path']}")
            if r["file_type"] == "symlink": raise ValueError(f"symlink deletion row: {r['path']}")
    required_evidence = [completed / "review_inventory/inventory/payload_inventory.csv", completed / "review_inventory/protected_path_contract.csv", completed / "review_inventory/remote_root_allowlist.csv", completed / "review_inventory/inventory/inventory_metadata.json", completed / "catalogue_snapshot"]
    if any(not p.exists() for p in required_evidence): raise ValueError("frozen completed evidence missing")
    allowlist = rows(packet / "remote_root_allowlist.csv")
    if (packet / "remote_root_allowlist.csv").read_bytes() != (completed / "review_inventory/remote_root_allowlist.csv").read_bytes(): raise ValueError("allowlist contract mismatch")
    if (packet / "protected_path_contract.csv").read_bytes() != (completed / "review_inventory/protected_path_contract.csv").read_bytes(): raise ValueError("protected contract mismatch")
    roots = [Path(r["root_path"]) for r in allowlist]
    for r in ledger:
        normalized = Path(r["path"])
        if not normalized.is_absolute() or ".." in normalized.parts or not any(normalized.is_relative_to(root) for root in roots): raise ValueError(f"outside allowlist: {r['path']}")
    by_path = {r["path"]: r for r in ledger}
    catalogue_root = completed / "catalogue_snapshot"
    catalogue_ids = {}
    for root in catalogue_root.glob("production_*"):
        for stream in root.glob("*.h5.out"):
            kind = stream.name.split(".", 1)[0]
            catalogue_ids[(root.name, kind)] = {line.split()[0].zfill(4) for line in stream.read_text().splitlines() if line.split()}
    for r in ledger:
        if r["root_id"].startswith("production_") and r["file_type"] == "regular" and Path(r["path"]).name.startswith("data.") and Path(r["path"]).name.endswith(".h5") and r["catalogue_membership"] != "present": raise ValueError(f"wrong catalogue membership: {r['path']}")
        if r["root_id"].startswith("production_") and r["file_type"] == "regular" and Path(r["path"]).name.startswith("data.") and Path(r["path"]).name.endswith(".h5"):
            match = re.match(r"data\.(\d{4})\.(flt|dbl)\.h5$", Path(r["path"]).name)
            if match and match.group(1) not in catalogue_ids.get((r["root_id"], match.group(2)), set()): raise ValueError(f"recomputed catalogue mismatch: {r['path']}")
        if r["root_id"].startswith("production_") and r["action"] in {"DELETE_PROPOSED_UNIQUE_RAW", "DELETE_PROPOSED_METADATA_ONLY"}:
            suffix = ".xmf" if r["path"].endswith(".h5") else ".h5"
            pair = paired(r["path"])
            expected = "DELETE_PROPOSED_METADATA_ONLY" if suffix == ".xmf" else "DELETE_PROPOSED_UNIQUE_RAW"
            if pair not in by_path or by_path[pair]["action"] != expected: raise ValueError(f"action-inconsistent pair: {r['path']}")
    if counts != expected_actions: raise ValueError(f"action counts mismatch: {counts}")
    gate = rows(packet / "active_job_gate.csv")
    if len(gate) != 1 or gate[0]["status"] != "passed" or gate[0]["active_job_rows"] != "0" or gate[0]["command_exit_status"] != "0": raise ValueError("active-job gate failed")
    metadata = json.loads((packet / "inventory_metadata.json").read_text())
    if metadata.get("contract_digest_sha256") != FROZEN_CONTRACT_DIGEST: raise ValueError("metadata contract digest mismatch")
    if not metadata.get("dry_run_only") or metadata.get("deletion_capability") is not False: raise ValueError("unsafe metadata flags")
    ledger_digest = hashlib.sha256((packet / "payload_ledger.csv").read_bytes()).hexdigest()
    if metadata.get("active_job_gate_sha256") != hashlib.sha256((packet / "active_job_gate.csv").read_bytes()).hexdigest(): raise ValueError("active-job gate digest mismatch")
    external = rows(packet / "external_archive_manifest.csv")
    if metadata.get("external_archive_manifest_sha256") != hashlib.sha256((packet / "external_archive_manifest.csv").read_bytes()).hexdigest(): raise ValueError("external archive manifest digest mismatch")
    if any(r["status"] not in {"passed", "metadata_only_defect_recorded", "not_covered"} for r in external): raise ValueError("external archive validation failed")
    archive_members = [r for r in external if r["scope"] == "archive_member"]
    archive_row = next((r for r in external if r["scope"] == "archive"), None)
    if len(archive_members) != int(metadata.get("archive_member_count", -1)) or not archive_row or metadata.get("archive_sha256") != archive_row["observed_sha256"] or metadata.get("archive_listability") != "passed": raise ValueError("archive binding mismatch")
    source_inventory = completed / "review_inventory/inventory/payload_inventory.csv"
    source_rows = rows(source_inventory)
    source_map = {r["path"]: r for r in source_rows}
    ledger_source = {r["path"]: {k: r[k] for k in source_rows[0]} for r in ledger}
    if ledger_source != source_map: raise ValueError("ledger source inventory mismatch")
    hold_rows = {r["path"]: r["action"] for r in ledger if r["action"].startswith("HOLD_")}
    register_rows = {r["path"]: r["action"] for r in rows(packet / "active_hold_register.csv")}
    if hold_rows != register_rows: raise ValueError("hold register mismatch")
    transcript = completed / "remote_logs/active_job_gate_2026-07-24.txt"
    if gate[0].get("transcript_path") != "completed_run/remote_logs/active_job_gate_2026-07-24.txt" or metadata.get("active_job_transcript_sha256") != hashlib.sha256(transcript.read_bytes()).hexdigest() or gate[0].get("transcript_sha256") != hashlib.sha256(transcript.read_bytes()).hexdigest(): raise ValueError("active-job transcript mismatch")
    checked = datetime.datetime.fromisoformat(gate[0]["checked_utc"].replace("Z", "+00:00"))
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if (now - checked).total_seconds() > float(metadata.get("freshness_threshold_hours", 48)) * 3600: raise ValueError("active-job gate stale")
    if metadata.get("payload_ledger_sha256") != ledger_digest: raise ValueError("ledger digest mismatch")
    if expected_digest != ledger_digest: raise ValueError("expected digest mismatch")
    for line in (packet / "local_asset_manifest.sha256").read_text().splitlines():
        digest, name = line.split("  ", 1); path = packet / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest: raise ValueError(f"local asset manifest mismatch: {name}")
    manifest_names = {line.split("  ", 1)[1] for line in (packet / "local_asset_manifest.sha256").read_text().splitlines()}
    actual_names = {p.name for p in packet.iterdir() if p.is_file() and p.name != "local_asset_manifest.sha256"}
    if manifest_names != actual_names: raise ValueError("local asset manifest name set mismatch")
    return {"status": "validated_dry_run_only", "payload_count": len(ledger), "action_counts": dict(sorted(counts.items())), "payload_ledger_sha256": ledger_digest}

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--packet", type=Path, required=True)
    p.add_argument("--expected-digest", required=True)
    p.add_argument("--completed", type=Path, required=True)
    args = p.parse_args()
    print(json.dumps(validate(args.packet, args.expected_digest, args.completed), sort_keys=True))

if __name__ == "__main__": main()
