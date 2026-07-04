from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/c_lo_bounded_execution.pbs")


def test_c_lo_wrapper_targets_only_cluster_low_power_case() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N c_lo_bound" in text
    assert 'CASE_ID="${CASE_ID:-C-LO}"' in text
    assert 'CASE_VARIANT="${CASE_VARIANT:-particles}"' in text
    assert "goal032_c_lo_bounded_execution/rendered_c_lo_config/C-LO/particles" in text
    assert "tabulated_cosmo_002003.csv" not in text.lower()
    assert "G-LO" not in text
    assert "C-HI" in text


def test_c_lo_wrapper_uses_bounded_startup_checkpoint_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -l select=80:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=04:00:00" in text
    assert 'PLUTO_MAXTIME_HOURS="${PLUTO_MAXTIME_HOURS:-3.5}"' in text
    assert 'RESTART_POLICY="${RESTART_POLICY:-force-fresh}"' in text
    assert 'ALLOW_DONE_RERUN="${ALLOW_DONE_RERUN:-0}"' in text
    assert 'RUN_ROOT="${RUN_ROOT:-/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution}"' in text


def test_c_lo_wrapper_preserves_agn_impi_stack_and_template_contract() -> None:
    text = WRAPPER.read_text()

    assert 'KUNANYI_MODULE_STACK="${KUNANYI_MODULE_STACK:-agn_intel_impi}"' in text
    assert 'MPI_FLAVOR="${MPI_FLAVOR:-intelmpi}"' in text
    assert 'HDF5_USE_FILE_LOCKING="${HDF5_USE_FILE_LOCKING:-FALSE}"' in text
    assert "jet_setup_production_template_latest.pbs" in text
    assert 'exec bash "$BASE_SCRIPT"' in text


def test_c_lo_wrapper_does_not_submit_follow_on_or_postprocess() -> None:
    lower = WRAPPER.read_text().lower()

    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "cavity" not in lower
    assert "g-lo" not in lower
    assert "source-age" not in lower
