from __future__ import annotations

from pathlib import Path


WRAPPER = Path("scripts/kunanyi/c_hi_late_age_axis_extension.pbs")


def test_late_age_axis_extension_targets_only_authorized_new_samples() -> None:
    text = WRAPPER.read_text()

    assert '"48|Timestep_48|46.999852"' in text
    assert '"50|Timestep_50|48.999418"' in text
    assert 'ENDPOINT_CONTROL="51|Timestep_51|50.000000"' in text
    assert '"46|Timestep_46' not in text
    assert '"47|Timestep_47' not in text
    assert '"49|Timestep_49' not in text
    assert "Timestep_8" not in text
    assert "Timestep_14" not in text


def test_late_age_axis_extension_preserves_refined_projection_contract() -> None:
    text = WRAPPER.read_text()

    assert '"0|0deg|direct_y_axis_sum"' in text
    assert '"45|45deg|edge_overlap_uniform_cell_projection"' in text
    assert '"90|90deg|edge_overlap_uniform_cell_projection"' in text
    assert "projected_accumulation" in text
    assert "EMPTY_COLUMN_FRACTION_MAX" in text
    assert "projection_empty_columns.csv" in text


def test_late_age_axis_extension_is_postprocessing_only() -> None:
    text = WRAPPER.read_text().lower()

    assert "xraise_grid_smoke.py" in text
    assert "qsub" not in text
    assert "mpiexec" not in text
    assert "pluto " not in text
    assert "praise" not in text
    assert "cavity_stub" not in text
    assert "c-lo" not in text
    assert "g-lo" not in text


def test_late_age_axis_extension_archives_stable_snapshot_not_live_root() -> None:
    text = WRAPPER.read_text()

    assert 'ARCHIVE_SNAPSHOT_ROOT="${ARCHIVE_SNAPSHOT_ROOT:-$ANALYSIS_ROOT/archive_snapshot}"' in text
    assert 'ARCHIVE_PAYLOAD_DIR="$ARCHIVE_SNAPSHOT_ROOT/$(basename "$ANALYSIS_ROOT")"' in text
    assert 'ARCHIVE_FILE_LIST="$ARCHIVE_SNAPSHOT_ROOT/archive_file_list.txt"' in text
    assert 'tar -czf "$SUMMARY_ARCHIVE" -C "$ARCHIVE_SNAPSHOT_ROOT" --files-from "$ARCHIVE_FILE_LIST"' in text
    assert 'tar -czf "$SUMMARY_ARCHIVE" -C "$ARCHIVE_SNAPSHOT_ROOT" "$(basename "$ARCHIVE_PAYLOAD_DIR")"' not in text
    assert 'tar -czf "$SUMMARY_ARCHIVE" -C "$(dirname "$ANALYSIS_ROOT")" "$(basename "$ANALYSIS_ROOT")"' not in text


def test_late_age_axis_extension_snapshot_contract_includes_products_logs_and_manifest() -> None:
    text = WRAPPER.read_text()

    assert 'copy_completed_products_to_archive_snapshot()' in text
    assert 'copy_remote_logs_to_archive_snapshot()' in text
    assert 'write_archive_manifest()' in text
    assert 'xraise_grid_${label}' in text
    assert '$ARCHIVE_PAYLOAD_DIR/remote_logs' in text
    assert 'archive_manifest.tsv' in text
    assert 'archive_checksums.sha256' in text


def test_late_age_axis_extension_uses_goal021_paths_and_bounded_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N c_hi_ageext" in text
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=04:00:00" in text
    assert "/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension" in text
    assert "/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension" in text
    assert "c_hi_bounded_age_axis_extension_2026-07-01.tar.gz" in text
