from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/kunanyi/g_lo_pressure_smoothing_diagnostic.pbs")


def test_wrapper_is_read_only_cache_diagnostic() -> None:
    text = SCRIPT.read_text()

    assert "#PBS -N g_lo_psdiag" in text
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=64gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert "diagnose_g_lo_pressure_smoothing.py" in text
    assert "g_lo_history.h5" in text
    assert "--row-chunk 4096" in text
    assert "--expected-trim-rows 10030" in text
    assert "--expected-no-positive-rows 2" in text
    assert "--expected-single-record-rows 48" in text
    assert "runtime_import_preflight=passed" in text
    assert "smoothing_diagnostic_validation=passed" in text
    assert "pressure_smoothing_diagnostic.json" in text
    assert "pressure_smoothing_affected_rows.csv" in text


def test_wrapper_is_no_overwrite_and_bytecode_manifest_hardened() -> None:
    text = SCRIPT.read_text()

    assert "refusing to overwrite existing smoothing-diagnostic output root" in text
    assert "refusing to overwrite existing smoothing-diagnostic archive" in text
    assert "staged smoothing-diagnostic manifest must not bind generated Python bytecode" in text
    assert "sha256sum --check" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text
    assert "tar -tzf" in text


def test_wrapper_archives_stable_explicit_file_list_not_live_directory() -> None:
    text = SCRIPT.read_text()

    assert 'ARCHIVE_PAYLOAD="$STAGE_ROOT/archive_payload"' in text
    assert 'ARCHIVE_FILE_LIST="$ARCHIVE_PAYLOAD/archive_file_list.txt"' in text
    assert "cp -p \"$ANALYSIS_ROOT/pressure_smoothing_diagnostic.json\"" in text
    assert "cp -p \"$ANALYSIS_ROOT/pressure_smoothing_affected_rows.csv\"" in text
    assert 'tar -C "$ARCHIVE_PAYLOAD" -czf "$archive_tmp" --files-from "$ARCHIVE_FILE_LIST"' in text
    assert 'tar -C "$(dirname "$ANALYSIS_ROOT")" -czf "$archive_tmp" "$(basename "$ANALYSIS_ROOT")"' not in text
    assert "file changed as we read" not in text
    assert 'grep -Fxx "./$(basename "$ANALYSIS_ROOT")/pressure_smoothing_diagnostic.json" >/dev/null' in text


def test_wrapper_cannot_submit_or_mutate_source_cache() -> None:
    text = SCRIPT.read_text().lower()

    assert "qsub" not in text
    assert "mpirun" not in text
    assert "rm -rf" not in text
    assert "rm -f" not in text
    assert "h5py.file" not in text
    assert "pluto.ini" not in text
