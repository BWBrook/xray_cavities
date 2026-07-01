#!/usr/bin/env python3
"""Build Goal 027 conditional endpoint topology application package assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GOAL005 = ROOT / "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
GOAL007 = ROOT / "docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16"
GOAL025 = ROOT / "docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01"
GOAL026 = ROOT / "docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01"
DEFAULT_OUTPUT = (
    ROOT / "docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01"
)
SELECTED_PERCENTILE = "1"
DECISION_LABEL = "CONDITIONAL_CONNECTED_CORE_APPLICATION_NO_FINAL_FREEZE"


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def row_for_percentile(rows: list[dict[str, str]], percentile: str) -> dict[str, str]:
    matches = [row for row in rows if row.get("percentile") == percentile]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one row for percentile {percentile}, found {len(matches)}")
    return matches[0]


def connected_thresholds(rows: list[dict[str, str]], *, selected_percentile: str) -> list[str]:
    return [
        row["percentile"]
        for row in rows
        if row["percentile"] != selected_percentile
        and row["observed_topology_class"] == "connected_envelope_single_system"
        and row["gate_status"] == "pass"
    ]


def ambiguity_thresholds(rows: list[dict[str, str]]) -> list[str]:
    return [
        row["percentile"]
        for row in rows
        if row["observed_topology_class"] == "ambiguous_needs_review"
    ]


def threshold_role(row: dict[str, str], *, selected_percentile: str) -> str:
    if row["percentile"] == selected_percentile:
        return "selected_representative_conditional_application"
    if row["observed_topology_class"] == "connected_envelope_single_system":
        return "supporting_narrow_threshold_robustness"
    return "ambiguity_bound_threshold"


def conditional_application_summary_row(
    sensitivity_rows: list[dict[str, str]],
    *,
    selected_percentile: str,
    figure_path: str,
) -> dict[str, Any]:
    selected = row_for_percentile(sensitivity_rows, selected_percentile)
    if selected["observed_topology_class"] != "connected_envelope_single_system":
        raise ValueError("selected percentile does not preserve connected-envelope topology")
    if selected["gate_status"] != "pass":
        raise ValueError("selected percentile does not pass the seeded topology gate")
    support = connected_thresholds(sensitivity_rows, selected_percentile=selected_percentile)
    ambiguity = ambiguity_thresholds(sensitivity_rows)
    return {
        "application_id": "goal027_conditional_endpoint_topology_percentile_1",
        "decision_label": DECISION_LABEL,
        "selection_status": "selected_conditional_connected_core",
        "selected_threshold_percentile": selected["percentile"],
        "selected_residual_threshold": selected["residual_threshold"],
        "selection_rationale": (
            "1 percent is the Goal 025 representative residual-core threshold and sits inside the "
            "Goal 026 narrow-threshold connected regime; 0.5 and 2 percent support robustness, "
            "while 3 percent and broader thresholds mark ambiguity bounds"
        ),
        "observed_topology_class": selected["observed_topology_class"],
        "gate_status": selected["gate_status"],
        "mask_pixels": selected["mask_pixels"],
        "mask_fraction": selected["mask_fraction"],
        "significant_component_count_all": selected["significant_component_count_all"],
        "seeded_component_count": selected["seeded_component_count"],
        "unlabelled_component_count": selected["unlabelled_component_count"],
        "component_side_class_counts": selected["component_side_class_counts"],
        "negative_seed_overlap_pixels": selected["negative_seed_overlap_pixels"],
        "positive_seed_overlap_pixels": selected["positive_seed_overlap_pixels"],
        "negative_seed_overlap_fraction": selected["negative_seed_overlap_fraction"],
        "positive_seed_overlap_fraction": selected["positive_seed_overlap_fraction"],
        "supporting_narrow_thresholds": ";".join(support),
        "ambiguity_bound_thresholds": ";".join(ambiguity),
        "final_observational_topology_frozen": "false",
        "accepted_product_relationship": "sits_beside_does_not_replace_goal005_goal007",
        "figure_reference": figure_path,
    }


def selected_threshold_component_rows(
    component_rows: list[dict[str, str]],
    *,
    selected_percentile: str,
) -> list[dict[str, Any]]:
    rows = [row for row in component_rows if row["percentile"] == selected_percentile]
    if not rows:
        raise ValueError(f"no component rows for selected percentile {selected_percentile}")
    output: list[dict[str, Any]] = []
    for row in rows:
        if row["side_class"] == "spans_negative_and_positive":
            role = "selected_connected_seeded_component"
        elif row["side_class"] == "unlabelled":
            role = "unlabelled_residual_island_caveat"
        else:
            role = "side_specific_component_not_expected_for_selected_threshold"
        output.append(
            {
                "application_id": "goal027_conditional_endpoint_topology_percentile_1",
                "application_role": role,
                **row,
            }
        )
    return output


def threshold_sensitivity_carried_forward_rows(
    sensitivity_rows: list[dict[str, str]],
    *,
    selected_percentile: str,
) -> list[dict[str, Any]]:
    return [
        {
            "application_role": threshold_role(row, selected_percentile=selected_percentile),
            "carried_forward_reason": (
                "selected representative threshold"
                if row["percentile"] == selected_percentile
                else (
                    "supports narrow-threshold connected-core robustness"
                    if row["observed_topology_class"] == "connected_envelope_single_system"
                    else "bounds interpretation by showing broader-mask ambiguity"
                )
            ),
            **row,
        }
        for row in sensitivity_rows
    ]


def accepted_product_relationship_rows() -> list[dict[str, str]]:
    rows = [
        {
            "asset_or_product": "Goal005 final endpoint X-ray/cavity alignment",
            "source_goal": "005",
            "path": display_path(ROOT / "docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md"),
            "relationship": "accepted endpoint provenance; not overwritten or replaced",
            "role_in_goal027": "source accepted corrected X-ray, tracer proxy, lobe volumes, pV/4pV convention",
            "replacement_or_overwrite": "false",
        },
        {
            "asset_or_product": "Goal005 tracer-defined cavity ellipse boundary",
            "source_goal": "005",
            "path": display_path(GOAL005 / "cavity_stub/cavity_ellipse_boundary_0deg.tsv"),
            "relationship": "remains accepted tracer-proxy overlay; not replaced by conditional residual mask",
            "role_in_goal027": "provenance comparator only, not an X-ray-fitted boundary",
            "replacement_or_overwrite": "false",
        },
        {
            "asset_or_product": "Goal007 observational product readiness",
            "source_goal": "007",
            "path": display_path(ROOT / "docs/science/c_hi_final_observational_product_readiness_2026-06-16.md"),
            "relationship": "topology-context provenance; not overwritten or replaced",
            "role_in_goal027": "records connected-envelope versus two-tracer-lobe caveat and residual-display method",
            "replacement_or_overwrite": "false",
        },
        {
            "asset_or_product": "Goal025 conditional application design",
            "source_goal": "025",
            "path": display_path(GOAL025 / "topology_application_result.csv"),
            "relationship": "protocol provenance carried forward",
            "role_in_goal027": "defines the 1 percent selected residual-core application",
            "replacement_or_overwrite": "false",
        },
        {
            "asset_or_product": "Goal026 residual threshold sensitivity",
            "source_goal": "026",
            "path": display_path(GOAL026 / "residual_threshold_sensitivity.csv"),
            "relationship": "first-class evidence carried beside selected application",
            "role_in_goal027": "bounds conditional interpretation with narrow connected and broader ambiguous thresholds",
            "replacement_or_overwrite": "false",
        },
        {
            "asset_or_product": "Goal026 reviewer-facing sensitivity figure",
            "source_goal": "026",
            "path": display_path(GOAL026 / "residual_threshold_sensitivity.png"),
            "relationship": "referenced directly rather than duplicated",
            "role_in_goal027": "compact figure pointer/provenance row for the conditional application package",
            "replacement_or_overwrite": "false",
        },
    ]
    for row in rows:
        path = ROOT / row["path"]
        row["sha256"] = sha256(path) if path.exists() else ""
    return rows


def caveat_rows() -> list[dict[str, str]]:
    return [
        {
            "caveat": "final_observational_topology_not_frozen",
            "status": "active",
            "meaning": "Goal027 preserves a conditional connected-core result, not a final cavity-topology method",
            "consequence": "do not use as publication-ready cavity topology",
        },
        {
            "caveat": "threshold_sensitivity",
            "status": "active",
            "meaning": "0.5/1/2 percent masks are connected; 3 percent and broader masks are ambiguous",
            "consequence": "carry sensitivity rows beside the selected application",
        },
        {
            "caveat": "tracer_proxy_seeds_not_xray_fit",
            "status": "active",
            "meaning": "side labels come from tracer threshold and z sign, not X-ray-fitted cavity boundaries",
            "consequence": "do not claim tracer seeds are observational X-ray cavities",
        },
        {
            "caveat": "unlabelled_residual_islands",
            "status": "active",
            "meaning": "unlabelled residual components are reported explicitly but ignored for seeded topology class",
            "consequence": "reviewers can see what the seeded classifier excludes",
        },
        {
            "caveat": "accepted_products_no_overwrite",
            "status": "active",
            "meaning": "Goal005/007 accepted endpoint products remain unchanged",
            "consequence": "Goal027 sits beside accepted assets as a review/application artifact",
        },
        {
            "caveat": "sparse_radio_diagnostic_only",
            "status": "active",
            "meaning": "sparse radio products remain diagnostics, not validated radio observables",
            "consequence": "do not use this topology package to imply radio-observable readiness",
        },
        {
            "caveat": "level3_gravity_blocked_missing_potential",
            "status": "active",
            "meaning": "gravitational Level 3 remains blocked without a reviewed potential/profile convention",
            "consequence": "do not treat energy accounting as fully closed",
        },
        {
            "caveat": "energy_convention",
            "status": "active",
            "meaning": "report pV, adopted non-relativistic 2.5pV, and 4pV where energy context is needed",
            "consequence": "preserve Stas-agent convention in future summaries",
        },
    ]


def next_step_rows() -> list[dict[str, str]]:
    return [
        {
            "rank": "1",
            "next_goal_shape": "conditional_topology_application_acceptance_review",
            "recommendation_label": "accept_as_conditional_control_surface_not_final",
            "why": (
                "Goal027 packages the selected connected residual core and threshold sensitivity durably; "
                "the next decision is whether X-ray Cavities accepts it as the conditional endpoint topology control surface"
            ),
            "minimum_scope": "docs/evidence review only; no rerun or accepted-product replacement",
            "do_not_do": "do not claim final observational topology or publication readiness",
        },
        {
            "rank": "2",
            "next_goal_shape": "refine_residual_mask_protocol",
            "recommendation_label": "fallback_if_conditional_threshold_not_accepted",
            "why": "broader masks are ambiguous, so the protocol should be refined if the conditional 1 percent threshold is not acceptable",
            "minimum_scope": "local residual/morphology protocol design",
            "do_not_do": "do not broaden products or rerun HDF5/XRAiSE by default",
        },
        {
            "rank": "3",
            "next_goal_shape": "hold_at_tracer_proxy_status",
            "recommendation_label": "fallback_if_no_conditional_application",
            "why": "accepted tracer ellipsoids remain valid prove-out/provenance proxies",
            "minimum_scope": "status and caveat preservation",
            "do_not_do": "do not call tracer ellipses X-ray-fitted cavities",
        },
    ]


def build_assets(output_dir: Path) -> None:
    sensitivity_rows = read_rows(GOAL026 / "residual_threshold_sensitivity.csv")
    component_rows = read_rows(GOAL026 / "residual_component_sensitivity.csv")
    figure_path = display_path(GOAL026 / "residual_threshold_sensitivity.png")

    summary_rows = [
        conditional_application_summary_row(
            sensitivity_rows,
            selected_percentile=SELECTED_PERCENTILE,
            figure_path=figure_path,
        )
    ]
    selected_component_rows = selected_threshold_component_rows(
        component_rows,
        selected_percentile=SELECTED_PERCENTILE,
    )
    carried_rows = threshold_sensitivity_carried_forward_rows(
        sensitivity_rows,
        selected_percentile=SELECTED_PERCENTILE,
    )
    relationship_rows = accepted_product_relationship_rows()
    caveats = caveat_rows()
    recommendations = next_step_rows()

    write_rows(
        output_dir / "conditional_topology_application_summary.csv",
        summary_rows,
        [
            "application_id",
            "decision_label",
            "selection_status",
            "selected_threshold_percentile",
            "selected_residual_threshold",
            "selection_rationale",
            "observed_topology_class",
            "gate_status",
            "mask_pixels",
            "mask_fraction",
            "significant_component_count_all",
            "seeded_component_count",
            "unlabelled_component_count",
            "component_side_class_counts",
            "negative_seed_overlap_pixels",
            "positive_seed_overlap_pixels",
            "negative_seed_overlap_fraction",
            "positive_seed_overlap_fraction",
            "supporting_narrow_thresholds",
            "ambiguity_bound_thresholds",
            "final_observational_topology_frozen",
            "accepted_product_relationship",
            "figure_reference",
        ],
    )
    write_rows(
        output_dir / "selected_threshold_component_summary.csv",
        selected_component_rows,
        [
            "application_id",
            "application_role",
            "percentile",
            "residual_threshold",
            "component_index",
            "pixel_count",
            "component_fraction_of_mask",
            "component_fraction_of_total",
            "negative_seed_overlap_pixels",
            "positive_seed_overlap_pixels",
            "unlabelled_overlap_pixels",
            "side_class",
            "used_for_seeded_topology_classification",
        ],
    )
    write_rows(
        output_dir / "threshold_sensitivity_carried_forward.csv",
        carried_rows,
        [
            "application_role",
            "carried_forward_reason",
            "percentile",
            "residual_threshold",
            "mask_pixels",
            "mask_fraction",
            "significant_component_count_all",
            "seeded_component_count",
            "unlabelled_component_count",
            "component_side_class_counts",
            "negative_seed_overlap_pixels",
            "positive_seed_overlap_pixels",
            "negative_seed_overlap_fraction",
            "positive_seed_overlap_fraction",
            "spanning_component_exists",
            "side_specific_components_exist",
            "observed_topology_class",
            "gate_status",
            "recommendation_consequence",
        ],
    )
    write_rows(
        output_dir / "accepted_product_relationship.csv",
        relationship_rows,
        [
            "asset_or_product",
            "source_goal",
            "path",
            "relationship",
            "role_in_goal027",
            "replacement_or_overwrite",
            "sha256",
        ],
    )
    write_rows(
        output_dir / "caveat_register.csv",
        caveats,
        ["caveat", "status", "meaning", "consequence"],
    )
    write_rows(
        output_dir / "next_step_recommendation.csv",
        recommendations,
        ["rank", "next_goal_shape", "recommendation_label", "why", "minimum_scope", "do_not_do"],
    )

    selected = summary_rows[0]
    metadata = {
        "date": "2026-07-01",
        "goal": "027-c-hi-conditional-endpoint-topology-application",
        "status": "complete_conditional_endpoint_topology_application_package",
        "decision_label": DECISION_LABEL,
        "selected_threshold_percentile": selected["selected_threshold_percentile"],
        "selected_residual_threshold": selected["selected_residual_threshold"],
        "selected_application_status": selected["selection_status"],
        "observed_topology_class": selected["observed_topology_class"],
        "final_observational_topology_frozen": False,
        "accepted_product_relationship": selected["accepted_product_relationship"],
        "figure_reference": figure_path,
        "headline_result": (
            "The 1 percent residual-core mask is selected as the representative conditional "
            "connected-core endpoint application. Goal026 threshold sensitivity remains first-class "
            "evidence: 0.5 and 2 percent support the narrow connected regime, while 3 percent and "
            "broader thresholds are ambiguity bounds."
        ),
        "boundary_confirmation": {
            "remote_commands": False,
            "open_ondemand_or_ssh": False,
            "pbs_jobs": False,
            "hdf5_xraise_rerun": False,
            "cavity_regeneration": False,
            "endpoint_rerun": False,
            "source_age_substitution": False,
            "agent_comms_edits": False,
            "commits_or_pushes": False,
            "accepted_assets_overwritten": False,
        },
        "active_caveats": [row["caveat"] for row in caveats],
        "asset_files": [
            "conditional_topology_application_summary.csv",
            "selected_threshold_component_summary.csv",
            "threshold_sensitivity_carried_forward.csv",
            "accepted_product_relationship.csv",
            "caveat_register.csv",
            "next_step_recommendation.csv",
            "conditional_endpoint_topology_application_metadata.json",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "conditional_endpoint_topology_application_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_assets(args.output_dir)
    print(f"wrote {display_path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
