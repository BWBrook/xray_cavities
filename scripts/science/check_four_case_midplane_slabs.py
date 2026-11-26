"""Review of the four-case midplane-slab result (XR-08).

Run on the 18 retained slab projections and their archived 90-degree views.
The flux and area sums below reuse Codex's rasters, so they check the
arithmetic only. Two parts are separate implementations: the radial
detector (review_source_excluded_backgrounds.py, which the four-case scorer
does not import) and the perpendicular row weights.

Tables written to docs/science/assets/four_case_midplane_slab_review_2026-11-26:

- outer_gas.csv: for each case-age and slab, the change in the footprint's
  flux deficit between the slab and the full column, split into the initial
  light of the gas beyond the slab, the excavation of lobe cells beyond the
  slab, and the change of ambient gas beyond the slab;
- controls.csv: the detector on each initial image over the threshold
  ladder, the largest time-zero fitted deficit, and how the initial images
  differ between ages and between runs in the same atmosphere;
- outlines.csv: the evolved outline at 5% and at the first clean cut, with
  the coverage splits;
- side_view_rows.csv: slab row totals against the 90-degree archive. The
  widened-cut change is a fraction of the exact-cut flux; Codex's
  perpendicular_rows.csv divides by the widened flux, so 4.50% here is
  4.31% there;
- comparison.csv: every value compared with Codex's case_age_depth.csv.
  Twelve of the 17 quantities per image depend on the detector; the other
  five are flux and area sums.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from check_ghi20_midplane_slabs import outline
from check_ghi20_slab_side_view import weights

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'docs/science/assets/four_case_midplane_slabs_2026-11-26'
OUT = ROOT / 'docs/science/assets/four_case_midplane_slab_review_2026-11-26'
DEPTHS = {'full': 200., 'slab30': 30., 'slab10': 10.}
LADDER = (0.05, 0.06, 0.07, 0.08, 0.10, 0.15, 0.20)
WHOLE = 'brightness_current_retained_linear_whole'
ATMOSPHERE = {'C-HI': 'C', 'C-LO': 'C', 'G-HI': 'G', 'G-LO': 'G'}


def write(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--archive', type=Path, required=True, help='private_archive/turn34_four_case_slabs')
    args = parser.parse_args()

    from skimage.measure import label
    import review_source_excluded_backgrounds as det

    with (PUBLIC / 'case_age_depth.csv').open(newline='') as stream:
        published = {(r['case'], int(r['snapshot_index']), r['depth']): r for r in csv.DictReader(stream)}
    units = sorted({key[:2] for key in published})
    OUT.mkdir(exist_ok=True)
    outer, outlines, rows, comparison, controls = [], [], [], [], []
    initial_images, first_clean, control_masks, control_fits, nothing = {}, {}, {}, {}, None

    def compare(unit, depth, name, mine, theirs):
        theirs = float(theirs) if theirs not in ('', None) else float('nan')
        both_nan = np.isnan(mine) and np.isnan(theirs)
        comparison.append({
            'case': unit[0], 'snapshot_index': unit[1], 'depth': depth, 'quantity': name, 'review': mine, 'published': theirs,
            'agrees': bool(both_nan or np.isclose(mine, theirs, rtol=1e-9, atol=1e-9))})

    for unit in units:
        case, index = unit
        with np.load(args.archive / f'native/{case}_{index:04d}/projections.npz', allow_pickle=False) as data:
            maps = {key: data[key] for key in data.files}
        axes = {key: maps[key] for key in det.AXES}
        path = maps['tracer_path_full']
        truth = path > 0
        nothing = np.zeros_like(truth)
        short = truth & (path <= 5)

        for depth in DEPTHS:
            current, initial = maps[f'current_{depth}'], maps[f'initial_{depth}']
            digest = hashlib.sha256(initial.tobytes()).hexdigest()
            view = det.View(depth, 'science', axes, current, initial, path, nothing, None)
            area = view.area
            total = lambda image, region=truth: float((area * image)[region].sum())
            if (case, depth) not in initial_images:
                null = det.View(depth, 'initial_null', axes, initial, initial, path, nothing, None)
                fit0 = null.profiles(initial, nothing)[0]
                selected = {}
                for cut in LADDER:
                    mask0, background0 = outline(null, fit0, cut, det, label)
                    selected[cut] = [float(area[mask0 & half].sum()) for half in view.sides.values()]
                    if cut == 0.05:
                        control_masks[case, depth] = mask0
                        control_fits[case, depth] = background0
                        largest = float(((background0 - initial) / background0)[view.search].max())
                clean = next((cut for cut in LADDER if not any(selected[cut])), None)
                first_clean[case, depth] = clean
                initial_images[case, depth] = {'digest': digest, 'image': initial, 'ages': 1}
                controls.append({
                    'case': case, 'depth': depth, 'time_zero_selected_kpc2_at_5pct': sum(selected[0.05]),
                    'share_of_search': sum(selected[0.05]) / float(area[view.search].sum()),
                    'largest_time_zero_fitted_deficit_in_search': largest, 'first_clean_cut': clean,
                    **{f'selected_kpc2_at_{round(cut * 100)}pct': sum(selected[cut]) for cut in LADDER[1:]}})
            else:
                initial_images[case, depth]['ages'] += initial_images[case, depth]['digest'] == digest

            control = control_masks[case, depth]
            fit = view.profiles(current, nothing)[0]
            dimmed = current < 0.95 * initial
            lobe = float(area[truth].sum())
            theirs = published[case, index, depth]
            for label_name, cut in (('registered_5pct', 0.05), ('first_clean', first_clean[case, depth])):
                if cut is None:
                    continue
                mask, background = outline(view, fit, cut, det, label)
                overlap, false = mask & truth, mask & ~truth
                background0 = control_fits[case, depth]
                on_false = lambda image: float((area * image)[false].sum()) if false.any() else float('nan')
                selected_area, overlap_area = float(area[mask].sum()), float(area[overlap].sum())
                outlines.append({
                    'case': case, 'snapshot_index': index, 'depth': depth, 'outline': label_name, 'cut': cut,
                    'lobe_kpc2': lobe, 'lobe_outside_aperture_kpc2': float(area[truth & ~view.search].sum()),
                    'selected_kpc2': selected_area, 'overlap_kpc2': overlap_area, 'false_kpc2': selected_area - overlap_area,
                    'coverage': overlap_area / lobe, 'purity': overlap_area / selected_area if selected_area else float('nan'),
                    'control_cover_of_lobe': float(area[control & truth].sum()) / lobe,
                    'overlap_in_control_outline_kpc2': float(area[overlap & control].sum()),
                    'overlap_not_dimmed_kpc2': float(area[overlap & ~dimmed].sum()),
                    'dimmed_on_lobe_fraction': float(area[dimmed & truth].sum()) / lobe,
                    'dimmed_on_lobe_missed_kpc2': float(area[dimmed & truth & ~mask].sum()),
                    'dimmed_off_lobe_in_search_kpc2': float(area[dimmed & ~truth & view.search].sum()),
                    'false_dimmed_kpc2': float(area[false & dimmed].sum()),
                    'false_time_zero_fit_over_time_zero_image': on_false(background0) / on_false(initial),
                    'false_current_fit_over_time_zero_fit': on_false(background) / on_false(background0),
                    'false_current_over_time_zero_image': on_false(current) / on_false(initial),
                    'false_area_weighted_radius_kpc': on_false(view.radius) / on_false(np.ones_like(initial))})
                row = outlines[-1]
                if label_name == 'registered_5pct':
                    for name, column in (('selected_kpc2', 'registered_selected_kpc2'), ('overlap_kpc2', 'registered_overlap_kpc2'),
                                         ('false_kpc2', 'registered_false_kpc2'), ('coverage', 'registered_completeness'),
                                         ('control_cover_of_lobe', 'control_coverage'),
                                         ('overlap_in_control_outline_kpc2', 'overlap_in_control_outline_kpc2'),
                                         ('overlap_not_dimmed_kpc2', 'overlap_not_dimmed_kpc2'),
                                         ('dimmed_on_lobe_missed_kpc2', 'dimmed_on_lobe_missed_kpc2'),
                                         ('dimmed_off_lobe_in_search_kpc2', 'dimmed_off_lobe_in_search_kpc2')):
                        compare(unit, depth, name, row[name], theirs[column])
                    compare(unit, depth, 'dimmed_on_lobe_kpc2', row['dimmed_on_lobe_fraction'] * lobe, theirs['dimmed_on_lobe_kpc2'])
                    compare(unit, depth, 'time_zero_selected_kpc2', float(area[control].sum()), theirs['time_zero_selected_kpc2'])
                else:
                    compare(unit, depth, 'first_clean_cut', cut, theirs['first_clean_cut'])
                    compare(unit, depth, 'first_clean_coverage', row['coverage'], theirs['first_clean_coverage'])
                    compare(unit, depth, 'first_clean_false_kpc2', row['false_kpc2'], theirs['first_clean_false_kpc2'])

            full0, full1 = total(maps['initial_full']), total(maps['current_full'])
            slab0, slab1 = total(initial), total(current)
            deficit, full_deficit = 1 - slab1 / slab0, 1 - full1 / full0
            compare(unit, depth, 'matched_deficit', deficit, theirs['matched_deficit'])
            compare(unit, depth, 'full_deficit', full_deficit, theirs['full_deficit'])
            compare(unit, depth, 'unchanged_outer_deficit', (slab0 - slab1) / full0, theirs['unchanged_outer_deficit'])
            if depth == 'full':
                short0, short1 = total(maps['initial_full'], short), total(maps['current_full'], short)
                continue
            lobe0 = total(maps['initial_on_current_lobe_full']) - total(maps[f'initial_on_current_lobe_{depth}'])
            lobe1 = total(maps['current_lobe_full']) - total(maps[f'current_lobe_{depth}'])
            ambient0, ambient1 = full0 - slab0 - lobe0, full1 - slab1 - lobe1
            outer.append({
                'case': case, 'snapshot_index': index, 'depth': depth,
                'lobe_volume_inside_slab': float(theirs['slab_volume_retained_fraction']),
                'initial_light_inside_slab': slab0 / full0, 'slab_deficit': deficit, 'full_deficit': full_deficit,
                'points_from_initial_outer_light': deficit - (slab0 - slab1) / full0,
                'points_from_outer_change': (slab0 - slab1) / full0 - full_deficit,
                'points_from_outer_lobe_cells': -(lobe0 - lobe1) / full0,
                'points_from_outer_ambient_gas': -(ambient0 - ambient1) / full0,
                'outer_ambient_fractional_change': ambient1 / ambient0 - 1,
                'outer_lobe_cell_share_of_outer_initial_light': lobe0 / (full0 - slab0),
                'short_path_area_kpc2': float(area[short].sum()),
                'short_path_full_column_change': short1 / short0 - 1 if short0 else float('nan')})

            dx = np.diff(maps['horizontal_edges_kpc'])
            for epoch, name, key in (('current', f'{case}_{index:04d}', f'current_{depth}'), ('initial', f'{case}_0000', f'initial_{depth}')):
                with np.load(args.archive / f'references/map_inputs/{name}_90deg.npz', allow_pickle=False) as side:
                    edges, image, same_rows = side['horizontal_edges_kpc'], side[WHOLE], np.array_equal(side['z_edges_kpc'], maps['z_edges_kpc'])
                slab = (maps[key] * dx[None, :]).sum(axis=1)
                exact = (image * weights(edges, DEPTHS[depth], 'exact')[None, :]).sum(axis=1)
                wider = (image * weights(edges, DEPTHS[depth], 'one_pixel_wider')[None, :]).sum(axis=1)
                dz = np.abs(np.diff(maps['z_edges_kpc']))
                rows.append({
                    'case': case, 'snapshot_index': index, 'depth': depth, 'epoch': epoch, 'same_z_rows': bool(same_rows),
                    'z_rows': len(slab), 'flux_ratio_minus_one': (dz * slab).sum() / (dz * exact).sum() - 1,
                    'largest_row_ratio_minus_one': float(np.abs(slab / exact - 1).max()),
                    'flux_change_if_one_pixel_wider': (dz * wider).sum() / (dz * exact).sum() - 1})
        print(case, index, flush=True)

    for (case, depth), entry in initial_images.items():
        partner = next(other for other in initial_images if other[1] == depth and other[0] != case and ATMOSPHERE[other[0]] == ATMOSPHERE[case])
        other = initial_images[partner]['image']
        relative = np.abs(entry['image'] / other - 1)
        radius = np.hypot(axes['horizontal_axis_kpc'][None, :], axes['z_axis_kpc'][:, None])
        row = next(r for r in controls if (r['case'], r['depth']) == (case, depth))
        row.update({
            'ages_with_identical_initial_image': entry['ages'], 'same_atmosphere_run': partner[0],
            'pixels_differing_from_that_run': int((entry['image'] != other).sum()),
            'largest_radius_of_a_differing_pixel_kpc': float(radius[entry['image'] != other].max()),
            'largest_relative_difference_from_that_run': float(relative.max()),
            'same_control_outline_as_that_run': bool(np.array_equal(control_masks[case, depth], control_masks[partner]))})

    for name, table in (('outer_gas.csv', outer), ('controls.csv', controls), ('outlines.csv', outlines),
                        ('side_view_rows.csv', rows), ('comparison.csv', comparison)):
        write(name, table)
    digest = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
    summary = {
        'case_ages': len(units), 'values_compared_with_published': len(comparison),
        'values_agreeing': sum(r['agrees'] for r in comparison),
        'disagreements': [r for r in comparison if not r['agrees']][:40],
        'largest_evolved_row_difference': {d: max(r['largest_row_ratio_minus_one'] for r in rows if (r['depth'], r['epoch']) == (d, 'current')) for d in ('slab30', 'slab10')},
        'largest_initial_row_difference': {d: max(r['largest_row_ratio_minus_one'] for r in rows if (r['depth'], r['epoch']) == (d, 'initial')) for d in ('slab30', 'slab10')},
        'published_table_sha256': digest(PUBLIC / 'case_age_depth.csv'),
        'tables': {name: digest(OUT / name) for name in ('outer_gas.csv', 'controls.csv', 'outlines.csv', 'side_view_rows.csv', 'comparison.csv')}}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'tables'}, indent=1)[:3000])


if __name__ == '__main__':
    main()
