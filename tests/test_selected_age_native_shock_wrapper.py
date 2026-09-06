from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/kunanyi/four_case_selected_age_native_shock.pbs"


def test_wrapper_runs_complete_prespecified_surface() -> None:
    text = WRAPPER.read_text()
    assert "#PBS -l walltime=12:00:00" in text
    assert "#PBS -l select=1:ncpus=2:mpiprocs=1:mem=128gb" in text
    assert "run_pair C-HI C-LO" in text
    assert "run_pair G-HI G-LO" in text
    assert "10 20 30 40 50" in text
    assert "G-HI" in text and "10 20 30 40\n" in text
    assert "G-HI/50 excluded" in text


def test_wrapper_reuses_tracer_independent_controls_and_runs_synthetic_checks() -> None:
    text = WRAPPER.read_text()
    assert "cluster_control_thresholds.csv" in text
    assert "group_control_thresholds.csv" in text
    assert "python -m pytest" in text
    assert "control_joint_exceedance_fraction" in text
    assert "baseline_h5" in text
    assert "baseline_timestep" in text
    assert "declare -n" not in text
    assert 'cp "$INPUT_ROOT/calibration/cluster_control_thresholds.csv"' in text
    assert 'cp "$INPUT_ROOT/calibration/group_control_thresholds.csv"' in text


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
    assert "refusing to overwrite Q-029 surface" in text
    assert "Q-029 case pair failed" in text
    assert "sha256sum --check" in text


def test_wrapper_validator_uses_emitted_energy_schema_and_validates_native_products() -> None:
    import ast
    import re
    import sys

    sys.path.insert(0, str(ROOT / "scripts/science"))
    from snapshot_shock_energy import empty_shock_energy

    text = WRAPPER.read_text()
    fields = ast.literal_eval(re.search(r"energy_fields = (\([\s\S]*?\))", text).group(1))
    assert set(fields) <= set(empty_shock_energy())
    assert 'validate_selected_age_native_refresh.py' in text
    assert '--census-root "$INPUT_ROOT/native_census"' in text
    assert './native_strict_equivalence.json' in text
    assert 'index < 10 else root_b' in text
    assert 'np.array_equal' in text
