from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT = Path("scripts/science/build_source_age_sampling_plan.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_source_age_sampling_plan", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_candidate_rows_distinguish_segment_context_from_final_production() -> None:
    module = load_script_module()
    rows = module.candidate_snapshot_rows()
    by_id = {row["candidate_id"]: row for row in rows}

    assert by_id["early_segment_output0008"]["time_myr"] == "4.99943585081067"
    assert (
        by_id["early_segment_output0008"]["execution_readiness"]
        == "not_default_goal018_execution_target_until_fullgrid_equivalent_is_verified"
    )
    assert by_id["fullgrid_prod64_output0046"]["recommended_role"] == "recommended_first_pass_new_sample"
    assert by_id["fullgrid_prod64_output0049"]["recommended_role"] == "recommended_first_pass_new_sample"
    assert by_id["fullgrid_prod64_output0051"]["recommended_role"] == "accepted_endpoint_control_reuse_not_rerun_by_default"
    assert by_id["fullgrid_prod64_output0051"]["execution_readiness"] == "accepted_control_already_processed"


def test_proposed_sampling_plan_is_bounded_and_planning_only() -> None:
    module = load_script_module()
    rows = module.proposed_sampling_plan_rows()
    new_samples = [row for row in rows if row["phase"] == "first_pass_new_sample"]
    by_step = {row["plan_step"]: row for row in rows}

    assert [row["output_index"] for row in new_samples] == ["46", "49"]
    assert all(row["views"] == "0deg;45deg;90deg" for row in new_samples)
    assert by_step["1"]["run_action"] == "verify_only_before_any_submission"
    assert by_step["4"]["run_action"] == "reuse_accepted_control_surface"
    assert by_step["5"]["execution_status"] == "held"
    assert all(row["execution_status"] != "authorized_to_run_now" for row in rows)


def test_contract_and_metadata_preserve_no_execution_and_caveats() -> None:
    module = load_script_module()
    contract = {row["contract_item"]: row for row in module.post_maintenance_contract_rows()}
    risks = {row["risk_id"]: row for row in module.risk_and_caveat_rows()}
    metadata = module.metadata()

    assert contract["authorization"]["required"] == "yes"
    assert "Goal 018 authorizes planning only" in contract["authorization"]["validation_or_stop_rule"]
    assert contract["pbs_stop_rule"]["contract_value"].startswith("stage, submit one bounded")
    assert risks["level3_gravity"]["status"] == "blocked_missing_potential"
    assert risks["sparse_radio_observable_status"]["status"] == "diagnostic_only"
    assert metadata["no_execution_authorized"] is True
    assert metadata["recommended_design"]["nonzero_view_accumulator"] == module.REFINED_ACCUMULATOR
