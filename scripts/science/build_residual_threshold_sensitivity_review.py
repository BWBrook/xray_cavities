#!/usr/bin/env python3
"""Build Goal 026 residual-threshold topology sensitivity review assets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import hybrid_xray_cavity_topology as topology


ROOT = Path(__file__).resolve().parents[2]
GOAL005 = ROOT / "docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
GOAL007 = ROOT / "docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16"
GOAL025 = ROOT / "docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01"
DEFAULT_OUTPUT = (
    ROOT / "docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01"
)
DEFAULT_THRESHOLDS = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0]


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


def format_percentile(value: float) -> str:
    return f"{value:g}"


def bool_text(value: bool) -> str:
    return str(bool(value)).lower()


def component_rows_for_mask(
    mask: np.ndarray,
    side_labels: np.ndarray,
    *,
    percentile: float,
    residual_threshold: float,
    min_component_pixels: int,
    connectivity: int,
) -> list[dict[str, Any]]:
    components = topology.connected_components(mask, connectivity=connectivity)
    mask_pixels = int(np.count_nonzero(mask))
    total_pixels = int(mask.size)
    rows: list[dict[str, Any]] = []
    for component_index, component in enumerate(components, start=1):
        pixel_count = int(np.count_nonzero(component))
        if pixel_count < min_component_pixels:
            continue
        negative = int(np.count_nonzero(component & (side_labels == -1)))
        positive = int(np.count_nonzero(component & (side_labels == 1)))
        unlabelled = pixel_count - negative - positive
        side_class = topology.component_side_class(component, side_labels)
        rows.append(
            {
                "percentile": format_percentile(percentile),
                "residual_threshold": f"{residual_threshold:.16g}",
                "component_index": component_index,
                "pixel_count": pixel_count,
                "component_fraction_of_mask": f"{pixel_count / mask_pixels:.16g}",
                "component_fraction_of_total": f"{pixel_count / total_pixels:.16g}",
                "negative_seed_overlap_pixels": negative,
                "positive_seed_overlap_pixels": positive,
                "unlabelled_overlap_pixels": unlabelled,
                "side_class": side_class,
                "used_for_seeded_topology_classification": bool_text(side_class != "unlabelled"),
            }
        )
    rows.sort(
        key=lambda row: (
            float(row["percentile"]),
            -int(row["pixel_count"]),
            int(row["component_index"]),
        )
    )
    return rows


def overlap_rows_for_mask(
    mask: np.ndarray,
    side_labels: np.ndarray,
    *,
    percentile: float,
    residual_threshold: float,
) -> list[dict[str, Any]]:
    mask_pixels = int(np.count_nonzero(mask))
    rows: list[dict[str, Any]] = []
    for side, label in (("negative_z", -1), ("positive_z", 1)):
        seed_pixels = int(np.count_nonzero(side_labels == label))
        overlap = int(np.count_nonzero(mask & (side_labels == label)))
        rows.append(
            {
                "percentile": format_percentile(percentile),
                "residual_threshold": f"{residual_threshold:.16g}",
                "side": side,
                "seed_pixels": seed_pixels,
                "mask_seed_overlap_pixels": overlap,
                "seed_overlap_fraction": f"{overlap / seed_pixels:.16g}",
                "mask_overlap_fraction": f"{overlap / mask_pixels:.16g}",
            }
        )
    return rows


def recommendation_for_threshold(
    topology_class: str,
    gate_status: str,
    spanning: bool,
    side_specific: bool,
    unlabelled_count: int,
) -> str:
    if topology_class == "connected_envelope_single_system" and gate_status == "pass":
        return "preserve_as_conditional_connected_residual_core_not_final_topology"
    if spanning and side_specific:
        return "broader_mask_mixes_connected_core_with_side_specific_structure"
    if unlabelled_count > 0:
        return "unlabelled_residual_islands_require_explicit_review"
    return "ambiguous_under_current_seeded_topology_contract"


def sensitivity_tables_from_arrays(
    residual: np.ndarray,
    side_labels: np.ndarray,
    *,
    percentiles: list[float] | tuple[float, ...] = tuple(DEFAULT_THRESHOLDS),
    min_component_pixels: int = 50,
    connectivity: int = 4,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    residual = np.asarray(residual, dtype=float)
    side_labels = np.asarray(side_labels, dtype=int)
    if residual.ndim != 2 or side_labels.ndim != 2 or residual.shape != side_labels.shape:
        raise ValueError("residual and side_labels must be two-dimensional arrays with matching shape")
    if not np.all(np.isfinite(residual)):
        raise ValueError("residual must contain finite values")
    if not {-1, 1}.issubset(set(np.unique(side_labels).astype(int).tolist())):
        raise ValueError("side_labels must include both negative and positive seed labels")

    params = topology.TopologyParameters(
        min_component_pixels=min_component_pixels,
        bridge_connectivity=connectivity,
    )
    summary_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    overlap_rows: list[dict[str, Any]] = []
    total_pixels = int(residual.size)
    negative_seed_pixels = int(np.count_nonzero(side_labels == -1))
    positive_seed_pixels = int(np.count_nonzero(side_labels == 1))

    for percentile in percentiles:
        mask, residual_threshold = topology.low_residual_percentile_mask(
            residual,
            percentile=float(percentile),
        )
        rows_for_threshold = component_rows_for_mask(
            mask,
            side_labels,
            percentile=float(percentile),
            residual_threshold=residual_threshold,
            min_component_pixels=min_component_pixels,
            connectivity=connectivity,
        )
        component_rows.extend(rows_for_threshold)
        overlap_rows.extend(
            overlap_rows_for_mask(
                mask,
                side_labels,
                percentile=float(percentile),
                residual_threshold=residual_threshold,
            )
        )
        result = topology.classify_hybrid_topology_from_mask(
            mask,
            side_labels,
            parameters=params,
            case_id=f"residual_percentile_{percentile:g}",
            ignore_unlabelled_components=True,
        )
        side_counts = Counter(row["side_class"] for row in rows_for_threshold)
        spanning = side_counts["spans_negative_and_positive"] > 0
        side_specific = side_counts["negative_z"] > 0 or side_counts["positive_z"] > 0
        unlabelled_count = side_counts["unlabelled"]
        mask_pixels = int(np.count_nonzero(mask))
        negative_overlap = int(np.count_nonzero(mask & (side_labels == -1)))
        positive_overlap = int(np.count_nonzero(mask & (side_labels == 1)))
        summary_rows.append(
            {
                "percentile": format_percentile(float(percentile)),
                "residual_threshold": f"{residual_threshold:.16g}",
                "mask_pixels": mask_pixels,
                "mask_fraction": f"{mask_pixels / total_pixels:.16g}",
                "significant_component_count_all": len(rows_for_threshold),
                "seeded_component_count": result.significant_component_count,
                "unlabelled_component_count": unlabelled_count,
                "component_side_class_counts": ";".join(
                    f"{key}={side_counts[key]}"
                    for key in (
                        "spans_negative_and_positive",
                        "negative_z",
                        "positive_z",
                        "unlabelled",
                    )
                ),
                "negative_seed_overlap_pixels": negative_overlap,
                "positive_seed_overlap_pixels": positive_overlap,
                "negative_seed_overlap_fraction": f"{negative_overlap / negative_seed_pixels:.16g}",
                "positive_seed_overlap_fraction": f"{positive_overlap / positive_seed_pixels:.16g}",
                "spanning_component_exists": bool_text(spanning),
                "side_specific_components_exist": bool_text(side_specific),
                "observed_topology_class": result.topology_class,
                "gate_status": result.gate_status,
                "recommendation_consequence": recommendation_for_threshold(
                    result.topology_class,
                    result.gate_status,
                    spanning,
                    side_specific,
                    unlabelled_count,
                ),
            }
        )
    return summary_rows, component_rows, overlap_rows


def decision_from_summary(rows: list[dict[str, Any]]) -> tuple[str, str]:
    connected_percentiles = {
        row["percentile"]
        for row in rows
        if row["observed_topology_class"] == "connected_envelope_single_system"
        and row["gate_status"] == "pass"
    }
    ambiguous_percentiles = {
        row["percentile"]
        for row in rows
        if row["observed_topology_class"] == "ambiguous_needs_review"
    }
    if {"1", "2"}.issubset(connected_percentiles) and ambiguous_percentiles:
        return (
            "CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL",
            "bounded_conditional_endpoint_topology_application_package",
        )
    if connected_percentiles and not ambiguous_percentiles:
        return (
            "CONNECTED_CORE_STABLE_OVER_REVIEW_THRESHOLDS_BOUNDED_APPLICATION_READY",
            "bounded_endpoint_topology_application_package",
        )
    return (
        "THRESHOLD_SENSITIVITY_TOO_BRITTLE_HOLD_TRACER_PROXY",
        "hold_at_tracer_proxy_or_refine_mask_protocol",
    )


def load_endpoint_context() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, int]:
    xray_path = GOAL005 / "xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv"
    tracer_path = GOAL005 / "xraise_grid/tracer_max_los.tsv"
    x_path = GOAL005 / "xraise_grid/x_kpc.tsv"
    z_path = GOAL005 / "xraise_grid/z_kpc.tsv"
    metadata_path = GOAL007 / "observational_product_readiness_metadata.json"
    xray = read_matrix(xray_path)
    tracer = read_matrix(tracer_path)
    x_axis = read_vector(x_path)
    z_axis = read_vector(z_path)
    with metadata_path.open() as handle:
        metadata = json.load(handle)
    tracer_threshold = float(metadata["tracer_threshold"])
    boxcar_pixels = int(metadata["contrast_method"]["boxcar_pixels"])
    if xray.shape != tracer.shape:
        raise ValueError("xray and tracer arrays have different shapes")
    if z_axis.shape[0] != xray.shape[0] or x_axis.shape[0] != xray.shape[1]:
        raise ValueError("x/z axes are not compatible with xray array shape")
    return xray, tracer, x_axis, z_axis, tracer_threshold, boxcar_pixels


def figure_panel_for_mask(mask: np.ndarray, side_labels: np.ndarray) -> np.ndarray:
    panel = np.zeros(mask.shape, dtype=float)
    panel[mask & (side_labels == 0)] = 1.0
    panel[mask & (side_labels == -1)] = 2.0
    panel[mask & (side_labels == 1)] = 3.0
    return panel


def write_figure(
    output_path: Path,
    xray: np.ndarray,
    residual: np.ndarray,
    side_labels: np.ndarray,
    percentiles: list[float],
    summary_rows: list[dict[str, Any]],
) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    masks = [
        topology.low_residual_percentile_mask(residual, percentile=percentile)[0]
        for percentile in percentiles
    ]
    summary_by_percentile = {row["percentile"]: row for row in summary_rows}
    fig, axes = plt.subplots(3, 4, figsize=(14, 10), constrained_layout=True)
    axes = axes.ravel()

    log_xray = np.log10(xray)
    axes[0].imshow(log_xray, origin="lower", cmap="magma")
    axes[0].set_title("corrected X-ray log10")
    axes[1].imshow(residual, origin="lower", cmap="coolwarm")
    axes[1].set_title("boxcar residual")
    axes[2].imshow(side_labels, origin="lower", cmap=ListedColormap(["#2b6cb0", "#f7f7f7", "#c53030"]))
    axes[2].set_title("tracer-proxy side seeds")
    axes[3].axis("off")
    axes[3].text(
        0.02,
        0.95,
        "mask colors\n"
        "gray: unlabelled residual island\n"
        "blue: negative-z seed overlap\n"
        "red: positive-z seed overlap\n\n"
        "classification uses seeded components;\n"
        "unlabelled islands remain visible.",
        va="top",
        fontsize=9,
    )

    mask_cmap = ListedColormap(["#f7f7f7", "#8a8a8a", "#2b6cb0", "#c53030"])
    class_short = {
        "connected_envelope_single_system": "connected core",
        "ambiguous_needs_review": "ambiguous",
        "two_separate_cavities": "two-side",
    }
    used_axes: set[int] = set(range(4))
    for axis_index, (axis, percentile, mask) in enumerate(
        zip(axes[4:], percentiles, masks, strict=False),
        start=4,
    ):
        used_axes.add(axis_index)
        panel = figure_panel_for_mask(mask, side_labels)
        axis.imshow(panel, origin="lower", cmap=mask_cmap, vmin=0, vmax=3)
        row = summary_by_percentile[format_percentile(percentile)]
        axis.set_title(f"{percentile:g}% {class_short[row['observed_topology_class']]}", fontsize=10)
        axis.text(
            0.02,
            0.02,
            (
                f"mask={row['mask_pixels']}\n"
                f"seeded={row['seeded_component_count']} "
                f"unlabelled={row['unlabelled_component_count']}"
            ),
            transform=axis.transAxes,
            va="bottom",
            ha="left",
            fontsize=7,
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none", "pad": 2},
        )
    for axis_index, axis in enumerate(axes):
        axis.set_xticks([])
        axis.set_yticks([])
        if axis_index not in used_axes:
            axis.axis("off")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def next_step_rows(decision_label: str, recommendation: str) -> list[dict[str, str]]:
    return [
        {
            "rank": "1",
            "next_goal_shape": recommendation,
            "recommendation_label": "preserve_connected_core_as_conditional_not_final",
            "why": (
                "the 1-2 percent residual-core regime stays connected while broader masks become ambiguous; "
                "the evidence supports a bounded no-overwrite conditional application package but not a final topology freeze"
            ),
            "minimum_scope": (
                "local or explicitly authorized no-overwrite endpoint topology package using the accepted "
                "residual-threshold sensitivity table and figure"
            ),
            "do_not_do": "do not overwrite accepted products, rerun HDF5/XRAiSE, or claim final observational topology",
            "decision_label": decision_label,
        },
        {
            "rank": "2",
            "next_goal_shape": "refine_residual_mask_protocol",
            "recommendation_label": "fallback_if_threshold_choice_not_accepted",
            "why": "threshold sensitivity remains visible: 5/10/20 percent masks are ambiguous under the seeded topology contract",
            "minimum_scope": "local threshold/morphology design only",
            "do_not_do": "do not use a broader mask as a decisive topology classifier",
            "decision_label": decision_label,
        },
        {
            "rank": "3",
            "next_goal_shape": "hold_at_tracer_proxy_status",
            "recommendation_label": "fallback_if_reviewer_wants_no_conditional_application",
            "why": "the accepted tracer ellipsoids remain reproducible prove-out/provenance proxies",
            "minimum_scope": "status/caveat preservation",
            "do_not_do": "do not call the tracer proxy an X-ray-fitted cavity topology",
            "decision_label": decision_label,
        },
    ]


def build_assets(output_dir: Path) -> None:
    xray, tracer, x_axis, z_axis, tracer_threshold, boxcar_pixels = load_endpoint_context()
    side_labels = topology.derive_tracer_side_seed_labels(
        tracer,
        z_axis,
        tracer_threshold=tracer_threshold,
    )
    residual = topology.boxcar_log_residual(xray, boxcar_pixels=boxcar_pixels)
    min_component_pixels = 50
    connectivity = 4
    summary_rows, component_rows, overlap_rows = sensitivity_tables_from_arrays(
        residual,
        side_labels,
        percentiles=DEFAULT_THRESHOLDS,
        min_component_pixels=min_component_pixels,
        connectivity=connectivity,
    )
    decision_label, recommendation = decision_from_summary(summary_rows)
    figure_path = output_dir / "residual_threshold_sensitivity.png"
    write_figure(figure_path, xray, residual, side_labels, DEFAULT_THRESHOLDS, summary_rows)

    xray_path = GOAL005 / "xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv"
    tracer_path = GOAL005 / "xraise_grid/tracer_max_los.tsv"
    x_path = GOAL005 / "xraise_grid/x_kpc.tsv"
    z_path = GOAL005 / "xraise_grid/z_kpc.tsv"
    goal007_metadata = GOAL007 / "observational_product_readiness_metadata.json"
    goal025_result = GOAL025 / "topology_application_result.csv"
    figure_rows = [
        {
            "asset": "corrected_xray",
            "path": display_path(xray_path),
            "sha256": sha256(xray_path),
            "role": "context panel and source for residual",
            "parameters": "log10 display; no XRAiSE rerun",
        },
        {
            "asset": "tracer_max_los",
            "path": display_path(tracer_path),
            "sha256": sha256(tracer_path),
            "role": "source for tracer-proxy side labels",
            "parameters": f"tracer_max_los >= {tracer_threshold:g}; z sign split",
        },
        {
            "asset": "x_axis_kpc",
            "path": display_path(x_path),
            "sha256": sha256(x_path),
            "role": "axis compatibility evidence",
            "parameters": f"{x_axis.shape[0]} columns",
        },
        {
            "asset": "z_axis_kpc",
            "path": display_path(z_path),
            "sha256": sha256(z_path),
            "role": "axis compatibility and side-sign evidence",
            "parameters": f"{z_axis.shape[0]} rows",
        },
        {
            "asset": "goal007_metadata",
            "path": display_path(goal007_metadata),
            "sha256": sha256(goal007_metadata),
            "role": "boxcar residual and tracer-threshold provenance",
            "parameters": f"boxcar_pixels={boxcar_pixels}; tracer_threshold={tracer_threshold:g}",
        },
        {
            "asset": "goal025_conditional_application",
            "path": display_path(goal025_result),
            "sha256": sha256(goal025_result),
            "role": "prior conditional application and threshold sensitivity context",
            "parameters": "1/2 percent connected; 5/10/20 percent ambiguous",
        },
        {
            "asset": "residual_threshold_sensitivity_png",
            "path": display_path(figure_path),
            "sha256": sha256(figure_path),
            "role": "reviewer-facing threshold sensitivity figure",
            "parameters": f"percentiles={','.join(format_percentile(p) for p in DEFAULT_THRESHOLDS)}",
        },
    ]

    write_rows(
        output_dir / "residual_threshold_sensitivity.csv",
        summary_rows,
        [
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
        output_dir / "residual_component_sensitivity.csv",
        component_rows,
        [
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
        output_dir / "mask_seed_overlap_summary.csv",
        overlap_rows,
        [
            "percentile",
            "residual_threshold",
            "side",
            "seed_pixels",
            "mask_seed_overlap_pixels",
            "seed_overlap_fraction",
            "mask_overlap_fraction",
        ],
    )
    write_rows(
        output_dir / "figure_provenance.csv",
        figure_rows,
        ["asset", "path", "sha256", "role", "parameters"],
    )
    write_rows(
        output_dir / "next_step_recommendation.csv",
        next_step_rows(decision_label, recommendation),
        [
            "rank",
            "next_goal_shape",
            "recommendation_label",
            "why",
            "minimum_scope",
            "do_not_do",
            "decision_label",
        ],
    )
    metadata = {
        "date": "2026-07-01",
        "goal": "026-c-hi-residual-threshold-sensitivity-review",
        "status": "complete_local_threshold_sensitivity_review",
        "decision_label": decision_label,
        "selected_next_step_recommendation": recommendation,
        "headline_result": (
            "The 1-2 percent residual-core masks preserve the connected-envelope seeded topology result, "
            "while broader 5/10/20 percent masks are ambiguous; this supports only a conditional bounded "
            "application package, not a final endpoint topology claim."
        ),
        "threshold_percentiles": [format_percentile(value) for value in DEFAULT_THRESHOLDS],
        "method_parameters": {
            "residual": "log10(corrected_xray) - boxcar_smooth(log10(corrected_xray))",
            "boxcar_pixels": boxcar_pixels,
            "side_seed": "tracer_max_los >= tracer_threshold split by z_kpc sign",
            "tracer_threshold": tracer_threshold,
            "min_component_pixels": min_component_pixels,
            "bridge_connectivity": connectivity,
            "classification_unlabelled_components": "reported explicitly; ignored for seeded topology class",
        },
        "input_shape": {
            "xray_rows": int(xray.shape[0]),
            "xray_columns": int(xray.shape[1]),
            "x_axis_columns": int(x_axis.shape[0]),
            "z_axis_rows": int(z_axis.shape[0]),
        },
        "active_caveats": [
            "not publication-ready observables",
            "threshold sensitivity prevents a final observational endpoint topology claim",
            "tracer side labels remain provenance proxies, not X-ray-fitted cavities",
            "connected residual core is conditional under the selected residual/mask protocol",
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
            "residual_threshold_sensitivity.csv",
            "residual_component_sensitivity.csv",
            "mask_seed_overlap_summary.csv",
            "figure_provenance.csv",
            "next_step_recommendation.csv",
            "residual_threshold_sensitivity_metadata.json",
            "residual_threshold_sensitivity.png",
        ],
    }
    (output_dir / "residual_threshold_sensitivity_metadata.json").write_text(
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
