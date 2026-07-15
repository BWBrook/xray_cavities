from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


SCRIPT = Path("scripts/science/analyse_common_age_case.py")


def load_module():
    spec = importlib.util.spec_from_file_location("analyse_common_age_case", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_case_fixture(root: Path, case: str, nominal: int, actual: float, *, ambiguous: bool = False) -> None:
    age = root / f"age_{nominal}myr"
    for view in (() if nominal == 50 else ("0deg", "45deg", "90deg")):
        xraise = age / f"xraise_grid_{view}"
        xraise.mkdir(parents=True, exist_ok=True)
        axis = np.arange(-60.0, 61.0, 5.0)
        xx, zz = np.meshgrid(axis, axis)
        base = np.ones_like(xx)
        cavities = ((xx / 15.0) ** 2 + ((zz - 30.0) / 12.0) ** 2 <= 1.0) | (
            (xx / 15.0) ** 2 + ((zz + 30.0) / 12.0) ** 2 <= 1.0
        )
        if ambiguous:
            cavities |= (abs(xx) <= 20.0) & (abs(zz) <= 40.0)
        np.savetxt(xraise / "x_kpc.tsv", axis)
        np.savetxt(xraise / "z_kpc.tsv", axis)
        np.savetxt(xraise / "xray_1kev_xraise_corrected_mjy_sr.tsv", base - 0.8 * cavities, delimiter="\t")
        np.savetxt(xraise / "tracer_max_los.tsv", cavities.astype(float), delimiter="\t")
        accumulator = "direct_y_axis_sum" if view == "0deg" else "edge_overlap_uniform_cell_projection"
        (xraise / "xraise_grid_smoke_metadata.json").write_text(json.dumps({
            "time_myr": actual,
            "projection": {
                "view_angle_deg": int(view[:-3]),
                "projected_accumulation": accumulator,
                "sky_horizontal_bins": len(axis),
            },
            "corrected_stats_mjy_sr": {"finite_cells": int(base.size), "positive_cells": int(base.size)},
        }) + "\n")
        write_csv(xraise / "xraise_grid_smoke_summary.csv", [
            {"metric": "time_myr", "value": actual, "unit": "Myr"},
            {"metric": "corrected_xray_max", "value": 1.0, "unit": "mJy sr^-1"},
            {"metric": "corrected_xray_sum", "value": float(base.sum()), "unit": "mJy sr^-1 pixels"},
            {"metric": "correction_ratio_positive_max", "value": 1.0, "unit": "dimensionless"},
            {"metric": "correction_ratio_positive_sum", "value": float(base.sum()), "unit": "dimensionless pixels"},
        ])

    if nominal < 50:
        truth = age / "truth"
        write_csv(truth / "level1_injected_energy.csv", [
            {"metric": "time_code", "value": actual * 306.6013937879523, "unit": "code_time"},
            {"metric": "time_myr", "value": actual, "unit": "Myr"},
            {"metric": "injected_energy_bipolar_elapsed", "value": 1.0e60, "unit": "erg"},
            {"metric": "injected_energy_one_sided_elapsed", "value": 5.0e59, "unit": "erg"},
        ])
        level2_rows = []
        for threshold in ("1e-03", "5e-03", "1e-02"):
            for side in ("negative_z", "positive_z", "bipolar_total"):
                level2_rows.append({"threshold": threshold, "side": side, "time_myr": actual,
                                    "volume_kpc3": 100.0, "total_energy_erg": 2.0e59,
                                    "cell_count": 10})
        write_csv(truth / "level2_tracer_lobe_truth.csv", level2_rows)
        cavity = age / "cavity"
        cavity_rows = []
        for side, z in (("negative_z", -30.0), ("positive_z", 30.0)):
            cavity_rows.append({"side": side, "time_myr": actual, "ambient_pressure_dyn_cm2": 2.0e-10,
                                "sound_age_myr": 10.0, "buoyancy_age_myr": 20.0, "refill_age_myr": 30.0,
                                "center_z_kpc": z, "pV_erg": 1.0e58, "four_pV_erg": 4.0e58})
        write_csv(cavity / "cavity_stub_summary.csv", cavity_rows)
    level3 = age / "level3"
    write_csv(level3 / "level3_extractor_output.csv", [
        {"side": side, "tracer_threshold": "5e-03", "ambient_cell_count": 10,
         "ambient_volume_kpc3": 100.0, "thermal_delta_erg": 1.0e58,
         "kinetic_delta_erg": 2.0e58, "thermal_plus_kinetic_delta_erg": 3.0e58}
        for side in ("negative_z", "positive_z", "bipolar_total")
    ])


def write_manifest(path: Path, case: str, ages: list[int]) -> None:
    jet_power = {"C-HI": 1.0e45, "C-LO": 1.0e43, "G-LO": 1.0e43}[case]
    rows = []
    for age in ages:
        rows.append({
            "case": case, "nominal_age_myr": age, "actual_time_myr": age + 0.02,
            "time_code": (age + 0.02) * 306.6013937879523,
            "input_h5": f"/remote/{case}/data.{age:04d}.flt.h5", "timestep": f"Timestep_{age}",
            "output_index": age, "file_size_bytes": 100, "grid_shape_nz_ny_nx": "2x2x2",
            "jet_power_erg_s": jet_power, "baseline_h5": f"/remote/{case}/data.0000.flt.h5",
            "baseline_timestep": "Timestep_0", "baseline_time_code": 0.0, "baseline_time_myr": 0.0,
            "baseline_file_size_bytes": 90, "baseline_grid_shape_nz_ny_nx": "2x2x2",
            "action": "compute_new" if age < 50 else "reuse_endpoint_plus_level3",
            "compute_xray": "true" if age < 50 else "false", "compute_truth_cavity": "true" if age < 50 else "false",
            "compute_level3": "true", "endpoint_reuse_id": f"{case}:50myr", "selection_status": "selected",
        })
    write_csv(path, rows)


def test_analysis_propagates_actual_time_and_writes_protected_compact_surface(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "analysis"
    for age in (10, 20, 30, 40, 50):
        write_case_fixture(root, "C-HI", age, age + 0.02)
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, "C-HI", [10, 20, 30, 40, 50])
    compact = tmp_path / "compact"

    module.build_analysis(case="C-HI", source_manifest=manifest, analysis_root=root, compact_output=compact)

    with (compact / "xray_recovery_summary.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 12
    assert rows and rows[0]["nominal_age_myr"] == "10"
    assert float(rows[0]["actual_time_myr"]) == 10.02
    sensitivity = list(csv.DictReader((compact / "xray_method_sensitivity.csv").open(newline="")))
    assert len(sensitivity) == 180
    level3 = list(csv.DictReader((compact / "level3_ambient_energy.csv").open(newline="")))
    assert len(level3) == 15
    assert {row["nominal_age_myr"] for row in level3} == {"10", "20", "30", "40", "50"}
    level2 = list(csv.DictReader((compact / "level2_truth.csv").open(newline="")))
    assert {row["threshold"] for row in level2} == {"1e-3", "5e-3", "1e-2"}
    energies = list(csv.DictReader((compact / "cavity_energy_power_alignment.csv").open(newline="")))
    assert {row["side"] for row in energies} >= {"negative_z", "positive_z", "bipolar_total"}
    assert {row["view"] for row in energies} == {"0deg", "45deg", "90deg"}
    assert {row["volume_depth_assumption"] for row in energies} == {
        "minor_depth", "geometric_depth", "major_depth"
    }
    assert any(row["energy_model"] == "2.5pV" for row in energies)
    ledger = list(csv.DictReader((compact / "product_dependency_ledger.csv").open(newline="")))
    assert ledger and all(row["deletion_authority"] == "barry_only_after_goal041_synthesis_acceptance" for row in ledger)
    assert {row["data_class"] for row in ledger} >= {
        "raw_snapshot_source", "zero_time_baseline", "processed_full_array"
    }
    assert all(row["size_bytes"] for row in ledger)
    assert all(row["sha256_status"] for row in ledger)
    manifest_text = (compact / "goal041_sha256_manifest.sha256").read_text()
    assert "goal041_sha256_manifest.sha256" not in manifest_text
    assert not list(compact.glob("*.tsv"))


def test_ambiguous_topology_emits_mean_pressure_without_side_ages(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "analysis"
    for age in (10, 20, 30, 40, 50):
        write_case_fixture(root, "C-LO", age, age + 0.02, ambiguous=True)
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, "C-LO", [10, 20, 30, 40, 50])
    compact = tmp_path / "compact"

    module.build_analysis(case="C-LO", source_manifest=manifest, analysis_root=root, compact_output=compact)

    rows = list(csv.DictReader((compact / "cavity_energy_power_alignment.csv").open(newline="")))
    assert rows and {row["side"] for row in rows} == {"bipolar_total"}
    assert all(row["sound_age_myr"] == "" for row in rows)
    assert all(row["energy_pressure_convention"] == "bipolar_mean_shell_pressure" for row in rows)


def test_analysis_rejects_manifest_or_generated_product_time_drift(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "analysis"
    for age in (10, 20, 30, 40, 50):
        write_case_fixture(root, "G-LO", age, age + 0.02)
    manifest = tmp_path / "manifest.csv"
    write_manifest(manifest, "G-LO", [10, 20, 30, 40, 50])
    rows = list(csv.DictReader(manifest.open(newline="")))
    rows[0]["selection_status"] = "unchecked"
    write_csv(manifest, rows)
    with pytest.raises(ValueError, match="selection status"):
        module.build_analysis(case="G-LO", source_manifest=manifest, analysis_root=root, compact_output=tmp_path / "compact-a")

    write_manifest(manifest, "G-LO", [10, 20, 30, 40, 50])
    level2_path = root / "age_10myr" / "truth" / "level2_tracer_lobe_truth.csv"
    level2 = list(csv.DictReader(level2_path.open(newline="")))
    level2[0]["time_myr"] = "11.0"
    write_csv(level2_path, level2)
    with pytest.raises(ValueError, match="Level 2 time mismatch"):
        module.build_analysis(case="G-LO", source_manifest=manifest, analysis_root=root, compact_output=tmp_path / "compact-b")
