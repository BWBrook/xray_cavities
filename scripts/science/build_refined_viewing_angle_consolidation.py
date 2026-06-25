#!/usr/bin/env python3
"""Build Goal 017 refined viewing-angle consolidation assets."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_refined_viewing_angle_consolidation_2026-06-25"
GOAL005_ASSET = ASSET_ROOT / "c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
GOAL011_ASSET = ASSET_ROOT / "c_hi_final_45deg_viewing_angle_broadening_2026-06-23"
GOAL012_ASSET = ASSET_ROOT / "c_hi_final_90deg_viewing_angle_broadening_2026-06-23"
GOAL016_ASSET = ASSET_ROOT / "c_hi_refined_projection_viewing_rerun_2026-06-25"
GOAL009_ASSET = ASSET_ROOT / "c_hi_final_level3_remote_extraction_closeout_2026-06-18"

HISTORICAL_REFINED_COLUMNS = [
    "view",
    "historical_goal",
    "refined_goal",
    "historical_product_status",
    "future_evidence_status",
    "raw_empty_columns_historical",
    "raw_empty_columns_refined",
    "corrected_empty_columns_historical",
    "corrected_empty_columns_refined",
    "correction_ratio_empty_columns_historical",
    "correction_ratio_empty_columns_refined",
    "raw_xray_sum_relative_delta",
    "corrected_xray_sum_relative_delta",
    "raw_xray_max_relative_delta",
    "corrected_xray_max_relative_delta",
    "correction_ratio_positive_sum_relative_delta",
    "interpretation",
]
TRIO_CONTEXT_COLUMNS = [
    "view",
    "view_angle_deg",
    "product_status",
    "source_goal",
    "source_asset_path",
    "projected_accumulation",
    "raw_empty_columns",
    "corrected_empty_columns",
    "correction_ratio_empty_columns",
    "raw_xray_max",
    "corrected_xray_max",
    "raw_xray_sum",
    "corrected_xray_sum",
    "correction_ratio_positive_max",
    "correction_ratio_positive_sum",
    "corrected_xray_max_ratio_to_0deg",
    "corrected_xray_sum_ratio_to_0deg",
    "future_use",
]
PROVENANCE_COLUMNS = [
    "product_id",
    "role",
    "source_goal",
    "source_asset_path",
    "status",
    "note",
]
NEXT_STEP_COLUMNS = [
    "option",
    "readiness_label",
    "recommendation_rank",
    "why_now",
    "blockers_or_caveats",
    "compute_timing",
    "goal018_fit",
    "recommended_action",
]


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"{path}: no rows")
    return rows


def read_summary(path: Path) -> dict[str, dict[str, str]]:
    return {row["metric"]: row for row in read_rows(path)}


def read_json(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        return json.load(handle)


def by_view_layer(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["view"], row["layer"]): row for row in rows}


def by_view_metric(rows: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    return {(row["view"], row["metric"]): row for row in rows}


def metric_value(summary: dict[str, dict[str, str]], metric: str) -> float:
    return float(summary[metric]["value"])


def fmt(value: float) -> str:
    return f"{value:.16g}"


def ratio_or_one(value: float, baseline: float) -> str:
    return "nan" if baseline == 0.0 else fmt(value / baseline)


def historical_vs_refined_rows(
    empty_rows: list[dict[str, str]],
    scalar_rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    empty = by_view_layer(empty_rows)
    scalar = by_view_metric(scalar_rows)
    out: list[dict[str, Any]] = []
    for view, historical_goal in (("45deg", "Goal 011"), ("90deg", "Goal 012")):
        raw_empty = empty[(view, "raw_xray")]
        corrected_empty = empty[(view, "corrected_xray")]
        ratio_empty = empty[(view, "correction_ratio")]
        raw_sum = scalar[(view, "raw_xray_sum")]
        corrected_sum = scalar[(view, "corrected_xray_sum")]
        raw_max = scalar[(view, "raw_xray_max")]
        corrected_max = scalar[(view, "corrected_xray_max")]
        ratio_sum = scalar[(view, "correction_ratio_positive_sum")]
        out.append(
            {
                "view": view,
                "historical_goal": historical_goal,
                "refined_goal": "Goal 016",
                "historical_product_status": "preserved_historical_diagnostic",
                "future_evidence_status": "superseded_by_refined_projection_product",
                "raw_empty_columns_historical": raw_empty["accepted_empty_columns"],
                "raw_empty_columns_refined": raw_empty["refined_empty_columns"],
                "corrected_empty_columns_historical": corrected_empty["accepted_empty_columns"],
                "corrected_empty_columns_refined": corrected_empty["refined_empty_columns"],
                "correction_ratio_empty_columns_historical": ratio_empty["accepted_empty_columns"],
                "correction_ratio_empty_columns_refined": ratio_empty["refined_empty_columns"],
                "raw_xray_sum_relative_delta": raw_sum["relative_delta_fraction"],
                "corrected_xray_sum_relative_delta": corrected_sum["relative_delta_fraction"],
                "raw_xray_max_relative_delta": raw_max["relative_delta_fraction"],
                "corrected_xray_max_relative_delta": corrected_max["relative_delta_fraction"],
                "correction_ratio_positive_sum_relative_delta": ratio_sum["relative_delta_fraction"],
                "interpretation": (
                    "Refined projection removes historical empty X-ray columns while conserving raw/corrected "
                    "X-ray pixel sums to roundoff; use refined product for future viewing-angle evidence."
                ),
            }
        )
    return out


def refined_metric_by_view(metrics: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["view"]: row for row in metrics}


def trio_context_rows(
    *,
    goal005_summary: dict[str, dict[str, str]],
    refined_metrics: list[dict[str, str]],
) -> list[dict[str, Any]]:
    refined = refined_metric_by_view(refined_metrics)
    corrected_max_0 = metric_value(goal005_summary, "corrected_xray_max")
    corrected_sum_0 = metric_value(goal005_summary, "corrected_xray_sum")
    rows: list[dict[str, Any]] = [
        {
            "view": "0deg",
            "view_angle_deg": "0",
            "product_status": "accepted_unchanged_baseline",
            "source_goal": "Goal 005",
            "source_asset_path": "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid/xraise_grid_smoke_summary.csv",
            "projected_accumulation": "direct_y_axis_sum_accepted_baseline",
            "raw_empty_columns": "0",
            "corrected_empty_columns": "0",
            "correction_ratio_empty_columns": "0",
            "raw_xray_max": goal005_summary["raw_xray_max"]["value"],
            "corrected_xray_max": goal005_summary["corrected_xray_max"]["value"],
            "raw_xray_sum": goal005_summary["raw_xray_sum"]["value"],
            "corrected_xray_sum": goal005_summary["corrected_xray_sum"]["value"],
            "correction_ratio_positive_max": goal005_summary["correction_ratio_positive_max"]["value"],
            "correction_ratio_positive_sum": goal005_summary["correction_ratio_positive_sum"]["value"],
            "corrected_xray_max_ratio_to_0deg": "1",
            "corrected_xray_sum_ratio_to_0deg": "1",
            "future_use": "unchanged control baseline",
        }
    ]
    for view, source_asset in (
        ("45deg", "docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_metrics.csv"),
        ("90deg", "docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_metrics.csv"),
    ):
        row = refined[view]
        rows.append(
            {
                "view": view,
                "view_angle_deg": row["view_angle_deg"],
                "product_status": "refined_projection_product",
                "source_goal": "Goal 016",
                "source_asset_path": source_asset,
                "projected_accumulation": row["projected_accumulation"],
                "raw_empty_columns": "0",
                "corrected_empty_columns": "0",
                "correction_ratio_empty_columns": "0",
                "raw_xray_max": row["raw_max_mjy_sr"],
                "corrected_xray_max": row["corrected_max_mjy_sr"],
                "raw_xray_sum": row["raw_sum_mjy_sr_pixels"],
                "corrected_xray_sum": row["corrected_sum_mjy_sr_pixels"],
                "correction_ratio_positive_max": row["correction_ratio_max"],
                "correction_ratio_positive_sum": row["correction_ratio_sum"],
                "corrected_xray_max_ratio_to_0deg": ratio_or_one(float(row["corrected_max_mjy_sr"]), corrected_max_0),
                "corrected_xray_sum_ratio_to_0deg": ratio_or_one(
                    float(row["corrected_sum_mjy_sr_pixels"]), corrected_sum_0
                ),
                "future_use": "preferred future viewing-angle evidence",
            }
        )
    return rows


def provenance_rows() -> list[dict[str, str]]:
    return [
        {
            "product_id": "accepted_0deg_baseline",
            "role": "unchanged_control_view",
            "source_goal": "Goal 005",
            "source_asset_path": "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/",
            "status": "accepted_unchanged",
            "note": "Use as the 0-degree control baseline for refined trio context.",
        },
        {
            "product_id": "historical_45deg_projection",
            "role": "historical_diagnostic",
            "source_goal": "Goal 011",
            "source_asset_path": "docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/",
            "status": "preserved_historical_artifact",
            "note": "Superseded for future viewing-angle evidence by the Goal 016 refined 45-degree product.",
        },
        {
            "product_id": "historical_90deg_projection",
            "role": "historical_diagnostic",
            "source_goal": "Goal 012",
            "source_asset_path": "docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/",
            "status": "preserved_historical_artifact",
            "note": "Superseded for future viewing-angle evidence by the Goal 016 refined 90-degree product.",
        },
        {
            "product_id": "refined_45deg_projection",
            "role": "preferred_future_viewing_angle_evidence",
            "source_goal": "Goal 016",
            "source_asset_path": "docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/",
            "status": "accepted_refined_projection",
            "note": "Uses edge_overlap_uniform_cell_projection and removes 45-degree empty X-ray columns.",
        },
        {
            "product_id": "refined_90deg_projection",
            "role": "preferred_future_viewing_angle_evidence",
            "source_goal": "Goal 016",
            "source_asset_path": "docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/",
            "status": "accepted_refined_projection",
            "note": "Uses edge_overlap_uniform_cell_projection and fixes the 90-degree empty-column failure.",
        },
        {
            "product_id": "projection_method_refinement",
            "role": "method_basis",
            "source_goal": "Goal 015",
            "source_asset_path": "docs/science/c_hi_projection_bin_refinement_2026-06-24.md",
            "status": "accepted_method_refinement",
            "note": "Synthetic proof for the edge-overlap projected-bin accumulator.",
        },
        {
            "product_id": "striping_diagnostic",
            "role": "problem_diagnosis",
            "source_goal": "Goal 014",
            "source_asset_path": "docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md",
            "status": "accepted_diagnostic",
            "note": "Diagnosed historical 90-degree striping as projection/binning occupancy.",
        },
        {
            "product_id": "level3_gravity_gap",
            "role": "carried_caveat",
            "source_goal": "Goal 009/010",
            "source_asset_path": "docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/level3_evidence_summary.csv",
            "status": "blocked_missing_potential",
            "note": "Thermal/kinetic Level 3 is green; gravitational Level 3 remains blocked.",
        },
    ]


def next_step_readiness_rows() -> list[dict[str, str]]:
    return [
        {
            "option": "tightly_bounded_c_hi_source_age_sampling_after_maintenance",
            "readiness_label": "recommended_next_planning_goal",
            "recommendation_rank": "1",
            "why_now": (
                "Refined 45/90 projections fix the viewing-angle artifact and preserve X-ray sums; "
                "this unblocks planning for a narrow within-C-HI age axis."
            ),
            "blockers_or_caveats": (
                "Do not run before Kunanyi maintenance clears; keep projection-sensitivity, topology, radio, "
                "and Level 3 gravity caveats visible."
            ),
            "compute_timing": "prepare_plan_now_run_after_maintenance",
            "goal018_fit": "strong",
            "recommended_action": "write a local plan/packet for a small post-maintenance C-HI source-age sampling run",
        },
        {
            "option": "xray_cavity_topology_refinement",
            "readiness_label": "important_but_not_next_blocker",
            "recommendation_rank": "2",
            "why_now": "Connected-envelope and single-lobe topology caveats remain scientifically important.",
            "blockers_or_caveats": (
                "Would refine cavity interpretation but is not required before planning a small source-age probe."
            ),
            "compute_timing": "local_method_design_or_later_bounded_postprocessing",
            "goal018_fit": "medium",
            "recommended_action": "keep as a near-term method goal if source-age planning reveals topology sensitivity",
        },
        {
            "option": "radio_observable_raytracing_method_work",
            "readiness_label": "hold_for_method_lane",
            "recommendation_rank": "3",
            "why_now": "Sparse particle-binned radio remains diagnostic rather than a validated observable.",
            "blockers_or_caveats": "Would require method work beyond the refined X-ray projection consolidation surface.",
            "compute_timing": "local_design_before_any_remote_product",
            "goal018_fit": "low",
            "recommended_action": "defer until after the next C-HI sampling control surface is chosen",
        },
        {
            "option": "gravitational_level3_convention_work",
            "readiness_label": "blocked_missing_potential",
            "recommendation_rank": "4",
            "why_now": "Level 3 gravity remains a tracked gap from Goal 009/010.",
            "blockers_or_caveats": "Needs reviewed potential/profile convention before calculation or claims.",
            "compute_timing": "local_method_review_first",
            "goal018_fit": "low",
            "recommended_action": "do not fold into source-age sampling; keep as a separate convention goal",
        },
        {
            "option": "comparison_case_preparation_c_lo_g_lo",
            "readiness_label": "hold_until_c_hi_age_axis_or_method_review",
            "recommendation_rank": "5",
            "why_now": "Comparison cases are valuable but would broaden beyond the repaired C-HI control surface.",
            "blockers_or_caveats": "Do not start C-LO/G-LO before the C-HI source-age/topology decision is tighter.",
            "compute_timing": "not_before_maintenance_and_not_goal018",
            "goal018_fit": "low",
            "recommended_action": "defer comparison-case preparation",
        },
    ]


def build_metadata(
    historical_rows: list[dict[str, Any]],
    trio_rows: list[dict[str, Any]],
    next_rows: list[dict[str, str]],
) -> dict[str, Any]:
    refined_rows = {row["view"]: row for row in historical_rows}
    return {
        "status": "complete_consolidation",
        "decision_label": "REFINED_VIEWING_ANGLE_EVIDENCE_READY_FOR_NEXT_STEP_PLANNING",
        "supersession": {
            "45deg": "Goal 016 refined projection supersedes Goal 011 for future viewing-angle evidence",
            "90deg": "Goal 016 refined projection supersedes Goal 012 for future viewing-angle evidence",
            "0deg": "Goal 005 remains the unchanged accepted baseline",
        },
        "empty_column_repair": {
            "45deg": {
                "raw": {
                    "historical": int(refined_rows["45deg"]["raw_empty_columns_historical"]),
                    "refined": int(refined_rows["45deg"]["raw_empty_columns_refined"]),
                },
                "corrected": {
                    "historical": int(refined_rows["45deg"]["corrected_empty_columns_historical"]),
                    "refined": int(refined_rows["45deg"]["corrected_empty_columns_refined"]),
                },
            },
            "90deg": {
                "raw": {
                    "historical": int(refined_rows["90deg"]["raw_empty_columns_historical"]),
                    "refined": int(refined_rows["90deg"]["raw_empty_columns_refined"]),
                },
                "corrected": {
                    "historical": int(refined_rows["90deg"]["corrected_empty_columns_historical"]),
                    "refined": int(refined_rows["90deg"]["corrected_empty_columns_refined"]),
                },
            },
        },
        "trio_products": [row["product_status"] for row in trio_rows],
        "recommended_next_option": next_rows[0]["option"],
        "recommended_goal018_shape": "local planning packet for tightly bounded C-HI source-age sampling after maintenance",
        "caveats": [
            "not publication-ready observables",
            "connected-envelope/X-ray topology unresolved",
            "sparse radio remains diagnostic",
            "Level 3 gravity remains blocked_missing_potential",
            "pV/2.5pV/4pV convention remains active",
        ],
    }


def build_assets(output_dir: Path) -> dict[str, Any]:
    goal005_summary = read_summary(GOAL005_ASSET / "xraise_grid/xraise_grid_smoke_summary.csv")
    empty_rows = read_rows(GOAL016_ASSET / "empty_column_before_after.csv")
    scalar_rows = read_rows(GOAL016_ASSET / "refined_vs_accepted_xray_summary.csv")
    refined_metrics = read_rows(GOAL016_ASSET / "refined_projection_metrics.csv")

    historical_rows = historical_vs_refined_rows(empty_rows, scalar_rows)
    trio_rows = trio_context_rows(goal005_summary=goal005_summary, refined_metrics=refined_metrics)
    provenance = provenance_rows()
    next_rows = next_step_readiness_rows()
    metadata = build_metadata(historical_rows, trio_rows, next_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_rows(output_dir / "historical_vs_refined_viewing_products.csv", historical_rows, HISTORICAL_REFINED_COLUMNS)
    write_rows(output_dir / "refined_trio_context.csv", trio_rows, TRIO_CONTEXT_COLUMNS)
    write_rows(output_dir / "product_provenance.csv", provenance, PROVENANCE_COLUMNS)
    write_rows(output_dir / "next_step_readiness.csv", next_rows, NEXT_STEP_COLUMNS)
    (output_dir / "refined_viewing_angle_consolidation_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metadata = build_assets(args.output_dir)
    print(json.dumps(metadata, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
