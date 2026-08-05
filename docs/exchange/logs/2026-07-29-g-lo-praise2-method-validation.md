# Exchange log — Goal 052 G-LO PRAiSE2 method validation

Date: 2026-07-29
Status: `complete_local_fail_closed_gate`

Patrick-agent's `Q-022` request was applied to the documented high-level
`plutokore.radio.praise2.praise(...)` call, not to a lower-level alias.

Exact source identity passed. The local adapter contract also establishes the
same immutable Goal 051 cache and selection, exact ordering, loss switches,
frequencies, pressure modes, unit conversion, endpoint index, shape, and
singleton-history policy. It also fails closed unless PRAiSE2's full internal
resampling-index vector preserves every declared history record.

The scientific gate fails before cache-scale execution. The public PRAiSE2
result exposes emissivity but not gamma trajectories, cutoff classifications,
or fallback records. The pinned source also differs from the Goal 050 stable
method in Larmor gamma, radiative coefficient, and full-loss recurrence.

Decision:
`PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION`.

No PRAiSE2 promotion, Goal 050/051 relabelling, cache-scale comparison, remote
job, production history generation, raytracing, plutokore modification,
scientific-default change, commit, or push occurred.

Barry separately reported Goal 051 PBS `779913.kunanyi-ohpc` completed with
`Exit_status=3`. The exact Goal 051 result remains unclaimed until its archived
summary is retrieved; exit `3` alone covers both scientific `FAIL` and
`HOLD_FOR_CUTOFF_REVIEW`.

The executable scaffold's available comparator is explicitly the raw Goal 049
lower-level method. It does not claim to compare Goal 051's stable branches;
those outputs must first be retrieved and aligned.
