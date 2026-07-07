from __future__ import annotations

import csv
import re
from pathlib import Path


WRAPPER = Path("scripts/kunanyi/c_lo_endpoint_first_products.pbs")
ASSET_DIR = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07")


def test_c_lo_endpoint_first_products_targets_only_endpoint_surface() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -N c_lo_xprod" in text
    assert "goal036_c_lo_endpoint_first_products" in text
    assert "2026-07-07-c-lo-endpoint-first-products" in text
    assert "2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles" in text
    assert "data.0053.flt.h5" in text
    assert "Timestep_53" in text
    assert "data.0013.dbl.h5" in text
    assert "particles.5003.dbl" in text
    assert "15330.06968940" in text
    assert "C-HI/particles/problem/outputs" not in text
    assert "G-LO" not in text


def test_c_lo_endpoint_first_products_preserves_projection_contract() -> None:
    text = WRAPPER.read_text()

    assert '"0|0deg|direct_y_axis_sum"' in text
    assert '"45|45deg|edge_overlap_uniform_cell_projection"' in text
    assert '"90|90deg|edge_overlap_uniform_cell_projection"' in text
    assert "projected_accumulation" in text
    assert "projection_empty_columns.csv" in text
    assert "EMPTY_COLUMN_FRACTION_MAX" in text
    assert "c_lo_endpoint_projection_metrics.csv" in text
    assert "c_hi_c_lo_endpoint_comparison.csv" in text
    assert "c_hi_refined_trio_context.csv" in text


def test_c_lo_endpoint_first_products_projection_metric_columns_are_unique() -> None:
    text = WRAPPER.read_text()

    summary_match = re.search(r"summary_fields = \((.*?)\)", text, flags=re.S)
    assert summary_match is not None
    assert '"time_myr"' not in summary_match.group(1)
    assert "duplicate projection metric columns" in text

    projection_match = re.search(r"projection_columns = \[(.*?)\]", text, flags=re.S)
    assert projection_match is not None
    assert projection_match.group(1).count('"time_myr"') == 1


def test_goal036_csv_review_surfaces_have_unique_headers() -> None:
    assert ASSET_DIR.exists()
    csv_paths = sorted(ASSET_DIR.rglob("*.csv"))
    assert csv_paths

    for path in csv_paths:
        with path.open(newline="") as handle:
            reader = csv.reader(handle)
            header = next(reader)
        duplicates = sorted({name for name in header if header.count(name) > 1})
        assert duplicates == [], f"{path} has duplicate CSV headers: {duplicates}"


def test_c_lo_endpoint_first_products_is_postprocessing_only() -> None:
    text = WRAPPER.read_text().lower()

    assert "xraise_grid_smoke.py" in text
    assert "qsub" not in text
    assert "mpiexec" not in text
    assert "pluto " not in text
    assert "praise" not in text
    assert "cavity_stub" not in text
    assert "source-age" not in text
    assert "g-lo" not in text


def test_c_lo_endpoint_first_products_archives_stable_snapshot_not_live_root() -> None:
    text = WRAPPER.read_text()

    assert 'ARCHIVE_SNAPSHOT_ROOT="${ARCHIVE_SNAPSHOT_ROOT:-$ANALYSIS_ROOT/archive_snapshot}"' in text
    assert 'ARCHIVE_PAYLOAD_DIR="$ARCHIVE_SNAPSHOT_ROOT/$(basename "$ANALYSIS_ROOT")"' in text
    assert 'ARCHIVE_FILE_LIST="$ARCHIVE_SNAPSHOT_ROOT/archive_file_list.txt"' in text
    assert 'tar -czf "$SUMMARY_ARCHIVE" -C "$ARCHIVE_SNAPSHOT_ROOT" --files-from "$ARCHIVE_FILE_LIST"' in text
    assert 'tar -czf "$SUMMARY_ARCHIVE" -C "$(dirname "$ANALYSIS_ROOT")" "$(basename "$ANALYSIS_ROOT")"' not in text


def test_c_lo_endpoint_first_products_snapshot_contract_includes_products_logs_and_manifest() -> None:
    text = WRAPPER.read_text()

    assert "copy_completed_products_to_archive_snapshot()" in text
    assert "copy_remote_logs_to_archive_snapshot()" in text
    assert "write_archive_manifest()" in text
    assert "xraise_grid_${label}" in text
    assert "$ARCHIVE_PAYLOAD_DIR/remote_logs" in text
    assert "archive_manifest.tsv" in text
    assert "archive_checksums.sha256" in text


def test_c_lo_endpoint_first_products_uses_bounded_single_node_resources() -> None:
    text = WRAPPER.read_text()

    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=04:00:00" in text
    assert "c_lo_endpoint_first_products_2026-07-07.tar.gz" in text
