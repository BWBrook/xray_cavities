from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np


SCRIPT = Path("scripts/science/build_residual_threshold_sensitivity_review.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "build_residual_threshold_sensitivity_review", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def two_side_labels(shape: tuple[int, int]) -> np.ndarray:
    labels = np.zeros(shape, dtype=int)
    labels[:, : shape[1] // 2] = -1
    labels[:, shape[1] // 2 :] = 1
    return labels


def test_sensitivity_tables_capture_connected_core_then_ambiguous_broader_mask() -> None:
    module = load_script_module()
    residual = np.zeros((10, 10), dtype=float)
    residual[4:6, 4:6] = -3.0
    residual[0:3, 0:3] = -2.0
    residual[7:10, 7:10] = -2.0
    residual[0:2, 7:9] = -2.0
    side_labels = two_side_labels(residual.shape)
    side_labels[0:2, 7:9] = 0

    summary_rows, component_rows, overlap_rows = module.sensitivity_tables_from_arrays(
        residual,
        side_labels,
        percentiles=[3.0, 25.0],
        min_component_pixels=3,
        connectivity=4,
    )

    assert [row["percentile"] for row in summary_rows] == ["3", "25"]
    assert summary_rows[0]["observed_topology_class"] == "connected_envelope_single_system"
    assert summary_rows[0]["spanning_component_exists"] == "true"
    assert summary_rows[0]["side_specific_components_exist"] == "false"
    assert summary_rows[1]["observed_topology_class"] == "ambiguous_needs_review"
    assert summary_rows[1]["spanning_component_exists"] == "true"
    assert summary_rows[1]["side_specific_components_exist"] == "true"
    assert int(summary_rows[1]["unlabelled_component_count"]) >= 1

    side_classes = {row["side_class"] for row in component_rows}
    assert side_classes >= {
        "spans_negative_and_positive",
        "negative_z",
        "positive_z",
        "unlabelled",
    }
    assert {row["side"] for row in overlap_rows} == {"negative_z", "positive_z"}


def test_recommendation_preserves_conditional_connected_core_without_final_freeze() -> None:
    module = load_script_module()
    rows = [
        {
            "percentile": "1",
            "observed_topology_class": "connected_envelope_single_system",
            "gate_status": "pass",
        },
        {
            "percentile": "2",
            "observed_topology_class": "connected_envelope_single_system",
            "gate_status": "pass",
        },
        {
            "percentile": "5",
            "observed_topology_class": "ambiguous_needs_review",
            "gate_status": "fail",
        },
    ]

    label, recommendation = module.decision_from_summary(rows)

    assert label == "CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL"
    assert recommendation == "bounded_conditional_endpoint_topology_application_package"
