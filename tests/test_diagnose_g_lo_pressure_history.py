from __future__ import annotations

import csv
import json
import struct
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from scripts.science.diagnose_g_lo_pressure_history import _canonical_source_path, diagnose_pressure_history


SCRIPT = Path("scripts/kunanyi/g_lo_pressure_history_diagnostic.pbs")


def make_cache(path: Path) -> None:
    with h5py.File(path, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.array([101, 202], dtype="i8"))
        h5.create_dataset("times", data=np.arange(4, dtype="f8"))
        h5.create_dataset("output_indices", data=np.arange(4, dtype="i8"))
        h5.create_dataset("tinj", data=np.array([1.0, 1.0]))
        h5.create_dataset("presence", data=np.array([[False, True, True, True], [False, True, True, True]]))
        h5.create_dataset("pressure", data=np.array([[np.nan, np.nan, 0.0, -1.0], [np.nan, 1.0, np.nan, 3.0]]))
        h5.create_dataset("density", data=np.ones((2, 4)))
        h5.create_dataset("tracer", data=np.ones((2, 4)) * 0.5)
        h5.attrs["next_output"] = 4


def write_source(path: Path, *, pressure: float = 0.0) -> None:
    fields = ("id", "pressure", "density", "tracer")
    dims = (1, 1, 1, 1)
    header = ["# PLUTO 4.4", "# dimensions 3", "# nparticles 1", "# nfields 4", "# nelem 4",
              "# endianity little", "# precision double", "# time 2", "# field_names " + " ".join(fields),
              "# field_dim " + " ".join(map(str, dims))]
    payload = struct.pack("<4d", 101, pressure, 1.0, 0.5)
    path.write_bytes(("\n".join(header) + "\n").encode() + payload)


def write_sources(path: Path, records: list[tuple[int, float, float, float]], *, time: float) -> None:
    fields = ("id", "pressure", "density", "tracer")
    dims = (1, 1, 1, 1)
    header = ["# PLUTO 4.4", "# dimensions 3", f"# nparticles {len(records)}", "# nfields 4", "# nelem 4",
              "# endianity little", "# precision double", f"# time {time}", "# field_names " + " ".join(fields),
              "# field_dim " + " ".join(map(str, dims))]
    payload = b"".join(struct.pack("<4d", *record) for record in records)
    path.write_bytes(("\n".join(header) + "\n").encode() + payload)


def test_counts_first_present_later_and_chunked(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    out = tmp_path / "out"
    make_cache(cache)
    summary = diagnose_pressure_history(cache, out, row_chunk=1, source_crosscheck_limit=0)
    assert summary["counts_over_present_suffix"] == {"finite_positive": 2, "zero": 1, "negative": 1, "nonfinite": 2}
    assert summary["first_present_bad_records"] == 1
    assert summary["later_bad_records"] == 3
    assert summary["affected_row_count"] == 2
    rows = list(csv.DictReader((out / "pressure_nonpositive_by_output.csv").open()))
    assert len(rows) == 4
    assert rows[2]["zero_count"] == "1"
    assert json.loads((out / "pressure_history_diagnostic.json").read_text())["min_positive_pressure"] == 1.0


def test_source_crosscheck_is_bounded_and_cache_unchanged(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    initial = tmp_path / "initial"
    guarded = tmp_path / "guarded"
    initial.mkdir(); guarded.mkdir()
    make_cache(cache)
    write_source(initial / "particles.0001.dbl", pressure=9.0)
    write_source(initial / "particles.0002.dbl", pressure=0.0)
    write_source(guarded / "particles.0002.dbl", pressure=0.0)
    write_source(guarded / "particles.1000.dbl", pressure=0.0)
    before = cache.read_bytes()
    out = tmp_path / "out"
    diagnose_pressure_history(cache, out, source_roots=[initial, guarded], row_chunk=1, source_crosscheck_limit=4)
    records = list(csv.DictReader((out / "representative_bad_records.csv").open()))
    matched = [row for row in records if row["source_status"] == "matched"]
    assert matched and any(row["output_index"] == "2" and row["source_segment"] == "initial" and row["cache_source_pressure_match"] == "True" for row in matched)
    assert any(row["output_index"] == "1" and row["source_segment"] == "initial" for row in matched)
    selected, segment = _canonical_source_path(initial, guarded, 1000)
    assert selected == guarded / "particles.1000.dbl" and segment == "guarded"
    assert cache.read_bytes() == before


def test_refuses_nonempty_output_and_internal_gap(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    make_cache(cache)
    out = tmp_path / "out"
    out.mkdir(); (out / "keep").write_text("x")
    with pytest.raises(RuntimeError, match="non-empty"):
        diagnose_pressure_history(cache, out)
    with h5py.File(cache, "r+") as h5:
        h5["presence"][0, 2] = False
    summary = diagnose_pressure_history(cache, tmp_path / "out2")
    assert summary["lifecycle_violation_rows"] == 1


def test_distinguishes_leading_zero_prefix_from_internal_defect(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    with h5py.File(cache, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.array([101, 202], dtype="i8"))
        h5.create_dataset("times", data=np.arange(5, dtype="f8"))
        h5.create_dataset("output_indices", data=np.arange(5, dtype="i8"))
        h5.create_dataset("tinj", data=np.array([2.0, 1.0]))
        h5.create_dataset(
            "presence",
            data=np.array(
                [
                    [False, False, True, True, True],
                    [False, True, True, True, True],
                ]
            ),
        )
        h5.create_dataset(
            "pressure",
            data=np.array(
                [
                    [np.nan, np.nan, 0.0, 0.0, 2.0],
                    [np.nan, 1.0, 0.0, 2.0, 3.0],
                ]
            ),
        )
        h5.create_dataset("density", data=np.ones((2, 5)))
        h5.create_dataset("tracer", data=np.ones((2, 5)) * 0.5)

    summary = diagnose_pressure_history(
        cache,
        tmp_path / "out",
        row_chunk=1,
        source_crosscheck_limit=0,
    )
    assert summary["pattern_counts"] == {
        "leading_zero_only_prefix_rows": 1,
        "leading_zero_only_prefix_records": 2,
        "internal_nonpositive_after_positive_rows": 1,
        "internal_nonpositive_after_positive_records": 1,
        "no_positive_record_rows": 0,
        "no_positive_record_records": 0,
        "nonpositive_endpoint_rows": 0,
        "nonpositive_endpoint_records": 0,
    }


def test_exports_all_exceptional_rows_beyond_representative_limit_and_crosschecks_first_final(tmp_path: Path) -> None:
    cache = tmp_path / "cache.h5"
    initial = tmp_path / "initial"
    guarded = tmp_path / "guarded"
    initial.mkdir(); guarded.mkdir()
    with h5py.File(cache, "w") as h5:
        h5.create_dataset("endpoint_ids", data=np.array([101, 202, 303], dtype="i8"))
        h5.create_dataset("times", data=np.arange(4, dtype="f8"))
        h5.create_dataset("output_indices", data=np.arange(4, dtype="i8"))
        h5.create_dataset("tinj", data=np.array([1.0, 1.0, 1.0]))
        h5.create_dataset("presence", data=np.array([[False, True, True, True]] * 3))
        h5.create_dataset("pressure", data=np.array([
            [np.nan, 0.0, 2.0, 3.0],
            [np.nan, 0.0, 0.0, 0.0],
            [np.nan, 1.0, 2.0, 0.0],
        ]))
        h5.create_dataset("density", data=np.ones((3, 4)))
        h5.create_dataset("tracer", data=np.ones((3, 4)) * 0.5)
    for output, time, pressures in ((1, 1.0, (0.0, 0.0, 1.0)), (3, 3.0, (3.0, 0.0, 0.0))):
        write_sources(
            initial / f"particles.{output:04d}.dbl",
            [(101, pressures[0], 1.0, 0.5), (202, pressures[1], 1.0, 0.5), (303, pressures[2], 1.0, 0.5)],
            time=time,
        )

    out = tmp_path / "out"
    summary = diagnose_pressure_history(
        cache,
        out,
        initial_source_root=initial,
        guarded_source_root=guarded,
        representative_limit=1,
        source_crosscheck_limit=0,
        row_chunk=1,
    )
    assert summary["representative_bad_record_count"] == 1
    assert summary["exceptional_row_count"] == 2
    rows = list(csv.DictReader((out / "exceptional_pressure_rows.csv").open()))
    assert len(rows) == 2
    no_positive = next(row for row in rows if row["endpoint_id"] == "202")
    assert no_positive["finite_positive_count"] == "0"
    assert no_positive["endpoint_bad"] == "True"
    assert no_positive["first_source_status"] == "matched"
    assert no_positive["last_source_status"] == "matched"
    assert no_positive["first_cache_source_all_match"] == "True"
    assert no_positive["last_cache_source_all_match"] == "True"
    assert {row["endpoint_id"] for row in rows} == {"202", "303"}
    assert "101" not in {row["endpoint_id"] for row in rows}


def test_wrapper_static_read_only_resource_and_output_contract() -> None:
    text = SCRIPT.read_text()
    assert "#PBS -l select=1:ncpus=1:mpiprocs=1:mem=32gb" in text
    assert "#PBS -l walltime=02:00:00" in text
    assert "module load Anaconda3/2024.02-1" in text
    assert "diagnose_g_lo_pressure_history.py" in text
    assert "g_lo_particle_history.py" in text
    assert 'PYTHONPATH="$STAGE_ROOT:' in text
    assert "g_lo_history.h5" in text
    assert "g_lo_history.h5.inprogress" not in text
    assert "sha256sum --check" in text
    assert "refusing to overwrite existing diagnostic output root" in text
    assert 'mkdir "$ANALYSIS_ROOT"' not in text
    assert "pressure_history_diagnostic.json" in text
    assert "pressure_nonpositive_by_output.csv" in text
    assert "representative_bad_records.csv" in text
    assert "exceptional_pressure_rows.csv" in text
    assert "qsub" not in text and "mpirun" not in text and "rm -rf" not in text
