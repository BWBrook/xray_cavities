from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path("scripts/science/build_conditional_endpoint_topology_application.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location(
        "build_conditional_endpoint_topology_application", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sensitivity_fixture() -> list[dict[str, str]]:
    return [
        {
            "percentile": "0.5",
            "residual_threshold": "-0.05",
            "mask_pixels": "50",
            "mask_fraction": "0.005",
            "significant_component_count_all": "3",
            "seeded_component_count": "1",
            "unlabelled_component_count": "2",
            "component_side_class_counts": "spans_negative_and_positive=1;negative_z=0;positive_z=0;unlabelled=2",
            "negative_seed_overlap_pixels": "6",
            "positive_seed_overlap_pixels": "6",
            "negative_seed_overlap_fraction": "0.01",
            "positive_seed_overlap_fraction": "0.01",
            "spanning_component_exists": "true",
            "side_specific_components_exist": "false",
            "observed_topology_class": "connected_envelope_single_system",
            "gate_status": "pass",
            "recommendation_consequence": "preserve_as_conditional_connected_residual_core_not_final_topology",
        },
        {
            "percentile": "1",
            "residual_threshold": "-0.04",
            "mask_pixels": "100",
            "mask_fraction": "0.01",
            "significant_component_count_all": "4",
            "seeded_component_count": "1",
            "unlabelled_component_count": "3",
            "component_side_class_counts": "spans_negative_and_positive=1;negative_z=0;positive_z=0;unlabelled=3",
            "negative_seed_overlap_pixels": "7",
            "positive_seed_overlap_pixels": "7",
            "negative_seed_overlap_fraction": "0.02",
            "positive_seed_overlap_fraction": "0.02",
            "spanning_component_exists": "true",
            "side_specific_components_exist": "false",
            "observed_topology_class": "connected_envelope_single_system",
            "gate_status": "pass",
            "recommendation_consequence": "preserve_as_conditional_connected_residual_core_not_final_topology",
        },
        {
            "percentile": "2",
            "residual_threshold": "-0.03",
            "mask_pixels": "200",
            "mask_fraction": "0.02",
            "significant_component_count_all": "5",
            "seeded_component_count": "1",
            "unlabelled_component_count": "4",
            "component_side_class_counts": "spans_negative_and_positive=1;negative_z=0;positive_z=0;unlabelled=4",
            "negative_seed_overlap_pixels": "8",
            "positive_seed_overlap_pixels": "8",
            "negative_seed_overlap_fraction": "0.03",
            "positive_seed_overlap_fraction": "0.03",
            "spanning_component_exists": "true",
            "side_specific_components_exist": "false",
            "observed_topology_class": "connected_envelope_single_system",
            "gate_status": "pass",
            "recommendation_consequence": "preserve_as_conditional_connected_residual_core_not_final_topology",
        },
        {
            "percentile": "3",
            "residual_threshold": "-0.02",
            "mask_pixels": "300",
            "mask_fraction": "0.03",
            "significant_component_count_all": "6",
            "seeded_component_count": "3",
            "unlabelled_component_count": "1",
            "component_side_class_counts": "spans_negative_and_positive=1;negative_z=0;positive_z=2;unlabelled=1",
            "negative_seed_overlap_pixels": "9",
            "positive_seed_overlap_pixels": "12",
            "negative_seed_overlap_fraction": "0.04",
            "positive_seed_overlap_fraction": "0.05",
            "spanning_component_exists": "true",
            "side_specific_components_exist": "true",
            "observed_topology_class": "ambiguous_needs_review",
            "gate_status": "fail",
            "recommendation_consequence": "broader_mask_mixes_connected_core_with_side_specific_structure",
        },
    ]


def component_fixture() -> list[dict[str, str]]:
    return [
        {
            "percentile": "1",
            "residual_threshold": "-0.04",
            "component_index": "1",
            "pixel_count": "40",
            "component_fraction_of_mask": "0.4",
            "component_fraction_of_total": "0.004",
            "negative_seed_overlap_pixels": "7",
            "positive_seed_overlap_pixels": "7",
            "unlabelled_overlap_pixels": "0",
            "side_class": "spans_negative_and_positive",
            "used_for_seeded_topology_classification": "true",
        },
        {
            "percentile": "1",
            "residual_threshold": "-0.04",
            "component_index": "2",
            "pixel_count": "60",
            "component_fraction_of_mask": "0.6",
            "component_fraction_of_total": "0.006",
            "negative_seed_overlap_pixels": "0",
            "positive_seed_overlap_pixels": "0",
            "unlabelled_overlap_pixels": "60",
            "side_class": "unlabelled",
            "used_for_seeded_topology_classification": "false",
        },
    ]


def test_builds_selected_conditional_application_summary_without_final_freeze() -> None:
    module = load_script_module()

    row = module.conditional_application_summary_row(
        sensitivity_fixture(),
        selected_percentile="1",
        figure_path="docs/science/assets/goal026/residual_threshold_sensitivity.png",
    )

    assert row["selected_threshold_percentile"] == "1"
    assert row["selection_status"] == "selected_conditional_connected_core"
    assert row["observed_topology_class"] == "connected_envelope_single_system"
    assert row["final_observational_topology_frozen"] == "false"
    assert row["supporting_narrow_thresholds"] == "0.5;2"
    assert row["ambiguity_bound_thresholds"] == "3"
    assert row["accepted_product_relationship"] == "sits_beside_does_not_replace_goal005_goal007"


def test_carries_forward_threshold_roles_and_selected_components() -> None:
    module = load_script_module()

    carried = module.threshold_sensitivity_carried_forward_rows(
        sensitivity_fixture(),
        selected_percentile="1",
    )
    components = module.selected_threshold_component_rows(
        component_fixture(),
        selected_percentile="1",
    )

    roles = {row["percentile"]: row["application_role"] for row in carried}
    assert roles == {
        "0.5": "supporting_narrow_threshold_robustness",
        "1": "selected_representative_conditional_application",
        "2": "supporting_narrow_threshold_robustness",
        "3": "ambiguity_bound_threshold",
    }
    assert components[0]["application_role"] == "selected_connected_seeded_component"
    assert components[1]["application_role"] == "unlabelled_residual_island_caveat"
