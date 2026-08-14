from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/g_lo_snapshot_science.py")


def load_module():
    science_dir = str(SCRIPT.resolve().parent)
    if science_dir not in sys.path:
        sys.path.insert(0, science_dir)
    spec = importlib.util.spec_from_file_location("g_lo_snapshot_science", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_environment(path: Path, *, mismatch: bool = False) -> None:
    radius = np.linspace(0.0, 20.0 * 3.0856775814913673e21, 21)
    gravity_a = np.full_like(radius, -1.0e-8)
    gravity_b = gravity_a.copy()
    if mismatch:
        gravity_b[-1] *= 1.1
    values = np.column_stack(
        (
            radius,
            np.full_like(radius, 1.0e-27),
            np.full_like(radius, 1.0e-11),
            np.full_like(radius, 1.0e7),
            gravity_a,
            gravity_b,
        )
    )
    np.savetxt(path, values)


def write_snapshot(
    path: Path,
    *,
    index: int,
    time_code: float,
    tracer: np.ndarray | None = None,
    pressure: np.ndarray | None = None,
    vz: np.ndarray | None = None,
) -> None:
    shape = (6, 2, 2)
    tracer = np.zeros(shape) if tracer is None else np.asarray(tracer, dtype=float)
    pressure = np.ones(shape) if pressure is None else np.asarray(pressure, dtype=float)
    vz = np.zeros(shape) if vz is None else np.asarray(vz, dtype=float)
    with h5py.File(path, "w") as h5:
        timestep = h5.create_group(f"Timestep_{index}")
        timestep.attrs["Time"] = time_code
        variables = timestep.create_group("vars")
        variables.create_dataset("rho", data=np.ones(shape))
        variables.create_dataset("prs", data=pressure)
        variables.create_dataset("tr1", data=tracer)
        variables.create_dataset("vx1", data=np.zeros(shape))
        variables.create_dataset("vx2", data=np.zeros(shape))
        variables.create_dataset("vx3", data=vz)
        coordinates = h5.create_group("cell_coords")
        z = np.asarray([-3.0, -2.0, -1.0, 1.0, 2.0, 3.0])
        y = np.asarray([-0.5, 0.5])
        x = np.asarray([-0.5, 0.5])
        zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
        coordinates.create_dataset("X", data=xx)
        coordinates.create_dataset("Y", data=yy)
        coordinates.create_dataset("Z", data=zz)


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_environment_builds_centre_zero_potential_and_rejects_column_drift(tmp_path: Path) -> None:
    module = load_module()
    table = tmp_path / "environment.csv"
    write_environment(table)
    profile = module.load_environment(table)
    assert profile.potential_cm2_s2[0] == 0.0
    assert profile.potential_cm2_s2[-1] == pytest.approx(1.0e-8 * profile.radius_cm[-1])
    assert profile.gravity_max_relative_delta == 0.0

    bad = tmp_path / "bad.csv"
    write_environment(bad, mismatch=True)
    with pytest.raises(ValueError, match="gravity columns disagree"):
        module.load_environment(bad)


def test_fractional_energy_partition_is_complementary() -> None:
    module = load_module()
    rho = np.asarray([[2.0, 2.0]])
    pressure = np.asarray([[3.0, 3.0]])
    velocity_squared = np.asarray([[4.0, 4.0]])
    volume = np.asarray([[1.0, 1.0]])
    potential = np.asarray([[5.0, 5.0]])
    tracer = np.asarray([[0.25, 0.75]])
    fractional = module.tracer_partitions(tracer)[0][2]
    gas = module.slice_energy(
        rho=rho,
        pressure=pressure,
        velocity_squared=velocity_squared,
        weight=1.0 - fractional,
        volume_kpc3=volume,
        potential_cm2_s2=potential,
    )
    lobe = module.slice_energy(
        rho=rho,
        pressure=pressure,
        velocity_squared=velocity_squared,
        weight=fractional,
        volume_kpc3=volume,
        potential_cm2_s2=potential,
    )
    total = module.slice_energy(
        rho=rho,
        pressure=pressure,
        velocity_squared=velocity_squared,
        weight=np.ones_like(tracer),
        volume_kpc3=volume,
        potential_cm2_s2=potential,
    )
    for field in module.ENERGY_FIELDS:
        assert gas[field] + lobe[field] == pytest.approx(total[field])


def test_injected_energy_uses_bipolar_power_and_active_time_cap() -> None:
    module = load_module()
    one, bipolar = module.injected_energy(
        80.0,
        one_sided_power_erg_s=1.0e43,
        jet_start_myr=5.0,
        jet_active_myr=50.0,
    )
    assert one == pytest.approx(1.0e43 * 50.0 * module.SECONDS_PER_MYR)
    assert bipolar == pytest.approx(2.0 * one)


def test_shock_detection_requires_outward_contiguous_disturbance() -> None:
    module = load_module()
    rows = []
    for z in (-4.0, -3.0, -2.0, -1.0, 1.0, 2.0, 3.0, 4.0):
        disturbed = abs(z) >= 3.0
        rows.append(
            {
                "z_kpc": z,
                "dz_kpc": 1.0,
                "rho_code": 2.0 if disturbed else 1.0,
                "pressure_code": 3.0 if disturbed else 1.0,
                "vz_code": (0.02 if z > 0 else -0.02) if disturbed else 0.0,
                "baseline_rho_code": 1.0,
                "baseline_pressure_code": 1.0,
                "baseline_vz_code": 0.0,
            }
        )
    positive = module.detect_shock(
        rows,
        side="positive_z",
        velocity_cut_code=1.0e-4,
        disturbance_fraction=0.05,
        min_contiguous_cells=2,
    )
    negative = module.detect_shock(
        rows,
        side="negative_z",
        velocity_cut_code=1.0e-4,
        disturbance_fraction=0.05,
        min_contiguous_cells=2,
    )
    assert positive is not None and positive["shock_z_kpc"] == 4.0
    assert negative is not None and negative["shock_z_kpc"] == -4.0


def test_local_three_snapshot_fit_recovers_expansion_rate() -> None:
    module = load_module()
    result = module.local_three_point_slope(
        np.asarray([10.0, 20.0, 30.0]),
        np.asarray([5.0, 15.0, 25.0]),
        np.asarray([0.5, 0.5, 0.5]),
        1,
    )
    assert result is not None
    assert result[0] == pytest.approx(1.0)
    assert result[1] > 0.0


def test_run_chain_produces_resumable_fluid_science_surface(tmp_path: Path) -> None:
    module = load_module()
    table = tmp_path / "environment.csv"
    write_environment(table)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    write_snapshot(first / "data.0000.flt.h5", index=0, time_code=0.0)
    tracer = np.zeros((6, 2, 2))
    tracer[2:4] = 0.5
    pressure = np.full((6, 2, 2), 1.2)
    write_snapshot(
        first / "data.0001.flt.h5",
        index=1,
        time_code=module.CODE_TIME_PER_MYR,
        tracer=tracer,
        pressure=pressure,
    )
    write_snapshot(
        second / "data.0001.flt.h5",
        index=1,
        time_code=module.CODE_TIME_PER_MYR,
        tracer=tracer,
        pressure=pressure,
    )
    write_snapshot(
        second / "data.0002.flt.h5",
        index=2,
        time_code=2.0 * module.CODE_TIME_PER_MYR,
        tracer=tracer,
        pressure=pressure,
    )
    output = tmp_path / "output"
    args = argparse.Namespace(
        case="G-LO",
        outputs_dir=[first, second],
        environment_table=table,
        output_root=output,
        jet_power_one_sided_erg_s=1.0e43,
        jet_start_myr=0.0,
        jet_active_myr=50.0,
        tube_radius_kpc=2.0,
        velocity_floor_code=1.0e-4,
        velocity_noise_multiplier=5.0,
        disturbance_fraction=0.05,
        min_contiguous_cells=2,
        resume=False,
        remove_geometry_cache_on_success=True,
    )
    metadata = module.run_chain(args)
    assert metadata["snapshot_count"] == 3
    manifest = read_rows(output / "snapshot_manifest.csv")
    assert [row["snapshot_index"] for row in manifest] == ["0", "1", "2"]
    assert Path(manifest[1]["input_h5"]).parent == second
    energy = read_rows(output / "energy_partition_timeseries.csv")
    primary = [
        row for row in energy
        if row["snapshot_index"] == "1"
        and row["side"] == "bipolar_total"
        and row["partition_method"] == "fractional"
    ]
    assert len(primary) == 1
    assert primary[0]["boundary_status"] == "unmeasured_from_retained_snapshots"
    assert primary[0]["residual_interpretation"] == "not_promoted_to_cocoon_boundary_unresolved"
    assert not (output / "cache").exists()
