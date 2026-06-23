from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_final_45deg_viewing_angle_broadening.py")
FINAL_INPUT_H5 = (
    "/scratch/bwbrook/xray_cavities_runs/"
    "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5"
)


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_45deg_viewing_angle_broadening", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str], *, delimiter: str = ",") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def write_vector(path: Path, values: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(value) for value in values) + "\n")


def write_matrix(path: Path, values: list[list[float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join("\t".join(str(value) for value in row) for row in values) + "\n")


def xraise_summary_rows() -> list[dict[str, object]]:
    return [
        {"metric": "time_myr", "value": 50.0, "unit": "Myr"},
        {"metric": "frequency_hz", "value": 2.417990504024e17, "unit": "Hz"},
        {"metric": "redshift", "value": 0.05, "unit": "dimensionless"},
        {"metric": "raw_xray_max", "value": 22.0, "unit": "mJy sr^-1"},
        {"metric": "corrected_xray_max", "value": 20.0, "unit": "mJy sr^-1"},
        {"metric": "raw_xray_sum", "value": 44.0, "unit": "mJy sr^-1 pixels"},
        {"metric": "corrected_xray_sum", "value": 40.0, "unit": "mJy sr^-1 pixels"},
        {"metric": "correction_ratio_positive_max", "value": 1.2, "unit": "dimensionless"},
        {"metric": "correction_ratio_positive_sum", "value": 4.0, "unit": "dimensionless pixels"},
    ]


def write_xraise_dir(path: Path, *, view_angle: float | None) -> None:
    write_vector(path / "x_kpc.tsv", [-1.0, 1.0])
    if view_angle is not None:
        write_vector(path / "u_kpc.tsv", [-1.0, 1.0])
    write_vector(path / "z_kpc.tsv", [-1.0, 1.0])
    write_matrix(path / "xray_1kev_xraise_corrected_mjy_sr.tsv", [[10.0, 20.0], [30.0, 40.0]])
    write_matrix(path / "tracer_max_los.tsv", [[0.0, 0.01], [0.02, 0.0]])
    write_csv(path / "xraise_grid_smoke_summary.csv", xraise_summary_rows(), ["metric", "value", "unit"])
    metadata = {
        "input_h5": FINAL_INPUT_H5,
        "timestep": "Timestep_51",
        "time_myr": 50.0,
        "grid_shape_nz_ny_nx": [2, 2, 2],
    }
    if view_angle is not None:
        metadata["projection"] = {
            "view_angle_deg": view_angle,
            "sky_horizontal_axis": "u = x*cos(theta) - y*sin(theta)",
            "sky_horizontal_bins": 2,
        }
    (path / "xraise_grid_smoke_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


def cavity_rows() -> list[dict[str, object]]:
    return [
        {
            "side": "negative_z",
            "time_myr": 50.0,
            "tracer_threshold": 0.005,
            "ambient_tracer_max": 0.001,
            "center_x_kpc": 2.0,
            "center_y_kpc": 4.0,
            "center_z_kpc": -20.0,
            "semi_x_kpc": 3.0,
            "semi_y_kpc": 5.0,
            "semi_z_kpc": 6.0,
            "projected_area_kpc2": 75.0,
            "ellipsoid_volume_kpc3": 500.0,
            "tracer_extent_volume_kpc3": 120.0,
            "ambient_shell_cells": 20,
            "ambient_shell_volume_kpc3": 50.0,
            "ambient_pressure_code": 0.1,
            "ambient_pressure_dyn_cm2": 1.0e-10,
            "ambient_density_code": 0.2,
            "ambient_density_g_cm3": 2.0e-27,
            "pV_erg": 1.0e58,
            "four_pV_erg": 4.0e58,
            "cavity_distance_kpc": 20.0,
            "sound_speed_km_s": 900.0,
            "sound_age_myr": 15.0,
            "gravity_hse_cm_s2": 1.0e-8,
            "buoyancy_age_myr": 20.0,
            "refill_age_myr": 12.0,
            "inner_shell_pressure_code": 0.11,
            "outer_shell_pressure_code": 0.09,
            "inner_shell_radius_kpc": 21.0,
            "outer_shell_radius_kpc": 22.0,
        },
        {
            "side": "positive_z",
            "time_myr": 50.0,
            "tracer_threshold": 0.005,
            "ambient_tracer_max": 0.001,
            "center_x_kpc": -1.0,
            "center_y_kpc": 2.0,
            "center_z_kpc": 22.0,
            "semi_x_kpc": 4.0,
            "semi_y_kpc": 6.0,
            "semi_z_kpc": 8.0,
            "projected_area_kpc2": 82.0,
            "ellipsoid_volume_kpc3": 560.0,
            "tracer_extent_volume_kpc3": 180.0,
            "ambient_shell_cells": 22,
            "ambient_shell_volume_kpc3": 55.0,
            "ambient_pressure_code": 0.1,
            "ambient_pressure_dyn_cm2": 1.1e-10,
            "ambient_density_code": 0.2,
            "ambient_density_g_cm3": 2.1e-27,
            "pV_erg": 2.0e58,
            "four_pV_erg": 8.0e58,
            "cavity_distance_kpc": 22.0,
            "sound_speed_km_s": 920.0,
            "sound_age_myr": 16.0,
            "gravity_hse_cm_s2": 1.1e-8,
            "buoyancy_age_myr": 21.0,
            "refill_age_myr": 13.0,
            "inner_shell_pressure_code": 0.11,
            "outer_shell_pressure_code": 0.09,
            "inner_shell_radius_kpc": 22.0,
            "outer_shell_radius_kpc": 23.0,
        },
    ]


def write_cavity_dir(path: Path) -> None:
    rows = cavity_rows()
    write_csv(path / "cavity_stub_summary.csv", rows, list(rows[0]))
    write_csv(
        path / "cavity_ellipse_boundary_0deg.tsv",
        [
            {"side": "negative_z", "x_kpc": -1.0, "z_kpc": -1.0},
            {"side": "negative_z", "x_kpc": 1.0, "z_kpc": -1.0},
            {"side": "positive_z", "x_kpc": -1.0, "z_kpc": 1.0},
            {"side": "positive_z", "x_kpc": 1.0, "z_kpc": 1.0},
        ],
        ["side", "x_kpc", "z_kpc"],
        delimiter="\t",
    )


def build_fixture(tmp_path: Path, *, target_view_angle: float = 45.0) -> tuple[Path, Path]:
    baseline = tmp_path / "baseline"
    output = tmp_path / "out"
    write_xraise_dir(baseline / "xraise_grid", view_angle=None)
    write_cavity_dir(baseline / "cavity_stub")
    write_xraise_dir(output / "xraise_grid_45deg", view_angle=target_view_angle)
    write_cavity_dir(output / "cavity_stub")
    remote_logs = output / "remote_logs"
    remote_logs.mkdir(parents=True)
    (remote_logs / "c_hi_final_45deg_viewing_angle_broadening.out").write_text(
        "\n".join(
            [
                "jobid=699815.kunanyi-ohpc",
                "stage_dir=/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle",
                "analysis_root=/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening",
                "hdf5_preflight=passed",
                "xray_45deg_validation=passed",
                "cavity_validation=passed",
                "finished_utc=2026-06-23T08:06:05Z",
            ]
        )
        + "\n"
    )
    (remote_logs / "c_hi_final_45deg_viewing_angle_broadening.err").write_text("")
    (remote_logs / "final_45deg_viewing_angle_broadening_2026-06-23.tar.gz").write_bytes(b"fake archive\n")
    return baseline, output


def test_projected_boundary_uses_3d_x_y_extent() -> None:
    module = load_script_module()
    rows = module.projected_boundary_rows(cavity_rows(), view_angle_deg=45.0, samples=17)
    first_negative = next(row for row in rows if row["side"] == "negative_z")

    expected_center = (2.0 - 4.0) / 2**0.5
    expected_semi = ((3.0 / 2**0.5) ** 2 + (5.0 / 2**0.5) ** 2) ** 0.5
    assert first_negative["u_kpc"] == pytest.approx(expected_center + expected_semi)
    assert first_negative["z_kpc"] == pytest.approx(-20.0)


def test_build_package_writes_expected_closeout_files(tmp_path: Path) -> None:
    module = load_script_module()
    baseline, output = build_fixture(tmp_path)

    metadata = module.build_package(baseline_dir=baseline, output_dir=output)

    assert metadata["status"] == "complete_product"
    assert metadata["target_view_angle_deg"] == 45.0
    assert (output / "c_hi_final_45deg_viewing_angle_broadening.png").exists()
    assert (output / "viewing_angle_comparison.csv").exists()
    assert (output / "projection_metrics.csv").exists()
    assert (output / "cavity_energy_convention.csv").exists()
    assert (output / "cavity_stub/cavity_ellipse_boundary_45deg.tsv").exists()


def test_build_package_rejects_non_45deg_target(tmp_path: Path) -> None:
    module = load_script_module()
    baseline, output = build_fixture(tmp_path, target_view_angle=0.0)

    with pytest.raises(ValueError, match="expected 45 deg product"):
        module.build_package(baseline_dir=baseline, output_dir=output)


def test_cli_writes_metadata(tmp_path: Path) -> None:
    baseline, output = build_fixture(tmp_path)

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--baseline-dir",
            str(baseline),
            "--output-dir",
            str(output),
        ],
        check=True,
    )

    metadata = json.loads((output / "final_45deg_viewing_angle_metadata.json").read_text())
    assert metadata["remote_job_id"] == "699815.kunanyi-ohpc"
