from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path("scripts/science/build_refined_viewing_angle_consolidation.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_refined_viewing_angle_consolidation", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_historical_vs_refined_rows_mark_future_supersession() -> None:
    module = load_script_module()
    empty_rows = []
    for view, accepted in (("45deg", 22), ("90deg", 400)):
        for layer in ("raw_xray", "corrected_xray", "correction_ratio"):
            empty_rows.append(
                {
                    "view": view,
                    "layer": layer,
                    "accepted_empty_columns": str(accepted),
                    "refined_empty_columns": "0",
                }
            )
    scalar_rows = []
    for view in ("45deg", "90deg"):
        for metric, delta in (
            ("raw_xray_sum", "0"),
            ("corrected_xray_sum", "1e-15"),
            ("raw_xray_max", "0.001"),
            ("corrected_xray_max", "0.002"),
            ("correction_ratio_positive_sum", "0.7"),
        ):
            scalar_rows.append({"view": view, "metric": metric, "relative_delta_fraction": delta})

    rows = module.historical_vs_refined_rows(empty_rows, scalar_rows)
    by_view = {row["view"]: row for row in rows}

    assert by_view["90deg"]["corrected_empty_columns_historical"] == "400"
    assert by_view["90deg"]["corrected_empty_columns_refined"] == "0"
    assert by_view["90deg"]["future_evidence_status"] == "superseded_by_refined_projection_product"
    assert by_view["45deg"]["historical_goal"] == "Goal 011"
    assert "conserving raw/corrected" in by_view["45deg"]["interpretation"]


def test_trio_context_keeps_zero_degree_as_unchanged_baseline() -> None:
    module = load_script_module()
    summary = {
        "raw_xray_max": {"value": "10"},
        "corrected_xray_max": {"value": "20"},
        "raw_xray_sum": {"value": "100"},
        "corrected_xray_sum": {"value": "200"},
        "correction_ratio_positive_max": {"value": "2"},
        "correction_ratio_positive_sum": {"value": "50"},
    }
    refined = [
        {
            "view": "45deg",
            "view_angle_deg": "45",
            "projected_accumulation": "edge_overlap_uniform_cell_projection",
            "raw_max_mjy_sr": "4",
            "corrected_max_mjy_sr": "5",
            "raw_sum_mjy_sr_pixels": "40",
            "corrected_sum_mjy_sr_pixels": "50",
            "correction_ratio_max": "2.1",
            "correction_ratio_sum": "51",
        },
        {
            "view": "90deg",
            "view_angle_deg": "90",
            "projected_accumulation": "edge_overlap_uniform_cell_projection",
            "raw_max_mjy_sr": "8",
            "corrected_max_mjy_sr": "10",
            "raw_sum_mjy_sr_pixels": "80",
            "corrected_sum_mjy_sr_pixels": "100",
            "correction_ratio_max": "2.2",
            "correction_ratio_sum": "52",
        },
    ]

    rows = module.trio_context_rows(goal005_summary=summary, refined_metrics=refined)
    by_view = {row["view"]: row for row in rows}

    assert by_view["0deg"]["product_status"] == "accepted_unchanged_baseline"
    assert by_view["0deg"]["corrected_xray_sum_ratio_to_0deg"] == "1"
    assert by_view["45deg"]["product_status"] == "refined_projection_product"
    assert by_view["45deg"]["corrected_xray_sum_ratio_to_0deg"] == "0.25"
    assert by_view["90deg"]["future_use"] == "preferred future viewing-angle evidence"


def test_next_step_readiness_recommends_planning_not_running() -> None:
    module = load_script_module()
    rows = module.next_step_readiness_rows()

    assert rows[0]["option"] == "tightly_bounded_c_hi_source_age_sampling_after_maintenance"
    assert rows[0]["readiness_label"] == "recommended_next_planning_goal"
    assert rows[0]["compute_timing"] == "prepare_plan_now_run_after_maintenance"
    assert "defer" in rows[-1]["recommended_action"]
