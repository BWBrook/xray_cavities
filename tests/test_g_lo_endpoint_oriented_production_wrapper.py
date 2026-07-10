from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_endpoint_oriented_production.pbs")


def test_g_lo_endpoint_wrapper_targets_only_group_low_power_case() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_lo_endpt" in text
    assert 'CASE_ID="${CASE_ID:-G-LO}"' in text
    assert 'CASE_VARIANT="${CASE_VARIANT:-particles}"' in text
    assert "goal037_g_lo_endpoint_oriented_production/rendered_g_lo_config/G-LO/particles" in text
    assert "2026-07-07-g-lo-endpoint-oriented-production" in text
    assert "tabulated_cosmo_002031.csv" not in text.lower()
    assert "C-LO" not in text
    assert "C-HI" not in text


def test_g_lo_endpoint_wrapper_uses_endpoint_oriented_fresh_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'PLUTO_MAXTIME_HOURS="${PLUTO_MAXTIME_HOURS:-47.5}"' in text
    assert 'RESTART_POLICY="${RESTART_POLICY:-force-fresh}"' in text
    assert 'ALLOW_DONE_RERUN="${ALLOW_DONE_RERUN:-0}"' in text
    assert 'FORCE_REBUILD="${FORCE_REBUILD:-0}"' in text
    assert "#PBS -l walltime=04:00:00" not in text
    assert 'PLUTO_MAXTIME_HOURS="${PLUTO_MAXTIME_HOURS:-3.5}"' not in text


def test_g_lo_endpoint_wrapper_preserves_agn_impi_stack_and_template_contract() -> None:
    text = WRAPPER.read_text()

    assert 'KUNANYI_MODULE_STACK="${KUNANYI_MODULE_STACK:-agn_intel_impi}"' in text
    assert 'MPI_FLAVOR="${MPI_FLAVOR:-intelmpi}"' in text
    assert 'HDF5_USE_FILE_LOCKING="${HDF5_USE_FILE_LOCKING:-FALSE}"' in text
    assert "jet_setup_production_template_latest.pbs" in text
    assert 'exec bash "$BASE_SCRIPT"' in text


def test_g_lo_endpoint_wrapper_does_not_submit_follow_on_or_postprocess() -> None:
    lower = WRAPPER.read_text().lower()

    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "cavity" not in lower
    assert "source-age" not in lower
