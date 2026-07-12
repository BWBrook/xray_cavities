import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/science/build_g_lo_guarded_continuation_completion.py"
REMOTE_STAGE = (
    ROOT
    / "docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/remote_stage"
)


def load_module():
    spec = importlib.util.spec_from_file_location("goal038_completion", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_builds_green_endpoint_summary_from_retrieved_evidence(tmp_path):
    module = load_module()
    module.build_completion_package(REMOTE_STAGE, tmp_path)

    metadata = json.loads(
        (tmp_path / "g_lo_guarded_continuation_completion_metadata.json").read_text()
    )
    assert metadata["status"] == "complete_endpoint_review"
    assert metadata["decision_label"] == "G_LO_GUARDED_CONTINUATION_REACHED_ENDPOINT_GREEN"
    assert metadata["job"]["exit_status"] == 0
    assert metadata["job"]["stageout_status"] == 1
    assert metadata["endpoint"]["fluid_restart_index"] == 10
    assert metadata["endpoint"]["particle_restart_index"] == 5000
    assert metadata["endpoint"]["particle_count"] == 197568
    assert metadata["watchdog"]["triggered"] is False
    assert metadata["watchdog"]["command_exit_code"] == 0


def test_rejects_failed_endpoint_validator(tmp_path):
    module = load_module()
    copied = tmp_path / "remote_stage"
    copied.mkdir()
    evidence = copied / "completion_evidence"
    evidence.mkdir()
    (evidence / "endpoint_validation.exit_code.txt").write_text("1\n")

    with pytest.raises(ValueError, match="endpoint validator did not pass"):
        module.build_completion_package(copied, tmp_path / "out")


def test_generated_tables_and_manifest_are_nonempty(tmp_path):
    module = load_module()
    module.build_completion_package(REMOTE_STAGE, tmp_path)

    expected = {
        "qstat_final.csv",
        "completion_summary.csv",
        "watchdog_summary.csv",
        "run_output_inventory_summary.csv",
        "next_step_recommendation.csv",
        "g_lo_guarded_continuation_completion_metadata.json",
        "local_asset_manifest.sha256",
    }
    assert expected <= {path.name for path in tmp_path.iterdir()}
    for name in expected:
        assert (tmp_path / name).stat().st_size > 0
