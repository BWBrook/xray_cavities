# G-LO PRAiSE2 High-Level Method Validation

Date: 2026-07-29

Status: `complete_local_fail_closed_gate`

Decision label:
`PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION`

## Decision

Patrick-agent's conditional rule is applied exactly: anything short of a green
documentation, provenance, numerical, state/cutoff, test, and determinism gate
means no PRAiSE2 promotion.

The gate is not green. The high-level
`plutokore.radio.praise2.praise(...)` interface is a distinct numerical method,
not a production wrapper around the Goal 050 stable implementation. It also
does not expose the gamma/state information needed to audit its silent
no-emission decisions. Goals 050-051 therefore do not transfer unchanged and
must not be relabelled as PRAiSE2 evidence.

## Observations

- The pinned source identity is exact: commit
  `e80252cf35ff5a06166240e2867d3d485aaf6956`, SHA-256
  `ad664648040c4330ce124fdde7b739b7cd701759a52569863fc79460895f9668`.
- PRAiSE2's Larmor gamma contains a denominator factor of three that is absent
  from the lower-level implementation. For otherwise identical inputs, this
  changes gamma by `1/sqrt(3)`.
- PRAiSE2's effective Myr radiative coefficient is
  `7,687,346.536601961`, while the lower-level SI coefficient converted to Myr
  is `10,249,795.35055844`; the ratio is `0.7500000023105955`.
- PRAiSE2 full losses use the original power-form recurrence. They do not use
  Goal 050's scaled/log-domain stable full-loss recurrence.
- In the pinned high-level loop, a nonpositive or NaN gamma fails the `> 0`
  test and is assigned zero. The public result returns emissivity plus output
  indices, but no internal state, so the cause cannot be distinguished as a
  physical cutoff, numerical cutoff, or fallback from the returned object.
- PRAiSE2 resamples particle times internally. The adapter must group histories
  by effective post-injection start, use a Myr-valued time unit, require the
  complete resampling-index vector to preserve every declared history record,
  require the returned particle-output index to equal the endpoint, and reject
  any order or shape drift.
- The exact Goal 051 selection includes 48 one-record histories. The high-level
  lossy branches cannot establish the approved instantaneous singleton
  convention directly; any adapter must label that convention as external and
  exclude those rows from direct lossy-method validation.

## Inference

The observed differences are scientific/numerical method differences, not
provenance wording. Widening a tolerance cannot establish equivalence. A
cache-scale emissivity comparison could describe endpoint differences, but it
could not satisfy Patrick's direct state/cutoff requirement through the
current public API.

The most informative and least wasteful action is therefore to stop at the
failed state-observability gate. The completed local adapter is retained so a
future reviewed PRAiSE2 run can reuse the exact cache, selection, units,
pressure treatments, branch labels, and order without reconstructing the
contract.

The included executable scaffold can compare PRAiSE2 with the raw Goal 049
lower-level branches only. It is explicitly not a Goal 051 stable-branch
comparison. Adding that comparison requires the retrieved Goal 051 branch
outputs and a new exact input-alignment gate.

## Goal 051 Completion Context

Barry reported that PBS `779913.kunanyi-ohpc` / `g_lo_stmv` completed with
`Exit_status=3`, walltime `05:12:08`, and `16` CPUs. Under the Goal 051 wrapper
contract, exit `3` means either scientific `FAIL` or
`HOLD_FOR_CUTOFF_REVIEW` after evidence archival. The exit code alone does not
distinguish those outcomes.

The exact Goal 051 archive and summary have not yet been retrieved because the
TPAC Open OnDemand route is currently stopped at Microsoft sign-in in Chrome.
No Goal 051 scientific result is inferred here.

## Verification Boundary

The local tests exercise:

- pinned live-Git and staged-commit provenance;
- exact loss-code and SI-frequency construction;
- pressure-only log-Savitzky-Golay treatment;
- component-2 last-shock mapping;
- high-level output shape, units, endpoint index, and non-finite preservation;
- deterministic nested-array fingerprints;
- exact cache/selection hash failure;
- exact full-history resampling-index preservation;
- grouped start-time and singleton adapter behaviour; and
- fail-closed state visibility.

The actual 33 GB cache comparison and actual-call deterministic repeat were
not run because the state gate had already failed. No production default is
changed.

Final related verification passed `43` tests. A focused independent review
first returned NO-GO on four execution-scaffold defects; after repair, the
same review returned GO for the fail-closed scaffold only. That GO is not a
PRAiSE2 scientific pass.

## Next Step

Patrick-agent should treat `Q-022` as answered with `HOLD`: do not promote
PRAiSE2 and do not relabel Goals 050-051. A later method decision can choose
between:

1. exposing auditable gamma/cutoff/fallback state from PRAiSE2, followed by a
   fresh high-level 4096-row comparison; or
2. accepting PRAiSE2 as a distinct method whose production preference requires
   a newly scoped scientific validation rather than an equivalence claim.

Separately, retrieve and package Goal 051 once Chrome authentication is
available. That retrieval cannot reverse the PRAiSE2 state-observability hold,
but it is required to close Goal 051 honestly.
