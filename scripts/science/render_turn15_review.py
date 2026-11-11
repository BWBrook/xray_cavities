"""Render reviewed native-energy and G-HI filling comparisons from compact CSVs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

CASES = ('C-HI', 'C-LO', 'G-HI', 'G-LO')
METHODS = ('seed_grow_goal045', 'deficit_threshold_observer_radial_0.05')


def rows(path):
    with path.open() as handle:
        return list(csv.DictReader(handle))


def numbers(records, field):
    return np.array([float(r[field]) if r[field] else np.nan for r in records])


def save(fig, destination):
    fig.savefig(destination.with_suffix('.png'), dpi=160, bbox_inches='tight')
    fig.savefig(destination.with_suffix('.pdf'), bbox_inches='tight')
    plt.close(fig)


def histories(budgets, output):
    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
    for ax, case in zip(axes.flat, CASES):
        data = rows(budgets/case/'measurements.csv')
        for speed, colour in ((100, '#0072b2'), (300, '#d55e00')):
            selected = [r for r in data if int(r['speed_threshold_km_s']) == speed]
            ax.plot(numbers(selected, 'actual_time_myr'), numbers(selected, 'all_total_over_injected'),
                    color=colour, lw=1.8, label=f'Stored change, R{speed}')
        selected = [r for r in data if int(r['speed_threshold_km_s']) == 100]
        age = numbers(selected, 'actual_time_myr')
        for alpha, style, colour in (('2.5', ':', '#777777'), ('4', '--', '#111111')):
            ax.plot(age, numbers(selected, f'native_enthalpy_{alpha}_over_injected'),
                    style, color=colour, lw=1.8, label=f'Global native lobe {alpha}pV')
        conflict = [float(r['actual_time_myr']) for r in selected if 'boundary_safe_box_conflict' in r['measurement_hold_codes']]
        truncated = [float(r['actual_time_myr']) for r in selected if r['domain_geometry_status'] == 'domain_truncated_spherical_cell_selection']
        if conflict:
            ax.axvspan(min(conflict), 50, color='#aaaaaa', alpha=.15)
        if truncated:
            ax.axvspan(min(truncated), 50, facecolor='none', edgecolor='#888888', hatch='///', lw=0)
        ax.axhline(1, color='#777777', lw=.8)
        ax.set(title=case, xlim=(0, 50), ylim=(0, 2))
        ax.grid(alpha=.2)
    for ax in axes[:, 0]:
        ax.set_ylabel('Ratio to labelled bipolar input')
    for ax in axes[-1]:
        ax.set_xlabel('Actual simulation age (Myr)')
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=2, bbox_to_anchor=(.5, .055), frameon=False)
    fig.suptitle('Native lobe pressure proxies and spherical stored-energy changes', fontsize=14)
    fig.text(.5, .012, 'Grey: candidate inset-box conflict; hatching: domain-truncated selection.\n'
             'Earlier points are not certified boundary-free. Moving-aperture storage is not energy closure.',
             ha='center', fontsize=9)
    fig.subplots_adjust(bottom=.22, top=.93, hspace=.18)
    save(fig, output/'four_case_energy_histories')


def filling(attribution_path, filling_path, output):
    f = rows(filling_path)
    a = rows(attribution_path)
    keys = [(method, angle) for method in METHODS for angle in (0, 45, 90)]
    fs, attrs = [], []
    for method, angle in keys:
        fr = [r for r in f if r['method'] == method and int(r['view_deg']) == angle
              and r['solid'] == 'pooled_Wplus_Wminus' and r['hemisphere'] == 'bipolar_total']
        ar = [r for r in a if r['method'] == method and int(r['view_deg']) == angle
              and r['correction'] == 'retained_linear' and r['velocity_cut_km_s'] == '100'
              and r['hemisphere'] == 'bipolar_total']
        if len(fr) != 1 or len(ar) != 1:
            raise ValueError('missing or duplicate reviewed bipolar comparison')
        fs.append(fr[0]); attrs.append(ar[0])
    angles = [f'{angle}°' for _, angle in keys]
    labels = [f'{angle}°\n' + ('Seed/grow' if method == METHODS[0] else '5% deficit') for method, angle in keys]
    x = np.arange(len(keys))
    fig = plt.figure(figsize=(12, 9))
    grid = fig.add_gridspec(2, 2, hspace=.42, height_ratios=(1, 1.15))
    ax = fig.add_subplot(grid[0, 0])
    for offset, field, label, colour in ((-.24, 'volume_kpc3_share', 'Volume', '#0072b2'),
                                       (0, 'mass_g_share', 'Mass', '#d55e00'),
                                       (.24, 'pressure_integral_erg_share', 'Pressure integral', '#009e73')):
        ax.bar(x+offset, numbers(fs, field), width=.23, label=label, color=colour)
    ax.set(xticks=x, xticklabels=angles, ylim=(0, 1.18), ylabel='Current lobe share',
           title='Native filling of the reconstructed solids')
    ax.legend(fontsize=8, loc='upper center', ncol=3)
    ax.text(1, -.14, 'Seed/grow', ha='center', transform=ax.get_xaxis_transform())
    ax.text(4, -.14, '5% deficit', ha='center', transform=ax.get_xaxis_transform())
    ax = fig.add_subplot(grid[0, 1])
    values = 100*numbers(attrs, 'cocoon_brightness_share')
    ax.bar(x, values, color='#0072b2')
    for i, value in enumerate(values):
        ax.text(i, value+.05, f'{value:.2f}%', ha='center', fontsize=8)
    ax.set(xticks=x, xticklabels=angles, ylim=(0, max(values)*1.3),
           ylabel='Lobe share of sightline brightness (%)', title='Full line of sight through the observed mask')
    ax.text(1, -.14, 'Seed/grow', ha='center', transform=ax.get_xaxis_transform())
    ax.text(4, -.14, '5% deficit', ha='center', transform=ax.get_xaxis_transform())
    ax = fig.add_subplot(grid[1, :])
    positive = np.zeros(len(keys)); negative = np.zeros(len(keys))
    for field, label, colour in (('cocoon_deficit_integral', 'Lobe', '#0072b2'),
                                 ('moving_ambient_deficit_integral', 'Ambient ≥100 km/s', '#d55e00'),
                                 ('external_deficit_integral', 'Ambient <100 km/s', '#009e73'),
                                 ('background_difference_integral', 'Fitted background − initial reference', '#cc79a7')):
        values = numbers(attrs, field)/numbers(attrs, 'observed_deficit_integral')
        ax.bar(x, values, bottom=np.where(values >= 0, positive, negative), label=label, color=colour)
        positive += np.maximum(values, 0); negative += np.minimum(values, 0)
    if not np.allclose(positive+negative, 1, rtol=1e-10, atol=1e-10):
        raise ValueError('signed deficit contributions do not sum to the observed deficit')
    ax.axhline(1, color='#333333', ls='--', lw=1)
    ax.axhline(0, color='#777777', lw=.7)
    ax.set(xticks=x, xticklabels=labels, ylabel='Contribution / observed deficit',
           title='Signed deficit attribution: negative terms reduce the observed deficit')
    ax.legend(loc='upper left', bbox_to_anchor=(0, -.17), ncol=2, fontsize=9, frameon=False)
    fig.suptitle('G-HI at 20 Myr: bipolar filling, brightness and signed deficit', fontsize=13)
    fig.text(.5, .012, 'Native filling pools W+ and W−; brightness/deficit use the observed mask and full sightline.\n'
             'Angles are side-on azimuths. Retained-linear correction, 100-km/s partition; diagnostic masks, no shock attribution.',
             ha='center', fontsize=9)
    fig.subplots_adjust(top=.91, bottom=.20)
    save(fig, output/'G-HI_filling_and_deficit')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--budgets', type=Path, required=True)
    p.add_argument('--filling', type=Path, required=True)
    p.add_argument('--attribution', type=Path, required=True)
    p.add_argument('--output-dir', type=Path, required=True)
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    histories(args.budgets, args.output_dir)
    filling(args.attribution, args.filling, args.output_dir)
    inputs = {f'{case}/measurements.csv': hashlib.sha256((args.budgets/case/'measurements.csv').read_bytes()).hexdigest() for case in CASES}
    inputs.update({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.filling, args.attribution)})
    products = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in args.output_dir.iterdir()}
    (args.output_dir/'render_receipt.json').write_text(json.dumps({'inputs_sha256': inputs, 'products_sha256': products,
        'renderer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2)+'\n')


if __name__ == '__main__':
    main()
