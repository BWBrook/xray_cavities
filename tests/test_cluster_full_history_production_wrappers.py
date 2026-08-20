from __future__ import annotations

from pathlib import Path

import pytest


CASES = (
    (
        Path("scripts/kunanyi/c_hi_full_history_production.pbs"),
        "c_hi_hist",
        "C-HI",
        "2026-08-17-c-hi-full-history-rerun",
    ),
    (
        Path("scripts/kunanyi/c_lo_full_history_production.pbs"),
        "c_lo_hist",
        "C-LO",
        "2026-08-17-c-lo-full-history-rerun",
    ),
)


@pytest.mark.parametrize(("wrapper", "job_name", "case_id", "run_id"), CASES)
def test_wrapper_pins_case_and_history_complete_production_resources(
    wrapper: Path,
    job_name: str,
    case_id: str,
    run_id: str,
) -> None:
    text = wrapper.read_text()

    assert f"#PBS -N {job_name}" in text
    assert f'readonly CASE_ID="{case_id}"' in text
    assert 'readonly CASE_VARIANT="particles"' in text
    assert f"rendered_cluster_configs/{case_id}/particles" in text
    assert run_id in text
    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly PLUTO_MAXTIME_HOURS="47.5"' in text
    assert 'readonly RESTART_POLICY="fresh"' in text
    assert 'readonly ALLOW_DONE_RERUN="0"' in text


@pytest.mark.parametrize(("wrapper", "job_name", "case_id", "run_id"), CASES)
def test_wrapper_fails_closed_on_existing_workdir_and_enables_watchdog(
    wrapper: Path,
    job_name: str,
    case_id: str,
    run_id: str,
) -> None:
    text = wrapper.read_text()

    assert 'if [ -e "$WORK_ROOT" ]; then' in text
    assert "no-overwrite gate failed" in text
    assert 'readonly WATCHDOG_TIMEOUT_SECONDS="5400"' in text
    assert 'readonly WATCHDOG_POLL_SECONDS="60"' in text
    assert 'readonly WATCHDOG_TERM_GRACE_SECONDS="120"' in text
    assert "run_with_progress_watchdog.sh" in text
    assert 'readonly I_MPI_JOB_SIGNAL_PROPAGATION="1"' in text
    assert 'readonly KUNANYI_MODULE_STACK="agn_intel_impi"' in text
    assert 'readonly MPI_FLAVOR="intelmpi"' in text


@pytest.mark.parametrize(("wrapper", "job_name", "case_id", "run_id"), CASES)
def test_wrapper_contains_no_follow_on_or_destructive_fresh_start(
    wrapper: Path,
    job_name: str,
    case_id: str,
    run_id: str,
) -> None:
    text = wrapper.read_text()
    lower = text.lower()

    assert 'exec bash "$BASE_SCRIPT"' in text
    assert "force-fresh" not in lower
    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "postprocess" not in lower
    assert "compact" not in lower
