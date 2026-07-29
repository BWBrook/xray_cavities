from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/kunanyi/g_lo_pressure_method_value_diagnostic.pbs")


def test_wrapper_resources_and_actual_praise_contract() -> None:
    text = SCRIPT.read_text()
    assert "#PBS -N g_lo_pmvalue" in text
    assert "#PBS -l select=1:ncpus=16:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    assert "calculate_praise_emissivity_numba" in text
    assert 'PRESSURE_MODES == ("unsmoothed", "log_savgol")' in text
    assert "--sample-size 4096" in text
    assert "--expected-trim-rows 10030" in text
    assert "--expected-no-positive-rows 2" in text
    assert "--expected-single-record-rows 48" in text
    assert "--expected-trim-single-record-overlap-rows 2" in text
    assert "pressure_method_unsmoothed_emissivity_checkpoint.npz" in text
    assert "pressure_method_log_savgol_emissivity_checkpoint.npz" in text
    assert "pressure_method_full_reference_ordering.csv" in text
    assert "pressure_method_gamma_fallback_summary.csv" in text
    assert "pressure_method_gamma_fallback_records.csv" in text
    assert "pressure_method_nonfinite_emissivity_summary.csv" in text
    assert "pressure_method_nonfinite_emissivity_records.csv" in text
    assert "pressure_method_value_validation=passed" in text


def test_wrapper_is_no_overwrite_and_immutable_input_bound() -> None:
    text = SCRIPT.read_text()
    assert "refusing to overwrite pressure-method diagnostic output" in text
    assert "sha256sum --check" in text
    assert "staged_inputs.sha256" in text
    assert "f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30" in text
    assert "85caef2184edd7786e4d791fd52e77e422269bb6a156a48047d3c7901e4d79f2" in text
    assert 'printf \'%s  %s\\n\' "$EXPECTED_CACHE_SHA256" "$CACHE" | sha256sum --check -' in text
    assert "pressure_smoothing_affected_rows.csv" in text
    assert "g_lo_history.h5" in text
    assert "PYTHONDONTWRITEBYTECODE=1" in text


def test_wrapper_uses_stable_explicit_archive_payload() -> None:
    text = SCRIPT.read_text()
    assert 'ARCHIVE_PAYLOAD="$STAGE_ROOT/archive_payload"' in text
    assert 'ARCHIVE_FILE_LIST="$ARCHIVE_PAYLOAD/archive_file_list.txt"' in text
    assert 'cp -p "$ANALYSIS_ROOT/$name" "$ARCHIVE_PAYLOAD_ROOT/$name"' in text
    assert 'cp -p "$STAGED_SHA256" "$ARCHIVE_PAYLOAD_ROOT/staged_inputs.sha256"' in text
    assert 'printf \'./%s/staged_inputs.sha256\\n\' "$(basename "$ANALYSIS_ROOT")"' in text
    assert 'tar -C "$ARCHIVE_PAYLOAD" -czf "$archive_tmp" --files-from "$ARCHIVE_FILE_LIST"' in text
    assert "file changed as we read" not in text


def test_wrapper_archives_evidence_then_fails_closed_on_scientific_fail() -> None:
    text = SCRIPT.read_text()
    archive_marker = 'mv "$archive_tmp" "$ARCHIVE"'
    decision_marker = 'scientific_decision="$('
    assert archive_marker in text
    assert decision_marker in text
    assert text.index(archive_marker) < text.index(decision_marker)
    assert 'if [[ "$scientific_decision" != "PASS" ]]; then' in text
    assert 'pressure_method_science_gate=FAIL evidence_archived=1' in text
    assert "exit 3" in text


def test_wrapper_has_no_submission_or_science_production() -> None:
    text = SCRIPT.read_text().lower()
    assert "qsub" not in text
    assert "mpirun" not in text
    assert "pluto.ini" not in text
    assert "xraise" not in text
    assert "raytrace" not in text
