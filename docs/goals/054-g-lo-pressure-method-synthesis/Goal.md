# Goal 054 - G-LO pressure-method synthesis

Date opened: 2026-08-01
Status: `complete_local_synthesis`

## Objective

Synthesize the preserved Goal 051 weighted comparison and Goal 053 exact
critical-stratum census into one finite-population evidence surface. Determine
whether the pressure-method discrepancy remains material after sample-to-census
replacement, where the residual discrepancy is concentrated, and whether a
further targeted Kunanyi census could change the current decision.

This is local analysis of compact preserved products. It does not authorize
new cache generation, PRAiSE computation, raytracing, a production-default
change, PRAiSE2 promotion, or publication-facing inference.

## Inputs

Authoritative inputs are the no-recompute Goal 053 repair assets:

- `original_particle_comparison.csv`: Goal 051's 4096-row unequal-probability
  sample;
- `critical_stratum_particle_comparison.csv`: the 262-row exact census; and
- `critical_stratum_census_summary.json`: census identity and decision
  provenance.

The builder validates unique particle identity, target-stratum membership,
row schemas, branch values, exact represented population mass, and fresh
no-overwrite output before synthesis.

## Estimands

For each pressure mode, loss branch, and frequency, the aggregate is the sum
of particle emissivity times analysis weight. Per-particle pressure-method
discrepancy is the sum across 0.15 and 1.4 GHz of the absolute full-loss
log-Savitzky-Golay versus unsmoothed differences.

Concentration `C(p)` ranks histories by unweighted discrepancy, then uses
analysis weights and a fractional boundary row to measure the share of total
discrepancy carried by the highest-discrepancy `p` fraction of represented
population mass. This matches the Goal 051-053 contract.

The hybrid population replaces only Goal 051's weighted target-stratum rows
with the exact unit-weight census. Diagnostic ablations retain all population
rows and set selected discrepancy contributions to zero; they are influence
diagnostics, not alternative estimates.

## Result

Decision label:

```text
LOCALIZED_REGIME_SYNTHESIZED_NO_FURTHER_CENSUS
```

- Exact census replacement reduces total weighted discrepancy from
  `7.981414981573116e-36` to `3.316030257842135e-36`, a `58.4531%` reduction.
- The Goal 051 weighted estimate of target-stratum discrepancy was
  `3.34306` times the exact census value.
- Full-loss aggregate shifts fall from `4.39-4.50%` in Goal 051 to
  `1.89-1.95%` in the hybrid population. The maximum hybrid full-branch shift
  is `0.00838081 dex`, below the existing `0.10 dex` gate.
- The exact target stratum is `0.1326%` of represented population mass but
  contributes `60.0462%` of hybrid discrepancy and `67.9558%` of the global
  top-1% numerator.
- Its internal top-1% concentration is only `0.0706964`, so sensitivity is
  distributed within the rare stratum rather than being defined by the two
  influential Goal 051 sample histories.
- The leading uncensused secondary stratum contributes `18.3132%` of hybrid
  discrepancy. Zeroing that entire stratum still leaves global `C(1%)` at
  `0.860074`; zeroing the exact target alone leaves `0.710356`. Only zeroing
  both reaches `0.476646`, below the `0.50` gate.

All 99 uncensused strata were zeroed one at a time while retaining their
population rows. The secondary stratum above produced the lowest resulting
`C(1%)`; every other single-stratum diagnostic remained at least as far above
the gate.

Under this deliberately aggressive influence diagnostic, no single further
stratum census can clear the current concentration gate. Further census work
is therefore not decision-relevant now. The next step is a local
pressure-method interpretation and production-default review.

## Boundaries

The result is descriptive for one deterministic G-LO simulation/cache. It has
no sampling confidence interval, does not quantify physical uncertainty, and
does not establish causal attribution. Frequencies are repeated responses,
not independent replicates, and the influential strata were identified after
Goal 051. Production defaults remain unchanged pending explicit review.

No remote command, cache read, PRAiSE computation, PBS job, or supervisor
escalation occurred in Goal 054.
