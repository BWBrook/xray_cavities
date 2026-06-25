# C-HI Source-Age Sampling Plan

Date: 2026-06-25

## Status

Goal 018 completed a local-only planning/control packet for a future bounded
`C-HI` source-age sampling run after Kunanyi maintenance and explicit
X-ray Cavities/Barry authorization.

Decision label:

```text
SOURCE_AGE_SAMPLING_PLAN_READY_FOR_POST_MAINTENANCE_AUTHORIZATION
```

This log records planning only. No remote work or source-age execution occurred.

## New Files

- `docs/science/c_hi_source_age_sampling_plan_2026-06-25.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_candidate_snapshots.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/proposed_sampling_plan.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/post_maintenance_run_contract.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/runtime_resource_estimate.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/risk_and_caveat_register.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_sampling_plan_metadata.json`
- `scripts/science/build_source_age_sampling_plan.py`
- `tests/test_source_age_sampling_plan.py`
- `docs/goals/018-c-hi-source-age-sampling-plan/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/`
- `docs/goals/017-c-hi-refined-viewing-angle-consolidation/Log.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/`
- `docs/goals/016-c-hi-refined-projection-viewing-rerun/Log.md`
- Goal 014/015 notes/assets sufficient to preserve the refined-projection rationale
- Goal 005/011/012 notes/assets sufficient to preserve the accepted historical/refined trio context
- Goal 009/010 Level 3 and broadening-decision evidence sufficient to preserve the gravity blocker and energy convention
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- final full-grid catalogue/integrity logs under `docs/exchange/logs/`

No remote files were queried.

## Recommendation

Recommended first post-maintenance execution design:

- Use a future authorized goal to preflight final-production `prod64` outputs
  `data.0046.flt.h5`, `data.0049.flt.h5`, and the accepted endpoint
  `data.0051.flt.h5`.
- If preflight passes, post-process two new late-source-age samples:
  - `Timestep_46`, about `44.999274 Myr`
  - `Timestep_49`, about `47.999129 Myr`
- Use `0/45/90 deg` views for each new source age.
- Require the Goal 015/016 refined accumulator for nonzero views:
  `edge_overlap_uniform_cell_projection`.
- Reuse the accepted 50 Myr endpoint control surface:
  Goal 005 `0 deg`, Goal 016 refined `45 deg`, and Goal 016 refined `90 deg`.

The earlier `5 Myr` and `10 Myr` segment diagnostics remain useful source-age
anchors, but they should not be the default first final-production execution
targets unless a future authorized preflight verifies equivalent full-grid
inputs and X-ray Cavities chooses that broader branch.

## Unknowns For Future Execution

- Live post-maintenance Kunanyi access and queue status.
- Immediate HDF5 presence/readability for outputs `46` and `49`.
- Whether particle/cavity companion inputs for those source ages are sufficient
  for the exact future product surface.
- Whether X-ray Cavities wants to move from this late-source-age pilot to early
  `5/10 Myr` full-grid equivalents after the first pass.

## Boundary Confirmation

- No remote commands, Open OnDemand, SSH/SCP, Kunanyi staging, `qstat`, PBS
  submission, finalizer, retrieval, or job polling occurred.
- No PLUTO production, source-age sampling execution, `C-LO`, `G-LO`,
  comparison-case processing, PRAiSE/radio/cavity regeneration, heavy XRAiSE
  rerun, or scientific-default change occurred.
- No commits, pushes, staging, cleanup, `agent_comms` changes, or Stas/Patrick
  escalation occurred.
- Accepted Goal 005/011/012/016/017 assets were not overwritten.
