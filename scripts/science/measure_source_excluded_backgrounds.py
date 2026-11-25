"""Apply source-excluded radial backgrounds to the original DET-05 images."""

import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

import compare_compressive_front as front
import fit_source_excluded_background as radial
import source_excluded_inputs as inputs
import xray_cavity_method_ladder as ladder


SPEEDS = (30, 100, 300)
CHANGES = ('pressure_changed', 'density_changed', 'boundary_thermo_changed')
PRIMARY = ('original', 'tracer', 'speed_100')
PROTOCOL = inputs.SCIENCE / 'source_excluded_background_protocol_2026-11-25.md'
CRITERIA = inputs.load_config(inputs.SCIENCE.parents[1] / 'configs/background_refit_blind_2026-11-11.json')['criteria']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_native(view, root):
    directory = root / f'{view.case}_{view.snapshot_index:04d}'
    receipt_path = directory / 'completion.json'
    receipt = json.loads(receipt_path.read_text())
    if ((receipt['case'], receipt['snapshot_index'], receipt['kind']) != (view.case, view.snapshot_index, view.kind)
            or receipt['producer_sha256'] != view.provenance['producer_receipt_sha256']
            or not np.isclose(receipt['time_myr'], view.actual_age_myr, rtol=0, atol=1e-8)):
        raise ValueError(f'{view.unit_id}: incorrect native projection binding')
    for role, record in receipt['native_inputs'].items():
        if record['sha256'] != view.provenance[role + '_sha256']:
            raise ValueError(f'{view.unit_id}: native {role} identity differs')
    file = directory / (view.unit_id + '.npz')
    record = receipt['files'][file.name]
    if file.stat().st_size != record['size_bytes'] or sha(file) != record['sha256']:
        raise ValueError(f'{view.unit_id}: native projection digest differs')
    with np.load(file, allow_pickle=False) as data:
        if any(not np.array_equal(data[name], axis) for name, axis in view.axes.items()):
            raise ValueError(f'{view.unit_id}: unequal original and native detector grids')
        maps = {k: data[k] for k in ('tracer_footprint', *(f'speed_ge_{s}' for s in SPEEDS), *CHANGES)}
    if any(mask.dtype != bool or mask.shape != view.image.shape for mask in maps.values()):
        raise ValueError(f'{view.unit_id}: invalid native sky mask')
    tracer = maps['tracer_footprint']
    if not tracer.any() or (view.kind != 'initial_null' and not np.array_equal(tracer, view.target_path_kpc > 0)):
        raise ValueError(f'{view.unit_id}: native and original tracer footprints disagree')
    if (np.any(maps['speed_ge_300'] & ~maps['speed_ge_100']) or np.any(maps['speed_ge_100'] & ~maps['speed_ge_30'])
            or np.any(maps['boundary_thermo_changed'] & ~(maps['pressure_changed'] | maps['density_changed']))):
        raise ValueError(f'{view.unit_id}: inconsistent native support nesting')
    projection = receipt['projection'][str(view.view_deg)]
    if any(projection['footprint_pixels'][k] != int(m.sum()) for k, m in maps.items()):
        raise ValueError(f'{view.unit_id}: projection pixel counts disagree')
    metadata = {'native_receipt_sha256': sha(receipt_path), 'native_map_sha256': record['sha256'],
                'producer_source_sha256': receipt['source_code_sha256'], 'pbs_job': receipt['pbs_job_id'],
                'boundary_face_counts': receipt['boundary_face_counts'],
                'projected_tracer_kpc3': projection['projected_tracer_kpc3'],
                'native_tracer_kpc3': projection['native_tracer_kpc3']}
    return maps, metadata


def detect(image, grid, background):
    return ladder.deficit_threshold(image, grid.u, grid.z, background=background,
                                    background_label='radial', threshold=0.05).mask


def score_mask(view, grid, mask):
    truth = view.target_path_kpc > 0
    area = grid.area
    dimmed = (view.initial_image > 0) & (view.image < 0.95 * view.initial_image)
    rows = {}
    for side, half in (('negative_z', grid.z[:, None] < 0), ('positive_z', grid.z[:, None] > 0),
                       ('both', np.ones((len(grid.z), 1), dtype=bool))):
        result = front.recovery_metrics(grid, mask, view.target_path_kpc, half, view.baseline_mask)
        selected = mask & half
        intersection = selected & truth
        result['intersection_kpc2'] = float(area[intersection].sum())
        result['false_dimmed_over_5pct_kpc2'] = float(area[selected & ~truth & dimmed].sum())
        result['captured_native_kpc3'] = float((area[intersection] * view.target_path_kpc[intersection]).sum())
        if not np.isclose(result['native_lobe_kpc3'], view.native_volume_kpc3[side], rtol=2e-12):
            raise ValueError(f'{view.unit_id}/{side}: native volume closure failed')
        if side != 'both':
            result['screen_passed'] = (result['nondetection'] if view.kind == 'initial_null' else bool(
                result['completeness'] is not None and result['completeness'] >= CRITERIA['minimum_completeness']
                and result['purity'] is not None and result['purity'] >= CRITERIA['minimum_purity']
                and not result['touches_aperture']))
        rows[side] = result
    for field in ('selected_kpc2', 'truth_kpc2', 'intersection_kpc2', 'false_area_kpc2', 'inferred_volume_kpc3',
                  'native_lobe_kpc3', 'captured_native_kpc3'):
        halves = rows['negative_z'][field] + rows['positive_z'][field]
        if not np.isclose(rows['both'][field], halves, rtol=1e-10, atol=1e-8):
            raise ValueError(f'{view.unit_id}: hemispheres do not close for {field}')
    return rows


def describe_support(fit, excluded, maps, grid, valid, bins):
    area = grid.area
    retained = valid & ~excluded
    n = len(fit.rows)
    flags = {k: maps[k] for k in CHANGES if k in maps}
    if flags:
        flags['thermo_changed'] = flags['pressure_changed'] | flags['density_changed']
    tracer = maps['tracer_footprint']
    flags['tracer'] = tracer
    for name, mask in flags.items():
        use = retained & mask
        areas = np.bincount(bins[use], weights=area[use], minlength=n)
        for index, row in enumerate(fit.rows):
            row['retained_' + name + '_kpc2'] = float(areas[index])
    for row in fit.rows:
        if any(row['retained_' + key + '_kpc2'] > row['retained_area_kpc2'] + 1e-7 for key in flags):
            raise ValueError('retained intersection larger than its annulus')
    direct = [r for r in fit.rows if r['support_class'] == 'direct']
    inner = [r for r in fit.rows if r['support_class'] == 'inner_extrapolated']
    coverage = {'valid_area_kpc2': float(area[valid].sum()), 'retained_area_kpc2': float(area[retained].sum()),
                'excluded_area_kpc2': float(area[valid & excluded].sum()),
                'min_direct_inner_kpc': direct[0]['r_inner_kpc'] if direct else None,
                'central_extrapolation_kpc': inner[-1]['r_outer_kpc'] if inner else (0. if direct else None),
                'n_direct': len(direct), 'n_bracketed': sum(r['support_class'] == 'interpolated' for r in fit.rows),
                'n_outer_extrapolated': sum(r['support_class'] == 'outer_extrapolated' for r in fit.rows),
                'tracer_sky_kpc2': float(area[tracer].sum()), 'unmasked_tracer_sky_kpc2': float(area[tracer & ~excluded].sum()),
                'valid_tracer_kpc2': float(area[tracer & valid].sum())}
    coverage.update({'retained_' + k + '_kpc2': sum(r['retained_' + k + '_kpc2'] for r in fit.rows) for k in flags})
    return coverage


def process_view(view, output, native_root=None, make_figure=True):
    destination = output / view.unit_id
    grid = front.Grid(*(view.axes[k] for k in inputs.AXES))
    model = radial.prepare_radial_fit(view.image, grid.u, grid.z, grid.ue, grid.ze)
    original = detect(view.image, grid, model.baseline)
    if not np.array_equal(original, view.baseline_mask):
        raise ValueError(f'{view.unit_id}: original outline differs from archived DET-05 or exposed reference')
    native = None
    if native_root:
        maps, native = read_native(view, native_root)
    elif view.fit_tracer_path_kpc is not None:
        maps = {'tracer_footprint': view.fit_tracer_path_kpc > 0}
    else:
        raise ValueError(f'{view.unit_id}: initial control fitting requires the physical nozzle projection')
    exclusions = {'original': np.zeros_like(original), 'tracer': maps['tracer_footprint']}
    if native:
        exclusions.update({f'speed_{cut}': maps[f'speed_ge_{cut}'] for cut in SPEEDS})
    valid = ladder._rois(grid.u, grid.z)[0] & np.isfinite(view.image) & (view.image > 0)
    bins = (np.hypot(grid.u[None, :], grid.z[:, None]) / ladder.recovery.RADIAL_BIN_KPC).astype(int)
    fits, selected, arms = {}, {}, {}
    for name, excluded in exclusions.items():
        fit = model.fit(excluded)
        stats = describe_support(fit, excluded, maps, grid, valid, bins)
        arms[name] = {'status': fit.status, 'coverage': stats, 'bins': fit.rows, 'scores': {}, 'mask_sha256': {}}
        flat = None
        for continuation in ('flat', 'log_slope') if name != 'original' else ('flat',):
            bg = fit.backgrounds[continuation]
            if bg is None:
                continue
            if continuation == 'log_slope' and bg is fit.backgrounds['flat']:
                arms[name]['scores'][continuation] = arms[name]['scores']['flat']
                arms[name]['mask_sha256'][continuation] = arms[name]['mask_sha256']['flat']
                continue
            mask = original if name == 'original' else detect(view.image, grid, bg)
            arms[name]['mask_sha256'][continuation] = hashlib.sha256(mask.tobytes(order='C')).hexdigest()
            if continuation == 'flat':
                flat = mask
            arms[name]['scores'][continuation] = score_mask(view, grid, mask)
        if name in PRIMARY:
            fits[name], selected[name] = fit, flat
    result = {'unit_id': view.unit_id, 'case': view.case, 'index': view.snapshot_index,
              'age_myr': view.actual_age_myr, 'angle': view.view_deg, 'kind': view.kind,
              'qualifications': view.qualification_holds, 'original_replayed': True,
              'protocol_sha256': sha(PROTOCOL), 'original_inputs': view.provenance,
              'native_support': native, 'arms': arms}
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output, prefix='.' + view.unit_id + '-') as tmp:
        path = Path(tmp) / view.unit_id
        path.mkdir(mode=0o700)
        if native and make_figure:
            from plot_source_excluded_background import plot_view
            plot_view(view, fits, exclusions, selected, path / 'comparison.png')
        (path / 'result.json').write_text(json.dumps(result, allow_nan=False, separators=(',', ':')) + '\n')
        path.rename(destination)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exposed-dir', type=Path, required=True)
    p.add_argument('--prediction-tar', type=Path, required=True)
    p.add_argument('--truth-tar', type=Path, required=True)
    p.add_argument('--native-root', type=Path, help='verified projections, required for speed, controls and figures')
    p.add_argument('--cohort', choices=('exposed', 'registered', 'all'), default='all')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--without-figures', action='store_true')
    args = p.parse_args()
    for view in inputs.iter_source_views(args.exposed_dir, args.prediction_tar, args.truth_tar,
                                         include_exposed=args.cohort != 'registered', include_registered=args.cohort != 'exposed'):
        if not args.native_root and view.kind == 'initial_null':
            continue
        process_view(view, args.out, args.native_root, not args.without_figures)
        print(view.unit_id, flush=True)


if __name__ == '__main__':
    main()
