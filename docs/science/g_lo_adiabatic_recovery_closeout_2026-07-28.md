# G-LO Adiabatic Recovery Closeout

Date: 2026-07-28

Status: `complete_diagnostic_closeout`

Decision label:
`ADIABATIC_RECOVERY_SUPPORTED_FULL_LOSS_METHOD_BLOCKED_A2`

## Decision

PBS `779693.kunanyi-ohpc` completed the repaired diagnostic and returned its
deliberate scientific `Exit_status=3`. The infrastructure, immutable inputs,
archive, and HDF5 row-order repair passed.

The result separates two conclusions:

1. The proposed pressure-ratio/log-difference adiabatic recurrence passes on
   the bounded recovery panel.
2. The full-loss PRAiSE method remains blocked because its radiative
   coefficient and gamma state machine are not numerically reliable on the
   same relevant intervals.

No full `4096`-row comparison or raytrace is authorized by this result.

## Observations

- All four selected archived pressure-mode/frequency failure strata reproduced
  as non-finite under pinned PRAiSE.
- All `431,744` retained stable gamma values were finite, positive, and below
  `gamma_inf`.
- All `98` grouped stable-versus-80-digit checks passed. The maximum relative
  difference was `9.994967978657982e-12`.
- Reconstructed stable injection states produced finite emissivity.
- The two stable algebraic forms differed in `32 / 431,744` cells, with a
  maximum relative difference of `1.6612874572382827e-11`.
- The pinned zero-radiative-loss recurrence differed from the stable result in
  `32 / 372,496` finite-overlap cells. Every material violation came from
  physical ID `147678` next to upstream numerical breakdown.
- Full-loss `a2` was non-finite in `22,737 / 215,872` relevant intervals.
- Pinned PRAiSE then made `45,474` relevant NaN gamma updates, exactly two
  frequencies per non-finite `a2` interval, and silently retained the previous
  gamma.

## Interpretation

The archived `stable_endpoint_trajectory=false` label combined stable
trajectory validity with unrelated full-loss fallback and upstream-comparison
state. It therefore did not show that the proposed adiabatic recurrence
failed. The local diagnostic now reports those checks separately; no remote
rerun is needed to correct that bookkeeping.

The non-finite `a2` and silent gamma fallback counts are a genuine scientific
blocker for the full-loss estimand. A finite endpoint full-loss emissivity is
not sufficient evidence of valid loss integration when the state machine has
silently retained prior gamma values.

## Provenance And Retention

The retrieved archive is readable and has SHA-256:

```text
71f40e9510834acbc4475bfa59b4e22faddbba0a32dd343dcdef3b81956cf3f8
```

It preserves the `96 MB` trace table and the archived non-finite record table.
After deriving the compact closeout tables, their redundant extracted copies
were removed. The immutable archive, stdout, stderr, compact summaries,
staged-input manifest, and reclassification tables remain locally.

## Next Step

The highest-value next goal is a stable full-loss numerical-method gate:

- derive a stable evaluation of `a2` and the full gamma recurrence;
- prove analytic limiting cases locally;
- compare every relevant interval on the existing bounded panel with an
  independent high-precision reference;
- require finite `a2`, zero silent gamma fallback, and finite reconstructed
  full-loss emissivity.

If that gate fails, close the loss-aware PRAiSE branch as method-blocked and
use the already identified matched lossless endpoint fallback. If it passes,
one `4096`-row method-value comparison becomes justified. Raytracing and new
multi-node history production remain on hold.
