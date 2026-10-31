from __future__ import annotations

import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest


SCRIPT = Path("scripts/science/build_q031_native_emission.py")
SCIENCE_DIR = SCRIPT.resolve().parent


def load_module():
    if str(SCIENCE_DIR) not in sys.path:
        sys.path.insert(0, str(SCIENCE_DIR))
    spec = importlib.util.spec_from_file_location("build_q031_native_emission", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_fake_runtime(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir()
    xraise = root / "xraise.py"
    xraise.write_text(
        "import numpy as np\n"
        "def grid_bremsstrahlung(rho, pressure, *, frequencies, redshifts):\n"
        "    temperature = pressure / rho * 1.0e-5\n"
        "    emission = (rho * rho * 1.0e20)[..., None, None]\n"
        "    return emission, temperature\n"
    )
    apec = root / "apec_corrections.txt"
    np.savetxt(
        apec,
        np.array(
            [
                [np.nan, 0.01, 0.1],
                [0.01, 1.0, 1.1],
                [10.0, 1.2, 1.3],
            ]
        ),
        delimiter=",",
    )
    gaunt = root / "gaunt_lut_2d.npz"
    np.savez(
        gaunt,
        T=np.array([1e5, 1e13]),
        f=np.array([1e16, 1e19]),
        g=np.array([[1.0, 1.1], [1.2, 1.3]]),
    )
    return xraise, apec, gaunt


def write_snapshot(
    path: Path,
    *,
    timestep: str,
    time_code: float,
    current: bool,
) -> None:
    shape = (14, 12, 12)
    rho = np.ones(shape, dtype=np.float32)
    pressure = np.full(shape, 1.0e-5, dtype=np.float32)
    tracer = np.zeros(shape, dtype=np.float32)
    if current:
        shock = np.zeros(shape, dtype=bool)
        shock[1:3, 2:10, 2:10] = True
        shock[11:13, 2:10, 2:10] = True
        rho[shock] = 1.1
        pressure[shock] = 1.3e-5
        tracer[5:7, 4:8, 4:8] = 0.8
        tracer[7:9, 4:8, 4:8] = 0.8
        tracer[4, 3, 3] = np.float32(0.001)
        rho[tracer > 0.01] = 0.5
        pressure[tracer > 0.01] = 0.8e-5
    z = np.array([-7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7], dtype=float)
    x = np.arange(-5.5, 6.0, 1.0)
    y = x.copy()
    zz, yy, xx = np.meshgrid(z, y, x, indexing="ij")
    with h5py.File(path, "w") as h5:
        coords = h5.create_group("cell_coords")
        coords.create_dataset("X", data=xx)
        coords.create_dataset("Y", data=yy)
        coords.create_dataset("Z", data=zz)
        group = h5.create_group(timestep)
        group.attrs["Time"] = time_code
        variables = group.create_group("vars")
        variables.create_dataset("rho", data=rho)
        variables.create_dataset("prs", data=pressure)
        variables.create_dataset("tr1", data=tracer)
        for name in ("vx1", "vx2", "vx3"):
            variables.create_dataset(name, data=np.zeros(shape, dtype=np.float32))


def build_synthetic_fixture(
    root: Path,
    *,
    runtime_root: Path | None = None,
) -> SimpleNamespace:
    """Create a tiny complete CLI fixture, optionally using the real runtime."""

    module = load_module()
    root.mkdir(parents=True)
    baseline = root / "baseline.h5"
    current = root / "current.h5"
    time_code = 40.0 * module.renderer.CODE_TIME_PER_MYR
    write_snapshot(baseline, timestep="Timestep_0", time_code=0.0, current=False)
    write_snapshot(current, timestep="Timestep_40", time_code=time_code, current=True)
    if runtime_root is None:
        xraise, apec, gaunt = write_fake_runtime(root / "runtime")
    else:
        xraise = runtime_root / "xraise.py"
        apec = runtime_root / "apec_corrections.txt"
        gaunt = runtime_root / "gaunt_lut_2d.npz"
        for path in (xraise, apec, gaunt):
            if not path.is_file():
                raise ValueError(f"real runtime fixture input missing: {path}")

    source = root / "source.csv"
    write_csv(
        source,
        [
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "actual_time_myr": 40.0,
                "actual_time_code": time_code,
                "input_h5": str(current),
                "timestep": "Timestep_40",
                "baseline_h5": str(baseline),
                "baseline_timestep": "Timestep_0",
                "shape_nz_ny_nx": "14x12x12",
                "jet_power_one_sided_erg_s": 1e45,
                "selection_rule": "synthetic snapshot-40 smoke",
                "overlap_verification": "synthetic",
            }
        ],
    )
    fronts = root / "fronts.csv"
    write_csv(
        fronts,
        [
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "actual_time_myr": 40.0,
                "side": side,
                "velocity_threshold_factor": 1.0,
                "status": "detected",
                "shock_z_kpc": -6.0 if side == "negative_z" else 6.0,
                "shock_distance_kpc": 6.0,
                "mach_kinematic": 2.0,
            }
            for side in ("negative_z", "positive_z")
        ],
    )
    thresholds = module.native_shock.ShockThresholds(
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
    calibration = root / "calibration.csv"
    calibration_row = thresholds.as_row(environment="cluster_synthetic", source="synthetic")
    write_csv(calibration, [calibration_row])

    with h5py.File(current, "r") as h5:
        tracer = np.asarray(h5["Timestep_40/vars/tr1"], dtype=np.float64)
        current_density = np.asarray(h5["Timestep_40/vars/rho"], dtype=np.float64)
        quantized = float(h5["Timestep_40/vars/tr1"].dtype.type(0.001))
    with h5py.File(baseline, "r") as h5:
        initial_density = np.asarray(h5["Timestep_0/vars/rho"], dtype=np.float64)
    cocoon = tracer > 0.001
    z = np.array([-7, -6, -5, -4, -3, -2, -1, 1, 2, 3, 4, 5, 6, 7])
    dz = module.pluto.derive_widths(z.astype(float))
    cell_volume = dz[:, None, None] * np.ones((1, 12, 12))
    native_energy = root / "native_energy.csv"
    native_rows = []
    shock_rows = []
    for side in module.SIDES:
        zmask = module.side_selector(z, side)
        cocoon_volume = float(np.sum(cell_volume[zmask] * cocoon[zmask]))
        selected_volume = cell_volume[zmask]
        selected_cocoon = cocoon[zmask]
        current_side_density = current_density[zmask]
        initial_side_density = initial_density[zmask]
        lobe_mass = float(
            np.sum(current_side_density[selected_cocoon] * selected_volume[selected_cocoon])
            * module.MASS_FACTOR
        )
        masked_initial_lobe_mass = float(
            np.sum(initial_side_density[selected_cocoon] * selected_volume[selected_cocoon])
            * module.MASS_FACTOR
        )
        current_mass = float(np.sum(current_side_density * selected_volume) * module.MASS_FACTOR)
        initial_mass = float(np.sum(initial_side_density * selected_volume) * module.MASS_FACTOR)
        ambient = ~selected_cocoon
        gas_mass = float(
            np.sum(current_side_density[ambient] * selected_volume[ambient]) * module.MASS_FACTOR
        )
        shock_count = 256 if side == "bipolar_total" else 128
        native_rows.append(
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "side": side,
                "partition_method": "binary_threshold_1e-3",
                "actual_time_myr": 40.0,
                "actual_time_code": time_code,
                "tracer_threshold": "1e-3",
                "threshold_comparison": "float64_stored_value_strict_gt",
                "lobe_cell_equivalent": int(np.count_nonzero(cocoon[zmask])),
                "lobe_volume_kpc3": cocoon_volume,
                "lobe_mass_g": lobe_mass,
                "masked_initial_lobe_mass_g": masked_initial_lobe_mass,
                "current_mass_g": current_mass,
                "initial_mass_g": initial_mass,
                "gas_mass_g": gas_mass,
            }
        )
        shock_rows.append(
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "side": side,
                "threshold_factor": 1.0,
                "actual_time_myr": 40.0,
                "status": (
                    "quantitative_bilateral"
                    if side == "bipolar_total" else "quantitative_seeded_component"
                ),
                "mask_volume_kpc3": shock_count,
                "selected_cell_count": shock_count,
                "ambient_tracer_max": 0.001,
                "ambient_energy_weighting": "binary_full_cell",
                "pressure_excess_threshold": 0.05,
                "density_excess_threshold": 0.03,
                "entropy_excess_threshold": 0.02,
                "control_environment": calibration_row["environment"],
                "control_role": calibration_row["control_role"],
            }
        )
    write_csv(native_energy, native_rows)
    native_shock = root / "native_shock.csv"
    write_csv(native_shock, shock_rows)
    precision = root / "precision.csv"
    write_csv(
        precision,
        [
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "raw_tracer_dtype": "float32",
                "primary_threshold_float64": 0.001,
                "actual_time_myr": 40.0,
                "input_h5": str(current),
                "timestep": "Timestep_40",
                "tracer_min": float(np.min(tracer)),
                "tracer_max": float(np.max(tracer)),
                "tracer_outside_unit_interval_count": int(np.count_nonzero((tracer < 0) | (tracer > 1))),
                "raw_dtype_quantized_threshold": quantized,
                "raw_dtype_quantized_equality_cell_count": int(np.count_nonzero(tracer == quantized)),
                "raw_dtype_quantized_equality_volume_kpc3": float(
                    np.sum(cell_volume * (tracer == quantized))
                ),
                "exact_double_equality_cell_count": int(np.count_nonzero(tracer == 0.001)),
            }
        ],
    )

    retained = root / "retained"
    retained.mkdir()
    for view in module.VIEWS:
        output = retained / f"xraise_grid_{view}deg"
        args = SimpleNamespace(
            input_h5=current,
            timestep="Timestep_40",
            output_dir=output,
            xraise_py=xraise,
            apec_table=apec,
            gaunt_lut=gaunt,
            frequency_hz=module.renderer.DEFAULT_FREQ_HZ,
            redshift=0.05,
            y_chunk=4,
            view_angle_deg=float(view),
            projected_u_bins=12,
            projection_mode="auto",
        )
        module.renderer.run(args)
    return SimpleNamespace(
        case="C-HI",
        snapshot_index=40,
        source_manifest=source,
        shock_dynamics=fronts,
        control_calibration=calibration,
        native_energy_reference=native_energy,
        native_shock_reference=native_shock,
        tracer_precision_reference=precision,
        retained_views_root=retained,
        xraise_py=xraise,
        apec_table=apec,
        gaunt_lut=gaunt,
        output_dir=root / "output",
        cache_dir=root / "cache",
        projected_u_bins=12,
        y_chunk=4,
        geometry_refinement_factor=2,
        frequency_hz=module.renderer.DEFAULT_FREQ_HZ,
        redshift=0.05,
        keep_cache=False,
    )


def test_full_cli_fixture_closes_partitions_and_refuses_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = load_module()
    args = build_synthetic_fixture(tmp_path / "fixture")
    memmaps: list[np.memmap] = []
    create_ratio_cache = module.native_shock._create_ratio_cache
    build_masks = module.native_shock._build_masks
    rmtree = module.shutil.rmtree
    cleanup_observed = False

    def capture_ratio_cache(**kwargs):
        mapping = create_ratio_cache(**kwargs)
        memmaps.extend(mapping.values())
        return mapping

    def capture_masks(**kwargs):
        mapping, diagnostics = build_masks(**kwargs)
        memmaps.extend(mapping.values())
        return mapping, diagnostics

    def assert_closed_before_cleanup(path):
        nonlocal cleanup_observed
        assert Path(path) == args.cache_dir
        assert memmaps and all(array._mmap.closed for array in memmaps)
        cleanup_observed = True
        rmtree(path)

    monkeypatch.setattr(module.native_shock, "_create_ratio_cache", capture_ratio_cache)
    monkeypatch.setattr(module.native_shock, "_build_masks", capture_masks)
    monkeypatch.setattr(module, "shutil", SimpleNamespace(rmtree=assert_closed_before_cleanup))
    result = module.run_case(args)
    assert result["status"] == "validated"
    assert "not physical emissivity acceptance" in result["validation_scope"]
    assert result["scientific_interpretation_status"] == "pending_emissivity_diagnostic_review"
    assert result["views"] == [0, 45, 90]
    assert result["conventions"] == ["retained_linear", "clamp_each_coordinate"]
    assert len(result["density_temperature_distributions"]) == 12
    assert cleanup_observed
    assert memmaps and all(array._mmap.closed for array in memmaps)
    assert not args.cache_dir.exists()
    assert {path.name for path in args.output_dir.iterdir()} == {
        "native_emission_0deg.npz",
        "native_emission_45deg.npz",
        "native_emission_90deg.npz",
        "summary.csv",
        "summary.json",
        "provenance.json",
        "manifest.sha256",
    }
    manifest = (args.output_dir / "manifest.sha256").read_text().splitlines()
    assert len(manifest) == 6
    for line in manifest:
        digest, name = line.split("  ", 1)
        assert digest == module.sha256_file(args.output_dir / name)
    provenance = json.loads((args.output_dir / "provenance.json").read_text())
    assert provenance["status"] == "validated"
    assert provenance["scientific_interpretation_status"] == "pending_emissivity_diagnostic_review"
    assert provenance["projection"]["methods"] == {
        "0deg": "direct_y_axis_sum",
        "45deg": "edge_overlap_uniform_cell_projection",
        "90deg": "edge_overlap_uniform_cell_projection",
    }
    assert provenance["native_hdf5"]["pre_read_identities"] == provenance["native_hdf5"]["post_read_identities"]
    assert result["native_validation"]["tracer_precision"]["raw_dtype_quantized_equality_cell_count"] == 1
    with np.load(args.output_dir / "native_emission_45deg.npz") as maps:
        np.testing.assert_allclose(
            maps["path_whole_kpc"],
            maps["path_cocoon_kpc"] + maps["path_ambient_total_kpc"],
        )
        np.testing.assert_allclose(
            maps["path_ambient_total_kpc"],
            maps["path_shocked_ambient_kpc"] + maps["path_unshocked_ambient_kpc"],
        )
        assert np.isnan(maps["temperature_cocoon_current_retained_linear_k"]).any()
    with pytest.raises(ValueError, match="refusing to overwrite output"):
        module.run_case(args)


def test_keep_cache_retains_closed_memmap_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = load_module()
    args = build_synthetic_fixture(tmp_path / "keep-cache")
    args.keep_cache = True
    memmaps: list[np.memmap] = []
    create_ratio_cache = module.native_shock._create_ratio_cache
    build_masks = module.native_shock._build_masks

    def capture_ratio_cache(**kwargs):
        mapping = create_ratio_cache(**kwargs)
        memmaps.extend(mapping.values())
        return mapping

    def capture_masks(**kwargs):
        mapping, diagnostics = build_masks(**kwargs)
        memmaps.extend(mapping.values())
        return mapping, diagnostics

    monkeypatch.setattr(module.native_shock, "_create_ratio_cache", capture_ratio_cache)
    monkeypatch.setattr(module.native_shock, "_build_masks", capture_masks)

    module.run_case(args)

    assert memmaps and all(array._mmap.closed for array in memmaps)
    assert args.cache_dir.is_dir()
    assert sorted(path.name for path in (args.cache_dir / "ratios_and_masks").iterdir()) == [
        "ambient.npy",
        "density_ratio.npy",
        "entropy.npy",
        "pressure_ratio.npy",
        "selected_mask_0.5.npy",
        "selected_mask_1.npy",
        "selected_mask_2.npy",
    ]
    provenance = json.loads((args.output_dir / "provenance.json").read_text())
    assert provenance["cache_removed_after_manifest"] is False


def test_real_kernel_cli_smoke(tmp_path: Path) -> None:
    runtime = os.environ.get("Q031_REAL_RUNTIME")
    if runtime is None:
        pytest.skip("Q031_REAL_RUNTIME is not configured")
    args = build_synthetic_fixture(tmp_path / "real", runtime_root=Path(runtime))
    command = [
        sys.executable,
        str(SCRIPT.resolve()),
        "--case", args.case,
        "--source-manifest", str(args.source_manifest),
        "--shock-dynamics", str(args.shock_dynamics),
        "--control-calibration", str(args.control_calibration),
        "--native-energy-reference", str(args.native_energy_reference),
        "--native-shock-reference", str(args.native_shock_reference),
        "--tracer-precision-reference", str(args.tracer_precision_reference),
        "--retained-views-root", str(args.retained_views_root),
        "--xraise-py", str(args.xraise_py),
        "--apec-table", str(args.apec_table),
        "--gaunt-lut", str(args.gaunt_lut),
        "--output-dir", str(args.output_dir),
        "--cache-dir", str(args.cache_dir),
        "--projected-u-bins", str(args.projected_u_bins),
        "--y-chunk", str(args.y_chunk),
        "--geometry-refinement-factor", str(args.geometry_refinement_factor),
        "--frequency-hz", str(args.frequency_hz),
        "--redshift", str(args.redshift),
    ]
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    assert "status=validated case=C-HI" in completed.stdout
    assert "RuntimeWarning" not in completed.stderr
    result = json.loads((args.output_dir / "summary.json").read_text())
    assert result["status"] == "validated"
    assert all(
        result["validation_diagnostics"][f"{view}deg"]["tracer_support"]["unexplained_pixel_count"] == 0
        for view in (0, 45, 90)
    )
    provenance = json.loads((args.output_dir / "provenance.json").read_text())
    assert provenance["status"] == "validated"


def test_invalid_shock_side_is_unavailable_not_zero(tmp_path: Path) -> None:
    module = load_module()
    args = build_synthetic_fixture(tmp_path / "invalid")
    rows = module.read_rows(args.shock_dynamics)
    rows[0]["status"] = "unresolved"
    write_csv(args.shock_dynamics, rows)
    with pytest.raises(ValueError, match="shock classification unavailable"):
        module.run_case(args)
    assert not args.output_dir.exists()


def test_source_manifest_and_axis_mismatch_fail_closed(tmp_path: Path) -> None:
    module = load_module()
    manifest = tmp_path / "source.csv"
    write_csv(
        manifest,
        [
            {
                "case": "C-HI",
                "snapshot_index": 40,
                "actual_time_myr": 40,
                "actual_time_code": 1,
                "timestep": "Timestep_40",
                "input_h5": "/tmp/current.h5",
                "baseline_h5": "/tmp/baseline.h5",
                "baseline_timestep": "Timestep_0",
                "shape_nz_ny_nx": "14x12x12",
            }
        ],
    )
    with pytest.raises(ValueError, match="time-code/time-Myr mismatch"):
        module.select_source(manifest, "C-HI")
    baseline, current = tmp_path / "base.h5", tmp_path / "current.h5"
    write_snapshot(baseline, timestep="Timestep_0", time_code=0, current=False)
    write_snapshot(current, timestep="Timestep_40", time_code=40 * module.renderer.CODE_TIME_PER_MYR, current=True)
    with h5py.File(current, "r+") as h5:
        h5["cell_coords/X"][..., 0] += 0.1
    with pytest.raises(ValueError, match="coordinate mismatch"):
        module.lightweight_geometry(
            baseline, "Timestep_0", current, "Timestep_40", (14, 12, 12), tmp_path
        )


def test_retained_source_identity_mismatch_fails_closed(tmp_path: Path) -> None:
    module = load_module()
    view = tmp_path / "xraise_grid_0deg"
    view.mkdir()
    (view / "xraise_grid_smoke_metadata.json").write_text(
        json.dumps(
            {
                "input_h5": "/wrong/source.h5",
                "timestep": "Timestep_40",
                "time_code": 40 * module.renderer.CODE_TIME_PER_MYR,
                "frequency_hz": module.renderer.DEFAULT_FREQ_HZ,
                "redshift": 0.05,
                "grid_shape_nz_ny_nx": [14, 12, 12],
                "y_chunk": 4,
                "projection": {
                    "view_angle_deg": 0,
                    "sky_horizontal_bins": 12,
                    "projected_accumulation": "direct_y_axis_sum",
                },
            }
        )
    )
    with pytest.raises(ValueError, match="input_h5 mismatch"):
        module.validate_retained_metadata(
            retained_dirs={0: view},
            source={"timestep": "Timestep_40", "actual_time_code": str(40 * module.renderer.CODE_TIME_PER_MYR)},
            original_current_path="/expected/source.h5",
            shape=(14, 12, 12),
            projected_u_bins=12,
            y_chunk=4,
            frequency_hz=module.renderer.DEFAULT_FREQ_HZ,
            redshift=0.05,
        )


def test_input_drift_guard_binds_stat_identity_and_hash(tmp_path: Path) -> None:
    module = load_module()
    native = tmp_path / "native.h5"
    compact = tmp_path / "reference.csv"
    native.write_bytes(b"native")
    compact.write_text("a,b\n1,2\n")
    before = module.capture_input_state(native_paths=(native,), hashed_paths=(compact,))
    compact.write_text("a,b\n1,3\n")
    with pytest.raises(ValueError, match="input drift"):
        module.verify_input_state(before, native_paths=(native,), hashed_paths=(compact,))


def test_partition_and_projected_integral_gates_fail_on_deliberate_drift() -> None:
    module = load_module()
    statistics = {
        (region, side): module.RegionStats()
        for region in (*module.REGIONS, "whole") for side in module.SIDES
    }
    for side in module.SIDES:
        statistics[("whole", side)].cell_count = 3
        statistics[("whole", side)].volume_kpc3 = 4.0
        for region in module.REGIONS:
            statistics[(region, side)].cell_count = 1
            statistics[(region, side)].volume_kpc3 = 1.0
    with pytest.raises(ValueError, match="regional volume_kpc3 partition"):
        module.summary_partition_checks(statistics)
    with pytest.raises(ValueError, match="projected test mismatch"):
        module.validate_projected_integral(
            "projected test",
            np.ones((2, 2)),
            np.ones((2, 2)),
            np.array([True, True]),
            5.0,
        )


def test_clamp_is_independent_and_preserves_linear_negative_emissivity() -> None:
    module = load_module()

    class FakeXraise:
        @staticmethod
        def grid_bremsstrahlung(rho, pressure, *, frequencies, redshifts):
            emission = np.ones(rho.shape + (1, 1))
            temperature = np.full_like(rho, 20.0 / module.KEV_PER_K)
            return emission, temperature

    class Apec:
        def __call__(self, points):
            return 11.0 - points[..., 0]

    class Gaunt:
        def __call__(self, points):
            return points[..., 0] / 1e8

    tables = module.TableBundle(Apec(), Gaunt(), (0.01, 10.0), (0.01, 10.0), (1e5, 1e13), (1e16, 1e19))
    values, _temperature, flags = module.cell_emissivity(
        xraise=FakeXraise,
        tables=tables,
        rho_code=np.ones((1, 1, 1)),
        pressure_code=np.ones((1, 1, 1)),
        frequency_hz=module.renderer.DEFAULT_FREQ_HZ,
        redshift=0.05,
    )
    assert values["retained_linear"][0, 0, 0] < 0
    assert values["clamp_each_coordinate"][0, 0, 0] > 0
    assert flags["apec_temperature"][0, 0, 0]
    assert not flags["gaunt_temperature"][0, 0, 0]
    expected = (20.0 / module.KEV_PER_K) / 1e8
    assert values["clamp_each_coordinate"][0, 0, 0] == pytest.approx(expected)


def test_raw_kernel_nonfinite_is_distinct_from_corrected_invalid_diagnostic() -> None:
    module = load_module()

    class FakeXraise:
        @staticmethod
        def grid_bremsstrahlung(rho, pressure, *, frequencies, redshifts):
            return np.full(rho.shape + (1, 1), np.nan), np.full_like(rho, 1e7)

    class Ones:
        def __call__(self, points):
            return np.ones(points.shape[:-1])

    tables = module.TableBundle(Ones(), Ones(), (0.01, 10), (0.01, 10), (1e5, 1e13), (1e16, 1e19))
    emissivity, temperature, flags = module.cell_emissivity(
        xraise=FakeXraise,
        tables=tables,
        rho_code=np.ones((1, 1, 1)),
        pressure_code=np.ones((1, 1, 1)),
        frequency_hz=module.renderer.DEFAULT_FREQ_HZ,
        redshift=0.05,
    )
    stats = module.RegionStats()
    stats.add(
        mask=np.ones((1, 1, 1), dtype=bool),
        volume=np.ones((1, 1, 1)),
        rho={state: np.ones((1, 1, 1)) for state in module.STATES},
        temperature={state: temperature for state in module.STATES},
        emissivity={state: emissivity for state in module.STATES},
        flags={state: flags for state in module.STATES},
    )
    row = stats.output_row("C-HI", "whole", "bipolar_total")
    assert row["current_raw_kernel_nonfinite_cell_count_before_sanitization"] == 1
    assert row["current_retained_linear_nonfinite_cell_count_before_sanitization"] == 0


def test_exact_half_plane_revolution_handles_axis_crossing_and_refinement() -> None:
    module = load_module()
    mask = np.ones((1, 2), dtype=bool)
    coarse = module.exact_abs_u_moments(mask, np.array([-1.0, 0.25, 1.0]), np.array([0.0, 2.0]))
    refined = module.exact_abs_u_moments(
        np.ones((2, 4), dtype=bool),
        np.array([-1.0, -0.375, 0.25, 0.625, 1.0]),
        np.array([0.0, 1.0, 2.0]),
    )
    expected_half = 2.0 * math.pi
    assert coarse["negative_u_revolution_kpc3"] == pytest.approx(expected_half)
    assert coarse["positive_u_revolution_kpc3"] == pytest.approx(expected_half)
    assert refined["symmetrized_revolution_kpc3"] == pytest.approx(coarse["symmetrized_revolution_kpc3"])


@pytest.mark.parametrize("n", [16, 32])
def test_ellipsoid_projection_conserves_voxel_volume_at_all_angles(n: int) -> None:
    module = load_module()
    edges = np.linspace(-2.0, 2.0, n + 1)
    centres = 0.5 * (edges[:-1] + edges[1:])
    zz, yy, xx = np.meshgrid(centres, centres, centres, indexing="ij")
    ellipsoid = (xx / 1.2) ** 2 + (yy / 0.8) ** 2 + (zz / 1.5) ** 2 <= 1
    widths = np.diff(edges)
    geometry = module.snapshot_energy.Geometry(
        centres, centres, centres, widths, widths, widths, np.outer(widths, widths), Path("unused")
    )
    accumulators = module.make_map_accumulators(geometry, n)
    module.project_chunk(
        accumulators=accumulators,
        geometry=geometry,
        start=0,
        stop=n,
        fields={"path_cocoon_kpc": ellipsoid},
        tracer=ellipsoid.astype(float),
    )
    native_volume = float(np.sum(ellipsoid * widths[:, None, None] * widths[None, :, None] * widths[None, None, :]))
    for view, bundle in accumulators.items():
        z_edges = module.renderer.centres_to_edges(centres)
        area = np.diff(z_edges)[:, None] * np.diff(bundle["horizontal_edges"])[None, :]
        projected_volume = float(np.sum(bundle["maps"]["path_cocoon_kpc"] * area))
        assert projected_volume == pytest.approx(native_volume, rel=3e-13, abs=3e-13), view
    analytic_volume = 4 * math.pi * 1.2 * 0.8 * 1.5 / 3
    tolerance = 0.12 if n == 16 else 0.05
    assert abs(native_volume / analytic_volume - 1) < tolerance
