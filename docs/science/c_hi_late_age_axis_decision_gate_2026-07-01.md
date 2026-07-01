# C-HI Late Age-Axis Decision Gate

Date: 2026-07-01

Status: `complete_local_decision_gate`

Decision label: `LATE_AXIS_SUFFICIENT_FOR_NOW_TOPOLOGY_METHOD_NEXT`

## Scope

Goal 022 consolidates the accepted late-age `C-HI` X-ray/tracer evidence
surface:

```text
outputs 46, 48, 49, 50, endpoint 51
views 0deg, 45deg, 90deg
```

This is a local-only decision package. It uses existing compact assets from
Goals 016-021 and does not run remote commands, stage Kunanyi files, submit PBS
jobs, retrieve data, rerun HDF5/XRAiSE, rerun the endpoint, substitute source
ages, broaden to comparison cases, or edit `agent_comms`.

## Evidence Surface

Machine-readable assets are under:

```text
docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/
```

Primary assets:

| File | Purpose |
| --- | --- |
| `late_axis_summary.csv` | one row per view summarizing the `46/48/49/50/51` trend |
| `age_axis_decision_matrix.csv` | ranked next-step options |
| `candidate_age_gap_assessment.csv` | assessment of whether another age is justified |
| `product_provenance.csv` | row-to-goal and row-to-asset mapping |
| `late_age_axis_decision_metadata.json` | compact status, caveats, and recommendation |

Evidence read:

- Goal 021 note, log, metadata, validation table, trend table, provenance, and
  recommendation assets;
- Goal 020 consolidation note/assets for `46/49` and endpoint context;
- Goal 016/017 refined-viewing notes/assets for endpoint and projection-method
  context;
- Goal 018 source-age plan assets for candidate inventory and no-broad-sweep
  guardrails;
- current project status.

## Late-Axis Result

Across every view, raw and corrected X-ray sums converge monotonically toward
the endpoint over the accepted late-age sequence. All rows retain complete
projected support:

```text
raw/corrected/correction-ratio empty columns = 0/0/0
```

Corrected X-ray sum ratios to the same-view endpoint:

| output | `0deg` | `45deg` | `90deg` |
| --- | ---: | ---: | ---: |
| 46 | 1.029214 | 1.009666 | 1.009666 |
| 48 | 1.017252 | 1.005886 | 1.005886 |
| 49 | 1.011406 | 1.003947 | 1.003947 |
| 50 | 1.005652 | 1.001983 | 1.001983 |
| 51 | 1.000000 | 1.000000 | 1.000000 |

For the nonzero views, the active product surface uses:

```text
edge_overlap_uniform_cell_projection
```

The `0deg` surface uses direct y-axis summation, with the endpoint row retained
as the accepted Goal 005 direct-baseline product.

## One-More-Age Assessment

The only concrete late-axis candidate left by local catalogue evidence is:

```text
data.0047.flt.h5::Timestep_47
source age about 45.999563 Myr
```

It would answer the interpolation gap between output `46` and output `48`.
That is the largest remaining unsampled one-output interval inside the current
late-axis sequence.

I do not recommend running it now. Goal 021 already added `48` as the bridge
between the original `46/49` pilot and added `50` as the near-endpoint
neighbor. The resulting `46/48/49/50/51` surface is smooth, monotonic, and
support-complete in every view. Output `47` would most likely be an audit or
interpolation check, not a decision-making product.

## Decision Matrix

Recommended ranking:

| Rank | Option | Recommendation |
| ---: | --- | --- |
| 1 | stop late-age sampling for now | adopt current late-axis surface |
| 2 | X-ray/cavity topology-method refinement | best next project move |
| 3 | one more precisely chosen `C-HI` age | hold unless a concrete gap is identified |
| 4 | early-age branch | defer |
| 5 | `C-LO`/`G-LO` or comparison cases | defer |
| 6 | radio/raytracing readiness | separate method lane |
| 7 | Level 3 gravity convention | separate blocked lane |

The full decision matrix is:

```text
docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/age_axis_decision_matrix.csv
```

## Recommendation

Pause additional late-age `C-HI` source-age sampling for now. The next project
move should be a local X-ray/cavity topology and method decision/refinement
package using existing assets, with explicit go/no-go criteria for any later
product rerun.

Reason: after the refined projection repair and the completed late-axis scalar
surface, the connected-envelope/X-ray topology caveat is now the leading
interpretive limitation. More late-age scalar points are unlikely to resolve
that caveat.

## Caveats

- This is late-age X-ray/tracer evidence, not publication-ready observables.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
- `C-LO`, `G-LO`, early ages, comparison cases, radio observables, broad
  batches, endpoint rerun, and scientific-default changes remain out of scope.
- Accepted Goal 005/016/017/019/020/021 assets were not overwritten.

## Non-Claims

Goal 022 does not authorize another PBS job, another source-age target, a broad
source-age sweep, comparison-case processing, or publication-facing claims. It
is an internal decision aid for the next bounded project move.
