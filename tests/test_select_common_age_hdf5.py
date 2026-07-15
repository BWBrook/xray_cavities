from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/select_common_age_hdf5.py")


def load_module():
    spec = importlib.util.spec_from_file_location("select_common_age_hdf5", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_h5(
    path: Path,
    *,
    time_code: float,
    timestep: str = "Timestep_0",
    shape: tuple[int, int, int] = (2, 2, 2),
    missing: str | None = None,
) -> None:
    with h5py.File(path, "w") as h5:
        group = h5.create_group(timestep)
        group.attrs["Time"] = time_code
        variables = group.create_group("vars")
        for name in ("rho", "prs", "tr1", "vx1", "vx2", "vx3"):
            if name != missing:
                variables.create_dataset(name, data=np.ones(shape))


def test_selector_uses_time_metadata_and_writes_endpoint_flags(tmp_path: Path) -> None:
    module = load_module()
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    for age in (10, 20, 30, 40, 50):
        write_h5(outputs / f"data.{age:04d}.flt.h5", time_code=age * module.CODE_TIME_PER_MYR)
    baseline = outputs / "data.0000.flt.h5"
    write_h5(baseline, time_code=0.0)

    rows = module.select_manifest_rows(
        outputs_dir=outputs,
        case="C-HI",
        jet_power_erg_s=1.0e45,
        baseline_h5=baseline,
        baseline_timestep="Timestep_0",
    )

    assert [row["nominal_age_myr"] for row in rows] == [10, 20, 30, 40, 50]
    assert rows[0]["actual_time_myr"] == pytest.approx(10.0)
    assert rows[0]["action"] == "compute_new"
    assert rows[0]["compute_xray"] == "true"
    assert rows[-1]["action"] == "reuse_endpoint_plus_level3"
    assert rows[-1]["compute_xray"] == "false"
    assert rows[-1]["compute_truth_cavity"] == "false"
    assert all(row["compute_level3"] == "true" for row in rows)
    assert all(float(row["baseline_time_myr"]) == pytest.approx(0.0) for row in rows)
    assert all(row["baseline_grid_shape_nz_ny_nx"] == "2x2x2" for row in rows)


def test_selector_fails_on_ambiguous_target(tmp_path: Path) -> None:
    module = load_module()
    write_h5(tmp_path / "data.0001.flt.h5", time_code=10.0 * module.CODE_TIME_PER_MYR)
    write_h5(tmp_path / "data.0002.flt.h5", time_code=10.01 * module.CODE_TIME_PER_MYR)
    baseline = tmp_path / "baseline.flt.h5"
    write_h5(baseline, time_code=0.0)
    with pytest.raises(ValueError, match="ambiguous"):
        module.select_manifest_rows(
            outputs_dir=tmp_path,
            case="C-LO",
            jet_power_erg_s=1.0,
            baseline_h5=baseline,
            baseline_timestep="Timestep_0",
        )


def test_selector_fails_on_missing_target(tmp_path: Path) -> None:
    module = load_module()
    write_h5(tmp_path / "data.0001.flt.h5", time_code=10.0 * module.CODE_TIME_PER_MYR)
    baseline = tmp_path / "baseline.flt.h5"
    write_h5(baseline, time_code=0.0)
    with pytest.raises(ValueError, match="missing target age"):
        module.select_manifest_rows(
            outputs_dir=tmp_path,
            case="G-LO",
            jet_power_erg_s=1.0,
            baseline_h5=baseline,
            baseline_timestep="Timestep_0",
        )


def test_selector_rejects_dataset_shape_mismatch(tmp_path: Path) -> None:
    module = load_module()
    write_h5(tmp_path / "data.0001.flt.h5", time_code=10.0 * module.CODE_TIME_PER_MYR)
    write_h5(
        tmp_path / "data.0002.flt.h5",
        time_code=20.0 * module.CODE_TIME_PER_MYR,
        shape=(2, 2, 3),
    )
    with pytest.raises(ValueError, match="shape"):
        module.inspect_outputs(tmp_path)


def test_selector_rejects_missing_required_dataset(tmp_path: Path) -> None:
    module = load_module()
    write_h5(
        tmp_path / "data.0001.flt.h5",
        time_code=10.0 * module.CODE_TIME_PER_MYR,
        missing="vx3",
    )
    with pytest.raises(ValueError, match="vx3"):
        module.inspect_outputs(tmp_path)


def test_selector_rejects_nonzero_or_shape_incompatible_baseline(tmp_path: Path) -> None:
    module = load_module()
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    for age in (10, 20, 30, 40, 50):
        write_h5(outputs / f"data.{age:04d}.flt.h5", time_code=age * module.CODE_TIME_PER_MYR)
    baseline = tmp_path / "baseline.flt.h5"
    write_h5(baseline, time_code=0.2 * module.CODE_TIME_PER_MYR)

    with pytest.raises(ValueError, match="zero-time"):
        module.select_manifest_rows(
            outputs_dir=outputs, case="C-HI", jet_power_erg_s=1.0,
            baseline_h5=baseline, baseline_timestep="Timestep_0",
        )

    write_h5(baseline, time_code=0.0, shape=(2, 3, 2))
    with pytest.raises(ValueError, match="baseline grid shape"):
        module.select_manifest_rows(
            outputs_dir=outputs, case="C-HI", jet_power_erg_s=1.0,
            baseline_h5=baseline, baseline_timestep="Timestep_0",
        )


def test_selector_combines_promoted_multi_segment_case_chain(tmp_path: Path) -> None:
    module = load_module()
    early = tmp_path / "early"
    late = tmp_path / "late"
    early.mkdir()
    late.mkdir()
    for age in (10, 20, 30):
        write_h5(early / f"data.{age:04d}.flt.h5", time_code=age * module.CODE_TIME_PER_MYR)
    for age in (40, 50):
        write_h5(late / f"data.{age:04d}.flt.h5", time_code=age * module.CODE_TIME_PER_MYR)
    baseline = early / "data.0000.flt.h5"
    write_h5(baseline, time_code=0.0)

    rows = module.select_manifest_rows(
        outputs_dirs=[early, late],
        case="G-LO",
        jet_power_erg_s=1.0e43,
        baseline_h5=baseline,
        baseline_timestep="Timestep_0",
    )

    assert [Path(row["input_h5"]).parent for row in rows] == [early, early, early, late, late]
