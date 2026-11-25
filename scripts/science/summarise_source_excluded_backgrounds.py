"""Publish compact numerical diagnostics and reproduce the source-exclusion comparisons."""

import argparse
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'docs/science/assets/source_excluded_backgrounds_2026-11-25'
CONFIG = ROOT / 'configs/background_refit_blind_2026-11-11.json'
ARMS = ('original', 'tracer', 'speed_30', 'speed_100', 'speed_300')
CASES = ('C-HI', 'C-LO', 'G-HI', 'G-LO')
SIDES = ('negative_z', 'positive_z', 'both')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_table(path, rows):
    cols = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('wb') as stream, gzip.GzipFile(filename='', mode='wb', fileobj=stream, mtime=0) as zipped:
        with io.TextIOWrapper(zipped, encoding='utf-8', newline='') as text:
            writer = csv.DictWriter(text, fieldnames=cols, lineterminator='\n')
            writer.writeheader()
            writer.writerows(rows)


def read_table(path):
    with gzip.open(path, 'rt', newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def expected():
    config = json.loads(CONFIG.read_text())
    return {f'{case}_{idx:04d}_{angle}deg': ('initial_null' if idx == 0 else
            'development' if (case, idx) == ('G-HI', 20) else 'science')
            for case, indices in config['heldout_indices'].items()
            for idx in [0, *indices, *([20] if case == 'G-HI' else [])] for angle in config['azimuths_deg']}


def collect(source, out):
    cohort = expected()
    units, coverage, annuli, scores = [], [], [], []
    files = {p.parent.name: p for p in source.glob('*/result.json')}
    if set(files) != set(cohort):
        raise ValueError(f'result inventory differs: {sorted(set(files) ^ set(cohort))}')
    for uid, path in sorted(files.items()):
        data = json.loads(path.read_text())
        if (data['unit_id'] != uid or data['kind'] != cohort[uid] or not data['original_replayed']
                or set(data['arms']) != set(ARMS) or not data['native_support']):
            raise ValueError(f'incomplete comparison for {uid}')
        base = {k: data[k] for k in ('unit_id', 'kind', 'case', 'index', 'angle', 'age_myr')}
        old, native = data['original_inputs'], data['native_support']
        geom = old['geometry']
        unit = {**base, 'private_result_sha256': digest(path), 'protocol_sha256': data['protocol_sha256'],
                'projection_source_sha256': native['producer_source_sha256'],
                'projection_receipt_sha256': native['native_receipt_sha256'],
                'projection_file_sha256': native['native_map_sha256'], 'projection_job': native['pbs_job'],
                'native_tracer_kpc3': native['native_tracer_kpc3'], 'projected_tracer_kpc3': native['projected_tracer_kpc3'],
                'xy_uncovered_fraction': geom['uncovered_native_xy_area_fraction'],
                'input_qualifications': '|'.join(data['qualifications']),
                **{k: v for k, v in old.items() if k.endswith('_sha256')}}
        for name, faces in native['boundary_face_counts'].items():
            unit[name + '_boundary_faces_with_any'] = sum(bool(v) for v in faces.values())
            unit[name + '_face_cell_incidents'] = sum(faces.values())
        units.append(unit)
        for arm, fit in data['arms'].items():
            labels = {**base, 'arm': arm}
            coverage.append({**labels, **fit['coverage']})
            annuli.extend({**labels, **row} for row in fit['bins'])
            for continuation in (('flat',) if arm == 'original' else ('flat', 'log_slope')):
                status = fit['status'][continuation]
                rows = fit['scores'].get(continuation, {})
                mask_digest = fit['mask_sha256'].get(continuation)
                if (set(rows) != (set(SIDES) if status == 'ok' else set())
                        or bool(mask_digest) != (status == 'ok')):
                    raise ValueError(f'{uid}/{arm}/{continuation}: score inventory and fit status differ')
                for side in SIDES:
                    scores.append({**labels, 'continuation': continuation, 'side': side, 'status': status,
                                   'mask_sha256': mask_digest,
                                   **rows.get(side, {})})
    out.mkdir(parents=True, exist_ok=True)
    tables = {'scores.csv.gz': scores, 'coverage.csv.gz': coverage, 'radial_support.csv.gz': annuli,
              'input_receipts.csv.gz': units}
    for name, rows in tables.items():
        write_table(out / name, rows)
    manifest = {name: {'sha256': digest(out / name), 'rows': len(rows)} for name, rows in tables.items()}
    (out / 'tables.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')


def fraction(num, den):
    return num / den if den else None


def stats(rows):
    sides = [r for r in rows if r['side'] != 'both']
    ok = [r for r in sides if r['status'] == 'ok']

    def total(k):
        return sum(float(r[k]) for r in ok)

    def med(k):
        values = [float(r[k]) for r in ok if r[k] != '']
        return median(values) if values else None

    return {'sides': len(sides), 'undefined': len(sides) - len(ok),
            'passed': sum(r['screen_passed'] == 'True' for r in ok),
            'nondetections': sum(r['nondetection'] == 'True' for r in ok),
            'aperture_contacts': sum(r['touches_aperture'] == 'True' for r in ok),
            'median_completeness': med('completeness'), 'median_purity_defined': med('purity'),
            'median_volume_ratio': med('inferred_over_native'), 'false_area_kpc2': total('false_area_kpc2'),
            'false_dimmed_over_5pct_kpc2': total('false_dimmed_over_5pct_kpc2'),
            'total_selected_kpc2': total('selected_kpc2'), 'total_target_kpc2': total('truth_kpc2'),
            'total_intersection_kpc2': total('intersection_kpc2'),
            'pooled_completeness': fraction(total('intersection_kpc2'), total('truth_kpc2')),
            'pooled_purity': fraction(total('intersection_kpc2'), total('selected_kpc2')),
            'pooled_volume_ratio': fraction(total('inferred_volume_kpc3'), total('native_lobe_kpc3')),
            'pooled_native_volume_covered': fraction(total('captured_native_kpc3'), total('native_lobe_kpc3'))}


def support(rows):
    def total(k):
        return sum(float(r[k]) for r in rows)

    inner = [float(r['central_extrapolation_kpc']) for r in rows if r['central_extrapolation_kpc']]
    return {'views': len(rows), 'central_gap_views': sum(v > 0 for v in inner),
            'max_central_gap_kpc': max(inner, default=None), 'bracketed_bins': int(total('n_bracketed')),
            'outer_extrapolated_bins': int(total('n_outer_extrapolated')),
            'retained_fraction': fraction(total('retained_area_kpc2'), total('valid_area_kpc2')),
            'retained_thermo_changed_fraction': fraction(total('retained_thermo_changed_kpc2'), total('retained_area_kpc2')),
            'retained_boundary_changed_fraction': fraction(total('retained_boundary_thermo_changed_kpc2'), total('retained_area_kpc2')),
            'unmasked_tracer_fraction': fraction(total('unmasked_tracer_sky_kpc2'), total('tracer_sky_kpc2'))}


def summarise(directory):
    meta = json.loads((directory / 'tables.json').read_text())
    for name, record in meta.items():
        if digest(directory / name) != record['sha256']:
            raise ValueError(f'published table digest differs: {name}')
    scores, coverage = (read_table(directory / name) for name in ('scores.csv.gz', 'coverage.csv.gz'))
    cohort = expected()
    keys = {(uid, arm, cont, side) for uid in cohort for arm in ARMS for side in SIDES
            for cont in (('flat',) if arm == 'original' else ('flat', 'log_slope'))}
    if len(scores) != len(keys) or {(r['unit_id'], r['arm'], r['continuation'], r['side']) for r in scores} != keys:
        raise ValueError('unexpected source comparison score table keys')
    result = {}
    for kind in ('development', 'science', 'initial_null'):
        by_case = result[kind] = {}
        for case in ('all', *CASES):
            subset = [r for r in scores if r['kind'] == kind and (case == 'all' or case == r['case'])]
            if not subset:
                continue
            by_arm = by_case[case] = {}
            for arm in ARMS:
                rows = [r for r in subset if r['arm'] == arm]
                fitting = [r for r in coverage if r['kind'] == kind and r['arm'] == arm and (case == 'all' or case == r['case'])]
                by_arm[arm] = {'support': support(fitting), **{cont: stats([r for r in rows if r['continuation'] == cont])
                              for cont in sorted({r['continuation'] for r in rows})}}
    archived = result['science']['all']['original']['flat']
    if (archived['sides'] != 108 or archived['passed'] or archived['nondetections'] != 15 or archived['aperture_contacts'] != 6
            or abs(archived['false_area_kpc2'] - 55070.6) > 0.05 or abs(archived['false_dimmed_over_5pct_kpc2'] - 9.52) > .01):
        raise ValueError('original science summary differs from published DET-05')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collect', type=Path, help='directory containing completed private per-view results')
    p.add_argument('--assets', default=ASSETS, type=Path)
    args = p.parse_args()
    if args.collect:
        collect(args.collect, args.assets)
    data = summarise(args.assets)
    path = args.assets / 'summary.json'
    if args.collect:
        path.write_text(json.dumps(data, sort_keys=True, indent=2, allow_nan=False) + '\n')
    elif json.loads(path.read_text()) != data:
        raise ValueError('published summary differs from numerical tables')
    for name in ARMS:
        row = data['science']['all'][name]['flat']
        print(f"{name}: {row['passed']}/{row['sides']} science sides, {row['undefined']} undefined, "
              f"{row['nondetections']} empty, {row['false_area_kpc2']:.2f} kpc² exterior")


if __name__ == '__main__':
    main()
