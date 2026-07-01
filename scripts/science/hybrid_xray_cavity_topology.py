#!/usr/bin/env python3
"""Hybrid tracer-seeded, X-ray-constrained topology gate helpers."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / "docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01"
)
GOAL005_ASSET_DIR = (
    ROOT / "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
)
GOAL007_ASSET_DIR = (
    ROOT / "docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16"
)


class AmbiguousTopologyError(ValueError):
    """Raised when a caller requires a decisive topology classification."""


@dataclass(frozen=True)
class TopologyParameters:
    cavity_fraction_of_background: float = 0.5
    min_component_pixels: int = 4
    bridge_connectivity: int = 4

    def validate(self) -> None:
        if not (0.0 < self.cavity_fraction_of_background < 1.0):
            raise ValueError("cavity_fraction_of_background must be between 0 and 1")
        if self.min_component_pixels < 1:
            raise ValueError("min_component_pixels must be at least 1")
        if self.bridge_connectivity not in {4, 8}:
            raise ValueError("bridge_connectivity must be 4 or 8")

    def as_metadata(self) -> dict[str, str]:
        return {
            "cavity_fraction_of_background": f"{self.cavity_fraction_of_background:.16g}",
            "background_statistic": "median finite X-ray value",
            "cavity_mask_rule": "xray <= median(xray) * cavity_fraction_of_background",
            "min_component_pixels": str(self.min_component_pixels),
            "bridge_connectivity": str(self.bridge_connectivity),
            "side_labels": "-1=negative_z tracer proxy, +1=positive_z tracer proxy, 0=unlabelled",
            "classification_rule": (
                "two significant side-specific components => two_separate_cavities; "
                "one significant component spanning both sides => connected_envelope_single_system; "
                "otherwise ambiguous_needs_review"
            ),
        }


@dataclass(frozen=True)
class TopologyResult:
    case_id: str
    topology_class: str
    gate_status: str
    reason: str
    significant_component_count: int
    component_side_classes: list[str]
    side_label_summary: dict[str, dict[str, int]]
    parameters: dict[str, str]
    cavity_threshold: float
    cavity_candidate_pixels: int

    def to_row(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "observed_topology_class": self.topology_class,
            "gate_status": self.gate_status,
            "reason": self.reason,
            "significant_component_count": self.significant_component_count,
            "component_side_classes": ";".join(self.component_side_classes),
            "negative_seed_pixels": self.side_label_summary["negative_z"]["seed_pixels"],
            "positive_seed_pixels": self.side_label_summary["positive_z"]["seed_pixels"],
            "cavity_candidate_pixels": self.cavity_candidate_pixels,
            "cavity_threshold": f"{self.cavity_threshold:.16g}",
        }


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def validate_inputs(xray: np.ndarray, side_labels: np.ndarray, parameters: TopologyParameters) -> None:
    parameters.validate()
    if xray.ndim != 2:
        raise ValueError("xray must be a two-dimensional array")
    if side_labels.ndim != 2:
        raise ValueError("side_labels must be a two-dimensional array")
    if xray.shape != side_labels.shape:
        raise ValueError("xray and side_labels must have the same shape")
    if not np.all(np.isfinite(xray)):
        raise ValueError("xray contains non-finite values")
    labels = set(np.unique(side_labels).astype(int).tolist())
    if not {-1, 1}.issubset(labels):
        raise ValueError("side_labels must contain both -1 and 1 tracer-proxy side labels")
    if not labels.issubset({-1, 0, 1}):
        raise ValueError("side_labels may contain only -1, 0, and 1")


def side_label_summary(side_labels: np.ndarray) -> dict[str, dict[str, int]]:
    return {
        "negative_z": {"seed_pixels": int(np.count_nonzero(side_labels == -1))},
        "positive_z": {"seed_pixels": int(np.count_nonzero(side_labels == 1))},
    }


def neighbour_offsets(connectivity: int) -> list[tuple[int, int]]:
    offsets = [(-1, 0), (0, -1), (0, 1), (1, 0)]
    if connectivity == 8:
        offsets.extend([(-1, -1), (-1, 1), (1, -1), (1, 1)])
    return offsets


def connected_components(mask: np.ndarray, *, connectivity: int) -> list[np.ndarray]:
    visited = np.zeros(mask.shape, dtype=bool)
    components: list[np.ndarray] = []
    offsets = neighbour_offsets(connectivity)
    rows, cols = mask.shape
    for start_row, start_col in zip(*np.nonzero(mask), strict=True):
        if visited[start_row, start_col]:
            continue
        stack = [(int(start_row), int(start_col))]
        visited[start_row, start_col] = True
        pixels: list[tuple[int, int]] = []
        while stack:
            row, col = stack.pop()
            pixels.append((row, col))
            for d_row, d_col in offsets:
                n_row = row + d_row
                n_col = col + d_col
                if n_row < 0 or n_row >= rows or n_col < 0 or n_col >= cols:
                    continue
                if visited[n_row, n_col] or not mask[n_row, n_col]:
                    continue
                visited[n_row, n_col] = True
                stack.append((n_row, n_col))
        component = np.zeros(mask.shape, dtype=bool)
        rr, cc = zip(*pixels, strict=True)
        component[np.array(rr), np.array(cc)] = True
        components.append(component)
    return components


def component_side_class(component: np.ndarray, side_labels: np.ndarray) -> str:
    negative = int(np.count_nonzero(component & (side_labels == -1)))
    positive = int(np.count_nonzero(component & (side_labels == 1)))
    if negative > 0 and positive > 0:
        return "spans_negative_and_positive"
    if negative > 0:
        return "negative_z"
    if positive > 0:
        return "positive_z"
    return "unlabelled"


def classify_from_component_sides(component_sides: list[str]) -> tuple[str, str, str]:
    if component_sides == ["spans_negative_and_positive"]:
        return (
            "connected_envelope_single_system",
            "pass",
            "one significant X-ray cavity component spans both tracer-proxy side labels",
        )
    if sorted(component_sides) == ["negative_z", "positive_z"] and len(component_sides) == 2:
        return (
            "two_separate_cavities",
            "pass",
            "two significant X-ray cavity components map separately to negative_z and positive_z labels",
        )
    return (
        "ambiguous_needs_review",
        "fail",
        "topology does not satisfy two-side or connected-envelope criteria",
    )


def classify_hybrid_topology(
    xray: np.ndarray,
    side_labels: np.ndarray,
    *,
    parameters: TopologyParameters | None = None,
    case_id: str = "case",
    fail_on_ambiguous: bool = False,
) -> TopologyResult:
    params = parameters or TopologyParameters()
    xray = np.asarray(xray, dtype=float)
    side_labels = np.asarray(side_labels, dtype=int)
    validate_inputs(xray, side_labels, params)

    background = float(np.median(xray[np.isfinite(xray)]))
    threshold = background * params.cavity_fraction_of_background
    cavity_mask = xray <= threshold
    components = connected_components(cavity_mask, connectivity=params.bridge_connectivity)
    significant = [
        component
        for component in components
        if int(np.count_nonzero(component)) >= params.min_component_pixels
    ]
    component_sides = [component_side_class(component, side_labels) for component in significant]
    topology_class, gate_status, reason = classify_from_component_sides(component_sides)
    result = TopologyResult(
        case_id=case_id,
        topology_class=topology_class,
        gate_status=gate_status,
        reason=reason,
        significant_component_count=len(significant),
        component_side_classes=component_sides,
        side_label_summary=side_label_summary(side_labels),
        parameters=params.as_metadata(),
        cavity_threshold=threshold,
        cavity_candidate_pixels=int(np.count_nonzero(cavity_mask)),
    )
    if fail_on_ambiguous and topology_class == "ambiguous_needs_review":
        raise AmbiguousTopologyError(f"{case_id}: {reason}")
    return result


def two_side_seed_labels(shape: tuple[int, int]) -> np.ndarray:
    labels = np.zeros(shape, dtype=int)
    labels[:, : shape[1] // 2] = -1
    labels[:, shape[1] // 2 :] = 1
    return labels


def synthetic_case_arrays(case_id: str) -> tuple[np.ndarray, np.ndarray, str]:
    xray = np.ones((12, 16), dtype=float)
    expected: str
    if case_id == "synthetic_two_separate_cavities":
        xray[3:6, 3:6] = 0.2
        xray[3:6, 10:13] = 0.2
        expected = "two_separate_cavities"
    elif case_id == "synthetic_connected_envelope_single_system":
        xray[3:6, 3:13] = 0.2
        expected = "connected_envelope_single_system"
    elif case_id == "synthetic_one_side_only_ambiguous":
        xray[3:6, 3:6] = 0.2
        expected = "ambiguous_needs_review"
    else:
        raise ValueError(f"unknown synthetic case: {case_id}")
    return xray, two_side_seed_labels(xray.shape), expected


def synthetic_gate_tables() -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    parameters = TopologyParameters(
        cavity_fraction_of_background=0.5,
        min_component_pixels=4,
        bridge_connectivity=4,
    )
    case_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []
    for case_id in (
        "synthetic_two_separate_cavities",
        "synthetic_connected_envelope_single_system",
        "synthetic_one_side_only_ambiguous",
    ):
        xray, side_labels, expected = synthetic_case_arrays(case_id)
        result = classify_hybrid_topology(
            xray,
            side_labels,
            parameters=parameters,
            case_id=case_id,
        )
        case_rows.append(
            {
                "case_id": case_id,
                "shape": f"{xray.shape[0]}x{xray.shape[1]}",
                "expected_topology_class": expected,
                "expected_gate_status": "fail" if expected == "ambiguous_needs_review" else "pass",
                "xray_background": "1.0",
                "xray_cavity_value": "0.2",
                "side_label_contract": "-1 negative_z proxy, +1 positive_z proxy",
            }
        )
        row = result.to_row()
        row["expected_topology_class"] = expected
        row["classification_matches_expected"] = str(result.topology_class == expected).lower()
        result_rows.append(row)

    parameter_rows = [
        {"parameter": key, "value": value, "role": "deterministic_topology_protocol"}
        for key, value in parameters.as_metadata().items()
    ]
    return case_rows, result_rows, parameter_rows


def accepted_asset_readiness_rows() -> list[dict[str, str]]:
    goal005_xray = GOAL005_ASSET_DIR / "xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv"
    goal005_tracer = GOAL005_ASSET_DIR / "xraise_grid/tracer_max_los.tsv"
    goal005_boundary = GOAL005_ASSET_DIR / "cavity_stub/cavity_ellipse_boundary_0deg.tsv"
    goal007_metadata = GOAL007_ASSET_DIR / "observational_product_readiness_metadata.json"
    return [
        {
            "asset_or_requirement": "Goal005 corrected X-ray map",
            "path": display_path(goal005_xray),
            "available_locally": str(goal005_xray.exists()).lower(),
            "enough_for_goal024_application": "partial",
            "reason": "provides the accepted 0deg surface-brightness field, but not a reviewed X-ray cavity mask",
            "remaining_need": "deterministic residual/topology mask protocol before real application",
        },
        {
            "asset_or_requirement": "Goal005 tracer max line-of-sight map",
            "path": display_path(goal005_tracer),
            "available_locally": str(goal005_tracer.exists()).lower(),
            "enough_for_goal024_application": "partial",
            "reason": "supports tracer-proxy provenance, but does not itself define side-labelled X-ray cavity masks",
            "remaining_need": "side-seed derivation rule and X-ray mask rule must be reviewed locally",
        },
        {
            "asset_or_requirement": "Goal005 cavity ellipse boundary",
            "path": display_path(goal005_boundary),
            "available_locally": str(goal005_boundary.exists()).lower(),
            "enough_for_goal024_application": "no",
            "reason": "ellipse is the accepted tracer-defined overlay, not an X-ray-fitted topology boundary",
            "remaining_need": "use only as provenance comparator, not as ground truth for the gate",
        },
        {
            "asset_or_requirement": "Goal007 residual/topology review metadata",
            "path": display_path(goal007_metadata),
            "available_locally": str(goal007_metadata.exists()).lower(),
            "enough_for_goal024_application": "partial",
            "reason": "records the residual display method and topology caveat, but not a machine-readable residual matrix",
            "remaining_need": "future local method goal should generate or record a parseable residual/topology layer",
        },
    ]


def next_step_rows() -> list[dict[str, str]]:
    return [
        {
            "rank": "1",
            "next_goal_shape": "local_existing_asset_application_design",
            "recommendation_label": "prepare_bounded_application_protocol",
            "why": (
                "synthetic gate can distinguish two-side, connected-envelope, and ambiguous cases while "
                "preserving tracer-proxy labels"
            ),
            "minimum_scope": (
                "derive deterministic side-seed and residual/topology-mask tables from existing Goal005/007 "
                "compact assets without HDF5 rerun"
            ),
            "do_not_do": "do not rerun XRAiSE/HDF5, overwrite accepted products, or call the proxy an X-ray fit",
        },
        {
            "rank": "2",
            "next_goal_shape": "bounded_existing_output_endpoint_application",
            "recommendation_label": "future_only_after_local_application",
            "why": "real endpoint application may be useful after the local asset protocol is deterministic and reviewed",
            "minimum_scope": "explicitly authorized no-overwrite endpoint package",
            "do_not_do": "do not stage or submit remote work from Goal024",
        },
        {
            "rank": "3",
            "next_goal_shape": "maintain_tracer_proxy_status_quo",
            "recommendation_label": "fallback_if_method_bandwidth_missing",
            "why": "current tracer ellipsoids remain valid prove-out/provenance proxies",
            "minimum_scope": "status-only caveat preservation",
            "do_not_do": "do not freeze tracer ellipses as final observational X-ray topology",
        },
    ]


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def write_gate_assets(output_dir: Path) -> None:
    case_rows, result_rows, parameter_rows = synthetic_gate_tables()
    readiness_rows = accepted_asset_readiness_rows()
    recommendation_rows = next_step_rows()
    write_rows(
        output_dir / "synthetic_topology_cases.csv",
        case_rows,
        [
            "case_id",
            "shape",
            "expected_topology_class",
            "expected_gate_status",
            "xray_background",
            "xray_cavity_value",
            "side_label_contract",
        ],
    )
    write_rows(
        output_dir / "topology_gate_results.csv",
        result_rows,
        [
            "case_id",
            "expected_topology_class",
            "observed_topology_class",
            "classification_matches_expected",
            "gate_status",
            "reason",
            "significant_component_count",
            "component_side_classes",
            "negative_seed_pixels",
            "positive_seed_pixels",
            "cavity_candidate_pixels",
            "cavity_threshold",
        ],
    )
    write_rows(output_dir / "method_parameters.csv", parameter_rows, ["parameter", "value", "role"])
    write_rows(
        output_dir / "accepted_asset_application_readiness.csv",
        readiness_rows,
        [
            "asset_or_requirement",
            "path",
            "available_locally",
            "enough_for_goal024_application",
            "reason",
            "remaining_need",
        ],
    )
    write_rows(
        output_dir / "next_step_recommendation.csv",
        recommendation_rows,
        ["rank", "next_goal_shape", "recommendation_label", "why", "minimum_scope", "do_not_do"],
    )
    metadata = {
        "date": "2026-07-01",
        "goal": "024-c-hi-hybrid-xray-cavity-topology-gate",
        "status": "complete_synthetic_local_gate",
        "decision_label": "HYBRID_TOPOLOGY_SYNTHETIC_GATE_PASSED_LOCAL_APPLICATION_PROTOCOL_NEXT",
        "headline_result": (
            "The helper separates tracer-proxy side labels from X-ray topology class and passes "
            "synthetic tests for two-side, connected-envelope, and ambiguous cases."
        ),
        "topology_classes": [
            "two_separate_cavities",
            "connected_envelope_single_system",
            "ambiguous_needs_review",
        ],
        "synthetic_gate": {
            "case_count": len(case_rows),
            "all_expected_classifications_matched": all(
                row["classification_matches_expected"] == "true" for row in result_rows
            ),
            "ambiguous_case_gate_status": "fail",
        },
        "accepted_asset_application_status": (
            "not_applied_to_real_endpoint_in_goal024; compact assets are partial and need a "
            "deterministic side-seed/residual-mask application protocol first"
        ),
        "recommended_next_goal_shape": (
            "local existing-asset application protocol that derives parseable side-seed and "
            "X-ray residual/topology mask tables from Goal005/007 compact assets without HDF5 rerun"
        ),
        "active_caveats": [
            "not publication-ready observables",
            "tracer side labels remain provenance proxies, not X-ray-fitted cavities",
            "connected-envelope versus two-side real endpoint topology remains unresolved until local application",
            "sparse radio remains diagnostic only",
            "Level 3 gravity remains blocked_missing_potential",
            "pV/adopted 2.5pV/4pV convention remains active",
        ],
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
        "asset_files": [
            "synthetic_topology_cases.csv",
            "topology_gate_results.csv",
            "method_parameters.csv",
            "accepted_asset_application_readiness.csv",
            "next_step_recommendation.csv",
            "hybrid_topology_gate_metadata.json",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "hybrid_topology_gate_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for Goal 024 topology gate assets.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_gate_assets(args.output_dir)
    print(f"wrote {display_path(args.output_dir)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
