#!/usr/bin/env python3
"""Diagnose Goal 012 90-degree X-ray striping from local review assets."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "docs/science/assets"
DEFAULT_GOAL005 = ASSET_ROOT / "c_hi_final_endpoint_xray_cavity_alignment_2026-06-11"
DEFAULT_GOAL011 = ASSET_ROOT / "c_hi_final_45deg_viewing_angle_broadening_2026-06-23"
DEFAULT_GOAL012 = ASSET_ROOT / "c_hi_final_90deg_viewing_angle_broadening_2026-06-23"
DEFAULT_OUTPUT = ASSET_ROOT / "c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24"
XRAISE_LAYERS = (
    ("raw_xray", "xray_1kev_raw_mjy_sr.tsv", True),
    ("corrected_xray", "xray_1kev_xraise_corrected_mjy_sr.tsv", True),
    ("correction_ratio", "xray_1kev_correction_ratio.tsv", True),
    ("tracer_max", "tracer_max_los.tsv", False),
)
VIEW_DIRS = {
    "0deg": ("xraise_grid", None),
    "45deg": ("xraise_grid_45deg", 45.0),
    "90deg": ("xraise_grid_90deg", 90.0),
}
STRIPING_COLUMNS = [
    "view",
    "layer",
    "matrix_shape",
    "finite_fraction",
    "positive_fraction",
    "zero_or_nonpositive_fraction",
    "empty_column_fraction",
    "near_empty_column_fraction",
    "empty_column_count",
    "near_empty_column_count",
    "column_positive_fraction_min",
    "column_positive_fraction_median",
    "column_positive_fraction_max",
    "adjacent_column_median_abs_diff",
    "adjacent_row_median_abs_diff",
    "stripe_anisotropy",
    "positive_mask_equal_to_raw",
    "interpretation",
]
AXIS_COLUMNS = [
    "view",
    "axis_file",
    "axis_role",
    "n",
    "min_kpc",
    "max_kpc",
    "median_step_kpc",
    "min_step_kpc",
    "max_step_kpc",
    "max_step_deviation_kpc",
    "strictly_increasing",
    "x_u_identical_in_view",
    "same_length_as_0deg_x",
    "allclose_to_0deg_x",
    "interpretation",
]
RECOMMENDATION_COLUMNS = [
    "recommendation_label",
    "confidence",
    "primary_diagnosis",
    "evidence_summary",
    "not_supported_by_evidence",
    "smallest_next_local_step",
    "q018_q019_status",
]


def read_vector(path: Path) -> np.ndarray:
    values = np.loadtxt(path)
    if values.ndim != 1 or values.size < 2:
        raise ValueError(f"{path}: expected a one-dimensional coordinate vector")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path}: non-finite coordinate values")
    return np.asarray(values, dtype=float)


def read_matrix(path: Path) -> np.ndarray:
    values = np.loadtxt(path, delimiter="\t")
    if values.ndim != 2:
        raise ValueError(f"{path}: expected a two-dimensional matrix")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{path}: non-finite matrix values")
    return np.asarray(values, dtype=float)


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def display_path(path: Path) -> str:
    return str(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def transformed_for_stripe_metric(values: np.ndarray, *, log_positive: bool) -> np.ndarray:
    if log_positive:
        out = np.full(values.shape, np.nan, dtype=float)
        mask = np.isfinite(values) & (values > 0.0)
        out[mask] = np.log10(values[mask])
        return out
    return np.where(np.isfinite(values), values, np.nan)


def median_abs_diff(values: np.ndarray, *, axis: int) -> float:
    diffs = np.abs(np.diff(values, axis=axis))
    finite = diffs[np.isfinite(diffs)]
    if finite.size == 0:
        return 0.0
    return float(np.nanmedian(finite))


def mask_equal_to_reference(mask: np.ndarray, reference: np.ndarray | None) -> str:
    if reference is None:
        return "not_applicable"
    if mask.shape != reference.shape:
        return "shape_mismatch"
    return "true" if bool(np.array_equal(mask, reference)) else "false"


def striping_diagnostics_for_layer(
    *,
    view: str,
    layer: str,
    values: np.ndarray,
    log_positive: bool,
    raw_positive_mask: np.ndarray | None,
) -> dict[str, Any]:
    finite = np.isfinite(values)
    positive = finite & (values > 0.0)
    column_positive_fraction = positive.mean(axis=0)
    empty_columns = column_positive_fraction == 0.0
    near_empty_columns = column_positive_fraction < 0.05
    transformed = transformed_for_stripe_metric(values, log_positive=log_positive)
    adjacent_column = median_abs_diff(transformed, axis=1)
    adjacent_row = median_abs_diff(transformed, axis=0)
    anisotropy = math.inf if adjacent_row == 0.0 and adjacent_column > 0.0 else (
        adjacent_column / adjacent_row if adjacent_row > 0.0 else 0.0
    )
    if layer in {"raw_xray", "corrected_xray", "correction_ratio"} and empty_columns.any():
        interpretation = (
            "X-ray map has all-zero projected columns; if shared by raw/corrected/ratio "
            "this points to projection/bin occupancy, not display scaling or correction only."
        )
    elif layer in {"raw_xray", "corrected_xray", "correction_ratio"}:
        interpretation = (
            "X-ray map has no all-zero projected columns; useful contrast against projected "
            "views with empty projected columns."
        )
    else:
        interpretation = (
            "Tracer max is spatially compact, so empty tracer columns are not by themselves "
            "evidence for an X-ray projection defect."
        )
    return {
        "view": view,
        "layer": layer,
        "matrix_shape": f"{values.shape[0]}x{values.shape[1]}",
        "finite_fraction": f"{float(finite.mean()):.16g}",
        "positive_fraction": f"{float(positive.mean()):.16g}",
        "zero_or_nonpositive_fraction": f"{float(1.0 - positive.mean()):.16g}",
        "empty_column_fraction": f"{float(empty_columns.mean()):.16g}",
        "near_empty_column_fraction": f"{float(near_empty_columns.mean()):.16g}",
        "empty_column_count": int(empty_columns.sum()),
        "near_empty_column_count": int(near_empty_columns.sum()),
        "column_positive_fraction_min": f"{float(column_positive_fraction.min()):.16g}",
        "column_positive_fraction_median": f"{float(np.median(column_positive_fraction)):.16g}",
        "column_positive_fraction_max": f"{float(column_positive_fraction.max()):.16g}",
        "adjacent_column_median_abs_diff": f"{adjacent_column:.16g}",
        "adjacent_row_median_abs_diff": f"{adjacent_row:.16g}",
        "stripe_anisotropy": "inf" if math.isinf(anisotropy) else f"{anisotropy:.16g}",
        "positive_mask_equal_to_raw": mask_equal_to_reference(positive, raw_positive_mask),
        "interpretation": interpretation,
    }


def view_xraise_dir(goal005_dir: Path, goal011_dir: Path, goal012_dir: Path, view: str) -> Path:
    if view == "0deg":
        return goal005_dir / VIEW_DIRS[view][0]
    if view == "45deg":
        return goal011_dir / VIEW_DIRS[view][0]
    if view == "90deg":
        return goal012_dir / VIEW_DIRS[view][0]
    raise ValueError(f"unknown view: {view}")


def collect_striping_rows(goal005_dir: Path, goal011_dir: Path, goal012_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for view in ("0deg", "45deg", "90deg"):
        xraise_dir = view_xraise_dir(goal005_dir, goal011_dir, goal012_dir, view)
        raw_mask: np.ndarray | None = None
        raw_path = xraise_dir / "xray_1kev_raw_mjy_sr.tsv"
        if raw_path.exists():
            raw = read_matrix(raw_path)
            raw_mask = np.isfinite(raw) & (raw > 0.0)
        for layer, filename, log_positive in XRAISE_LAYERS:
            path = xraise_dir / filename
            if not path.exists():
                continue
            values = read_matrix(path)
            rows.append(
                striping_diagnostics_for_layer(
                    view=view,
                    layer=layer,
                    values=values,
                    log_positive=log_positive,
                    raw_positive_mask=raw_mask,
                )
            )
    return rows


def axis_rows_for_view(
    *,
    view: str,
    xraise_dir: Path,
    baseline_x: np.ndarray,
) -> list[dict[str, Any]]:
    axes: list[tuple[str, str, Path]] = [
        ("x_kpc.tsv", "sky_axis_written_as_x", xraise_dir / "x_kpc.tsv"),
        ("u_kpc.tsv", "projected_u_axis", xraise_dir / "u_kpc.tsv"),
        ("z_kpc.tsv", "vertical_z_axis", xraise_dir / "z_kpc.tsv"),
    ]
    x_values = read_vector(xraise_dir / "x_kpc.tsv") if (xraise_dir / "x_kpc.tsv").exists() else None
    u_values = read_vector(xraise_dir / "u_kpc.tsv") if (xraise_dir / "u_kpc.tsv").exists() else None
    x_u_identical = "not_applicable"
    if x_values is not None and u_values is not None and x_values.shape == u_values.shape:
        x_u_identical = "true" if np.array_equal(x_values, u_values) else "false"

    out: list[dict[str, Any]] = []
    for axis_file, role, path in axes:
        if not path.exists():
            continue
        values = read_vector(path)
        diffs = np.diff(values)
        same_length = values.shape == baseline_x.shape
        allclose = bool(same_length and np.allclose(values, baseline_x, rtol=0.0, atol=1.0e-8))
        if axis_file in {"x_kpc.tsv", "u_kpc.tsv"} and view in {"45deg", "90deg"}:
            interpretation = (
                "For nonzero views xraise_grid_smoke writes the sky-horizontal axis to x_kpc "
                "and, additionally, u_kpc; x/u identity inside the product is expected."
            )
        elif axis_file == "z_kpc.tsv":
            interpretation = "Shared vertical axis; not implicated in vertical striping."
        else:
            interpretation = "Baseline sky x-axis."
        out.append(
            {
                "view": view,
                "axis_file": axis_file,
                "axis_role": role,
                "n": int(values.size),
                "min_kpc": f"{float(values[0]):.16g}",
                "max_kpc": f"{float(values[-1]):.16g}",
                "median_step_kpc": f"{float(np.median(diffs)):.16g}",
                "min_step_kpc": f"{float(diffs.min()):.16g}",
                "max_step_kpc": f"{float(diffs.max()):.16g}",
                "max_step_deviation_kpc": f"{float(np.max(np.abs(diffs - np.median(diffs)))):.16g}",
                "strictly_increasing": "true" if bool(np.all(diffs > 0.0)) else "false",
                "x_u_identical_in_view": x_u_identical,
                "same_length_as_0deg_x": "true" if same_length else "false",
                "allclose_to_0deg_x": "true" if allclose else "false",
                "interpretation": interpretation,
            }
        )
    return out


def collect_axis_rows(goal005_dir: Path, goal011_dir: Path, goal012_dir: Path) -> list[dict[str, Any]]:
    baseline_x = read_vector(goal005_dir / "xraise_grid/x_kpc.tsv")
    rows: list[dict[str, Any]] = []
    for view in ("0deg", "45deg", "90deg"):
        rows.extend(
            axis_rows_for_view(
                view=view,
                xraise_dir=view_xraise_dir(goal005_dir, goal011_dir, goal012_dir, view),
                baseline_x=baseline_x,
            )
        )
    return rows


def row_float(row: dict[str, Any], key: str) -> float:
    value = row[key]
    if value == "inf":
        return math.inf
    return float(value)


def recommendation_from_rows(striping_rows: list[dict[str, Any]], axis_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_view_layer = {(row["view"], row["layer"]): row for row in striping_rows}
    required_90 = [by_view_layer[("90deg", layer)] for layer in ("raw_xray", "corrected_xray", "correction_ratio")]
    required_45 = [by_view_layer[("45deg", layer)] for layer in ("raw_xray", "corrected_xray", "correction_ratio")]
    empty_90 = [row_float(row, "empty_column_fraction") for row in required_90]
    empty_45 = [row_float(row, "empty_column_fraction") for row in required_45]
    masks_match_raw = all(row["positive_mask_equal_to_raw"] == "true" for row in required_90)
    axis_identity_expected = any(
        row["view"] == "90deg"
        and row["axis_file"] == "u_kpc.tsv"
        and row["x_u_identical_in_view"] == "true"
        for row in axis_rows
    )

    if min(empty_90) >= 0.25 and max(empty_45) < 0.05 and masks_match_raw:
        label = "X_RAY_METHOD_REFINEMENT_FIRST"
        confidence = "high"
        diagnosis = (
            "90-degree raw, corrected, and correction-ratio X-ray maps share a large all-zero "
            "projected-column mask, while 45-degree X-ray maps do not. This points to a "
            "projection/binning occupancy issue at or near 90 degrees rather than display "
            "scaling, APEC/Gaunt correction, or a physical X-ray feature."
        )
        next_step = (
            "Write a local X-ray/projection-method refinement goal: reproduce the empty-bin "
            "case with a stretched synthetic grid, revise projected-axis/bin accumulation for "
            "near-90-degree views, and rerun only bounded existing-output post-processing if "
            "the local method test passes."
        )
    else:
        label = "INSUFFICIENT_LOCAL_EVIDENCE"
        confidence = "medium"
        diagnosis = (
            "Local metrics do not isolate the striping mechanism strongly enough to choose "
            "between projection/binning, upstream XRAiSE, or display."
        )
        next_step = "Add the smallest synthetic projection/binning reproduction test before choosing the next science branch."

    not_supported = (
        "The local evidence does not support treating the striping as display-only, "
        "as an APEC/Gaunt correction-only problem, as a physically meaningful cavity feature, "
        "or as a reason for Stas/Patrick escalation."
    )
    if axis_identity_expected:
        axis_note = (
            "The 90-degree x_kpc/u_kpc identity is expected from the current writer because "
            "nonzero projected views store the same sky-horizontal axis in both files; this "
            "identity is not itself suspicious."
        )
    else:
        axis_note = "The projected-axis file identity check did not match the expected current writer behavior."
    return {
        "recommendation_label": label,
        "confidence": confidence,
        "primary_diagnosis": diagnosis,
        "evidence_summary": (
            f"90deg empty-column fractions raw/corrected/ratio={empty_90}; "
            f"45deg empty-column fractions raw/corrected/ratio={empty_45}; "
            f"90deg X-ray masks all match raw={masks_match_raw}. {axis_note}"
        ),
        "not_supported_by_evidence": not_supported,
        "smallest_next_local_step": next_step,
        "q018_q019_status": (
            "Q-018/Q-019 can remain non-blocking review inputs; Goal 015 need not wait "
            "for them if it is framed as local X-ray/projection-method refinement."
        ),
    }


def plot_column_profiles(striping_rows: list[dict[str, Any]], goal011_dir: Path, goal012_dir: Path, output_png: Path) -> None:
    fig, axes = plt.subplots(4, 1, figsize=(9.0, 8.5), sharex=True, constrained_layout=True)
    layers = [
        ("raw_xray", "xray_1kev_raw_mjy_sr.tsv"),
        ("corrected_xray", "xray_1kev_xraise_corrected_mjy_sr.tsv"),
        ("correction_ratio", "xray_1kev_correction_ratio.tsv"),
        ("tracer_max", "tracer_max_los.tsv"),
    ]
    dirs = {
        "45deg": goal011_dir / "xraise_grid_45deg",
        "90deg": goal012_dir / "xraise_grid_90deg",
    }
    colors = {"45deg": "#2c7fb8", "90deg": "#d95f0e"}
    for ax, (layer, filename) in zip(axes, layers):
        for view, xraise_dir in dirs.items():
            values = read_matrix(xraise_dir / filename)
            positive_fraction = (values > 0.0).mean(axis=0)
            ax.plot(np.linspace(0.0, 1.0, positive_fraction.size), positive_fraction, lw=1.0, color=colors[view], label=view)
        ax.set_ylabel(layer)
        ax.set_ylim(-0.03, 1.03)
        ax.grid(alpha=0.25, lw=0.4)
    axes[0].legend(loc="lower right")
    axes[-1].set_xlabel("normalized projected-column index")
    fig.suptitle("Column positive-fraction profiles for 45 and 90 degree local assets", fontsize=12.5)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, dpi=180, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def build_diagnostic(*, goal005_dir: Path, goal011_dir: Path, goal012_dir: Path, output_dir: Path) -> dict[str, Any]:
    striping_rows = collect_striping_rows(goal005_dir, goal011_dir, goal012_dir)
    axis_rows = collect_axis_rows(goal005_dir, goal011_dir, goal012_dir)
    recommendation = recommendation_from_rows(striping_rows, axis_rows)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_rows(output_dir / "striping_diagnostics.csv", striping_rows, STRIPING_COLUMNS)
    write_rows(output_dir / "projection_axis_diagnostics.csv", axis_rows, AXIS_COLUMNS)
    write_rows(output_dir / "next_step_recommendation.csv", [recommendation], RECOMMENDATION_COLUMNS)
    plot_column_profiles(
        striping_rows,
        goal011_dir=goal011_dir,
        goal012_dir=goal012_dir,
        output_png=output_dir / "column_positive_fraction_profiles.png",
    )
    metadata = {
        "status": "complete_diagnostic",
        "recommendation_label": recommendation["recommendation_label"],
        "outputs": {
            "striping_diagnostics": display_path(output_dir / "striping_diagnostics.csv"),
            "projection_axis_diagnostics": display_path(output_dir / "projection_axis_diagnostics.csv"),
            "next_step_recommendation": display_path(output_dir / "next_step_recommendation.csv"),
            "column_positive_fraction_profiles": display_path(output_dir / "column_positive_fraction_profiles.png"),
        },
    }
    return metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--goal005-dir", type=Path, default=DEFAULT_GOAL005)
    parser.add_argument("--goal011-dir", type=Path, default=DEFAULT_GOAL011)
    parser.add_argument("--goal012-dir", type=Path, default=DEFAULT_GOAL012)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    metadata = build_diagnostic(
        goal005_dir=args.goal005_dir,
        goal011_dir=args.goal011_dir,
        goal012_dir=args.goal012_dir,
        output_dir=args.output_dir,
    )
    print(json.dumps(metadata, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
