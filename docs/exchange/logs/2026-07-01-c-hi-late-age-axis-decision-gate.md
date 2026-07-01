# 2026-07-01 - C-HI Late Age-Axis Decision Gate

## Scope

Goal 022 is a local-only consolidation and decision gate for the completed
late-age `C-HI` X-ray/tracer evidence surface:

```text
outputs 46, 48, 49, 50, endpoint 51
views 0deg, 45deg, 90deg
```

No remote commands, Open OnDemand, SSH/SCP, `qstat`, Kunanyi staging, PBS jobs,
finalizers, retrieval, HDF5/XRAiSE reruns, endpoint rerun, source-age
substitution, comparison cases, early-age branch, PLUTO/PRAiSE/radio/cavity
work, scientific-default changes, commits, pushes, cleanup, or `agent_comms`
edits occurred.

## Evidence Read

- Goal 021 science note, log, metadata, validation, trend, provenance, and
  recommendation assets.
- Goal 020 consolidation note/assets for `46/49` and endpoint context.
- Goal 016/017 refined projection/viewing context.
- Goal 018 source-age plan/candidate inventory and guardrails.
- Current project status.

## Outputs

Science note:

```text
docs/science/c_hi_late_age_axis_decision_gate_2026-07-01.md
```

Asset bundle:

```text
docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/
```

Machine-readable assets:

- `late_axis_summary.csv`
- `age_axis_decision_matrix.csv`
- `candidate_age_gap_assessment.csv`
- `product_provenance.csv`
- `late_age_axis_decision_metadata.json`

Goal log:

```text
docs/goals/022-c-hi-late-age-axis-decision-gate/Log.md
```

## Decision

Decision label:

```text
LATE_AXIS_SUFFICIENT_FOR_NOW_TOPOLOGY_METHOD_NEXT
```

The completed `46/48/49/50/51` late-axis surface is enough for the current
late-age pass. Corrected and raw X-ray sums converge monotonically toward the
endpoint in all views, projected support is complete, and nonzero views use the
refined accumulator.

The only concrete additional late `C-HI` age candidate is `output47`, which
would fill the interpolation gap between `46` and `48`. It is not recommended
now because it is unlikely to change the decision unless a reviewer explicitly
requests that adjacent point.

Recommended next goal shape:

```text
local X-ray/cavity topology and method decision/refinement package using
existing assets, before broader sampling or comparison-case work.
```

## Caveats

- Late-age X-ray/tracer evidence only; not publication-ready observables.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- `pV` / adopted `2.5pV` / `4pV` convention remains active.
- `C-LO`, `G-LO`, early ages, comparison cases, radio observables, broad
  batches, endpoint rerun, and scientific-default changes remain out of scope.

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
