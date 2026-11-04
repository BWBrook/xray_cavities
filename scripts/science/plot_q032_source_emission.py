#!/usr/bin/env python3
"""Render source, external and total maps from a completed G-HI/20 diagnostic."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import SymLogNorm
from matplotlib.lines import Line2D
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def draw(maps, *, angle: int, cut: int, convention: str, age: float, output: Path) -> None:
    h, z = maps['horizontal_axis_kpc'], maps['z_axis_kpc']
    ue, ze = maps['horizontal_edges_kpc'], maps['z_edges_kpc']
    rows = []
    for epoch in ('current', 'initial'):
        prefix = f'brightness_{epoch}_{convention}_'
        rows.append([maps[prefix+'C'] + maps[prefix+f'A_v{cut}'],
                     maps[prefix+f'E_v{cut}'], maps[prefix+'whole']])
    rows.append([a-b for a, b in zip(rows[1], rows[0])])
    if any(not np.all(np.isfinite(a)) for row in rows for a in row):
        raise ValueError('cannot render non-finite component maps')
    brightness_max = max(float(np.max(np.abs(a))) for row in rows[:2] for a in row)
    deficit_max = max(float(np.max(np.abs(a))) for a in rows[2])
    norms = []
    for maximum in (brightness_max, brightness_max, deficit_max):
        maximum = max(maximum, np.finfo(float).tiny)
        norms.append(SymLogNorm(linthresh=maximum*1e-4, vmin=-maximum, vmax=maximum, base=10))
    fig, axes = plt.subplots(3, 3, figsize=(12, 12), constrained_layout=True, sharex=True, sharey=True)
    titles = ('Expanding-source diagnostic: C + A', 'Approximately static external: E', 'Total: C + A + E')
    labels = ('Current brightness', 'Same-current-cell initial reference', 'Signed deficit: initial − current')
    outlines = [(maps['tracer_max'] > 1e-3, '#ffffff', 'Tracer sightline'),
                (maps['original_mask_seed_grow_goal045'], '#ffb000', 'Retained seed-and-grow'),
                (maps['original_mask_deficit_threshold_observer_radial_0.05'], '#00cfe8', 'Retained 5% deficit')]
    for ri, row in enumerate(rows):
        for ci, values in enumerate(row):
            ax = axes[ri, ci]
            artist = ax.pcolormesh(ue, ze, values, shading='flat', cmap='RdBu_r', norm=norms[ri], rasterized=True)
            for mask, color, _ in outlines:
                if np.any(mask) and not np.all(mask):
                    ax.contour(h, z, mask, levels=[.5], colors=[color], linewidths=.65)
            ax.set_aspect('equal')
            if ri == 0:
                ax.set_title(titles[ci], fontsize=10)
            if ci == 0:
                ax.set_ylabel(labels[ri]+'\nz (kpc)', fontsize=9)
            if ri == 2:
                ax.set_xlabel('Sky position u (kpc)')
        fig.colorbar(artist, ax=list(axes[ri]), shrink=.8, label='mJy sr⁻¹; signed symmetric-log scale')
    handles = [Line2D([0], [0], color=color if color != '#ffffff' else '#777777', label=label) for _, color, label in outlines]
    fig.legend(handles=handles, loc='outside lower center', ncol=3, fontsize=9)
    fig.suptitle(f'G-HI, {age:.4f} Myr, side-on azimuth {angle}°; speed cut {cut} km/s\n'
                 f'{convention}; raw diagnostic, qualification holds retained\n'
                 'Moving ambient is not proof of shock or jet origin; outlines remain diagnostic comparators', fontsize=11)
    stem = output/f'G-HI_0020_{angle}deg_v{cut}_{convention}'
    fig.savefig(stem.with_suffix('.png'), dpi=160)
    fig.savefig(stem.with_suffix('.pdf'))
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--cuts', type=int, nargs='+', choices=(30, 100, 300), default=[100, 300])
    args = parser.parse_args()
    receipt_path = args.input_dir/'completion.json'
    receipt_hash = sha256(receipt_path)
    receipt = json.loads(receipt_path.read_text())
    if receipt.get('execution_status') != 'completed_GHI20_source_emission_diagnostic':
        raise ValueError('a completed G-HI/20 diagnostic is required')
    inputs = {'completion.json': receipt_hash}
    paths = [args.input_dir/f'G-HI_0020_{angle}deg.npz' for angle in (0, 45, 90)]
    for path in paths:
        inputs[path.name] = sha256(path)
        if inputs[path.name] != receipt['files'][path.name]['sha256']:
            raise ValueError(f'map hash mismatch: {path.name}')
    args.output_dir.mkdir(parents=True, exist_ok=False)
    for angle, path in zip((0, 45, 90), paths):
        with np.load(path, allow_pickle=False) as maps:
            for cut in args.cuts:
                for convention in ('retained_linear', 'clamp_each_coordinate'):
                    draw(maps, angle=angle, cut=cut, convention=convention,
                         age=receipt['actual_time_myr'], output=args.output_dir)
    if sha256(receipt_path) != receipt_hash or any(sha256(path) != inputs[path.name] for path in paths):
        raise ValueError('diagnostic inputs changed during rendering')
    products = {p.name: sha256(p) for p in sorted(args.output_dir.iterdir())}
    (args.output_dir/'render_receipt.json').write_text(json.dumps({
        'status': 'rendered_GHI20_source_emission_diagnostic', 'inputs_sha256': inputs,
        'products_sha256': products, 'renderer_sha256': sha256(Path(__file__)),
        'scientific_qualification': receipt['scientific_qualification'],
        'negative_brightness_policy': 'preserved with signed symmetric-log scales; no clipping',
    }, indent=2)+'\n')


if __name__ == '__main__':
    main()
