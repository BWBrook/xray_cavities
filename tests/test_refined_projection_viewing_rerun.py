from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/build_refined_projection_viewing_rerun.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_refined_projection_viewing_rerun", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_matrix(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savetxt(path, values, delimiter="\t")


def write_product(product_dir: Path, *, view_angle: float, accumulator: str) -> None:
    metadata = {
        "projection": {
            "view_angle_deg": view_angle,
            "projected_accumulation": accumulator,
            "sky_horizontal_bins": 4,
            "sky_horizontal_min_kpc": -2.0,
            "sky_horizontal_max_kpc": 2.0,
        },
        "raw_stats_mjy_sr": {
            "finite_cells": 8,
            "positive_cells": 8,
            "min": 1.0,
            "max": 4.0,
            "sum": 20.0,
        },
        "corrected_stats_mjy_sr": {
            "finite_cells": 8,
            "positive_cells": 8,
            "min": 2.0,
            "max": 8.0,
            "sum": 40.0,
        },
        "correction_ratio_stats": {
            "finite_cells": 8,
            "positive_cells": 8,
            "min": 2.0,
            "max": 2.0,
            "sum": 16.0,
        },
        "input_h5": "/scratch/input.h5",
        "timestep": "Timestep_51",
    }
    product_dir.mkdir(parents=True, exist_ok=True)
    (product_dir / "xraise_grid_smoke_metadata.json").write_text(json.dumps(metadata))
    write_csv(
        product_dir / "xraise_grid_smoke_summary.csv",
        [
            {"metric": "raw_xray_sum", "value": "20.0", "unit": "mJy sr^-1 pixels"},
            {"metric": "corrected_xray_sum", "value": "40.0", "unit": "mJy sr^-1 pixels"},
            {"metric": "correction_ratio_positive_sum", "value": "16.0", "unit": "dimensionless pixels"},
            {"metric": "raw_xray_max", "value": "4.0", "unit": "mJy sr^-1"},
        ],
        ["metric", "value", "unit"],
    )
    write_csv(
        product_dir / "refined_projection_empty_columns.csv",
        [
            {"view": f"{int(view_angle)}deg", "layer": "raw_xray", "empty_columns": 0, "empty_column_fraction": 0},
            {
                "view": f"{int(view_angle)}deg",
                "layer": "corrected_xray",
                "empty_columns": 0,
                "empty_column_fraction": 0,
            },
            {
                "view": f"{int(view_angle)}deg",
                "layer": "correction_ratio",
                "empty_columns": 0,
                "empty_column_fraction": 0,
            },
        ],
        ["view", "layer", "empty_columns", "empty_column_fraction"],
    )
    raw = np.ones((2, 4), dtype=float)
    write_matrix(product_dir / "xray_1kev_raw_mjy_sr.tsv", raw)
    write_matrix(product_dir / "xray_1kev_xraise_corrected_mjy_sr.tsv", raw * 2.0)
    write_matrix(product_dir / "xray_1kev_correction_ratio.tsv", raw * 2.0)


def test_projection_metric_rows_require_refined_accumulator(tmp_path: Path) -> None:
    module = load_script_module()
    product_root = tmp_path / "remote"
    write_product(product_root / "xraise_grid_90deg_refined", view_angle=90.0, accumulator="legacy_center_bin")
    write_product(
        product_root / "xraise_grid_45deg_refined",
        view_angle=45.0,
        accumulator=module.EXPECTED_ACCUMULATOR,
    )

    with pytest.raises(ValueError, match="projected_accumulation"):
        module.projection_metric_rows(product_root)


def test_empty_column_comparison_reports_removed_artifact(tmp_path: Path) -> None:
    module = load_script_module()
    product_root = tmp_path / "remote"
    write_product(
        product_root / "xraise_grid_90deg_refined",
        view_angle=90.0,
        accumulator=module.EXPECTED_ACCUMULATOR,
    )
    write_product(
        product_root / "xraise_grid_45deg_refined",
        view_angle=45.0,
        accumulator=module.EXPECTED_ACCUMULATOR,
    )
    striping = tmp_path / "striping.csv"
    rows = []
    for view, empty in (("90deg", 2), ("45deg", 1)):
        for layer in module.LAYER_FILES:
            rows.append(
                {
                    "view": view,
                    "layer": layer,
                    "matrix_shape": "2x4",
                    "empty_column_count": empty,
                    "empty_column_fraction": empty / 4.0,
                    "positive_mask_equal_to_raw": "true",
                }
            )
    write_csv(
        striping,
        rows,
        [
            "view",
            "layer",
            "matrix_shape",
            "empty_column_count",
            "empty_column_fraction",
            "positive_mask_equal_to_raw",
        ],
    )

    comparison = module.empty_column_comparison_rows(product_root, striping)
    corrected90 = next(row for row in comparison if row["view"] == "90deg" and row["layer"] == "corrected_xray")

    assert corrected90["accepted_empty_columns"] == 2
    assert corrected90["refined_empty_columns"] == 0
    assert corrected90["refined_positive_columns"] == 4
    assert corrected90["assessment"] == "empty_column_artifact_removed"


def test_summary_comparison_preserves_sum_conservation_assessment(tmp_path: Path) -> None:
    module = load_script_module()
    product_root = tmp_path / "remote"
    accepted_90 = tmp_path / "accepted90"
    accepted_45 = tmp_path / "accepted45"
    write_product(
        product_root / "xraise_grid_90deg_refined",
        view_angle=90.0,
        accumulator=module.EXPECTED_ACCUMULATOR,
    )
    write_product(
        product_root / "xraise_grid_45deg_refined",
        view_angle=45.0,
        accumulator=module.EXPECTED_ACCUMULATOR,
    )
    for accepted in (accepted_90, accepted_45):
        write_csv(
            accepted / "xraise_grid_smoke_summary.csv",
            [
                {"metric": "raw_xray_sum", "value": "20.0", "unit": "mJy sr^-1 pixels"},
                {"metric": "corrected_xray_sum", "value": "40.0", "unit": "mJy sr^-1 pixels"},
                {"metric": "correction_ratio_positive_sum", "value": "8.0", "unit": "dimensionless pixels"},
            ],
            ["metric", "value", "unit"],
        )

    rows = module.summary_comparison_rows(product_root, {"90deg": accepted_90, "45deg": accepted_45})
    raw90 = next(row for row in rows if row["view"] == "90deg" and row["metric"] == "raw_xray_sum")
    ratio90 = next(
        row for row in rows if row["view"] == "90deg" and row["metric"] == "correction_ratio_positive_sum"
    )

    assert raw90["relative_delta_fraction"] == "0"
    assert raw90["assessment"] == "conserved_within_roundoff"
    assert ratio90["relative_delta_fraction"] == "1"
    assert ratio90["assessment"] == "positive_pixel_support_expanded"
