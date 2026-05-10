# 2026-05-10 C-HI Particle Radio Smoke

## Summary

Completed the first particle-loss-aware 150 MHz radio/lobe smoke for the aligned
`C-HI` 5 Myr, `0 deg` target.

The run used the already staged `plutokore` plus supplied `xraise.py` runtime on
`kunanyi`, recomputed the PRAiSE full-loss factor at `150 MHz`, attached it to
the lossless synchrotron emissivity expression, and projected the selected
particles into an `x-z` map.

## Job

- PBS job: `690641.kunanyi-ohpc`
- node: `n001`
- walltime: about `33 s`
- grid output: `8`
- grid time: `4.9994358508106655 Myr`
- particle output: `503`
- particle time: `4.999435003568512 Myr`
- selected particles: `16054`
- map shape: `220 x 180`
- lossy 150 MHz map max: `3.6847e15 mJy sr^-1`
- lossy 150 MHz map sum: `2.1212e17 mJy sr^-1 pixels`
- bipolar lossy luminosity proxy: `6.3450e27 W Hz^-1`
- archive SHA-256:
  `57f6a572218a03ef040e3376be5652df75396400cd633ffb3c0fc87e264c274e`

## Outputs

- report: `docs/science/c_hi_particle_radio_smoke_2026-05-10.md`
- PDF: `docs/science/c_hi_particle_radio_smoke_2026-05-10.pdf`
- assets: `docs/science/assets/c_hi_particle_radio_smoke_2026-05-10/`
- script: `scripts/science/xraise_particle_radio_smoke.py`
- plotting helper: `scripts/science/plot_particle_radio_smoke.py`
- PBS wrapper: `scripts/kunanyi/c_hi_particle_radio_smoke.pbs`

## Caveat

The output is a particle-binned smoke product with a volume proxy derived from
the Level 2 tracer-mask side volumes. It is suitable as a gate and scale check,
but the final radio product should move to the full grid loss-kernel/raytrace
workflow and then be beam-convolved.

The supplied `xraise.py` still emits the same `NumbaParallelSafetyWarning`.
Before productionizing this lane, run a deterministic check comparing
`NUMBA_NUM_THREADS=1` and `4`.

## Next Step

Build an aligned one-page comparison package for the 5 Myr target, then run the
deterministic particle-loss/radio cross-check before using the lane for longer
snapshots.
