# 2026-05-10 C-HI XRAiSE Grid Smoke

## Summary

Completed the first XRAiSE grid-thermal X-ray smoke for the aligned `C-HI`
5 Myr, `0 deg` target:

- `data.0008.flt.h5`
- `Timestep_8`
- `4.99943481897884 Myr`

The extraction ran on a `kunanyi` compute node as PBS job
`690624.kunanyi-ohpc` and completed with no stderr output.

## Runtime

The useful `kunanyi` module for this step is:

```bash
module purge
module load Anaconda3/2024.02-1
```

That provides the Python packages needed for the grid-only XRAiSE smoke:
`numpy`, `h5py`, `scipy`, `astropy`, `numba`, `matplotlib`, `yaml`, `pandas`,
and `IPython`.

The staged runtime bundle under `/u/bwbrook/codex_kunanyi/xraise_runtime`
contains:

- supplied `xraise.py`, copied from `env/graile-all.zip`
- supplied `apec_corrections.txt`
- supplied `gaunt_lut_2d.npz`
- the repo adapter `xraise_grid_smoke.py`
- the PBS wrapper `c_hi_xraise_grid_smoke.pbs`

## Outputs

- report: `docs/science/c_hi_xraise_grid_smoke_2026-05-10.md`
- PDF: `docs/science/c_hi_xraise_grid_smoke_2026-05-10.pdf`
- assets: `docs/science/assets/c_hi_xraise_grid_smoke_2026-05-10/`
- compact archive:
  `build/science/kunanyi_stage_2026-05-08/c_hi_xraise_grid_smoke_690624_compact_2026-05-10.tar.gz`
- archive SHA-256:
  `85f36265a1563483a582bb904d69094fffce2811f45493f7c38bf53545c6ca23`

Key scalar values:

- raw pre-correction 1 keV max: `1.4382e6 mJy sr^-1`
- XRAiSE-corrected 1 keV max: `2.8783e6 mJy sr^-1`
- raw map sum: `7.9961e8 mJy sr^-1 pixels`
- corrected map sum: `1.0937e9 mJy sr^-1 pixels`
- correction-ratio range: `1.3273` to `2.4404`

## Interpretation

This closes the grid-thermal part of the XRAiSE smoke. The earlier C bridge
map is still useful as a traceability check, but the X-ray grid map now uses
the supplied Python XRAiSE function plus the supplied APEC and Gaunt tables.

The next runtime gate is particle-loss-aware GRAiLE/XRAiSE. That still needs:

- a `plutokore` runtime on `kunanyi`
- the extra `plutokore` Python dependencies not present in the Anaconda module
  by default, especially `hdf5plugin`, `yt`, and `contextlib2`
- a preprocessed `*.particles.hdf5` product for the current `C-HI` particle
  outputs, because Georgia's supplied driver expects that rather than raw PLUTO
  `particles.*.dbl` files
