from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_lo_hdf5_stall_guarded_continuation.pbs")


def test_wrapper_targets_only_guarded_g_lo_continuation() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_lo_guard" in text
    assert 'readonly CASE_ID="G-LO"' in text
    assert 'readonly CASE_VARIANT="particles"' in text
    assert "goal038_g_lo_hdf5_stall_guarded_continuation" in text
    assert "2026-07-10-g-lo-hdf5-stall-guarded-continuation" in text
    assert "C-LO" not in text
    assert "C-HI" not in text
    assert 'readonly RESTART_POLICY="auto"' in text
    assert 'readonly RUN_ROOT="/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation"' in text
    assert 'CASE_ID="${CASE_ID:-G-LO}"' not in text
    assert 'CASE_VARIANT="${CASE_VARIANT:-particles}"' not in text
    assert 'RESTART_POLICY="${RESTART_POLICY:-auto}"' not in text


def test_wrapper_pins_validated_restart_and_endpoint_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly PLUTO_MAXTIME_HOURS="47.5"' in text
    assert 'readonly SAFE_H5_RESTART_INDEX="2"' in text
    assert 'readonly H5_RESTART_INDEX="$SAFE_H5_RESTART_INDEX"' in text
    assert 'readonly RESTART_POLICY="auto"' in text
    assert 'readonly ALLOW_DONE_RERUN="0"' in text
    assert 'readonly FORCE_REBUILD="0"' in text
    assert "export RESTART_POLICY H5_RESTART_INDEX ALLOW_DONE_RERUN" in text


def test_wrapper_enables_fail_closed_watchdog() -> None:
    text = WRAPPER.read_text()

    assert 'readonly WATCHDOG_TIMEOUT_SECONDS="5400"' in text
    assert 'readonly WATCHDOG_POLL_SECONDS="60"' in text
    assert 'readonly WATCHDOG_TERM_GRACE_SECONDS="120"' in text
    assert 'export PROGRESS_WATCHDOG_TIMEOUT_SECONDS="$WATCHDOG_TIMEOUT_SECONDS"' in text
    assert 'export PROGRESS_WATCHDOG_POLL_SECONDS="$WATCHDOG_POLL_SECONDS"' in text
    assert 'export PROGRESS_WATCHDOG_TERM_GRACE_SECONDS="$WATCHDOG_TERM_GRACE_SECONDS"' in text
    assert "run_with_progress_watchdog.sh" in text
    assert "progress_watchdog" in text


def test_wrapper_preserves_agn_impi_stack_and_has_no_follow_on_work() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert 'readonly KUNANYI_MODULE_STACK="agn_intel_impi"' in text
    assert 'readonly MPI_FLAVOR="intelmpi"' in text
    assert 'readonly HDF5_USE_FILE_LOCKING="FALSE"' in text
    assert 'readonly I_MPI_JOB_SIGNAL_PROPAGATION="1"' in text
    assert "jet_setup_production_template_latest.pbs" in text
    assert 'exec bash "$BASE_SCRIPT"' in text
    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "cavity" not in lower
    assert "postprocess" not in lower


def test_wrapper_revalidates_exact_fluid_particle_pair_and_hdf5_before_launch() -> None:
    text = WRAPPER.read_text()

    assert "validate_pluto_particle_restart_pair.py" in text
    assert 'readonly SAFE_PARTICLE_RESTART_INDEX="1000"' in text
    assert 'readonly SAFE_FLOAT_OUTPUT_INDEX="10"' in text
    assert 'readonly SAFE_RESTART_STEP="10578"' in text
    assert 'readonly SAFE_HDF5_BYTES="67318639276"' in text
    assert 'readonly SAFE_HDF5_TIMESTEP="Timestep_2"' in text
    assert 'readonly SAFE_SOURCE_HDF5_PATH=' in text
    assert '"--expected-record-count" "3"' in text
    assert '"--expected-output-index" "3" "$SAFE_FLOAT_OUTPUT_INDEX"' in text
    assert '"--expected-particle-index" "$SAFE_PARTICLE_RESTART_INDEX"' in text
    assert '"--expected-step" "$SAFE_RESTART_STEP"' in text
    assert '"--fluid-hdf5" "$SAFE_HDF5_PATH"' in text
    assert '"--fluid-catalogue" "$SAFE_FLUID_CATALOGUE"' in text
    assert '"--expected-fluid-hdf5-size" "$SAFE_HDF5_BYTES"' in text
    assert '"--expected-fluid-hdf5-sha256" "$SOURCE_HDF5_SHA256"' in text
    assert '"--fluid-timestep" "$SAFE_HDF5_TIMESTEP"' in text
    assert '"--expected-fluid-shape" "1014" "960" "960"' in text
    assert '"--hash-inputs"' in text
    assert 'SOURCE_HDF5_SHA256=$(sha256sum "$SAFE_SOURCE_HDF5_PATH"' in text
    assert "restart_pair_validation_job.json" in text
    assert text.index("validate_pluto_particle_restart_pair.py") < text.index('exec bash "$BASE_SCRIPT"')
