# Goal 022 Log - C-HI Late Age-Axis Decision Gate

## 2026-07-01 Start

Goal authorized:

```text
Goal 022: local C-HI late age-axis consolidation and next-step decision gate.
```

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git branch --show-current
main

git rev-parse --short HEAD
4d02142

git status --short --branch
## main...origin/main
```

Repo-local `AGENTS.md` was read first.

Boundary:

- local-only inside `/Users/bwbrook/papers/xray_cavities`;
- no remote commands, Open OnDemand, SSH/SCP, `qstat`, Kunanyi staging, PBS
  jobs, finalizers, retrieval, polling, HDF5/XRAiSE reruns, endpoint rerun,
  source-age substitution, `C-LO`, `G-LO`, comparison cases, early `5/10 Myr`
  branch, PLUTO/PRAiSE/radio/cavity work, scientific-default changes, commits,
  pushes, cleanup, or `agent_comms` edits;
- do not overwrite accepted Goal 005/016/017/019/020/021 assets.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_bounded_age_axis_extension_2026-07-01.md`
- `docs/goals/021-c-hi-bounded-age-axis-extension/Log.md`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/per_age_view_comparison.csv`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/goal021_product_validation.csv`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/age_axis_trend_summary.csv`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/product_provenance.csv`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/bounded_age_axis_extension_metadata.json`
- `docs/science/c_hi_late_source_age_pilot_consolidation_2026-07-01.md`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/per_age_view_comparison.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/source_age_trend_readiness.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/late_source_age_pilot_consolidation_metadata.json`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/c_hi_source_age_sampling_plan_2026-06-25.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_candidate_snapshots.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/proposed_sampling_plan.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/post_maintenance_run_contract.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/risk_and_caveat_register.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_sampling_plan_metadata.json`

No remote files, sibling repos, external UTAS source checkouts, or
`agent_comms` files were read.

## Assets Created

Created:

```text
docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/
```

Machine-readable assets:

```text
late_axis_summary.csv
age_axis_decision_matrix.csv
candidate_age_gap_assessment.csv
product_provenance.csv
late_age_axis_decision_metadata.json
```

Created science note:

```text
docs/science/c_hi_late_age_axis_decision_gate_2026-07-01.md
```

## Decision

Decision label:

```text
LATE_AXIS_SUFFICIENT_FOR_NOW_TOPOLOGY_METHOD_NEXT
```

Headline recommendation:

```text
Pause additional late-age C-HI sampling for now and make the next project move
a local X-ray/cavity topology/method decision-refinement package.
```

Rationale:

- outputs `46/48/49/50/51` now provide a smooth late-axis surface across
  `0/45/90deg`;
- raw and corrected X-ray sums converge monotonically toward the endpoint in
  every view;
- all rows have `0/0/0` raw/corrected/correction-ratio empty-column support;
- nonzero views use `edge_overlap_uniform_cell_projection`;
- the only concrete unprocessed late-axis candidate, `output47`, would mainly
  answer interpolation between `46` and `48`, and is not recommended now.

Active caveats retained:

- late-age X-ray/tracer evidence only, not publication-ready observables;
- connected-envelope/X-ray topology remains unresolved;
- sparse radio remains diagnostic only;
- Level 3 gravity remains `blocked_missing_potential`;
- `pV` / adopted `2.5pV` / `4pV` convention remains active;
- comparison cases, early ages, radio observables, broad batches, endpoint
  reruns, and scientific-default changes remain out of scope.

## Validation

No helper code was added, so no project tests were required.

Passed:

```text
python3 -m json.tool docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/late_age_axis_decision_metadata.json
passed

CSV parse / expected-column / nonempty checks:
late_axis_summary.csv: rows=3 columns_ok
age_axis_decision_matrix.csv: rows=7 columns_ok
candidate_age_gap_assessment.csv: rows=3 columns_ok
product_provenance.csv: rows=17 columns_ok

git diff --check
passed

targeted unresolved-marker scan over the science note, exchange log, Goal log,
and current status
passed
```

Final status:

```text
complete_local_decision_gate
```
