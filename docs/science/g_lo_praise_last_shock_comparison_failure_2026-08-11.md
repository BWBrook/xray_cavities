# G-LO PRAiSE last-shock comparison: first-attempt failure

Date: 2026-08-11
Goal: 056
Decision label: `FAILED_INVALID_UNIFORM_INDEX_GATE_AND_ARCHIVE_INVOCATION`

## Observed failure

PBS `784909.kunanyi-ohpc` (`g_lo_lstcmp`) finished with `Exit_status=1` after
`03:37:13`. The compact stdout shows that staged inputs, the history cache,
selection/comparator files, pinned source, and runtime imports all passed their
preflight checks.

The diagnostic run then raised:

```text
Praise2DiagnosticError: PRAiSE2 uniform resampler omitted one or more declared history indices
```

The wrapper subsequently failed to archive the diagnostic evidence because
`archive_file_list_payload.sh` was byte-preserved with mode `0600` and invoked
directly. No remote science-product archive was produced. The three compact
stage logs were retrieved without modifying the original stage:

| file | SHA-256 |
|---|---|
| `g_lo_praise_last_shock_comparison.out` | `1c122956a1a8a7756e7a313c245770f74af47eedcf40ac3c91862e78abe06473` |
| `g_lo_praise_last_shock_comparison.err` | `1becabaa698230e9e8cad7b24dfe36a6fbb34557a7c378d874fb439c153c9688` |
| `g_lo_praise_last_shock_comparison.run.log` | `ee8314066afa15debedd3c2c1074019bc23dc36771a0ae83283d6e23d6a85ec4` |

## Diagnosis

The cache's particle outputs are irregularly spaced around 0.01 Myr. Pinned
PRAiSE2 constructs a uniform 0.01 Myr target grid and selects each target's
nearest source sample. It is therefore expected that some intermediate source
indices will not be selected. Requiring exact retention of every source index
was a diagnostic assumption, not a PRAiSE2 contract.

Focused review also found that the detailed replay smoothed the irregular
source series before resampling. Pinned PRAiSE2 instead resamples, backfills,
and then optionally applies native linear Savitzky-Golay smoothing. A retry
without correcting that order could have passed infrastructure while replaying
a different trajectory.

## Repair gate

The repair accepts omitted intermediate source indices while retaining exact
source-index provenance and a bounded endpoint-lag check. Actual and replayed
single-particle calls now share one contract and the pinned preprocessing
order. The wrapper invokes the archive helper through `bash`.

Local tests passed (`15 passed`), including irregular raw and native-smoothed
histories compared directly with pinned PRAiSE2. The native-smoothed proof also
passed in the staged Kunanyi runtime. This validates the repair mechanism; it
does not produce or prejudge the Goal 056 science decision.

Retry PBS `784931.kunanyi-ohpc` is queued under fresh no-overwrite stage and
analysis paths. The original scheduler failure remains part of the provenance.
