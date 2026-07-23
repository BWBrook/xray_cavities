from pathlib import Path


WRAPPER = Path(
    "scripts/kunanyi/xray_cavity_recovery_method_refinement.pbs"
)


def test_wrapper_is_evaluation_only_against_existing_goal044_maps() -> None:
    text = WRAPPER.read_text()

    assert "2026-07-23-xray-cavity-production-validation" in text
    assert "evaluation_only_existing_goal044_maps=1" in text
    assert "make-fixtures" not in text
    assert "xraise_grid_smoke.py" not in text
    assert "data.0051.flt.h5" not in text
    assert "mpirun" not in text
    assert "qsub" not in text
    assert "pluto " not in text.lower()


def test_wrapper_preflights_complete_existing_product_surface() -> None:
    text = WRAPPER.read_text()

    assert "for case_id in axisymmetric nonaxisymmetric" in text
    assert "direct0 edge0 edge45 edge89p9 edge90 direct90" in text
    assert "for product in direct0 direct90 edge90" in text
    assert "tracer_max_los.tsv" in text
    assert "xray_1kev_xraise_corrected_mjy_sr.tsv" in text


def test_wrapper_freezes_contract_before_evaluation() -> None:
    text = WRAPPER.read_text()

    assert text.index("write-contract") < text.index('"$PYTHON" "$VALIDATOR" evaluate')
    assert "code_provenance.csv" in text
    assert '"goal045_wrapper|$GOAL045_WRAPPER"' in text
    assert (
        '"synthetic_fixture_contract|$SYNTHETIC_FIXTURE_CONTRACT"' in text
    )
    assert "sha256sum" in text
    assert "refusing to overwrite an existing Goal 045 output" in text


def test_wrapper_archives_failed_closed_evidence_before_exit() -> None:
    text = WRAPPER.read_text()

    assert "VALIDATION_EXIT_CODE=$?" in text
    assert "archive_checksums.sha256" in text
    assert "archive_file_list.txt" in text
    assert "evaluator_startup_failure.csv" in text
    assert text.index('if [ ! -d "$ANALYSIS_ROOT/validation" ]') < text.index(
        'cp -a "$ANALYSIS_ROOT/validation"'
    )
    assert "validation_failed_closed_archive_preserved" in text
    assert text.index('tar -czf "$ARCHIVE"') < text.index(
        'exit "$VALIDATION_EXIT_CODE"'
    )
