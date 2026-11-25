"""Review of the G-HI/20 midplane-slab pilot (XR-07).

Codex's second implementation of the slab scores already uses the detector
in review_source_excluded_backgrounds.py, so replaying the three outlines
here is a rerun, not a third implementation. This script adds what the
pilot did not measure:

- the registered detector applied to the three time-zero images, and the
  outline at stricter cuts;
- the excess of the smoothed radial fit over an undisturbed atmosphere;
- the area dimmed or brightened by more than 5% against matched time zero,
  on and off the lobe;
- the flux balance by depth layer on detected and missed sightlines and by
  tracer path length;
- two checks of the slab geometry that do not use job 884129: the lobe
  volume inside each slab from the archived 90-degree path map, and the
  time-zero slab images predicted from a spherical deprojection of the
  full-depth time-zero image.

Without arguments it re-summarises the committed tables.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / 'docs/science/assets/ghi20_midplane_slabs_2026-11-25'
OUT = ROOT / 'docs/science/assets/ghi20_midplane_slab_review_2026-11-25'
DEPTHS = {'full': 200., 'slab30': 30., 'slab10': 10.}
CUTS = (0.05, 0.06, 0.07, 0.08, 0.10, 0.15, 0.20)
BANDS = tuple(range(0, 120, 20))
PATHS = (0., 5., 10., 20., 30., 40., 50., 60., 100.)
SIDES = ('negative_z', 'positive_z', 'both')


def write(name, rows):
    with (OUT / name).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def read(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def outline(view, profile, cut, det, label):
    background = np.interp(np.minimum(view.radius, view.centres[-1]), view.centres, profile)
    candidate = view.search & view.fit_region & (background > 0) & ((background - view.image) / background > cut)
    mask = np.zeros(view.image.shape, dtype=bool)
    for half in view.sides.values():
        labels = label(candidate & half, connectivity=2)
        areas = np.bincount(labels.ravel(), weights=view.filter_area.ravel())
        keep = np.flatnonzero(areas >= det.MIN_AREA)
        mask |= np.isin(labels, keep[keep > 0])
    return mask, background


def deproject(radius, area, full, slabs):
    from scipy.interpolate import CubicSpline
    from scipy.optimize import least_squares

    edges = np.concatenate((np.geomspace(0.5, 20, 40)[:-1], np.arange(20, 200.5, 2.)))
    index = np.digitize(radius.ravel(), edges) - 1
    inside = (index >= 0) & (index < len(edges) - 1)

    def profile(image):
        weight = np.bincount(index[inside], weights=area.ravel()[inside], minlength=len(edges) - 1)
        return np.bincount(index[inside], weights=(area * image).ravel()[inside], minlength=len(edges) - 1) / weight

    centre = profile(radius)
    knots = np.geomspace(0.3, 450, 26)

    def integral(values, half):
        y = np.linspace(0, 1, 1201) ** 2 * half
        r = np.clip(np.hypot(centre[:, None], y[None, :]), knots[0], knots[-1])
        return 2 * np.trapezoid(np.exp(CubicSpline(np.log(knots), values, bc_type='natural')(np.log(r))), y, axis=1)

    measured = profile(full)
    fit = least_squares(lambda p: np.log(integral(p, 200.)) - np.log(measured), np.log(np.interp(knots, centre, measured / 400.)))
    result = {'full_fit_rms_log_residual': float(np.sqrt(np.mean(fit.fun ** 2)))}
    for name, image in slabs.items():
        error = integral(fit.x, DEPTHS[name]) / profile(image) - 1
        for lo, hi in ((2, 20), (20, 60), (60, 120), (120, 180)):
            band = (centre >= lo) & (centre < hi)
            result[f'{name}_{lo}_{hi}_kpc_max_abs_error'] = float(np.abs(error[band]).max())
    return result


def run(args):
    from skimage.measure import label
    import review_source_excluded_backgrounds as det

    with np.load(args.projection, allow_pickle=False) as data:
        maps = {key: data[key] for key in data.files}
    axes = {key: maps[key] for key in det.AXES}
    path = maps['tracer_path_full']
    truth = path > 0
    nothing = np.zeros_like(truth)
    receipt = json.loads((PUBLIC / 'score_receipt.json').read_text())
    checks, outlines, bias, physical, layers = [], [], [], [], []
    masks, exterior = {}, {}

    for depth in DEPTHS:
        current, initial = maps[f'current_{depth}'], maps[f'initial_{depth}']
        if (current <= 0).any() or (initial <= 0).any():
            raise ValueError(f'{depth}: non-positive brightness')
        view = det.View(depth, 'science', axes, current, initial, path, nothing, None)
        null = det.View(depth, 'initial_null', axes, initial, initial, path, nothing, None)
        area, halves = view.area, {**view.sides, 'both': np.ones_like(truth)}
        fit, fit0 = view.profiles(current, nothing)[0], null.profiles(initial, nothing)[0]
        raw0 = null.medians(initial, nothing)
        zero = {}
        for cut in CUTS:
            mask, background = outline(view, fit, cut, det, label)
            zero[cut], background0 = outline(null, fit0, cut, det, label)
            if cut == 0.05:
                masks[depth], used = mask, (background, background0)
                checks.append((f'{depth} outline digest', hashlib.sha256(mask.tobytes()).hexdigest()
                               == receipt['candidate_mask_sha256'][depth]))
            for epoch, chosen in (('current', mask), ('time_zero', zero[cut])):
                for side, half in halves.items():
                    selected, overlap = area[chosen & half].sum(), area[chosen & truth & half].sum()
                    outlines.append({
                        'depth': depth, 'epoch': epoch, 'cut': cut, 'hemisphere': side, 'selected_kpc2': selected,
                        'overlap_kpc2': overlap, 'false_kpc2': selected - overlap,
                        'coverage': overlap / area[truth & half].sum(), 'purity': overlap / selected if selected else '',
                        'share_of_search_area': selected / area[view.search & half].sum()})
        mask, (background, background0) = masks[depth], used
        false = mask & ~truth
        total = lambda image: float((area * image)[false].sum())
        exterior[depth] = {
            'false_kpc2': float(area[false].sum()), 'false_inside_time_zero_outline_kpc2': float(area[false & zero[0.05]].sum()),
            'current_over_time_zero_image': total(current) / total(initial),
            'time_zero_fit_over_time_zero_image': total(background0) / total(initial),
            'current_fit_over_time_zero_fit': total(background) / total(background0),
            'current_fit_over_time_zero_image': total(background) / total(initial),
            'largest_time_zero_fitted_deficit_in_search': float(((background0 - initial) / background0)[view.search].max())}
        raw = np.interp(np.minimum(view.radius, view.centres[-1]), view.centres, raw0)
        for inner in BANDS:
            band = (view.radius >= inner) & (view.radius < inner + 20)
            mean = lambda image: float((area * image)[band].sum() / area[band].sum())
            bins = slice(inner // 5, inner // 5 + 4)
            bias.append({
                'depth': depth, 'r_inner_kpc': inner, 'r_outer_kpc': inner + 20, 'area_kpc2': area[band].sum(),
                'time_zero_log_slope': np.polyfit(np.log(view.centres[bins]), np.log(raw0[bins]), 1)[0],
                'time_zero_deficit_against_smoothed_fit': mean((background0 - initial) / background0),
                'time_zero_deficit_against_unsmoothed_medians': mean((raw - initial) / raw),
                'time_zero_selected_kpc2': area[band & zero[0.05]].sum(),
                'current_false_kpc2': area[band & false].sum()})
        dim, bright = current < 0.95 * initial, current > 1.05 * initial
        physical.append({
            'depth': depth, 'lobe_kpc2': area[truth].sum(), 'search_kpc2': area[view.search].sum(),
            'dimmed_on_lobe_kpc2': area[dim & truth].sum(), 'dimmed_off_lobe_in_search_kpc2': area[dim & ~truth & view.search].sum(),
            'brightened_on_lobe_kpc2': area[bright & truth].sum(),
            'brightened_off_lobe_in_search_kpc2': area[bright & ~truth & view.search].sum()})
        slab = maps[f'tracer_path_{depth}'] > 0
        for row in read(PUBLIC / 'areas.csv'):
            if row['depth'] != depth:
                continue
            target = (truth if row['target'] == 'full_lobe' else slab) & halves[row['hemisphere']]
            chosen = mask & halves[row['hemisphere']]
            mine = (area[chosen].sum(), area[chosen & target].sum(), area[target & ~chosen].sum(), area[chosen & ~target].sum())
            theirs = [float(row[k]) for k in ('selected_kpc2', 'overlap_kpc2', 'missed_kpc2', 'false_kpc2')]
            checks.append((f"{depth}/{row['hemisphere']}/{row['target']} areas", np.allclose(mine, theirs, rtol=0, atol=1e-8)))

    area = np.outer(np.abs(np.diff(axes['z_edges_kpc'])), np.abs(np.diff(axes['horizontal_edges_kpc'])))
    detected, missed = truth & masks['full'], truth & ~masks['full']
    regions = {'lobe': truth, 'detected_at_full_depth': detected, 'missed_at_full_depth': missed}
    regions.update({f'path_{lo:g}_{hi:g}_kpc': truth & (path > lo) & (path <= hi) for lo, hi in zip(PATHS[:-1], PATHS[1:])})
    slices = {'within_10_kpc': ('slab10', None), '10_to_30_kpc': ('slab30', 'slab10'), 'beyond_30_kpc': ('full', 'slab30'),
              'whole_sightline': ('full', None)}
    for name, region in regions.items():
        flux = lambda key: float((area * maps[key])[region].sum())
        whole = flux('initial_full')
        for layer, (outer, inner) in slices.items():
            now, before = (flux(f'{epoch}_{outer}') - (flux(f'{epoch}_{inner}') if inner else 0.) for epoch in ('current', 'initial'))
            layers.append({
                'sightlines': name, 'area_kpc2': area[region].sum(), 'layer': layer, 'share_of_initial_flux': before / whole,
                'fractional_change': now / before - 1,
                'detected_full': area[region & masks['full']].sum() / area[region].sum(),
                'detected_slab30': area[region & masks['slab30']].sum() / area[region].sum(),
                'detected_slab10': area[region & masks['slab10']].sum() / area[region].sum()})
    public = {(r['depth'], r['region'], r['hemisphere']): r for r in read(PUBLIC / 'filling.csv')}
    for depth in DEPTHS:
        for name, region in (('full_lobe', truth), ('missed_by_full_depth_detector', missed)):
            row = public[depth, name, 'both']
            mine = [(area * maps[f'{epoch}_{depth}'])[region].sum() for epoch in ('current', 'initial')]
            checks.append((f'{depth}/{name} fluxes', np.allclose(mine, [float(row['current_flux']), float(row['initial_flux'])], rtol=1e-12)))

    geometry = {}
    with np.load(args.side_view, allow_pickle=False) as side:
        y_edges, side_path = side['horizontal_edges_kpc'], side['path_C_kpc']
        z = side['z_axis_kpc']
        cell = np.outer(np.abs(np.diff(side['z_edges_kpc'])), np.abs(np.diff(y_edges)))
    native = json.loads((PUBLIC / 'native_completion.json').read_text())['native_tracer_volume_kpc3']
    for depth, half_width in DEPTHS.items():
        inside = np.clip(np.minimum(y_edges[1:], half_width) - np.maximum(y_edges[:-1], -half_width), 0, None) / np.diff(y_edges)
        for side_name, rows in (('negative_z', z < 0), ('positive_z', z > 0), ('both', np.ones_like(z, dtype=bool))):
            volume = float((cell * side_path * inside[None, :])[rows].sum())
            geometry[f'{depth}/{side_name}'] = {'side_view_kpc3': volume, 'slab_job_kpc3': native[depth][side_name]}
            checks.append((f'{depth}/{side_name} lobe volume from the 90-degree archive',
                           np.isclose(volume, native[depth][side_name], rtol=1e-6)))
    radius = np.hypot(axes['horizontal_axis_kpc'][None, :], axes['z_axis_kpc'][:, None])
    deprojection = deproject(radius, area, maps['initial_full'], {k: maps[f'initial_{k}'] for k in ('slab30', 'slab10')})
    checks += [(f'{k} time-zero image from deprojection, 20 to 120 kpc',
                max(deprojection[f'{k}_20_60_kpc_max_abs_error'], deprojection[f'{k}_60_120_kpc_max_abs_error']) < 0.005)
               for k in ('slab30', 'slab10')]

    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit('failed: ' + '; '.join(failed))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (('outlines.csv', outlines), ('background_bias.csv', bias), ('physical_reference.csv', physical),
                       ('layers.csv', layers)):
        write(name, rows)
    flux = {(depth, epoch): float((area * maps[f'{epoch}_{depth}'])[truth].sum()) for depth in DEPTHS for epoch in ('current', 'initial')}
    lobe_cells = {depth: float((area * maps[f'current_lobe_{depth}'])[truth].sum()) for depth in DEPTHS}
    (OUT / 'run.json').write_text(json.dumps({
        'projection_sha256': hashlib.file_digest(args.projection.open('rb'), 'sha256').hexdigest(),
        'side_view_sha256': hashlib.file_digest(args.side_view.open('rb'), 'sha256').hexdigest(),
        'checks_passed': len(checks), 'exterior': exterior, 'lobe_volume': geometry, 'deprojection': deprojection,
        'footprint_flux': {f'{d}/{e}': v for (d, e), v in flux.items()}, 'footprint_flux_from_lobe_cells': lobe_cells},
        indent=2) + '\n')
    print(f'{len(checks)} checks passed')


def summarise():
    run_record = json.loads((OUT / 'run.json').read_text())
    flux, lobe_cells = run_record['footprint_flux'], run_record['footprint_flux_from_lobe_cells']
    outlines = {(r['depth'], r['epoch'], float(r['cut'])): r for r in read(OUT / 'outlines.csv') if r['hemisphere'] == 'both'}
    layers = {(r['sightlines'], r['layer']): r for r in read(OUT / 'layers.csv')}
    summary = {'checks_passed': run_record['checks_passed'], 'depths': {}}
    for depth in DEPTHS:
        now, before = flux[f'{depth}/current'], flux[f'{depth}/initial']
        physical = next(r for r in read(OUT / 'physical_reference.csv') if r['depth'] == depth)
        dim_on, dim_off = float(physical['dimmed_on_lobe_kpc2']), float(physical['dimmed_off_lobe_in_search_kpc2'])
        first_clean = next(cut for cut in CUTS if float(outlines[depth, 'time_zero', cut]['selected_kpc2']) == 0)
        summary['depths'][depth] = {
            'footprint_deficit': 1 - now / before,
            'footprint_deficit_without_lobe_cell_emission': 1 - (now - lobe_cells[depth]) / before,
            'full_depth_deficit_if_gas_outside_this_depth_were_unchanged': (before - now) / flux['full/initial'],
            'time_zero_selected_kpc2_at_5pct': float(outlines[depth, 'time_zero', 0.05]['selected_kpc2']),
            'current_selected_share_of_search_area': float(outlines[depth, 'current', 0.05]['share_of_search_area']),
            'lowest_tested_cut_with_empty_time_zero_outline': first_clean,
            'current_outline_at_that_cut': {k: float(outlines[depth, 'current', first_clean][k])
                                            for k in ('coverage', 'purity', 'false_kpc2')},
            'dimmed_over_5pct_coverage': dim_on / float(physical['lobe_kpc2']),
            'dimmed_over_5pct_purity': dim_on / (dim_on + dim_off),
            'dimmed_over_5pct_off_lobe_kpc2': dim_off,
            'exterior': run_record['exterior'][depth]}
    summary['layer_change'] = {name: {layer: float(layers[name, layer]['fractional_change']) for layer in
                                      ('within_10_kpc', '10_to_30_kpc', 'beyond_30_kpc', 'whole_sightline')}
                               for name in ('lobe', 'detected_at_full_depth', 'missed_at_full_depth', 'path_0_5_kpc', 'path_60_100_kpc')}
    for name, key in (('missed', 'missed_at_full_depth'), ('detected', 'detected_at_full_depth')):
        inner = sum(float(layers[key, layer]['share_of_initial_flux']) * float(layers[key, layer]['fractional_change'])
                    for layer in ('within_10_kpc', '10_to_30_kpc'))
        summary[f'{name}_change_if_gas_beyond_30_kpc_were_unchanged'] = inner
    summary['deprojection'] = run_record['deprojection']
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--projection', type=Path, help='projections.npz from the slab job')
    parser.add_argument('--side-view', type=Path, help='archived G-HI_0020_90deg.npz')
    args = parser.parse_args()
    if args.projection:
        run(args)
    summarise()


if __name__ == '__main__':
    main()
