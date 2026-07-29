from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/kunanyi/g_lo_radio_history_method_value.pbs")


def test_wrapper_requests_bold_single_node_postprocessing() -> None:
    text = SCRIPT.read_text()

    assert "#PBS -N g_lo_radhist" in text
    assert "#PBS -q normal" in text
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=128gb" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert "set -euo pipefail" in text
    assert "run_g_lo_radio_history_value.py" in text
    assert "OMP_NUM_THREADS=1" in text
    assert "NUMBA_NUM_THREADS=16" in text


def test_wrapper_uses_only_staged_pinned_plutokore_and_compat_shim() -> None:
    text = SCRIPT.read_text()

    assert 'EXPECTED_PLUTOKORE_COMMIT="e80252cf35ff5a06166240e2867d3d485aaf6956"' in text
    assert 'LEGACY_HISTORY_HELPER_SHA256="70a865778fbb279ad3f96a34c4f53810256824626fc21f7def1b0657bb76e654"' in text
    assert 'export GOAL049_LEGACY_HISTORY_HELPER_SHA256="$LEGACY_HISTORY_HELPER_SHA256"' in text
    assert 'PLUTOKORE_SOURCE="${PLUTOKORE_SOURCE:-$STAGE_ROOT/plutokore}"' in text
    assert 'PLUTOKORE_COMMIT_PROOF="${PLUTOKORE_COMMIT_PROOF:-$STAGE_ROOT/plutokore_commit.txt}"' in text
    assert 'PYTHON_COMPAT="${PYTHON_COMPAT:-$STAGE_ROOT/scripts/kunanyi/python_compat}"' in text
    assert 'PYTHONPATH="$PYTHON_COMPAT:$PLUTOKORE_SOURCE/src:$STAGE_ROOT' in text
    assert 'actual_plutokore_commit="$(tr -d \'[:space:]\' < "$PLUTOKORE_COMMIT_PROOF")"' in text
    assert "if command -v git >/dev/null 2>&1; then" in text
    assert 'git -C "$PLUTOKORE_SOURCE" rev-parse HEAD' in text
    assert "git is required for staged source verification" not in text
    assert "staged manifest must not bind generated Python bytecode" in text
    assert "(/__pycache__/|\\.(pyc|pyo)$)" in text
    assert "hdf5plugin" in text
    assert "calculate_praise_emissivity_numba" in text
    assert "raytrace_particles_multiple_freq" in text
    assert "/Users/bwbrook/git/utas-agn/plutokore" not in text
    assert "/home/bwbrook/git/utas-agn/plutokore" not in text


def test_wrapper_preflights_sources_disk_and_runtime_fail_closed() -> None:
    text = SCRIPT.read_text()

    assert "INITIAL_ROOT" in text and "GUARDED_ROOT" in text
    assert "particles.0000.dbl" in text
    assert "particles.1499.dbl" in text
    assert "particles.1000.dbl" in text
    assert "particles.5000.dbl" in text
    assert "find \"$INITIAL_ROOT\"" in text
    assert "find \"$GUARDED_ROOT\"" in text
    assert "1500" in text and "4001" in text
    assert "130" in text
    assert "--requested-memory-gb 128" in text
    assert "--max-projected-free-fraction 0.70" in text
    assert "--shock-threshold 5" in text
    assert "0.05,0.5,5.0" in text
    assert "197568" in text
    assert "source/output path overlap" in text
    assert "refusing to overwrite" in text
    assert 'RUN_LOG="${RUN_LOG:-$ANALYSIS_ROOT/g_lo_radio_history_method_value.${PBS_JOBID:-manual}.log}"' in text
    assert "refusing to overwrite an existing Goal 049 per-job run log" in text


def test_wrapper_gates_resume_on_exact_pressure_diagnostic_and_source_lineage() -> None:
    text = SCRIPT.read_text()

    assert "diagnose_g_lo_pressure_history.py" in text
    assert 'PRESSURE_CACHE="$ANALYSIS_ROOT/cache/g_lo_history.h5"' in text
    assert 'pressure_history_diagnostic_${PBS_JOBID:-manual}' in text
    assert '--initial-source-root "$INITIAL_ROOT"' in text
    assert '--guarded-source-root "$GUARDED_ROOT"' in text
    assert '"zero": 10032' in text
    assert '"leading_zero_only_prefix_rows": 10030' in text
    assert '"no_positive_record_rows": 2' in text
    assert '"internal_nonpositive_after_positive_rows": 0' in text
    assert '"nonpositive_endpoint_rows": 2' in text
    assert '"lifecycle_violation_rows": 0' in text
    assert "expected exactly two exceptional pressure histories" in text
    assert 'row[f"{label}_source_status"] != "matched"' in text
    assert 'row[f"{label}_cache_source_all_match"]' in text
    assert "exceptional canonical source row is not an exact joint zero" in text
    assert "pressure_diagnostic_validation=passed" in text
    diagnostic_position = text.index('"$PYTHON" "$PRESSURE_DIAGNOSTIC"')
    science_position = text.index('"$PYTHON" "$RUNNER" run')
    assert diagnostic_position < science_position


def test_wrapper_has_stable_compact_archive_and_no_destructive_or_production_actions() -> None:
    text = SCRIPT.read_text()
    lowered = text.lower()

    assert "archive_file_list.txt" in text
    assert "archive_checksums.sha256" in text
    assert "archive_manifest.tsv" in text
    assert "--files-from" in text
    assert "--sort=name" not in text
    assert 'tar -tzf "$ARCHIVE_TMP"' in text
    assert "os.link(source, destination)" in text
    assert "history.h5" in text
    assert "particles.*.dbl" in text
    assert "rm -rf" not in text
    assert "rm -f" not in text
    assert "qsub" not in text
    assert "mpirun" not in text
    assert "pluto.ini" not in lowered
    assert "makefile" not in lowered
    assert "source overwrite" in text
