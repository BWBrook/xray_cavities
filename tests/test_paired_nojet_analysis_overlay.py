import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


builder = load("paired_overlay_builder", ROOT / "scripts/kunanyi/build_paired_nojet_analysis_overlay.py")
revalidator = load("paired_overlay_revalidator", ROOT / "scripts/kunanyi/paired_nojet_revalidate.py")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_stage_manifest(stage):
    relatives = (builder.ORIGINAL_PBS, builder.ORIGINAL_BUDGET_VALIDATOR, builder.ORIGINAL_OUTPUT_VALIDATOR)
    records = [f"{digest(stage / relative)}  {relative.as_posix()}" for relative in sorted(relatives)]
    (stage / "stage_checksums.sha256").write_text("\n".join(records) + "\n")


def physics_stage(tmp_path):
    stage = tmp_path / "physics"
    original_pbs = ROOT / "scripts/kunanyi/paired_nojet_control.pbs"
    files = {
        builder.ORIGINAL_PBS: original_pbs.read_text(),
        builder.ORIGINAL_BUDGET_VALIDATOR: (
            ROOT / builder.UPDATED_BUDGET_VALIDATOR
        ).read_text().replace(builder.NEW_SCALE, builder.OLD_SCALE),
        builder.ORIGINAL_OUTPUT_VALIDATOR: (
            ROOT / builder.ORIGINAL_OUTPUT_VALIDATOR
        ).read_text().replace(builder.NEW_STABLE, builder.OLD_STABLE),
    }
    for relative, content in files.items():
        path = stage / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    write_stage_manifest(stage)
    return stage


def build_overlay(tmp_path):
    stage = physics_stage(tmp_path)
    overlay = tmp_path / "analysis_overlay"
    result = builder.build(argparse.Namespace(
        physics_stage=stage,
        remote_physics_stage=str(stage),
        output=overlay,
    ))
    return stage, overlay, result


def test_builder_binds_frozen_and_updated_validators_and_renders_constrained_pbs(tmp_path):
    stage, overlay, result = build_overlay(tmp_path)
    contract = json.loads((overlay / "overlay_contract.json").read_text())
    assert contract["status"] == "validator_only_analysis_overlay"
    assert contract["original_stage_manifest_sha256"] == digest(stage / "stage_checksums.sha256")
    assert contract["original_budget_validator_sha256"] == digest(stage / builder.ORIGINAL_BUDGET_VALIDATOR)
    assert contract["updated_budget_validator_sha256"] == digest(ROOT / builder.UPDATED_BUDGET_VALIDATOR)
    assert contract["updated_output_validator_sha256"] == digest(ROOT / builder.UPDATED_OUTPUT_VALIDATOR)
    assert contract["expected_budget_test_count"] == 38
    assert contract["expected_output_helper_test_count"] == 7
    assert contract["physical_acceptance_gates_changed"] is False
    assert contract["physics_stage_files_changed"] == []
    assert Path(result["archive"]).is_file()
    revalidator.verify_bindings(stage, overlay)

    full = (overlay / "scripts/kunanyi/paired_nojet_control_full.pbs").read_text()
    original = (stage / builder.ORIGINAL_PBS).read_text()
    assert original.count("python scripts/science/validate_paired_nojet_budget.py") == 1
    assert "python \"$OVERLAY/scripts/science/validate_paired_nojet_budget.py\"" in full
    assert str(overlay / "revalidated/gate_receipt.json") in full
    assert "original_stage_manifest_sha256" in full
    assert "--verify-bindings" in full
    for unchanged in (
        'cp bin/pluto bin/definitions.h bin/definitions_usr.h "$RUN"/',
        'mpirun -np 28 ./pluto -dec 2 2 7 -i pluto.ini -e environment.ini',
        'readonly INPUT="$STAGE/inputs/$KEY"',
    ):
        assert full.count(unchanged) == original.count(unchanged) == 1

    pbs = (overlay / "scripts/kunanyi/paired_nojet_revalidate.pbs").read_text()
    assert "select=1:ncpus=1:mem=8gb" in pbs
    assert "walltime=00:30:00" in pbs
    assert "Anaconda3/2024.02-1" in pbs
    assert 'export PYTHONPATH="$STAGE/scripts/science"' in pbs
    assert "@PHYSICS_STAGE@" not in pbs and "@ANALYSIS_OVERLAY@" not in pbs


def test_builder_refuses_overwrite_and_non_validator_only_change(tmp_path):
    stage, overlay, _ = build_overlay(tmp_path)
    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        builder.build(argparse.Namespace(
            physics_stage=stage,
            remote_physics_stage=str(stage),
            output=overlay,
        ))
    changed = stage / builder.ORIGINAL_BUDGET_VALIDATOR
    changed.write_text(changed.read_text() + "\n# unrelated\n")
    write_stage_manifest(stage)
    with pytest.raises(ValueError, match="beyond the authorised"):
        builder.build(argparse.Namespace(
            physics_stage=stage,
            remote_physics_stage=str(stage),
            output=tmp_path / "second_overlay",
        ))


def test_builder_rejects_output_helper_change_beyond_cross_device_stability_rule(tmp_path):
    stage = physics_stage(tmp_path)
    helper = stage / builder.ORIGINAL_OUTPUT_VALIDATOR
    helper.write_text(helper.read_text() + "\n# unrelated\n")
    write_stage_manifest(stage)
    with pytest.raises(ValueError, match="beyond the authorised stability replacement"):
        builder.build(argparse.Namespace(
            physics_stage=stage,
            remote_physics_stage=str(stage),
            output=tmp_path / "analysis_overlay",
        ))


def populate_smoke_receipts(stage, contract):
    binary = b"common-binary"
    binary_hash = hashlib.sha256(binary).hexdigest()
    build = stage / "build"
    build.mkdir()
    (build / "build_receipt.json").write_text(json.dumps({
        "status": "built_common_binary",
        "stage_manifest_sha256": contract["original_stage_manifest_sha256"],
        "files": {"pluto": binary_hash},
    }))
    for case in revalidator.CASES:
        for boundary in revalidator.BOUNDARIES:
            run = stage / "smoke" / f"{case}_{boundary}"
            run.mkdir(parents=True)
            (run / "pluto").write_bytes(binary)
            (run / "paired_nojet_budget.csv").write_text("ledger\n")
            (run / "simulation.resources.txt").write_text("Exit status: 0\n")
            (run / "output_receipt.json").write_text(json.dumps({
                "schema_version": 1,
                "status": "validated_paired_control_run",
                "case": case,
                "boundary": boundary,
                "mode": "smoke",
                "run_dir": str(run),
                "input_files": {
                    "pluto": {"sha256": binary_hash},
                    "validator_source:validate_paired_nojet_outputs.py": {
                        "sha256": contract["original_output_validator_sha256"],
                    },
                },
            }))
    return binary_hash


def test_revalidator_runs_uniform_four_budget_two_pair_gate_without_touching_stage(tmp_path, monkeypatch):
    stage, overlay, _ = build_overlay(tmp_path)
    contract = json.loads((overlay / "overlay_contract.json").read_text())
    binary_hash = populate_smoke_receipts(stage, contract)
    stage_before = digest(stage / "stage_checksums.sha256")

    def fake_tests(_stage, _overlay, output, expected):
        assert expected == 38
        path = output / "budget_tests.xml"
        path.write_text('<testsuites tests="38" failures="0" errors="0" skipped="0"/>\n')
        return path

    def fake_output_tests(_stage, _overlay, output, expected):
        assert expected == 7
        path = output / "output_helper_tests.xml"
        path.write_text('<testsuites tests="7" failures="0" errors="0" skipped="0"/>\n')
        return path

    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        output = Path(command[command.index("--output") + 1])
        if "--run-dir" in command:
            boundary = command[command.index("--boundary") + 1]
            run = Path(command[command.index("--run-dir") + 1])
            ledger = run / "paired_nojet_budget.csv"
            output.write_text(json.dumps({
                "status": "validated_paired_control_budget",
                "boundary": boundary,
                "input_files": [{"path": str(ledger), "sha256": digest(ledger)}],
            }))
        else:
            source = Path(command[command.index("--pair-receipts") + 1])
            case = source.parent.name.removesuffix("_reflective")
            output.write_text(json.dumps({
                "status": "validated_paired_control_identity",
                "case": case,
                "binary_sha256": binary_hash,
            }))
        return None

    monkeypatch.setattr(revalidator, "run_budget_tests", fake_tests)
    monkeypatch.setattr(revalidator, "run_output_helper_tests", fake_output_tests)
    monkeypatch.setattr(revalidator.subprocess, "run", fake_run)
    gate_path = revalidator.run_revalidation(stage, overlay)
    gate = json.loads(gate_path.read_text())
    assert gate["status"] == "all_four_smokes_and_both_pairs_passed"
    assert gate["original_stage_manifest_sha256"] == stage_before
    assert gate["native_smoke_receipts_verified"] == 4
    assert gate["measured_mpi_exit_zero_verified"] == 4
    assert gate["budgets_revalidated"] == 4
    assert gate["pairs_revalidated"] == 2
    assert gate["output_helper_tests_passed"] == 7
    assert len([call for call in calls if "--run-dir" in call]) == 4
    assert len([call for call in calls if "--pair-receipts" in call]) == 2
    assert digest(stage / "stage_checksums.sha256") == stage_before
    assert all(Path(path).is_file() and digest(Path(path)) == value for path, value in gate["evidence"].items())
    assert sum(path.endswith("paired_nojet_budget.csv") for path in gate["evidence"]) == 4
    with pytest.raises(FileExistsError):
        revalidator.run_revalidation(stage, overlay)


def test_native_verification_fails_closed_on_nonzero_measured_mpi_exit(tmp_path):
    stage, overlay, _ = build_overlay(tmp_path)
    contract = json.loads((overlay / "overlay_contract.json").read_text())
    populate_smoke_receipts(stage, contract)
    failed = stage / "smoke/group_002031_reflective/simulation.resources.txt"
    failed.write_text("Exit status: 1\n")
    with pytest.raises(ValueError, match="did not exit zero"):
        revalidator.verify_native_smokes(stage, contract)


def test_direct_ledger_evidence_must_match_budget_receipt_hash(tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    ledger = run / "paired_nojet_budget.csv"
    ledger.write_text("ledger\n")
    receipt = {"input_files": [{"path": str(ledger), "sha256": "0" * 64}]}
    with pytest.raises(ValueError, match="direct ledger evidence"):
        revalidator.verified_budget_ledger(receipt, run)
