# G-LO PRAiSE last-shock comparison: retry failure

Date: 2026-08-11
Goal: 056
Decision label: `FAILED_GOAL050_CONTEXT_COMPARATOR_FINITE_ASSUMPTION`

## Observed failure

PBS `784931.kunanyi-ohpc` (`g_lo_lstcmp_r1`) finished with `Exit_status=2`
after `02:08:29`. Staged hashes, immutable inputs, runtime imports, PRAiSE2
preprocessing, and the population comparison all passed far enough to reach
the representative-particle detailed evidence panel.

The detailed panel then raised:

```text
FullLossDiagnosticError: finite emissivity requires finite endpoint and injection gamma
```

The wrapper archived the failure evidence successfully. The original stage
and archive remain unchanged. Compact retrieved evidence is under
`docs/science/assets/g_lo_praise_last_shock_comparison_retry_failure_2026-08-11/`:

| file | SHA-256 |
|---|---|
| `g_lo_praise_last_shock_comparison_r1.out` | `93f22852bd949d17f28243db3a54a1836643899792d52cf67e021d46693e33ec` |
| `g_lo_praise_last_shock_comparison_r1.err` | `3216bb585104fc2a78ef69c7834814af101dd980d89292177bd2bfaf11f3f439` |
| `g_lo_praise_last_shock_comparison_retry_2026-08-11.tar.gz` | `c3ef7c511814f69e413d7ddacf8197ce999dc7597f6da82214c685cf7f752662` |

The archive is readable and contains eight compact evidence members. No
analysis directory or Goal 056 science product was produced.

## Diagnosis

This failure is in the contextual Goal 050 comparator, not a PRAiSE2
acceptance gate. Goal 050 classifies each frequency as finite, a physical or
gamma cutoff, post-cutoff, or subrelativistic. The Goal 056 panel discarded
that classification and passed the full frequency vector to the finite-only
emissivity reconstruction. One unavailable gamma therefore stopped the whole
diagnostic.

The repair now applies Goal 050's existing state policy frequency by
frequency: explicit cutoffs are retained as zero, finite states are
reconstructed, and subrelativistic or unexpectedly non-finite gamma states are
recorded as unavailable rather than converted into science values. Unexpected
reconstruction errors still fail closed. The PRAiSE2 gates and thresholds are
unchanged.

## Repair gate

Focused local validation passed (`16 passed`), including the exact
cutoff-plus-non-finite state combination. The same state-aware comparator test,
staged manifest verification, wrapper syntax check, and local/remote SHA-256
match passed in the Kunanyi runtime.

One final retry, PBS `784939.kunanyi-ohpc` (`g_lo_lstcmp_r2`), is queued under
fresh no-overwrite stage and analysis paths. If that run exposes another
material failure, Goal 056 should stop for method reassessment rather than
continue with another incremental retry.
