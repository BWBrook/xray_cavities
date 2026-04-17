#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PLUTO_DIR = Path('/home/bwbrook/git/utas-agn/pluto')
BASE = Path('/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep')
RESULTS = BASE / 'results'
PLOTS = BASE / 'plots'
PLOTS.mkdir(parents=True, exist_ok=True)
CASES = [
    ('baseline', 'Baseline'),
    ('higher_power', 'Higher power'),
    ('wider_angle', 'Wider opening angle'),
]

pypluto_src = PLUTO_DIR / 'Tools/pyPLUTO/pyPLUTO'
tmp_dir = Path(tempfile.mkdtemp(prefix='pypluto_patch_'))
patched_pkg = tmp_dir / 'pyPLUTO'
patched_pkg.mkdir()
for src in pypluto_src.glob('*.py'):
    text = src.read_text()
    if src.name == 'pload.py':
        text = text.replace('.fromstring(', '.frombytes(')
    (patched_pkg / src.name).write_text(text)
sys.path.insert(0, str(tmp_dir))

import pyPLUTO as pp  # type: ignore

loaded = {}
metrics_rows = []

fig, axes = plt.subplots(1, 3, figsize=(15, 5.2), constrained_layout=True)
for ax, (case_name, case_label) in zip(axes, CASES):
    D = pp.pload.pload(4, w_dir=str(RESULTS / case_name) + '/')
    rho = np.array(D.rho)
    r = np.array(D.x1)
    theta = np.array(D.x2)
    R, TH = np.meshgrid(r, theta, indexing='ij')
    X = R * np.sin(TH)
    Z = R * np.cos(TH)
    log_rho = np.log10(rho)
    mesh = ax.pcolormesh(X, Z, log_rho, shading='auto', cmap='magma')
    ax.set_title(case_label)
    ax.set_xlim(0, 60)
    ax.set_ylim(-60, 60)
    ax.set_xlabel('Cylindrical radius (kpc)')
    if ax is axes[0]:
        ax.set_ylabel('Axial distance (kpc)')
    mid = rho.shape[1] // 2
    axis_rho = rho[:, mid]
    head_mask = r >= 1.0
    head_peak_idx = np.where(head_mask)[0][np.nanargmax(axis_rho[head_mask])]
    log_axis = np.log10(np.clip(axis_rho, 1e-99, None))
    head_gradient_idx = np.where(head_mask)[0][np.nanargmax(np.abs(np.gradient(log_axis[head_mask], r[head_mask])))]
    metrics_rows.append({
        'case': case_name,
        'label': case_label,
        'radial_cells': int(rho.shape[0]),
        'angular_cells': int(rho.shape[1]),
        'density_min_code': float(np.nanmin(rho)),
        'density_max_code': float(np.nanmax(rho)),
        'head_peak_radius_kpc': float(r[head_peak_idx]),
        'head_gradient_radius_kpc': float(r[head_gradient_idx]),
        'axis_min_density_code': float(np.nanmin(axis_rho)),
    })
    loaded[case_name] = (r, axis_rho)

cbar = fig.colorbar(mesh, ax=axes, pad=0.02)
cbar.set_label('log10 density (code units)')
fig.suptitle('Basic jet parameter sweep: final density structure', y=1.02)
fig.savefig(PLOTS / 'jet_parameter_sweep_density.png', dpi=200, bbox_inches='tight')
plt.close(fig)

fig, ax = plt.subplots(figsize=(7.5, 5), constrained_layout=True)
for case_name, case_label in CASES:
    r, axis_rho = loaded[case_name]
    ax.plot(r, axis_rho, lw=2, label=case_label)
ax.set_xlabel('Radius along jet axis (kpc)')
ax.set_ylabel('Density (code units)')
ax.set_yscale('log')
ax.set_xlim(0, 60)
ax.set_title('Axis density profile comparison')
ax.legend(frameon=False)
fig.savefig(PLOTS / 'jet_parameter_sweep_axis_profile.png', dpi=200)
plt.close(fig)

with open(PLOTS / 'jet_parameter_sweep_metrics.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(metrics_rows[0].keys()))
    writer.writeheader()
    writer.writerows(metrics_rows)

print('[done] analysis complete')
print(f'saved {PLOTS / "jet_parameter_sweep_density.png"}')
print(f'saved {PLOTS / "jet_parameter_sweep_axis_profile.png"}')
print(f'saved {PLOTS / "jet_parameter_sweep_metrics.csv"}')
