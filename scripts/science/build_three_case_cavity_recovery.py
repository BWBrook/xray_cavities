#!/usr/bin/env python3
"""Build the local observer-side portion of Goal 040."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

import three_case_cavity_recovery as recovery


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    ROOT
    / "docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12"
)


@dataclass(frozen=True)
class MapAnalysis:
    observer_mask: np.ndarray
    deficit: np.ndarray
    summary_row: dict[str, Any]
    component_rows: list[dict[str, Any]]
    tracer_rows: list[dict[str, Any]]


def sensitivity_protocols() -> list[dict[str, Any]]:
    """Return the predeclared physical-method sensitivity grid."""

    radial_methods = ((4.0, 8.0), (5.0, 10.0), (8.0, 15.0))
    rows: list[dict[str, Any]] = []
    for radial_bin_kpc, radial_smoothing_kpc in radial_methods:
        for fraction in recovery.LOW_RESIDUAL_FRACTIONS_PERCENT:
            rows.append(
                {
                    "radial_bin_kpc": radial_bin_kpc,
                    "radial_smoothing_kpc": radial_smoothing_kpc,
                    "candidate_fraction_percent": fraction,
                    "is_base": (
                        radial_bin_kpc == recovery.RADIAL_BIN_KPC
                        and radial_smoothing_kpc == recovery.RADIAL_SMOOTHING_KPC
                        and fraction == 1.0
                    ),
                }
            )
    return rows


def _observer_mask(
    loaded: recovery.LoadedMap,
    *,
    radial_bin_kpc: float,
    radial_smoothing_kpc: float,
    candidate_fraction_percent: float,
) -> tuple[np.ndarray, np.ndarray, float, recovery.ComponentSelection]:
    background_roi = recovery.build_elliptical_roi(
        loaded.horizontal_axis,
        loaded.z_axis,
        recovery.BACKGROUND_RADIUS_KPC,
        recovery.BACKGROUND_RADIUS_KPC,
    )
    candidate_roi = recovery.build_elliptical_roi(
        loaded.horizontal_axis,
        loaded.z_axis,
        recovery.CANDIDATE_RADIUS_KPC,
        recovery.CANDIDATE_RADIUS_KPC,
    )
    background = recovery.compute_azimuthal_median_background(
        loaded.corrected_xray,
        loaded.horizontal_axis,
        loaded.z_axis,
        background_roi=background_roi,
        radial_bin_kpc=radial_bin_kpc,
        radial_smoothing_kpc=radial_smoothing_kpc,
    )
    deficit = recovery.compute_fractional_deficit(loaded.corrected_xray, background)
    candidate, threshold = recovery.select_area_fraction_candidate(
        deficit,
        candidate_roi,
        loaded.horizontal_axis,
        loaded.z_axis,
        fraction=candidate_fraction_percent,
        high_values_are_candidates=True,
    )
    selected = recovery.label_and_filter_components(
        candidate,
        loaded.horizontal_axis,
        loaded.z_axis,
        min_area_kpc2=recovery.MIN_COMPONENT_AREA_KPC2,
        connectivity=recovery.CONNECTIVITY,
    )
    retained = np.zeros_like(candidate)
    for component in selected.components:
        retained |= component.mask
    return retained, deficit, threshold, selected


def _topology_class(summaries: list[recovery.ComponentSummary]) -> str:
    if not summaries:
        return "no_significant_component"
    if any(summary.crosses_z_zero for summary in summaries):
        return "connected_cross_midplane_component"
    if len(summaries) == 2:
        signs = {int(np.sign(summary.centroid_z_kpc)) for summary in summaries}
        if signs == {-1, 1}:
            return "two_separate_components"
    return "multiple_or_one_sided_components"


def analyse_loaded_map(loaded: recovery.LoadedMap, time_myr: float = 50.0) -> MapAnalysis:
    """Apply the fixed X-ray protocol, then validate against tracer truth."""

    if not np.isfinite(time_myr) or time_myr <= 0.0:
        raise ValueError("time_myr must be finite and positive")

    observer_mask, deficit, threshold, selected = _observer_mask(
        loaded,
        radial_bin_kpc=recovery.RADIAL_BIN_KPC,
        radial_smoothing_kpc=recovery.RADIAL_SMOOTHING_KPC,
        candidate_fraction_percent=1.0,
    )
    summaries = recovery.summarize_components(
        selected.components, loaded.horizontal_axis, loaded.z_axis
    )
    summaries.sort(key=lambda item: (item.centroid_z_kpc, item.centroid_x_kpc))
    cell_area = recovery._cell_area_grid(loaded.horizontal_axis, loaded.z_axis)
    retained_area = float(cell_area[observer_mask].sum())
    retained_deficit = deficit[observer_mask]
    volume_totals = {
        depth: float(sum(summary.volumes_kpc3[depth] for summary in summaries))
        for depth in ("minor_depth", "geometric_depth", "major_depth")
    }
    summary_row = {
        "case": loaded.spec.case,
        "view": loaded.spec.view,
        "time_myr": float(time_myr),
        "background_radius_kpc": recovery.BACKGROUND_RADIUS_KPC,
        "candidate_radius_kpc": recovery.CANDIDATE_RADIUS_KPC,
        "radial_bin_kpc": recovery.RADIAL_BIN_KPC,
        "radial_smoothing_kpc": recovery.RADIAL_SMOOTHING_KPC,
        "candidate_fraction_percent": 1.0,
        "candidate_selection_basis": "projected_physical_area_fraction",
        "candidate_threshold_fractional_deficit": threshold,
        "component_count": len(summaries),
        "topology_class": _topology_class(summaries),
        "retained_pixels": int(np.count_nonzero(observer_mask)),
        "retained_area_kpc2": retained_area,
        "mean_fractional_deficit": (
            float(np.mean(retained_deficit)) if retained_deficit.size else float("nan")
        ),
        "max_fractional_deficit": (
            float(np.max(retained_deficit)) if retained_deficit.size else float("nan")
        ),
        "area_integrated_fractional_deficit_kpc2": (
            float(np.sum(deficit[observer_mask] * cell_area[observer_mask]))
            if retained_deficit.size
            else 0.0
        ),
        "volume_minor_depth_kpc3": volume_totals["minor_depth"],
        "volume_geometric_depth_kpc3": volume_totals["geometric_depth"],
        "volume_major_depth_kpc3": volume_totals["major_depth"],
        "status": "observer_recovery_complete_truth_alignment_complete",
    }
    component_rows: list[dict[str, Any]] = []
    for component_index, summary in enumerate(summaries, start=1):
        component_rows.append(
            {
                "case": loaded.spec.case,
                "view": loaded.spec.view,
                "component_index": component_index,
                "source_label": summary.label,
                "area_kpc2": summary.area_kpc2,
                "centroid_horizontal_kpc": summary.centroid_x_kpc,
                "centroid_z_kpc": summary.centroid_z_kpc,
                "crosses_z_zero": summary.crosses_z_zero,
                "major_semiaxis_kpc": summary.major_semiaxis_kpc,
                "minor_semiaxis_kpc": summary.minor_semiaxis_kpc,
                "minor_depth_kpc": summary.depths_kpc["minor_depth"],
                "geometric_depth_kpc": summary.depths_kpc["geometric_depth"],
                "major_depth_kpc": summary.depths_kpc["major_depth"],
                "volume_minor_depth_kpc3": summary.volumes_kpc3["minor_depth"],
                "volume_geometric_depth_kpc3": summary.volumes_kpc3["geometric_depth"],
                "volume_major_depth_kpc3": summary.volumes_kpc3["major_depth"],
            }
        )
    tracer_rows: list[dict[str, Any]] = []
    for tracer_threshold in recovery.TRACER_THRESHOLDS:
        tracer_rows.append(
            {
                "case": loaded.spec.case,
                "view": loaded.spec.view,
                "tracer_threshold": tracer_threshold,
                **recovery.tracer_validation_metrics(
                    observer_mask,
                    loaded.tracer_max_los,
                    threshold=tracer_threshold,
                ),
                "interpretation": "post_hoc_validation_only_tracer_not_used_for_recovery",
            }
        )
    return MapAnalysis(observer_mask, deficit, summary_row, component_rows, tracer_rows)


def _sensitivity_rows(loaded: recovery.LoadedMap) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for protocol in sensitivity_protocols():
        mask, _, threshold, selected = _observer_mask(
            loaded,
            radial_bin_kpc=protocol["radial_bin_kpc"],
            radial_smoothing_kpc=protocol["radial_smoothing_kpc"],
            candidate_fraction_percent=protocol["candidate_fraction_percent"],
        )
        summaries = recovery.summarize_components(
            selected.components, loaded.horizontal_axis, loaded.z_axis
        )
        rows.append(
            {
                "case": loaded.spec.case,
                "view": loaded.spec.view,
                **protocol,
                "candidate_selection_basis": "projected_physical_area_fraction",
                "candidate_threshold_fractional_deficit": threshold,
                "component_count": len(summaries),
                "topology_class": _topology_class(summaries),
                "retained_pixels": int(np.count_nonzero(mask)),
                "retained_area_kpc2": float(
                    recovery._cell_area_grid(loaded.horizontal_axis, loaded.z_axis)[mask].sum()
                ),
                "volume_geometric_depth_kpc3": float(
                    sum(item.volumes_kpc3["geometric_depth"] for item in summaries)
                ),
            }
        )
    return rows


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_manifest(output_dir: Path) -> None:
    manifest = output_dir / "local_asset_manifest.sha256"
    lines = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path != manifest:
            lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(output_dir)}")
    manifest.write_text("\n".join(lines) + "\n")


def build_assets(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_rows: list[dict[str, Any]] = []
    component_rows: list[dict[str, Any]] = []
    tracer_rows: list[dict[str, Any]] = []
    sensitivity_rows: list[dict[str, Any]] = []
    provenance_rows: list[dict[str, Any]] = []
    panels: list[tuple[recovery.LoadedMap, MapAnalysis]] = []
    for loaded in recovery.load_accepted_maps():
        analysis = analyse_loaded_map(loaded)
        summary_rows.append(analysis.summary_row)
        component_rows.extend(analysis.component_rows)
        tracer_rows.extend(analysis.tracer_rows)
        sensitivity_rows.extend(_sensitivity_rows(loaded))
        panels.append((loaded, analysis))
        provenance_rows.append(
            {
                "case": loaded.spec.case,
                "view": loaded.spec.view,
                "source_type": loaded.spec.source_type,
                "corrected_xray_source": loaded.spec.corrected_xray,
                "tracer_source": loaded.spec.tracer_max_los,
                "horizontal_axis_source": loaded.spec.horizontal_axis,
                "z_axis_source": loaded.spec.z_axis,
                "tracer_role": "post_hoc_truth_validation_only",
            }
        )

    _write_rows(output_dir / "xray_recovery_summary.csv", summary_rows)
    _write_rows(output_dir / "xray_component_summary.csv", component_rows)
    _write_rows(output_dir / "projected_tracer_alignment.csv", tracer_rows)
    _write_rows(output_dir / "method_sensitivity.csv", sensitivity_rows)
    _write_rows(output_dir / "input_provenance.csv", provenance_rows)
    method_rows = [
        {"parameter": "background_radius_kpc", "value": 180, "role": "ambient_profile_field"},
        {"parameter": "candidate_radius_kpc", "value": 120, "role": "edge_safe_search_aperture"},
        {"parameter": "radial_bin_kpc", "value": 5, "role": "base_azimuthal_median_bin"},
        {"parameter": "radial_smoothing_kpc", "value": 10, "role": "base_profile_smoothing"},
        {"parameter": "candidate_fraction_percent", "value": 1, "role": "base_high_deficit_physical_area_tail"},
        {"parameter": "minimum_component_area_kpc2", "value": 25, "role": "physical_component_gate"},
        {"parameter": "connectivity", "value": 8, "role": "component_labelling"},
        {"parameter": "tracer_thresholds", "value": "1e-3;5e-3;1e-2", "role": "validation_only"},
    ]
    _write_rows(output_dir / "method_parameters.csv", method_rows)

    fig, axes = plt.subplots(3, 3, figsize=(12.4, 11.8), constrained_layout=True)
    for axis, (loaded, analysis) in zip(axes.flat, panels, strict=True):
        extent = [
            float(loaded.horizontal_axis.min()),
            float(loaded.horizontal_axis.max()),
            float(loaded.z_axis.min()),
            float(loaded.z_axis.max()),
        ]
        image = axis.imshow(
            analysis.deficit,
            origin="lower",
            extent=extent,
            cmap="coolwarm",
            vmin=-0.5,
            vmax=0.5,
            aspect="auto",
        )
        axis.contour(
            loaded.horizontal_axis,
            loaded.z_axis,
            analysis.observer_mask,
            levels=[0.5],
            colors="#00a651",
            linewidths=1.2,
        )
        axis.contour(
            loaded.horizontal_axis,
            loaded.z_axis,
            loaded.tracer_max_los >= 5.0e-3,
            levels=[0.5],
            colors="black",
            linewidths=0.7,
        )
        axis.set_xlim(-120, 120)
        axis.set_ylim(-120, 120)
        axis.set_title(
            f"{loaded.spec.case} | {loaded.spec.view} | "
            f"n={analysis.summary_row['component_count']}"
        )
        axis.set_xlabel("projected horizontal (kpc)")
        axis.set_ylabel("z (kpc)")
    fig.colorbar(image, ax=axes.ravel().tolist(), label="fractional X-ray deficit")
    fig.suptitle(
        "Three-case 50 Myr endpoint cavity recovery\n"
        "green: X-ray-only 1% physical-area candidate; "
        "black: projected tracer >= 5e-3 (validation only)",
        fontsize=14,
    )
    fig.savefig(output_dir / "three_case_endpoint_cavity_recovery.png", dpi=180, facecolor="white")
    plt.close(fig)

    metadata = {
        "status": "complete_product",
        "decision_label": "THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE",
        "cases": ["C-HI", "C-LO", "G-LO"],
        "views": ["0deg", "45deg", "90deg"],
        "evidence_layers": {
            "observer": "corrected_xray_only",
            "simulation_truth": "projected_tracer_post_hoc_only",
            "remote_truth": "level1_level2_and_tracer_shell_pressure",
        },
        "base_protocol": next(row for row in sensitivity_protocols() if row["is_base"]),
        "candidate_selection_basis": "projected_physical_area_fraction",
        "sensitivity_rows": len(sensitivity_rows),
        "final_observational_topology_frozen": False,
        "publication_ready": False,
    }
    (output_dir / "three_case_endpoint_cavity_recovery_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )
    _write_manifest(output_dir)
    print("status=complete_product")
    print("decision_label=THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_assets(args.output_dir)


if __name__ == "__main__":
    main()
