# Exchange log — Goal 053 G-LO critical-stratum census

Date: 2026-07-30
Status: `complete_no_recompute_finalization`

Goal 053 resolves the sole material Goal 051 ambiguity with an exact census of
the declared 262-row stratum from the existing immutable cache. The 17
original target rows are an oracle, not the membership source.

The workflow preserves the stable Goal 051 branches, frequencies, pressure
treatments, cutoff semantics, and the predeclared 0.50 concentration
threshold. It also constructs a hybrid population estimate by replacing only
the weighted target stratum with its unit-weight census.

The execution wrapper requests one node, 16 CPUs, 96 GB, and 12 hours. It
binds all immutable hashes, fails closed on membership/count drift, archives
only compact generated evidence, and applies the PBS queued/running stop rule.
No production or raytracing work is authorized.

An independent pre-submission review repaired two fail-closed defects before
compute was committed: partial scientific failures now retain their available
cutoff/gate evidence without requiring success-only arrays, and the staged
Kunanyi compatibility modules are explicitly included on `PYTHONPATH`.
Regression and remote runtime checks passed after both repairs.

Exactly one PBS job was submitted: `780326.kunanyi-ohpc` / `g_lo_strcen`.
It finished with `Exit_status=2` after `00:34:56`. The retrieved archive shows
that all 262 census histories and all 22 stable-core gates completed, but an
obsolete bitwise-exact replay gate rejected 36 of 204 oracle cells.

Those differences occur in only three of 17 oracle histories. Their maximum
relative magnitude is `9.1601327385061e-12`; every cell passes the existing
project scale-aware tolerance, with a worst tolerance fraction of
`0.09160043107217158`. The evidence is consistent with batch-composition
floating-point drift, although exact runtime-package provenance is
insufficient to prove that mechanism.

A local fail-closed finalizer validated the preserved CSV/NPZ identity,
features, ordering, weights, population mass, and numerical tolerance, then
generated the missing summaries without reopening the cache or recomputing
stable branches. The result is:

```text
CENSUS_SUPPORTS_LOCALIZED_REGIME
```

The census-stratum top-1%-mass discrepancy fraction is
`0.07069644733314163`; the hybrid-population value is `0.883220701841804`;
the unchanged threshold is `0.50`. This is evidence consistent with
distributed localized sensitivity, not causal attribution or authorization
for a pressure-method default change.

The original PBS failure remains recorded. No rerun was submitted.
