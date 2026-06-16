from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/build_final_observational_product_readiness.py")


def load_script_module():
    spec = importlib.util.spec_from_file_location("build_final_observational_product_readiness", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_vector(path: Path, values: list[float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(value) for value in values) + "\n")


def write_matrix(path: Path, values: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join("\t".join(f"{value:.8g}" for value in row) for row in values) + "\n")


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str], *, delimiter: str = ",") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)


def make_fixture(tmp_path: Path, *, x_half_width: float = 120.0) -> tuple[Path, Path, Path, Path]:
    goal005 = tmp_path / "goal005"
    goal003 = tmp_path / "goal003"
    goal002 = tmp_path / "goal002"
    xraise = goal005 / "xraise_grid"
    cavity = goal005 / "cavity_stub"
    bridge = goal003 / "bridge_external_loss_volume_coupled"

    x = np.linspace(-x_half_width, x_half_width, 24)
    z = np.linspace(-160.0, 160.0, 32)
    xx, zz = np.meshgrid(x, z)
    xray = 100.0 + 50.0 * np.exp(-((xx / 45.0) ** 2 + (zz / 130.0) ** 2))
    xray += 8.0 * np.exp(-(((np.abs(zz) - 70.0) / 22.0) ** 2 + (xx / 25.0) ** 2))
    tracer = np.where(np.abs(zz) < 110.0, np.exp(-(xx / 24.0) ** 2), 0.0)

    write_vector(xraise / "x_kpc.tsv", list(x))
    write_vector(xraise / "z_kpc.tsv", list(z))
    write_matrix(xraise / "xray_1kev_xraise_corrected_mjy_sr.tsv", xray)
    write_matrix(xraise / "tracer_max_los.tsv", tracer)
    (xraise / "xraise_grid_smoke_metadata.json").write_text('{"timestep": "Timestep_51"}\n')
    write_csv(
        xraise / "xraise_grid_smoke_summary.csv",
        [{"metric": "corrected_xray_max", "value": float(xray.max()), "unit": "mJy sr^-1"}],
        ["metric", "value", "unit"],
    )
    write_csv(
        cavity / "cavity_ellipse_boundary_0deg.tsv",
        [
            {"side": "negative_z", "x_kpc": -20.0, "z_kpc": -120.0},
            {"side": "negative_z", "x_kpc": 20.0, "z_kpc": -120.0},
            {"side": "negative_z", "x_kpc": 20.0, "z_kpc": -20.0},
            {"side": "negative_z", "x_kpc": -20.0, "z_kpc": -20.0},
            {"side": "positive_z", "x_kpc": -22.0, "z_kpc": 20.0},
            {"side": "positive_z", "x_kpc": 22.0, "z_kpc": 20.0},
            {"side": "positive_z", "x_kpc": 22.0, "z_kpc": 120.0},
            {"side": "positive_z", "x_kpc": -22.0, "z_kpc": 120.0},
        ],
        ["side", "x_kpc", "z_kpc"],
        delimiter="\t",
    )
    write_csv(
        cavity / "cavity_stub_summary.csv",
        [{"side": "negative_z", "pV_erg": 1.0}, {"side": "positive_z", "pV_erg": 1.1}],
        ["side", "pV_erg"],
    )
    write_csv(
        goal005 / "final_xray_cavity_alignment_lobes.csv",
        [{"side": "bipolar_total", "cavity_four_pV_erg": 4.0}],
        ["side", "cavity_four_pV_erg"],
    )
    write_csv(
        bridge / "sparse_particle_radio_lobe_summary.csv",
        [{"side": "bipolar_total", "lossy_luminosity_doppler_w_hz": 1.0e29}],
        ["side", "lossy_luminosity_doppler_w_hz"],
    )
    write_csv(
        goal002 / "sparse_praise_loss_table.csv",
        [{"id": 1, "loss_factor": 0.9}],
        ["id", "loss_factor"],
    )
    return goal005, goal003, goal002, tmp_path / "out"


def test_boxcar_mean_preserves_shape_and_smooths() -> None:
    module = load_script_module()
    values = np.zeros((7, 7), dtype=float)
    values[3, 3] = 9.0
    smoothed = module.boxcar_mean(values, 3)
    assert smoothed.shape == values.shape
    assert smoothed[3, 3] == pytest.approx(1.0)


def test_build_package_writes_parseable_wide_field_assets(tmp_path: Path) -> None:
    module = load_script_module()
    goal005, goal003, goal002, out = make_fixture(tmp_path, x_half_width=120.0)

    metadata = module.build_package(
        goal005_dir=goal005,
        goal003_dir=goal003,
        goal002_dir=goal002,
        output_dir=out,
        contrast_boxcar_pixels=5,
    )

    figure = out / "c_hi_final_observational_product_readiness.png"
    assert figure.exists()
    assert figure.stat().st_size > 1000
    assert metadata["ready_for_patrick_review"] is True
    assert metadata["wide_field_fov_kpc"]["x_width"] > metadata["wide_field_fov_kpc"]["goal005_main_x_width"]

    parsed = json.loads((out / "observational_product_readiness_metadata.json").read_text())
    assert parsed["contrast_method"]["name"] == "boxcar_unsharp_residual"
    assert "not X-ray-fitted" in parsed["overlay_statement"]

    topology_rows = list(csv.DictReader((out / "xray_topology_readiness.csv").open()))
    radio_rows = list(csv.DictReader((out / "radio_observable_status.csv").open()))
    provenance_rows = list(csv.DictReader((out / "product_provenance.csv").open()))
    assert {row["aspect"] for row in topology_rows} >= {"topology_convention", "xray_fit_status"}
    assert any(row["not_yet_validated_as"] == "radio surface-brightness observable" for row in radio_rows)
    assert any(row["role"] == "corrected_xray_surface_brightness" for row in provenance_rows)


def test_rejects_goal005_width_as_main_wide_field(tmp_path: Path) -> None:
    module = load_script_module()
    goal005, goal003, goal002, out = make_fixture(tmp_path, x_half_width=40.0)

    with pytest.raises(ValueError, match="wide-field product"):
        module.build_package(
            goal005_dir=goal005,
            goal003_dir=goal003,
            goal002_dir=goal002,
            output_dir=out,
            contrast_boxcar_pixels=5,
        )
