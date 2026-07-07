# Goal 036 Log - C-LO Endpoint First Products

Date: 2026-07-07

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `17e148a`.
- Initial git status: `## main...origin/main`.
- Fast-forward: `git pull --ff-only` reported `Already up to date`.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 036 authorizes bounded C-LO endpoint post-processing from the accepted
Goal 035 endpoint run root if endpoint/input/runtime preflight passes. It does
not authorize G-LO, new PLUTO production, a C-LO continuation/restart job,
source-age sampling, broad batches, scientific-default changes, bulky local
payload retrieval, commits, pushes, cleanup, Stas/Patrick contact, or
`agent_comms` edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 035 completion science note/assets/log:
  `docs/science/c_lo_endpoint_oriented_continuation_completion_2026-07-07.md`,
  `completion_summary.csv`, `run_output_inventory.csv`, and metadata.
- C-HI refined endpoint control surface:
  `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_trio_context.csv`.
- Existing post-processing wrapper patterns:
  `scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs` and
  `scripts/kunanyi/c_hi_late_age_axis_extension.pbs`.
- Product helper:
  `scripts/science/xraise_grid_smoke.py`.

## Local Implementation

Added focused wrapper contract tests:

```text
tests/test_c_lo_endpoint_first_products_wrapper.py
```

Added the composite C-LO endpoint product wrapper:

```text
scripts/kunanyi/c_lo_endpoint_first_products.pbs
```

The wrapper:

- targets the accepted Goal 035 C-LO endpoint run root;
- validates `data.0053.flt.h5::Timestep_53` and endpoint catalogue surfaces;
- runs `xraise_grid_smoke.py` for `0deg`, `45deg`, and `90deg`;
- requires `edge_overlap_uniform_cell_projection` for nonzero views;
- writes C-LO projection metrics and a first C-HI/C-LO scalar comparison table;
- archives from a stable snapshot/file-list contract, not the live analysis
  root.

## Local Validation

Red test was confirmed first:

```text
uv run pytest tests/test_c_lo_endpoint_first_products_wrapper.py -q
```

The initial run failed because the wrapper did not exist.

After implementation:

```text
uv run pytest tests/test_c_lo_endpoint_first_products_wrapper.py -q
```

passed with `6 passed`.

Wrapper syntax:

```text
bash -n scripts/kunanyi/c_lo_endpoint_first_products.pbs
```

passed.

## Remote Access And Staging

The first repo-local helper attempt reported the TPAC MFA selector had expired.
The authorized Chrome/Open OnDemand route was used only to enable the
five-minute jumpbox SSH window. The page reported a live window closing at
`Tue Jul 7 11:39:42 2026`. Safari was not used.

The repo-local terminal helper then succeeded:

```text
<tpac-host>
/u/bwbrook
2026-07-07T01:35:17Z
```

Remote stage root:

```text
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products
```

Staged files:

- `c_lo_endpoint_first_products.pbs`
- `xraise_grid_smoke.py`
- `c_hi_refined_trio_context.csv`

Final staged SHA-256 checks:

- wrapper:
  `33b64132f78698cdbf679b39f823e0cecefa36dcf2081f89f3ac3a799518dcfc`;
- XRAiSE helper:
  `a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c`;
- C-HI reference:
  `3f08990d50882043399b863c48e32ca695aafb9bec6c5f4b840ee7a634cce3a7`.

Remote runtime inputs were readable:

- `xraise.py`:
  `4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5`;
- APEC corrections:
  `e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3`;
- Gaunt LUT:
  `64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747`.

Remote wrapper `bash -n` passed.

## Endpoint Preflight

Endpoint run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles
```

Remote read-only checks passed:

- `markers/DONE` present;
- `markers/FAILED` absent;
- `data.0013.dbl.h5` readable;
- `data.0053.flt.h5` readable;
- `particles.5003.dbl` readable;
- `dbl.h5.out`, `flt.h5.out`, `restart.out`, and `grid.out` readable under
  `problem/outputs`;
- `data.0053.flt.h5::Timestep_53` contains `rho`, `prs`, `tr1`, `vx1`, `vx2`,
  and `vx3`;
- all required datasets share shape `(1014, 960, 960)`;
- endpoint HDF5 time is `15330.069689399999`, matching the configured target
  `15330.06968940`.

One implementation mismatch was found before submission: the wrapper originally
looked for `restart.out` and `grid.out` under `problem/`, while the accepted
Goal 035 endpoint has them under `problem/outputs/`. The wrapper was patched,
the focused tests still passed, and the updated wrapper was restaged.

## Submission

Exactly one bounded PBS post-processing job was submitted:

```text
job id: 751098.kunanyi-ohpc
job name: c_lo_xprod
queue/state at stop: normal / Q
resources: select=1:ncpus=1:mpiprocs=1:mem=96gb
walltime: 04:00:00
```

Expected outputs after completion:

```text
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products/c_lo_endpoint_first_products_2026-07-07.tar.gz
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products/c_lo_endpoint_first_products.out
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products/c_lo_endpoint_first_products.err
/u/bwbrook/codex_kunanyi/goal036_c_lo_endpoint_first_products/remote_logs/
/scratch/bwbrook/xray_cavities_analysis/2026-07-07-c-lo-endpoint-first-products
```

The PBS stop rule was invoked immediately after qstat showed `Q`. No polling or
retrieval was performed after queued verification.

## Completion Retrieval

Status:
`complete_product`.

Decision label:
`C_LO_ENDPOINT_FIRST_PRODUCTS_COMPLETE_COMPACT_COMPARISON_READY`.

Barry reported the PBS completion email for `751098.kunanyi-ohpc` with
`Exit_status=0`. The authorized Chrome/Open OnDemand selector was refreshed
when the repo-local helper reported an expired MFA window; Safari was not used.

Final scheduler evidence was retrieved to:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/remote_logs/qstat_final_2026-07-07.txt
```

Key qstat fields:

- `Job_Name = c_lo_xprod`;
- `job_state = F`;
- `Exit_status = 0`;
- `resources_used.walltime = 00:27:19`;
- `resources_used.cput = 00:17:39`;
- `resources_used.mem = 1144972kb`;
- `resources_used.ncpus = 1`;
- `resources_used.vmem = 1709232kb`;
- `Stageout_status = 1`.

The stageout status is retained as a scheduler caveat. The requested stage-root
archive/stdout/stderr and remote logs were present and retrieved.

Retrieved compact files:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/c_lo_endpoint_first_products_2026-07-07.tar.gz
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/c_lo_endpoint_first_products.out
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/c_lo_endpoint_first_products.err
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/remote_logs/
```

Archive SHA-256:

```text
041eed367d0b74e5bbfbfd3d2ca1e9b51c0eb24b90c7fdd32c36a8bec95646c1
```

The archive was readable with `tar -tzf`. A schema-clean local review copy was
prepared at:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/
```

The original remote archive is retained unchanged under `remote_logs/` as
byte-for-byte provenance.

## Product Validation

The archive contains the expected compact C-LO endpoint products:

- `xraise_grid_0deg`;
- `xraise_grid_45deg`;
- `xraise_grid_90deg`;
- `c_lo_endpoint_preflight.csv`;
- `c_lo_endpoint_projection_metrics.csv`;
- `c_hi_c_lo_endpoint_comparison.csv`;
- `c_lo_product_provenance.csv`;
- `c_lo_endpoint_first_products_caveats.csv`.

Product checks:

- endpoint preflight rows passed `12/12`;
- stdout contains three `xray_validation=passed` markers and `finished_utc`;
- stderr is empty;
- `0deg` uses `direct_y_axis_sum`;
- `45deg` and `90deg` use `edge_overlap_uniform_cell_projection`;
- all raw, corrected, and correction-ratio layers have `0/960` empty projected
  columns;
- no `.h5`, `data.*`, or `particles.*` payload files were copied into the
  local Goal 036 asset bundle.

Package/schema review iteration:

- the original remote archive's `c_lo_endpoint_projection_metrics.csv` had a
  duplicate `time_myr` header;
- the local review copy now keeps the first `time_myr` column and drops the
  duplicate copy, with values otherwise unchanged;
- `schema_repair_manifest.csv` records the archive-original caveat and local
  review-copy repair;
- the wrapper was patched to remove the duplicate source of `time_myr` and to
  fail fast if projection metric columns are not unique;
- focused tests now check the wrapper metric schema and all Goal 036 CSV review
  surfaces for duplicate headers.

Large-file policy:

- `large_file_inventory.csv` records `13` files above `5 MiB`;
- these are the retrieved `39.419 MiB` archive plus twelve `15.782 MiB` TSV
  endpoint-review arrays;
- the TSV arrays are retained as compact parseable 2-D review payloads for the
  first C-LO endpoint maps, not as bulky HDF5/PLUTO `data.*`/particle outputs;
- every retained file is below `100 MiB`.

Headline C-LO corrected X-ray sums:

- `0deg`: `3494804623.455285`;
- `45deg`: `1385987160.135606`;
- `90deg`: `1960081839.138744`.

First-pass C-LO/C-HI corrected X-ray sum ratios:

- `0deg`: `1.087839647658863`;
- `45deg`: `0.9665266425113752`;
- `90deg`: `0.9665266425113748`.

Completion assets added:

- `completion_summary.csv`;
- `retrieved_archive_manifest.csv`;
- `product_validation_summary.csv`;
- `headline_c_hi_c_lo_comparison.csv`;
- `large_file_inventory.csv`;
- `schema_repair_manifest.csv`;
- `local_completion_asset_manifest.sha256`.

## Review Iteration Validation

The package/schema hardening review iteration stayed local-only. No PBS,
remote polling, remote product rerun, PLUTO, XRAiSE rerun, G-LO, source-age
work, scientific-default change, or accepted-asset overwrite occurred.

Validation commands:

```text
uv run pytest tests/test_c_lo_endpoint_first_products_wrapper.py tests/test_xraise_grid_smoke_projection.py -q
```

passed with `12 passed`.

```text
bash -n scripts/kunanyi/c_lo_endpoint_first_products.pbs
```

passed.

```text
uv run python -m json.tool docs/science/assets/c_lo_endpoint_first_products_2026-07-07/c_lo_endpoint_first_products_metadata.json
```

passed.

CSV parse, expected-column, nonempty, and duplicate-header checks passed across
`18` Goal 036 CSV review surfaces. The large-file inventory check passed with
`13` files above `5 MiB`, all below `100 MiB` and all either TSV endpoint
review arrays or the retained remote archive.

```text
tar -tzf docs/science/assets/c_lo_endpoint_first_products_2026-07-07/remote_logs/c_lo_endpoint_first_products_2026-07-07.tar.gz
```

passed with `38` members.

The no-bulky-payload guard found no `.h5`, `data.*`, or `particles.*` files in
the local Goal 036 asset bundle.

```text
git diff --check
```

passed.

Targeted unresolved/stale-label scans over the Goal 036 note, exchange log,
Goal log, metadata, and top current-status section found no unresolved markers
or stale submitted-waiting Goal 036 status. The only
`2026-07-07-c-lo-endpoint-first-products` matches in CSV assets are expected
remote analysis-root paths in `expected_products.csv`.

Recommendation:
review and accept Goal 036 as the first compact C-LO endpoint product surface,
then choose either a bounded C-HI/C-LO endpoint interpretation packet or the
next G-LO readiness/execution branch.
