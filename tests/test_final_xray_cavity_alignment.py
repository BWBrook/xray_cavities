from __future__ import annotations

import csv
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_final_xray_cavity_alignment.py")
FINAL_INPUT_H5 = (
    "/scratch/bwbrook/xray_cavities_runs/"
    "2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5"
)


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_xray_cavity_alignment", SCRIPT)
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
    path.write_text("\n".join(str(value) for value in values) + "\n")


def write_matrix(path: Path, values: list[list[float]]) -> None:
    path.write_text("\n".join("\t".join(str(value) for value in row) for row in values) + "\n")


def write_xraise_dir(path: Path, *, input_h5: str = FINAL_INPUT_H5, timestep: str = "Timestep_51") -> None:
    path.mkdir(parents=True, exist_ok=True)
    write_vector(path / "x_kpc.tsv", [-1.0, 1.0])
    write_vector(path / "z_kpc.tsv", [-1.0, 1.0])
    write_matrix(path / "xray_1kev_xraise_corrected_mjy_sr.tsv", [[10.0, 20.0], [30.0, 40.0]])
    write_matrix(path / "tracer_max_los.tsv", [[0.0, 0.01], [0.02, 0.0]])
    write_csv(
        path / "xraise_grid_smoke_summary.csv",
        [
            {"metric": "time_myr", "value": 50.0, "unit": "Myr"},
            {"metric": "frequency_hz", "value": 2.417990504024e17, "unit": "Hz"},
            {"metric": "redshift", "value": 0.05, "unit": "dimensionless"},
            {"metric": "raw_xray_max", "value": 44.0, "unit": "mJy sr^-1"},
            {"metric": "corrected_xray_max", "value": 40.0, "unit": "mJy sr^-1"},
            {"metric": "raw_xray_sum", "value": 110.0, "unit": "mJy sr^-1 pixels"},
            {"metric": "corrected_xray_sum", "value": 100.0, "unit": "mJy sr^-1 pixels"},
            {"metric": "correction_ratio_positive_max", "value": 1.2, "unit": "dimensionless"},
            {"metric": "correction_ratio_positive_sum", "value": 4.0, "unit": "dimensionless pixels"},
        ],
        ["metric", "value", "unit"],
    )
    (path / "xraise_grid_smoke_metadata.json").write_text(
        json.dumps(
            {
                "input_h5": input_h5,
                "timestep": timestep,
                "time_myr": 50.0,
                "grid_shape_nz_ny_nx": [2, 2, 2],
            },
            indent=2,
        )
        + "\n"
    )


def write_cavity_dir(path: Path, *, positive_four_pv: float = 2.0e58) -> None:
    path.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "side": "negative_z",
            "time_myr": 50.0,
            "tracer_threshold": 0.005,
            "ambient_tracer_max": 0.001,
            "center_x_kpc": 0.0,
            "center_y_kpc": 0.0,
            "center_z_kpc": -20.0,
            "semi_x_kpc": 4.0,
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
            "center_x_kpc": 0.0,
            "center_y_kpc": 0.0,
            "center_z_kpc": 22.0,
            "semi_x_kpc": 4.5,
            "semi_y_kpc": 5.5,
            "semi_z_kpc": 6.5,
            "projected_area_kpc2": 82.0,
            "ellipsoid_volume_kpc3": 560.0,
            "tracer_extent_volume_kpc3": 180.0,
            "ambient_shell_cells": 22,
            "ambient_shell_volume_kpc3": 55.0,
            "ambient_pressure_code": 0.1,
            "ambient_pressure_dyn_cm2": 1.1e-10,
            "ambient_density_code": 0.2,
            "ambient_density_g_cm3": 2.1e-27,
            "pV_erg": positive_four_pv / 4.0,
            "four_pV_erg": positive_four_pv,
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
    (path / "cavity_stub_metadata.txt").write_text(
        "\n".join(
            [
                f"input_h5={FINAL_INPUT_H5}",
                "timestep=Timestep_51",
                "time_code=15330.069689399999",
                "time_myr=50.0",
                "grid_shape_nz_ny_nx=2,2,2",
            ]
        )
        + "\n"
    )


def write_truth_dir(path: Path) -> None:
    path.mkdir(parents=True)
    write_csv(
        path / "level1_injected_energy.csv",
        [
            {"metric": "time_myr", "value": 50.0, "unit": "Myr"},
            {"metric": "injected_energy_one_sided_elapsed", "value": 1.0e60, "unit": "erg"},
            {"metric": "injected_energy_bipolar_elapsed", "value": 2.0e60, "unit": "erg"},
        ],
        ["metric", "value", "unit"],
    )
    write_csv(
        path / "level2_tracer_lobe_truth.csv",
        [
            {"threshold": "5e-03", "side": "negative_z", "volume_kpc3": 120.0, "total_energy_erg": 8.0e58},
            {"threshold": "5e-03", "side": "positive_z", "volume_kpc3": 180.0, "total_energy_erg": 9.0e58},
            {"threshold": "5e-03", "side": "bipolar_total", "volume_kpc3": 300.0, "total_energy_erg": 1.7e59},
        ],
        ["threshold", "side", "volume_kpc3", "total_energy_erg"],
    )


def write_radio_dir(path: Path) -> None:
    path.mkdir(parents=True)
    write_vector(path / "x_kpc.tsv", [-1.0, 1.0])
    write_vector(path / "z_kpc.tsv", [-1.0, 1.0])
    write_matrix(path / "radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv", [[1.0, 2.0], [3.0, 4.0]])
    rows = [
        {
            "side": "negative_z",
            "particle_count": 2,
            "volume_kpc3": 120.0,
            "lossy_luminosity_doppler_w_hz": 6.0e28,
        },
        {
            "side": "positive_z",
            "particle_count": 3,
            "volume_kpc3": 180.0,
            "lossy_luminosity_doppler_w_hz": 9.0e28,
        },
        {
            "side": "bipolar_total",
            "particle_count": 5,
            "volume_kpc3": 300.0,
            "lossy_luminosity_doppler_w_hz": 1.5e29,
        },
    ]
    write_csv(path / "sparse_particle_radio_lobe_summary.csv", rows, list(rows[0]))


def build_fixture(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    xraise_dir = tmp_path / "xraise"
    cavity_dir = tmp_path / "cavity"
    truth_dir = tmp_path / "truth"
    radio_dir = tmp_path / "radio"
    write_xraise_dir(xraise_dir)
    write_cavity_dir(cavity_dir)
    write_truth_dir(truth_dir)
    write_radio_dir(radio_dir)
    return xraise_dir, cavity_dir, truth_dir, radio_dir


def test_lobe_alignment_is_side_aware_and_bipolar(tmp_path: Path) -> None:
    module = load_script_module()
    xraise_dir, cavity_dir, truth_dir, radio_dir = build_fixture(tmp_path)

    metadata = module.build_package(
        xraise_dir=xraise_dir,
        cavity_dir=cavity_dir,
        truth_dir=truth_dir,
        radio_dir=radio_dir,
        output_dir=tmp_path / "out",
    )

    assert metadata["gate_status"] == "green"
    rows = list(csv.DictReader((tmp_path / "out/final_xray_cavity_alignment_lobes.csv").open()))
    by_side = {row["side"]: row for row in rows}
    assert set(by_side) == {"negative_z", "positive_z", "bipolar_total"}
    assert float(by_side["negative_z"]["cavity_to_level2_volume_ratio"]) == 1.0
    assert float(by_side["positive_z"]["radio_lossy_luminosity_doppler_w_hz"]) == 9.0e28
    assert float(by_side["bipolar_total"]["cavity_four_pV_erg"]) == pytest.approx(6.0e58)
    assert (tmp_path / "out/c_hi_final_endpoint_xray_cavity_alignment.png").exists()


def test_xray_metadata_must_reference_final_endpoint(tmp_path: Path) -> None:
    module = load_script_module()
    xraise_dir, cavity_dir, truth_dir, radio_dir = build_fixture(tmp_path)
    write_xraise_dir(xraise_dir, timestep="Timestep_8")

    with pytest.raises(ValueError, match="X-ray metadata timestep mismatch"):
        module.build_package(
            xraise_dir=xraise_dir,
            cavity_dir=cavity_dir,
            truth_dir=truth_dir,
            radio_dir=radio_dir,
            output_dir=tmp_path / "out",
        )


def test_cavity_rows_reject_nonfinite_age(tmp_path: Path) -> None:
    module = load_script_module()
    _xraise_dir, cavity_dir, _truth_dir, _radio_dir = build_fixture(tmp_path)
    rows = list(csv.DictReader((cavity_dir / "cavity_stub_summary.csv").open()))
    rows[0]["buoyancy_age_myr"] = "nan"

    with pytest.raises(ValueError, match="negative_z cavity buoyancy_age_myr must be finite"):
        module.validate_cavity_rows(rows)


def test_gate_status_marks_volume_mismatch_for_review(tmp_path: Path) -> None:
    module = load_script_module()
    xraise_dir, cavity_dir, truth_dir, radio_dir = build_fixture(tmp_path)
    write_cavity_dir(cavity_dir, positive_four_pv=2.0e58)
    rows = list(csv.DictReader((cavity_dir / "cavity_stub_summary.csv").open()))
    rows[1]["tracer_extent_volume_kpc3"] = "260.0"
    write_csv(cavity_dir / "cavity_stub_summary.csv", rows, list(rows[0]))

    metadata = module.build_package(
        xraise_dir=xraise_dir,
        cavity_dir=cavity_dir,
        truth_dir=truth_dir,
        radio_dir=radio_dir,
        output_dir=tmp_path / "out",
    )

    assert metadata["gate_status"] == "review"


def test_cli_writes_expected_package_files(tmp_path: Path) -> None:
    xraise_dir, cavity_dir, truth_dir, radio_dir = build_fixture(tmp_path)
    output_dir = tmp_path / "out"

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--xraise-dir",
            str(xraise_dir),
            "--cavity-dir",
            str(cavity_dir),
            "--truth-dir",
            str(truth_dir),
            "--radio-dir",
            str(radio_dir),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    assert (output_dir / "final_xray_cavity_alignment_metrics.csv").exists()
    assert (output_dir / "final_xray_cavity_alignment_lobes.csv").exists()
    assert (output_dir / "final_xray_cavity_alignment_metadata.json").exists()
    assert (output_dir / "final_xray_cavity_alignment_summary.md").exists()
