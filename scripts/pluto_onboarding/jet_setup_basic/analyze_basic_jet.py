#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PLUTO_DIR = Path('/home/bwbrook/git/utas-agn/pluto')
BASE = Path('/home/bwbrook/work/pluto-onboarding/jet_setup_basic')
RESULTS = BASE / 'results'
PLOTS = BASE / 'plots'
PLOTS.mkdir(parents=True, exist_ok=True)

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

D = pp.pload.pload(4, w_dir=str(RESULTS) + '/')

rho = np.array(D.rho)
r = np.array(D.x1)
theta = np.array(D.x2)
R, TH = np.meshgrid(r, theta, indexing='ij')
X = R * np.sin(TH)
Z = R * np.cos(TH)
log_rho = np.log10(rho)

fig, ax = plt.subplots(figsize=(7.5, 6.5), constrained_layout=True)
mesh = ax.pcolormesh(X, Z, log_rho, shading='auto', cmap='magma')
ax.set_xlabel('Cylindrical radius (kpc)')
ax.set_ylabel('Axial distance (kpc)')
ax.set_title('Basic 2D spherical jet: log10 density at final output')
ax.set_xlim(0, 30)
ax.set_ylim(-30, 30)
cbar = fig.colorbar(mesh, ax=ax, pad=0.02)
cbar.set_label('log10 density (code units)')
fig.savefig(PLOTS / 'basic_jet_density.png', dpi=200)
plt.close(fig)

mid = rho.shape[1] // 2
axis_rho = rho[:, mid]
fig, ax = plt.subplots(figsize=(7, 4.5), constrained_layout=True)
ax.plot(r, axis_rho, lw=2)
ax.set_xlabel('Radius along jet axis (kpc)')
ax.set_ylabel('Density (code units)')
ax.set_yscale('log')
ax.set_title('Axis density profile at final output')
fig.savefig(PLOTS / 'basic_jet_axis_profile.png', dpi=200)
plt.close(fig)

jet_extent_idx = np.where(axis_rho < 0.5 * np.nanmax(axis_rho))[0]
jet_front_kpc = float(r[jet_extent_idx[-1]]) if len(jet_extent_idx) else float(r[0])

metrics = {
    'final_output_index': 4,
    'radial_cells': int(rho.shape[0]),
    'angular_cells': int(rho.shape[1]),
    'density_min_code': float(np.nanmin(rho)),
    'density_max_code': float(np.nanmax(rho)),
    'jet_front_proxy_kpc': jet_front_kpc,
}

with open(PLOTS / 'basic_jet_metrics.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['metric', 'value'])
    for key, value in metrics.items():
        writer.writerow([key, value])

print('[done] analysis complete')
print(f"saved {PLOTS / 'basic_jet_density.png'}")
print(f"saved {PLOTS / 'basic_jet_axis_profile.png'}")
print(f"saved {PLOTS / 'basic_jet_metrics.csv'}")
