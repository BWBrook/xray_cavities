from __future__ import annotations

from pathlib import Path


SCRIPT = Path("scripts/kunanyi/three_case_common_age_evolution.pbs")


def test_common_age_wrapper_has_fixed_resources_and_boundaries() -> None:
    text = SCRIPT.read_text()
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=96gb" in text
    assert "#PBS -l walltime=12:00:00" in text
    for name in (
        "CASE", "SOURCE_MANIFEST", "ENDPOINT_CONTRACT", "SCRATCH_GATE", "ANALYSIS_ROOT",
        "STAGE_DIR", "TRUTH_SOURCE", "CAVITY_SOURCE",
    ):
        assert f'${{{name}:?' in text
    assert "if [ -e \"$ANALYSIS_ROOT\" ]" in text
    assert "age_10myr" in text and "age_40myr" in text
    assert "age_50myr" in text and "level3" in text
    assert "xraise_grid_0deg" in text and "xraise_grid_45deg" in text and "xraise_grid_90deg" in text
    assert "--files-from" in text
    assert ".tsv" in text
    assert "module load HDF5/1.14.0-gompi-2023a" in text
    assert "module load Anaconda3/2024.02-1" in text
    assert "projection_empty_columns.csv" in text
    assert "endpoint_reuse_status" in text and "accepted_goal040" in text
    assert "scratch headroom" in text and "GREEN" in text
    assert "endpoint_reuse_contract.csv" in text and "scratch_capacity_gate.csv" in text
    assert "baseline_time_myr" in text and "zero-time" in text
    assert "selection_status" in text and "endpoint_reuse_id" in text
    assert "raw_xray" in text and "corrected_xray" in text and "correction_ratio" in text
    assert "--projected-u-bins" in text and "--y-chunk" in text
    assert "compact_snapshot_${CASE_SLUG}.tmp" in text
    assert 'tar -czf "$ARCHIVE" -C "$SNAPSHOT_TMP" --files-from "$SNAPSHOT_TMP/archive_file_list.txt"' in text
    assert "ENDPOINT_ROOT" not in text
    assert "copytree" not in text
    for forbidden in ("qsub", "mpirun", "PLUTO", "PRAiSE", "rm -rf \"$RAW", "delete"):
        assert forbidden.lower() not in text.lower()


def test_compiled_extractors_keep_hdf5_runtime_paths_and_fail_closed() -> None:
    text = SCRIPT.read_text()
    build_marker = '"$H5CC" -O2 "$CAVITY_SOURCE" -lm -o "$CAVITY_EXE"'
    analysis_marker = 'PYTHON="$(command -v python)"'
    build_start = text.index(build_marker)
    runtime_block = text[build_start : text.index(analysis_marker, build_start)]

    assert "module purge" not in runtime_block
    assert "module load Anaconda3/2024.02-1" in runtime_block
    assert 'for extractor in "$TRUTH_EXE" "$CAVITY_EXE"' in runtime_block
    assert 'ldd "$extractor" | grep -q "not found"' in runtime_block
    assert "extractor_runtime_link_validation=passed" in runtime_block


def test_wrapper_fails_closed_on_case_power_binding() -> None:
    text = SCRIPT.read_text()

    assert 'EXPECTED_POWER_ERG_S = {"C-HI": 1.0e45, "C-LO": 1.0e43, "G-LO": 1.0e43}' in text
    assert "manifest jet power violates the authoritative three-case contract" in text
