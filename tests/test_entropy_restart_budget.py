from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts/science"))
import entropy_restart_budget as budget


def test_quadrature_with_one_unphysical_face_state():
    assert budget.mean_rate(None, 4.0, 1.0) == 4.0
    assert budget.mean_rate(None, 4.0, 0.5) is None
    assert budget.mean_rate(-3.0, None, 0.0) == -3.0
    assert budget.mean_rate(-3.0, 4.0, 0.5) == 0.5


def test_whole_window_uses_actual_durations_and_retains_missing_coverage():
    shared = dict(case="G-HI", arm="OFF", injector_method="linear_snapshot_flags",
                  outer_boundary="linear_to_boundary_face", time_rule="trapezoid")
    a = dict(shared, start_age_myr=10, end_age_myr=10.5, labelled_energy_erg=2,
             **dict.fromkeys(budget.BUDGET_FIELDS, 3))
    b = dict(shared, start_age_myr=10.5, end_age_myr=12, labelled_energy_erg=6,
             **dict.fromkeys(budget.BUDGET_FIELDS, -1))
    assert budget.weighted_window([a, b])["exterior"] == pytest.approx(0)
    b["exterior"] = None
    result = budget.weighted_window([a, b])
    assert result["exterior"] is None and result["valid_exterior_intervals"] == 1
    assert result["labelled_energy_erg"] == 8 and result["native_stage"] == pytest.approx(0)
