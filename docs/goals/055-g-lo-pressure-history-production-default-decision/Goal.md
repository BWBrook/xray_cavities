# Goal 055 - G-LO pressure-history production-default decision

Date opened: 2026-08-05
Status: `complete_local_method_decision`

## Objective

Interpret the Goals 050-054 pressure-history evidence and choose the smallest
defensible project method contract for future radio analysis. Separate the
primary project analysis from sensitivity analysis, preserve the published
PRAiSE context, and state which later decisions require supervisor review.

This is a local scientific decision using preserved compact evidence and
source inspection. It does not authorize new PRAiSE computation, raytracing,
particle-history production, a `plutokore` change, PRAiSE2 promotion, or a
publication-facing method claim.

## Inputs

- Goal 049 pressure-smoothing diagnostic and method decision;
- Goal 050 stable full-loss recurrence gate;
- Goal 051 stable method-value comparison;
- Goal 052 PRAiSE2 high-level fail-closed gate;
- Goals 053-054 exact-census and localized-regime synthesis;
- pinned local `plutokore.radio.praise` and `praise2` source; and
- Yates-Jones et al. (2022) PRAiSE method description.

## Decision

Decision label:

```text
UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE
```

- Retain stable unsmoothed particle-pressure histories as the provisional
  project-analysis default.
- Require the positivity-preserving log-Savitzky-Golay treatment as a paired
  method sensitivity whenever the radio result is consequential.
- Reject the published linear-domain Savitzky-Golay operation for this G-LO
  cache because it creates non-positive pressures.
- Do not describe log-SG as the published PRAiSE method: it is a project
  adaptation that preserves positivity.
- Do not interpret the observed `1.89-1.95%` integrated full-loss shift as a
  physical uncertainty interval.
- Keep PRAiSE2 on hold and stop further census work.

This is a provisional internal analysis contract, not a final publication
method freeze. Before the contract drives new C-HI/C-LO history production or
a publication-facing radio comparison, request one focused Patrick/Stas review
of the method choice and its relationship to published PRAiSE.

## Boundaries

No remote command, cache read, PRAiSE call, PBS job, code change, scientific
default change outside this project, supervisor contact, or publication-facing
claim occurred.
