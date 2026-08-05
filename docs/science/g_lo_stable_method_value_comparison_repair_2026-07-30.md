# G-LO stable method-value comparison repair — 2026-07-30

Status: `complete_repair_green_new_scientific_gate_fail`

Decision label:
`G_LO_STABLE_METHOD_VALUE_FAIL`

## Observed completion

PBS `779913.kunanyi-ohpc` finished with `Exit_status=3`. The retrieved
archive is readable and has SHA-256
`4f7b689fb30bc44f1d35557fbbfd32272f895acd41a7f730a3be8eeb907ec27c`.
Its structured decision is `FAIL`, not `HOLD_FOR_CUTOFF_REVIEW`.

Every declared infrastructure gate passed. The exact deterministic selection
contains `4096` rows and the pinned cache, selection, pressure treatment,
runtime, and source identities agree. The primary unsmoothed stable adiabatic
trajectory also passed its endpoint gate, with zero relevant non-finite
states, fallbacks, and nonpositive-time records.

The first history group contained eight finite disagreements between the
primary pressure-ratio recurrence and its algebraically equivalent time-ratio
diagnostic form. Execution stopped immediately, so eight is not an exhaustive
prevalence estimate. The archive correctly contains the early-failure summary
surfaces but not the branch arrays or particle/order comparisons.

## Root cause and repair

The shared adiabatic implementation intentionally uses the pressure-ratio
trajectory as primary and records the time-ratio difference as a numerical
diagnostic. Its endpoint gate does not require the two finite representations
to agree at the tighter pairwise threshold. Existing tests likewise require
finite algebraic-form differences to remain diagnostic-only.

Goal 051 nevertheless promoted
`relevant_algebraic_disagreement_count` into a hard failure in both its
per-group and aggregate adiabatic gates. This was a local gate-contract
mismatch, not evidence of alternate physics or an unstable primary
trajectory.

The repair removes only that count from the fatal criteria. It remains
reported. Non-finite states, fallbacks, nonpositive times, endpoint failure,
and nondeterministic repeats still fail closed.

An independent review reproduced the accepted Goal 049 evidence: 32 marginal
pressure-versus-time differences among `431744` cells, while the primary
pressure-ratio values remained within the declared high-precision tolerance.
The review classified the original Goal 051 outcome as a false negative and
recommended exactly one fresh retry.

## Verification and retry

- Regression red phase reproduced the false failure.
- The repaired regression and related Goal 049-052 suites passed:
  `77 passed in 6.94s`.
- Python compilation, wrapper `bash -n`, `shellcheck`, and
  `git diff --check` passed.
- The retry stage has the same immutable cache, exact selection, pinned
  plutokore commit, and wrapper hash, with repaired diagnostic script SHA-256
  `4d8d093d95fef7681d1f778e999bf0ef255bc6264881321f449ca24bc3d177e1`.
- Fresh stage:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison_r1`.
- Fresh analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison-r1`.
- PBS `780137.kunanyi-ohpc` / `g_lo_stmv_r1` was verified queued on
  `normal` at `Thu Jul 30 00:02:12 2026`, requesting `16` CPUs, `96gb`,
  and `12:00:00`.

At submission, the PBS stop rule prohibited polling or another retry before
Barry reported completion. The declared response to a different material
scientific gate was to stop and review rather than open another incremental
repair ladder.

## Retry outcome

The retry did reach a different material scientific gate, so the repair ladder
has stopped.

PBS `780137.kunanyi-ohpc` completed with `Exit_status=3` after `09:54:05`.
Its archive is complete and has SHA-256
`abd34c707197f6b984d5ea9e34c07731abcb7565223e8fc01f2c6900ddc5ca62`.
All eight output products passed local schema and finite-value validation.

The bookkeeping repair is confirmed: the stable recurrence, adiabatic
recovery, reconstruction, repeatability, cutoff, and infrastructure gates all
pass. The sole remaining failure is the predeclared pressure-method
discrepancy-concentration gate. The top `1%` of represented population weight
accounts for `95.116%` of total absolute method discrepancy, compared with the
declared maximum `50%`.

Two recent-shock histories of length eight account for `83.391%` of the
weighted discrepancy and `80.400%` without weights. This is therefore not a
weighting artefact, although their stratum sample has high design leverage.
The result is best described as a numerically green method comparison with a
localized scientific sensitivity that requires a complete critical-stratum
census before any production decision.

No further Goal 051 retry is justified.

## Relationship to Goal 052

The PRAiSE2 high-level validation remains
`PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION`. Its unavailable
trajectory/cutoff/fallback state and material coefficient/recurrence
differences are independent of this Goal 051 bookkeeping repair. The repaired
Goal 051 retry has now provided the stable comparison, but its localized
discrepancy-concentration failure does not authorize PRAiSE2 promotion.
