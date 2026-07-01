#!/usr/bin/env python3
"""Build Goal 025 existing-asset topology application design assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

import hybrid_xray_cavity_topology as topology


ROOT = Path(__file__).resolve().parents[2]
GOAL005 = ROOT / "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
GOAL007 = ROOT / "docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16"
DEFAULT_OUTPUT = (
    ROOT
    / "docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01"
)


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_vector(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    if values.ndim != 1 or not np.all(np.isfinite(values)):
        raise ValueError(f"{path}: expected finite 1D vector")
    return np.asarray(values, dtype=float)


def read_matrix(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2 or not np.all(np.isfinite(values)):
        raise ValueError(f"{path}: expected finite 2D matrix")
    return np.asarray(values, dtype=float)


def component_summary_rows(
    mask: np.ndarray,
    side_labels: np.ndarray,
    *,
    min_component_pixels: int,
    connectivity: int,
    max_rows: int = 20,
) -> list[dict[str, Any]]:
    components = topology.connected_components(mask, connectivity=connectivity)
    rows: list[dict[str, Any]] = []
    for index, component in enumerate(components, start=1):
        pixel_count = int(np.count_nonzero(component))
        if pixel_count < min_component_pixels:
            continue
        negative = int(np.count_nonzero(component & (side_labels == -1)))
        positive = int(np.count_nonzero(component & (side_labels == 1)))
        if negative == 0 and positive == 0:
            side_class = "unlabelled"
        elif negative > 0 and positive > 0:
            side_class = "spans_negative_and_positive"
        elif negative > 0:
            side_class = "negative_z"
        else:
            side_class = "positive_z"
        rows.append(
            {
                "component_index": index,
                "pixel_count": pixel_count,
                "negative_seed_overlap_pixels": negative,
                "positive_seed_overlap_pixels": positive,
                "side_class": side_class,
                "used_for_seeded_topology_classification": str(side_class != "unlabelled").lower(),
            }
        )
    rows.sort(key=lambda row: int(row["pixel_count"]), reverse=True)
    return rows[:max_rows]


def build_assets(output_dir: Path) -> None:
    xray_path = GOAL005 / "xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv"
    tracer_path = GOAL005 / "xraise_grid/tracer_max_los.tsv"
    x_path = GOAL005 / "xraise_grid/x_kpc.tsv"
    z_path = GOAL005 / "xraise_grid/z_kpc.tsv"
    ellipse_path = GOAL005 / "cavity_stub/cavity_ellipse_boundary_0deg.tsv"
    lobe_path = GOAL005 / "final_xray_cavity_alignment_lobes.csv"
    metadata_path = GOAL005 / "final_xray_cavity_alignment_metadata.json"
    topology_ready_path = GOAL007 / "xray_topology_readiness.csv"
    goal007_metadata_path = GOAL007 / "observational_product_readiness_metadata.json"

    xray = read_matrix(xray_path)
    tracer = read_matrix(tracer_path)
    x_axis = read_vector(x_path)
    z_axis = read_vector(z_path)
    with goal007_metadata_path.open() as handle:
        goal007_metadata = json.load(handle)
    tracer_threshold = float(goal007_metadata["tracer_threshold"])
    boxcar_pixels = int(goal007_metadata["contrast_method"]["boxcar_pixels"])

    same_shape = xray.shape == tracer.shape
    axis_compatible = z_axis.shape[0] == xray.shape[0] and x_axis.shape[0] == xray.shape[1]
    side_labels = topology.derive_tracer_side_seed_labels(
        tracer,
        z_axis,
        tracer_threshold=tracer_threshold,
    )
    residual = topology.boxcar_log_residual(xray, boxcar_pixels=boxcar_pixels)

    selected_percentile = 1.0
    min_component_pixels = 50
    connectivity = 4
    mask, selected_threshold = topology.low_residual_percentile_mask(
        residual,
        percentile=selected_percentile,
    )
    result = topology.classify_hybrid_topology_from_mask(
        mask,
        side_labels,
        parameters=topology.TopologyParameters(
            min_component_pixels=min_component_pixels,
            bridge_connectivity=connectivity,
        ),
        case_id="goal005_goal007_existing_asset_residual_core",
        ignore_unlabelled_components=True,
    )

    sensitivity_rows: list[dict[str, Any]] = []
    for percentile in (1.0, 2.0, 5.0, 10.0, 20.0):
        test_mask, threshold = topology.low_residual_percentile_mask(residual, percentile=percentile)
        test_result = topology.classify_hybrid_topology_from_mask(
            test_mask,
            side_labels,
            parameters=topology.TopologyParameters(
                min_component_pixels=min_component_pixels,
                bridge_connectivity=connectivity,
            ),
            case_id=f"residual_percentile_{percentile:g}",
            ignore_unlabelled_components=True,
        )
        sensitivity_rows.append(
            {
                "candidate": f"residual_percentile_{percentile:g}",
                "percentile": f"{percentile:g}",
                "threshold": f"{threshold:.16g}",
                "mask_pixels": int(np.count_nonzero(test_mask)),
                "observed_topology_class": test_result.topology_class,
                "gate_status": test_result.gate_status,
                "significant_seeded_component_count": test_result.significant_component_count,
                "component_side_classes": ";".join(test_result.component_side_classes),
            }
        )

    input_rows = [
        {
            "asset": "corrected_xray_map",
            "path": display_path(xray_path),
            "available": str(xray_path.exists()).lower(),
            "shape_or_count": f"{xray.shape[0]}x{xray.shape[1]}",
            "compatibility": "compatible" if same_shape and axis_compatible else "blocked",
            "role": "source corrected 1 keV X-ray surface-brightness array",
            "sha256": sha256(xray_path),
        },
        {
            "asset": "tracer_max_los",
            "path": display_path(tracer_path),
            "available": str(tracer_path.exists()).lower(),
            "shape_or_count": f"{tracer.shape[0]}x{tracer.shape[1]}",
            "compatibility": "compatible" if same_shape else "blocked",
            "role": "source tracer-proxy seed array",
            "sha256": sha256(tracer_path),
        },
        {
            "asset": "x_axis_kpc",
            "path": display_path(x_path),
            "available": str(x_path.exists()).lower(),
            "shape_or_count": str(x_axis.shape[0]),
            "compatibility": "compatible" if x_axis.shape[0] == xray.shape[1] else "blocked",
            "role": "horizontal map coordinate axis",
            "sha256": sha256(x_path),
        },
        {
            "asset": "z_axis_kpc",
            "path": display_path(z_path),
            "available": str(z_path.exists()).lower(),
            "shape_or_count": str(z_axis.shape[0]),
            "compatibility": "compatible" if z_axis.shape[0] == xray.shape[0] else "blocked",
            "role": "vertical coordinate and side-sign axis",
            "sha256": sha256(z_path),
        },
        {
            "asset": "cavity_ellipse_boundary",
            "path": display_path(ellipse_path),
            "available": str(ellipse_path.exists()).lower(),
            "shape_or_count": "tabular_boundary",
            "compatibility": "provenance_only",
            "role": "accepted tracer-defined overlay, not selected as X-ray topology mask",
            "sha256": sha256(ellipse_path),
        },
        {
            "asset": "goal005_lobe_scalars",
            "path": display_path(lobe_path),
            "available": str(lobe_path.exists()).lower(),
            "shape_or_count": "3 rows",
            "compatibility": "provenance_only",
            "role": "energy and side-volume convention preservation",
            "sha256": sha256(lobe_path),
        },
        {
            "asset": "goal005_metadata",
            "path": display_path(metadata_path),
            "available": str(metadata_path.exists()).lower(),
            "shape_or_count": "json",
            "compatibility": "compatible",
            "role": "tracer threshold and caveat provenance",
            "sha256": sha256(metadata_path),
        },
        {
            "asset": "goal007_topology_readiness",
            "path": display_path(topology_ready_path),
            "available": str(topology_ready_path.exists()).lower(),
            "shape_or_count": "4 rows",
            "compatibility": "context_only",
            "role": "records unresolved connected-envelope versus two-tracer-lobe context",
            "sha256": sha256(topology_ready_path),
        },
    ]

    side_rows = [
        {
            "protocol_option": "tracer_threshold_z_sign_seed",
            "status": "selected",
            "parameters": f"tracer_max_los >= {tracer_threshold:g}; negative_z if z_kpc < 0; positive_z if z_kpc > 0",
            "negative_seed_pixels": int(np.count_nonzero(side_labels == -1)),
            "positive_seed_pixels": int(np.count_nonzero(side_labels == 1)),
            "unlabelled_pixels": int(np.count_nonzero(side_labels == 0)),
            "reason": "deterministic from local tracer max LOS and z axis; preserves tracer-proxy side provenance",
            "limitation": "side labels remain tracer proxies and are not X-ray-fitted cavity boundaries",
        },
        {
            "protocol_option": "cavity_ellipse_boundary_seed",
            "status": "not_selected",
            "parameters": "accepted Goal005 ellipse overlay",
            "negative_seed_pixels": "",
            "positive_seed_pixels": "",
            "unlabelled_pixels": "",
            "reason": "ellipse is useful provenance but is already the tracer-defined proxy being tested",
            "limitation": "would circularly reuse the proxy overlay as the X-ray topology seed",
        },
    ]

    xray_rows = [
        {
            "protocol_option": "goal007_boxcar_unsharp_low_residual_core",
            "status": "selected_conditional",
            "parameters": (
                f"log10(corrected_xray) - uniform_filter(log10(corrected_xray), {boxcar_pixels}px); "
                f"mask residual <= percentile {selected_percentile:g}; min_component_pixels={min_component_pixels}; "
                f"connectivity={connectivity}; ignore_unlabelled_components=true"
            ),
            "mask_pixels": int(np.count_nonzero(mask)),
            "threshold": f"{selected_threshold:.16g}",
            "observed_topology_class": result.topology_class,
            "gate_status": result.gate_status,
            "reason": "deterministic from existing corrected X-ray map and Goal007 residual display method",
            "limitation": "threshold choice is a local application parameter, not a reviewed production X-ray cavity mask default",
        }
    ]
    xray_rows.extend(
        {
            "protocol_option": row["candidate"],
            "status": "sensitivity_check",
            "parameters": (
                f"same residual method; percentile={row['percentile']}; "
                f"min_component_pixels={min_component_pixels}; connectivity={connectivity}"
            ),
            "mask_pixels": row["mask_pixels"],
            "threshold": row["threshold"],
            "observed_topology_class": row["observed_topology_class"],
            "gate_status": row["gate_status"],
            "reason": "threshold sensitivity audit",
            "limitation": "not selected as the primary conditional application row",
        }
        for row in sensitivity_rows
        if row["candidate"] != "residual_percentile_1"
    )

    readiness_rows = [
        {
            "decision": "conditional_local_application_made_not_final_topology",
            "supported_now": "conditional",
            "side_seed_status": "selected",
            "xray_mask_status": "selected_conditional",
            "endpoint_application_made": "true",
            "final_observational_topology_claim": "false",
            "reason": (
                "existing compact arrays support a deterministic residual-core application, "
                "but threshold sensitivity and absent reviewed mask default prevent final topology freeze"
            ),
            "required_before_final_or_rerun": (
                "review local residual threshold/morphology sensitivity and decide whether the "
                "conditional connected-core result is adequate for a bounded no-overwrite application package"
            ),
        }
    ]

    application_rows = [
        {
            "application_id": "goal005_goal007_residual_core_percentile_1",
            "application_type": "selected_conditional",
            "side_seed_protocol": "tracer_threshold_z_sign_seed",
            "xray_mask_protocol": "goal007_boxcar_unsharp_low_residual_core",
            "observed_topology_class": result.topology_class,
            "gate_status": result.gate_status,
            "reason": result.reason,
            "significant_seeded_component_count": result.significant_component_count,
            "component_side_classes": ";".join(result.component_side_classes),
            "cavity_candidate_pixels": result.cavity_candidate_pixels,
            "negative_seed_pixels": result.side_label_summary["negative_z"]["seed_pixels"],
            "positive_seed_pixels": result.side_label_summary["positive_z"]["seed_pixels"],
            "final_observational_topology_claim": "false",
        }
    ]
    application_rows.extend(
        {
            "application_id": row["candidate"],
            "application_type": "sensitivity_check",
            "side_seed_protocol": "tracer_threshold_z_sign_seed",
            "xray_mask_protocol": "goal007_boxcar_unsharp_low_residual_core",
            "observed_topology_class": row["observed_topology_class"],
            "gate_status": row["gate_status"],
            "reason": "threshold sensitivity audit",
            "significant_seeded_component_count": row["significant_seeded_component_count"],
            "component_side_classes": row["component_side_classes"],
            "cavity_candidate_pixels": row["mask_pixels"],
            "negative_seed_pixels": int(np.count_nonzero(side_labels == -1)),
            "positive_seed_pixels": int(np.count_nonzero(side_labels == 1)),
            "final_observational_topology_claim": "false",
        }
        for row in sensitivity_rows
        if row["candidate"] != "residual_percentile_1"
    )

    component_rows = component_summary_rows(
        mask,
        side_labels,
        min_component_pixels=min_component_pixels,
        connectivity=connectivity,
    )
    next_rows = [
        {
            "rank": "1",
            "next_goal_shape": "local_residual_threshold_sensitivity_review_package",
            "recommendation_label": "review_conditional_connected_core_before_rerun",
            "why": (
                "the 1 percent residual-core application gives a connected-envelope result, but broader "
                "thresholds become mixed/ambiguous; this needs a compact local review before any rerun"
            ),
            "minimum_scope": (
                "no remote work; create reviewer-facing residual/mask sensitivity figure and table from "
                "existing Goal005/007 arrays"
            ),
            "do_not_do": "do not claim final endpoint topology or run HDF5/XRAiSE",
        },
        {
            "rank": "2",
            "next_goal_shape": "bounded_no_overwrite_endpoint_topology_application",
            "recommendation_label": "future_only_after_local_threshold_review",
            "why": "a bounded endpoint application package may be justified after the local threshold/mask choice is accepted",
            "minimum_scope": "explicit no-overwrite existing-output package with accepted threshold/mask protocol",
            "do_not_do": "do not stage, submit, or overwrite accepted Goal005/007 products from this design pass",
        },
        {
            "rank": "3",
            "next_goal_shape": "hold_at_tracer_proxy",
            "recommendation_label": "fallback_if_threshold_sensitivity_not_accepted",
            "why": "the existing tracer ellipsoids remain valid provenance/prove-out proxies",
            "minimum_scope": "preserve current caveats and avoid topology freeze",
            "do_not_do": "do not call tracer ellipses X-ray-fitted cavities",
        },
    ]

    write_rows(
        output_dir / "input_asset_contract.csv",
        input_rows,
        ["asset", "path", "available", "shape_or_count", "compatibility", "role", "sha256"],
    )
    write_rows(
        output_dir / "side_seed_protocol.csv",
        side_rows,
        [
            "protocol_option",
            "status",
            "parameters",
            "negative_seed_pixels",
            "positive_seed_pixels",
            "unlabelled_pixels",
            "reason",
            "limitation",
        ],
    )
    write_rows(
        output_dir / "xray_mask_protocol.csv",
        xray_rows,
        [
            "protocol_option",
            "status",
            "parameters",
            "mask_pixels",
            "threshold",
            "observed_topology_class",
            "gate_status",
            "reason",
            "limitation",
        ],
    )
    write_rows(
        output_dir / "application_readiness_decision.csv",
        readiness_rows,
        [
            "decision",
            "supported_now",
            "side_seed_status",
            "xray_mask_status",
            "endpoint_application_made",
            "final_observational_topology_claim",
            "reason",
            "required_before_final_or_rerun",
        ],
    )
    write_rows(
        output_dir / "topology_application_result.csv",
        application_rows,
        [
            "application_id",
            "application_type",
            "side_seed_protocol",
            "xray_mask_protocol",
            "observed_topology_class",
            "gate_status",
            "reason",
            "significant_seeded_component_count",
            "component_side_classes",
            "cavity_candidate_pixels",
            "negative_seed_pixels",
            "positive_seed_pixels",
            "final_observational_topology_claim",
        ],
    )
    write_rows(
        output_dir / "topology_component_summary.csv",
        component_rows,
        [
            "component_index",
            "pixel_count",
            "negative_seed_overlap_pixels",
            "positive_seed_overlap_pixels",
            "side_class",
            "used_for_seeded_topology_classification",
        ],
    )
    write_rows(
        output_dir / "next_step_recommendation.csv",
        next_rows,
        ["rank", "next_goal_shape", "recommendation_label", "why", "minimum_scope", "do_not_do"],
    )

    metadata = {
        "date": "2026-07-01",
        "goal": "025-c-hi-existing-asset-topology-application-design",
        "status": "complete_conditional_local_application_design",
        "decision_label": "CONDITIONAL_LOCAL_APPLICATION_CONNECTED_CORE_NOT_FINAL",
        "headline_result": (
            "Existing Goal005/007 compact assets support a deterministic conditional residual-core "
            "application. The selected 1 percent residual-core mask classifies as connected_envelope_single_system, "
            "but broader threshold sensitivity becomes mixed/ambiguous, so this is not a final endpoint topology claim."
        ),
        "endpoint_application_made": True,
        "final_observational_topology_claim": False,
        "selected_application": {
            "side_seed_protocol": "tracer_threshold_z_sign_seed",
            "xray_mask_protocol": "goal007_boxcar_unsharp_low_residual_core",
            "residual_percentile": selected_percentile,
            "boxcar_pixels": boxcar_pixels,
            "min_component_pixels": min_component_pixels,
            "bridge_connectivity": connectivity,
            "observed_topology_class": result.topology_class,
            "gate_status": result.gate_status,
        },
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
        "active_caveats": [
            "not publication-ready observables",
            "conditional residual-core classification is not a final observational endpoint topology",
            "tracer side labels remain provenance proxies, not X-ray-fitted cavities",
            "threshold sensitivity needs local review before any bounded application/rerun",
            "sparse radio remains diagnostic only",
            "Level 3 gravity remains blocked_missing_potential",
            "pV/adopted 2.5pV/4pV convention remains active",
        ],
        "asset_files": [
            "input_asset_contract.csv",
            "side_seed_protocol.csv",
            "xray_mask_protocol.csv",
            "application_readiness_decision.csv",
            "topology_application_result.csv",
            "topology_component_summary.csv",
            "next_step_recommendation.csv",
            "existing_asset_topology_application_metadata.json",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "existing_asset_topology_application_metadata.json").write_text(
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
