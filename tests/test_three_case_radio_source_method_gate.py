from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/science/build_three_case_radio_source_method_gate.py"
EXPECTED_DECISION = (
    "THREE_CASE_LOSS_AWARE_RADIO_BLOCKED_G_LO_METHOD_VALUE_GATE_REQUIRED"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_three_case_radio_source_method_gate", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames
        assert len(reader.fieldnames) == len(set(reader.fieldnames))
        return list(reader)


def test_builder_writes_deterministic_schema_and_decision(tmp_path: Path) -> None:
    module = load_module()
    first = tmp_path / "first"
    second = tmp_path / "second"
    metadata = module.build_gate(REPO, first)
    module.build_gate(REPO, second)

    names = (
        "source_inventory.csv",
        "source_ledger_extract.csv",
        "runtime_semantics_audit.csv",
        "method_acceptance_gate.csv",
        "decision_matrix.csv",
        "radio_source_method_gate_metadata.json",
    )
    assert metadata["overall_decision"] == EXPECTED_DECISION
    for name in names:
        assert (first / name).is_file()
        assert (first / name).read_bytes() == (second / name).read_bytes()
        assert hashlib.sha256((first / name).read_bytes()).hexdigest()

    inventory = csv_rows(first / "source_inventory.csv")
    assert {row["case_id"] for row in inventory} == {"C-HI", "C-LO", "G-LO"}
    required_inventory = {
        "accepted_endpoint_lineage",
        "retained_raw_sequence_coverage",
        "full_history_available",
        "available_dense_cache_max_age_myr",
        "dense_cache_lineage",
        "loss_aware_readiness",
        "history_coverage_status",
        "runtime_semantics_resolved",
        "evidence_type",
        "inferred_assessment",
        "decision_status",
    }
    assert required_inventory <= set(inventory[0])
    assert {row["evidence_type"] for row in inventory} == {"observed"}
    assert all(row["inferred_assessment"] for row in inventory)
    assert all(row["decision_status"] for row in inventory)
    inventory_by_case = {row["case_id"]: row for row in inventory}
    assert "regular 4277 in fresh" in inventory_by_case["C-HI"]["retained_raw_sequence_coverage"]
    assert "4277 symlink" in inventory_by_case["C-HI"]["retained_raw_sequence_coverage"]
    assert "regular 5000 in prod64" in inventory_by_case["C-HI"]["retained_raw_sequence_coverage"]
    assert inventory_by_case["C-LO"]["retained_raw_sequence_coverage"].startswith("regular 1611 and 5003")
    assert "0000..1499" in inventory_by_case["G-LO"]["retained_raw_sequence_coverage"]
    assert "1000..5000" in inventory_by_case["G-LO"]["retained_raw_sequence_coverage"]
    assert inventory_by_case["G-LO"]["available_dense_cache_max_age_myr"] == "not_available"
    assert inventory_by_case["G-LO"]["full_history_available"] == "false"
    assert inventory_by_case["G-LO"]["history_coverage_status"] == "candidate_history_coverage"
    assert "not dense-cache evidence" in inventory_by_case["G-LO"]["dense_cache_lineage"]
    assert (
        "/scratch/bwbrook/xray_cavities_analysis/2026-05-13-c-hi-to33-particles-hdf5/"
        "C-HI.to33.particles.hdf5"
        in inventory_by_case["C-HI"]["dense_cache_lineage"]
    )
    assert "404x404x452" in inventory_by_case["C-HI"]["dense_cache_lineage"]
    assert "docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/completed_run/review_inventory/inventory/payload_inventory.csv" in inventory_by_case["C-HI"]["source_evidence"]

    audit = csv_rows(first / "runtime_semantics_audit.csv")
    assert any("4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5" in row["value"] for row in audit)
    assert any("e80252cf35ff5a06166240e2867d3d485aaf6956" in row["value"] for row in audit)
    assert any("ce4b17cf40ecefabbd4ef4330b75fb63c39d40c2ef1a05a6e5ac87131145bf4" in row["value"] for row in audit)
    assert any("597bf9241fee0eabc1f57a9715a338ee588157787dd2ad1edd939e7c17426f38" in row["value"] for row in audit)
    assert any(row["status"] == "rejected_not_blocking" for row in audit)
    assert metadata["plutokore_source_review"]["status"] == "source_reviewed_candidate_not_production_validated"

    ledger = csv_rows(first / "source_ledger_extract.csv")
    ledger_by_root = {row["root_id"]: row for row in ledger}
    assert len(ledger) == 5
    assert ledger_by_root["production_C-HI_c_hi_fresh"]["particle_file_count"] == "1"
    assert ledger_by_root["production_C-HI_c_hi_fresh"]["regular_file_count"] == "1"
    assert ledger_by_root["production_C-HI_c_hi_prod64"]["particle_file_count"] == "2"
    assert ledger_by_root["production_C-HI_c_hi_prod64"]["symlink_file_count"] == "1"
    assert ledger_by_root["production_C-HI_c_hi_prod64"]["interior_gap_count"] == "722"
    assert ledger_by_root["production_C-LO_c_lo_final"]["interior_gap_count"] == "3391"
    assert ledger_by_root["production_G-LO_g_lo_production"]["particle_file_count"] == "1500"
    assert ledger_by_root["production_G-LO_g_lo_production"]["interior_gap_count"] == "0"
    assert ledger_by_root["production_G-LO_g_lo_guarded"]["particle_file_count"] == "4001"
    assert ledger_by_root["production_G-LO_g_lo_guarded"]["interior_gap_count"] == "0"
    assert metadata["preliminary_history_feasibility"]["one_float64_field_bytes_decimal"] == 7904300544

    gate = {row["gate_id"]: row for row in csv_rows(first / "method_acceptance_gate.csv")}
    assert gate["full_history_G-LO"]["status"] == "pending"
    assert gate["full_history_G-LO"]["passed"] == "false"
    assert "ID/time/schema/continuation-seam" in gate["full_history_G-LO"]["failure_reason"]
    assert gate["current_plutokore_correctness"]["passed"] == "false"
    assert gate["current_plutokore_raytracing"]["passed"] == "false"
    assert all(row["status"] == "rejected_not_blocking" for row in audit if row["audit_id"].startswith("xraise_"))
    decisions = {row["option_id"]: row for row in csv_rows(first / "decision_matrix.csv")}
    assert decisions["g_lo_method_value_of_information_gate"]["status"] == "recommended_next_gate"
    assert decisions["c_hi_c_lo_source_history_reruns"]["status"] == "conditional_not_default"


def test_gate_aggregates_fail_closed_and_rejects_mixed_methods() -> None:
    module = load_module()
    cases = [
        {"case_id": "C-HI", "full_history": False, "runtime_semantics_resolved": False, "method": "loss_aware"},
        {"case_id": "C-LO", "full_history": False, "runtime_semantics_resolved": False, "method": "loss_aware"},
        {"case_id": "G-LO", "full_history": True, "runtime_semantics_resolved": False, "method": "loss_aware"},
    ]
    result = module.evaluate_common_loss_aware_gate(cases)
    assert result["accepted"] is False
    assert "full_comparable_history" in result["failed_requirements"]
    assert "runtime_semantics_resolved" in result["failed_requirements"]

    mixed = [dict(cases[0], full_history=True, runtime_semantics_resolved=True),
             dict(cases[1], full_history=True, runtime_semantics_resolved=True, method="lossless"),
             dict(cases[2], full_history=True, runtime_semantics_resolved=True)]
    with pytest.raises(ValueError, match="mix"):
        module.evaluate_common_loss_aware_gate(mixed)


def test_numerical_validation_fixtures() -> None:
    module = load_module()
    assert module.uniform_emissivity_los_integral(3.5, 2.0) == pytest.approx(7.0)
    values = [0.0, 1.0, 4.0, 1.0, 0.0]
    convolved = module.gaussian_normalized_convolution_flux(values, sigma=0.8)
    assert sum(convolved) == pytest.approx(sum(values), rel=1e-12, abs=1e-12)
    assert module.symmetric_source_rotation_view_invariance(
        radius=2.0, view_angles=(0.0, 45.0, 90.0), tolerance=1e-12
    )
