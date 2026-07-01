# C-HI Bounded Age-Axis Extension

Date: 2026-07-01

Status: `complete_product_retrieved_and_packaged`

Decision label: `BOUNDED_LATE_AXIS_EXTENSION_COMPLETE_REVIEW_READY`

## Scope

Goal 021 retrieved and packaged the already-completed bounded post-processing
job for two additional final-production `C-HI` late source-age targets:

- `data.0048.flt.h5::Timestep_48`, about `46.999857 Myr`;
- `data.0050.flt.h5::Timestep_50`, about `48.999420 Myr`.

The accepted endpoint control remains reused, not rerun: Goal 005 `0deg` and
Goal 016 refined `45deg`/`90deg` for `output51`. Goal 019/020 `output46` and
`output49` are used only as accepted compact pilot context.

No new PBS job, finalizer, HDF5/XRAiSE rerun, endpoint rerun, source-age
substitution, early-age branch, comparison-case processing, radio/cavity work,
or scientific-default change occurred during this retrieval and packaging
continuation.

## Remote Completion Evidence

Barry reported the completion email for PBS job `718233.kunanyi-ohpc`
(`c_hi_ageext`):

```text
Exit_status=0
resources_used.cpupercent=98
resources_used.cput=00:38:08
resources_used.mem=1337596kb
resources_used.ncpus=1
resources_used.vmem=1770088kb
resources_used.walltime=00:52:48
```

A final read-only `qstat -x -f` check found the job in finished state with the
same resource usage and `Exit_status = 0`. It also reported
`Stageout_status = 1`, retained here as a scheduler caveat. The expected
archive, stdout, and empty stderr were retrieved directly from the Goal 021
stage path and validated locally.

Retrieved archive:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
```

Archive SHA-256:

```text
8147e945034df15510e831f85e0393c7b88c74cd8d70ae1fa16ca025b86e71e7
```

Stdout SHA-256:

```text
24057dc3a96b92335234780e0777d42870daa956f71624d9224f1a363e06be4f
```

Stderr SHA-256:

```text
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

## Product Validation

All six intended Goal 021 products were present in the retrieved archive and
passed the wrapper validation markers:

| output | view | projection method | raw/corrected/ratio empty columns | status |
| --- | --- | --- | --- | --- |
| 48 | `0deg` | `direct_y_axis_sum` | `0/0/0` | passed |
| 48 | `45deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` | passed |
| 48 | `90deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` | passed |
| 50 | `0deg` | `direct_y_axis_sum` | `0/0/0` | passed |
| 50 | `45deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` | passed |
| 50 | `90deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` | passed |

The compact product-validation table is:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/goal021_product_validation.csv
```

## Late-Axis Context

The new `48` and `50` products fill the late-axis gap between the accepted
Goal 019/020 pilot context (`46`, `49`) and the accepted endpoint control
(`51`). Across `46 -> 48 -> 49 -> 50 -> 51`, the corrected X-ray sums move
smoothly toward the endpoint within each view, with complete projected support.

Corrected X-ray sum ratios to the same-view endpoint:

| output | `0deg` | `45deg` | `90deg` |
| --- | ---: | ---: | ---: |
| 46 | 1.029214 | 1.009666 | 1.009666 |
| 48 | 1.017252 | 1.005886 | 1.005886 |
| 49 | 1.011406 | 1.003947 | 1.003947 |
| 50 | 1.005652 | 1.001983 | 1.001983 |
| 51 | 1.000000 | 1.000000 | 1.000000 |

The full comparison table is:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/per_age_view_comparison.csv
```

The trend summary is:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/age_axis_trend_summary.csv
```

## Interpretation

The bounded age-axis extension completed cleanly and produced reviewable compact
X-ray/tracer products for both requested ages and all three requested viewing
angles. The refined projection accumulator is active for nonzero views, and the
Goal 014/012 empty-column failure does not recur in the new `45deg` or `90deg`
outputs.

This is still a late-source-age pilot/extension review surface, not a
publication-ready observable product. It is not implicit authorization for a
broad source-age sweep, early ages, `C-LO`, `G-LO`, comparison cases, or radio
observable generation.

## Caveats

- `Stageout_status = 1` remains visible as a scheduler caveat, although the
  stage archive/stdout/stderr were directly retrieved and locally validated.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV`/adopted `2.5pV`/`4pV` convention remains active.
- Accepted Goal 005/011/012/016/017/018/019/020 assets are preserved as
  provenance and were not overwritten.

## Recommendation

The next useful goal should be local-only: consolidate and interpret the full
late-axis surface (`46`, `48`, `49`, `50`, endpoint `51`) before choosing any
additional sampling. That decision gate should decide whether the current
late-axis evidence is sufficient for the next science step, whether one more
explicitly selected `C-HI` age is justified, or whether X-ray/cavity topology
work should take priority.
