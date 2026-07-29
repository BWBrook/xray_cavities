# Goal 050: G-LO Stable Full-Loss Recurrence Gate

## Objective

Determine whether the retained Goal 049 G-LO failure panel supports a
numerically stable, scientifically equivalent implementation of the RAiSE II
full-loss coefficient and backward Lorentz-factor recurrence.

The goal must distinguish numerical failure from the physical pole at which no
finite positive injection Lorentz factor can produce the observed electron.
It must not hide either state by retaining the previous gamma.

## Approved Scope

Barry approved Goal 050 on 2026-07-28.

In scope:

- derive a scaled/log-domain form of RAiSE II equations A10 and A11;
- handle the removable `a3 = 0` and `a4 = 0` limits explicitly;
- test constant-pressure, zero-radiation, small-cadence, extreme-exponent,
  physical-pole, `gamma_inf`, and sub-relativistic cases;
- replay both accepted Goal 049 pressure modes on the deterministic retained
  64-trace panel;
- compare every relevant loss coefficient and gamma update with an independent
  80-digit reference;
- classify finite trajectories, physical cutoffs, boundary-unstable cases, and
  invalid inputs explicitly;
- preserve the original pinned-PRAiSE non-finite evidence unchanged; and
- produce a compact decision package that either unlocks the deterministic
  4096-row method-value comparison or closes the loss-aware branch.

## Numerical Contract

For an earlier/later interval `(t0, t1)` with `t1 > t0 > 0`, positive
pressures `(p0, p1)`, and `Gamma > 1`, define:

```text
L     = log(t1 / t0)
delta = log(p1 / p0)
ap    = delta / L
b     = ap / (3 Gamma)
q     = b L
x3    = L + delta + q
x4    = L + q
```

With `exprel(x) = expm1(x) / x` and `exprel(0) = 1`, evaluate the coefficient
actually used by the recurrence:

```text
lambda = a2 / t1**b
       = c1 t0 exp(-q) L
         [uB exprel(x3) + uC exprel(x4)]
```

The backward update is:

```text
g0 = g1 exp(-q) / (1 - g1 lambda)
```

The implementation must use log-domain evaluation where direct exponentiation
would overflow or lose the denominator near a pole. It must not require raw
dimensional `a2` to be representable as a binary64 number.

## Decision Gate

The gate passes only if:

1. all relevant inputs satisfy the declared domain;
2. all analytic and limiting-case tests pass;
3. every relevant panel coefficient has a finite log/scaled representation and
   agrees with the independent 80-digit reference within the predeclared
   tolerance;
4. every relevant frequency update is finite or receives an explicit physical
   cutoff classification, with exact agreement against the reference;
5. no update silently retains the previous gamma;
6. classifications are invariant to one-ULP perturbations near any observed
   pole or `gamma_inf` boundary;
7. finite trajectories reconstruct finite full-loss emissivity, while proven
   physical cutoffs are represented explicitly as no emission; and
8. a deterministic repeat yields the same decision and compact hashes.

Pass label:
`G_LO_STABLE_FULL_LOSS_RECURRENCE_GREEN_4096_COMPARISON_JUSTIFIED`.

Fail label:
`G_LO_RADIO_METHOD_BLOCKED_STABLE_FULL_LOSS_GATE_FAILED`.

## Compute And Side-Effect Boundary

- The immutable Goal 049 history cache may be read but not modified. Its live
  file size is `33191119360` bytes (about 33.2 GB).
- One small, single-node post-processing PBS job may be submitted if needed to
  access the retained panel on Kunanyi.
- No PLUTO production, history regeneration, 4096-row comparison, raytracing,
  C-HI/C-LO work, or pinned `plutokore` default change is authorized.
- Compact evidence may be retrieved; the full cache and raw simulation payloads
  must remain remote.
- Apply the normal PBS queued/running stop rule.

## Completion And Stopping

- Use red-green tests for the stable recurrence.
- Perform one focused implementation review and one independent scientific
  audit of the decision-grade result.
- If the panel gate passes, stop after authorizing only the 4096-row comparison.
- If it fails, stop with the exact failing interval/classification and close the
  loss-aware branch; do not add another algebraic retry without new evidence.
- Follow the 80/20 delivery policy and avoid marginal parameter sweeps.

## Validation

- focused unit and integration tests;
- independent 80-digit comparisons on every relevant panel interval/update;
- Python compilation;
- PBS wrapper `bash -n` and `shellcheck`;
- JSON/CSV schema and duplicate-header checks;
- immutable input and staged-source hashes;
- compact-payload guard;
- deterministic repeat checks;
- independent scientific audit; and
- `git diff --check`.
