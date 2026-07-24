from __future__ import annotations

import csv
import dataclasses
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest


SCRIPT = Path("scripts/science/execute_three_case_lifecycle_compaction.py")


def load_module():
    spec = importlib.util.spec_from_file_location("goal047_executor", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, base: Path, files: list[Path]) -> None:
    lines = []
    for item in sorted(files):
        lines.append(f"{sha(item)}  {item.relative_to(base).as_posix()}\n")
    path.write_text("".join(lines))


@dataclasses.dataclass
class Synthetic:
    module: object
    root: Path
    h5: Path
    xmf: Path
    protected: Path
    held: Path
    stage: Path
    packet: Path
    completed: Path
    evidence: Path
    paths: object
    policy: object
    job_id: str
    source_rows: list[dict[str, str]]

    def candidates_exist(self) -> bool:
        return self.h5.exists() and self.xmf.exists()


def source_row(module, root: Path, path: Path, *, protection: str) -> dict[str, str]:
    st = os.lstat(path)
    return {
        "case_id": "C-HI",
        "root_id": "production_synthetic",
        "root_path": str(root),
        "root_kind": "production",
        "path": str(path),
        "relative_path": str(path.relative_to(root)),
        "resolved_path": str(path),
        "file_type": "regular",
        "link_target": "",
        "symlink_target_status": "not_applicable",
        "device": str(st.st_dev),
        "inode": str(st.st_ino),
        "apparent_bytes": str(st.st_size),
        "allocated_bytes": str(st.st_blocks * 512),
        "mtime_ns": str(st.st_mtime_ns),
        "data_class": "KEEP" if protection == "PROTECTED" else "CANDIDATE_REVIEW",
        "contract_protection": protection,
        "dependency": "synthetic",
        "source_evidence": "synthetic fixture",
        "hash_policy": "full_sha256",
        "sha256": sha(path),
        "sha256_status": "hashed",
        "hash_provenance": "synthetic_sha256",
        "identity_method": "lstat_pre_and_post_read",
        "identity_status": "stable",
        "hdf5_status": "not_hdf5",
        "hdf5_timestep": "",
        "hdf5_time_code": "",
        "hdf5_time_myr": "",
        "hdf5_shape": "",
        "hdf5_datasets": "",
    }


def ledger_row(module, source: dict[str, str], action: str) -> dict[str, str]:
    row = dict(source)
    row.update(
        {
            "action": action,
            "action_priority": "test",
            "canonical_source": "",
            "rationale": "synthetic",
            "rollback_condition": "synthetic",
            "approval_digest_scope": "synthetic",
            "catalogue_membership": (
                "present" if action == module.DELETE_HDF5 else "not_required"
            ),
            "pair_status": (
                "complete" if action in module.DELETE_ACTIONS else "not_applicable"
            ),
            "full_hash_required": (
                "true" if action in module.DELETE_ACTIONS else "false"
            ),
            "dry_run_only": "true",
        }
    )
    if action == "HOLD_REGENERATION_UNPROVEN":
        row["data_class"] = "CANDIDATE_REVIEW"
    return row


def packet_dummy_files(module, packet: Path) -> None:
    for name in module.REQUIRED_PACKET_FILES:
        path = packet / name
        if path.exists():
            continue
        if name.endswith(".json"):
            path.write_text("{}\n")
        else:
            path.write_text("field,value\nsynthetic,synthetic\n")


def refresh_packet(fx: Synthetic) -> None:
    module = fx.module
    metadata_path = fx.packet / "inventory_metadata.json"
    ledger_rows = list(
        csv.DictReader((fx.packet / "payload_ledger.csv").open())
    )
    action_counts: dict[str, int] = {}
    for row in ledger_rows:
        action_counts[row["action"]] = action_counts.get(row["action"], 0) + 1
    metadata = {
        "payload_ledger_sha256": sha(fx.packet / "payload_ledger.csv"),
        "payload_count": len(ledger_rows),
        "action_counts": action_counts,
        "dry_run_only": True,
        "deletion_capability": False,
    }
    metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n")
    write_csv(
        fx.packet / "goal047_execution_contract.csv",
        [
            "step",
            "mode",
            "allowlist",
            "required_gate",
            "ledger_digest",
            "mutation_allowed",
        ],
        [
            {
                "step": "synthetic",
                "mode": "preflight",
                "allowlist": "exact",
                "required_gate": "all",
                "ledger_digest": metadata["payload_ledger_sha256"],
                "mutation_allowed": "false",
            }
        ],
    )
    packet_files = [
        fx.packet / name for name in sorted(module.REQUIRED_PACKET_FILES)
    ]
    write_manifest(
        fx.packet / "local_asset_manifest.sha256",
        fx.packet,
        packet_files,
    )
    refresh_stage_manifest(fx)


def refresh_completed_manifest(fx: Synthetic) -> None:
    files = [
        path
        for path in fx.completed.rglob("*")
        if path.is_file()
    ]
    manifest = fx.stage / "goal046_completed_evidence_manifest.sha256"
    write_manifest(manifest, fx.completed, files)
    refresh_stage_manifest(fx)


def refresh_stage_manifest(fx: Synthetic) -> None:
    manifest = fx.stage / "goal047_staged_input_manifest.sha256"
    files = [
        fx.stage / "approval_receipt.json",
        fx.stage / "execute_three_case_lifecycle_compaction.py",
        fx.stage / "three_case_lifecycle_compaction.pbs",
        fx.stage / "goal046_completed_evidence_manifest.sha256",
        fx.packet / "payload_ledger.csv",
        fx.packet / "local_asset_manifest.sha256",
    ]
    if all(path.exists() for path in files):
        write_manifest(manifest, fx.stage, files)


def refresh_receipt_and_policy(fx: Synthetic) -> None:
    module = fx.module
    ledger = fx.packet / "payload_ledger.csv"
    rows = list(csv.DictReader(ledger.open()))
    digest = sha(ledger)
    hdf5 = sum(row["action"] == module.DELETE_HDF5 for row in rows)
    xmf = sum(row["action"] == module.DELETE_XMF for row in rows)
    allocated = sum(
        int(row["allocated_bytes"])
        for row in rows
        if row["action"] in module.DELETE_ACTIONS
    )
    fx.policy = module.ExecutionPolicy(
        ledger_sha256=digest,
        confirmation_token="SYNTHETIC_EXACT_CONFIRMATION",
        hdf5_count=hdf5,
        xmf_count=xmf,
        allocated_bytes=allocated,
        payload_count=len(rows),
        hash_workers=2,
        lock_path=fx.paths.lock_path,
        production_frozen=False,
        trusted_stage_root=fx.stage,
        trusted_evidence_root=fx.evidence,
    )
    (fx.stage / "approval_receipt.json").write_text(
        json.dumps(
            {
                "approval_status": "approved",
                "approved_payload_ledger_sha256": digest,
                "approved_row_count": hdf5 + xmf,
                "approved_hdf5_count": hdf5,
                "approved_xmf_count": xmf,
                "approved_allocated_bytes": allocated,
                "confirmation_token": fx.policy.confirmation_token,
            },
            sort_keys=True,
        )
        + "\n"
    )
    refresh_packet(fx)


def make_fixture(tmp_path: Path) -> Synthetic:
    module = load_module()
    root = tmp_path / "estate"
    root.mkdir()
    h5 = root / "data.0001.flt.h5"
    xmf = root / "data.0001.flt.xmf"
    protected = root / "protected.txt"
    held = root / "held.txt"
    h5.write_bytes(b"candidate-hdf5-content")
    xmf.write_bytes(b"candidate-xmf-content")
    protected.write_bytes(b"protected-content")
    held.write_bytes(b"held-content")
    source_rows = [
        source_row(module, root, h5, protection="UNPROTECTED"),
        source_row(module, root, xmf, protection="UNPROTECTED"),
        source_row(module, root, protected, protection="PROTECTED"),
        source_row(module, root, held, protection="UNPROTECTED"),
    ]
    ledger = [
        ledger_row(module, source_rows[0], module.DELETE_HDF5),
        ledger_row(module, source_rows[1], module.DELETE_XMF),
        ledger_row(module, source_rows[2], "KEEP_PROTECTED"),
        ledger_row(module, source_rows[3], "HOLD_REGENERATION_UNPROVEN"),
    ]
    stage = tmp_path / "stage"
    packet = stage / "authorization_packet"
    completed = stage / "completed_run"
    evidence = tmp_path / "evidence"
    packet.mkdir(parents=True)
    evidence.mkdir()
    fields = list(ledger[0])
    write_csv(packet / "payload_ledger.csv", fields, ledger)
    allowlist_fields = [
        "case_id",
        "root_id",
        "root_path",
        "root_kind",
        "purpose",
        "expected_presence",
        "source_evidence",
    ]
    allowlist = [
        {
            "case_id": "C-HI",
            "root_id": "production_synthetic",
            "root_path": str(root),
            "root_kind": "production",
            "purpose": "synthetic",
            "expected_presence": "true",
            "source_evidence": "synthetic",
        }
    ]
    write_csv(packet / "remote_root_allowlist.csv", allowlist_fields, allowlist)
    protected_fields = [
        "path",
        "protection_class",
        "dependency",
        "source_evidence",
        "existing_sha256",
        "expected_timestep",
        "expected_time_code",
        "expected_time_myr",
        "expected_shape",
        "expected_datasets",
    ]
    protected_rows = [
        {
            "path": str(protected),
            "protection_class": "KEEP_PROTECTED",
            "dependency": "synthetic_provenance",
            "source_evidence": "synthetic",
            "existing_sha256": sha(protected),
            "expected_timestep": "",
            "expected_time_code": "",
            "expected_time_myr": "",
            "expected_shape": "",
            "expected_datasets": "",
        }
    ]
    write_csv(
        packet / "protected_path_contract.csv",
        protected_fields,
        protected_rows,
    )
    hold_fields = [
        "path",
        "case_id",
        "root_id",
        "action",
        "rationale",
        "sha256",
        "file_type",
    ]
    write_csv(
        packet / "active_hold_register.csv",
        hold_fields,
        [
            {
                "path": str(held),
                "case_id": "C-HI",
                "root_id": "production_synthetic",
                "action": "HOLD_REGENERATION_UNPROVEN",
                "rationale": "synthetic",
                "sha256": sha(held),
                "file_type": "regular",
            }
        ],
    )
    packet_dummy_files(module, packet)
    write_csv(
        completed / "review_inventory/inventory/payload_inventory.csv",
        module.SOURCE_COLUMNS,
        source_rows,
    )
    write_csv(
        completed / "review_inventory/inventory/remote_root_inventory.csv",
        allowlist_fields
        + [
            "exists",
            "root_type",
            "payload_count",
            "apparent_bytes",
            "allocated_bytes",
        ],
        [
            {
                **allowlist[0],
                "exists": "true",
                "root_type": "directory",
                "payload_count": str(len(source_rows)),
                "apparent_bytes": str(sum(int(row["apparent_bytes"]) for row in source_rows)),
                "allocated_bytes": str(sum(int(row["allocated_bytes"]) for row in source_rows)),
            }
        ],
    )
    write_csv(
        completed / "review_inventory/remote_root_allowlist.csv",
        allowlist_fields,
        allowlist,
    )
    write_csv(
        completed / "review_inventory/protected_path_contract.csv",
        protected_fields,
        protected_rows,
    )
    catalogue = completed / "catalogue_snapshot/production_synthetic/flt.h5.out"
    catalogue.parent.mkdir(parents=True)
    catalogue.write_text("1 1.0 0.1 1 single_file little rho\n")
    (stage / "execute_three_case_lifecycle_compaction.py").write_text(
        "# staged synthetic executor\n"
    )
    (stage / "three_case_lifecycle_compaction.pbs").write_text(
        "# staged synthetic wrapper\n"
    )
    paths = module.ExecutionPaths(
        approved_ledger=packet / "payload_ledger.csv",
        packet_manifest=packet / "local_asset_manifest.sha256",
        completed_evidence_dir=completed,
        completed_evidence_manifest=stage
        / "goal046_completed_evidence_manifest.sha256",
        staged_input_manifest=stage / "goal047_staged_input_manifest.sha256",
        approval_receipt=stage / "approval_receipt.json",
        evidence_root=evidence,
        stage_transcript=stage
        / "three_case_lifecycle_compaction_transcript.jsonl",
        status_json=evidence / "execution_status.json",
        compact_evidence_file_list=evidence / "compact_evidence_file_list.txt",
        lock_path=stage / "synthetic.lock",
    )
    fx = Synthetic(
        module=module,
        root=root,
        h5=h5,
        xmf=xmf,
        protected=protected,
        held=held,
        stage=stage,
        packet=packet,
        completed=completed,
        evidence=evidence,
        paths=paths,
        policy=None,
        job_id="999.synthetic",
        source_rows=source_rows,
    )
    refresh_completed_manifest(fx)
    refresh_receipt_and_policy(fx)
    return fx


def qstat_services(
    fx: Synthetic,
    *,
    extra_job: str | None = None,
    unlinker: Callable[[int, str, dict[str, str]], None] | None = None,
    before_postscan: Callable[[], None] = lambda: None,
):
    module = fx.module

    def qstat(owner: str):
        del owner
        jobs = [fx.job_id]
        if extra_job:
            jobs.append(extra_job)
        stdout = "".join(f"{job} bwbrook normal job 0 1 1 -- 01:00 R 00:01\n" for job in jobs)
        return subprocess.CompletedProcess(["qstat"], 0, stdout, "")

    return module.Services(
        qstat_runner=qstat,
        unlinker=unlinker or module._default_unlinker,
        before_postscan=before_postscan,
    )


def run(fx: Synthetic, *, mode: str = "execute", services=None, token=None):
    return fx.module.execute_compaction(
        fx.paths,
        mode=mode,
        expected_ledger_sha256=fx.policy.ledger_sha256,
        confirmation_token=(
            fx.policy.confirmation_token if token is None else token
        ),
        pbs_job_id=fx.job_id,
        policy=fx.policy,
        services=services or qstat_services(fx),
    )


def assert_predelete_failure(fx: Synthetic, match: str = "") -> None:
    with pytest.raises(fx.module.CompactionError, match=match):
        run(fx)
    assert fx.candidates_exist()
    assert fx.paths.status_json.is_file()
    assert fx.paths.stage_transcript.is_file()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_NO_MUTATION"
    assert status["deleted_row_count"] == 0
    records = [
        json.loads(line)
        for line in fx.paths.stage_transcript.read_text().splitlines()
    ]
    assert records[-1]["event"] == "terminal_failure"
    previous = "0" * 64
    for record in records:
        observed = record.pop("record_sha256")
        assert record["previous_record_sha256"] == previous
        assert (
            hashlib.sha256(fx.module._canonical_record(record)).hexdigest()
            == observed
        )
        previous = observed


def rewrite_ledger(
    fx: Synthetic, mutate: Callable[[list[dict[str, str]]], None]
) -> None:
    path = fx.packet / "payload_ledger.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        assert fields
        rows = list(reader)
    mutate(rows)
    write_csv(path, fields, rows)
    refresh_receipt_and_policy(fx)


def test_dry_run_default_path_never_mutates_and_hash_chain_is_valid(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    result = run(fx, mode="dry-run", token="")
    assert result["status"] == fx.module.DRY_RUN_STATUS
    assert fx.candidates_exist()
    records = [
        json.loads(line)
        for line in fx.paths.stage_transcript.read_text().splitlines()
    ]
    previous = "0" * 64
    for record in records:
        observed = record.pop("record_sha256")
        assert record["previous_record_sha256"] == previous
        assert hashlib.sha256(fx.module._canonical_record(record)).hexdigest() == observed
        previous = observed


@pytest.mark.parametrize("kind", ["wrong_digest", "wrong_token", "missing_receipt", "bad_receipt"])
def test_execute_requires_exact_digest_token_and_receipt(tmp_path: Path, kind: str) -> None:
    fx = make_fixture(tmp_path)
    kwargs = {
        "mode": "execute",
        "expected_ledger_sha256": fx.policy.ledger_sha256,
        "confirmation_token": fx.policy.confirmation_token,
        "pbs_job_id": fx.job_id,
        "policy": fx.policy,
        "services": qstat_services(fx),
    }
    if kind == "wrong_digest":
        kwargs["expected_ledger_sha256"] = "0" * 64
    elif kind == "wrong_token":
        kwargs["confirmation_token"] = "WRONG"
    elif kind == "missing_receipt":
        fx.paths.approval_receipt.unlink()
    else:
        receipt = json.loads(fx.paths.approval_receipt.read_text())
        receipt["approved_row_count"] = 999
        fx.paths.approval_receipt.write_text(json.dumps(receipt) + "\n")
    with pytest.raises(fx.module.CompactionError):
        fx.module.execute_compaction(fx.paths, **kwargs)
    assert fx.candidates_exist()


def test_last_candidate_mismatch_leaves_all_candidates(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    before = os.lstat(fx.xmf)
    fx.xmf.write_bytes(b"changed-last-row-data")
    os.utime(fx.xmf, ns=(before.st_atime_ns, before.st_mtime_ns))
    assert_predelete_failure(fx, "identity mismatch|hash mismatch")


def test_symlink_candidate_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    target = tmp_path / "other"
    target.write_bytes(fx.xmf.read_bytes())
    fx.xmf.unlink()
    fx.xmf.symlink_to(target)
    assert_predelete_failure(fx, "identity mismatch")


def test_hardlink_candidate_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    alias = tmp_path / "outside-hardlink"
    os.link(fx.h5, alias)
    assert_predelete_failure(fx, "hardlink count")


def test_path_traversal_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)

    def mutate(rows):
        rows[0]["path"] = str(fx.root / ".." / "escaped.flt.h5")

    rewrite_ledger(fx, mutate)
    assert_predelete_failure(fx, "source-row reconciliation|allowlisted")


def test_content_hash_mismatch_with_preserved_identity_fails_before_deletion(
    tmp_path: Path,
) -> None:
    fx = make_fixture(tmp_path)
    st = os.lstat(fx.h5)
    original = fx.h5.read_bytes()
    replacement = bytes((value + 1) % 256 for value in original)
    fx.h5.write_bytes(replacement)
    os.utime(fx.h5, ns=(st.st_atime_ns, st.st_mtime_ns))
    assert os.lstat(fx.h5).st_size == st.st_size
    assert_predelete_failure(fx, "hash mismatch")


@pytest.mark.parametrize("kind", ["inode", "mtime"])
def test_inode_or_mtime_change_fails_before_deletion(tmp_path: Path, kind: str) -> None:
    fx = make_fixture(tmp_path)
    st = os.lstat(fx.h5)
    if kind == "inode":
        replacement = fx.root / "replacement"
        replacement.write_bytes(fx.h5.read_bytes())
        os.utime(replacement, ns=(st.st_atime_ns, st.st_mtime_ns))
        os.replace(replacement, fx.h5)
    else:
        os.utime(fx.h5, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000))
    assert_predelete_failure(fx, "identity mismatch")


def test_pair_gate_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    rewrite_ledger(
        fx,
        lambda rows: next(
            row for row in rows if row["action"] == fx.module.DELETE_HDF5
        ).update(pair_status="missing"),
    )
    assert_predelete_failure(fx, "pair|unsafe approved")


def test_catalogue_gate_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    catalogue = (
        fx.completed / "catalogue_snapshot/production_synthetic/flt.h5.out"
    )
    catalogue.write_text("2 2.0 0.1 2 single_file little rho\n")
    refresh_completed_manifest(fx)
    assert_predelete_failure(fx, "catalogue")


@pytest.mark.parametrize("gate", ["protected", "hold"])
def test_protected_or_hold_antijoin_fails_before_deletion(
    tmp_path: Path, gate: str
) -> None:
    fx = make_fixture(tmp_path)
    if gate == "protected":
        path = fx.packet / "protected_path_contract.csv"
        rows = list(csv.DictReader(path.open()))
        rows.append({**rows[0], "path": str(fx.h5)})
        write_csv(path, list(rows[0]), rows)
    else:
        path = fx.packet / "active_hold_register.csv"
        rows = list(csv.DictReader(path.open()))
        rows.append({**rows[0], "path": str(fx.h5)})
        write_csv(path, list(rows[0]), rows)
    refresh_packet(fx)
    assert_predelete_failure(fx, "protected|hold register|held")


def test_packet_manifest_omission_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    manifest = fx.packet / "local_asset_manifest.sha256"
    lines = manifest.read_text().splitlines()
    manifest.write_text("\n".join(lines[:-1]) + "\n")
    refresh_stage_manifest(fx)
    assert_predelete_failure(fx, "manifest")


def test_real_completed_evidence_manifest_accepts_dot_slash_paths() -> None:
    module = load_module()
    manifest = Path(
        "docs/science/assets/"
        "three_case_lifecycle_compaction_execution_2026-07-24/"
        "goal046_completed_evidence_manifest.sha256"
    )
    entries = module._manifest_entries(manifest)
    assert entries
    assert all(not name.startswith("./") for name in entries)
    assert (
        "review_inventory/inventory/payload_inventory.csv"
        in entries
    )


def test_other_active_qstat_job_fails_before_deletion(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    assert_predelete_failure_with_services = qstat_services(
        fx, extra_job="1000.synthetic"
    )
    with pytest.raises(fx.module.CompactionError, match="qstat"):
        run(fx, services=assert_predelete_failure_with_services)
    assert fx.candidates_exist()


@pytest.mark.parametrize("array_suffix", ["[]", "[1]"])
def test_qstat_array_job_with_own_numeric_parent_fails_closed(
    tmp_path: Path,
    array_suffix: str,
) -> None:
    fx = make_fixture(tmp_path)
    own_number, server = fx.job_id.split(".", 1)
    stdout = (
        "kunanyi-ohpc:\n"
        "                                                            Req'd  Req'd   Elap\n"
        "Job ID          Username Queue    Jobname    SessID NDS TSK Memory Time  S Time\n"
        "--------------- -------- -------- ---------- ------ --- --- ------ ----- - -----\n"
        f"{fx.job_id} bwbrook normal tri_compact 1 1 8 64gb 48:00 R 00:01\n"
        f"{own_number}{array_suffix}.{server} bwbrook normal other_array "
        "2 1 8 64gb 48:00 R 00:01\n"
    )

    def qstat(owner: str):
        del owner
        return subprocess.CompletedProcess(["qstat"], 0, stdout, "")

    services = fx.module.Services(
        qstat_runner=qstat,
        unlinker=fx.module._default_unlinker,
    )
    with pytest.raises(fx.module.CompactionError, match="qstat.*rejected"):
        run(fx, services=services)
    assert fx.candidates_exist()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_NO_MUTATION"
    assert status["deleted_row_count"] == 0
    assert fx.paths.stage_transcript.is_file()
    evidence_names = set(
        fx.paths.compact_evidence_file_list.read_text().splitlines()
    )
    assert {"execution_status.json", "qstat_start.txt"} <= evidence_names


def test_exact_success_removes_only_approved_rows(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    result = run(fx)
    assert result["status"] == "DELETION_COMPLETE_POSTCHECK_GREEN"
    assert not fx.h5.exists()
    assert not fx.xmf.exists()
    assert fx.protected.read_bytes() == b"protected-content"
    assert fx.held.read_bytes() == b"held-content"
    assert result["deleted_row_count"] == 2
    assert result["deleted_hdf5_count"] == 1
    assert result["deleted_xmf_count"] == 1
    assert result["recovered_allocated_bytes"] == fx.policy.allocated_bytes
    transcript = fx.paths.stage_transcript.read_text()
    h5_position = transcript.index(str(fx.h5))
    xmf_position = transcript.index(str(fx.xmf))
    assert h5_position < xmf_position


def test_injected_unlink_failure_stops_and_records_partial_state(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)
    calls = 0

    def fail_second(parent_fd: int, name: str, row: dict[str, str]) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError(5, "synthetic unlink failure")
        os.unlink(name, dir_fd=parent_fd)

    with pytest.raises(
        fx.module.CompactionError, match="unlink failed"
    ) as captured:
        run(fx, services=qstat_services(fx, unlinker=fail_second))
    assert captured.value.status == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert not fx.h5.exists()
    assert fx.xmf.exists()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert status["deleted_row_count"] == 1
    assert "unlink_failed" in fx.paths.stage_transcript.read_text()


def test_post_unlink_descriptor_failure_still_counts_removed_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fx = make_fixture(tmp_path)
    real_fstat = fx.module.os.fstat

    def fail_after_first_unlink(fd: int):
        if not fx.h5.exists():
            raise OSError(5, "synthetic post-unlink descriptor failure")
        return real_fstat(fd)

    monkeypatch.setattr(fx.module.os, "fstat", fail_after_first_unlink)
    with pytest.raises(fx.module.CompactionError) as captured:
        run(fx)
    assert captured.value.status == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert not fx.h5.exists()
    assert fx.xmf.exists()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert status["deleted_row_count"] == 1
    assert status["deleted_hdf5_count"] == 1


def test_remove_then_raise_counts_removed_path_and_stops_pair(
    tmp_path: Path,
) -> None:
    fx = make_fixture(tmp_path)

    def remove_then_raise(
        parent_fd: int, name: str, row: dict[str, str]
    ) -> None:
        del row
        os.unlink(name, dir_fd=parent_fd)
        raise OSError(5, "synthetic ambiguous remove acknowledgement")

    with pytest.raises(fx.module.CompactionError) as captured:
        run(
            fx,
            services=qstat_services(fx, unlinker=remove_then_raise),
        )
    assert captured.value.status == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert not fx.h5.exists()
    assert fx.xmf.exists()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_PARTIAL_MUTATION"
    assert status["deleted_row_count"] == 1
    assert status["deleted_hdf5_count"] == 1
    assert (
        "unlink_outcome_ambiguous_or_removed"
        in fx.paths.stage_transcript.read_text()
    )


def test_immediate_preunlink_identity_mismatch_is_no_mutation(
    tmp_path: Path,
) -> None:
    fx = make_fixture(tmp_path)
    calls = 0

    def qstat(owner: str):
        nonlocal calls
        del owner
        calls += 1
        if calls == 2:
            before = os.lstat(fx.h5)
            replacement = fx.root / "preunlink-replacement"
            replacement.write_bytes(fx.h5.read_bytes())
            os.utime(
                replacement,
                ns=(before.st_atime_ns, before.st_mtime_ns),
            )
            os.replace(replacement, fx.h5)
        stdout = (
            f"{fx.job_id} bwbrook normal tri_compact "
            "0 1 1 -- 01:00 R 00:01\n"
        )
        return subprocess.CompletedProcess(["qstat"], 0, stdout, "")

    services = fx.module.Services(
        qstat_runner=qstat,
        unlinker=fx.module._default_unlinker,
    )
    with pytest.raises(
        fx.module.CompactionError,
        match="immediate path/descriptor identity mismatch",
    ) as captured:
        run(fx, services=services)
    assert captured.value.status == "FAILED_CLOSED_NO_MUTATION"
    assert fx.candidates_exist()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_NO_MUTATION"
    assert status["deleted_row_count"] == 0
    assert "DELETION_COMPLETE_POSTCHECK_GREEN" not in status


@pytest.mark.parametrize(
    "late_failure",
    ["compact_evidence_file_list", "transcript_close"],
)
def test_late_evidence_failure_never_publishes_green_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    late_failure: str,
) -> None:
    fx = make_fixture(tmp_path)
    if late_failure == "compact_evidence_file_list":
        def fail_evidence_list(*args, **kwargs):
            del args, kwargs
            raise fx.module.CompactionError(
                "synthetic late compact-evidence-list failure"
            )

        monkeypatch.setattr(
            fx.module,
            "_write_evidence_file_list",
            fail_evidence_list,
        )
    else:
        original_close = fx.module.HashChainTranscript.close

        def close_then_fail(transcript):
            original_close(transcript)
            raise OSError(5, "synthetic late transcript close failure")

        monkeypatch.setattr(
            fx.module.HashChainTranscript,
            "close",
            close_then_fail,
        )

    with pytest.raises(fx.module.CompactionError) as captured:
        run(fx)
    assert captured.value.status == "FAILED_CLOSED_POSTCHECK"
    assert not fx.h5.exists()
    assert not fx.xmf.exists()
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_POSTCHECK"
    assert status["deleted_row_count"] == 2
    assert "DELETION_COMPLETE_POSTCHECK_GREEN" not in status
    assert (
        "DELETION_COMPLETE_POSTCHECK_GREEN"
        not in fx.paths.stage_transcript.read_text()
    )


def test_nfs_silly_rename_nlink_one_is_closed_then_postscan_can_pass(
    tmp_path: Path,
) -> None:
    fx = make_fixture(tmp_path)
    renamed: list[Path] = []

    def silly_rename(parent_fd: int, name: str, row: dict[str, str]) -> None:
        target = f".nfs-{Path(row['path']).name}"
        os.rename(
            name,
            target,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
        )
        renamed.append(fx.root / target)

    def nfs_close_cleanup() -> None:
        for path in renamed:
            path.unlink()

    result = run(
        fx,
        services=qstat_services(
            fx,
            unlinker=silly_rename,
            before_postscan=nfs_close_cleanup,
        ),
    )
    assert result["status"] == "DELETION_COMPLETE_POSTCHECK_GREEN"
    records = [
        json.loads(line)
        for line in fx.paths.stage_transcript.read_text().splitlines()
    ]
    completed = [row for row in records if row["event"] == "unlink_complete"]
    assert completed
    assert all(row["preclose_nlink"] == 1 for row in completed)
    assert not renamed[0].exists()


def test_postscan_explicitly_rejects_nfs_remnant(tmp_path: Path) -> None:
    fx = make_fixture(tmp_path)

    def create_nfs() -> None:
        (fx.root / ".nfs-residual").write_text("residual")

    with pytest.raises(fx.module.CompactionError) as captured:
        run(fx, services=qstat_services(fx, before_postscan=create_nfs))
    assert captured.value.status == "FAILED_CLOSED_POSTCHECK"


@pytest.mark.parametrize("post_change", ["new", "retained"])
def test_postcheck_rejects_new_or_changed_retained_path(
    tmp_path: Path, post_change: str
) -> None:
    fx = make_fixture(tmp_path)

    def mutate_postscan() -> None:
        if post_change == "new":
            (fx.root / "unexpected.txt").write_text("new")
        else:
            fx.held.write_text("changed")

    with pytest.raises(fx.module.CompactionError) as captured:
        run(
            fx,
            services=qstat_services(fx, before_postscan=mutate_postscan),
        )
    assert captured.value.status == "FAILED_CLOSED_POSTCHECK"
    status = json.loads(fx.paths.status_json.read_text())
    assert status["status"] == "FAILED_CLOSED_POSTCHECK"
    assert status["deleted_row_count"] == 2


def test_preexisting_protected_hdf5_fault_fails_before_mutation(
    tmp_path: Path,
) -> None:
    pytest.importorskip("h5py")
    fx = make_fixture(tmp_path)
    old_path = fx.protected
    broken_hdf5 = old_path.with_suffix(".h5")
    old_path.rename(broken_hdf5)

    for table in (
        fx.packet / "payload_ledger.csv",
        fx.completed / "review_inventory/inventory/payload_inventory.csv",
    ):
        with table.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            assert fields
            rows = list(reader)
        for row in rows:
            if row["path"] != str(old_path):
                continue
            row["path"] = str(broken_hdf5)
            row["relative_path"] = str(broken_hdf5.relative_to(fx.root))
            row["resolved_path"] = str(broken_hdf5)
        write_csv(table, fields, rows)

    for table in (
        fx.packet / "protected_path_contract.csv",
        fx.completed / "review_inventory/protected_path_contract.csv",
    ):
        with table.open(newline="") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            assert fields
            rows = list(reader)
        for row in rows:
            if row["path"] == str(old_path):
                row["path"] = str(broken_hdf5)
        write_csv(table, fields, rows)

    fx.protected = broken_hdf5
    refresh_completed_manifest(fx)
    refresh_receipt_and_policy(fx)
    assert_predelete_failure(fx, "protected HDF5 validation failed")
    assert fx.protected.exists()


def test_every_protected_hdf5_is_reopened_even_without_contract_metadata(
    tmp_path: Path,
) -> None:
    h5py = pytest.importorskip("h5py")
    module = load_module()
    path = tmp_path / "protected.h5"
    with h5py.File(path, "w") as handle:
        group = handle.create_group("Timestep_7")
        group.attrs["Time"] = 12.5
        vars_group = group.create_group("vars")
        vars_group.create_dataset("rho", shape=(2, 3), dtype="f8")
        coords = handle.create_group("cell_coords")
        coords.create_dataset("X", shape=(2, 3), dtype="f8")
    protected = {
        "path": str(path),
        "expected_timestep": "",
        "expected_time_code": "",
        "expected_shape": "",
        "expected_datasets": "",
    }
    ledger = {
        "path": str(path),
        "hdf5_timestep": "Timestep_7",
        "hdf5_time_code": "12.5",
        "hdf5_datasets": "Timestep_7/vars/rho;cell_coords/X",
        "hdf5_shape": (
            "Timestep_7/vars/rho:(2, 3);cell_coords/X:(2, 3)"
        ),
    }
    assert module._validate_protected_hdf5([protected], [ledger]) == 1
    with h5py.File(path, "a") as handle:
        del handle["cell_coords/X"]
    with pytest.raises(module.CompactionError, match="protected HDF5"):
        module._validate_protected_hdf5([protected], [ledger])


def test_no_recursive_or_glob_deletion_primitive() -> None:
    text = SCRIPT.read_text()
    forbidden = (
        "shutil.rmtree",
        "os.removedirs",
        "rm -r",
        "rm -f",
        "Path.glob",
        "Path.rglob",
    )
    for primitive in forbidden:
        assert primitive not in text
    assert "os.unlink(name, dir_fd=parent_fd)" in text
