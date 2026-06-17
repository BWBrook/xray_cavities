from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/pluto_h5_level3_ambient_extract.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("pluto_h5_level3_ambient_extract", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_h5(
    path: Path,
    *,
    timestep: str,
    prs: np.ndarray,
    tr1: np.ndarray,
    vx1: np.ndarray,
    x_offset: float = 0.0,
    z_offset: float = 0.0,
) -> None:
    nz, ny, nx = prs.shape
    with h5py.File(path, "w") as h5:
        group = h5.create_group(timestep)
        group.attrs["Time"] = 1.0
        vars_group = group.create_group("vars")
        vars_group.create_dataset("rho", data=np.ones_like(prs))
        vars_group.create_dataset("prs", data=prs)
        vars_group.create_dataset("tr1", data=tr1)
        vars_group.create_dataset("vx1", data=vx1)
        vars_group.create_dataset("vx2", data=np.zeros_like(prs))
        vars_group.create_dataset("vx3", data=np.zeros_like(prs))
        coords = h5.create_group("cell_coords")
        z = np.array([-0.5, 0.5])[:nz] + z_offset
        y = np.arange(ny, dtype=float)
        x = np.arange(nx, dtype=float) + x_offset
        zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
        coords.create_dataset("X", data=xx)
        coords.create_dataset("Y", data=yy)
        coords.create_dataset("Z", data=zz)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_extract_level3_ambient_energy_respects_final_tracer_mask(tmp_path: Path) -> None:
    module = load_script_module()
    baseline = tmp_path / "baseline.h5"
    final = tmp_path / "final.h5"
    out = tmp_path / "level3.csv"

    shape = (2, 1, 2)
    write_h5(
        baseline,
        timestep="Timestep_0",
        prs=np.ones(shape),
        tr1=np.zeros(shape),
        vx1=np.zeros(shape),
    )
    final_tracer = np.array([[[0.0, 0.01]], [[0.0, 0.0]]])
    final_prs = np.array([[[3.0, 100.0]], [[5.0, 7.0]]])
    final_vx1 = np.array([[[2.0, 9.0]], [[4.0, 6.0]]])
    write_h5(final, timestep="Timestep_1", prs=final_prs, tr1=final_tracer, vx1=final_vx1)

    module.extract_level3(
        baseline_h5=baseline,
        baseline_timestep="Timestep_0",
        final_h5=final,
        final_timestep="Timestep_1",
        output_csv=out,
        tracer_threshold=5.0e-3,
    )

    rows = {row["side"]: row for row in read_rows(out)}
    assert rows["negative_z"]["ambient_cell_count"] == "1"
    assert rows["positive_z"]["ambient_cell_count"] == "2"
    assert rows["bipolar_total"]["ambient_cell_count"] == "3"

    unit_energy = module.UNIT_ENERGY_ERG
    gamma_minus_one = module.GAMMA_GAS - 1.0
    expected_thermal_code = ((3.0 - 1.0) + (5.0 - 1.0) + (7.0 - 1.0)) / gamma_minus_one
    expected_kinetic_code = 0.5 * (2.0**2 + 4.0**2 + 6.0**2)
    assert float(rows["bipolar_total"]["thermal_delta_erg"]) == pytest.approx(
        expected_thermal_code * unit_energy
    )
    assert float(rows["bipolar_total"]["kinetic_delta_erg"]) == pytest.approx(
        expected_kinetic_code * unit_energy
    )


def test_extract_level3_rejects_shape_mismatch(tmp_path: Path) -> None:
    module = load_script_module()
    baseline = tmp_path / "baseline.h5"
    final = tmp_path / "final.h5"
    write_h5(
        baseline,
        timestep="Timestep_0",
        prs=np.ones((2, 1, 2)),
        tr1=np.zeros((2, 1, 2)),
        vx1=np.zeros((2, 1, 2)),
    )
    write_h5(
        final,
        timestep="Timestep_1",
        prs=np.ones((1, 1, 2)),
        tr1=np.zeros((1, 1, 2)),
        vx1=np.zeros((1, 1, 2)),
    )

    with pytest.raises(ValueError, match="shape mismatch"):
        module.extract_level3(
            baseline_h5=baseline,
            baseline_timestep="Timestep_0",
            final_h5=final,
            final_timestep="Timestep_1",
            output_csv=tmp_path / "out.csv",
        )


def test_extract_level3_rejects_coordinate_mismatch(tmp_path: Path) -> None:
    module = load_script_module()
    baseline = tmp_path / "baseline.h5"
    final = tmp_path / "final.h5"
    shape = (2, 1, 2)
    write_h5(
        baseline,
        timestep="Timestep_0",
        prs=np.ones(shape),
        tr1=np.zeros(shape),
        vx1=np.zeros(shape),
    )
    write_h5(
        final,
        timestep="Timestep_1",
        prs=np.ones(shape),
        tr1=np.zeros(shape),
        vx1=np.zeros(shape),
        x_offset=0.25,
    )

    with pytest.raises(ValueError, match="coordinate mismatch.*X"):
        module.extract_level3(
            baseline_h5=baseline,
            baseline_timestep="Timestep_0",
            final_h5=final,
            final_timestep="Timestep_1",
            output_csv=tmp_path / "out.csv",
        )
