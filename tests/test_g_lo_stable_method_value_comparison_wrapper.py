from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_stable_method_value_comparison.pbs")


def test_wrapper_has_fixed_goal051_interface_and_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_lo_stmv" in text
    assert "#PBS -q normal" in text
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert "set -euo pipefail" in text
    for option in (
        "--cache",
        "--selection-csv",
        "--output-dir",
        "--expected-cache-sha256",
        "--expected-selection-sha256",
    ):
        assert option in text
    assert "--expected-selection-count" not in text
    for output_name in (
        "stable_method_value_selection.csv",
        "stable_method_value_unsmoothed_branches.npz",
        "stable_method_value_log_savgol_branches.npz",
        "stable_method_value_particle_comparison.csv",
        "stable_method_value_ordering.csv",
        "stable_method_value_cutoff_records.csv",
        "stable_method_value_gate_summary.csv",
        "stable_method_value_summary.json",
    ):
        assert output_name in text


def test_wrapper_binds_input_provenance_and_runtime_stack() -> None:
    text = WRAPPER.read_text()

    assert "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30" in text
    assert "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df" in text
    assert "e80252cf35ff5a06166240e2867d3d485aaf6956" in text
    assert "staged_inputs.sha256" in text
    assert "plutokore_commit.txt" in text
    assert "module load Anaconda3/2024.02-1" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "export OMP_NUM_THREADS=16" in text
    assert "export NUMBA_NUM_THREADS=16" in text
    for helper in (
        "diagnose_g_lo_stable_method_value.py",
        "diagnose_g_lo_full_loss_recurrence.py",
        "diagnose_g_lo_adiabatic_recovery.py",
        "diagnose_g_lo_pressure_method_value.py",
        "run_g_lo_radio_history_value.py",
        "g_lo_radio_method_value.py",
        "g_lo_particle_history.py",
    ):
        assert helper in text


def test_wrapper_archives_evidence_and_fails_closed() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert "another goal 051 run owns the stage lock" in lower
    assert "refusing to overwrite goal 051 output" in lower
    assert "archive_file_list.txt" in text
    assert 'tar -tzf "$archive_tmp"' in text
    assert "evidence_archived=1" in text
    assert "stable_method_value_science_gate=PASS" in text
    assert "stable_method_value_science_gate=FAIL" in text
    assert "stable_method_value_infrastructure=FAIL" in text
    assert "qsub" not in lower
    assert "mpirun" not in lower
    assert "raytrace" not in lower
    assert "rm -rf" not in lower


def test_wrapper_validates_summary_schema_and_exit_contract() -> None:
    text = WRAPPER.read_text()

    assert 'summary.get("status") != "diagnostic_complete"' in text
    assert 'summary.get("stable_gates", summary.get("gates"))' in text
    assert '"infrastructure_gates", summary.get("infrastructure")' in text
    assert 'decision not in {"PASS", "FAIL", "HOLD_FOR_CUTOFF_REVIEW"}' in text
    assert "HOLD_FOR_CUTOFF_REVIEW" in text
    assert 'diagnostic_rc" -eq 0' in text
    assert 'diagnostic_rc" -eq 3' in text
    assert 'exit 2' in text
    assert 'exit 3' in text
