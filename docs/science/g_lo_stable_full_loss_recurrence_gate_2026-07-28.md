# G-LO stable full-loss recurrence gate

Date: 2026-07-28

## Status

Goal 050 is complete. The retained deterministic 64-trace G-LO panel passed
the numerical-method gate under decision label
`G_LO_STABLE_FULL_LOSS_RECURRENCE_GREEN_4096_COMPARISON_JUSTIFIED`.

PBS `779729.kunanyi-ohpc` / `g_lo_flloss` finished with `Exit_status=0`.
The compact evidence was retrieved and independently validated. See
`docs/science/g_lo_stable_full_loss_recurrence_gate_completion_2026-07-29.md`.
The result authorizes only the later deterministic 4096-row comparison; it
does not alter pinned PRAiSE or authorize raytracing or production adoption.

## Why this gate is needed

Goal 049 observed two distinct facts in the pinned full-loss calculation:

- raw dimensional `a2` was non-finite in `22,737` relevant intervals; and
- PRAiSE silently retained the previous Lorentz factor in `45,474`
  frequency-specific updates.

Those observations block scientific use of the full-loss result, but they do
not by themselves prove that the RAiSE II recurrence lacks a finite numerical
representation. Raw `a2` contains absolute-time powers that can overflow even
when the dimensionless coefficient used by the gamma denominator remains
finite.

## Stable representation

For an earlier/later interval `(t0, t1)`, set

```text
L     = log(t1 / t0)
delta = log(p1 / p0)
ap    = delta / L
b     = ap / (3 Gamma)
q     = b L
x3    = L + delta + q
x4    = L + q
```

With `exprel(x) = expm1(x) / x` and its removable limit
`exprel(0) = 1`, the diagnostic evaluates

```text
lambda = a2 / t1**b
       = c1 t0 exp(-q) L
         [uB exprel(x3) + uC exprel(x4)]
```

and then

```text
g0 = g1 exp(-q) / (1 - g1 lambda).
```

The calculation stays in log space except in the narrow representable
neighbourhood of the pole, where a direct scaled product avoids cancellation
in `log(g1) + log(lambda)`. Raw `a2` is retained as a log-valued diagnostic and
is not required to fit in binary64.

## State semantics

Every relevant update must be one of:

- `finite`: a positive finite antecedent Lorentz factor exists;
- `physical_cutoff`: `g1 lambda >= 1`, so no finite positive antecedent exists;
- `gamma_inf_cutoff`: the formal antecedent exceeds the declared upper bound;
- `subrelativistic`: the formal antecedent is below one; or
- `post_cutoff`: an earlier interval follows an already explicit cutoff.

A physical or `gamma_inf` cutoff is represented as no emission, consistent
with the RAiSE II treatment of electrons whose required injection Lorentz
factor is infinite. It is never implemented by retaining the previous gamma.
`subrelativistic` is an invalid state for this Lorentz-factor and emissivity
model, not another no-emission policy. Any relevant occurrence fails the gate
and is rejected by emissivity reconstruction.
See Turner et al. (2018), Appendix A,
[RAiSE II](https://academic.oup.com/mnras/article/473/3/4179/4411818).

## Evidence contract

The gate will:

1. bind the completed history cache, 4096-row selection, archived non-finite
   records, and pinned `plutokore` source by SHA-256;
2. deterministically recover the same 64-trace panel used by Goal 049;
3. evaluate both accepted pressure modes at `0.15` and `1.4 GHz`;
4. compare every relevant scaled loss and gamma update with an independent
   80-digit implementation;
5. require exact state agreement and one-ULP classification stability;
6. reproduce the pinned raw-`a2` and silent-fallback counts;
7. reconstruct finite emissivity or an explicit no-emission cutoff state; and
8. write deterministic compact evidence before returning a scientific pass or
   fail.

The analytic-limit gate is executed at runtime. It checks the constant-pressure
closed form, the removable `a3 = 0` and `a4 = 0` limits against the independent
80-digit implementation, and a case where raw `a2` exceeds binary64 range
while the scaled coefficient remains finite.

The retained local Goal 049 archive lacks the interval time, pressure, and
adiabatic-index arrays. The real panel gate therefore requires one small,
single-node read-only post-processing job against the immutable remote cache.

## Local readiness

The implementation passed:

- `16` focused Goal 050 tests, including explicit `gamma_inf` and
  subrelativistic-state policy checks;
- `161` related Goal 048-050 regression tests;
- wrapper `bash -n` and `shellcheck`; and
- `git diff --check`.

An independent scientific audit found the recurrence algebra, relevant-history
window, physical-cutoff semantics, and 4096-only decision boundary sound. Its
single material objection was that a subrelativistic state could previously
reach emissivity reconstruction. That path is now rejected and independently
gated at zero relevant occurrences.

## Decision scope

The observed pass authorizes only the deterministic 4096-row method-value
comparison. It does not approve a production default, raytracing, population
interpretation, or a publication-facing radio observable.
