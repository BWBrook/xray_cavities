# Goal 053 — G-LO critical-stratum census

Date opened: 2026-07-30
Status: `complete_no_recompute_finalization`

## Objective

Resolve the high-leverage sampling ambiguity behind Goal 051 by evaluating
every member of its one critical pressure-history stratum from the immutable
G-LO cache. Replace the original 17 weighted sample rows with the exact
262-row unit-weight census in a hybrid population comparison.

This is existing-cache post-processing. It does not authorize a new
simulation, history generation, raytracing, a pressure-method default change,
PRAiSE2 promotion, or publication-facing inference.

## Immutable inputs

- Cache:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate/cache/g_lo_history.h5`
- Cache SHA-256:
  `f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30`
- Affected-row SHA-256:
  `85caef2184edd7786e4d791fd52e77e422269bb6a156a48047d3c7901e4d79f2`
- Goal 051 selection SHA-256:
  `35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df`
- Goal 051 comparison SHA-256:
  `5fa466a1db5450921cd4b95785c0b949a499fd4457cc62da18333061dee8ebeb`
- Pinned plutokore commit:
  `e80252cf35ff5a06166240e2867d3d485aaf6956`

## Census contract

The authoritative membership is reconstructed from the full cache using the
unchanged Goal 049 feature, quartile, shock-median, and certainty-selection
logic. The target is:

```text
affected=1|trim=0|length_q=0|injection_q=0|range_q=1|shock=post_injection_recent
```

The run fails closed unless it finds exactly 262 unique rows: 13 certainty
rows and 249 ordinary rows. The 17 Goal 051 target-stratum rows must be an
exact feature-compatible subset and represent total weight 262.

All census rows receive inclusion probability and analysis weight one. The
stable full-loss, stable adiabatic, and pinned lossless branches are evaluated
under unsmoothed and log-Savitzky-Golay pressure at 0.15 and 1.4 GHz.

## Decision contract

Goal 051's formal predeclared failure remains historical fact. The unchanged
top-1%-mass discrepancy threshold of 0.50 classifies Goal 053:

- `CENSUS_RESOLVES_SAMPLE_LEVERAGE`: hybrid population concentration is at or
  below 0.50.
- `CENSUS_SUPPORTS_LOCALIZED_REGIME`: hybrid concentration remains above 0.50
  but the census-stratum concentration is at or below 0.50. This is evidence
  consistent with distributed localized sensitivity, not proof that the
  target stratum causes the hybrid discrepancy; attribution remains a
  post-run diagnostic.
- `CENSUS_FINDS_RARE_HISTORY_SENSITIVITY`: both concentrations remain above
  0.50.
- `HOLD_FOR_CUTOFF_REVIEW`: a verified cutoff is present.
- `FAIL_NUMERICAL_OR_PROVENANCE`: an inherited numerical, scientific, or
  provenance gate fails.

No confidence interval is interpreted as physical uncertainty. Frequencies
are repeated responses, not independent replicates.

## Execution boundary

The wrapper requests one `normal` node, 16 CPUs, 96 GB, and 12 hours. It uses
fresh no-overwrite stage and analysis roots, an explicit stable archive file
list, immutable hash checks, and the established PBS stop rule. After a single
submission is verified queued or running, stop without polling until Barry
reports the completion email.

## Submission

- PBS job: `780326.kunanyi-ohpc`
- Job name: `g_lo_strcen`
- State at the stop point: `R`
- Queue time / start time: `Thu Jul 30 23:10:51 2026`
- Resources: `select=1:ncpus=16:mpiprocs=1:mem=96gb`,
  `walltime=12:00:00`
- Stage:
  `/u/bwbrook/codex_kunanyi/goal053_g_lo_critical_stratum_census`
- Analysis:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-30-g-lo-critical-stratum-census`

The original scheduler record is a failed run:

- final state: `F`
- `Exit_status=2`
- `Stageout_status=1`
- walltime: `00:34:56`

The run completed all 262 census histories and all 22 stable-core gates before
an obsolete bitwise-exact oracle-replay gate rejected 36 of 204 branch cells.
Those differences are confined to three of the 17 oracle histories, have
maximum relative magnitude `9.1601327385061e-12`, and all satisfy the existing
project scale-aware tolerance with a worst tolerance fraction of
`0.09160043107217158`.

The preserved arrays were finalized locally without cache access or stable
branch recomputation. The resulting decision is:

```text
CENSUS_SUPPORTS_LOCALIZED_REGIME
```

The census-stratum and hybrid top-1%-mass discrepancy fractions are
`0.07069644733314163` and `0.883220701841804`, respectively, against the
unchanged threshold of `0.50`. This supports a distributed localized-
sensitivity interpretation; it does not establish causal attribution or a
production-method default.
