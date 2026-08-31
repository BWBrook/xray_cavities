from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path


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
    )

    assert metadata["status"] == "complete_product_recovered_no_hdf5_rerun"
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
