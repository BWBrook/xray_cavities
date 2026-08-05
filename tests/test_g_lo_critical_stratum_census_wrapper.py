from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_critical_stratum_census.pbs")


def test_wrapper_declares_goal053_resources_and_inputs() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_lo_strcen" in text
    assert "#PBS -q normal" in text
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert "set -euo pipefail" in text
    assert "/u/bwbrook/codex_kunanyi/goal053_g_lo_critical_stratum_census" in text
    assert "/scratch/bwbrook/xray_cavities_analysis/2026-07-30-g-lo-critical-stratum-census" in text
    assert "g_lo_critical_stratum_census_2026-07-30.tar.gz" in text
    for option in (
        "--cache",
        "--affected-rows-csv",
        "--original-selection-csv",
        "--original-comparison-csv",
        "--output-dir",
        "--expected-cache-sha256",
        "--expected-affected-rows-sha256",
        "--expected-original-selection-sha256",
        "--expected-census-count",
        "--target-stratum",
    ):
        assert option in text


def test_wrapper_pins_provenance_runtime_and_contract() -> None:
    text = WRAPPER.read_text()

    for value in (
        "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30",
        "85caef2184edd7786e4d791fd52e77e422269bb6a156a48047d3c7901e4d79f2",
        "35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df",
        "5fa466a1db5450921cd4b95785c0b949a499fd4457cc62da18333061dee8ebeb",
        "e80252cf35ff5a06166240e2867d3d485aaf6956",
        "affected=1|trim=0|length_q=0|injection_q=0|range_q=1|shock=post_injection_recent",
    ):
        assert value in text
    assert "EXPECTED_CENSUS_COUNT:-262" in text
    assert "EXPECTED_ORACLE_COUNT:-17" in text
    assert "EXPECTED_CERTAINTY_COUNT:-13" in text
    assert "EXPECTED_ORDINARY_COUNT:-249" in text
    assert "module load Anaconda3/2024.02-1" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert 'PYTHON_COMPAT="${PYTHON_COMPAT:-$STAGE_ROOT/scripts/kunanyi/python_compat}"' in text
    assert 'PYTHONPATH="$PYTHON_COMPAT:$PLUTOKORE_SOURCE/src:$STAGE_ROOT' in text
    assert "export OMP_NUM_THREADS=16" in text
    assert "export NUMBA_NUM_THREADS=16" in text
    assert "plutokore_commit.txt" in text
    assert "staged_inputs.sha256" in text
    assert "EXPECTED_ORIGINAL_COMPARISON_SHA256" in text


def test_wrapper_validates_outputs_and_archives_only_stable_files() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert "another goal 053 run owns the stage lock" in lower
    assert "refusing to overwrite goal 053 output" in lower
    assert "archive_file_list.txt" in text
    assert 'tar -tzf "$archive_tmp"' in text
    assert "evidence_archived=1" in text
    assert "census_count" in text
    assert "oracle_count" in text
    assert "frequency contract: 0.15, 1.4 GHz" in text
    assert "0.15" in text and "1.4" in text
    assert "critical_stratum_unsmoothed_branches.npz" in text
    assert "critical_stratum_log_savgol_branches.npz" in text
    assert "--expected-original-comparison-sha256" in text
    for output_name in (
        "critical_stratum_census_selection.csv",
        "hybrid_population_gate_summary.csv",
        "sampling_extrapolation_audit.csv",
        "census_concentration_summary.csv",
        "critical_stratum_membership_summary.csv",
        "census_cutoff_records.csv",
        "census_gate_summary.csv",
        "critical_stratum_census_summary.json",
    ):
        assert output_name in text
    assert "qsub" not in lower
    assert "mpirun" not in lower
    assert "raytrace" not in lower
    assert "rm -rf" not in lower


def test_wrapper_fails_closed_and_preserves_scientific_exit_contract() -> None:
    text = WRAPPER.read_text()

    assert '"$diagnostic_rc" -eq 3' in text
    assert 'diagnostic_rc" =~ ^(0|3)$' in text
    assert "exit 2" in text
    assert "exit 3" in text
    assert 'summary.get("status") != "diagnostic_complete"' in text
    assert 'summary.get(key' in text
    assert 'summary.get("decision")' in text
    assert '"HOLD_FOR_CUTOFF_REVIEW"' in text
    assert '"FAIL_NUMERICAL_OR_PROVENANCE"' in text
    assert 'if decision == "FAIL_NUMERICAL_OR_PROVENANCE":' in text
    assert 'missing partial-failure evidence' in text
    assert 'test ! -L "$path"' in text


def test_wrapper_partial_failure_does_not_require_branch_arrays() -> None:
    text = WRAPPER.read_text()
    failure_branch = text.split(
        'if decision == "FAIL_NUMERICAL_OR_PROVENANCE":',
        1,
    )[1].split(
        'for filename in ("critical_stratum_unsmoothed_branches.npz",',
        1,
    )[0]
    assert "census_cutoff_records.csv" in failure_branch
    assert "census_gate_summary.csv" in failure_branch
    assert "critical_stratum_unsmoothed_branches.npz" not in failure_branch
