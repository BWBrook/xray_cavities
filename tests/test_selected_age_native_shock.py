from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np


SCRIPT = Path("scripts/science/build_selected_age_native_shock.py")


def load_module():
    science_dir = str(SCRIPT.resolve().parent)
    if science_dir not in sys.path:
        sys.path.insert(0, science_dir)
    spec = importlib.util.spec_from_file_location("build_selected_age_native_shock", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_environment(path: Path) -> None:
    radius = np.linspace(0.0, 20.0 * 3.0856775814913673e21, 101)
    gravity = np.full_like(radius, -1.0e-8)
    np.savetxt(
        path,
        np.column_stack(
            (
                radius,
                np.full_like(radius, 1.0e-27),
                np.full_like(radius, 1.0e-11),
                np.full_like(radius, 1.0e7),
                gravity,
                gravity,
            )
        ),
    )


def write_snapshot(path: Path, *, timestep: str, time_code: float, shocked: bool) -> None:
    shape = (12, 10, 10)
    rho = np.ones(shape)
    pressure = np.ones(shape)
    vz = np.zeros(shape)
    if shocked:
        region = np.zeros(shape, dtype=bool)
        region[1:3, 1:9, 1:9] = True
        region[9:11, 1:9, 1:9] = True
        rho[region] = 1.1
        pressure[region] = 1.3
        vz[region] = 0.1
    with h5py.File(path, "w") as h5:
        group = h5.create_group(timestep)
        group.attrs["Time"] = time_code
        variables = group.create_group("vars")
        variables.create_dataset("rho", data=rho)
        variables.create_dataset("prs", data=pressure)
        variables.create_dataset("tr1", data=np.zeros(shape))
        variables.create_dataset("vx1", data=np.zeros(shape))
        variables.create_dataset("vx2", data=np.zeros(shape))
        variables.create_dataset("vx3", data=vz)
        coords = h5.create_group("cell_coords")
        z = np.asarray([-6.0, -5.0, -4.0, -3.0, -2.0, -1.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
        y = np.linspace(-2.25, 2.25, shape[1])
        x = np.linspace(-2.25, 2.25, shape[2])
        zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
        coords.create_dataset("X", data=xx)
        coords.create_dataset("Y", data=yy)
        coords.create_dataset("Z", data=zz)


def test_selected_age_native_shock_builds_bilateral_seeded_energy_product(tmp_path: Path) -> None:
    module = load_module()
    baseline = tmp_path / "baseline.h5"
    target = tmp_path / "target.h5"
    environment = tmp_path / "environment.csv"
    write_snapshot(baseline, timestep="Timestep_0", time_code=0.0, shocked=False)
    write_snapshot(target, timestep="Timestep_10", time_code=10.0 * 306.6013937879523, shocked=True)
    write_environment(environment)
    source = tmp_path / "source.csv"
    write_rows(source, [{
        "case": "G-LO",
        "snapshot_index": 10,
        "actual_time_myr": 10.0,
        "actual_time_code": 10.0 * 306.6013937879523,
        "input_h5": str(target),
        "timestep": "Timestep_10",
        "baseline_h5": str(baseline),
        "baseline_timestep": "Timestep_0",
        "shape_nz_ny_nx": "12x10x10",
        "jet_power_one_sided_erg_s": 1.0e43,
    }])
    shock = tmp_path / "shock.csv"
    write_rows(shock, [
        {
            "case": "G-LO", "snapshot_index": 10, "side": side,
            "velocity_threshold_factor": 1.0, "status": "detected",
            "shock_distance_kpc": 5.0, "mach_kinematic": 2.0,
        }
        for side in ("negative_z", "positive_z")
    ])
    thresholds = module.ShockThresholds(
        pressure_excess=0.05,
        density_excess=0.03,
        entropy_excess=0.02,
        control_sample_count=1000,
        control_joint_exceedance_fraction=0.0,
        pressure_control_quantile=0.001,
        density_control_quantile=0.001,
        entropy_control_quantile=0.001,
        pressure_control_max=0.002,
        density_control_max=0.002,
        entropy_control_max=0.002,
    )
    calibration = tmp_path / "calibration.csv"
    write_rows(calibration, [thresholds.as_row(environment="group_002031", source="synthetic")])

    metadata = module.analyze_case(
        case="G-LO",
        source_manifest=source,
        shock_dynamics=shock,
        environment_table=environment,
        control_calibration=calibration,
        output_root=tmp_path / "output",
    )

    assert metadata["status"] == "complete_selected_age_native_shock_partition"
    rows = module.read_rows(tmp_path / "output" / "native_shock_energy_selected_age.csv")
    assert len(rows) == 9
    primary = [row for row in rows if row["threshold_factor"] == "1.0"]
    assert {row["status"] for row in primary} == {
        "quantitative_seeded_component",
        "quantitative_bilateral",
    }
    bipolar = next(row for row in primary if row["side"] == "bipolar_total")
    assert float(bipolar["total_delta_erg"]) > 0.0
    assert float(bipolar["irreversible_heating_erg"]) > 0.0
    assert float(bipolar["selected_cell_count"]) == 256.0
    assert not (tmp_path / "output" / "cache").exists()
