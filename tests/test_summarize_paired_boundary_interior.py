import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/science'))
from summarize_paired_boundary_interior import ENERGY_COMPONENTS, summarize


def test_joint_width_not_maximum_of_separate_first_passes():
    rows = []
    for width, paired, stable in ((0, False, True), (20, True, False), (30, False, True), (40, True, True)):
        rows.append({'buffer_kpc': width, 'cell_count': 10,
                     'contrast_cell_l1': dict.fromkeys(ENERGY_COMPONENTS, .5 if paired else 2),
                     'reflective_delta_cell_l1': dict.fromkeys(ENERGY_COMPONENTS, .5 if stable else 2),
                     'outflow_delta_cell_l1': dict.fromkeys(ENERGY_COMPONENTS, .5 if stable else 2),
                     'contrast': dict.fromkeys(ENERGY_COMPONENTS, 0)})
    raw = {'case': 'synthetic', 'time_myr': 50, 'absolute_energy_tolerance_erg': 1, 'regions': rows}
    before = copy.deepcopy(raw)
    result = summarize(raw)
    assert result['smallest_paired_localization_width_kpc'] == 20
    assert result['adopted_coarse_width_at_50_myr_kpc'] == 40
    assert raw == before
    raw['regions'].pop()
    assert summarize(raw)['adopted_coarse_width_at_50_myr_kpc'] is None
