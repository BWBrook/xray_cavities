from pathlib import Path

import pytest

from test_spherical_energy_budget import _base_state, _run
from summarize_spherical_energy_budgets import collect, plot


def test_missing_and_unavailable_are_distinct_and_native_holds_survive(tmp_path: Path):
    current = _base_state()
    current['tr1'][2, 2, 2] = 1.1
    _, product, _ = _run(tmp_path / 'input', current)
    rows, hashes = collect([product], 'C-HI', [1, 2])
    assert len(hashes) == 1
    assert rows[0]['measurement_status'] == 'unavailable_no_cells_meet_speed_threshold'
    assert rows[0]['raw_radius_kpc'] is None
    assert rows[0]['all_total_over_injected'] is None
    assert rows[0]['native_enthalpy_2.5_over_injected'] > 0
    assert 'tracer_values_outside_unit_interval_unreviewed' in rows[0]['native_enthalpy_hold_codes']
    assert rows[2]['measurement_status'] == 'not_measured'
    assert rows[2]['native_enthalpy_2.5_over_injected'] is None
    target = tmp_path / 'plots'
    target.mkdir()
    plot(rows, target, 'C-HI')
    assert (target / 'C-HI_spherical_budgets.pdf').is_file()


def test_summary_rejects_duplicate_and_wrong_case(tmp_path: Path):
    _, product, _ = _run(tmp_path, _base_state())
    with pytest.raises(ValueError, match='duplicate'):
        collect([product, product], 'C-HI', [1])
    with pytest.raises(ValueError, match='case mismatch'):
        collect([product], 'G-HI', [1])
