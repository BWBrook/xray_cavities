# Log: Goal 016 C-HI Refined Projection Viewing Rerun

## 2026-06-25 - start state

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
bd161e6

git fetch --prune origin
<no output>

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
bd161e6
```

Repo-local `AGENTS.md` was read before project work. The worktree was clean at
start and no fast-forward was needed.

## 2026-06-25 - evidence and code read

Read scoped, repo-local evidence/code:

- `docs/exchange/current_status.md`
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/goals/015-c-hi-projection-bin-refinement/Log.md`
- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/synthetic_occupancy_comparison.csv`
- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/method_comparison.csv`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv`
- `scripts/science/xraise_grid_smoke.py`
- `scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs`
- `scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs`
- `scripts/kunanyi/run_on_kunanyi.sh`
- `scripts/kunanyi/copy_to_kunanyi.sh`
- Goal 011 and Goal 012 notes/assets only enough to preserve context and avoid
  touching accepted historical products

Key evidence:

- Goal 015 refined `xraise_grid_smoke.py` to use
  `edge_overlap_uniform_cell_projection` for nonzero projected views.
- Goal 015 synthetic proof moved the near-90 stretched-grid old center-bin
  failure from `18/24` empty bins to `0/24`, with conservation error `0`.
- Goal 014 identified the accepted Goal 012 `90 deg` striping as a local
  projection/binning occupancy issue.
- Prior Goal 011/012 single-view post-processing jobs completed in about
  17 minutes each.

## 2026-06-25 - wrapper prepared

Created:

```text
scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
```

Wrapper choices:

- job name: `c_hi_xrefprj`
- queue: `normal`
- resources: `select=1:ncpus=1:mpiprocs=1:mem=96gb`
- walltime: `04:00:00`
- required product: final `C-HI`, `90 deg`, refined X-ray/tracer
- included sanity product: final `C-HI`, `45 deg`, refined X-ray/tracer
- input HDF5:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`
- timestep: `Timestep_51`
- remote stage:
  `/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun`
- remote analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun`
- expected archive:
  `/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/refined_projection_viewing_rerun_2026-06-25.tar.gz`

Maintenance-window judgment: including both `90 deg` and `45 deg` remains
small/bounded and compatible with the Friday 2026-06-26 09:00 Kunanyi outage if
the job starts promptly.

## 2026-06-25 - local validation

Local validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py tests/test_90deg_xray_striping_diagnostic.py -q
7 passed

bash -n scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
<no output>

git diff --check
<no output>
```

## 2026-06-25 - remote staging and submission

Access route:

```text
Chrome/Open OnDemand Enable SSH page
You have a 5.0 min window which closes at Thu Jun 25 13:11:02 2026 to ssh to <tpac-host>.
```

Staged files:

```text
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/xraise_grid_smoke.py
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/c_hi_refined_projection_viewing_rerun.pbs
```

Local and remote SHA-256 values matched:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
eb0f83c82e355de88ef20ae348b4a8f553026a83e8ebdca6a244b95e736bcbb7  c_hi_refined_projection_viewing_rerun.pbs
```

Remote syntax validation:

```text
cd /u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun
bash -n c_hi_refined_projection_viewing_rerun.pbs
<no output>
```

Submitted exactly one bounded PBS job:

```text
SUBMITTED_JOB_ID=700044.kunanyi-ohpc
Job Id: 700044.kunanyi-ohpc
    Job_Name = c_hi_xrefprj
    job_state = Q
    queue = normal
    ctime = Thu Jun 25 13:06:42 2026
    Resource_List.mem = 96gb
    Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
    Resource_List.walltime = 04:00:00
```

Final phase status:

```text
submitted_waiting_pbs_completion
```

Stop rule invoked: the job was submitted and verified queued. No polling after
queued verification.

## 2026-06-25 - boundary confirmation

No remote retrieval/package is authorized until Barry reports the PBS
completion email or X-ray Cavities explicitly authorizes a re-check.

No PLUTO production, source-age sampling, `C-LO`, `G-LO`, comparison-case
processing, PRAiSE/radio/cavity regeneration, scientific-default changes,
commits, pushes, `agent_comms` changes, or Stas/Patrick escalation occurred.

## 2026-06-25 - retrieval start state

Barry reported the PBS completion email for `700044.kunanyi-ohpc`:

```text
PBS Job Id: 700044.kunanyi-ohpc
Job Name:   c_hi_xrefprj
Execution terminated
Exit_status=0
resources_used.cpupercent=94
resources_used.cput=00:17:40
resources_used.mem=1362356kb
resources_used.ncpus=1
resources_used.vmem=1770972kb
resources_used.walltime=00:22:01
```

Continuation start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main
 M docs/exchange/current_status.md
?? docs/exchange/logs/2026-06-25-c-hi-refined-projection-viewing-rerun.md
?? docs/goals/016-c-hi-refined-projection-viewing-rerun/
?? scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs

git rev-parse --short HEAD
bd161e6
```

Repo-local `AGENTS.md` was read fresh for the continuation.

## 2026-06-25 - remote completion evidence and retrieval

Allowed final remote evidence check:

```text
qstat -x -f 700044.kunanyi-ohpc
Job_Name = c_hi_xrefprj
resources_used.cpupercent = 94
resources_used.cput = 00:17:40
resources_used.mem = 1362356kb
resources_used.ncpus = 1
resources_used.vmem = 1770972kb
resources_used.walltime = 00:22:01
job_state = F
queue = normal
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 04:00:00
Exit_status = 0
```

Retrieved only the completed archive/stdout/stderr from:

```text
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/
```

Local retrieval targets:

```text
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/refined_projection_viewing_rerun_2026-06-25.tar.gz
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/c_hi_refined_projection_viewing_rerun.out
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/c_hi_refined_projection_viewing_rerun.err
```

Local SHA-256 values:

```text
363b942f93908a342141d88220f30e5c2585bde74679e57322beb751e15dbf77  refined_projection_viewing_rerun_2026-06-25.tar.gz
925c9e932dd1da5357a55b5be23ff8022f243dab8a50b5fd3034b018ced8d090  c_hi_refined_projection_viewing_rerun.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  c_hi_refined_projection_viewing_rerun.err
```

Remote stderr is zero bytes. No Chrome selector refresh was needed in this
continuation because the repo-local helper route worked.

## 2026-06-25 - package builder and assets

Created:

```text
scripts/science/build_refined_projection_viewing_rerun.py
tests/test_refined_projection_viewing_rerun.py
docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/
```

Updated `.gitattributes` so the new fetched asset bundle is preserved
byte-for-byte like the accepted Goal 011/012 bundles.

Package builder output:

```text
status=complete_product
result_label=REFINED_PROJECTION_FIXES_EMPTY_COLUMN_FAILURE
archive_sha256=363b942f93908a342141d88220f30e5c2585bde74679e57322beb751e15dbf77
stderr_bytes=0
```

Machine-readable package assets:

```text
refined_projection_metrics.csv
empty_column_before_after.csv
refined_vs_accepted_xray_summary.csv
product_provenance.csv
refined_projection_viewing_rerun_metadata.json
```

The full-size remote TSV products were inspected from the fetched archive and
used to derive compact evidence, but unpacked TSVs were not retained in the
repo asset bundle.

## 2026-06-25 - refined-versus-historical review

Remote stdout records:

```text
hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960) time_code=15330.069689399999
xray_90deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]
xray_45deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]
finished_utc=2026-06-25T03:28:43Z
```

Accepted versus refined empty columns:

```text
90deg raw/corrected/correction-ratio: 400/960 -> 0/960
45deg raw/corrected/correction-ratio: 22/960 -> 0/960
```

Scalar checks:

```text
90deg raw_xray_sum relative delta = 6.31e-16
90deg corrected_xray_sum relative delta = 5.88e-16
90deg correction_ratio_positive_sum relative delta = 0.712242
45deg raw_xray_sum relative delta = 0
45deg corrected_xray_sum relative delta = -1.33e-15
45deg correction_ratio_positive_sum relative delta = 0.023463
```

Interpretation: the Goal 015 accumulator fixes the Goal 012 90-degree
empty-bin/striping artifact on the real final `C-HI` endpoint while preserving
raw/corrected X-ray pixel sums to roundoff. The correction-ratio positive sum
increase is expected because previously empty projected columns become
positive cells.

## 2026-06-25 - retrieval/package validation

Validation run:

```text
uv run pytest tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_90deg_xray_striping_diagnostic.py -q
10 passed

bash -n scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
<no output>

uv run python -m json.tool docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_viewing_rerun_metadata.json
<valid JSON>

CSV parse/expected-column checks
passed

git diff --check
<no output>

targeted unresolved-marker scan
<no output>
```

## 2026-06-25 - final status

Goal 016 status:

```text
complete_product
```

Recommended next action: review/accept Goal 016, then write a narrow Goal 017
that either packages reviewer-facing refined 45/90 figures/trio context or
proceeds to tightly bounded `C-HI` source-age sampling using the refined
projection method. Do not open a broad batch by implication.

No new PBS job was submitted in the retrieval/package phase. No finalizer,
PLUTO production, source-age sampling, `C-LO`, `G-LO`, comparison-case
processing, PRAiSE/radio/cavity regeneration, scientific-default changes,
commits, pushes, `agent_comms` changes, Stas/Patrick escalation, or accepted
Goal 011/012 asset overwrites occurred.
