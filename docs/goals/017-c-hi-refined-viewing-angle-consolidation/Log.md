# Log: Goal 017 C-HI Refined Viewing-Angle Consolidation

## 2026-06-25 - start state

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main
 M .gitattributes
 M docs/exchange/current_status.md
?? docs/exchange/logs/2026-06-25-c-hi-refined-projection-viewing-rerun.md
?? docs/goals/016-c-hi-refined-projection-viewing-rerun/
?? docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/
?? docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md
?? scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
?? scripts/science/build_refined_projection_viewing_rerun.py
?? tests/test_refined_projection_viewing_rerun.py

git rev-parse --short HEAD
bd161e6
```

Repo-local `AGENTS.md` was read first. The dirty Goal 016 package was expected
and accepted by the new goal instructions. No fast-forward, staging, commit,
push, or cleanup was performed.

## 2026-06-25 - evidence read

Read scoped, repo-local evidence:

- `docs/exchange/current_status.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/goals/016-c-hi-refined-projection-viewing-rerun/Log.md`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/empty_column_before_after.csv`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_metrics.csv`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_vs_accepted_xray_summary.csv`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/product_provenance.csv`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_viewing_rerun_metadata.json`
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/goals/015-c-hi-projection-bin-refinement/Log.md`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/goals/014-c-hi-90deg-xray-striping-projection-diagnostic/Log.md`
- Goal 005, Goal 011, and Goal 012 notes/assets only enough for 0/45/90-degree context and provenance
- `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/level3_evidence_summary.csv`

Key evidence:

- Goal 016 fixed the historical `90 deg` raw/corrected/correction-ratio
  X-ray empty-column failure from `400/960` to `0/960`.
- Goal 016 fixed the historical `45 deg` raw/corrected/correction-ratio
  X-ray empty-column issue from `22/960` to `0/960`.
- Raw/corrected X-ray pixel sums are conserved to roundoff relative to the
  accepted historical products.
- Goal 005 remains the accepted unchanged `0 deg` baseline.
- Goal 011/012 remain historical diagnostic artifacts and should not be
  overwritten.
- Connected-envelope topology, sparse-radio diagnostic status, Level 3 gravity
  `blocked_missing_potential`, and the `pV`/`2.5pV`/`4pV` convention remain
  active caveats.

## 2026-06-25 - builder and assets

Created:

```text
scripts/science/build_refined_viewing_angle_consolidation.py
tests/test_refined_viewing_angle_consolidation.py
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/
```

Generated compact assets:

```text
historical_vs_refined_viewing_products.csv
refined_trio_context.csv
product_provenance.csv
next_step_readiness.csv
refined_viewing_angle_consolidation_metadata.json
```

Builder output:

```text
status=complete_consolidation
decision_label=REFINED_VIEWING_ANGLE_EVIDENCE_READY_FOR_NEXT_STEP_PLANNING
recommended_next_option=tightly_bounded_c_hi_source_age_sampling_after_maintenance
recommended_goal018_shape=local planning packet for tightly bounded C-HI source-age sampling after maintenance
```

## 2026-06-25 - docs and status package

Created:

- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/exchange/logs/2026-06-25-c-hi-refined-viewing-angle-consolidation.md`
- this Goal 017 log

Updated:

- `docs/exchange/current_status.md`

No `agent_comms` files were changed.

## 2026-06-25 - decision

Decision label:

```text
REFINED_VIEWING_ANGLE_EVIDENCE_READY_FOR_NEXT_STEP_PLANNING
```

Decision:

- Goal 016 refined `45 deg` supersedes Goal 011 for future 45-degree viewing
  evidence.
- Goal 016 refined `90 deg` supersedes Goal 012 for future 90-degree viewing
  evidence.
- Goal 005 remains the accepted unchanged `0 deg` control baseline.

Recommended Goal 018 shape:

```text
Prepare a tightly bounded C-HI source-age sampling plan after Kunanyi maintenance; do not run it yet.
```

X-ray/cavity topology refinement remains important but is not the next blocker
for a planning goal. Radio observable/raytracing, gravitational Level 3
convention work, and `C-LO`/`G-LO` comparison-case preparation should remain
separate later lanes.

## 2026-06-25 - validation

Validation:

```text
uv run pytest tests/test_refined_viewing_angle_consolidation.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_90deg_xray_striping_diagnostic.py -q
13 passed

uv run python scripts/science/build_refined_viewing_angle_consolidation.py
status=complete_consolidation

uv run python -m json.tool docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_viewing_angle_consolidation_metadata.json
<valid JSON>

CSV parse/expected-column checks
passed

git diff --check
<no output>

targeted unresolved-marker scan
<no output>
```

## 2026-06-25 - final status

Goal 017 status:

```text
complete_consolidation
```

Boundary confirmation: no remote commands, Open OnDemand, SSH/SCP, Kunanyi
staging, `qstat`, PBS submission, finalizer, retrieval, job polling, PLUTO
production, source-age sampling, `C-LO`, `G-LO`, comparison-case processing,
PRAiSE/radio/cavity regeneration, heavy XRAiSE rerun, scientific-default
changes, commits, pushes, staging, cleanup, `agent_comms` changes, or
Stas/Patrick escalation occurred. Accepted Goal 005/011/012/016 assets were
not overwritten.
