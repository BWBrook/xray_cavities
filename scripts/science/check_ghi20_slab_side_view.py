"""Two follow-up checks on the revised G-HI/20 slab result (XR-07).

1. Row totals. Summing a slab image over x leaves, in each z row, the
   emission from |y| <= h integrated over x and y. The archived 90-degree
   projection of the same snapshot (an earlier job, integrated along x and
   resampled to a uniform 0.417-kpc grid in y) gives the same quantity when
   summed over |y| <= h. The comparison tests the y cut of job 884129 on the
   evolved emission row by row. It does not test how the emission is
   distributed along x within a row, and both products use the same
   emissivity code and tables.

2. Coverage. The registered outline's overlap with the lobe is split by
   whether the pixel dimmed by more than 5% against matched time zero and
   by whether the time-zero control outline already selects it.

Neither check rewrites the tables of check_ghi20_midplane_slabs.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from check_ghi20_midplane_slabs import DEPTHS, OUT, outline, write

FIELDS = {
    'current': ('current_{}', 'brightness_current_retained_linear_whole'),
    'initial': ('initial_{}', 'brightness_initial_retained_linear_whole'),
    'current_lobe_cells': ('current_lobe_{}', 'brightness_current_retained_linear_C'),
    'initial_on_current_lobe_cells': ('initial_on_current_lobe_{}', 'brightness_initial_retained_linear_C'),
}


def weights(edges, half, rule):
    lower, upper = edges[:-1], edges[1:]
    if rule == 'exact':
        return np.clip(np.minimum(upper, half) - np.maximum(lower, -half), 0, None)
    if rule == 'one_pixel_wider':
        return np.where((upper > -half) & (lower < half), upper - lower, 0.)
    if rule == 'shifted_one_pixel':
        return np.roll(weights(edges, half, 'exact'), 1)
    raise ValueError(rule)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--projection', type=Path, required=True)
    parser.add_argument('--side-view', type=Path, required=True)
    args = parser.parse_args()

    from skimage.measure import label
    import review_source_excluded_backgrounds as det

    with np.load(args.projection, allow_pickle=False) as data:
        maps = {key: data[key] for key in data.files}
    with np.load(args.side_view, allow_pickle=False) as data:
        side = {key: data[key] for key in ('horizontal_edges_kpc', 'z_edges_kpc', *(pair[1] for pair in FIELDS.values()))}
    if not np.array_equal(side['z_edges_kpc'], maps['z_edges_kpc']):
        raise ValueError('the two views do not share z rows')
    dx, y_edges = np.diff(maps['horizontal_edges_kpc']), side['horizontal_edges_kpc']

    rows = []
    for field, (slab_key, side_key) in FIELDS.items():
        for depth, half in DEPTHS.items():
            slab = (maps[slab_key.format(depth)] * dx[None, :]).sum(axis=1)
            for rule in ('exact', 'one_pixel_wider', 'shifted_one_pixel'):
                if rule != 'exact' and (depth == 'full' or field != 'current'):
                    continue
                other = (side[side_key] * weights(y_edges, half, rule)[None, :]).sum(axis=1)
                used = other > 0
                rows.append({
                    'field': field, 'depth': depth, 'side_view_cut': rule, 'z_rows': int(used.sum()),
                    'total_ratio_minus_one': slab.sum() / other.sum() - 1,
                    'largest_row_ratio_minus_one': np.abs(slab[used] / other[used] - 1).max(),
                    'largest_row_difference_over_largest_row': np.abs(slab - other).max() / other.max()})
    for depth, half in DEPTHS.items():
        if depth == 'full':
            continue
        cut = weights(y_edges, half, 'exact')[None, :]
        current, initial = ((side[FIELDS[name][1]] * cut).sum(axis=1) for name in ('current', 'initial'))
        rows.append({
            'field': 'side_view_current_against_side_view_initial', 'depth': depth, 'side_view_cut': 'exact',
            'z_rows': len(current), 'total_ratio_minus_one': current.sum() / initial.sum() - 1,
            'largest_row_ratio_minus_one': np.abs(current / initial - 1).max(),
            'largest_row_difference_over_largest_row': np.abs(current - initial).max() / initial.max()})
    write('side_view_rows.csv', rows)

    axes = {key: maps[key] for key in det.AXES}
    path = maps['tracer_path_full']
    truth, nothing = path > 0, np.zeros(path.shape, dtype=bool)
    split = []
    for depth in DEPTHS:
        current, initial = maps[f'current_{depth}'], maps[f'initial_{depth}']
        view = det.View(depth, 'science', axes, current, initial, path, nothing, None)
        null = det.View(depth, 'initial_null', axes, initial, initial, path, nothing, None)
        mask = outline(view, view.profiles(current, nothing)[0], 0.05, det, label)[0]
        control = outline(null, null.profiles(initial, nothing)[0], 0.05, det, label)[0]
        dimmed, area, overlap = current < 0.95 * initial, view.area, mask & truth
        lobe = area[truth].sum()
        split.append({
            'depth': depth, 'lobe_kpc2': lobe, 'overlap_kpc2': area[overlap].sum(), 'coverage': area[overlap].sum() / lobe,
            'overlap_dimmed_kpc2': area[overlap & dimmed].sum(), 'overlap_not_dimmed_kpc2': area[overlap & ~dimmed].sum(),
            'coverage_dimmed_only': area[overlap & dimmed].sum() / lobe,
            'overlap_in_control_outline_kpc2': area[overlap & control].sum(),
            'overlap_not_dimmed_in_control_outline_kpc2': area[overlap & ~dimmed & control].sum(),
            'dimmed_on_lobe_kpc2': area[dimmed & truth].sum(),
            'dimmed_on_lobe_missed_kpc2': area[dimmed & truth & ~mask].sum(),
            'lobe_in_control_outline_kpc2': area[truth & control].sum()})
    write('coverage_split.csv', split)

    digest = lambda p: hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
    (OUT / 'side_view.json').write_text(json.dumps({
        'projection_sha256': digest(args.projection), 'side_view_sha256': digest(args.side_view),
        'side_view_pixel_kpc': float(np.diff(y_edges).mean()),
        'side_view_nearest_edge_to_cut_kpc': {name: float(np.abs(np.abs(y_edges) - half).min()) for name, half in DEPTHS.items() if name != 'full'},
        'tables': {name: digest(OUT / name) for name in ('side_view_rows.csv', 'coverage_split.csv')}}, indent=2) + '\n')
    for row in rows:
        print(f"{row['field']:44s}{row['depth']:8s}{row['side_view_cut']:18s}{row['total_ratio_minus_one']:+.2e} {row['largest_row_ratio_minus_one']:.2e}")
    for row in split:
        print({key: (round(value, 4) if isinstance(value, float) else value) for key, value in row.items()})


if __name__ == '__main__':
    main()
