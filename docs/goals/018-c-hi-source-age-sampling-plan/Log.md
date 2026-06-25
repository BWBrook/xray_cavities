# Log: Goal 018 C-HI Source-Age Sampling Plan

## Start

Goal authorized:

```text
Goal 018: local-only C-HI source-age sampling plan for post-maintenance execution.
```

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main
 M .gitattributes
 M docs/exchange/current_status.md
?? docs/exchange/logs/2026-06-25-c-hi-refined-projection-viewing-rerun.md
?? docs/exchange/logs/2026-06-25-c-hi-refined-viewing-angle-consolidation.md
?? docs/goals/016-c-hi-refined-projection-viewing-rerun/
?? docs/goals/017-c-hi-refined-viewing-angle-consolidation/
?? docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/
?? docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/
?? docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md
?? docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md
?? scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
?? scripts/science/build_refined_projection_viewing_rerun.py
?? scripts/science/build_refined_viewing_angle_consolidation.py
?? tests/test_refined_projection_viewing_rerun.py
?? tests/test_refined_viewing_angle_consolidation.py

git rev-parse --short HEAD
bd161e6
```

The dirty accepted Goal 016/017 package was expected. No fast-forward, staging,
commit, push, cleanup, or remote action was performed.

Repo-local `AGENTS.md` was read first.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/`
- `docs/goals/017-c-hi-refined-viewing-angle-consolidation/Log.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/`
- `docs/goals/016-c-hi-refined-projection-viewing-rerun/Log.md`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- Goal 005/011/012 notes/assets sufficient for `0/45/90 deg` provenance
- Goal 009/010 notes/assets sufficient for Level 3 gravity and energy-convention caveats
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/science/assets/c_hi_early_snapshot_series_2026-05-10/`
- `docs/science/assets/c_hi_to10_snapshot_series_2026-05-11/`
- `docs/exchange/logs/2026-06-07-c-hi-fullgrid-agn-impi-r9-prod64-integrity.md`
- final full-grid completion/catalogue evidence in `docs/exchange/current_status.md`

No remote files were queried or listed.

## Choices Made

Created a deterministic planning asset builder:

```text
scripts/science/build_source_age_sampling_plan.py
```

Created focused tests:

```text
tests/test_source_age_sampling_plan.py
```

Created compact asset bundle:

```text
docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/
```

Asset files:

- `source_age_candidate_snapshots.csv`
- `proposed_sampling_plan.csv`
- `post_maintenance_run_contract.csv`
- `runtime_resource_estimate.csv`
- `risk_and_caveat_register.csv`
- `source_age_sampling_plan_metadata.json`

Recommended first-pass execution design for a later goal:

- Future authorized post-maintenance preflight for final-production
  `data.0046.flt.h5`, `data.0049.flt.h5`, and accepted endpoint
  `data.0051.flt.h5`.
- If preflight passes, process two new late-source-age samples:
  `Timestep_46` at about `44.999274 Myr` and `Timestep_49` at about
  `47.999129 Myr`.
- Use `0/45/90 deg` views for each new source age.
- Require `edge_overlap_uniform_cell_projection` for nonzero views.
- Reuse the accepted `50 Myr` endpoint control surface from Goal 005/016 rather
  than rerunning it by default.

Reasoning:

- Goal 017 made the refined `0/45/90 deg` control surface ready for next-step
  planning.
- The final-production integrity evidence locally catalogues late outputs
  `46-51`, while the early `5/10 Myr` products are segment-era diagnostics.
- A two-new-age late-source-age pilot is the narrowest final-production run that
  tests source-age sensitivity without opening an early-time or broad-batch
  branch.

## Deliverables

- `docs/science/c_hi_source_age_sampling_plan_2026-06-25.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/`
- `docs/exchange/logs/2026-06-25-c-hi-source-age-sampling-plan.md`
- `docs/goals/018-c-hi-source-age-sampling-plan/Log.md`
- `docs/exchange/current_status.md` update
- `scripts/science/build_source_age_sampling_plan.py`
- `tests/test_source_age_sampling_plan.py`

## Validation

Focused validation:

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_viewing_angle_consolidation.py tests/test_refined_projection_viewing_rerun.py -q
.........                                                                [100%]
9 passed in 0.04s
```

Assets regenerated with:

```text
uv run python scripts/science/build_source_age_sampling_plan.py
```

Metadata JSON parsed:

```text
uv run python -m json.tool docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_sampling_plan_metadata.json
```

CSV parse and expected-column checks passed:

```text
source_age_candidate_snapshots.csv: rows=17 columns_ok
proposed_sampling_plan.csv: rows=5 columns_ok
post_maintenance_run_contract.csv: rows=8 columns_ok
runtime_resource_estimate.csv: rows=5 columns_ok
risk_and_caveat_register.csv: rows=7 columns_ok
```

Whitespace validation passed:

```text
git diff --check
```

Targeted unresolved-marker scan:

```text
targeted unresolved-marker scan over the new note, exchange log, Goal log,
and current_status.md
result: no matches
```

## Final Status

Goal 018 is complete pending orchestrator wake-up.

Boundary confirmation so far:

- no remote commands;
- no Open OnDemand, SSH/SCP, Kunanyi staging, `qstat`, PBS submission,
  finalizer, retrieval, or job polling;
- no PLUTO production;
- no source-age sampling execution;
- no `C-LO`, `G-LO`, comparison-case processing, PRAiSE/radio/cavity
  regeneration, heavy XRAiSE rerun, or scientific-default changes;
- no commits, pushes, staging, cleanup, `agent_comms` changes, or
  Stas/Patrick escalation;
- accepted Goal 005/011/012/016/017 assets were not overwritten.
