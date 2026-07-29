from __future__ import annotations

import struct
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

import scripts.science.g_lo_particle_history as history
from scripts.science.g_lo_particle_history import (
    HistoryError,
    audit_roots,
    build_history_cache,
    classify_endpoint_completeness,
    endpoint_ids_from_final,
    parse_particle_file,
    resolve_roots,
    validate_seam,
)


FIELDS = ("id", "pressure", "density", "tracer", "last_shock_time", "x1", "x2", "x3", "vx1", "vx2", "vx3", "tinj")
DIMS = (1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1)


def write_particle(path: Path, *, index: int, time: float, rows, endian="little", precision="double", shock_thresholds=None):
    endian_char = "<" if endian == "little" else ">"
    code = "d" if precision == "double" else "f"
    header = [
        "# PLUTO 4.4",
        "# dimensions 3",
        "# nflux 0",
        f"# nparticles {len(rows)}",
        f"# nfields {len(FIELDS)}",
        f"# nelem {sum(DIMS)}",
        "# idCounter 100",
        "# dt_particles 1",
        f"# endianity {endian}",
        "# particletype 1",
        f"# precision {precision}",
        f"# time {time}",
        f"# stepNumber {index}",
        "# field_names " + " ".join(FIELDS),
        "# field_dim " + " ".join(map(str, DIMS)),
    ]
    if shock_thresholds is not None:
        header.append("# shk_thresh " + " ".join(map(str, shock_thresholds)))
    payload = b"".join(struct.pack(endian_char + str(sum(DIMS)) + code, *row) for row in rows)
    path.write_bytes(("\n".join(header) + "\n").encode() + payload)


def row(pid, p=1, d=2, tr=3, shock=(4, 5, 6), pos=(7, 8, 9), vel=(10, 11, 12), tinj=0):
    return (pid, p, d, tr, *shock, *pos, *vel, tinj)


def test_parse_endian_header_and_selected_fields(tmp_path):
    path = tmp_path / "particles.0001.dbl"
    write_particle(path, index=1, time=2.5, rows=[row(10), row(20, p=9)], endian="big", precision="single", shock_thresholds=(1.2, 3.4))
    parsed = parse_particle_file(path, fields=("pressure", "last_shock_time", "x2"), vector_components={"last_shock_time": 1})
    assert parsed.header.output_index == 1
    data = path.read_bytes()
    assert parsed.header.header_offset == data.find(b"\n", data.find(b"# shk_thresh")) + 1
    assert parsed.header.endianity == "big"
    assert parsed.header.precision == "single"
    assert parsed.header.shock_thresholds == (1.2, 3.4)
    assert parsed.fields["pressure"].tolist() == [1.0, 9.0]
    assert parsed.fields["last_shock_time"].shape == (2,)
    assert parsed.fields["x2"][1].tolist() == 8.0


def test_resolve_uses_exact_restart_anchor_then_guarded_replay(tmp_path):
    initial, guarded = tmp_path / "initial", tmp_path / "guarded"
    initial.mkdir(); guarded.mkdir()
    for i in (0, 1, 2):
        write_particle(initial / f"particles.{i:04d}.dbl", index=i, time=i + 1, rows=[row(1)])
    for i in (1, 2, 3):
        write_particle(guarded / f"particles.{i:04d}.dbl", index=i, time=i + 1, rows=[row(1)])
    resolved = resolve_roots(
        initial,
        guarded,
        initial_range=range(0, 3),
        guarded_range=range(1, 4),
        restart_anchor_index=1,
    )
    assert [p.name for p in resolved.canonical_paths] == [f"particles.{i:04d}.dbl" for i in range(4)]
    assert resolved.canonical_paths[2].parent == guarded
    assert resolved.superseded_overlap_indices == (2,)
    write_particle(guarded / "particles.0002.dbl", index=2, time=99, rows=[row(1)])
    replay = resolve_roots(
        initial,
        guarded,
        initial_range=range(0, 3),
        guarded_range=range(1, 4),
        restart_anchor_index=1,
    )
    assert replay.canonical_paths[2].parent == guarded
    write_particle(guarded / "particles.0001.dbl", index=1, time=99, rows=[row(1)])
    with pytest.raises(HistoryError, match="restart anchor"):
        resolve_roots(
            initial,
            guarded,
            initial_range=range(0, 3),
            guarded_range=range(1, 4),
            restart_anchor_index=1,
        )


def test_seam_uses_robust_median_cadence_and_relative_tolerance():
    assert validate_seam([0.0, 1.0, 2.0, 3.0], relative_tolerance=0.01)
    with pytest.raises(HistoryError, match="seam"):
        validate_seam([0.0, 1.0, 2.0, 3.0, 5.0], seam=(3, 5), relative_tolerance=0.01)


def test_noncontiguous_ids_and_pre_vs_post_injection():
    endpoint_ids = np.array([10, 20, 30])
    records = {0: np.array([10, 20]), 1: np.array([10, 30]), 2: np.array([10, 20, 30])}
    result = classify_endpoint_completeness(endpoint_ids, records, injection_time=1.5)
    assert {(0, 30), (1, 20)} == result.valid_pre_injection_absence
    assert result.missing_post_injection == set()
    result = classify_endpoint_completeness(endpoint_ids, {0: np.array([10]), 1: np.array([10]), 2: np.array([10, 30])}, injection_time=1.5)
    assert (2, 20) in result.missing_post_injection


def test_chunked_cache_resume(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    for i in range(3):
        write_particle(
            root / f"particles.{i:04d}.dbl",
            index=i,
            time=float(i),
            rows=[row(10, p=i + 1), row(20, p=i + 2)],
            shock_thresholds=(0.01, 0.5, 5.0),
        )
    cache = tmp_path / "history.h5"
    manifest = build_history_cache(
        [root / f"particles.{i:04d}.dbl" for i in range(3)],
        cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
    )
    assert manifest["processed_outputs"] == 3
    assert manifest["shock_component"] == 2
    resumed = build_history_cache(
        [root / f"particles.{i:04d}.dbl" for i in range(3)],
        cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
    )
    assert resumed["processed_outputs"] == 3
    with h5py.File(cache) as h5:
        assert h5["pressure"].dtype == np.dtype("float64")
        assert h5["pressure"].shape == (2, 3)
        assert h5["pressure"].chunks == (2, 2)
        assert h5.attrs["shock_threshold"] == pytest.approx(5.0)
        assert h5.attrs["shock_component"] == 2
        assert h5.attrs["next_output"] == 3
        assert h5.attrs["cache_writer_current"] == "sequential_chunk_batched_v2"


def test_batched_cache_recovers_after_interrupted_unaligned_batch(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    paths = []
    for i in range(5):
        path = root / f"particles.{i:04d}.dbl"
        write_particle(
            path,
            index=i,
            time=float(i),
            rows=[row(10, p=i + 1), row(20, p=i + 2)],
            shock_thresholds=(0.01, 0.5, 5.0),
        )
        paths.append(path)

    interrupted_cache = tmp_path / "interrupted.h5"
    original_parse = history.parse_particle_file

    def fail_in_second_batch(path, **kwargs):
        if path.name == "particles.0004.dbl":
            raise RuntimeError("synthetic interruption")
        return original_parse(path, **kwargs)

    monkeypatch.setattr(history, "parse_particle_file", fail_in_second_batch)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        build_history_cache(
            paths,
            interrupted_cache,
            endpoint_ids=[10, 20],
            particle_chunk_rows=2,
            time_chunk=2,
            write_batch_outputs=3,
        )
    with h5py.File(interrupted_cache) as h5:
        assert h5.attrs["next_output"] == 3
        assert h5.attrs["pending_batch_start"] == 3
        assert h5.attrs["pending_batch_stop"] == 5

    monkeypatch.setattr(history, "parse_particle_file", original_parse)
    resumed = build_history_cache(
        paths,
        interrupted_cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
        write_batch_outputs=3,
    )
    assert resumed["processed_outputs"] == 5
    assert resumed["batched_writer_start_output"] == 0

    reference_cache = tmp_path / "reference.h5"
    build_history_cache(
        paths,
        reference_cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
        write_batch_outputs=1,
    )
    with h5py.File(interrupted_cache) as resumed_h5, h5py.File(reference_cache) as reference_h5:
        assert set(resumed_h5) == set(reference_h5)
        for name in resumed_h5:
            np.testing.assert_array_equal(resumed_h5[name][:], reference_h5[name][:])
        for attribute in ("dtype", "shock_threshold", "shock_component", "next_output"):
            assert resumed_h5.attrs[attribute] == reference_h5.attrs[attribute]
        assert "pending_batch_start" not in resumed_h5.attrs
        assert "pending_batch_stop" not in resumed_h5.attrs

    # Simulate termination after the data and next_output flushes but before
    # cleanup of the pending marker. Reopening must recognize it as committed.
    with h5py.File(interrupted_cache, "a") as h5:
        h5.attrs["pending_batch_start"] = 3
        h5.attrs["pending_batch_stop"] = 5
    build_history_cache(
        paths,
        interrupted_cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
        write_batch_outputs=3,
    )
    with h5py.File(interrupted_cache) as h5:
        assert h5.attrs["next_output"] == 5
        assert "pending_batch_start" not in h5.attrs
        assert "pending_batch_stop" not in h5.attrs


def test_batched_cache_migrates_exact_legacy_partial_checkpoint(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    paths = []
    for i in range(5):
        path = root / f"particles.{i:04d}.dbl"
        write_particle(
            path,
            index=i,
            time=float(i),
            rows=[row(10, p=i + 1), row(20, p=i + 2)],
            shock_thresholds=(0.01, 0.5, 5.0),
        )
        paths.append(path)

    reference_cache = tmp_path / "reference.h5"
    build_history_cache(
        paths,
        reference_cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
        write_batch_outputs=1,
    )

    legacy_cache = tmp_path / "legacy_partial.h5"
    legacy_cache.write_bytes(reference_cache.read_bytes())
    with h5py.File(legacy_cache, "a") as h5:
        h5.attrs["next_output"] = 3
        for attribute in (
            "batched_writer_start_output",
            "batched_writer_sha256",
            "cache_writer_current",
            "legacy_writer_sha256",
        ):
            if attribute in h5.attrs:
                del h5.attrs[attribute]
        h5["times"][3:] = 0
        h5["output_indices"][3:] = 0
        for name in ("pressure", "density", "tracer", "last_shock_time"):
            h5[name][:, 3:] = np.nan
        h5["presence"][:, 3:] = False
        h5["position"][:] = np.nan
        h5["velocity"][:] = np.nan
        h5["tinj"][:] = np.nan

    legacy_sha256 = "a" * 64
    monkeypatch.setenv("GOAL049_LEGACY_HISTORY_HELPER_SHA256", legacy_sha256)
    migrated = build_history_cache(
        paths,
        legacy_cache,
        endpoint_ids=[10, 20],
        particle_chunk_rows=2,
        time_chunk=2,
        write_batch_outputs=3,
    )
    assert migrated["batched_writer_start_output"] == 3
    assert migrated["writer_segments"] == [
        {
            "start_output_inclusive": 0,
            "stop_output_exclusive": 3,
            "writer": "serial_column_v1",
            "helper_sha256": legacy_sha256,
        },
        {
            "start_output_inclusive": 3,
            "stop_output_exclusive": 5,
            "writer": "sequential_chunk_batched_v2",
            "helper_sha256": migrated["writer_segments"][1]["helper_sha256"],
        },
    ]
    assert len(migrated["writer_segments"][1]["helper_sha256"]) == 64

    with h5py.File(legacy_cache) as migrated_h5, h5py.File(reference_cache) as reference_h5:
        assert set(migrated_h5) == set(reference_h5)
        for name in migrated_h5:
            np.testing.assert_array_equal(migrated_h5[name][:], reference_h5[name][:])
        for attribute in ("dtype", "shock_threshold", "shock_component", "next_output"):
            assert migrated_h5.attrs[attribute] == reference_h5.attrs[attribute]
        assert migrated_h5.attrs["legacy_writer_sha256"] == legacy_sha256
        assert migrated_h5.attrs["batched_writer_start_output"] == 3


def test_chunked_cache_distinguishes_pre_and_post_injection_absence(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    write_particle(
        root / "particles.0000.dbl",
        index=0,
        time=0.0,
        rows=[row(10, tinj=0.0)],
        shock_thresholds=(0.01, 0.5, 5.0),
    )
    for i in (1, 2):
        write_particle(
            root / f"particles.{i:04d}.dbl",
            index=i,
            time=float(i),
            rows=[row(10, tinj=0.0), row(20, tinj=1.0)],
            shock_thresholds=(0.01, 0.5, 5.0),
        )
    manifest = build_history_cache(
        [root / f"particles.{i:04d}.dbl" for i in range(3)],
        tmp_path / "valid.h5",
        endpoint_ids=[10, 20],
        particle_chunk_rows=1,
        time_chunk=2,
    )
    assert manifest["pre_injection_absence_records"] == 1
    assert manifest["missing_post_injection_records"] == 0

    write_particle(
        root / "particles.0001.dbl",
        index=1,
        time=1.0,
        rows=[row(10, tinj=0.0)],
        shock_thresholds=(0.01, 0.5, 5.0),
    )
    write_particle(
        root / "particles.0002.dbl",
        index=2,
        time=2.0,
        rows=[row(10, tinj=0.0), row(20, tinj=0.0)],
        shock_thresholds=(0.01, 0.5, 5.0),
    )
    with pytest.raises(HistoryError, match="missing post-injection"):
        build_history_cache(
            [root / f"particles.{i:04d}.dbl" for i in range(3)],
            tmp_path / "invalid.h5",
            endpoint_ids=[10, 20],
            particle_chunk_rows=1,
            time_chunk=2,
        )


def test_chunked_cache_accepts_float32_injection_boundary_roundoff(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    injection_time = float(np.float32(12729.8487))
    write_particle(
        root / "particles.0000.dbl",
        index=0,
        time=injection_time + 3.6e-5,
        rows=[row(10, tinj=0.0)],
        shock_thresholds=(0.01, 0.5, 5.0),
    )
    write_particle(
        root / "particles.0001.dbl",
        index=1,
        time=injection_time + 3.0,
        rows=[row(10, tinj=0.0), row(20, tinj=injection_time)],
        shock_thresholds=(0.01, 0.5, 5.0),
    )

    manifest = build_history_cache(
        [root / f"particles.{i:04d}.dbl" for i in range(2)],
        tmp_path / "boundary.h5",
        endpoint_ids=[10, 20],
        particle_chunk_rows=1,
        time_chunk=2,
    )

    assert manifest["pre_injection_absence_records"] == 1
    assert manifest["injection_boundary_roundoff_records"] == 1
    assert manifest["missing_post_injection_records"] == 0
    assert manifest["presence_contract"] == "single contiguous suffix per endpoint particle"


def test_chunked_cache_rejects_internal_presence_gap(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    rows_by_output = (
        [row(10, tinj=0.0)],
        [row(10, tinj=0.0), row(20, tinj=0.5)],
        [row(10, tinj=0.0)],
        [row(10, tinj=0.0), row(20, tinj=0.5)],
    )
    for i, rows in enumerate(rows_by_output):
        write_particle(
            root / f"particles.{i:04d}.dbl",
            index=i,
            time=float(i),
            rows=rows,
            shock_thresholds=(0.01, 0.5, 5.0),
        )

    with pytest.raises(HistoryError, match="internal/post-injection"):
        build_history_cache(
            [root / f"particles.{i:04d}.dbl" for i in range(4)],
            tmp_path / "gap.h5",
            endpoint_ids=[10, 20],
            particle_chunk_rows=1,
            time_chunk=2,
        )


def test_endpoint_ids_derive_from_final_and_audit_requires_seam(tmp_path):
    root = tmp_path / "root"; root.mkdir()
    final = root / "particles.0002.dbl"
    write_particle(final, index=2, time=2.0, rows=[row(101), row(205)])
    assert endpoint_ids_from_final(final) == [101, 205]
    initial, guarded = tmp_path / "initial", tmp_path / "guarded"
    initial.mkdir(); guarded.mkdir()
    for i in (0, 1, 2):
        write_particle(initial / f"particles.{i:04d}.dbl", index=i, time=float(i), rows=[row(1)])
    for i in (1, 2, 3):
        write_particle(guarded / f"particles.{i:04d}.dbl", index=i, time=float(i), rows=[row(1)])
    with pytest.raises(HistoryError, match="seam"):
        audit_roots(
            initial,
            guarded,
            initial_range=range(0, 3),
            guarded_range=range(1, 4),
            restart_anchor_index=1,
        )
