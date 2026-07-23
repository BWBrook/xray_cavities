from __future__ import annotations

import re
from pathlib import Path


WRAPPER = Path("scripts/kunanyi/xray_cavity_production_validation.pbs")


def test_wrapper_is_existing_output_postprocessing_only() -> None:
    text = WRAPPER.read_text()

    assert "data.0051.flt.h5" in text
    assert "Timestep_51" in text
    assert "xraise_grid_smoke.py" in text
    assert "validate_xray_cavity_production.py" in text
    assert "mpirun" not in text
    assert "qsub" not in text
    assert "pluto " not in text.lower()
    assert "refusing to overwrite" in text


def test_wrapper_runs_native_and_edge_projection_contract() -> None:
    text = WRAPPER.read_text()

    assert "--projection-mode \"$mode\"" in text
    assert re.search(r"direct0 .* 0 direct_axis", text)
    assert re.search(r"edge0 .* 0 edge_overlap", text)
    assert re.search(r"edge45 .* 45 edge_overlap", text)
    assert re.search(r"edge89p9 .* 89\.9 edge_overlap", text)
    assert re.search(r"edge90 .* 90 edge_overlap", text)
    assert re.search(r"direct90 .* 90 direct_axis", text)


def test_wrapper_repeats_synthetic_surface_and_real_edge90_for_determinism() -> None:
    text = WRAPPER.read_text()

    assert "for repeat_scope in synthetic synthetic_repeat" in text
    assert "edge90_repeat" in text
    assert "run_command_manifest.csv" in text
    assert "provenance.csv" in text
    assert "acceptance_criteria.csv" not in text or "contracts" in text


def test_wrapper_fails_closed_and_archives_only_compact_validation_evidence() -> None:
    text = WRAPPER.read_text()

    assert "set -euo pipefail" in text
    assert "validation_status" not in text
    assert "ARCHIVE_PAYLOAD_TMP/validation" in text
    assert "ARCHIVE_PAYLOAD_TMP/contracts" in text
    assert 'cp -a "$REAL_ROOT"' not in text
    assert 'cp -a "$ANALYSIS_ROOT/fixtures"' not in text
    assert "archive_checksums.sha256" in text
    assert "archive_file_list.txt" in text
    assert "VALIDATION_EXIT_CODE=$?" in text
    assert "validation_failed_closed_archive_preserved" in text
    assert text.index('tar -czf "$ARCHIVE"') < text.index('exit "$VALIDATION_EXIT_CODE"')
