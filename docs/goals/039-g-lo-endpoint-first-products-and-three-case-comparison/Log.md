# Goal 039 Log - G-LO Endpoint First Products And Three-Case Comparison

## Objective

Generate the full first G-LO endpoint X-ray/tracer product surface at
`0/45/90 deg` and produce a coherent scalar endpoint comparison across
`C-HI`, `C-LO`, and `G-LO` in one post-processing job.

## Local Implementation

Added:

- `scripts/kunanyi/g_lo_endpoint_first_products.pbs`;
- `tests/test_g_lo_endpoint_first_products_wrapper.py`.

The wrapper uses the accepted G-LO endpoint
`data.0050.flt.h5::Timestep_50`, with `data.0010.dbl.h5` and
`particles.5000.dbl` as endpoint-integrity guards. It runs direct-y projection
at `0 deg` and the refined `edge_overlap_uniform_cell_projection` at `45` and
`90 deg`. It then creates `g_lo_endpoint_projection_metrics.csv` and a
nine-row `three_case_endpoint_comparison.csv` using the accepted C-HI and C-LO
reference tables.

The archive is built from a stable explicit file-list snapshot and includes
product arrays, compact metrics, logs, manifests, and checksums. It excludes
raw production HDF5 and particle payloads.

## Validation

Local validation before staging:

```text
uv run pytest tests/test_g_lo_endpoint_first_products_wrapper.py \
  tests/test_c_lo_endpoint_first_products_wrapper.py \
  tests/test_xraise_grid_smoke_projection.py -q
16 passed in 0.89s

bash -n scripts/kunanyi/g_lo_endpoint_first_products.pbs
passed
```

The G-LO wrapper was developed red-first: all four focused tests initially
failed because the wrapper did not exist, then passed after implementation.

## Remote Preflight And Submission

Chrome/Open OnDemand enabled the TPAC jumpbox SSH window. Terminal-first
repo-local helpers then staged and verified:

```text
/u/bwbrook/codex_kunanyi/goal039_g_lo_endpoint_first_products/
```

Staged SHA-256 values matched local:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
e37bc185cbb6450effe5bad2b5f1b016b1e9731473101cfefbd5d4a4ceb69545  g_lo_endpoint_first_products.pbs
3f08990d50882043399b863c48e32ca695aafb9bec6c5f4b840ee7a634cce3a7  c_hi_refined_trio_context.csv
89900fd76d76ae6db1a90d8ee3d88d7749ecf19c60f507c79bb4836a5b8a486a  c_lo_endpoint_projection_metrics.csv
```

Remote wrapper syntax passed. The endpoint preflight verified
`data.0050.flt.h5::Timestep_50`, size `44,890,581,676` bytes, shape
`1014 x 960 x 960`, required datasets, and code time
`15330.069689399999`. C-HI and C-LO reference tables each contained the exact
`0/45/90 deg` view set.

Exactly one PBS job was submitted:

```text
job_id=756090.kunanyi-ohpc
Job_Name=g_lo_xprod
job_state=Q
queue=normal
qtime=Sun Jul 12 20:20:43 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime=04:00:00
```

## Expected Products

- analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-12-g-lo-endpoint-first-products`;
- archive:
  `/u/bwbrook/codex_kunanyi/goal039_g_lo_endpoint_first_products/g_lo_endpoint_first_products_2026-07-12.tar.gz`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal039_g_lo_endpoint_first_products/g_lo_endpoint_first_products.{out,err}`;
- view directories: `xraise_grid_0deg`, `xraise_grid_45deg`, and
  `xraise_grid_90deg`;
- comparison table: `three_case_endpoint_comparison.csv`.

## Status

`submitted_waiting_pbs_completion`

Decision label:
`G_LO_ENDPOINT_FIRST_PRODUCTS_AND_THREE_CASE_COMPARISON_SUBMITTED`.

The PBS stop rule is active. No polling occurred after queued verification.

## Boundary

No new production simulation, G-LO restart, source-age sweep, PRAiSE/radio,
cavity extraction, scientific-default change, commit, push, or raw-payload
retrieval occurred. Stop until Barry reports the PBS completion email or
explicitly authorizes a re-check.

## Completion Review

Barry reported PBS completion for `756090.kunanyi-ohpc` with `Exit_status=0`
and walltime `00:29:05`. One final qstat check found `job_state=F`,
`Stageout_status=1`, and the reported resource use. The scheduler stageout
caveat did not prevent direct stage-root retrieval.

Retrieved:

- archive SHA-256
  `149141739f6f8a631b94425230d5e824f6efc426c0ddc25dacd84aacb73e4e99`;
- 7.6 KB stdout with endpoint, three view, comparison, and finish markers;
- zero-byte stderr;
- final qstat record.

The archive contains 37 members. Its internal checksum manifest passed for all
files. The extracted review surface contains all three G-LO views, each with
finite metrics and `0/0/0` raw/corrected/correction-ratio empty columns. The
comparison contains exactly nine rows covering `C-HI`, `C-LO`, and `G-LO` at
`0/45/90 deg`.

Headline corrected-sum ratios to same-view C-HI:

```text
C-LO: 1.08783965, 0.96652664, 0.96652664
G-LO: 0.06194623, 0.04676664, 0.04676664
```

A local common-layout morphology figure was generated with deliberately
independent panel scaling and explicit ratio annotations. A focused
`sol_medium_scientist` direct-profile review completed cleanly and independently
recomputed the ratios. It classified the contrast as computationally credible
but not yet physically identified; total-map flux must not be substituted for
cavity deficit or feedback recovery.

The product bundle is 234 MB. Thirteen files exceed 5 MiB: the immutable
archive plus twelve parseable endpoint-review arrays. No raw HDF5 or particle
payload was retrieved.

Completion status: `complete_product`.

Decision label: `THREE_CASE_ENDPOINT_FIRST_PRODUCTS_COMPLETE`.

Recommended next goal: execute a three-case, multi-view endpoint
cavity-recovery and Level 1/2 truth-alignment analysis from existing outputs,
including common-aperture background, fractional deficits, tracer-threshold
sensitivity, and correction-method sensitivity. No further production run is
needed for that goal.
