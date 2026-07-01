from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/hybrid_xray_cavity_topology.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("hybrid_xray_cavity_topology", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def two_side_seed_labels(shape: tuple[int, int]) -> np.ndarray:
    labels = np.zeros(shape, dtype=int)
    labels[:, : shape[1] // 2] = -1
    labels[:, shape[1] // 2 :] = 1
    return labels


def test_classifies_clean_two_lobe_synthetic_case_and_preserves_side_labels() -> None:
    module = load_script_module()
    xray = np.ones((12, 16), dtype=float)
    xray[3:6, 3:6] = 0.2
    xray[3:6, 10:13] = 0.2
    side_labels = two_side_seed_labels(xray.shape)

    result = module.classify_hybrid_topology(
        xray,
        side_labels,
        parameters=module.TopologyParameters(
            cavity_fraction_of_background=0.5,
            min_component_pixels=4,
            bridge_connectivity=4,
        ),
        case_id="two_lobe_fixture",
    )

    assert result.topology_class == "two_separate_cavities"
    assert result.gate_status == "pass"
    assert result.significant_component_count == 2
    assert result.side_label_summary["negative_z"]["seed_pixels"] == 96
    assert result.side_label_summary["positive_z"]["seed_pixels"] == 96
    assert result.parameters["cavity_fraction_of_background"] == "0.5"
    assert result.parameters["bridge_connectivity"] == "4"


def test_classifies_connected_envelope_separately_from_side_labels() -> None:
    module = load_script_module()
    xray = np.ones((12, 16), dtype=float)
    xray[3:6, 3:13] = 0.2
    side_labels = two_side_seed_labels(xray.shape)

    result = module.classify_hybrid_topology(
        xray,
        side_labels,
        parameters=module.TopologyParameters(
            cavity_fraction_of_background=0.5,
            min_component_pixels=4,
            bridge_connectivity=4,
        ),
        case_id="connected_fixture",
    )

    assert result.topology_class == "connected_envelope_single_system"
    assert result.gate_status == "pass"
    assert result.significant_component_count == 1
    assert result.component_side_classes == ["spans_negative_and_positive"]
    assert set(result.side_label_summary) == {"negative_z", "positive_z"}


def test_returns_ambiguous_result_or_raises_when_requested() -> None:
    module = load_script_module()
    xray = np.ones((12, 16), dtype=float)
    xray[3:6, 3:6] = 0.2
    side_labels = two_side_seed_labels(xray.shape)
    parameters = module.TopologyParameters(
        cavity_fraction_of_background=0.5,
        min_component_pixels=4,
        bridge_connectivity=4,
    )

    result = module.classify_hybrid_topology(
        xray,
        side_labels,
        parameters=parameters,
        case_id="one_side_only_fixture",
    )
    assert result.topology_class == "ambiguous_needs_review"
    assert result.gate_status == "fail"
    assert "does not satisfy" in result.reason

    with pytest.raises(module.AmbiguousTopologyError):
        module.classify_hybrid_topology(
            xray,
            side_labels,
            parameters=parameters,
            case_id="one_side_only_fixture",
            fail_on_ambiguous=True,
        )


def test_rejects_unsupported_inputs_before_classification() -> None:
    module = load_script_module()
    xray = np.ones((4, 5), dtype=float)
    side_labels = np.ones((4, 4), dtype=int)

    with pytest.raises(ValueError, match="same shape"):
        module.classify_hybrid_topology(xray, side_labels)

    bad_labels = np.zeros((4, 5), dtype=int)
    with pytest.raises(ValueError, match="both -1 and 1"):
        module.classify_hybrid_topology(xray, bad_labels)


def test_synthetic_gate_rows_are_deterministic_and_machine_readable() -> None:
    module = load_script_module()

    case_rows, result_rows, parameter_rows = module.synthetic_gate_tables()

    assert [row["case_id"] for row in case_rows] == [
        "synthetic_two_separate_cavities",
        "synthetic_connected_envelope_single_system",
        "synthetic_one_side_only_ambiguous",
    ]
    assert {row["observed_topology_class"] for row in result_rows} == {
        "two_separate_cavities",
        "connected_envelope_single_system",
        "ambiguous_needs_review",
    }
    assert any(row["gate_status"] == "fail" for row in result_rows)
    assert {row["parameter"] for row in parameter_rows} >= {
        "cavity_fraction_of_background",
        "min_component_pixels",
        "bridge_connectivity",
        "side_labels",
        "classification_rule",
    }


def test_classifies_direct_cavity_mask_without_rethresholding_xray() -> None:
    module = load_script_module()
    mask = np.zeros((6, 8), dtype=bool)
    mask[2:4, 2:6] = True
    side_labels = two_side_seed_labels(mask.shape)

    result = module.classify_hybrid_topology_from_mask(
        mask,
        side_labels,
        parameters=module.TopologyParameters(min_component_pixels=4, bridge_connectivity=4),
        case_id="direct_mask_fixture",
    )

    assert result.topology_class == "connected_envelope_single_system"
    assert result.component_side_classes == ["spans_negative_and_positive"]
    assert result.cavity_candidate_pixels == 8


def test_direct_mask_can_ignore_unseeded_components_for_seeded_topology() -> None:
    module = load_script_module()
    mask = np.zeros((8, 10), dtype=bool)
    mask[3:5, 3:7] = True
    mask[0:2, 0:2] = True
    side_labels = two_side_seed_labels(mask.shape)
    side_labels[0:2, 0:2] = 0

    result = module.classify_hybrid_topology_from_mask(
        mask,
        side_labels,
        parameters=module.TopologyParameters(min_component_pixels=4, bridge_connectivity=4),
        case_id="direct_mask_with_unseeded_island",
        ignore_unlabelled_components=True,
    )

    assert result.topology_class == "connected_envelope_single_system"
    assert result.significant_component_count == 1
    assert result.component_side_classes == ["spans_negative_and_positive"]


def test_derives_side_seed_labels_from_tracer_threshold_and_z_axis() -> None:
    module = load_script_module()
    tracer = np.array(
        [
            [0.0, 0.01, 0.0],
            [0.02, 0.0, 0.0],
            [0.0, 0.0, 0.03],
        ]
    )
    z_kpc = np.array([-1.0, 0.0, 1.0])

    labels = module.derive_tracer_side_seed_labels(
        tracer,
        z_kpc,
        tracer_threshold=5.0e-3,
    )

    np.testing.assert_array_equal(labels, np.array([[0, -1, 0], [0, 0, 0], [0, 0, 1]]))


def test_unsharp_residual_percentile_mask_selects_dark_residual_core() -> None:
    module = load_script_module()
    xray = np.ones((7, 7), dtype=float)
    xray[3, 3] = 0.1

    residual = module.boxcar_log_residual(xray, boxcar_pixels=3)
    mask, threshold = module.low_residual_percentile_mask(residual, percentile=1.0)

    assert residual[3, 3] < 0.0
    assert mask[3, 3]
    assert threshold < 0.0
