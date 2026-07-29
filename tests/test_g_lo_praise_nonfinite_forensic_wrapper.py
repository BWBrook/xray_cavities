from pathlib import Path
import subprocess


ROOT = Path(__file__).parents[1]
WRAPPER = ROOT / "scripts/kunanyi/g_lo_praise_nonfinite_forensic.pbs"


def test_forensic_wrapper_is_valid_bash() -> None:
    result = subprocess.run(["bash", "-n", str(WRAPPER)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_forensic_wrapper_binds_inputs_and_accepts_blocked_decision() -> None:
    text = WRAPPER.read_text()
    assert "EXPECTED_CACHE_SHA256" in text
    assert "EXPECTED_AFFECTED_ROWS_SHA256" in text
    assert "CUTOFF_ZERO_POLICY_ELIGIBLE" in text
    assert "PRAISE_NUMERICS_BLOCKED" in text
    assert "NO_NONFINITE_REPRODUCED" in text
    assert "archive_file_list.txt" in text
    assert "--expected-single-record-rows 48" in text
    assert "pressure_method_particle_comparison.csv" not in text
