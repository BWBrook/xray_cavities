from __future__ import annotations
import csv, importlib.util, json, sys, subprocess
from pathlib import Path
import pytest

BUILD = Path("scripts/science/build_three_case_lifecycle_authorization.py")
VALIDATE = Path("scripts/science/validate_three_case_lifecycle_dry_run.py")
COMPLETED = Path("docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/completed_run")

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path); assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec); sys.modules[name] = mod; spec.loader.exec_module(mod); return mod

def test_real_packet_is_exhaustive_and_dry_run(tmp_path):
    b = load(BUILD, "goal046_build")
    v = load(VALIDATE, "goal046_validate")
    completed = COMPLETED
    packet = tmp_path / "packet"
    meta = b.build_packet(completed, packet)
    result = v.validate(packet, meta["payload_ledger_sha256"], completed)
    assert result["status"] == "validated_dry_run_only"
    assert result["payload_count"] == 17153
    assert result["action_counts"]["DELETE_PROPOSED_UNIQUE_RAW"] == 148
    assert result["action_counts"]["DELETE_PROPOSED_METADATA_ONLY"] == 148
    assert result["action_counts"]["HOLD_RADIO_UNRESOLVED"] == 5501
    assert result["action_counts"]["HOLD_AMBIGUOUS"] == 3
    assert result["action_counts"]["HOLD_REGENERATION_UNPROVEN"] == 968
    assert "DELETE_PROPOSED_REGENERABLE" not in result["action_counts"]

def test_generation_is_deterministic(tmp_path):
    b = load(BUILD, "goal046_build_det")
    completed = COMPLETED
    a, c = tmp_path / "a", tmp_path / "c"; b.build_packet(completed, a); b.build_packet(completed, c)
    names = sorted(x.name for x in a.iterdir() if x.is_file())
    assert names == sorted(x.name for x in c.iterdir() if x.is_file())
    for name in names: assert (a / name).read_bytes() == (c / name).read_bytes(), name

def test_validator_rejects_digest_mismatch(tmp_path):
    b = load(BUILD, "goal046_build_mismatch"); v = load(VALIDATE, "goal046_validate_mismatch")
    completed = COMPLETED; packet = tmp_path / "p"; b.build_packet(completed, packet)
    with pytest.raises(ValueError, match="expected digest mismatch"): v.validate(packet, "0" * 64, completed)

def _packet(tmp_path, name="packet"):
    b = load(BUILD, f"goal046_build_{name}")
    completed = Path("docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/completed_run")
    packet = tmp_path / name; b.build_packet(completed, packet); return packet

def _mutate_ledger(packet, mutate):
    path = packet / "payload_ledger.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle); fields = reader.fieldnames; data = list(reader)
    mutate(data)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n"); writer.writeheader(); writer.writerows(data)

def _digest(packet):
    return json.loads((packet / "inventory_metadata.json").read_text())["payload_ledger_sha256"]

def test_validator_rejects_outside_allowlist(tmp_path):
    v = load(VALIDATE, "goal046_validate_allowlist"); packet = _packet(tmp_path, "allowlist")
    _mutate_ledger(packet, lambda data: data.__setitem__(0, {**data[0], "path": "/outside/forbidden.h5"}))
    with pytest.raises(ValueError, match="outside allowlist"): v.validate(packet, _digest(packet), COMPLETED)

def test_validator_rejects_protected_deletion_and_pair_mismatch(tmp_path):
    v = load(VALIDATE, "goal046_validate_pair"); packet = _packet(tmp_path, "pair")
    def mutate(data):
        row = next(r for r in data if r["action"] == "DELETE_PROPOSED_UNIQUE_RAW")
        row["contract_protection"] = "PROTECTED"
    _mutate_ledger(packet, mutate)
    with pytest.raises(ValueError, match="protected deletion"): v.validate(packet, _digest(packet), COMPLETED)

def test_validator_rejects_parent_traversal(tmp_path):
    v = load(VALIDATE, "goal046_validate_traversal"); packet = _packet(tmp_path, "traversal")
    _mutate_ledger(packet, lambda data: next(r for r in data if r["action"] == "DELETE_PROPOSED_UNIQUE_RAW").update(path="/scratch/bwbrook/../outside.h5"))
    with pytest.raises(ValueError, match="outside allowlist"): v.validate(packet, _digest(packet), COMPLETED)

def test_coherent_ledger_rehash_still_fails_frozen_source(tmp_path):
    v = load(VALIDATE, "goal046_validate_coherent"); packet = _packet(tmp_path, "coherent")
    _mutate_ledger(packet, lambda data: data[0].update(relative_path="tampered-but-rehashed"))
    import hashlib
    digest = hashlib.sha256((packet / "payload_ledger.csv").read_bytes()).hexdigest()
    metadata = json.loads((packet / "inventory_metadata.json").read_text()); metadata["payload_ledger_sha256"] = digest; (packet / "inventory_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="ledger source inventory mismatch"): v.validate(packet, digest, COMPLETED)

def test_validator_rejects_stale_active_job_gate(tmp_path):
    v = load(VALIDATE, "goal046_validate_stale"); packet = _packet(tmp_path, "stale")
    gate = (packet / "active_job_gate.csv").read_text().replace("2026-07-23T22:48:47Z", "2026-07-20T22:48:47Z")
    (packet / "active_job_gate.csv").write_text(gate)
    digest = __import__("hashlib").sha256((packet / "active_job_gate.csv").read_bytes()).hexdigest()
    metadata = json.loads((packet / "inventory_metadata.json").read_text()); metadata["active_job_gate_sha256"] = digest; (packet / "inventory_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValueError, match="active-job gate stale"): v.validate(packet, _digest(packet), COMPLETED, now=__import__("datetime").datetime(2026, 7, 24, tzinfo=__import__("datetime").timezone.utc))

def test_validator_rejects_manifest_tamper(tmp_path):
    v = load(VALIDATE, "goal046_validate_manifest"); packet = _packet(tmp_path, "manifest")
    (packet / "active_job_gate.csv").write_text((packet / "active_job_gate.csv").read_text().replace(",0,passed", ",1,passed"))
    with pytest.raises(ValueError, match="active-job gate failed"): v.validate(packet, _digest(packet), COMPLETED)

def test_validator_rejects_omitted_manifest_entry(tmp_path):
    v = load(VALIDATE, "goal046_validate_omitted"); packet = _packet(tmp_path, "omitted")
    manifest = packet / "local_asset_manifest.sha256"; lines = manifest.read_text().splitlines(); manifest.write_text("\n".join(lines[:-1]) + "\n")
    with pytest.raises(ValueError, match="local asset manifest name set mismatch"): v.validate(packet, _digest(packet), COMPLETED)

def test_cli_requires_expected_digest_and_completed():
    result = subprocess.run(["uv", "run", "python", str(VALIDATE), "--packet", "."], capture_output=True, text=True)
    assert result.returncode != 0 and "expected-digest" in result.stderr

def test_validator_has_no_execute_surface():
    text = VALIDATE.read_text()
    assert "unlink(" not in text and "os.remove" not in text
