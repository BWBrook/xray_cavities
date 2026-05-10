# 2026-05-10 C-HI Aligned Comparison And Determinism Gate

## Summary

The aligned `C-HI`, 5 Myr, `0 deg` smoke products have been folded into a
compact comparison package, and the particle-radio lane has passed a
`NUMBA_NUM_THREADS=1` versus `4` deterministic rerun.

## Inputs

Aligned target:

- case: `C-HI`
- grid output: `data.0008.flt.h5`
- grid time: about `4.9994 Myr`
- view: `0 deg`
- truth/cavity threshold: `tracer > 5e-3`
- X-ray product: XRAiSE-corrected `1 keV`
- radio product: particle-loss-aware `150 MHz`

Local source products:

- `docs/science/assets/c_hi_to5_quicklook_2026-05-10/`
- `docs/science/assets/c_hi_cavity_stub_2026-05-10/`
- `docs/science/assets/c_hi_xraise_grid_smoke_2026-05-10/`
- `docs/science/assets/c_hi_particle_radio_smoke_2026-05-10/`

## New Products

Aligned comparison:

- `docs/science/assets/c_hi_aligned_comparison_2026-05-10/aligned_smoke_metrics.csv`
- `docs/science/assets/c_hi_aligned_comparison_2026-05-10/c_hi_aligned_comparison_maps.png`

Determinism check:

- PBS job: `690644.kunanyi-ohpc`
- job name: `c_hi_rdet5`
- node: `n001`
- archive SHA256:
  `e04a16b996111a118998eac52fd3c10f90a602b0fc9a54a8d9df3e28b71802f0`
- comparison products:
  `docs/science/assets/c_hi_particle_radio_determinism_2026-05-10/`

Report:

- `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md`
- `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.pdf`

## Determinism Result

The same 5 Myr particle-radio smoke was rerun with `NUMBA_NUM_THREADS=1` and
`NUMBA_NUM_THREADS=4`. The saved products matched exactly:

- arrays allclose: `True`
- exact hashes: `True`
- maximum array relative difference: `0.0`
- maximum scalar-metric relative difference: `0.0`
- overall pass: `True`

The supplied `xraise.py` still emits the known `NumbaParallelSafetyWarning`,
but the current smoke target is stable across the tested thread counts.

## Next Move

Use this aligned package as the reference target for early-snapshot reporting.
The next science decision is whether to continue the existing `C-HI` run toward
the first `50 Myr` milestone or first extend the extraction/report template to
additional existing early outputs.
