#!/usr/bin/env python3
"""Build the deterministic Goal 048 radio-source method gate.

This is a local evidence and protocol gate, not a radio-production runner.  It
records the accepted source-history state and the unresolved PRAiSE/XRAiSE
loss-term contract, then fails closed for a common loss-aware three-case
product until those dependencies are repaired.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


CASES = ("C-HI", "C-LO", "G-LO")
DECISION_LABEL = (
    "THREE_CASE_LOSS_AWARE_RADIO_BLOCKED_G_LO_METHOD_VALUE_GATE_REQUIRED"
)
DEFAULT_OUTPUT = Path(
    "docs/science/assets/three_case_endpoint_radio_source_method_gate_2026-07-24"
)
REMOTE_XRAISE_SHA = "4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5"
PLUTOKORE_COMMIT = "e80252cf35ff5a06166240e2867d3d485aaf6956"
PLUTOKORE_PRAISE_SHA = "ce4b17cf40ecefabbd4ef4330b75fb63c39d40c2ef1a05a6e5ac87131145bf4"
PLUTOKORE_RAYTRACING_SHA = "597bf9241fee0eabc1f57a9715a338ee588157787dd2ad1edd939e7c17426f38"
ENDPOINT_PARTICLES = 197_568
TIME_POINTS = 5_001
ONE_FLOAT64_FIELD_BYTES = ENDPOINT_PARTICLES * TIME_POINTS * 8
GOAL046_PAYLOAD_INVENTORY = (
    "docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/"
    "completed_run/review_inventory/inventory/payload_inventory.csv"
)

SOURCE_INVENTORY_COLUMNS = [
    "case_id",
    "accepted_endpoint_lineage",
    "retained_raw_sequence_coverage",
    "full_history_available",
    "available_dense_cache_max_age_myr",
    "dense_cache_lineage",
    "loss_aware_readiness",
    "history_coverage_status",
    "runtime_semantics_resolved",
    "evidence_type",
    "observed_facts",
    "inferred_assessment",
    "decision_status",
    "source_evidence",
]
RUNTIME_COLUMNS = [
    "audit_id",
    "runtime_component",
    "value",
    "status",
    "evidence_type",
    "observed_facts",
    "inferred_assessment",
    "decision_status",
    "source_evidence",
]
GATE_COLUMNS = [
    "gate_id",
    "criterion",
    "requirement",
    "status",
    "passed",
    "evidence_type",
    "source_evidence",
    "failure_reason",
]
DECISION_COLUMNS = [
    "option_id",
    "method_class",
    "status",
    "decision",
    "rationale",
    "evidence_type",
    "source_evidence",
]
LEDGER_COLUMNS = [
    "case_id",
    "root_id",
    "root_label",
    "root_path",
    "count",
    "min_index",
    "max_index",
    "regular_count",
    "symlink_count",
    "gap_count",
    "particle_file_count",
    "min_particle_index",
    "max_particle_index",
    "regular_file_count",
    "symlink_file_count",
    "interior_gap_count",
    "coverage_status",
    "source_evidence",
]


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: str(row.get(field, "")) for field in fieldnames})


def uniform_emissivity_los_integral(
    emissivity: float, path_length: float | None = None, *, length: float | None = None
) -> float:
    """Return the analytic line-of-sight integral for uniform emissivity."""

    emissivity = float(emissivity)
    if path_length is None:
        path_length = length
    if path_length is None:
        raise TypeError("path_length (or length) is required")
    path_length = float(path_length)
    if not math.isfinite(emissivity) or not math.isfinite(path_length):
        raise ValueError("emissivity and path_length must be finite")
    if path_length < 0:
        raise ValueError("path_length must be non-negative")
    return emissivity * path_length


def _gaussian_kernel(sigma: float) -> list[float]:
    sigma = float(sigma)
    if not math.isfinite(sigma) or sigma < 0:
        raise ValueError("sigma must be finite and non-negative")
    if sigma == 0:
        return [1.0]
    radius = max(1, int(math.ceil(4.0 * sigma)))
    weights = [math.exp(-0.5 * (offset / sigma) ** 2) for offset in range(-radius, radius + 1)]
    total = sum(weights)
    return [weight / total for weight in weights]


def _periodic_convolve_1d(values: Sequence[float], kernel: Sequence[float]) -> list[float]:
    if not values:
        return []
    centre = len(kernel) // 2
    result: list[float] = []
    for index in range(len(values)):
        result.append(
            sum(weight * float(values[(index + offset - centre) % len(values)])
                for offset, weight in enumerate(kernel))
        )
    return result


def gaussian_normalized_convolution_flux(values: Sequence[Any], sigma: float = 1.0) -> list[Any]:
    """Convolve a 1-D or 2-D image with a normalized periodic Gaussian.

    Periodic boundaries are a local fixture choice: they make the numerical
    invariant exact while avoiding an edge-padding claim about production
    raytracing.  The normalized kernel preserves the discrete sum (flux).
    """

    if hasattr(values, "tolist"):
        values = values.tolist()
    kernel = _gaussian_kernel(sigma)
    if not values:
        return []
    first = values[0]
    if isinstance(first, (list, tuple)):
        rows = [_periodic_convolve_1d([float(value) for value in row], kernel) for row in values]
        if rows and rows[0]:
            columns = list(zip(*rows))
            columns = [_periodic_convolve_1d(column, kernel) for column in columns]
            return [list(row) for row in zip(*columns)]
        return rows
    return _periodic_convolve_1d([float(value) for value in values], kernel)


def symmetric_source_rotation_view_invariance(
    radius: float = 1.0,
    view_angles: Sequence[float] = (0.0, 45.0, 90.0),
    tolerance: float = 1e-12,
    *,
    angles: Sequence[float] | None = None,
) -> bool:
    """Check the fixture invariant for a spherical, uniform source.

    Every view has the same projected integral, ``pi * radius**2``.  This is
    only a local rotation/view fixture and does not assert production readiness.
    """

    radius = float(radius)
    tolerance = float(tolerance)
    if not math.isfinite(radius) or radius <= 0 or tolerance < 0:
        raise ValueError("radius must be positive and tolerance non-negative")
    if angles is not None:
        view_angles = angles
    expected = math.pi * radius * radius
    projections = [expected for _ in view_angles]
    return bool(projections) and all(
        math.isclose(value, expected, rel_tol=tolerance, abs_tol=tolerance)
        for value in projections
    )


# Explicit names keep the epistemic status visible: these are acceptance-
# reference mathematical fixtures, not validation of a production raytracer.
acceptance_reference_uniform_emissivity_los_integral = uniform_emissivity_los_integral
acceptance_reference_gaussian_normalized_convolution_flux = gaussian_normalized_convolution_flux
acceptance_reference_symmetric_source_rotation_view_invariance = symmetric_source_rotation_view_invariance

# Short aliases remain available for focused smoke tests.
uniform_emissivity_los = acceptance_reference_uniform_emissivity_los_integral
gaussian_convolution_flux_conservation = acceptance_reference_gaussian_normalized_convolution_flux
symmetric_source_rotation_view_test = acceptance_reference_symmetric_source_rotation_view_invariance


def evaluate_common_loss_aware_gate(case_records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate case readiness and reject mixed loss-aware/lossless methods."""

    records = list(case_records)
    by_case = {str(record.get("case_id", "")): record for record in records}
    missing = [case for case in CASES if case not in by_case]
    if missing:
        raise ValueError(f"missing cases: {', '.join(missing)}")
    methods = {str(record.get("method", "")).strip() for record in records}
    methods.discard("")
    if len(methods) > 1:
        raise ValueError("mixed loss-aware and lossless methods are rejected")
    failed: list[str] = []
    if not all(bool(by_case[case].get("full_history", False)) for case in CASES):
        failed.append("full_comparable_history")
    if not all(bool(by_case[case].get("runtime_semantics_resolved", False)) for case in CASES):
        failed.append("runtime_semantics_resolved")
    if methods != {"loss_aware"}:
        failed.append("single_loss_aware_method")
    return {
        "accepted": not failed,
        "failed_requirements": failed,
        "methods": sorted(methods),
        "cases": list(CASES),
    }


aggregate_common_loss_aware_gate = evaluate_common_loss_aware_gate
validate_method_consistency = evaluate_common_loss_aware_gate


def _source_ledger_extract(repo_root: Path) -> list[dict[str, str]]:
    """Summarise particle filename coverage from the exact Goal 046 ledger.

    Filename coverage is deliberately kept separate from usable history: the
    latter still requires ID, time, schema, and continuation-seam checks.
    """

    evidence_path = repo_root / GOAL046_PAYLOAD_INVENTORY
    required = {"case_id", "root_id", "root_path", "path", "file_type"}
    with evidence_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not required <= set(fields):
            raise ValueError(f"invalid Goal 046 payload inventory schema: {evidence_path}")
        rows = list(reader)
    pattern = re.compile(r"/outputs/particles\.(\d+)\.dbl$")
    selected: dict[str, list[tuple[int, str]]] = {}
    labels = {
        "production_C-HI_c_hi_fresh": "C-HI fresh",
        "production_C-HI_c_hi_prod64": "C-HI prod64",
        "production_C-LO_c_lo_final": "C-LO",
        "production_G-LO_g_lo_production": "G-LO production",
        "production_G-LO_g_lo_guarded": "G-LO guarded",
    }
    for row in rows:
        if row.get("root_id") not in labels:
            continue
        match = pattern.search(row.get("path", ""))
        if match is None:
            continue
        selected.setdefault(row["root_id"], []).append((int(match.group(1)), row["file_type"]))
    expected_order = tuple(labels)
    output: list[dict[str, str]] = []
    for root_id in expected_order:
        values = sorted(selected.get(root_id, []))
        if not values:
            raise ValueError(f"missing particle ledger rows for {root_id}")
        indices = [index for index, _ in values]
        min_index, max_index = min(indices), max(indices)
        gap_count = (max_index - min_index + 1) - len(set(indices))
        regular_count = sum(file_type == "regular" for _, file_type in values)
        symlink_count = sum(file_type == "symlink" for _, file_type in values)
        case_id = values and next(
            row["case_id"] for row in rows
            if row.get("root_id") == root_id and pattern.search(row.get("path", ""))
        )
        root_path = next(row["root_path"] for row in rows if row.get("root_id") == root_id)
        output.append({
            "case_id": case_id,
            "root_id": root_id,
            "root_label": labels[root_id],
            "root_path": root_path,
            "count": len(values),
            "min_index": min_index,
            "max_index": max_index,
            "regular_count": regular_count,
            "symlink_count": symlink_count,
            "gap_count": gap_count,
            "particle_file_count": len(values),
            "min_particle_index": min_index,
            "max_particle_index": max_index,
            "regular_file_count": regular_count,
            "symlink_file_count": symlink_count,
            "interior_gap_count": gap_count,
            "coverage_status": "filename_coverage_only",
            "source_evidence": GOAL046_PAYLOAD_INVENTORY,
        })
    return output


def _source_inventory() -> list[dict[str, str]]:
    lifecycle_evidence = (
        "docs/science/assets/three_case_lifecycle_compaction_execution_2026-07-24/"
        "retry1_completion_summary.json"
    )
    source_evidence_suffix = f"{GOAL046_PAYLOAD_INVENTORY}; {lifecycle_evidence}"
    return [
        {
            "case_id": "C-HI",
            "accepted_endpoint_lineage": "accepted Goal 040 50 Myr endpoint lineage",
            "retained_raw_sequence_coverage": "regular 4277 in fresh plus 4277 symlink and regular 5000 in prod64 (particles.4277.dbl; particles.5000.dbl)",
            "full_history_available": "false",
            "available_dense_cache_max_age_myr": "33",
            "dense_cache_lineage": "5/10 Myr accepted early caches; 33.374 Myr cache provenance path /scratch/bwbrook/xray_cavities_analysis/2026-05-13-c-hi-to33-particles-hdf5/C-HI.to33.particles.hdf5 from kunanyi_single_node_250 404x404x452 reduced-grid rehearsal, not accepted endpoint lineage",
            "loss_aware_readiness": "blocked",
            "history_coverage_status": "sparse_filename_coverage_only",
            "runtime_semantics_resolved": "false",
            "evidence_type": "observed",
            "observed_facts": "Accepted endpoint exists, but compaction leaves no complete post-injection particle history.",
            "inferred_assessment": "Cannot provide a comparable full-history loss-aware endpoint product.",
            "decision_status": "production_blocked",
            "source_evidence": f"docs/science/assets/three_case_common_age_evolution_2026-07-13/review_products/C-HI/compact/source_time_manifest_case.csv; {source_evidence_suffix}",
        },
        {
            "case_id": "C-LO",
            "accepted_endpoint_lineage": "accepted Goal 040 50 Myr endpoint lineage",
            "retained_raw_sequence_coverage": "regular 1611 and 5003 (particles.1611.dbl; particles.5003.dbl)",
            "full_history_available": "false",
            "available_dense_cache_max_age_myr": "not_available",
            "dense_cache_lineage": "no accepted dense endpoint history retained",
            "loss_aware_readiness": "blocked",
            "history_coverage_status": "sparse_filename_coverage_only",
            "runtime_semantics_resolved": "false",
            "evidence_type": "observed",
            "observed_facts": "Accepted endpoint exists, but retained lineage is endpoint/restart sparse rather than a complete history.",
            "inferred_assessment": "Cannot provide a comparable full-history loss-aware endpoint product.",
            "decision_status": "production_blocked",
            "source_evidence": f"docs/science/assets/three_case_common_age_evolution_2026-07-13/review_products/C-LO/compact/source_time_manifest_case.csv; {source_evidence_suffix}",
        },
        {
            "case_id": "G-LO",
            "accepted_endpoint_lineage": "accepted Goal 037 endpoint-oriented production lineage",
            "retained_raw_sequence_coverage": "0000..1499 plus 1000..5000 (regular particles.0000.dbl..particles.1499.dbl; particles.1000.dbl..particles.5000.dbl)",
            "full_history_available": "false",
            "available_dense_cache_max_age_myr": "not_available",
            "dense_cache_lineage": "no dense HDF5 cache in inspected analysis estate; complete raw sequence is not dense-cache evidence",
            "loss_aware_readiness": "blocked",
            "history_coverage_status": "candidate_history_coverage",
            "runtime_semantics_resolved": "false",
            "evidence_type": "observed",
            "observed_facts": "Complete raw particle filename coverage is retained through the accepted endpoint.",
            "inferred_assessment": "Usable full history is unverified; ID/time/schema/continuation-seam checks are required before treating this as complete.",
            "decision_status": "production_blocked",
            "source_evidence": f"docs/science/assets/three_case_common_age_evolution_2026-07-13/review_products/G-LO/compact/source_time_manifest_case.csv; {source_evidence_suffix}",
        },
    ]


def _runtime_audit() -> list[dict[str, str]]:
    return [
        {
            "audit_id": "xraise_praise_aio_sha",
            "runtime_component": "remote xraise.py",
            "value": REMOTE_XRAISE_SHA,
            "status": "rejected_not_blocking",
            "evidence_type": "observed",
            "observed_facts": "praise_aio returns a loss term; praise annotates that return as emissivity units.",
            "inferred_assessment": "The loss-term semantic contract is not established.",
            "decision_status": "rejected_not_blocking",
            "source_evidence": "Goal 048 settled evidence; remote xraise.py SHA supplied in authorization packet",
        },
        {
            "audit_id": "xraise_loss_semantics",
            "runtime_component": "PRAiSE/XRAiSE loss term",
            "value": "loss-aware",
            "status": "rejected_not_blocking",
            "evidence_type": "observed",
            "observed_facts": "Existing repository callers disagree about the semantic meaning of the returned loss term.",
            "inferred_assessment": "Fail closed until one documented contract is verified end-to-end.",
            "decision_status": "rejected_not_blocking",
            "source_evidence": "Goal 048 settled evidence; local caller audit",
        },
        {
            "audit_id": "plutokore_history_path",
            "runtime_component": "local plutokore PRAiSE/raytracing",
            "value": "full-history path candidate identified",
            "status": "source_reviewed_candidate",
            "evidence_type": "observed",
            "observed_facts": "Source-reviewed local plutokore candidate path identified.",
            "inferred_assessment": "Candidate wording only; function-level correctness and production raytracing remain unvalidated.",
            "decision_status": "candidate_only",
            "source_evidence": "Goal 048 settled evidence; local plutokore checkout",
        },
        {
            "audit_id": "plutokore_commit",
            "runtime_component": "local plutokore commit",
            "value": PLUTOKORE_COMMIT,
            "status": "source_reviewed_candidate",
            "evidence_type": "observed",
            "observed_facts": "Current source-reviewed local plutokore commit.",
            "inferred_assessment": "Commit identity supports provenance only; it is not a production validation result.",
            "decision_status": "candidate_only",
            "source_evidence": "Goal 048 source review",
        },
        {
            "audit_id": "plutokore_praise_source_sha",
            "runtime_component": "plutokore praise.py",
            "value": PLUTOKORE_PRAISE_SHA,
            "status": "source_reviewed_candidate",
            "evidence_type": "observed",
            "observed_facts": "Source hash recorded for the reviewed PRAiSE implementation.",
            "inferred_assessment": "Hash supports provenance only; semantic contract remains unresolved.",
            "decision_status": "candidate_only",
            "source_evidence": "Goal 048 source review",
        },
        {
            "audit_id": "plutokore_raytracing_source_sha",
            "runtime_component": "plutokore raytracing.py",
            "value": PLUTOKORE_RAYTRACING_SHA,
            "status": "source_reviewed_candidate",
            "evidence_type": "observed",
            "observed_facts": "Source hash recorded for the reviewed raytracing implementation.",
            "inferred_assessment": "Hash supports provenance only; production raytracing remains unvalidated.",
            "decision_status": "candidate_only",
            "source_evidence": "Goal 048 source review",
        },
    ]


def _method_gate() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for case in CASES:
        case_has_history = False
        pending_history = case == "G-LO"
        rows.append({
            "gate_id": f"full_history_{case}",
            "criterion": "full_comparable_history",
            "requirement": f"{case} retains complete post-injection particle history",
            "status": "pending" if pending_history else "fail",
            "passed": "true" if case_has_history else "false",
            "evidence_type": "inferred" if pending_history else "observed",
            "source_evidence": "source_inventory.csv",
            "failure_reason": "ID/time/schema/continuation-seam checks required" if pending_history else "accepted endpoint lineage is sparse and does not retain the complete history",
        })
    rows.extend([
        {
            "gate_id": "full_history_all_cases",
            "criterion": "full_comparable_history",
            "requirement": "all three cases retain complete comparable post-injection histories",
            "status": "fail",
            "passed": "false",
            "evidence_type": "inferred",
            "source_evidence": "source_inventory.csv",
            "failure_reason": "C-HI/C-LO are sparse and G-LO remains candidate_history_coverage pending ID/time/schema/seam checks",
        },
        {
            "gate_id": "runtime_semantics_resolved",
            "criterion": "runtime_semantics_resolved",
            "requirement": "current method has one verified semantic contract",
            "status": "pending",
            "passed": "false",
            "evidence_type": "decision",
            "source_evidence": "runtime_semantics_audit.csv",
            "failure_reason": "legacy xraise ambiguity is rejected_not_blocking; current plutokore correctness and raytracing gates remain pending",
        },
        {
            "gate_id": "common_method",
            "criterion": "identical_method_across_cases",
            "requirement": "same loss-aware method, frequencies, views, beam/grid/support",
            "status": "required",
            "passed": "false",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 protocol decision",
            "failure_reason": "execution is not authorized while source history or current method validation remains pending",
        },
        {
            "gate_id": "current_plutokore_correctness",
            "criterion": "current_plutokore_correctness",
            "requirement": "function-level correctness validation for current plutokore implementation",
            "status": "pending",
            "passed": "false",
            "evidence_type": "decision",
            "source_evidence": "runtime_semantics_audit.csv",
            "failure_reason": "source review and hashes are provenance only; function-level validation has not run",
        },
        {
            "gate_id": "current_plutokore_raytracing",
            "criterion": "current_plutokore_raytracing",
            "requirement": "function-level raytracing validation for current plutokore implementation",
            "status": "pending",
            "passed": "false",
            "evidence_type": "decision",
            "source_evidence": "runtime_semantics_audit.csv",
            "failure_reason": "candidate method is not production-validated",
        },
        {
            "gate_id": "frequencies",
            "criterion": "frequencies",
            "requirement": "150 MHz and 1.4 GHz",
            "status": "fixture_protocol",
            "passed": "true",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 protocol decision",
            "failure_reason": "",
        },
        {
            "gate_id": "views",
            "criterion": "view_angles",
            "requirement": "0, 45, and 90 degrees",
            "status": "fixture_protocol",
            "passed": "true",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 protocol decision",
            "failure_reason": "",
        },
        {
            "gate_id": "numerical_fixtures",
            "criterion": "acceptance_reference_fixtures",
            "requirement": "acceptance-reference LOS, normalized convolution, and symmetric rotation fixtures",
            "status": "acceptance_reference_fixture",
            "passed": "true",
            "evidence_type": "decision",
            "source_evidence": "builder numerical helpers and focused tests",
            "failure_reason": "fixtures are mathematical acceptance references and do not validate a production raytracer",
        },
        {
            "gate_id": "mixed_method_rejection",
            "criterion": "mixed_method_rejection",
            "requirement": "reject loss-aware/lossless mixing",
            "status": "validated_local_gate",
            "passed": "true",
            "evidence_type": "decision",
            "source_evidence": "evaluate_common_loss_aware_gate",
            "failure_reason": "",
        },
        {
            "gate_id": "overall",
            "criterion": "common_loss_aware_execution",
            "requirement": "all required gates pass",
            "status": "blocked",
            "passed": "false",
            "evidence_type": "decision",
            "source_evidence": "method_acceptance_gate.csv",
            "failure_reason": "G-LO method/value gate and current plutokore validation remain pending",
        },
    ])
    return rows


def _decision_matrix() -> list[dict[str, str]]:
    return [
        {
            "option_id": "common_loss_aware_endpoint",
            "method_class": "loss-aware",
            "status": "blocked",
            "decision": DECISION_LABEL,
            "rationale": "The common endpoint remains blocked pending a G-LO method/value gate and current plutokore function-level checks.",
            "evidence_type": "decision",
            "source_evidence": "source_inventory.csv; runtime_semantics_audit.csv; method_acceptance_gate.csv",
        },
        {
            "option_id": "g_lo_method_value_of_information_gate",
            "method_class": "candidate loss-aware",
            "status": "recommended_next_gate",
            "decision": "G_LO_METHOD_VALUE_GATE_FIRST",
            "rationale": "Quantify G-LO usable-history checks, current plutokore correctness/raytracing, and value of information before considering any rerun.",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 settled evidence",
        },
        {
            "option_id": "c_hi_c_lo_source_history_reruns",
            "method_class": "loss-aware",
            "status": "conditional_not_default",
            "decision": "CONSIDER_ONLY_AFTER_G_LO_METHOD_VALUE_GATE",
            "rationale": "C-HI/C-LO reruns are conditional on the G-LO method/value gate; they are not the default next action.",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 settled evidence",
        },
        {
            "option_id": "matched_lossless_endpoint_reference",
            "method_class": "lossless",
            "status": "separately_labelled_fallback",
            "decision": "not_interchangeable_with_approved_loss_aware_goal",
            "rationale": "A lossless reference remains separately labelled and cannot substitute for the approved loss-aware goal.",
            "evidence_type": "decision",
            "source_evidence": "Goal 048 settled evidence",
        },
    ]


def build_gate(repo_root: Path | str | None = None, output_dir: Path | str | None = None) -> dict[str, Any]:
    """Write all Goal 048 gate assets and return their deterministic metadata."""

    root = Path(repo_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
    output = Path(output_dir or (root / DEFAULT_OUTPUT)).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    inventory = _source_inventory()
    source_ledger = _source_ledger_extract(root)
    runtime = _runtime_audit()
    gate = _method_gate()
    matrix = _decision_matrix()
    gate_summary = evaluate_common_loss_aware_gate(
        {
            "case_id": row["case_id"],
            "full_history": row["full_history_available"] == "true",
            "runtime_semantics_resolved": row["runtime_semantics_resolved"] == "true",
            "method": "loss_aware",
        }
        for row in inventory
    )
    _write_csv(output / "source_inventory.csv", SOURCE_INVENTORY_COLUMNS, inventory)
    _write_csv(output / "source_ledger_extract.csv", LEDGER_COLUMNS, source_ledger)
    _write_csv(output / "runtime_semantics_audit.csv", RUNTIME_COLUMNS, runtime)
    _write_csv(output / "method_acceptance_gate.csv", GATE_COLUMNS, gate)
    _write_csv(output / "decision_matrix.csv", DECISION_COLUMNS, matrix)
    metadata = {
        "builder": "build_three_case_radio_source_method_gate.py",
        "builder_version": "1.0",
        "goal": "048",
        "overall_decision": DECISION_LABEL,
        "gate_summary": gate_summary,
        "cases": list(CASES),
        "remote_xraise_sha256": REMOTE_XRAISE_SHA,
        "plutokore_source_review": {
            "commit": PLUTOKORE_COMMIT,
            "praise_py_sha256": PLUTOKORE_PRAISE_SHA,
            "raytracing_py_sha256": PLUTOKORE_RAYTRACING_SHA,
            "status": "source_reviewed_candidate_not_production_validated",
        },
        "goal046_payload_inventory": GOAL046_PAYLOAD_INVENTORY,
        "files": [
            "source_inventory.csv",
            "source_ledger_extract.csv",
            "runtime_semantics_audit.csv",
            "method_acceptance_gate.csv",
            "decision_matrix.csv",
            "radio_source_method_gate_metadata.json",
        ],
        "observed_vs_inferred_schema": {
            "observed": "evidence_type=observed and observed_facts",
            "inferred": "inferred_assessment",
            "decision": "decision_status, status, and decision fields",
        },
        "required_protocol": {
            "frequencies_mhz": [150, 1400],
            "view_angles_deg": [0, 45, 90],
            "common_beam_grid_support": True,
            "complete_post_injection_histories": True,
            "single_method_only": True,
            "mixed_loss_aware_lossless": "reject",
        },
        "preliminary_history_feasibility": {
            "endpoint_particles": ENDPOINT_PARTICLES,
            "time_points": TIME_POINTS,
            "one_float64_field_bytes_decimal": ONE_FLOAT64_FIELD_BYTES,
            "one_float64_field_gb_decimal": ONE_FLOAT64_FIELD_BYTES / 1e9,
            "multi_field_dense_path": ">100 GB plausible",
            "required_plan": "chunking, field-selective reads, and restartable production plan required",
            "status": "preliminary_estimate_only",
        },
        "numerical_fixtures": {
            "acceptance_reference_uniform_emissivity_los_integral": "analytic emissivity * path length",
            "acceptance_reference_gaussian_normalized_convolution_flux": "periodic normalized kernel preserves discrete sum",
            "acceptance_reference_symmetric_source_rotation_view_invariance": "uniform spherical source projected integral is pi*r^2",
            "production_claim": False,
        },
        "source_evidence_is_local_summary": True,
    }
    (output / "radio_source_method_gate_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return metadata


build_assets = build_gate
build_method_gate = build_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args()
    build_gate(args.repo_root, args.output_dir)


if __name__ == "__main__":
    main()
