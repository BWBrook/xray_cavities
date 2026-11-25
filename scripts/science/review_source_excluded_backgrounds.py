"""Independent review of the source-excluded background comparison (DET-06).

The radial fit, support rule, both inward continuations, 5% deficit
outline and side areas are implemented separately here. Nothing is
imported from the project's detector modules, and component labelling uses
scikit-image, not SciPy. It was written after reading the protocol, the
original detector and Codex's fitting module, so it shares their reading of
the rules. The tracer and speed sky masks are Codex's native projections
and are taken as given.

Adds, for every view and fit, the split of gained, lost and false area at
the first directly supported radius, the share of each outline that is
dimmer than the same pixels at time zero, and each continuation's central
background against the time-zero radial profile.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from skimage.measure import label

ROOT = Path(__file__).resolve().parents[2]
SEAL = ROOT / 'docs/science/assets/xray_prediction_seal_2026-11-23/seal.json'
PUBLIC = ROOT / 'docs/science/assets/source_excluded_backgrounds_2026-11-25/scores.csv.gz'
OUT = ROOT / 'docs/science/assets/source_excluded_review_2026-11-25'
IMAGE = 'brightness_current_retained_linear_whole'
BASELINE = 'observer_refit__deficit_threshold_observer_radial_0.05__retained_linear__v0'
AXES = ('horizontal_axis_kpc', 'horizontal_edges_kpc', 'z_axis_kpc', 'z_edges_kpc')
FIT_KPC, SEARCH_KPC, BIN_KPC, SIGMA_BINS, THRESHOLD, MIN_AREA = 180., 120., 5., 2., 0.05, 25.
ARMS = {'tracer': 'tracer_footprint', 'speed_30': 'speed_ge_30', 'speed_100': 'speed_ge_100',
        'speed_300': 'speed_ge_300'}


def centre_widths(axis):
    edges = np.concatenate(([axis[0] - (axis[1] - axis[0]) / 2], (axis[:-1] + axis[1:]) / 2,
                            [axis[-1] + (axis[-1] - axis[-2]) / 2]))
    return np.abs(np.diff(edges))


def smooth(profile):
    radius = int(4 * SIGMA_BINS + 0.5)
    kernel = np.exp(-0.5 * (np.arange(-radius, radius + 1) / SIGMA_BINS) ** 2)
    return np.convolve(np.pad(profile, radius, mode='edge'), kernel / kernel.sum(), mode='valid')


class View:
    def __init__(self, unit, kind, axes, image, initial, path, archived, native):
        self.unit, self.kind, self.image, self.initial, self.archived = unit, kind, image, initial, archived
        u, ue, z, ze = (np.asarray(axes[name], dtype=float) for name in AXES)
        self.z = z
        self.area = np.outer(np.abs(np.diff(ze)), np.abs(np.diff(ue)))
        self.filter_area = np.outer(centre_widths(z), centre_widths(u))
        self.revolved = np.outer(np.abs(np.diff(ze)), np.pi / 2 * np.abs(np.diff(ue * np.abs(ue))))
        self.radius = np.hypot(u[None, :], z[:, None])
        self.fit_region = self.radius <= FIT_KPC
        self.search = self.radius <= SEARCH_KPC
        self.positive = self.fit_region & np.isfinite(image) & (image > 0)
        self.bins = int(self.radius[self.positive].max() // BIN_KPC) + 1
        self.centres = BIN_KPC * (np.arange(self.bins) + 0.5)
        self.ring = (self.radius // BIN_KPC).astype(int)
        angle = np.mod(np.arctan2(z[:, None], u[None, :]), 2 * np.pi)
        self.sector = np.minimum((angle / (np.pi / 6)).astype(int), 11)
        self.truth = path > 0
        self.path = path
        self.native = native
        self.dimmed = (initial > 0) & (image < 0.95 * initial)
        self.sides = {'negative_z': np.broadcast_to(z[:, None] < 0, image.shape),
                      'positive_z': np.broadcast_to(z[:, None] > 0, image.shape)}

    def medians(self, image, excluded):
        positive = self.fit_region & np.isfinite(image) & (image > 0)
        measured = np.full(self.bins, np.nan)
        for index in range(self.bins):
            ring = positive & (self.ring == index)
            kept = ring & ~excluded
            need_pixels = min(8, int(ring.sum()))
            need_sectors = min(3, len(np.unique(self.sector[ring])))
            if kept.any() and kept.sum() >= need_pixels and len(np.unique(self.sector[kept])) >= need_sectors:
                measured[index] = np.median(image[kept])
        return measured

    def profiles(self, image, excluded):
        """Return the flat and log-slope smoothed profiles and the first supported bin."""
        measured = self.medians(image, excluded)
        have = np.flatnonzero(np.isfinite(measured))
        if have.size == 0 or (have.size == 1 and excluded[self.positive].any()):
            return None, None, None
        filled = np.interp(self.centres, self.centres[have], measured[have])
        first = int(have[0])
        steep = filled.copy()
        if first > 0:
            anchors = have[:3]
            slope = np.polyfit(self.centres[anchors], np.log(measured[anchors]), 1)[0]
            steep[:first] = measured[first] * np.exp(slope * (self.centres[:first] - self.centres[first]))
        return smooth(filled), smooth(steep), first

    def outline(self, profile):
        background = np.interp(np.minimum(self.radius, self.centres[-1]), self.centres, profile)
        with np.errstate(invalid='ignore', divide='ignore'):
            deficit = (background - self.image) / background
        candidate = self.search & self.fit_region & np.isfinite(deficit) & (background > 0) & (deficit > THRESHOLD)
        mask = np.zeros(self.image.shape, dtype=bool)
        for half in self.sides.values():
            labels = label(candidate & half, connectivity=2)
            areas = np.bincount(labels.ravel(), weights=self.filter_area.ravel())
            keep = np.flatnonzero(areas >= MIN_AREA)
            mask |= np.isin(labels, keep[keep > 0])
        return mask

    def score(self, mask, first):
        gap = self.ring < (first or 0)
        rows = {}
        for side, half in self.sides.items():
            def area(region):
                return float(self.area[region & half].sum())
            overlap, false = mask & self.truth, mask & ~self.truth
            rows[side] = {
                'selected_kpc2': area(mask), 'truth_kpc2': area(self.truth), 'intersection_kpc2': area(overlap),
                'false_area_kpc2': area(false), 'inferred_volume_kpc3': float(self.revolved[mask & half].sum()),
                'captured_native_kpc3': float((self.area * self.path)[overlap & half].sum()),
                'lost_inside_gap_kpc2': area(self.archived & self.truth & ~mask & gap),
                'lost_outside_gap_kpc2': area(self.archived & self.truth & ~mask & ~gap),
                'gained_inside_gap_kpc2': area(overlap & ~self.archived & gap),
                'gained_outside_gap_kpc2': area(overlap & ~self.archived & ~gap),
                'false_inside_gap_kpc2': area(false & gap), 'false_outside_gap_kpc2': area(false & ~gap),
                'intersection_dimmed_kpc2': area(overlap & self.dimmed),
                'false_dimmed_kpc2': area(false & self.dimmed),
                'truth_inside_gap_kpc2': area(self.truth & gap),
                'truth_dimmed_kpc2': area(self.truth & self.dimmed),
                'truth_in_search_kpc2': area(self.truth & self.search),
                'truth_dimmed_in_search_kpc2': area(self.truth & self.dimmed & self.search),
                'native_kpc3': float((self.area * self.path)[self.truth & half].sum()),
                'native_dimmed_kpc3': float((self.area * self.path)[self.truth & self.dimmed & half].sum()),
                **{f'truth_dimmed_over_{int(100 * cut)}pct_kpc2':
                   area(self.truth & (self.initial > 0) & (self.image < (1 - cut) * self.initial))
                   for cut in (0., 0.02, 0.10)}}
        return rows


def load_views(args):
    seal = json.loads(SEAL.read_text())
    for angle in (0, 45, 90):
        unit = f'G-HI_0020_{angle}deg'
        with np.load(args.exposed_dir / f'{unit}.npz', allow_pickle=False) as data, \
                np.load(args.native_root / 'G-HI_0020' / f'{unit}.npz', allow_pickle=False) as native:
            if any(not np.array_equal(data[name], native[name]) for name in AXES):
                raise ValueError(f'{unit}: native mask grid differs from the image')
            yield View(unit, 'development', {name: data[name] for name in AXES}, data[IMAGE],
                       data['brightness_initial_retained_linear_whole'], data['path_C_kpc'],
                       data['mask_retained_linear_v100_deficit_threshold_observer_radial_0.05_exact_projection_refit'],
                       {name: native[key] for name, key in ARMS.items()})
    for unit in seal['units']:
        name, tag = unit['unit_id'], f'{unit["case"]}_{unit["snapshot_index"]:04d}'
        with np.load(args.extract / 'map_inputs' / unit['file'], allow_pickle=False) as data, \
                np.load(args.extract / 'map_inputs' / f'{unit["case"]}_0000_{unit["view_deg"]}deg.npz',
                        allow_pickle=False) as start, \
                np.load(args.extract / 'predictions' / unit['file'], allow_pickle=False) as masks, \
                np.load(args.native_root / tag / f'{name}.npz', allow_pickle=False) as native:
            axes = {key: data[key] for key in AXES}
            if any(not np.array_equal(axes[key], other[key]) for key in AXES for other in (start, masks, native)):
                raise ValueError(f'{name}: grids differ between inputs')
            if unit['kind'] == 'science':
                with np.load(args.truth_dir / f'{name}.truth.npz', allow_pickle=False) as target:
                    path = np.asarray(target['path_C_kpc'], dtype=float)
                if not np.array_equal(native['tracer_footprint'], path > 0):
                    raise ValueError(f'{name}: native tracer footprint differs from the scoring raster')
            else:
                path = np.zeros(data[IMAGE].shape)
            yield View(name, unit['kind'], axes, data[IMAGE], start[IMAGE], path, masks[BASELINE].astype(bool),
                       {key: native[value] for key, value in ARMS.items()})


def run(args):
    with gzip.open(PUBLIC, 'rt', newline='') as handle:
        public = {(row['unit_id'], row['arm'], row['continuation'], row['side']): row for row in csv.DictReader(handle)}
    sides, views = [], []
    for view in load_views(args):
        flat, _, _ = view.profiles(view.image, np.zeros(view.image.shape, dtype=bool))
        start, _, _ = view.profiles(view.initial, np.zeros(view.image.shape, dtype=bool))
        original = view.outline(flat)
        replayed = bool(np.array_equal(original, view.archived))
        ring_area = np.bincount(view.ring[view.positive], weights=view.area[view.positive], minlength=view.bins)
        fits = {'original': {'flat': (original, 0)}}
        for arm, excluded in view.native.items():
            constant, steep, first = view.profiles(view.image, excluded)
            entry = {'unit_id': view.unit, 'kind': view.kind, 'arm': arm, 'original_replayed': replayed,
                     'defined': constant is not None}
            fits[arm] = {}
            if constant is not None:
                weight = ring_area[:first]
                entry.update(first_direct_inner_kpc=BIN_KPC * first,
                             excluded_fraction_of_fit_area=float(view.area[view.positive & excluded].sum()
                                                                 / view.area[view.positive].sum()))
                for name, profile in (('flat', constant), ('log_slope', steep), ('original', flat)):
                    entry[f'{name}_over_time_zero_centre'] = float(profile[0] / start[0])
                    entry[f'{name}_over_time_zero_gap_mean'] = (
                        float(np.average(profile[:first] / start[:first], weights=weight)) if first else None)
                fits[arm] = {'flat': (view.outline(constant), first), 'log_slope': (view.outline(steep), first)}
            views.append(entry)
        for arm, models in fits.items():
            for continuation, (mask, first) in models.items():
                digest = hashlib.sha256(mask.tobytes(order='C')).hexdigest()
                for side, metrics in view.score(mask, first).items():
                    reference = public[view.unit, arm, continuation, side]
                    agree = reference['mask_sha256'] == digest and all(
                        np.isclose(float(reference[key]), metrics[key], rtol=1e-9, atol=1e-6)
                        for key in ('selected_kpc2', 'truth_kpc2', 'intersection_kpc2', 'false_area_kpc2',
                                    'inferred_volume_kpc3', 'captured_native_kpc3'))
                    sides.append({'unit_id': view.unit, 'kind': view.kind, 'arm': arm, 'continuation': continuation,
                                  'side': side, 'first_direct_inner_kpc': BIN_KPC * first, 'mask_sha256': digest,
                                  'mask_matches_public': reference['mask_sha256'] == digest,
                                  'areas_and_volumes_match_public': bool(agree), **metrics})
        print(view.unit, replayed, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    for name, rows in (('sides.csv.gz', sides), ('fits.csv', views)):
        fields = list(dict.fromkeys(key for row in rows for key in row))
        opener = gzip.open if name.endswith('.gz') else open
        with opener(OUT / name, 'wt', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def summarise():
    """Reduce the two tables to the figures quoted in the review. Needs only the committed tables."""
    import pandas as pd
    sides = pd.read_csv(OUT / 'sides.csv.gz')
    fits = pd.read_csv(OUT / 'fits.csv')
    science = sides[sides.kind == 'science'].assign(case=lambda d: d.unit_id.str[:4])
    science = science.assign(completeness=science.intersection_kpc2 / science.truth_kpc2)
    index = ['unit_id', 'side']

    def arm(name, continuation='flat'):
        return science[(science.arm == name) & (science.continuation == continuation)].set_index(index)

    original = arm('original')
    table = {}
    for name, continuation in (('original', 'flat'), ('tracer', 'flat'), ('tracer', 'log_slope'),
                               ('speed_100', 'flat'), ('speed_100', 'log_slope')):
        rows = arm(name, continuation)
        change = rows.completeness - original.completeness
        table[f'{name}/{continuation}'] = {
            'median_completeness': float(rows.completeness.median()),
            'best_completeness': float(rows.completeness.max()),
            'sides_at_or_above_75pct': int((rows.completeness >= 0.75).sum()),
            'lobe_area_kpc2': float(rows.intersection_kpc2.sum()),
            'false_area_kpc2': float(rows.false_area_kpc2.sum()),
            'pooled_purity': float(rows.intersection_kpc2.sum() / rows.selected_kpc2.sum()),
            'paired_median_completeness_change': float(change.median()),
            'sides_up_down_by_half_point': [int((change > 0.005).sum()), int((change < -0.005).sum())],
            'paired_median_change_by_case': change.groupby(rows.case).median().to_dict(),
            'lobe_area_lost_inside_unsupported_centre_kpc2': float(rows.lost_inside_gap_kpc2.sum()),
            'lobe_area_lost_outside_kpc2': float(rows.lost_outside_gap_kpc2.sum()),
            'false_area_inside_unsupported_centre_kpc2': float(rows.false_inside_gap_kpc2.sum()),
            'share_of_recovered_lobe_area_dimmed_over_5pct': float(
                rows.intersection_dimmed_kpc2.sum() / rows.intersection_kpc2.sum()),
            'sides_recovering_more_than_the_dimmed_lobe_area': int(
                (rows.intersection_kpc2 > rows.truth_dimmed_kpc2 + 1e-6).sum())}
    flat, steep = arm('speed_100'), arm('speed_100', 'log_slope')
    gap = flat.first_direct_inner_kpc > 0
    added = steep.intersection_kpc2 - flat.intersection_kpc2
    added_dimmed = steep.intersection_dimmed_kpc2 - flat.intersection_dimmed_kpc2
    dimmed = original.truth_dimmed_kpc2 / original.truth_kpc2
    ceiling = {
        'pooled_share_of_lobe_area_dimmed_over_5pct': float(original.truth_dimmed_kpc2.sum() / original.truth_kpc2.sum()),
        'median_side': float(dimmed.median()), 'best_side': float(dimmed.max()),
        'sides_at_or_above_75pct': int((dimmed >= 0.75).sum()),
        'by_case_median_min_max': {case: [float(v.median()), float(v.min()), float(v.max())]
                                   for case, v in dimmed.groupby(original.case)},
        'median_side_within_search_aperture': float(
            (original.truth_dimmed_in_search_kpc2 / original.truth_in_search_kpc2).median()),
        'pooled_share_of_lobe_volume_on_dimmed_sightlines': float(
            original.native_dimmed_kpc3.sum() / original.native_kpc3.sum()),
        'pooled_share_by_dimming_cut_pct': {
            str(cut): float(original[f'truth_dimmed_over_{cut}pct_kpc2'].sum() / original.truth_kpc2.sum())
            for cut in (0, 2, 10)},
        'best_side_by_dimming_cut_pct': {
            str(cut): float((original[f'truth_dimmed_over_{cut}pct_kpc2'] / original.truth_kpc2).max())
            for cut in (0, 2, 10)}}
    centre = fits[(fits.kind == 'science') & (fits.first_direct_inner_kpc > 0)]
    columns = [f'{name}_over_time_zero_{where}' for name in ('flat', 'log_slope', 'original')
               for where in ('centre', 'gap_mean')]
    profile = {name: {column: [float(rows[column].median()), float(rows[column].min()), float(rows[column].max())]
                      for column in columns} | {'views': len(rows),
                                                'largest_unsupported_radius_kpc': float(rows.first_direct_inner_kpc.max())}
               for name, rows in centre[centre.arm.isin(['tracer', 'speed_100'])].groupby('arm')}
    summary = {
        'reproduction': {
            'views': int(fits.unit_id.nunique()), 'original_outlines_replayed': int(
                fits.drop_duplicates('unit_id').original_replayed.sum()),
            'outlines_compared': int(len(sides) // 2), 'outlines_equal_to_public_hash': int(sides.mask_matches_public.sum() // 2),
            'side_rows_with_equal_areas_and_volumes': int(sides.areas_and_volumes_match_public.sum()),
            'side_rows': len(sides), 'views_without_a_30_km_s_fit': int((~fits[fits.arm == 'speed_30'].defined).sum())},
        'science_sides': table,
        'speed_100_unsupported_centre': {
            'sides_with_gap': int(gap.sum()), 'sides_without_gap': int((~gap).sum()),
            'median_completeness_original_flat_slope_with_gap': [
                float(rows.completeness[gap].median()) for rows in (original, flat, steep)],
            'median_completeness_original_flat_slope_without_gap': [
                float(rows.completeness[~gap].median()) for rows in (original, flat, steep)],
            'lobe_area_added_by_slope_kpc2': float(added.sum()),
            'share_of_added_area_dimmed_over_5pct': float(added_dimmed.sum() / added.sum()),
            'share_of_added_area_dimmed_by_case': (added_dimmed.groupby(flat.case).sum()
                                                   / added.groupby(flat.case).sum()).dropna().to_dict()},
        'lobe_area_dimmer_than_time_zero': ceiling,
        'central_background_over_time_zero_median_min_max': profile}
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2, sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--extract', type=Path, help='extracted prediction archive')
    parser.add_argument('--truth-dir', type=Path, help='directory of <unit>.truth.npz')
    parser.add_argument('--native-root', type=Path, help='native tracer and speed sky masks')
    parser.add_argument('--exposed-dir', type=Path, help='G-HI/20 emission maps')
    args = parser.parse_args()
    paths = (args.extract, args.truth_dir, args.native_root, args.exposed_dir)
    if any(paths):
        if not all(paths):
            parser.error('refitting needs all four private inputs; give none to summarise the committed tables')
        run(args)
    summarise()


if __name__ == '__main__':
    main()
