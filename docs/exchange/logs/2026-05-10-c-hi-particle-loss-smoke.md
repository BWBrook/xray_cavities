# 2026-05-10 C-HI Particle-Loss Smoke

## Summary

Completed the first particle-loss-aware GRAiLE/XRAiSE runtime smoke for the
aligned `C-HI` 5 Myr target.

This closes the runtime pieces that were still missing after the XRAiSE
grid-thermal smoke:

- staged a compact `plutokore` runtime on `kunanyi`
- used small import shims for `contextlib2`, `hdf5plugin`, and `yt`
- generated the preprocessed `C-HI.particles.hdf5` file Georgia's supplied
  driver expects
- ran the supplied `xraise.py`/`praise(...)` particle-loss path against
  grid output `8`, particle output `503`, and the 1 keV target frequency

## Jobs

Particle HDF5 preprocessing:

- PBS job: `690635.kunanyi-ohpc`
- node: `n001`
- walltime: about `1 min`
- processed HDF5: `129 MB`
- particle IDs: `17516`
- particle times: `550`, spanning `0.0` to `5.4550 Myr`
- compact archive SHA-256:
  `282820847ceb41071cc7199a22eec0ccd5438c91442183095ea09511e24352de`

Particle-loss smoke:

- PBS job: `690636.kunanyi-ohpc`
- node: `n001`
- walltime: about `28 s`
- grid output: `8`
- grid time: `4.9994358508106655 Myr`
- particle output: `503`
- particle time: `4.999435003568512 Myr`
- finite particle emissivity values: `17516`
- positive values: `13144`
- NaNs: `0`
- max: `4.2874063006224175`
- mean: `0.7759846208637153`
- compact archive SHA-256:
  `be405ff8884c24de2a0e61a2b8cb63c9602106f66bd5bfa47d942abda560c89d`

## Outputs

- report: `docs/science/c_hi_particle_loss_smoke_2026-05-10.md`
- PDF: `docs/science/c_hi_particle_loss_smoke_2026-05-10.pdf`
- HDF5 summary assets:
  `docs/science/assets/c_hi_particle_hdf5_smoke_2026-05-10/`
- particle-loss assets:
  `docs/science/assets/c_hi_particle_loss_smoke_2026-05-10/`

The large processed particle HDF5 remains on `kunanyi` scratch:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-05-10-c-hi-particles-hdf5/C-HI.particles.hdf5
```

It is intentionally not tracked in Git.

## Caveat

The supplied `xraise.py` emitted a `NumbaParallelSafetyWarning` inside the
parallel particle loop. The result is adequate for this smoke gate because the
output is finite and the runtime path is proven, but the next productionization
pass should compare single-thread and four-thread output on the same snapshot.

## Next Step

Turn the particle emissivity vector into the first mapped/raytraced radio smoke
for the same `C-HI`, 5 Myr, `0 deg` target, then update the aligned
X-ray/radio/truth/cavity comparison package.
