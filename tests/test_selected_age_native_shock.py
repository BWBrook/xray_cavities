from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import h5py
import numpy as np
import pytest


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


@pytest.mark.parametrize("valid_front", [True, False])
def test_selected_age_native_shock_builds_bilateral_seeded_energy_product(tmp_path: Path, valid_front: bool) -> None:
    module = load_module()
    baseline = tmp_path / "baseline.h5"
    target = tmp_path / "target.h5"
    environment = tmp_path / "environment.csv"
    write_snapshot(baseline, timestep="Timestep_0", time_code=0.0, shocked=False)
    write_snapshot(target, timestep="Timestep_10", time_code=10.0 * 306.6013937879523, shocked=True)
    # Retained t0 may already contain a nozzle. Keep its energy in the actual
    # baseline, rather than silently replacing it by a tracer-free atmosphere.
    for path, timestep in ((baseline, "Timestep_0"), (target, "Timestep_10")):
        with h5py.File(path, "r+") as h5:
            variables = h5[f"/{timestep}/vars"]
            variables["rho"][5, 5, 5] = 2.0
            variables["prs"][5, 5, 5] = 4.0
            variables["vx3"][5, 5, 5] = 0.2
            del variables["tr1"]
            tracer = np.zeros((12, 10, 10), dtype=np.float32)
            tracer[5, 5, 5] = 0.8
            if path == target:
                tracer[6, 5, 5] = np.float32(0.001)
            variables.create_dataset("tr1", data=tracer)
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
            "velocity_threshold_factor": 1.0, "status": "detected" if valid_front else "unresolved",
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
    bipolar = next(row for row in primary if row["side"] == "bipolar_total")
    if valid_front:
        assert {row["status"] for row in primary} == {
            "quantitative_seeded_component", "quantitative_bilateral",
        }
        assert float(bipolar["total_delta_erg"]) > 0.0
        assert float(bipolar["irreversible_heating_erg"]) > 0.0
        assert float(bipolar["selected_cell_count"]) == 256.0
    else:
        assert bipolar["status"] == "unresolved_bilateral_gate"
        assert bipolar["total_delta_erg"] == ""
    native_rows = module.read_rows(tmp_path / "output" / "native_energy_selected_age.csv")
    assert len(native_rows) == metadata["native_energy_row_count"] == 12
    for side in ("negative_z", "positive_z", "bipolar_total"):
        side_rows = [row for row in native_rows if row["side"] == side]
        retained = float(side_rows[0]["retained_energy_erg"])
        for row in side_rows:
            assert float(row["lobe_total_erg"]) + float(row["gas_total_delta_erg"]) == pytest.approx(retained, rel=1e-12)
            assert float(row["lobe_region_total_delta_erg"]) + float(row["ambient_region_total_delta_erg"]) == pytest.approx(retained, rel=1e-12)
            assert float(row["lobe_region_total_delta_erg"]) == pytest.approx(0.0, abs=1e30)
            assert float(row["lobe_total_erg"]) == pytest.approx(float(row["masked_initial_lobe_total_erg"]))
            assert float(row["lobe_volume_kpc3"]) + float(row["gas_volume_kpc3"]) == pytest.approx(325.0 if side == "bipolar_total" else 162.5)
            for field in module.ENERGY_FIELDS:
                assert float(row[f"lobe_{field}"]) + float(row[f"gas_{field}"]) == pytest.approx(float(row[f"current_{field}"]))
                assert np.isfinite(float(row[f"initial_{field}"]))
            for component in ("thermal", "kinetic", "gravitational"):
                scale = max(abs(float(row[f"lobe_{component}_erg"])), abs(float(row[f"gas_{component}_delta_erg"])), 1.0)
                assert abs(float(row[f"allocation_{component}_invariant_residual_erg"])) <= 1e-12 * scale
                assert abs(float(row[f"region_{component}_invariant_residual_erg"])) <= 1e-12 * scale
    binary = next(row for row in native_rows if row["side"] == "bipolar_total" and row["partition_method"] == "binary_threshold_1e-3")
    assert float(binary["lobe_volume_kpc3"]) == pytest.approx(0.75)
    assert float(binary["masked_initial_lobe_total_erg"]) > 0
    precision = module.read_rows(tmp_path / "output" / "tracer_threshold_precision.csv")[0]
    assert precision["raw_tracer_dtype"] == "float32"
    assert int(precision["exact_double_equality_cell_count"]) == 0
    assert int(precision["raw_dtype_quantized_equality_cell_count"]) == 1
    assert float(precision["raw_dtype_quantized_equality_volume_kpc3"]) == pytest.approx(0.375)
    assert float(precision["raw_dtype_quantized_equality_pressure_volume_erg"]) == pytest.approx(0.375 * module.UNIT_ENERGY_ERG)
    assert float(precision["raw_dtype_quantized_equality_kinetic_erg"]) == 0
    assert float(precision["raw_dtype_quantized_equality_gravitational_erg"]) > 0
    manifest_text = (tmp_path / "output" / "local_asset_manifest.sha256").read_text()
    assert "native_energy_selected_age.csv" in manifest_text
    assert "tracer_threshold_precision.csv" in manifest_text
    assert not (tmp_path / "output" / "cache").exists()


def test_nonfinite_tracer_fails_before_ambient_classification(tmp_path: Path) -> None:
    module = load_module()
    baseline, target = tmp_path / "base.h5", tmp_path / "target.h5"
    write_snapshot(baseline, timestep="Timestep_0", time_code=0, shocked=False)
    write_snapshot(target, timestep="Timestep_10", time_code=10, shocked=True)
    with h5py.File(target, "r+") as h5:
        h5["Timestep_10/vars/tr1"][0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="non-finite tracer"):
        module._create_ratio_cache(
            baseline_h5_path=baseline, baseline_timestep="Timestep_0",
            target_h5_path=target, target_timestep="Timestep_10",
            shape=(12, 10, 10), cache_root=tmp_path / "cache",
        )
    with pytest.raises(ValueError, match="non-finite tracer"):
        module.tracer_partitions(np.asarray([0.0, np.nan, 1.0]))


@pytest.mark.parametrize("in_baseline", [False, True])
@pytest.mark.parametrize("field, bad_value", [
    ("rho", np.nan), ("prs", np.inf), ("rho", 0.0), ("prs", -1.0),
    ("vx1", np.nan), ("vx2", np.inf), ("vx3", -np.inf),
])
def test_invalid_fluid_slab_fails_before_energy_sums(tmp_path: Path, in_baseline: bool,
                                                  field: str, bad_value: float) -> None:
    module = load_module()
    baseline, target = tmp_path / "base.h5", tmp_path / "target.h5"
    write_snapshot(baseline, timestep="Timestep_0", time_code=0, shocked=False)
    write_snapshot(target, timestep="Timestep_10", time_code=10, shocked=True)
    path, timestep = (baseline, "Timestep_0") if in_baseline else (target, "Timestep_10")
    with h5py.File(path, "r+") as h5:
        h5[f"{timestep}/vars/{field}"][0, 0, 0] = bad_value
    arguments = dict(baseline_h5_path=baseline, baseline_timestep="Timestep_0",
                     target_h5_path=target, target_timestep="Timestep_10")
    if field in ("rho", "prs"):
        with pytest.raises(ValueError, match="non-finite or non-positive density/pressure"):
            module._create_ratio_cache(**arguments, shape=(12, 10, 10), cache_root=tmp_path / "ratios")
    environment = tmp_path / "environment.csv"
    write_environment(environment)
    geometry = module.build_geometry(baseline_h5=baseline, baseline_timestep="Timestep_0",
                                     shape=(12, 10, 10), environment=module.load_environment(environment),
                                     cache_path=tmp_path / "phi.npy")
    with pytest.raises(ValueError, match="non-finite"):
        module._integrate_masks(**arguments, geometry=geometry, masks={})


def test_native_allocation_uses_cellwise_changes_when_domain_totals_cancel() -> None:
    module = load_module()
    values = {name: module.empty_energy_totals() for name in (
        "lobe", "ambient", "masked_initial_lobe", "initial", "current",
        "lobe_region_delta", "ambient_region_delta", "retained_delta",
    )}
    # A large, unchanged atmosphere hides a small change in domain totals.
    for name, energy in (("lobe", 103.0), ("masked_initial_lobe", 100.0),
                         ("lobe_region_delta", 3.0), ("ambient_region_delta", 2.0),
                         ("retained_delta", 5.0), ("initial", 1e30),
                         ("current", 1e30), ("ambient", 1e30)):
        values[name]["thermal_erg"] = energy
    source = {"snapshot_index": 10, "actual_time_code": 3066.0, "actual_time_myr": 10.0}
    row = module._native_energy_rows("G-LO", source,
                                    {("binary_threshold_1e-3", "bipolar_total"): values}, 5.0, 10.0)[0]
    assert row["gas_thermal_delta_erg"] == -98.0
    assert row["retained_energy_erg"] == 5.0
    assert row["unattributed_residual_erg"] == 5.0
    assert row["closure_fraction_of_injected"] == 0.5
    assert row["allocation_thermal_invariant_residual_erg"] == 0.0
