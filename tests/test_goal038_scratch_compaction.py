from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


SCRIPT = Path("scripts/kunanyi/compact_xray_cavities_scratch_goal038.py")


def load_module():
    spec = importlib.util.spec_from_file_location("goal038_compaction", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write(path: Path, value: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value)


def output_root(runs: Path, name: str, case: str) -> Path:
    return runs / name / case / "particles" / "problem" / "outputs"


def make_fixture(tmp_path: Path) -> tuple[Path, Path]:
    runs = tmp_path / "runs"
    stage = tmp_path / "stage"
    stage.mkdir()

    for name in (
        "2026-05-08-c-hi-segment",
        "2026-05-19-c-hi-fullgrid-startup",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-16node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-48node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-64node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node",
    ):
        write(runs / name / "sentinel.txt")

    fresh = output_root(
        runs, "2026-06-01-c-hi-fullgrid-agn-impi-fresh", "C-HI"
    )
    for index in range(10):
        write(fresh / f"data.{index:04d}.dbl.h5", f"fresh-double-{index}")
        write(fresh / f"data.{index:04d}.dbl.xmf", f"fresh-xmf-{index}")
    write(fresh / "particles.0123.dbl", "discard")
    write(fresh / "particles.4277.dbl", "keep-fresh-particle")
    write(fresh / "data.0000.flt.h5", "keep-fresh-float")

    prod = output_root(
        runs, "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64", "C-HI"
    )
    write(prod / "data.0010.dbl.h5", "discard-double")
    write(prod / "data.0010.dbl.xmf", "discard-xmf")
    write(prod / "data.0011.dbl.h5", "keep-final-double")
    write(prod / "data.0011.dbl.xmf", "keep-final-xmf")
    write(prod / "particles.4500.dbl", "discard-particle")
    write(prod / "particles.5000.dbl", "keep-final-particle")
    (prod / "data.0009.dbl.h5").symlink_to(fresh / "data.0009.dbl.h5")
    (prod / "particles.4277.dbl").symlink_to(fresh / "particles.4277.dbl")

    c_lo_1 = output_root(runs, "2026-07-03-c-lo-bounded-execution", "C-LO")
    c_lo_2 = output_root(
        runs, "2026-07-04-c-lo-bounded-continuation", "C-LO"
    )
    c_lo_3 = output_root(
        runs, "2026-07-05-c-lo-bounded-continuation-2", "C-LO"
    )
    c_lo_final = output_root(
        runs, "2026-07-05-c-lo-endpoint-oriented-continuation", "C-LO"
    )
    for root in (c_lo_1, c_lo_2, c_lo_3, c_lo_final):
        root.mkdir(parents=True, exist_ok=True)

    for index in range(0, 7):
        write(c_lo_1 / f"data.{index:04d}.flt.h5", f"float-{index}")
        write(c_lo_1 / f"data.{index:04d}.flt.xmf", f"float-xmf-{index}")
    for index in range(7, 13):
        write(c_lo_2 / f"data.{index:04d}.flt.h5", f"float-{index}")
        write(c_lo_2 / f"data.{index:04d}.flt.xmf", f"float-xmf-{index}")
    for index in range(13, 20):
        write(c_lo_3 / f"data.{index:04d}.flt.h5", f"float-{index}")
        write(c_lo_3 / f"data.{index:04d}.flt.xmf", f"float-xmf-{index}")
    for index in range(20, 54):
        write(c_lo_final / f"data.{index:04d}.flt.h5", f"float-{index}")
        write(c_lo_final / f"data.{index:04d}.flt.xmf", f"float-xmf-{index}")

    write(c_lo_3 / "data.0006.dbl.h5", "restart-double-6")
    write(c_lo_3 / "data.0006.dbl.xmf", "restart-xmf-6")
    write(c_lo_3 / "particles.1611.dbl", "restart-particle-1611")
    (c_lo_final / "data.0006.dbl.h5").symlink_to(c_lo_3 / "data.0006.dbl.h5")
    (c_lo_final / "particles.1611.dbl").symlink_to(
        c_lo_3 / "particles.1611.dbl"
    )
    write(c_lo_final / "data.0006.dbl.xmf", "restart-xmf-6")
    for index in range(7, 13):
        write(c_lo_final / f"data.{index:04d}.dbl.h5", f"superseded-double-{index}")
        write(c_lo_final / f"data.{index:04d}.dbl.xmf", f"superseded-xmf-{index}")
    write(c_lo_final / "data.0013.dbl.h5", "endpoint-double-13")
    write(c_lo_final / "data.0013.dbl.xmf", "endpoint-xmf-13")
    write(c_lo_final / "particles.2000.dbl", "superseded-particle")
    write(c_lo_final / "particles.4000.dbl", "superseded-particle")
    write(c_lo_final / "particles.5003.dbl", "endpoint-particle-5003")
    write(
        c_lo_final / "flt.h5.out",
        "".join(f"{index} {index + 1}.0 0.1 {100 + index}\n" for index in range(54)),
    )
    write(
        c_lo_final / "dbl.h5.out",
        "".join(f"{index} {index + 1}.0 0.1 {100 + index}\n" for index in range(14)),
    )

    g_lo = output_root(
        runs, "2026-07-07-g-lo-endpoint-oriented-production", "G-LO"
    )
    write(g_lo / "data.0002.dbl.h5", "valid-restart")
    write(g_lo / "data.0003.dbl.h5", "invalid-partial")

    partial = runs / "2026-07-10-g-lo-hdf5-stall-guarded-continuation"
    write(partial / "G-LO" / "particles" / "problem" / "pluto", "")
    return runs, stage


def test_dry_run_is_non_mutating_and_writes_hashed_plan(tmp_path: Path) -> None:
    module = load_module()
    runs, stage = make_fixture(tmp_path)

    result = module.run_compaction(
        runs_root=runs,
        stage_root=stage,
        execute=False,
        expected_float_size=None,
    )

    assert result["status"] == "dry_run_ready"
    assert (runs / "2026-05-08-c-hi-segment").exists()
    assert (stage / "remote_logs" / "goal038_compaction_pre_manifest.csv").is_file()
    assert (stage / "remote_logs" / "goal038_compaction_pre_manifest.sha256").is_file()


def test_execute_preserves_promoted_surfaces_and_removes_superseded_data(
    tmp_path: Path,
) -> None:
    module = load_module()
    runs, stage = make_fixture(tmp_path)

    result = module.run_compaction(
        runs_root=runs,
        stage_root=stage,
        execute=True,
        expected_float_size=None,
    )

    assert result["status"] == "compaction_complete"
    endpoint = output_root(
        runs, "2026-07-05-c-lo-endpoint-oriented-continuation", "C-LO"
    )
    for index in range(54):
        h5 = endpoint / f"data.{index:04d}.flt.h5"
        xmf = endpoint / f"data.{index:04d}.flt.xmf"
        assert h5.is_file() and not h5.is_symlink()
        assert xmf.is_file() and not xmf.is_symlink()
    assert (endpoint / "data.0006.dbl.h5").is_file()
    assert not (endpoint / "data.0006.dbl.h5").is_symlink()
    assert (endpoint / "particles.1611.dbl").is_file()
    assert not (endpoint / "particles.1611.dbl").is_symlink()
    assert sorted(path.name for path in endpoint.glob("data.*.dbl.h5")) == [
        "data.0006.dbl.h5",
        "data.0013.dbl.h5",
    ]
    assert sorted(path.name for path in endpoint.glob("particles.*.dbl")) == [
        "particles.1611.dbl",
        "particles.5003.dbl",
    ]

    for name in (
        "2026-07-03-c-lo-bounded-execution",
        "2026-07-04-c-lo-bounded-continuation",
        "2026-07-05-c-lo-bounded-continuation-2",
        "2026-05-08-c-hi-segment",
        "2026-05-19-c-hi-fullgrid-startup",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-16node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-48node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-64node",
        "2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node",
    ):
        assert not (runs / name).exists()

    fresh = output_root(
        runs, "2026-06-01-c-hi-fullgrid-agn-impi-fresh", "C-HI"
    )
    assert not (fresh / "data.0008.dbl.h5").exists()
    assert (fresh / "data.0009.dbl.h5").is_file()
    assert not (fresh / "particles.0123.dbl").exists()
    assert (fresh / "particles.4277.dbl").is_file()

    prod = output_root(
        runs, "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64", "C-HI"
    )
    assert not (prod / "data.0010.dbl.h5").exists()
    assert (prod / "data.0011.dbl.h5").is_file()
    assert not (prod / "particles.4500.dbl").exists()
    assert (prod / "particles.5000.dbl").is_file()
    assert (prod / "data.0009.dbl.h5").is_symlink()
    assert (prod / "particles.4277.dbl").is_symlink()

    g_lo = output_root(
        runs, "2026-07-07-g-lo-endpoint-oriented-production", "G-LO"
    )
    assert (g_lo / "data.0002.dbl.h5").is_file()
    assert not (g_lo / "data.0003.dbl.h5").exists()
    assert not (runs / "2026-07-10-g-lo-hdf5-stall-guarded-continuation").exists()
    summary = json.loads(
        (stage / "remote_logs" / "goal038_compaction_summary.json").read_text()
    )
    assert summary["status"] == "compaction_complete"

    second = module.run_compaction(
        runs_root=runs,
        stage_root=stage,
        execute=True,
        expected_float_size=None,
    )
    assert second["status"] == "compaction_complete"
    assert second["freed_manifest_bytes"] == 0


def test_preflight_collision_fails_before_any_mutation(tmp_path: Path) -> None:
    module = load_module()
    runs, stage = make_fixture(tmp_path)
    endpoint = output_root(
        runs, "2026-07-05-c-lo-endpoint-oriented-continuation", "C-LO"
    )
    write(endpoint / "data.0000.flt.h5", "collision")

    with pytest.raises(module.CompactionError, match="destination collision"):
        module.run_compaction(
            runs_root=runs,
            stage_root=stage,
            execute=True,
            expected_float_size=None,
        )

    assert (runs / "2026-05-08-c-hi-segment").exists()
    assert output_root(
        runs, "2026-07-03-c-lo-bounded-execution", "C-LO"
    ).exists()
