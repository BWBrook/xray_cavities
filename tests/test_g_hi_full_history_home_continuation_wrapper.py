from pathlib import Path


WRAPPER = Path("scripts/kunanyi/g_hi_full_history_home_continuation.pbs")


def test_wrapper_uses_enlarged_home_destination_at_production_scale() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N g_hi_hist_r1" in text
    assert "#PBS -l select=64:ncpus=28:mpiprocs=28" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert 'readonly CASE_ID="G-HI"' in text
    assert 'readonly RUN_ROOT="/u/bwbrook/xray_cavities_runs/' in text
    assert 'readonly PLUTO_MAXTIME_HOURS="47.5"' in text
    assert 'case "$RUN_ROOT" in' in text
    assert "/u/bwbrook/*" in text
    assert "home_write_fsync_probe=passed" in text
    assert "bs=1M count=16 conv=fsync" in text


def test_wrapper_pins_validated_ten_myr_restart_and_excludes_partial() -> None:
    text = WRAPPER.read_text()

    assert 'readonly SAFE_H5_RESTART_INDEX="2"' in text
    assert 'readonly SAFE_FLOAT_OUTPUT_INDEX="10"' in text
    assert 'readonly SAFE_PARTICLE_RESTART_INDEX="1000"' in text
    assert 'readonly SAFE_RESTART_STEP="10011"' in text
    assert 'readonly SAFE_HDF5_BYTES="67318639276"' in text
    assert 'readonly SAFE_HDF5_TIMESTEP="Timestep_2"' in text
    assert 'readonly H5_RESTART_INDEX="$SAFE_H5_RESTART_INDEX"' in text
    assert "data.0003.dbl.h5" in text
    assert "excluded partial checkpoint is present" in text


def test_wrapper_revalidates_pair_before_launch() -> None:
    text = WRAPPER.read_text()

    assert "validate_pluto_particle_restart_pair.py" in text
    assert '"--expected-record-count" "3"' in text
    assert '"--expected-output-index" "3" "$SAFE_FLOAT_OUTPUT_INDEX"' in text
    assert '"--expected-particle-index" "$SAFE_PARTICLE_RESTART_INDEX"' in text
    assert '"--expected-step" "$SAFE_RESTART_STEP"' in text
    assert '"--expected-fluid-hdf5-size" "$SAFE_HDF5_BYTES"' in text
    assert '"--expected-fluid-shdf5-sha256"' not in text
    assert '"--expected-fluid-hdf5-sha256" "$SOURCE_HDF5_SHA256"' in text
    assert '"--expected-fluid-shape" "1014" "960" "960"' in text
    assert text.index("validate_pluto_particle_restart_pair.py") < text.index(
        'exec bash "$BASE_SCRIPT"'
    )


def test_wrapper_has_watchdog_and_no_follow_on_or_submission() -> None:
    text = WRAPPER.read_text()
    lower = text.lower()

    assert 'readonly WATCHDOG_TIMEOUT_SECONDS="5400"' in text
    assert "run_with_progress_watchdog.sh" in text
    assert 'readonly ALLOW_DONE_RERUN="0"' in text
    assert 'readonly FORCE_REBUILD="0"' in text
    assert 'readonly KUNANYI_MODULE_STACK="agn_intel_impi"' in text
    assert 'exec bash "$BASE_SCRIPT"' in text
    assert "qsub" not in lower
    assert "xraise" not in lower
    assert "praise" not in lower
    assert "postprocess" not in lower
