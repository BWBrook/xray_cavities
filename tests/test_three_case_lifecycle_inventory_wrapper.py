from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/kunanyi/three_case_lifecycle_inventory.pbs")
REPAIR_SCRIPT = Path("scripts/kunanyi/three_case_lifecycle_inventory_repair.pbs")


def test_inventory_wrapper_uses_read_only_job_contract() -> None:
    text = SCRIPT.read_text()

    assert "#PBS -N tri_lifeinv" in text
    assert "#PBS -q normal" in text
    assert "select=1:ncpus=8:mpiprocs=1:mem=64gb" in text
    assert "#PBS -l walltime=48:00:00" in text
    assert "inventory_three_case_lifecycle.py" in text
    assert "remote_root_allowlist.csv" in text
    assert "protected_path_contract.csv" in text
    assert "contract_metadata.json" in text
    assert "--contract-metadata" in text
    assert "--read-hdf5-metadata" in text
    assert "--max-workers 8" in text
    assert "qsub" not in text
    assert "mpirun" not in text
    assert "pluto" not in text.lower()
    assert "rm -rf" not in text
    assert "delete" not in text.lower()


def test_inventory_wrapper_uses_exact_external_output_and_fails_closed() -> None:
    text = SCRIPT.read_text()

    assert 'ANALYSIS_ROOT="${ANALYSIS_ROOT:-/scratch/bwbrook/xray_cavities_analysis/2026-07-23-three-case-lifecycle-inventory}"' in text
    assert 'if [ -e "$ANALYSIS_ROOT" ]' in text
    assert "output directory is deliberately outside all roots" in text
    assert "refusing to overwrite" in text
    assert "ARCHIVE_RESERVATION" in text
    assert 'mkdir "$ANALYSIS_ROOT"' in text
    assert "remote_root_inventory.csv" in text
    assert "payload_inventory.csv" in text
    assert "inventory_summary.csv" in text
    assert "inventory_metadata.json" in text
    assert "read_only" in text and "deletion_capability" in text


def test_inventory_wrapper_builds_stable_archive_file_list() -> None:
    text = SCRIPT.read_text()

    assert "ARCHIVE_PAYLOAD_TMP" in text
    assert "archive_content_file_list.txt" in text
    assert "archive_checksums.sha256" in text
    assert "archive_file_list.txt" in text
    assert "archive_manifest.tsv" in text
    assert "find . -type f" in text
    assert "manifest_scope=content_files_plus_checksums_and_content_list" in text
    assert "archive_file_list.txt and archive_manifest.tsv are intentionally outside manifest byte coverage" in text
    assert "printf './archive_manifest.tsv\\n./archive_file_list.txt\\n'" in text
    assert "printf './archive_manifest.tsv\\n' >> archive_file_list.txt" not in text
    assert 'tar -czf "$ARCHIVE_TMP" -C "$ARCHIVE_PAYLOAD" --files-from "$ARCHIVE_PAYLOAD/archive_file_list.txt"' in text
    assert "os.link(source, destination)" in text
    assert "tar -tzf \"$ARCHIVE\"" in text


def test_inventory_wrapper_requires_stage_inputs_and_validates_reports() -> None:
    text = SCRIPT.read_text()

    assert 'for path in "$SCANNER" "$ROOT_CONTRACT" "$PROTECTED_CONTRACT" "$CONTRACT_METADATA"; do' in text
    assert "missing required input" in text
    assert "invalid report header" in text
    assert "empty report" in text
    assert "metadata contract failed" in text
    assert "validation_summary.csv" in text


def test_repair_wrapper_preserves_failed_run_and_uses_distinct_outputs() -> None:
    text = REPAIR_SCRIPT.read_text()

    assert "#PBS -N tri_liferep" in text
    assert "goal046_three_case_lifecycle_inventory_repair" in text
    assert "2026-07-24-three-case-lifecycle-inventory-repair" in text
    assert "three_case_lifecycle_inventory_repair_2026-07-24.tar.gz" in text
    assert "three_case_lifecycle_inventory_repair.out" in text
    assert "three_case_lifecycle_inventory_repair.err" in text
    assert 'exec bash "$BASE_WRAPPER"' in text
    assert "qsub" not in text
    assert "rm -rf" not in text
    assert "delete" not in text.lower()
