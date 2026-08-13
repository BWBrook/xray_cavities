# G-LO last-shock PRAiSE comparison review

Date: 2026-08-11
Goal: 056
Decision label:
`PRAISE2_USABLE_METHOD_DIFFERENCE_PERSISTS_PATRICK_CONFIRMATION_REQUIRED`

## Bottom line

PBS `784939.kunanyi-ohpc` completed the requested 4096-particle population
comparison and 14-particle detailed panel. Its `Exit_status=3` was the
wrapper's intentional science-hold exit, not a compute crash. Native PRAiSE2
pressure stayed positive in every retained post-shock interval, no native
numerical failure occurred, and all 62 applicable direct full-loss replay
checks matched the pinned high-level calls exactly.

The two reported replay failures are one selected width-one history evaluated
under native and common-input modes. The population calculation already uses
the approved singleton convention: with no elapsed interval, the lossless
value is also the full value. The detailed panel instead called PRAiSE2's full
loss branch directly, which returned zero. The instrumented replay and both
PRAiSE1/Goal 050 comparators returned finite emissivity of order `10^-42`.
This is a diagnostic-contract mismatch, not a PRAiSE2 numerical failure. The
48 singleton histories are `0.0243%` of represented weight.

No fourth remote run is justified. The local diagnostic now applies the same
singleton convention as the population path, with a focused regression test.
The immutable retrieved archive and its original hold decision remain intact.

## Patrick's method question

The controlled common-input comparison does not make the PRAiSE1/PRAiSE2
difference disappear:

- At `0.15 GHz`, common-input PRAiSE2 differs materially from PRAiSE1 for
  `17.96%` of represented weight; native PRAiSE2 gives `17.59%`.
- At `1.4 GHz`, common-input PRAiSE2 differs materially for `27.17%`; native
  PRAiSE2 gives `27.21%`.
- Material spectral-index changes are `12.79%` on common raw input and
  `12.86%` natively.
- Native smoothing versus common raw input is material for only `0.756%` of
  weight at either project frequency and for `0%` by the spectral-index gate.
  Its weighted median amplitude ratio is `1.00034`, with a 5-95% interval of
  approximately `0.993-1.009`.

Therefore the observed PRAiSE1/PRAiSE2 difference is principally a real
method difference in recurrence, coefficients, and cutoff handling, not an
artifact of PRAiSE2's pressure smoothing. This is consistent with Patrick's
instruction to record rather than erase the differences.

## Decision and boundary

The evidence supports pinned PRAiSE2 as numerically usable and scientifically
interpretable for post-shock histories under its explicit singleton
convention. Because adopting it controls future matched C-HI/C-LO/G-LO radio
production, Patrick should confirm that the persistent common-input difference
is the intended distinct-method behaviour. Matched production remains held
until that concise confirmation; another Goal 056 compute run is not needed.

This package does not claim publication-ready radio observables, reinterpret
PRAiSE1/Goal 050 as PRAiSE2, or turn method differences into physical
uncertainty. Future production must still report luminosity versus time, as
requested by Stas.

## Patrick decision - 2026-08-13

Patrick accepted this interval-aware validation and selected PRAiSE2 as the
published-method reference. The current pinned implementation remains the
uncorrected provenance baseline. Before production use, restore the published
equation (3) `4/3` multiplier in the radiative-loss coefficient and complete
the coefficient-only validation specified by `Q-027` in
`agent_comms/threads/2026-08-05-g-lo-pressure-history-method-review.md`.

## Evidence

- Machine-readable synthesis: `method_effect_summary.csv`,
  `singleton_gate_review.csv`, and `completion_summary.csv`.
- Immutable archive SHA-256:
  `17f829a509822960dabd6f6ae799dd9cc9636d46331436fc359023989ca644b4`.
- Review payload:
  `docs/science/assets/g_lo_praise_last_shock_comparison_hold_2026-08-11/`.
