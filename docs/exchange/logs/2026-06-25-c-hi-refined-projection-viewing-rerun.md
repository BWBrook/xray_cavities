# C-HI Refined Projection Viewing Rerun

Date: 2026-06-25
Agent: `jet`
Goal: `016-c-hi-refined-projection-viewing-rerun`
Status: `complete_product`

## Summary

Prepared, submitted, retrieved, and packaged a bounded Kunanyi
post-processing rerun for the accepted final `C-HI` HDF5 endpoint using the
Goal 015 refined projected-bin accumulator.

The run includes:

- required final `C-HI`, `90 deg` refined X-ray/tracer rerun; and
- final `C-HI`, `45 deg` refined sanity rerun in the same bounded job.

Decision label:

```text
REFINED_PROJECTION_FIXES_EMPTY_COLUMN_FAILURE
```

The refined products fix the Goal 012 90-degree X-ray empty-column artifact:
raw, corrected, and correction-ratio X-ray layers improve from `400/960`
all-zero projected columns to `0/960`. The `45 deg` sanity rerun improves from
`22/960` to `0/960`.

## Evidence Read

- `AGENTS.md`
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
- Goal 011/012 notes/assets only enough to preserve historical context and
  avoid overwriting accepted products

## Files Created Or Updated

- `.gitattributes`
- `scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs`
- `scripts/science/build_refined_projection_viewing_rerun.py`
- `tests/test_refined_projection_viewing_rerun.py`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/`
- `docs/exchange/logs/2026-06-25-c-hi-refined-projection-viewing-rerun.md`
- `docs/goals/016-c-hi-refined-projection-viewing-rerun/Log.md`
- `docs/exchange/current_status.md`

## Wrapper

Local wrapper:

```text
scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
```

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun
```

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun/refined_projection_viewing_rerun_2026-06-25.tar.gz
```

Expected refined product directories:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun/xraise_grid_90deg_refined
/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun/xraise_grid_45deg_refined
```

## Local Validation

Local validation before staging/submission:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py tests/test_90deg_xray_striping_diagnostic.py -q
7 passed

bash -n scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs
<no output>

git diff --check
<no output>
```

## Remote Submission

Chrome/Open OnDemand access route:

```text
https://<tpac-portal>/pun/sys/enable_ssh/
Enable SSH page reported:
You have a 5.0 min window which closes at Thu Jun 25 13:11:02 2026 to ssh to <tpac-jumpbox>.
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

Remote wrapper syntax validation passed:

```text
cd /u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun
bash -n c_hi_refined_projection_viewing_rerun.pbs
<no output>
```

PBS submission:

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

Stop rule invoked: the job was submitted and verified queued. Do not poll.

## Remote Completion And Retrieval

Barry reported the PBS completion email for:

```text
PBS Job Id: 700044.kunanyi-ohpc
Job Name:   c_hi_xrefprj
Exit_status=0
resources_used.cpupercent=94
resources_used.cput=00:17:40
resources_used.mem=1362356kb
resources_used.ncpus=1
resources_used.vmem=1770972kb
resources_used.walltime=00:22:01
```

Allowed final remote evidence check:

```text
qstat -x -f 700044.kunanyi-ohpc
job_state = F
Exit_status = 0
resources_used.walltime = 00:22:01
```

Retrieved from:

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

Remote stderr is zero bytes.

Remote stdout records:

```text
hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960) time_code=15330.069689399999
xray_90deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]
xray_45deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]
finished_utc=2026-06-25T03:28:43Z
```

## Local Package

Science note:

```text
docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md
```

Compact asset bundle:

```text
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/
```

Machine-readable package outputs:

```text
refined_projection_metrics.csv
empty_column_before_after.csv
refined_vs_accepted_xray_summary.csv
product_provenance.csv
refined_projection_viewing_rerun_metadata.json
```

The fetched archive/stdout/stderr are retained under `remote_logs/`; unpacked
full-size TSV products are not retained in the repo bundle.

## Refined-Versus-Historical Result

Empty-column repair:

| View | Layer | Accepted | Refined |
| --- | --- | ---: | ---: |
| `90 deg` | raw X-ray | `400/960` | `0/960` |
| `90 deg` | corrected X-ray | `400/960` | `0/960` |
| `90 deg` | correction ratio | `400/960` | `0/960` |
| `45 deg` | raw X-ray | `22/960` | `0/960` |
| `45 deg` | corrected X-ray | `22/960` | `0/960` |
| `45 deg` | correction ratio | `22/960` | `0/960` |

Scalar checks:

- `90 deg` raw/corrected X-ray sums conserved to relative deltas
  `6.31e-16` and `5.88e-16`.
- `45 deg` raw/corrected X-ray sums conserved to relative deltas `0` and
  `-1.33e-15`.
- `90 deg` correction-ratio positive sum increased by `0.712242`.
- `45 deg` correction-ratio positive sum increased by `0.023463`.

Interpretation: the Goal 015 accumulator fixes the real Goal 012 empty-bin
artifact while preserving X-ray pixel sums to roundoff.

## Retrieval/Package Validation

Validation run after retrieval/package:

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

## Boundaries

Accepted Goal 011/012 assets must remain historical and were not overwritten.

No new PBS job was submitted in the retrieval/package phase. No finalizer,
PLUTO production, source-age sampling, `C-LO`, `G-LO`, comparison-case
processing, PRAiSE/radio/cavity regeneration, scientific-default changes,
commits, pushes, `agent_comms` changes, or Stas/Patrick escalation occurred.

Recommended next action: review/accept Goal 016, then choose a narrow Goal 017
that either packages reviewer-facing refined 45/90 figures/trio context or
proceeds to tightly bounded `C-HI` source-age sampling using the refined
projection method.
