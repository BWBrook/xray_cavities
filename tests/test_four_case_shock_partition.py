import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import four_case_shock_partition as budget


@pytest.fixture(scope="module")
def tables():
    regions, axial, summary = budget.build()
    primary = {(r["case"], r["snapshot_index"], r["side"]): r for r in regions if r["threshold_factor"] == 1}
    return primary, budget.keyed(axial, ("case", "snapshot_index", "side")), summary


def test_same_cell_thermal_partition_and_common_denominator(tables):
    primary, _, _ = tables
    total = primary["C-LO", 10, "bipolar_total"]
    denominator = total["cumulative_bipolar_gas_delivery_erg"]
    adiabatic = total["same_cell_adiabatic_thermal_change_over_delivery"]
    excess = total["thermal_excess_over_same_cell_adiabat_over_delivery"]
    assert adiabatic == pytest.approx(-0.0379, abs=6e-5)
    assert adiabatic + excess == pytest.approx(total["downstream_thermal_change_over_delivery"])
    for component in budget.COMPONENTS:
        key = f"downstream_{component}_change_over_delivery"
        sides = [primary["C-LO", 10, s] for s in budget.SIDES]
        assert all(r["cumulative_bipolar_gas_delivery_erg"] == denominator for r in sides)
        assert sum(r[key] for r in sides) == pytest.approx(total[key])
        assert total[key] + total[f"ambient_outside_downstream_{component}_change_over_delivery"] == pytest.approx(
            total[f"ambient_{component}_change_erg"] / denominator)


def test_censored_side_and_oriented_speed(tables):
    primary, axial, _ = tables
    assert primary["C-LO", 40, "negative_z"]["downstream_total_change_erg"] is None
    assert primary["C-LO", 40, "positive_z"]["downstream_total_change_erg"] == pytest.approx(-1.3420e56, rel=1e-5)
    assert primary["C-LO", 40, "bipolar_total"]["downstream_total_change_erg"] is None
    assert axial["C-LO", 40, "positive_z"]["signed_radial_mach"] == pytest.approx(-1.05751, abs=1e-5)
    endpoint = axial["G-HI", 47, "positive_z"]
    assert endpoint["both_position_and_jump_samples_valid"]
    assert endpoint["pressure_jump_ratio"]
    assert endpoint["signed_radial_mach"] is None
    assert endpoint["downstream_inventory_status"] == "unmeasured"


def test_axial_sampling_and_inventory_are_separate(tables):
    _, axial, summary = tables
    assert summary["positive_ages_without_3d_measurement"] == 178
    assert summary["qualified_bilateral_primary"] == 15
    assert summary["qualified_with_both_jump_inversions_on_both_sides"] == ["C-HI/10", "G-HI/10", "G-HI/20", "G-HI/30"]
    for side, expected in zip(budget.SIDES, (0.742, 0.777), strict=True):
        assert axial["G-HI", 20, side]["axial_pressure_excess_over_upstream_adiabat_fraction"] == pytest.approx(expected, abs=0.0005)
    for i in range(10, 51, 10):
        for s in budget.SIDES:
            r = axial["G-LO", i, s]
            assert r["downstream_inventory_status"] == "quantitative_seeded_component"
            assert float(r["pressure_jump_ratio"]) < 1
            assert float(r["density_jump_ratio"]) < 1
            assert r["both_jump_machs_defined"] is False
