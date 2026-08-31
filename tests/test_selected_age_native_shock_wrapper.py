from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/kunanyi/four_case_selected_age_native_shock.pbs"


def test_wrapper_runs_complete_prespecified_surface() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l walltime=48:00:00" in text
    assert "#PBS -l select=1:ncpus=2:mpiprocs=1:mem=128gb" in text
    assert "run_pair C-HI C-LO" in text
    assert "run_pair G-HI G-LO" in text
    assert "10 20 30 40 50" in text
    assert "G-HI" in text and "10 20 30 40\n" in text
    assert "G-HI/50 excluded" in text


def test_wrapper_calibrates_controls_without_calling_them_matched_subtraction() -> None:
    text = WRAPPER.read_text()
    assert "cluster_control_thresholds.csv" in text
    assert "group_control_thresholds.csv" in text
    assert "--sample-stride 4" in text
    assert "control_joint_exceedance_fraction" in text
    assert "baseline_h5" in text
    assert "baseline_timestep" in text
    assert "declare -n" not in text
    assert '${#CLUSTER_CONTROLS[@]}' in text
    assert '${#GROUP_CONTROLS[@]}' in text


def test_wrapper_preserves_fail_closed_results_and_compact_archive() -> None:
    text = WRAPPER.read_text()
    assert "unresolved_bilateral_gate" in text
    assert "unresolved_non_supersonic_front" in text
    assert "unresolved_front_extent_mismatch" in text
    assert "primary_bipolar_rows != 19" in text
    assert '"mask_volume_kpc3"' in text
    assert '"volume_kpc3"' not in text
    assert "--files-from" in text
    assert "find ./C-HI ./C-LO ./G-HI ./G-LO ./calibration ./logs -type f" in text
    assert "data.*.flt.h5" not in text.split("tar -czf", 1)[1]


def test_wrapper_refuses_overwrite_and_stops_on_case_failure() -> None:
    text = WRAPPER.read_text()
    assert "set -euo pipefail" in text
    assert "refusing to overwrite Goal 067 surface" in text
    assert "Goal 067 case pair failed" in text
    assert "sha256sum --check" in text
