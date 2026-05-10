# 2026-05-10 C-HI Cavity-Protocol Stub

## Summary

Completed the first explicit cavity-protocol smoke product for the aligned
`C-HI` 5 Myr, `0 deg` target. This uses the same PLUTO HDF5 output as the
quick-look, truth, and bridge observable products:

- `data.0008.flt.h5`
- `Timestep_8`
- `4.9994348189788402 Myr`

The extraction was run on a `kunanyi` compute node as PBS job
`690620.kunanyi-ohpc` and completed with no stderr output.

## Method

The current stub fits one 3D tracer-defined ellipsoid per lobe using
`tracer > 5e-3`. It then estimates local ambient conditions from a same-side
ellipsoidal shell with `tracer <= 1e-3`.

It reports:

- projected `0 deg` cavity ellipse boundary
- ellipsoid and tracer-extent volumes
- local ambient pressure and density
- `pV` and `4pV`
- sound-crossing, buoyancy, and refill age estimates

The buoyancy/refill ages are provisional because the gravity term is currently
estimated from an inner/outer ambient-shell hydrostatic pressure-gradient
proxy. This is fine for the smoke gate but should not be treated as the final
science cavity-age method.

## Key Outputs

- report: `docs/science/c_hi_cavity_stub_2026-05-10.md`
- PDF: `docs/science/c_hi_cavity_stub_2026-05-10.pdf`
- assets: `docs/science/assets/c_hi_cavity_stub_2026-05-10/`
- compact archive:
  `build/science/kunanyi_stage_2026-05-08/c_hi_cavity_stub_690620_compact_2026-05-10.tar.gz`
- archive SHA-256:
  `8166ab35bf27f7058bb5b44a387fd0f169edc8ccf2e4bbab920228bf3d78f769`

Per-lobe smoke values:

- semi-axes: `9.465 x 9.465 x 16.510 kpc`
- ambient pressure: `1.7422e-10 dyn cm^-2`
- `pV`: `3.1709e58 erg`
- `4pV`: `1.2684e59 erg`
- sound age: `13.45 Myr`

## Interpretation

This closes the remaining mechanical item in Phase 6 of the meeting-2 action
plan. The aligned 5 Myr target now has:

- Level 1 injected-energy truth
- Level 2 tracer-mask truth
- bridge X-ray/radio observable smoke
- first cavity-protocol stub

The next science-facing upgrade is the full Python GRAiLE/XRAiSE runtime and
particle-loss-aware observable path for this same target.
