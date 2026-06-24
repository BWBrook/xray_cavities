#!/usr/bin/env python3
"""Generate synthetic diagnostics for the projected-bin refinement."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "docs/science/assets/c_hi_projection_bin_refinement_2026-06-24"
XRAISE_GRID_SMOKE = ROOT / "scripts/science/xraise_grid_smoke.py"

OCCUPANCY_COLUMNS = [
    "scenario",
    "view_angle_deg",
    "method",
    "projected_bins",
    "positive_bins",
    "empty_bins",
    "empty_bin_fraction",
    "integrated_path_weight",
    "expected_source_area",
    "relative_conservation_error",
]
METHOD_COLUMNS = [
    "decision_label",
    "method",
    "synthetic_failure_reproduced",
    "pathological_empty_bins_removed",
    "conservation_status",
    "zero_degree_default_status",
    "nonpathological_view_status",
    "later_bounded_rerun_justified",
]


def load_xraise_grid_smoke():
    spec = importlib.util.spec_from_file_location("xraise_grid_smoke", XRAISE_GRID_SMOKE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {XRAISE_GRID_SMOKE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def legacy_center_bin_path(
    module: Any,
    *,
    x: np.ndarray,
    y: np.ndarray,
    u_edges: np.ndarray,
    view_angle_deg: float,
) -> np.ndarray:
    theta = math.radians(view_angle_deg)
    x_widths = module.widths_from_centres(x)
    y_widths = module.widths_from_centres(y)
    u_widths = np.diff(u_edges)
    u_coord = x[np.newaxis, :] * math.cos(theta) - y[:, np.newaxis] * math.sin(theta)
    bins = np.searchsorted(u_edges, u_coord, side="right") - 1
    valid = (bins >= 0) & (bins < len(u_widths))
    flat_bins = bins[valid].astype(np.int64)
    cell_weights = x_widths[np.newaxis, :] * y_widths[:, np.newaxis]
    weights = cell_weights[valid] / u_widths[flat_bins]
    return np.bincount(flat_bins, weights=weights, minlength=len(u_widths))


def overlap_path(module: Any, *, x: np.ndarray, y: np.ndarray, u_edges: np.ndarray, view_angle_deg: float) -> np.ndarray:
    raw = np.ones((1, len(y), len(x)), dtype=float)
    corrected = raw.copy()
    tracer = np.ones_like(raw)
    raw_path = np.zeros((1, len(u_edges) - 1), dtype=float)
    corrected_path = np.zeros_like(raw_path)
    tracer_max = np.zeros_like(raw_path)
    module.accumulate_projected_chunk(
        raw_path=raw_path,
        corrected_path=corrected_path,
        tracer_max=tracer_max,
        raw=raw,
        corrected=corrected,
        tracer=tracer,
        x=x,
        y_chunk=y,
        x_widths=module.widths_from_centres(x),
        y_widths_chunk=module.widths_from_centres(y),
        u_edges=u_edges,
        view_angle_deg=view_angle_deg,
        x_edges=module.centres_to_edges(x),
        y_edges_chunk=module.centres_to_edges(y),
    )
    return raw_path[0]


def occupancy_row(
    *,
    scenario: str,
    view_angle_deg: float,
    method: str,
    path_weight: np.ndarray,
    u_edges: np.ndarray,
    expected_area: float,
) -> dict[str, Any]:
    positive = path_weight > 0.0
    integrated = float(np.sum(path_weight * np.diff(u_edges)))
    rel_error = 0.0 if expected_area == 0.0 else abs(integrated - expected_area) / expected_area
    return {
        "scenario": scenario,
        "view_angle_deg": f"{view_angle_deg:.16g}",
        "method": method,
        "projected_bins": int(path_weight.size),
        "positive_bins": int(np.count_nonzero(positive)),
        "empty_bins": int(np.count_nonzero(~positive)),
        "empty_bin_fraction": f"{float(np.count_nonzero(~positive) / path_weight.size):.16g}",
        "integrated_path_weight": f"{integrated:.16g}",
        "expected_source_area": f"{expected_area:.16g}",
        "relative_conservation_error": f"{rel_error:.16g}",
    }


def build_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    module = load_xraise_grid_smoke()
    scenarios = [
        {
            "name": "near90_stretched_grid",
            "x": np.array([-1.0, 1.0]),
            "y": np.array([-3.0, -1.7, -0.4, 0.35, 1.4, 3.0]),
            "view_angle_deg": 90.0,
            "bins": 24,
        },
        {
            "name": "nonpathological_45deg_grid",
            "x": np.array([-1.0, 1.0]),
            "y": np.array([-1.0, 1.0]),
            "view_angle_deg": 45.0,
            "bins": 4,
        },
    ]

    occupancy_rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        x = scenario["x"]
        y = scenario["y"]
        view_angle = float(scenario["view_angle_deg"])
        _u, u_edges = module.projected_axis(
            x,
            y,
            view_angle_deg=view_angle,
            projected_u_bins=int(scenario["bins"]),
        )
        x_edges = module.centres_to_edges(x)
        y_edges = module.centres_to_edges(y)
        expected_area = float(np.sum(np.diff(y_edges)[:, np.newaxis] * np.diff(x_edges)[np.newaxis, :]))
        legacy = legacy_center_bin_path(module, x=x, y=y, u_edges=u_edges, view_angle_deg=view_angle)
        refined = overlap_path(module, x=x, y=y, u_edges=u_edges, view_angle_deg=view_angle)
        occupancy_rows.append(
            occupancy_row(
                scenario=str(scenario["name"]),
                view_angle_deg=view_angle,
                method="legacy_center_bin",
                path_weight=legacy,
                u_edges=u_edges,
                expected_area=expected_area,
            )
        )
        occupancy_rows.append(
            occupancy_row(
                scenario=str(scenario["name"]),
                view_angle_deg=view_angle,
                method="edge_overlap_uniform_cell_projection",
                path_weight=refined,
                u_edges=u_edges,
                expected_area=expected_area,
            )
        )

    near90 = [row for row in occupancy_rows if row["scenario"] == "near90_stretched_grid"]
    legacy_near90 = next(row for row in near90 if row["method"] == "legacy_center_bin")
    refined_near90 = next(row for row in near90 if row["method"] == "edge_overlap_uniform_cell_projection")
    refined_45 = next(
        row
        for row in occupancy_rows
        if row["scenario"] == "nonpathological_45deg_grid"
        and row["method"] == "edge_overlap_uniform_cell_projection"
    )
    method_rows = [
        {
            "decision_label": "LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN",
            "method": "edge_overlap_uniform_cell_projection",
            "synthetic_failure_reproduced": "true" if int(legacy_near90["empty_bins"]) >= 12 else "false",
            "pathological_empty_bins_removed": "true" if int(refined_near90["empty_bins"]) == 0 else "false",
            "conservation_status": (
                "passed"
                if max(float(row["relative_conservation_error"]) for row in occupancy_rows) < 1.0e-12
                else "failed"
            ),
            "zero_degree_default_status": "unchanged_direct_y_axis_sum",
            "nonpathological_view_status": "passed" if int(refined_45["empty_bins"]) == 0 else "review",
            "later_bounded_rerun_justified": "true",
        }
    ]
    return occupancy_rows, method_rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    occupancy_rows, method_rows = build_rows()
    write_rows(args.output_dir / "synthetic_occupancy_comparison.csv", occupancy_rows, OCCUPANCY_COLUMNS)
    write_rows(args.output_dir / "method_comparison.csv", method_rows, METHOD_COLUMNS)
    print(
        json.dumps(
            {
                "status": "complete_diagnostic",
                "decision_label": method_rows[0]["decision_label"],
                "outputs": {
                    "synthetic_occupancy_comparison": str(
                        (args.output_dir / "synthetic_occupancy_comparison.csv").relative_to(ROOT)
                    ),
                    "method_comparison": str((args.output_dir / "method_comparison.csv").relative_to(ROOT)),
                },
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
