from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path("scripts/science/diagnose_90deg_xray_striping.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("diagnose_90deg_xray_striping", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_striping_diagnostics_detect_empty_columns_and_mask_match() -> None:
    module = load_script_module()
    values = np.array(
        [
            [1.0, 0.0, 2.0, 0.0],
            [2.0, 0.0, 3.0, 0.0],
            [3.0, 0.0, 4.0, 0.0],
        ]
    )
    raw_mask = values > 0.0

    row = module.striping_diagnostics_for_layer(
        view="90deg",
        layer="corrected_xray",
        values=values,
        log_positive=True,
        raw_positive_mask=raw_mask,
    )

    assert row["empty_column_count"] == 2
    assert float(row["empty_column_fraction"]) == 0.5
    assert row["positive_mask_equal_to_raw"] == "true"


def test_axis_rows_mark_projected_x_u_identity_as_expected(tmp_path: Path) -> None:
    module = load_script_module()
    xraise = tmp_path / "xraise"
    xraise.mkdir()
    (xraise / "x_kpc.tsv").write_text("-1\n0\n1\n")
    (xraise / "u_kpc.tsv").write_text("-1\n0\n1\n")
    (xraise / "z_kpc.tsv").write_text("-2\n0\n2\n")
    baseline_x = np.array([-1.0, 0.0, 1.0])

    rows = module.axis_rows_for_view(view="90deg", xraise_dir=xraise, baseline_x=baseline_x)
    by_axis = {row["axis_file"]: row for row in rows}

    assert by_axis["u_kpc.tsv"]["x_u_identical_in_view"] == "true"
    assert by_axis["u_kpc.tsv"]["allclose_to_0deg_x"] == "true"
    assert "expected" in by_axis["u_kpc.tsv"]["interpretation"]


def test_recommendation_prefers_method_refinement_for_90deg_empty_xray_columns() -> None:
    module = load_script_module()

    def row(view: str, layer: str, empty: float, mask_match: str) -> dict[str, object]:
        return {
            "view": view,
            "layer": layer,
            "empty_column_fraction": str(empty),
            "positive_mask_equal_to_raw": mask_match,
        }

    striping_rows = []
    for layer in ("raw_xray", "corrected_xray", "correction_ratio"):
        striping_rows.append(row("45deg", layer, 0.02, "true"))
        striping_rows.append(row("90deg", layer, 0.42, "true"))
    axis_rows = [
        {
            "view": "90deg",
            "axis_file": "u_kpc.tsv",
            "x_u_identical_in_view": "true",
        }
    ]

    recommendation = module.recommendation_from_rows(striping_rows, axis_rows)

    assert recommendation["recommendation_label"] == "X_RAY_METHOD_REFINEMENT_FIRST"
    assert recommendation["confidence"] == "high"
