# 2026-07-01 - C-HI Bounded Age-Axis Extension

## Scope

Goal 021 prepares and, if all preflight checks pass, submits one bounded
post-processing PBS job for two additional final-production `C-HI` late
source-age targets:

- `data.0048.flt.h5::Timestep_48`, about `46.999852 Myr`;
- `data.0050.flt.h5::Timestep_50`, about `48.999418 Myr`.

The accepted endpoint control remains `output51`: Goal 005 `0deg`, Goal 016
refined `45deg` and `90deg`. The endpoint is preflighted for consistency but
not rerun by default.

## Evidence Read

- Current status and Goal 020 consolidation handoff.
- Goal 020 recommendation and per-age/per-view comparison assets.
- Goal 019 repaired wrapper/tests/logs for the stable archive contract.
- Goal 018 source-age sampling plan assets for source-age metadata and remote
  run contract.
- Goal 016/017 refined projection context for the endpoint/refined-viewing
  control surface.

## Local Changes

Added PBS wrapper:

```text
scripts/kunanyi/c_hi_late_age_axis_extension.pbs
```

Added focused wrapper tests:

```text
tests/test_late_age_axis_extension_wrapper.py
```

Added Goal log:

```text
docs/goals/021-c-hi-bounded-age-axis-extension/Log.md
```

## Wrapper Contract

The wrapper is post-processing only. It preflights:

- `data.0048.flt.h5::Timestep_48`
- `data.0050.flt.h5::Timestep_50`
- endpoint-control `data.0051.flt.h5::Timestep_51`

It processes only outputs `48` and `50`.

For each new source age it writes compact products:

- `0deg`: `direct_y_axis_sum`
- `45deg`: `edge_overlap_uniform_cell_projection`
- `90deg`: `edge_overlap_uniform_cell_projection`

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension
```

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
```

The archive is built from a stable snapshot plus explicit file list, not the
live analysis root.

## Local Validation

Focused local validation passed:

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_late_source_age_pilot_wrapper.py tests/test_late_age_axis_extension_wrapper.py -q
21 passed

bash -n scripts/kunanyi/c_hi_late_age_axis_extension.pbs
git diff --check
targeted unresolved-marker scan
```

## Remote Status

Status:

```text
submitted_waiting_pbs_completion
```

Chrome/Open OnDemand selector refresh:

```text
You have a 5.0 min window which closes at Wed Jul 1 11:45:51 2026 to ssh to <tpac-jumpbox>.
```

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension
```

Remote staged hashes and syntax:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
6f96e26435fc25eeed726618932e0e2ebe35eae0b35411b9214dfd219592d526  c_hi_late_age_axis_extension.pbs
remote_hash_verification=passed
remote_bash_syntax=passed
```

Remote preflight:

```text
hdf5_preflight=passed output=48 timestep=Timestep_48 expected_myr=46.999852 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=14410.221814328825
hdf5_preflight=passed output=50 timestep=Timestep_50 expected_myr=48.999418 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=15023.29040598768
hdf5_preflight=passed output=51 timestep=Timestep_51 expected_myr=50.000000 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=15330.069689399999
hdf5_shape_consistency=passed shape_nz_ny_nx=(1014, 960, 960)
remote_preflight=passed
```

PBS job submitted:

```text
pbs_job_id=718233.kunanyi-ohpc
Job_Name = c_hi_ageext
job_state = Q
queue = normal
qtime = Wed Jul  1 11:42:52 2026
Resource_List.mem = 96gb
Resource_List.ncpus = 1
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 04:00:00
```

Expected products:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0048_Timestep_48/xraise_grid_0deg
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0048_Timestep_48/xraise_grid_45deg
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0048_Timestep_48/xraise_grid_90deg
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0050_Timestep_50/xraise_grid_0deg
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0050_Timestep_50/xraise_grid_45deg
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension/output0050_Timestep_50/xraise_grid_90deg
```

Expected archive/stdout/stderr:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_late_age_axis_extension.out
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_late_age_axis_extension.err
```

Stop rule is active: do not poll, retrieve, finalizer-run, or package until
Barry reports the PBS completion email or X-ray Cavities explicitly asks for a
re-check.

## Completion Retrieval / Packaging

Barry reported the PBS completion email for job `718233.kunanyi-ohpc`
(`c_hi_ageext`) with `Exit_status=0` and walltime `00:52:48`.

Final read-only `qstat -x -f` evidence:

```text
Job_Name = c_hi_ageext
job_state = F
Exit_status = 0
Stageout_status = 1
resources_used.cpupercent = 98
resources_used.cput = 00:38:08
resources_used.mem = 1337596kb
resources_used.ncpus = 1
resources_used.vmem = 1770088kb
resources_used.walltime = 00:52:48
```

`Stageout_status=1` is kept as a scheduler caveat. The expected archive,
stdout, and empty stderr were retrieved directly from the Goal 021 stage.

Retrieved local files:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_late_age_axis_extension.out
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_late_age_axis_extension.err
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/qstat_718233_excerpt.txt
```

Archive SHA-256:

```text
8147e945034df15510e831f85e0393c7b88c74cd8d70ae1fa16ca025b86e71e7
```

Local review product:

```text
docs/science/c_hi_bounded_age_axis_extension_2026-07-01.md
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/
```

Machine-readable assets:

- `per_age_view_comparison.csv`
- `goal021_product_validation.csv`
- `age_axis_trend_summary.csv`
- `product_provenance.csv`
- `next_step_recommendation.csv`
- `bounded_age_axis_extension_metadata.json`

Headline result:

- all six Goal 021 products (`48/0deg`, `48/45deg`, `48/90deg`,
  `50/0deg`, `50/45deg`, `50/90deg`) are present and validated;
- nonzero views use `edge_overlap_uniform_cell_projection`;
- raw/corrected/correction-ratio empty projected columns are `0/0/0` for every
  Goal 021 product;
- the new rows fill the late-axis surface between accepted `46/49` pilot
  context and endpoint `51`.

Recommendation:

```text
local-only late age-axis consolidation/decision gate using outputs 46/48/49/50
plus endpoint 51 before any additional sampling or broadening.
```

Boundary confirmation:

No new PBS job, finalizer, HDF5/XRAiSE rerun, endpoint rerun, source-age
substitution, early-age branch, `C-LO`, `G-LO`, comparison-case processing,
PLUTO/PRAiSE/radio/cavity work, scientific-default change, commit, push,
cleanup, or `agent_comms` edit occurred during retrieval and packaging.

## Final Local Validation

Passed:

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_late_source_age_pilot_wrapper.py tests/test_late_age_axis_extension_wrapper.py -q
21 passed in 0.67s

bash -n scripts/kunanyi/c_hi_late_age_axis_extension.pbs
passed

python3 -m json.tool docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/bounded_age_axis_extension_metadata.json
passed

tar -tzf docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
passed

CSV parse / expected-column / nonempty checks
passed

git diff --check
passed

targeted unresolved-marker scan over the science note, Goal log, exchange log,
and current status
passed
```
