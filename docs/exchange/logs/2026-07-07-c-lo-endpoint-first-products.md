# 2026-07-07 - C-LO Endpoint First Products

Goal 036 advanced from the accepted C-LO endpoint-status review into the first
bounded compact endpoint products and a first-pass C-HI/C-LO scalar comparison.

## Completion Decision

Status:
`complete_product`.

Decision label:
`C_LO_ENDPOINT_FIRST_PRODUCTS_COMPLETE_COMPACT_COMPARISON_READY`.

PBS completion:

- job id: `751098.kunanyi-ohpc`;
- job name: `c_lo_xprod`;
- final scheduler state: `F`;
- `Exit_status=0`;
- resources used: `walltime=00:27:19`, `cput=00:17:39`,
  `mem=1144972kb`, `ncpus=1`, `vmem=1709232kb`.

The qstat record reports `Stageout_status=1`, but the requested stage-root
archive/stdout/stderr and final qstat evidence were present and retrieved.

## Endpoint Gate

Accepted C-LO endpoint run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles
```

Preflight evidence packaged in the product archive:

- `markers/DONE` present and `markers/FAILED` absent.
- Endpoint file `data.0053.flt.h5` contains `Timestep_53`.
- Required datasets `rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3` exist with
  shared shape `(1014, 960, 960)`.
- Endpoint HDF5 time is `15330.069689399999`, consistent with
  `15330.06968940`.

## Retrieval

Retrieved compact evidence from:

```text
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products/
```

Local asset bundle:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/
```

Retrieved archive:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/c_lo_endpoint_first_products_2026-07-07.tar.gz
```

Archive SHA-256:

```text
041eed367d0b74e5bbfbfd3d2ca1e9b51c0eb24b90c7fdd32c36a8bec95646c1
```

No C-LO `.h5`, `data.*`, or particle payload files were copied locally.

The original retrieved archive is retained unchanged as provenance. The local
review product copy is:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/
```

The remote archive's `c_lo_endpoint_projection_metrics.csv` had a duplicate
`time_myr` header. The local review copy repairs that schema by retaining the
first `time_myr` column and dropping the duplicate copy; the scalar values are
unchanged. `schema_repair_manifest.csv` records this archive-original caveat.

Package size is explicit: `large_file_inventory.csv` records `13` files above
`5 MiB`, namely the retrieved `39.419 MiB` archive and twelve `15.782 MiB` TSV
endpoint-review arrays. The TSV arrays are retained as parseable 2-D C-LO
endpoint review payloads, not as HDF5/PLUTO `data.*`/particle payloads; every
retained file is below `100 MiB`.

## Review Iteration Validation

Local package/schema hardening validation:

- focused tests:
  `uv run pytest tests/test_c_lo_endpoint_first_products_wrapper.py tests/test_xraise_grid_smoke_projection.py -q`
  passed with `12 passed`;
- wrapper syntax:
  `bash -n scripts/kunanyi/c_lo_endpoint_first_products.pbs` passed;
- metadata JSON parse passed;
- CSV parse, expected-column, nonempty, and duplicate-header checks passed
  across `18` Goal 036 CSV review surfaces;
- archive readability:
  `tar -tzf` passed with `38` members;
- no-bulky-payload guard found no `.h5`, `data.*`, or `particles.*` files in
  the local Goal 036 asset bundle;
- `git diff --check` passed;
- targeted unresolved/stale-label scan found no Goal 036 stale
  submitted-waiting status or unresolved markers.

## Product Results

Validated compact C-LO endpoint views:

- `0deg`: `direct_y_axis_sum`, corrected X-ray sum
  `3494804623.455285`, empty columns `0/960`.
- `45deg`: `edge_overlap_uniform_cell_projection`, corrected X-ray sum
  `1385987160.135606`, empty columns `0/960`.
- `90deg`: `edge_overlap_uniform_cell_projection`, corrected X-ray sum
  `1960081839.138744`, empty columns `0/960`.

All raw, corrected, and correction-ratio layers report zero empty projected
columns across all three views.

First-pass C-LO/C-HI corrected X-ray sum ratios:

- `0deg`: `1.087839647658863`.
- `45deg`: `0.9665266425113752`.
- `90deg`: `0.9665266425113748`.

## Local Product Files

Science note:

```text
docs/science/c_lo_endpoint_first_products_2026-07-07.md
```

Key assets:

- `completion_summary.csv`
- `retrieved_archive_manifest.csv`
- `product_validation_summary.csv`
- `headline_c_hi_c_lo_comparison.csv`
- `large_file_inventory.csv`
- `schema_repair_manifest.csv`
- `c_lo_endpoint_first_products_metadata.json`
- schema-clean review product root `review_products/`

## Boundaries

No new PBS submission, PLUTO production, C-LO continuation, G-LO work,
XRAiSE/PRAiSE/radio/cavity rerun, source-age sweep, broad batch,
scientific-default change, bulky local retrieval, commit, push, cleanup,
Stas/Patrick contact, `agent_comms` edit, or accepted-asset overwrite occurred.

## Recommendation

Review and accept Goal 036 as the first compact C-LO endpoint product surface.
The next goal should either interpret the C-HI/C-LO endpoint comparison surface
in a bounded review packet or prepare the next G-LO readiness/execution branch
if X-ray Cavities wants to complete the three-case comparison ladder.
