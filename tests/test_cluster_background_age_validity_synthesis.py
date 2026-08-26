from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


SCRIPT = Path("scripts/science/build_cluster_background_age_validity.py")
BACKGROUND = Path("docs/science/assets/cluster_background_and_age_validity_2026-08-26/review_products")
SHOCKS = Path("docs/science/assets/four_case_fluid_snapshot_census_2026-08-25/primary_shock_timeseries.csv")


def _module():
    spec = importlib.util.spec_from_file_location("build_cluster_background_age_validity", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_paired_far_field_is_common_through_20_myr() -> None:
    module = _module()
    rows = module.paired_background_rows(BACKGROUND)
    early = [row for row in rows if row["early_far_field_control"]]

    assert len(early) == 16
    assert max(float(row["absolute_fractional_difference"]) for row in early) < 2.5e-4


def test_c_lo_endpoint_is_far_field_dominated() -> None:
    module = _module()
    endpoint = next(row for row in module.c_lo_accounting_rows(BACKGROUND) if row["snapshot_index"] == 50)

    assert 23.9 < endpoint["global_fraction_of_injected"] < 24.0
    assert endpoint["far_field_fraction_of_global"] > 0.94
    assert 1.28 < endpoint["inside_100_kpc_fraction_of_injected"] < 1.30
    assert endpoint["far_field_tracer_volume_fraction"] == 0.0


def test_g_hi_validity_window_accounts_for_three_snapshot_fit() -> None:
    module = _module()
    summary = module.shock_window_summary(module.shock_validity_rows(SHOCKS))
    g_hi = next(row for row in summary if row["case"] == "G-HI")

    assert g_hi["last_position_valid_snapshot"] == 47
    assert g_hi["last_kinematics_valid_snapshot"] == 46
