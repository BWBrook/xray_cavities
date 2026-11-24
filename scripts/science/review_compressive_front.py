"""Independent review of the G-HI/20 compression-front comparison (XR-05, XR-06).

Recomputes the published tables from the released CSVs and adds three
measurements the comparison does not report: the brightness of the exterior
5%-deficit area relative to time zero, the margin of that area above the 5%
threshold, and the ambient brightening outside the qualifying layer.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'docs/science/assets/compressive_front_observer_2026-11-23'
OUT = ROOT / 'docs/science/assets/compressive_front_review_2026-11-24'
ORANGE = 'deficit_threshold_observer_radial_0.05'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    overlap = pd.read_csv(SOURCE / 'front_sightline_overlap.csv')
    separations = pd.read_csv(SOURCE / 'front_contour_separations.csv')
    emission = pd.read_csv(SOURCE / 'emission_regions.csv')
    recovery = pd.read_csv(SOURCE / 'replacement_recovery.csv')
    profiles = pd.read_csv(SOURCE / 'transverse_profiles.csv.gz')

    lateral = overlap[overlap.region == 'orange_lateral_excess']
    arcs = separations[(separations.method == 'orange_5pct') & (separations.observer_region == 'lateral_arc')]
    primary = arcs[arcs.reference == 'primary'].set_index(['view_deg', 'hemisphere'])
    four = arcs[arcs.reference.isin(['primary', 'loose', 'tight', 'wide']) & (arcs.view_deg == 0)]

    sums = emission.groupby(['view_deg', 'region'])[[
        'area_kpc2', 'lobe_current_minus_initial', 'front_current_minus_initial',
        'rest_current_minus_initial', 'whole_current', 'whole_initial',
        'radial_background_minus_current_whole']].sum()
    budget = pd.DataFrame({
        'area_kpc2': sums.area_kpc2,
        'layer_gain_over_lobe_deficit': -sums.front_current_minus_initial / sums.lobe_current_minus_initial,
        'other_ambient_gain_over_lobe_deficit': -sums.rest_current_minus_initial / sums.lobe_current_minus_initial,
        'layer_share_of_ambient_gain': sums.front_current_minus_initial
        / (sums.front_current_minus_initial + sums.rest_current_minus_initial),
        'layer_gain_over_current': sums.front_current_minus_initial / sums.whole_current,
        'current_over_initial_minus_one': sums.whole_current / sums.whole_initial - 1,
        'radial_background_over_initial_minus_one':
            (sums.whole_current + sums.radial_background_minus_current_whole) / sums.whole_initial - 1,
        'mean_fractional_deficit': sums.radial_background_minus_current_whole
        / (sums.whole_current + sums.radial_background_minus_current_whole)})
    lobe_rows = ~budget.index.get_level_values('region').str.startswith('orange_lateral')
    budget.loc[~lobe_rows, ['layer_gain_over_lobe_deficit', 'other_ambient_gain_over_lobe_deficit']] = float('nan')
    budget.reset_index().to_csv(OUT / 'pooled_emission_budget.csv', index=False)

    keys = ['view_deg', 'method', 'comparison']
    pooled = recovery.assign(overlap=recovery.selected_kpc2 - recovery.false_area_kpc2).groupby(keys)[[
        'selected_kpc2', 'truth_kpc2', 'false_area_kpc2', 'overlap', 'inferred_volume_kpc3', 'native_lobe_kpc3']].sum()
    pooled['inferred_over_native'] = pooled.inferred_volume_kpc3 / pooled.native_lobe_kpc3
    pooled['completeness'] = pooled.overlap / pooled.truth_kpc2
    pooled['purity'] = pooled.overlap / pooled.selected_kpc2
    pooled.reset_index().to_csv(OUT / 'pooled_replacement_recovery.csv', index=False)

    exterior = profiles[(profiles.lobe_path_kpc == 0) & (profiles.front_path_kpc == 0) & (profiles.original_orange == 1)]
    exterior = exterior.assign(
        deficit=(exterior.original_radial_background - exterior.raw_brightness) / exterior.original_radial_background,
        deficit_after=(exterior.replacement_radial_background - exterior.replacement) / exterior.replacement_radial_background,
        background_shift=exterior.replacement_radial_background / exterior.original_radial_background - 1,
        brightness_shift=exterior.replacement / exterior.exact_brightness - 1)
    margin = exterior.groupby('view_deg').agg(
        samples=('deficit', 'size'), deficit_median=('deficit', 'median'), deficit_max=('deficit', 'max'),
        deficit_after_replacement_and_refit_max=('deficit_after', 'max'),
        background_shift_median=('background_shift', 'median'),
        largest_brightness_change=('brightness_shift', lambda value: value.abs().max()))
    margin.reset_index().to_csv(OUT / 'exterior_arc_threshold_margin.csv', index=False)

    def pick(view, method, comparison, column):
        return float(pooled.loc[(view, method, comparison), column])

    def region(name, column):
        return {int(view): float(budget.loc[(view, name), column]) for view in (0, 45, 90)}

    summary = {
        'reproduced_from_published_tables': {
            'no_compression_fraction_of_lateral_area_range': [float(lateral.no_compression_area_fraction.min()),
                                                              float(lateral.no_compression_area_fraction.max())],
            'signed_median_arc_to_front_kpc': {f'{view}_{side}': float(primary.loc[(view, side), 'signed_median_kpc'])
                                                for view, side in primary.index},
            'zero_degree_median_range_across_four_definitions_kpc': [float(four.signed_median_kpc.min()),
                                                                     float(four.signed_median_kpc.max())],
            'layer_gain_over_lobe_deficit_blue_missed': region('missed_lobe_blue', 'layer_gain_over_lobe_deficit'),
            'layer_gain_over_lobe_deficit_orange_missed': region('missed_lobe_orange', 'layer_gain_over_lobe_deficit'),
            'layer_gain_over_current_on_exterior_orange': region('orange_lateral_excess', 'layer_gain_over_current'),
            'orange_zero_degree_inferred_over_native': {
                name: pick(0, ORANGE, name, 'inferred_over_native') for name in (
                    'original', 'replace_same_cells_original_background', 'replace_same_cells_refit_background')},
            'orange_zero_degree_refit_completeness_before_after': [
                pick(0, ORANGE, 'exact_refit_background', 'completeness'),
                pick(0, ORANGE, 'replace_same_cells_refit_background', 'completeness')],
            'orange_zero_degree_false_area_before_after_kpc2': [
                pick(0, ORANGE, 'exact_refit_background', 'false_area_kpc2'),
                pick(0, ORANGE, 'replace_same_cells_refit_background', 'false_area_kpc2')]},
        'added_by_this_review': {
            'exterior_orange_current_over_initial_minus_one': region('orange_lateral_excess', 'current_over_initial_minus_one'),
            'exterior_orange_radial_background_over_initial_minus_one':
                region('orange_lateral_excess', 'radial_background_over_initial_minus_one'),
            'exterior_orange_mean_fractional_deficit': region('orange_lateral_excess', 'mean_fractional_deficit'),
            'sampled_rows_exterior_deficit_max': {int(view): float(value) for view, value in margin.deficit_max.items()},
            'sampled_rows_background_shift_median': {int(view): float(value) for view, value in margin.background_shift_median.items()},
            'sampled_rows_largest_brightness_change': float(margin.largest_brightness_change.max()),
            'other_ambient_gain_over_lobe_deficit_blue_missed': region('missed_lobe_blue', 'other_ambient_gain_over_lobe_deficit'),
            'other_ambient_gain_over_lobe_deficit_orange_missed': region('missed_lobe_orange', 'other_ambient_gain_over_lobe_deficit'),
            'layer_share_of_ambient_gain_blue_missed': region('missed_lobe_blue', 'layer_share_of_ambient_gain'),
            'layer_share_of_ambient_gain_orange_missed': region('missed_lobe_orange', 'layer_share_of_ambient_gain'),
            'missed_blue_current_over_initial_minus_one': region('missed_lobe_blue', 'current_over_initial_minus_one'),
            'missed_orange_current_over_initial_minus_one': region('missed_lobe_orange', 'current_over_initial_minus_one'),
            'full_lobe_ambient_gain_over_lobe_deficit': {
                int(view): float(budget.loc[(view, 'full_lobe_sightlines'), 'layer_gain_over_lobe_deficit']
                                 + budget.loc[(view, 'full_lobe_sightlines'), 'other_ambient_gain_over_lobe_deficit'])
                for view in (0, 45, 90)}}}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
