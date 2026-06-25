# C-HI Refined Viewing-Angle Consolidation

Date: 2026-06-25
Agent: `jet`
Goal: `017-c-hi-refined-viewing-angle-consolidation`
Status: `complete_consolidation`

## Summary

Created a local-only consolidation package for the accepted refined
viewing-angle evidence. Goal 016's refined `45 deg` and `90 deg` products now
supersede the historical Goal 011/012 projection products for future
viewing-angle evidence, while the Goal 005 `0 deg` product remains the
unchanged accepted baseline.

Decision label:

```text
REFINED_VIEWING_ANGLE_EVIDENCE_READY_FOR_NEXT_STEP_PLANNING
```

Recommended Goal 018 shape: prepare a tightly bounded `C-HI` source-age
sampling plan for after the Kunanyi maintenance outage. Do not run it yet.

## Evidence Read

- `AGENTS.md`
- `docs/exchange/current_status.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/goals/016-c-hi-refined-projection-viewing-rerun/Log.md`
- Goal 016 compact CSV/JSON assets
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/goals/015-c-hi-projection-bin-refinement/Log.md`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/goals/014-c-hi-90deg-xray-striping-projection-diagnostic/Log.md`
- Goal 005, Goal 011, and Goal 012 science notes/assets only enough for
  0/45/90-degree context and provenance
- Goal 009/010 Level 3 evidence summary only enough to preserve the
  `blocked_missing_potential` gravity caveat

## Files Created Or Updated

- `scripts/science/build_refined_viewing_angle_consolidation.py`
- `tests/test_refined_viewing_angle_consolidation.py`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/`
- `docs/exchange/logs/2026-06-25-c-hi-refined-viewing-angle-consolidation.md`
- `docs/goals/017-c-hi-refined-viewing-angle-consolidation/Log.md`
- `docs/exchange/current_status.md`

Existing accepted Goal 016 dirty files remain present in the worktree.

## Asset Bundle

New compact assets:

```text
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/historical_vs_refined_viewing_products.csv
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_trio_context.csv
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/product_provenance.csv
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/next_step_readiness.csv
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_viewing_angle_consolidation_metadata.json
```

No compact PNG was created; the requested decision surface is clearer as small
machine-readable tables and prose, and no heavy XRAiSE/product regeneration is
authorized.

## Key Results

Historical-to-refined supersession:

```text
45deg raw/corrected/correction-ratio empty columns: 22/960 -> 0/960
90deg raw/corrected/correction-ratio empty columns: 400/960 -> 0/960
```

Raw/corrected X-ray sum conservation:

```text
45deg raw sum delta = 0
45deg corrected sum delta = -1.33e-15
90deg raw sum delta = 6.31e-16
90deg corrected sum delta = 5.88e-16
```

Current preferred trio:

- `0 deg`: accepted unchanged Goal 005 baseline.
- `45 deg`: accepted refined Goal 016 projection.
- `90 deg`: accepted refined Goal 016 projection.

## Validation

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

## Boundaries

Local-only goal. No remote commands, Open OnDemand, SSH/SCP, Kunanyi staging,
`qstat`, PBS submission, finalizer, retrieval, job polling, PLUTO production,
source-age sampling, `C-LO`, `G-LO`, comparison-case processing,
PRAiSE/radio/cavity regeneration, heavy XRAiSE rerun, scientific-default
changes, commits, pushes, staging, cleanup, `agent_comms` changes, or
Stas/Patrick escalation occurred.

Accepted Goal 005/011/012/016 assets were not overwritten.
