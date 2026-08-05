# G-LO Critical-Stratum Census Failure Closeout

Date: 2026-07-30

## Scope

This note preserves the failed scheduler outcome for PBS
`780326.kunanyi-ohpc` / `g_lo_strcen`. It records retrieval and diagnosis only;
the separate repair note records the no-recompute finalization.

## Scheduler Evidence

```text
job_state = F
Exit_status = 2
Stageout_status = 1
resources_used.walltime = 00:34:56
resources_used.cput = 01:59:37
resources_used.mem = 616452kb
resources_used.ncpus = 16
resources_used.vmem = 3927500kb
```

The retrieved archive is readable and has SHA-256:

```text
dbacf66aaf88aed8cfba1bd901299683eec9334e1788ea58a55c9b09bc2f5bf8
```

Failure evidence is retained under:

```text
docs/science/assets/g_lo_critical_stratum_census_failure_2026-07-30/
```

## First Failure

Remote stdout records:

```text
CriticalStratumCensusError: Goal 051 oracle stable branches were not reproduced exactly
```

The full census calculation had already written all 262 census rows, both
branch NPZ files, the particle comparison, ordering table, cutoff table, and
stable-core gate table. All 22 stable-core gates passed and there were no
cutoffs. Downstream census/hybrid summaries were absent because the exact
oracle gate stopped the diagnostic.

## Diagnosis

Among 17 oracle histories and 204 branch cells:

- 168 cells are bitwise identical;
- 36 nonzero differences are confined to IDs `196752`, `197253`, and
  `197269`;
- maximum absolute difference is `9.15421913206577e-50`;
- maximum relative difference is `9.1601327385061e-12`;
- every cell satisfies the established project rtol-plus-ULP contract;
- the worst cell uses only `0.09160043107217158` of its tolerance.

IDs, cache rows, order, features, selection identity, weights, frequencies,
immutable input hashes, and represented target mass of `262` all align.

The most plausible explanation is batch-composition-dependent floating-point
replay drift between the original 4096-row selection and the 262-row census.
That exact mechanism is not proven because the partial run did not archive
complete runtime-package versions.

## Decision

Do not rerun the expensive branch calculation merely to satisfy bitwise
identity. Preserve this scheduler failure and use a fail-closed local
finalizer against the already generated evidence.
