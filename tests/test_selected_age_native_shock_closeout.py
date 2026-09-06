from __future__ import annotations

import csv
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import pytest


SCRIPT = Path("scripts/science/build_selected_age_native_shock_closeout.py")
SHOCK_ROOT = Path(
    "docs/science/assets/four_case_selected_age_native_shock_partition_2026-08-31/remote_analysis"
)
GOAL066 = Path(
    "docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/audit_products"
)


def load_module():
    spec = importlib.util.spec_from_file_location("build_selected_age_native_shock_closeout", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_closeout_validates_full_surface_and_preserves_goal066_gates(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "output"

    metadata = module.build_product(
        shock_root=SHOCK_ROOT,
        goal066_native=GOAL066 / "native_grid_selected_age.csv",
        goal066_matched=GOAL066 / "matched_native_xray_energetics.csv",
        output_root=output,
        surface_role="historical_sensitivity",
    )

    assert metadata["status"] == "complete_validated_selected_age_shock_closeout"
    assert metadata["surface_role"] == "historical_sensitivity"
    assert metadata["prespecified_row_count"] == 171
    assert metadata["primary_case_age_count"] == 19
    assert metadata["quantitative_primary_count"] == 15
    assert metadata["unresolved_primary_count"] == 4
    assert metadata["goal066_native_join_count"] == 19
    assert metadata["goal066_matched_join_count"] == 464
    primary = read_rows(output / "primary_shock_partition.csv")
    unresolved = [row for row in primary if row["status"] != "quantitative_bilateral"]
    assert {(row["case"], int(row["snapshot_index"])) for row in unresolved} == {
        ("C-LO", 20),
        ("C-LO", 30),
        ("C-LO", 40),
        ("C-LO", 50),
    }
    matched = read_rows(output / "goal066_matched_xray_shock_context.csv")
    assert {row["quantitative_cavity_valid"] for row in matched} == {"True", "False"}
    assert (output / "selected_age_native_shock_partition.png").stat().st_size > 10_000


def test_threshold_sensitivity_retains_decision_relevant_low_power_spread(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "output"
    module.build_product(
        shock_root=SHOCK_ROOT,
        goal066_native=GOAL066 / "native_grid_selected_age.csv",
        goal066_matched=GOAL066 / "matched_native_xray_energetics.csv",
        output_root=output,
        surface_role="historical_sensitivity",
    )
    rows = read_rows(output / "threshold_sensitivity.csv")
    assert len(rows) == 57
    g_lo_50 = {
        float(row["threshold_factor"]): row
        for row in rows
        if row["case"] == "G-LO" and int(row["snapshot_index"]) == 50
    }
    assert float(g_lo_50[0.5]["relative_shock_fraction_to_primary"]) > 1.3
    assert float(g_lo_50[2.0]["relative_shock_fraction_to_primary"]) < 0.75


def strict_synthetic_surface(module, tmp_path):
    """Synthetic full-cell data exercise validation; these are not refreshed science products."""
    root = tmp_path / "synthetic_strict"
    shutil.copytree(SHOCK_ROOT, root)
    for case in module.CASES:
        case_root = root / case
        path = case_root / "native_shock_energy_selected_age.csv"
        rows = module.read_rows(path)
        for row in rows:
            row["ambient_tracer_max"] = 0.001
            row["ambient_energy_weighting"] = "binary_full_cell"
            if row["status"].startswith("quantitative_"):
                row["ambient_weighted_volume_kpc3"] = row["mask_volume_kpc3"]
        module.write_rows(path, rows)
        meta_path = case_root / "selected_age_native_shock_metadata.json"
        meta = json.loads(meta_path.read_text())
        meta.update(ambient_tracer_max=0.001, ambient_energy_weighting="binary_full_cell")
        meta_path.write_text(json.dumps(meta))
        refresh_manifest(module, case_root)
    return root


def refresh_manifest(module, root):
    manifest = root / "local_asset_manifest.sha256"
    manifest.write_text("\n".join(f"{module.sha256_file(p)}  {p.name}" for p in sorted(root.iterdir())
                                  if p.is_file() and p != manifest) + "\n")


def strict_synthetic_context(module, tmp_path):
    """Explicitly synthetic labels; only exercise closeout wiring and validity handling."""
    root = tmp_path / "synthetic_native_context"
    root.mkdir()
    for name in ("native_grid_selected_age.csv", "matched_native_xray_energetics.csv"):
        rows = module.read_rows(GOAL066 / name)
        for row in rows:
            row["native_partition_method"] = "binary_tr1_gt_1e-3_full_cell_initial_state_subtraction_proven_ge_equivalent"
        module.write_rows(root / name, rows)
    return root


def test_historical_surface_cannot_be_used_as_primary():
    module = load_module()
    with pytest.raises(module.ProductError, match="metadata ambient tracer ceiling"):
        module.load_shock_surface(SHOCK_ROOT)


def test_primary_rejects_fractional_native_context(tmp_path):
    module = load_module()
    root = strict_synthetic_surface(module, tmp_path)
    with pytest.raises(module.ProductError, match="strict binary full-cell native context"):
        module.build_product(shock_root=root, goal066_native=GOAL066 / "native_grid_selected_age.csv",
                             goal066_matched=GOAL066 / "matched_native_xray_energetics.csv", output_root=tmp_path / "out")


@pytest.mark.parametrize("mutation", ["row_weight", "metadata_weight", "row_ceiling", "volume"])
def test_strict_primary_requires_consistent_full_cell_contract(tmp_path, mutation):
    module = load_module()
    root = strict_synthetic_surface(module, tmp_path)
    case_root = root / "C-HI"
    rows = module.read_rows(case_root / "native_shock_energy_selected_age.csv")
    if mutation == "metadata_weight":
        path = case_root / "selected_age_native_shock_metadata.json"
        meta = json.loads(path.read_text())
        meta["ambient_energy_weighting"] = "fractional_1_minus_clipped_tracer"
        path.write_text(json.dumps(meta))
    elif mutation == "row_weight":
        rows[0]["ambient_energy_weighting"] = "fractional_1_minus_clipped_tracer"
    elif mutation == "row_ceiling":
        rows[0]["ambient_tracer_max"] = 0.01
    else:
        rows[0]["ambient_weighted_volume_kpc3"] = float(rows[0]["mask_volume_kpc3"]) * 0.99
    module.write_rows(case_root / "native_shock_energy_selected_age.csv", rows)
    refresh_manifest(module, case_root)
    with pytest.raises(module.ProductError, match="ambient"):
        module.load_shock_surface(root)


@pytest.mark.parametrize("changed_case,changed_age,new_valid,expected_count", [
    ("C-HI", 50, False, 14), ("C-LO", 20, True, 16),
])
def test_changed_validity_is_reported_without_demanding_historical_conclusion(
    tmp_path, changed_case, changed_age, new_valid, expected_count
):
    module = load_module()
    root = strict_synthetic_surface(module, tmp_path)
    case_root = root / changed_case
    path = case_root / "native_shock_energy_selected_age.csv"
    rows = module.read_rows(path)
    for row in rows:
        if int(row["snapshot_index"]) != changed_age or float(row["threshold_factor"]) != 1.0:
            continue
        if new_valid:
            template = next(r for r in rows if int(r["snapshot_index"]) == 10
                            and r["side"] == row["side"] and float(r["threshold_factor"]) == 1.0)
            row["status"] = template["status"]
            for field in module.ENERGY_FIELDS:
                row[field] = template[field]
        else:
            row["status"] = "unresolved_bilateral_gate" if row["side"] == "bipolar_total" else "unresolved_boundary_touch"
            for field in module.ENERGY_FIELDS:
                row[field] = ""
    module.write_rows(path, rows)
    refresh_manifest(module, case_root)
    output = tmp_path / "closeout"
    native_context = strict_synthetic_context(module, tmp_path)
    meta = module.build_product(shock_root=root, goal066_native=native_context / "native_grid_selected_age.csv",
                                goal066_matched=native_context / "matched_native_xray_energetics.csv", output_root=output)
    assert meta["quantitative_primary_count"] == expected_count
    assert meta["surface_role"] == "primary"
    assert "scheduler_job" not in meta
    summary = next(r for r in module.read_rows(output / "case_summary.csv") if r["case"] == changed_case)
    assert summary["interpretation_status"] == "quantitative_subset_with_unresolved_ages"
    assert f"{changed_age}:" in summary["primary_status_by_age"]
