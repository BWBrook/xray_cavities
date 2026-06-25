#!/usr/bin/env python3
"""Build Goal 018 local-only source-age sampling planning assets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_source_age_sampling_plan_2026-06-25"

EARLY_METRICS = ASSET_ROOT / "c_hi_early_snapshot_series_2026-05-10/early_snapshot_series_metrics.csv"
EARLY_SNAPSHOTS = ASSET_ROOT / "c_hi_early_snapshot_series_2026-05-10/compact/snapshots.csv"
TO10_METRICS = ASSET_ROOT / "c_hi_to10_snapshot_series_2026-05-11/c_hi_to10_snapshot_series_metrics.csv"
TO10_SNAPSHOTS = ASSET_ROOT / "c_hi_to10_snapshot_series_2026-05-11/compact/snapshots.csv"

PROD64_ROOT = (
    "/scratch/bwbrook/xray_cavities_runs/"
    "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs"
)
REFINED_ACCUMULATOR = "edge_overlap_uniform_cell_projection"
FINAL_CODE_TIME = 15330.069689399999
FINAL_TIME_MYR = 50.00000000000777
CODE_TIME_PER_MYR = FINAL_CODE_TIME / FINAL_TIME_MYR

CANDIDATE_COLUMNS = [
    "candidate_id",
    "case_id",
    "run_family",
    "output_index",
    "timestep",
    "time_code",
    "time_myr",
    "particle_reference",
    "source_age_interpretation",
    "input_h5_or_expected_path",
    "evidence_path",
    "evidence_scope",
    "confidence",
    "execution_readiness",
    "missing_info",
    "recommended_role",
]
SAMPLING_COLUMNS = [
    "plan_step",
    "phase",
    "candidate_id",
    "output_index",
    "timestep",
    "time_myr",
    "views",
    "run_action",
    "product_surface",
    "rationale",
    "go_no_go_gate",
    "execution_status",
]
CONTRACT_COLUMNS = [
    "contract_item",
    "contract_value",
    "required",
    "validation_or_stop_rule",
    "notes",
]
RUNTIME_COLUMNS = [
    "evidence_id",
    "scope",
    "source_goal_or_job",
    "walltime",
    "cpu_time",
    "memory",
    "ncpus",
    "views_or_products",
    "estimate_basis",
    "planning_use",
]
RISK_COLUMNS = [
    "risk_id",
    "status",
    "applies_to",
    "mitigation",
    "source_evidence",
    "next_goal_implication",
]


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def fmt_float(value: float) -> str:
    return f"{value:.15g}"


def production_h5(output_index: int) -> str:
    return f"{PROD64_ROOT}/data.{output_index:04d}.flt.h5"


def source_time_from_code(time_code: float) -> str:
    return fmt_float(time_code / CODE_TIME_PER_MYR)


def snapshot_by_output(path: Path) -> dict[str, dict[str, str]]:
    return {row["output"]: row for row in read_rows(path)}


def historical_series_rows(
    metrics_path: Path,
    snapshots_path: Path,
    *,
    series_label: str,
    evidence_scope: str,
    recommended_outputs: set[str],
) -> list[dict[str, str]]:
    snapshots = snapshot_by_output(snapshots_path)
    rows: list[dict[str, str]] = []
    for metric in read_rows(metrics_path):
        output = metric["grid_output"]
        snap = snapshots[output]
        role = (
            "science_candidate_needs_fullgrid_equivalent_preflight"
            if output in recommended_outputs
            else "context_candidate_not_first_pass"
        )
        rows.append(
            {
                "candidate_id": f"{series_label}_output{int(output):04d}",
                "case_id": "C-HI",
                "run_family": series_label,
                "output_index": output,
                "timestep": snap["timestep"],
                "time_code": "",
                "time_myr": fmt_float(float(metric["grid_time_myr"])),
                "particle_reference": metric["particle_output"],
                "source_age_interpretation": "locally processed early source-age diagnostic",
                "input_h5_or_expected_path": snap["input_h5"],
                "evidence_path": display_path(metrics_path),
                "evidence_scope": evidence_scope,
                "confidence": "high_for_local_historical_diagnostic",
                "execution_readiness": "not_default_goal018_execution_target_until_fullgrid_equivalent_is_verified",
                "missing_info": (
                    "future authorized remote preflight must verify whether an equivalent final-production "
                    "full-grid HDF5 and matching particle/truth inputs exist"
                ),
                "recommended_role": role,
            }
        )
    return rows


def final_production_candidate_rows() -> list[dict[str, str]]:
    catalogue = [
        ("46", "13796.84", "44372"),
        ("47", "14103.53", "45349"),
        ("48", "14410.22", "46326"),
        ("49", "14716.60", "47302"),
        ("50", "15023.29", "48279"),
        ("51", "15330.069689399999", "49253"),
    ]
    rows: list[dict[str, str]] = []
    for output, time_code, step in catalogue:
        output_i = int(output)
        candidate_id = f"fullgrid_prod64_output{output_i:04d}"
        if output == "46":
            role = "recommended_first_pass_new_sample"
        elif output == "49":
            role = "recommended_first_pass_new_sample"
        elif output == "51":
            role = "accepted_endpoint_control_reuse_not_rerun_by_default"
        else:
            role = "late_fullgrid_context_candidate"
        rows.append(
            {
                "candidate_id": candidate_id,
                "case_id": "C-HI",
                "run_family": "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64",
                "output_index": output,
                "timestep": f"Timestep_{output}",
                "time_code": time_code,
                "time_myr": source_time_from_code(float(time_code)),
                "particle_reference": step,
                "source_age_interpretation": "final-production late-source-age float-output catalogue",
                "input_h5_or_expected_path": production_h5(output_i),
                "evidence_path": "docs/exchange/logs/2026-06-07-c-hi-fullgrid-agn-impi-r9-prod64-integrity.md",
                "evidence_scope": "local catalogue tail and final-product integrity evidence; no remote probe in Goal 018",
                "confidence": "high_for_catalogued_fullgrid_late_outputs",
                "execution_readiness": (
                    "accepted_control_already_processed"
                    if output == "51"
                    else "candidate_for_future_post_maintenance_preflight"
                ),
                "missing_info": (
                    "future authorized preflight should verify file presence, HDF5 readability, timestep, "
                    "and particle/cavity inputs immediately before submission"
                ),
                "recommended_role": role,
            }
        )
    rows.append(
        {
            "candidate_id": "mini_production_output0039",
            "case_id": "C-HI",
            "run_family": "2026-05-13-c-hi-8node-mini-production",
            "output_index": "39",
            "timestep": "Timestep_39",
            "time_code": "",
            "time_myr": "33.374180",
            "particle_reference": "particles.3343.dbl",
            "source_age_interpretation": "mini-production intermediate source age",
            "input_h5_or_expected_path": "data.0039.flt.h5",
            "evidence_path": "docs/exchange/current_status.md",
            "evidence_scope": "local handoff records the mini-production endpoint, not a default final-production input",
            "confidence": "medium_for_context_only",
            "execution_readiness": "not_default_goal018_execution_target",
            "missing_info": "future goal must decide whether mini-production context belongs with final-production source-age sampling",
            "recommended_role": "context_candidate_not_first_pass",
        }
    )
    return rows


def candidate_snapshot_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend(
        historical_series_rows(
            EARLY_METRICS,
            EARLY_SNAPSHOTS,
            series_label="early_segment",
            evidence_scope="existing 1-5 Myr aligned truth/cavity/XRAiSE/radio diagnostic series",
            recommended_outputs={"8"},
        )
    )
    rows.extend(
        historical_series_rows(
            TO10_METRICS,
            TO10_SNAPSHOTS,
            series_label="to10_segment",
            evidence_scope="existing 6-10 Myr compact diagnostic series",
            recommended_outputs={"14"},
        )
    )
    rows.extend(final_production_candidate_rows())
    return rows


def proposed_sampling_plan_rows() -> list[dict[str, str]]:
    return [
        {
            "plan_step": "1",
            "phase": "post_maintenance_preflight",
            "candidate_id": "fullgrid_prod64_output0046;fullgrid_prod64_output0049;fullgrid_prod64_output0051",
            "output_index": "46;49;51",
            "timestep": "Timestep_46;Timestep_49;Timestep_51",
            "time_myr": "44.999274;47.999129;50.000000",
            "views": "0deg;45deg;90deg",
            "run_action": "verify_only_before_any_submission",
            "product_surface": "HDF5 readability, timestep existence, vars rho/prs/tr1/vx1/vx2/vx3, particle/cavity input availability",
            "rationale": "keeps first pass on locally evidenced final-production late-source-age outputs",
            "go_no_go_gate": "if any target file/timestep/input is missing or unreadable, wake X-ray Cavities before substituting another age",
            "execution_status": "not_authorized_by_goal018",
        },
        {
            "plan_step": "2",
            "phase": "first_pass_new_sample",
            "candidate_id": "fullgrid_prod64_output0046",
            "output_index": "46",
            "timestep": "Timestep_46",
            "time_myr": "44.999274",
            "views": "0deg;45deg;90deg",
            "run_action": "post_process_if_future_goal_authorizes",
            "product_surface": "compact X-ray/tracer projection products with refined nonzero-view accumulation",
            "rationale": "first late-source-age point with exact final-production catalogue evidence before the accepted endpoint",
            "go_no_go_gate": "must pass HDF5/timestep/readability preflight and declare accumulator metadata",
            "execution_status": "planned_only",
        },
        {
            "plan_step": "3",
            "phase": "first_pass_new_sample",
            "candidate_id": "fullgrid_prod64_output0049",
            "output_index": "49",
            "timestep": "Timestep_49",
            "time_myr": "47.999129",
            "views": "0deg;45deg;90deg",
            "run_action": "post_process_if_future_goal_authorizes",
            "product_surface": "compact X-ray/tracer projection products with refined nonzero-view accumulation",
            "rationale": "second late-source-age point close enough to the endpoint to test sensitivity without opening a broad sweep",
            "go_no_go_gate": "must pass HDF5/timestep/readability preflight and preserve no-overwrite policy",
            "execution_status": "planned_only",
        },
        {
            "plan_step": "4",
            "phase": "control_reference",
            "candidate_id": "fullgrid_prod64_output0051",
            "output_index": "51",
            "timestep": "Timestep_51",
            "time_myr": "50.000000",
            "views": "0deg Goal005;45deg Goal016 refined;90deg Goal016 refined",
            "run_action": "reuse_accepted_control_surface",
            "product_surface": "accepted endpoint products; no default rerun",
            "rationale": "keeps the future run smaller and avoids overwriting accepted Goal 005/016 assets",
            "go_no_go_gate": "rerun endpoint only if a future goal explicitly requires uniform-code reproducibility",
            "execution_status": "already_accepted_reference",
        },
        {
            "plan_step": "5",
            "phase": "held_second_wave_context",
            "candidate_id": "early_segment_output0008;to10_segment_output0014",
            "output_index": "8;14",
            "timestep": "Timestep_8;Timestep_14",
            "time_myr": "4.999436;9.999876",
            "views": "0deg;45deg;90deg if later authorized",
            "run_action": "hold_pending_fullgrid_equivalent_preflight",
            "product_surface": "not in first pass",
            "rationale": "science-useful early anchors exist locally but are from segment diagnostics, not the default final-production tree",
            "go_no_go_gate": "do not substitute segment-era products into the final-production source-age run without explicit review",
            "execution_status": "held",
        },
    ]


def post_maintenance_contract_rows() -> list[dict[str, str]]:
    return [
        {
            "contract_item": "authorization",
            "contract_value": "future goal required after Kunanyi maintenance and explicit X-ray Cavities/Barry approval",
            "required": "yes",
            "validation_or_stop_rule": "Goal 018 authorizes planning only; no submission or staging",
            "notes": "prevents accidental execution during the outage window",
        },
        {
            "contract_item": "input_root",
            "contract_value": PROD64_ROOT,
            "required": "yes",
            "validation_or_stop_rule": "verify on Kunanyi only in future authorized execution goal",
            "notes": "derived from accepted final-production endpoint evidence",
        },
        {
            "contract_item": "target_snapshots_first_pass",
            "contract_value": "data.0046.flt.h5::Timestep_46 and data.0049.flt.h5::Timestep_49; reuse data.0051.flt.h5 accepted endpoint",
            "required": "yes",
            "validation_or_stop_rule": "stop before substitution if either new target is absent or unreadable",
            "notes": "keeps run to two new late-source-age samples plus existing endpoint reference",
        },
        {
            "contract_item": "views",
            "contract_value": "0deg,45deg,90deg for each new source age",
            "required": "yes",
            "validation_or_stop_rule": "nonzero views must report projection.projected_accumulation=edge_overlap_uniform_cell_projection",
            "notes": "uses Goal 017 preferred control surface",
        },
        {
            "contract_item": "product_surface",
            "contract_value": "compact X-ray/tracer maps, projection metrics, metadata JSON, provenance CSV, stdout/stderr, remote archive",
            "required": "yes",
            "validation_or_stop_rule": "finite positive metrics, expected timestep/view labels, parseable CSV/JSON, archive SHA",
            "notes": "no radio/PRAiSE/cavity regeneration unless a future packet explicitly adds it",
        },
        {
            "contract_item": "no_overwrite_policy",
            "contract_value": "write a new dated source-age asset bundle; do not overwrite Goal 005/011/012/016/017 assets",
            "required": "yes",
            "validation_or_stop_rule": "local packaging must preserve accepted historical and refined products byte-for-byte",
            "notes": "historical Goal 011/012 products remain diagnostics",
        },
        {
            "contract_item": "pbs_stop_rule",
            "contract_value": "stage, submit one bounded post-processing job, verify queued/running, wake X-ray Cavities, then stop",
            "required": "yes",
            "validation_or_stop_rule": "do not poll until Barry reports completion email or explicitly requests a re-check",
            "notes": "reuse the established Goal 011/012/016 operational pattern",
        },
        {
            "contract_item": "maintenance_window",
            "contract_value": "do not submit during the 2026-06-26 09:00 Hobart 72-hour Kunanyi outage",
            "required": "yes",
            "validation_or_stop_rule": "if timing is unclear, wake instead of submitting",
            "notes": "Goal 018 remains local-only planning",
        },
    ]


def runtime_resource_estimate_rows() -> list[dict[str, str]]:
    return [
        {
            "evidence_id": "goal011_45deg_historical",
            "scope": "single final 45deg post-processing product",
            "source_goal_or_job": "Goal 011 / 699815.kunanyi-ohpc",
            "walltime": "00:16:46",
            "cpu_time": "00:11:32",
            "memory": "1260168kb",
            "ncpus": "1",
            "views_or_products": "45deg historical projection",
            "estimate_basis": "accepted PBS completion email",
            "planning_use": "single-view reference only; historical accumulator superseded for future nonzero views",
        },
        {
            "evidence_id": "goal012_90deg_historical",
            "scope": "single final 90deg post-processing product",
            "source_goal_or_job": "Goal 012 / 699822.kunanyi-ohpc",
            "walltime": "00:16:34",
            "cpu_time": "00:12:10",
            "memory": "1288828kb",
            "ncpus": "1",
            "views_or_products": "90deg historical projection",
            "estimate_basis": "accepted PBS completion email",
            "planning_use": "single-view reference only; historical accumulator superseded for future nonzero views",
        },
        {
            "evidence_id": "goal016_refined_45_90",
            "scope": "combined final 45deg and 90deg refined post-processing products",
            "source_goal_or_job": "Goal 016 / 700044.kunanyi-ohpc",
            "walltime": "00:22:01",
            "cpu_time": "00:17:40",
            "memory": "1362356kb",
            "ncpus": "1",
            "views_or_products": "45deg refined;90deg refined",
            "estimate_basis": "accepted PBS completion email and packaged remote stdout",
            "planning_use": "primary runtime anchor for future refined nonzero-view source-age products",
        },
        {
            "evidence_id": "estimated_per_new_source_age",
            "scope": "one new source age with 0deg, 45deg, and 90deg compact products",
            "source_goal_or_job": "Goal 018 estimate from Goals 011/012/016",
            "walltime": "00:35:00-01:00:00",
            "cpu_time": "00:25:00-00:45:00",
            "memory": "about 2gb observed; request should keep conservative headroom",
            "ncpus": "1",
            "views_or_products": "0deg;45deg refined;90deg refined",
            "estimate_basis": "Goal 016 did two nonzero refined views in 22 minutes; add 0deg and preflight overhead",
            "planning_use": "not a 48-hour or production-scale job",
        },
        {
            "evidence_id": "estimated_first_pass_two_new_ages",
            "scope": "outputs 46 and 49, each with 0/45/90 views",
            "source_goal_or_job": "Goal 018 recommendation",
            "walltime": "01:15:00-02:00:00 estimated; request modest bounded walltime in future packet",
            "cpu_time": "00:50:00-01:30:00 estimated",
            "memory": "request should follow Goal 016-style conservative headroom",
            "ncpus": "1",
            "views_or_products": "six new compact projection products",
            "estimate_basis": "linear scale from Goal 016 with extra preflight/package overhead",
            "planning_use": "bounded post-processing after maintenance; not authorized by Goal 018",
        },
    ]


def risk_and_caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "risk_id": "connected_envelope_xray_topology",
            "status": "active_caveat",
            "applies_to": "all source-age X-ray/cavity interpretation",
            "mitigation": "frame products as control-surface diagnostics, not publication-ready topology claims",
            "source_evidence": "Goal 017 consolidation note",
            "next_goal_implication": "keep topology refinement as a separate near-term option if sampling exposes sensitivity",
        },
        {
            "risk_id": "sparse_radio_observable_status",
            "status": "diagnostic_only",
            "applies_to": "radio/PRAiSE products",
            "mitigation": "do not include final radio observables in the first source-age execution goal",
            "source_evidence": "Goal 001/002/017 caveats",
            "next_goal_implication": "radio/raytracing readiness stays a separate method lane",
        },
        {
            "risk_id": "level3_gravity",
            "status": "blocked_missing_potential",
            "applies_to": "ambient energy accounting",
            "mitigation": "carry thermal/kinetic Level 3 as available and keep gravitational component blocked",
            "source_evidence": "docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_metadata.json",
            "next_goal_implication": "do not solve gravity inside source-age sampling",
        },
        {
            "risk_id": "cavity_energy_convention",
            "status": "active",
            "applies_to": "cavity energetics summaries",
            "mitigation": "carry pV, adopted 2.5pV, and 4pV if any energy summary is included",
            "source_evidence": "Goal 010 and Goal 017 notes",
            "next_goal_implication": "avoid 4pV-only language",
        },
        {
            "risk_id": "fullgrid_snapshot_availability",
            "status": "preflight_required",
            "applies_to": "outputs 46 and 49, plus any substitution",
            "mitigation": "future execution goal must verify file presence, timestep, shape, and vars before submission",
            "source_evidence": "local catalogue tail and current_status; no remote probing in Goal 018",
            "next_goal_implication": "wake before substituting any source age",
        },
        {
            "risk_id": "maintenance_window",
            "status": "execution_hold_until_after_outage",
            "applies_to": "Kunanyi staging/submission",
            "mitigation": "Goal 018 is local-only; future execution waits for explicit approval after maintenance",
            "source_evidence": "Goal 018 delegation",
            "next_goal_implication": "no remote work from this packet",
        },
        {
            "risk_id": "comparison_cases",
            "status": "out_of_scope",
            "applies_to": "C-LO/G-LO and broader production work",
            "mitigation": "keep first pass within C-HI only",
            "source_evidence": "Goal 017 next-step readiness",
            "next_goal_implication": "comparison-case preparation remains a later decision",
        },
    ]


def metadata() -> dict[str, Any]:
    return {
        "date": "2026-06-25",
        "goal": "018-c-hi-source-age-sampling-plan",
        "status": "complete_plan",
        "decision_label": "SOURCE_AGE_SAMPLING_PLAN_READY_FOR_POST_MAINTENANCE_AUTHORIZATION",
        "no_execution_authorized": True,
        "recommended_design": {
            "new_source_age_outputs": ["data.0046.flt.h5::Timestep_46", "data.0049.flt.h5::Timestep_49"],
            "reference_control": "reuse accepted data.0051.flt.h5 endpoint: 0deg Goal005 plus 45/90deg Goal016 refined",
            "views_per_new_source_age": ["0deg", "45deg", "90deg"],
            "nonzero_view_accumulator": REFINED_ACCUMULATOR,
        },
        "known_from_local_evidence": [
            "early 1-10 Myr segment diagnostics exist locally",
            "final-production outputs 46-51 are locally catalogued in integrity evidence",
            "final 50 Myr endpoint products are accepted and refined for 45/90deg",
        ],
        "unknown_until_future_authorized_preflight": [
            "live Kunanyi availability after maintenance",
            "immediate HDF5 readability and timestep presence for outputs 46 and 49",
            "whether any earlier 5/10 Myr final-production equivalents should replace the late-source-age pilot",
        ],
        "hard_boundaries_observed": [
            "no remote commands",
            "no staging or PBS submission",
            "no source-age execution",
            "no commits or pushes",
            "no accepted asset overwrites",
        ],
    }


def build_assets(output_dir: Path) -> None:
    candidates = candidate_snapshot_rows()
    write_rows(output_dir / "source_age_candidate_snapshots.csv", candidates, CANDIDATE_COLUMNS)
    write_rows(output_dir / "proposed_sampling_plan.csv", proposed_sampling_plan_rows(), SAMPLING_COLUMNS)
    write_rows(output_dir / "post_maintenance_run_contract.csv", post_maintenance_contract_rows(), CONTRACT_COLUMNS)
    write_rows(output_dir / "runtime_resource_estimate.csv", runtime_resource_estimate_rows(), RUNTIME_COLUMNS)
    write_rows(output_dir / "risk_and_caveat_register.csv", risk_and_caveat_rows(), RISK_COLUMNS)
    (output_dir / "source_age_sampling_plan_metadata.json").write_text(json.dumps(metadata(), indent=2) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_assets(args.output_dir)


if __name__ == "__main__":
    main()
