# G-LO Pressure-Method Synthesis

Date: 2026-08-01

Status:

```text
complete_local_synthesis
```

Decision:

```text
LOCALIZED_REGIME_SYNTHESIZED_NO_FURTHER_CENSUS
```

## Question

Goal 051 found a formally failed discrepancy-concentration gate in a weighted
4096-history sample. Goal 053 then evaluated every one of the 262 histories in
the dominant target stratum. Goal 054 asks what remains after replacing the
sampled target-stratum estimate with that exact census, and whether another
targeted census could change the method decision.

## Observations

The original sample and census-replaced hybrid both represent population mass
`197566`; the change is confined to the target stratum.

| Quantity | Goal 051 sample | Census-replaced hybrid |
| --- | ---: | ---: |
| Total weighted method discrepancy | `7.981414981573116e-36` | `3.316030257842135e-36` |
| Top-1%-mass discrepancy fraction | `0.951162697227638` | `0.883220701841804` |
| Full-loss shift, 0.15 GHz | `4.3862%` | `1.8927%` |
| Full-loss shift, 1.4 GHz | `4.4988%` | `1.9485%` |

Exact replacement reduces total weighted discrepancy by `58.4531%`. The Goal
051 weighted target-stratum estimate was `3.34306` times its exact census
discrepancy. The hybrid full-loss shifts are only `0.00814-0.00838 dex`, well
inside the existing `0.10 dex` aggregate gate.

The exact target stratum has these properties:

- `262` histories and `0.132614%` of represented population mass;
- `60.0462%` of hybrid discrepancy;
- `67.9558%` of the global top-1% discrepancy numerator;
- internal top-1% concentration `0.0706964`; and
- largest single-history share only `2.7080%` of stratum discrepancy.

Thus almost all target-stratum discrepancy lies inside the global top 1% of
population mass, yet it is broadly distributed within that small stratum.

The leading uncensused secondary stratum represents `0.364435%` of population
mass and `18.3132%` of hybrid discrepancy. Within the weighted sample, history
`196136` supplies `98.9836%` of that stratum's discrepancy, so its magnitude is
uncertain. However, setting the entire secondary stratum's discrepancy to zero
still leaves global `C(1%) = 0.860074`. Setting the exact target to zero leaves
`0.710356`; setting both to zero yields `0.476646`.

The same retain-mass zeroing diagnostic was applied separately to all 99
uncensused strata. The secondary stratum was the most decision-favourable
single removal; none reduced `C(1%)` below `0.860074`.

These zeroing results retain population rows and are deliberately aggressive
influence diagnostics. They are not replacement estimates.

## Inference

The original sample materially overstated the discrepancy magnitude, but did
not invent the rare-regime signal. Goal 053's census shows that pressure-method
sensitivity is distributed across a very small, recent-post-injection history
regime rather than being a peculiarity of two sampled histories.

No single additional census is decision-relevant under the current gate:
even removing the leading uncensused stratum entirely cannot clear it. A new
Kunanyi census would refine magnitude but would not resolve the present
pass/fail classification. The highest-value next step is therefore an
interpretation and production-default review using the existing compact
evidence.

This does not itself justify changing the production pressure method. The
aggregate radio response is modest and all branches remain descriptive
within one simulation/cache.

## Limits

- The sample is one deterministic unequal-probability realization; joint
  inclusion probabilities or replicate samples needed for a defensible
  design-based variance are unavailable.
- No confidence interval or physical-uncertainty interval is claimed.
- The two frequencies are repeated responses, not independent replication.
- Stratum attribution is exploratory and post hoc, not causal.
- This is not cross-simulation validation, a publication-ready observable,
  PRAiSE2 promotion, or authorization to change scientific defaults.

## Products

The compact `300K` asset bundle is at:

```text
docs/science/assets/g_lo_pressure_method_synthesis_2026-08-01/
```

It contains branch/frequency comparisons, concentration curves, stratum
attribution, selected and exhaustive one-stratum influence diagnostics,
leading contributors, recommendations, metadata, a SHA-256 manifest, and the
synthesis figure.

## Validation

- Focused Goal 054 unit tests passed.
- Related Goal 053 diagnostic/finalizer tests passed.
- The builder compiled and regenerated the official bundle locally.
- Metadata JSON and every CSV parsed with unique, width-consistent schemas.
- The figure was opened and visually reviewed.
- The local SHA-256 manifest verified.
- `git diff --check` passed.

No remote command, cache read, PRAiSE computation, or PBS job occurred.
