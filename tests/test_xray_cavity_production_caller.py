"""Regression tests on the actual selected-age production caller (Q-032).

The fixture is a complete synthetic case tree with a known bipolar cavity
pair, fed through ``build_selected_age_xray_cavity.build_product`` exactly as
production runs it. These tests pin which recovery method production binds
and how far its volumes sit from a known truth. The strict xfail flips when
production moves to a validated method, which forces this file to change
in the same commit.
"""

from __future__ import annotations

import csv
import importlib.util
import json
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))

import numpy as np
import pytest

import xray_cavity_synthetic as synthetic

SCRIPT = Path("scripts/science/build_selected_age_xray_cavity.py")
AXES = Path("docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products")
STRIDE = 8
ALONG_KPC, ACROSS_KPC = 60.0, 35.0
CASE = "C-HI"


def load_module():
    spec = importlib.util.spec_from_file_location("build_selected_age_xray_cavity", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


@lru_cache(maxsize=None)
def view_map(view: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    horizontal_name = "x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"
    horizontal = np.loadtxt(AXES / f"xraise_grid_{view}" / horizontal_name)[::STRIDE]
    vertical = np.loadtxt(AXES / f"xraise_grid_{view}" / "z_kpc.tsv")[::STRIDE]
    rendered = synthetic.render_map(
        synthetic.load_atmosphere("cluster"), horizontal, vertical,
        synthetic.bipolar_pair(semiaxis_along_jet_kpc=ALONG_KPC, semiaxis_across_jet_kpc=ACROSS_KPC),
        view_deg=float(view.removesuffix("deg")),
    )
    image = rendered.surface_brightness / rendered.surface_brightness.max() * 1.0e4
    return image, rendered.cavity_mask.astype(float), horizontal, vertical


def build_case_tree(root: Path, module) -> Path:
    manifest = []
    for age in module.AGES:
        manifest.append({
            "case": CASE, "snapshot_index": age, "actual_time_myr": float(age),
            "timestep": f"Timestep_{age}", "input_h5": f"/synthetic/data.{age:04d}.dbl.h5",
            "file_size_bytes": 1,
        })
        age_dir = root / f"age_{age:02d}"
        write_rows(age_dir / "truth" / "level1_injected_energy.csv", [
            {"metric": "time_myr", "value": float(age), "unit": "Myr"},
        ])
        write_rows(age_dir / "truth" / "level2_tracer_lobe_truth.csv", [
            {"time_myr": float(age), "threshold": threshold, "side": side,
             "volume_kpc3": 1.0, "total_energy_erg": 1.0, "cell_count": 1}
            for threshold in ("1e-3", "5e-3", "1e-2")
            for side in ("negative_z", "positive_z", "bipolar_total")
        ])
        write_rows(age_dir / "cavity" / "cavity_stub_summary.csv", [
            {"side": side, "time_myr": float(age), "ambient_pressure_dyn_cm2": 1.0e-10,
             "sound_age_myr": 1.0, "buoyancy_age_myr": 1.0, "refill_age_myr": 1.0}
            for side in ("negative_z", "positive_z")
        ])
        for view in module.VIEWS:
            image, tracer, horizontal, vertical = view_map(view)
            directory = age_dir / f"xraise_grid_{view}"
            directory.mkdir(parents=True)
            np.savetxt(directory / "xray_1kev_xraise_corrected_mjy_sr.tsv", image, delimiter="\t")
            np.savetxt(directory / "tracer_max_los.tsv", tracer, delimiter="\t")
            np.savetxt(directory / ("x_kpc.tsv" if view == "0deg" else "u_kpc.tsv"), horizontal)
            np.savetxt(directory / "z_kpc.tsv", vertical)
            accumulation = "direct_y_axis_sum" if view == "0deg" else "edge_overlap_uniform_cell_projection"
            (directory / "xraise_grid_smoke_metadata.json").write_text(
                json.dumps({"projection": {"projected_accumulation": accumulation}})
            )
            write_rows(directory / "xraise_grid_smoke_summary.csv", [
                {"metric": "time_myr", "value": float(age)},
                {"metric": "corrected_xray_max", "value": float(image.max())},
                {"metric": "corrected_xray_sum", "value": float(image.sum())},
                {"metric": "correction_ratio_positive_max", "value": 1.0},
                {"metric": "correction_ratio_positive_sum", "value": float(image.size)},
            ])
    path = root / "manifest.csv"
    write_rows(path, manifest)
    return path


@pytest.fixture(scope="module")
def product(tmp_path_factory: pytest.TempPathFactory):
    module = load_module()
    calls: list[str] = []
    original = module.recovery_builder.analyse_loaded_map

    def spy(loaded, time_myr=50.0):
        calls.append(loaded.spec.view)
        return original(loaded, time_myr=time_myr)

    module.recovery_builder.analyse_loaded_map = spy
    try:
        root = tmp_path_factory.mktemp("case")
        manifest = build_case_tree(root / "analysis", module)
        metadata = module.build_product(
            case=CASE, source_manifest=manifest, analysis_root=root / "analysis",
            output_root=root / "output",
        )
    finally:
        module.recovery_builder.analyse_loaded_map = original
    with (root / "output" / "xray_cavity_energy.csv").open(newline="") as handle:
        energy = list(csv.DictReader(handle))
    true_volume = 2.0 * synthetic.Spheroid(ALONG_KPC, ALONG_KPC, ACROSS_KPC).volume_kpc3
    return metadata, calls, energy, true_volume


def bipolar_volumes(energy: list[dict[str, str]], depth: str) -> list[float]:
    return [
        float(row["volume_kpc3"])
        for row in energy
        if row["side"] == "bipolar_total"
        and row["volume_depth_assumption"] == depth
        and row["energy_model"] == "pV"
    ]


def test_production_binds_the_legacy_one_percent_area_method(product) -> None:
    metadata, calls, _, _ = product
    assert len(calls) == 15
    assert metadata["observer_mask"] == "X-ray-only 1 percent projected-physical-area deficit tail"


def test_production_volume_is_a_small_fixed_fraction_of_a_large_true_cavity(product) -> None:
    _, _, energy, true_volume = product
    volumes = bipolar_volumes(energy, "minor_depth")
    assert len(volumes) == 15
    assert max(volumes) < 0.05 * true_volume


@pytest.mark.xfail(strict=True, reason="Q-032: production uses the legacy 1% area selection")
def test_production_recovers_a_large_cavity_volume_within_thirty_percent(product) -> None:
    _, _, energy, true_volume = product
    for volume in bipolar_volumes(energy, "minor_depth"):
        assert volume == pytest.approx(true_volume, rel=0.3)
