"""Claude's check of the G-HI/20 front-constraint scores (DET-07).

A separate implementation, written after reading the protocol and Codex's
measurement script, so it shares their reading of the rule. It imports
nothing from the project's modules and labels components with scikit-image.
The published orange outline is read straight from the producer's archive.
The smaller refitted outline is rebuilt with the radial detector written for
the DET-06 review. The projected front, tracer and brightness maps are
Codex's archived projections and are taken as given.

Beyond the published rows it measures how far the tracer footprint sits
inside the front edge, what moving the bound inward or outward does, the
sky area between lobe and front, and whether the compression components
outside the dominant one reach beyond its footprint.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from skimage.measure import label

import review_source_excluded_backgrounds as det06

ROOT = Path(__file__).resolve().parents[2]
PUBLISHED = ROOT / 'docs/science/assets/ghi20_front_constraint_2026-11-25'
EARLIER = ROOT / 'docs/science/assets/compressive_front_observer_2026-11-23/front_sightline_overlap.csv'
OUT = ROOT / 'docs/science/assets/ghi20_front_constraint_review_2026-11-25'
FRONTS = {'primary': 'front_path_kpc', 'loose': 'front_path_loose_kpc', 'tight': 'front_path_tight_kpc',
          'wide': 'front_path_wide_kpc'}
ORANGE = 'original_mask_deficit_threshold_observer_radial_0.05'
OFFSETS = (-10., -5., -2., -1., 0., 1., 2., 5., 10., 20.)
AREAS = ('lobe_area_kpc2', 'lobe_outside_front_kpc2', 'false_before_kpc2', 'false_removed_kpc2',
         'false_after_kpc2', 'true_before_kpc2', 'true_lost_kpc2', 'true_after_kpc2')


def digest(mask):
    return hashlib.sha256(np.ascontiguousarray(mask).tobytes()).hexdigest()


def rows_of(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def enclosure(occupied):
    """Count pieces and enclosed empty pixels under four- and eight-neighbour adjacency."""
    record = {}
    for name, occupied_link, sky_link in (('4', 1, 2), ('8', 2, 1)):
        record['components_' + name] = int(label(occupied, connectivity=occupied_link).max())
        sky = label(~occupied, connectivity=sky_link)
        open_sky = np.unique(np.concatenate((sky[0], sky[-1], sky[:, 0], sky[:, -1])))
        record['hole_pixels_' + name] = int((~occupied & ~np.isin(sky, open_sky)).sum())
    record['edge_contact'] = bool(occupied[[0, -1]].any() or occupied[:, [0, -1]].any())
    return record


def edge(mask):
    """Pixels of the mask with a four-neighbour outside it."""
    padded = np.pad(mask, 1)
    return mask & ~(padded[:-2, 1:-1] & padded[2:, 1:-1] & padded[1:-1, :-2] & padded[1:-1, 2:])


def distances(inside, u, z):
    """Signed centre-to-centre distance to the bound: negative inside, positive outside."""
    grid_u, grid_z = np.meshgrid(u, z)
    points = np.column_stack((grid_u.ravel(), grid_z.ravel()))
    flat = inside.ravel()
    rim_in, rim_out = edge(inside).ravel(), edge(~inside).ravel()
    signed = np.empty(flat.size)
    signed[flat] = -cKDTree(points[rim_out]).query(points[flat])[0]
    signed[~flat] = cKDTree(points[rim_in]).query(points[~flat])[0]
    return signed.reshape(inside.shape)


def scores(candidate, truth, inside, area):
    def total(mask):
        return float(area[mask].sum())
    return {'lobe_area_kpc2': total(truth), 'lobe_outside_front_kpc2': total(truth & ~inside),
            'false_before_kpc2': total(candidate & ~truth), 'false_removed_kpc2': total(candidate & ~truth & ~inside),
            'false_after_kpc2': total(candidate & ~truth & inside), 'true_before_kpc2': total(candidate & truth),
            'true_lost_kpc2': total(candidate & truth & ~inside), 'true_after_kpc2': total(candidate & truth & inside)}


def run(args):
    published = {(int(r['view_deg']), r['front'], r['candidate'], r['hemisphere']): r
                 for r in rows_of(PUBLISHED / 'area_scores.csv')}
    geometry = {(int(r['view_deg']), r['front']): r for r in rows_of(PUBLISHED / 'front_geometry.csv')}
    receipt = json.loads((PUBLISHED / 'receipt.json').read_text())
    earlier = {(int(r['view_deg']), r['hemisphere']): r for r in rows_of(EARLIER)
               if r['region'] == 'orange_lateral_excess'}
    sides, bounds, offsets, checks = [], [], [], []
    for angle in (0, 45, 90):
        unit = f'G-HI_0020_{angle}deg'
        with np.load(args.exposed_dir / f'{unit}.npz', allow_pickle=False) as obs, \
                np.load(args.front_dir / f'{unit}.npz', allow_pickle=False) as native:
            axes = {name: obs[name] for name in det06.AXES}
            if any(not np.array_equal(axes[name], native[name]) for name in det06.AXES):
                raise ValueError(f'{unit}: front and image grids differ')
            image, initial, path = obs[det06.IMAGE], obs['brightness_initial_retained_linear_whole'], obs['path_C_kpc']
            orange = obs[ORANGE]
            replaced = image + native['front_initial_brightness'] - native['front_current_brightness']
            fronts = {name: native[key] > 0 for name, key in FRONTS.items()}
            other, boundary = native['other_path_kpc'] > 0, native['boundary_path_kpc'] > 0
        u, ue, z, ze = (axes[name] for name in det06.AXES)
        area = np.outer(np.abs(np.diff(ze)), np.abs(np.diff(ue)))
        truth = path > 0
        view = det06.View(unit, 'development', axes, replaced, initial, path, orange, None)
        refit = view.outline(view.profiles(replaced, np.zeros(image.shape, dtype=bool))[0])
        candidates = {'original_radial': orange, 'replacement_refit_radial': refit}
        bound = receipt['bindings'][unit]
        for name, mask in candidates.items():
            checks.append((f'{unit}/{name}: outline hash', digest(mask) == bound['candidates'][name]['before_mask_sha256']))
        checks.append((f'{unit}: tracer hash', digest(truth) == bound['tracer_footprint_sha256']))
        halves = {'negative_z': z < 0, 'positive_z': z > 0, 'both': np.ones(z.size, dtype=bool)}
        centre = (slice(np.searchsorted(z, 0) - 1, np.searchsorted(z, 0) + 1),
                  slice(np.searchsorted(u, 0) - 1, np.searchsorted(u, 0) + 1))
        for front, inside in fronts.items():
            shape = enclosure(inside)
            ref = geometry[angle, front]
            checks.append((f'{unit}/{front}: interior hash', digest(inside) == ref['inside_sha256']))
            row = {'view_deg': angle, 'front': front, **shape, 'source_inside': bool(inside[centre].all()),
                   'inside_kpc2': float(area[inside].sum()), 'lobe_kpc2': float(area[truth].sum()),
                   'between_lobe_and_front_kpc2': float(area[inside & ~truth].sum()),
                   'purity_if_front_filled': float(area[truth].sum() / area[inside].sum()),
                   'other_components_outside_kpc2': float(area[other & ~inside].sum()),
                   'boundary_components_kpc2': float(area[boundary].sum())}
            signed = distances(inside, u, z)
            for side in ('negative_z', 'positive_z'):
                row['lobe_margin_kpc_' + side] = float(-signed[halves[side]][truth[halves[side]]].max())
            bounds.append(row)
            for name, mask in candidates.items():
                checks.append((f'{unit}/{front}/{name}: clipped hash', digest(mask & inside)
                               == published[angle, front, name, 'both']['clipped_bipolar_mask_sha256']))
                for side, half in halves.items():
                    mine = scores(mask[half], truth[half], inside[half], area[half])
                    theirs = published[angle, front, name, side]
                    gap = max(abs(mine[k] - float(theirs[k])) for k in AREAS)
                    checks.append((f'{unit}/{front}/{name}/{side}: areas', gap < 1e-8))
                    kept = (mask & inside & ~truth)[half]
                    dim = (initial > 0) & (image < 0.95 * initial)
                    extra = {'false_after_dimmed_kpc2': float(area[half][kept & dim[half]].sum())}
                    if front == 'primary' and name == 'original_radial' and side != 'both':
                        old = earlier[angle, side]
                        share = mine['false_removed_kpc2'] / mine['false_before_kpc2']
                        checks.append((f'{unit}/{side}: equals 23 November overlap',
                                       np.isclose(share, 1 - float(old['dominant_area_fraction']), rtol=0, atol=1e-12)
                                       and np.isclose(mine['false_before_kpc2'], float(old['area_kpc2']), rtol=1e-12)))
                    sides.append({'view_deg': angle, 'front': front, 'candidate': name, 'hemisphere': side,
                                  **mine, **extra, 'max_area_difference_kpc2': gap})
                if front != 'primary':
                    continue
                for shift in OFFSETS:
                    moved = signed <= shift
                    for side in ('negative_z', 'positive_z'):
                        half = halves[side]
                        offsets.append({'view_deg': angle, 'candidate': name, 'hemisphere': side, 'offset_kpc': shift,
                                        **scores(mask[half], truth[half], moved[half], area[half])})
    failed = [name for name, passed in checks if not passed]
    if failed:
        raise SystemExit('Disagreements:\n' + '\n'.join(failed))
    OUT.mkdir(parents=True, exist_ok=True)
    for name, table in (('sides.csv', sides), ('bounds.csv', bounds), ('offsets.csv', offsets)):
        with (OUT / name).open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(table[0]), lineterminator='\n')
            writer.writeheader()
            writer.writerows(table)
    print(f'{len(checks)} comparisons agree')


def summarise():
    def number(rows):
        return [{k: (float(v) if k.endswith(('_kpc2', '_kpc')) or k.startswith(('purity', 'lobe_margin')) else v)
                 for k, v in r.items()} for r in rows]
    sides, bounds, offsets = (number(rows_of(OUT / name)) for name in ('sides.csv', 'bounds.csv', 'offsets.csv'))
    primary = [r for r in sides if r['front'] == 'primary' and r['hemisphere'] != 'both']
    summary = {'views': {}, 'offsets': {}, 'bounds': {}}
    for name in ('original_radial', 'replacement_refit_radial'):
        rows = [r for r in primary if r['candidate'] == name]
        pooled = {k: sum(r[k] for r in rows) for k in AREAS + ('false_after_dimmed_kpc2',)}
        per_side = []
        for r in rows:
            after = r['true_after_kpc2'] + r['false_after_kpc2']
            per_side.append({'view_deg': r['view_deg'], 'hemisphere': r['hemisphere'],
                             'share_removed': r['false_removed_kpc2'] / r['false_before_kpc2'],
                             'completeness': r['true_after_kpc2'] / r['lobe_area_kpc2'],
                             'purity_after': r['true_after_kpc2'] / after})
        summary['views'][name] = {
            'pooled': pooled, 'pooled_share_removed': pooled['false_removed_kpc2'] / pooled['false_before_kpc2'],
            'share_of_removed_area_from_0deg': sum(r['false_removed_kpc2'] for r in rows if r['view_deg'] == '0')
            / pooled['false_removed_kpc2'],
            'mean_of_side_shares': float(np.mean([s['share_removed'] for s in per_side])),
            'sides_meeting_75pct_completeness': sum(s['completeness'] >= 0.75 for s in per_side),
            'sides_meeting_95pct_purity_after': sum(s['purity_after'] >= 0.95 for s in per_side),
            'max_completeness': max(s['completeness'] for s in per_side), 'sides': per_side}
        for shift in OFFSETS:
            rows = [r for r in offsets if r['candidate'] == name and r['offset_kpc'] == shift]
            total = {k: sum(r[k] for r in rows) for k in AREAS}
            summary['offsets'].setdefault(name, {})[str(shift)] = {
                'false_left_kpc2': total['false_after_kpc2'], 'true_lost_kpc2': total['true_lost_kpc2'],
                'share_false_removed': total['false_removed_kpc2'] / total['false_before_kpc2'],
                'share_selected_lobe_lost': total['true_lost_kpc2'] / total['true_before_kpc2'],
                'lobe_outside_bound_kpc2': total['lobe_outside_front_kpc2'],
                'purity': total['true_after_kpc2'] / (total['true_after_kpc2'] + total['false_after_kpc2'])}
    for r in bounds:
        if r['front'] == 'primary':
            summary['bounds'][r['view_deg']] = {k: r[k] for k in (
                'inside_kpc2', 'lobe_kpc2', 'between_lobe_and_front_kpc2', 'purity_if_front_filled',
                'other_components_outside_kpc2', 'boundary_components_kpc2', 'lobe_margin_kpc_negative_z',
                'lobe_margin_kpc_positive_z', 'hole_pixels_4', 'hole_pixels_8', 'components_4', 'components_8')}
    summary['all_fronts'] = {k: [min(r[k] for r in bounds), max(r[k] for r in bounds)] for k in (
        'other_components_outside_kpc2', 'boundary_components_kpc2', 'lobe_margin_kpc_negative_z',
        'lobe_margin_kpc_positive_z', 'purity_if_front_filled')}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exposed-dir', type=Path, help='G-HI/20 emission maps')
    parser.add_argument('--front-dir', type=Path, help='G-HI/20 projected front maps')
    arguments = parser.parse_args()
    if arguments.exposed_dir and arguments.front_dir:
        run(arguments)
    print(json.dumps(summarise(), indent=1))
