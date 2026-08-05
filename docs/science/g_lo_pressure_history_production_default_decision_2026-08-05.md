# G-LO Pressure-History Production-Default Decision

Date: 2026-08-05

Status: `complete_local_method_decision`

Decision:

```text
UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE
```

## Question

Goals 050-054 established a numerically stable radio-loss calculation and
localized the difference between unsmoothed and log-Savitzky-Golay pressure
histories. This goal asks which treatment should be the project's primary
analysis, which should be retained as sensitivity analysis, and what remains
unresolved before three-case radio production.

## Observations

The published PRAiSE method smooths interpolated particle density and pressure
histories to reduce sampling noise. Yates-Jones et al. use a Savitzky-Golay
window of five samples and polynomial order three, corresponding to `0.05 Myr`
for their `0.01 Myr` sampling, and report that this retained the overall
pressure trend and emissivity evolution. See
[Yates-Jones et al. (2022)](https://academic.oup.com/mnras/article/511/4/5225/6527582).

The project pressure treatments are not equivalent to that published method:

- `unsmoothed` preserves the positive treated PLUTO pressure history and is
  the current low-level project primary contract;
- published-style linear-domain Savitzky-Golay smoothing creates `216035`
  non-positive values across `99108/197398` eligible G-LO histories and is
  therefore physically and numerically inadmissible for this cache; and
- `log_savgol` applies the same window and polynomial order to `log(pressure)`
  before exponentiation. It preserves positivity, but it is a project
  adaptation rather than the published linear-domain operation.

The project log-SG filter uses SciPy `mode="nearest"`, which extends the signal
with its boundary value and can alter endpoint values. That behaviour is
documented by the
[SciPy Savitzky-Golay reference](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.savgol_filter.html).

After the exact-census replacement, log-SG versus unsmoothed changes integrated
G-LO emissivity as follows:

| Branch | 0.15 GHz | 1.4 GHz |
| --- | ---: | ---: |
| no losses | `1.80646%` | `1.80646%` |
| adiabatic | `1.87143%` | `1.87143%` |
| full losses | `1.89273%` | `1.94849%` |

Thus most of the full-loss amplitude difference is already present when losses
are disabled. Relative to the no-loss branch, full ageing adds only `0.08626`
and `0.14203` percentage points at 0.15 and 1.4 GHz. The full-loss spectral
index changes by only `-0.00024496`.

Goal 054 also shows that `60.0462%` of method discrepancy occurs in a
recent-post-shock stratum representing `0.1326%` of population mass. The signal
is distributed within that stratum, but no additional single-stratum census
can change the current concentration classification.

## Inference

Smoothing has a legitimate methodological motivation: particle histories
contain interpolation noise, and published PRAiSE treats smoothing as part of
its workflow. However, the published linear-domain operation fails the basic
positive-pressure domain constraint for this dataset. The positivity-preserving
log-SG alternative is not independently calibrated against a higher-cadence or
higher-resolution pressure truth, and its dominant aggregate effect is a
change to present pressure rather than the accumulated loss history.

Consequently, adopting log-SG as the sole primary method would replace a
measured simulation quantity with an unvalidated transformation. Conversely,
discarding smoothing entirely would conceal a published-method sensitivity
that is strongly localized in young post-shock histories.

The defensible project contract is therefore:

1. use the stable unsmoothed pressure history as the provisional primary
   analysis;
2. calculate log-SG as a required paired sensitivity for consequential radio
   results;
3. report the difference as method sensitivity, not physical uncertainty;
4. keep the stable log-domain loss recurrence from Goal 050 for both pressure
   treatments; and
5. do not promote PRAiSE2 or identify project log-SG as published PRAiSE.

## Claim Boundary

This decision supports a project-internal primary/sensitivity convention. It
does not establish that unsmoothed pressure is a noise-free physical truth,
that log-SG is a statistically optimal smoother, or that the `1.9%` G-LO
amplitude difference transfers to C-HI or C-LO. It is not a confidence interval
or a publication-method certification.

One focused supervisor review is warranted before this convention triggers
new C-HI/C-LO history production or appears in a manuscript. The review should
ask whether unsmoothed-primary plus log-SG-sensitivity is acceptable given the
published smoothing motivation and the demonstrated failure of linear-domain
smoothing on the current cache.

## Next Step

Do not run another census or radio job now. Prepare a concise Patrick/Stas
method-review request containing this decision and its evidence. If accepted,
the next compute goal can generate the missing matched C-HI/C-LO histories and
then produce three-case, two-frequency radio products under both pressure
treatments.

## Products

The compact decision tables are under:

```text
docs/science/assets/g_lo_pressure_history_production_default_decision_2026-08-05/
```

No new scientific computation or remote work was performed.
