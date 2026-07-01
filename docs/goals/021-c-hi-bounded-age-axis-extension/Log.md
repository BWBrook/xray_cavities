# Goal 021 Log - C-HI Bounded Age-Axis Extension

## 2026-07-01 Start

Goal authorized:

```text
Goal 021: bounded C-HI age-axis extension with two additional late source-age targets.
```

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git branch --show-current
main

git rev-parse --short HEAD
6de2880

git status --short --branch
## main...origin/main
```

Repo-local `AGENTS.md` was read first.

Boundary:

- work only inside `/Users/bwbrook/papers/xray_cavities` plus the required
  bounded Kunanyi Goal 021 staging/output paths if preflight passes;
- no `C-LO`, `G-LO`, comparison cases, early `5/10 Myr`, broad source-age
  sweep, endpoint rerun, PLUTO production, PRAiSE/radio/cavity regeneration,
  publication-facing claims, scientific-default changes, commits, pushes,
  cleanup, or `agent_comms` edits;
- do not substitute source ages if `output48` or `output50` preflight fails;
- if a PBS job is submitted and verified queued/running, wake X-ray Cavities
  and stop without polling or retrieval.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_late_source_age_pilot_consolidation_2026-07-01.md`
- `docs/goals/020-c-hi-late-source-age-pilot-consolidation/Log.md`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/per_age_view_comparison.csv`
- `scripts/kunanyi/c_hi_late_source_age_pilot.pbs`
- `tests/test_late_source_age_pilot_wrapper.py`
- `docs/goals/019-c-hi-late-source-age-pilot/Log.md`
- `docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_candidate_snapshots.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/proposed_sampling_plan.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/post_maintenance_run_contract.csv`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/runtime_resource_estimate.csv`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_trio_context.csv`

No sibling repos, external UTAS source checkouts, or remote files were read
during local preparation.

## Local Implementation

Added focused tests first:

```text
tests/test_late_age_axis_extension_wrapper.py
```

The initial TDD red run failed because the new wrapper file did not yet exist:

```text
uv run pytest tests/test_late_age_axis_extension_wrapper.py -q
6 failed
```

Added PBS wrapper:

```text
scripts/kunanyi/c_hi_late_age_axis_extension.pbs
```

The wrapper:

- preflights `data.0048.flt.h5::Timestep_48`,
  `data.0050.flt.h5::Timestep_50`, and endpoint-control
  `data.0051.flt.h5::Timestep_51`;
- processes only outputs `48` and `50`;
- writes compact `0deg`, `45deg`, and `90deg` X-ray/tracer products for each
  new source age;
- requires `edge_overlap_uniform_cell_projection` for `45deg` and `90deg`;
- validates finite positive X-ray metrics and projected-column support;
- archives from a stable snapshot plus explicit file list, reusing the repaired
  Goal 019 packaging contract.

The TDD green run passed:

```text
uv run pytest tests/test_late_age_axis_extension_wrapper.py -q
......                                                                   [100%]
6 passed
```

Remote stage planned:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension
```

Remote analysis root planned:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension
```

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
```

## Local Validation

Passed:

- focused pytest for source-age plan, refined projection, projection helper, and
  Goal 019/021 wrapper contracts;
- `bash -n scripts/kunanyi/c_hi_late_age_axis_extension.pbs`;
- `git diff --check`;
- targeted unresolved-marker scan over Goal 021 log/exchange/current status.

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_late_source_age_pilot_wrapper.py tests/test_late_age_axis_extension_wrapper.py -q
.....................                                                    [100%]
21 passed in 0.72s

bash -n scripts/kunanyi/c_hi_late_age_axis_extension.pbs
git diff --check
targeted unresolved-marker scan
```

## Remote Preflight / Submission

Status:

```text
submitted_waiting_pbs_completion
```

Chrome/Open OnDemand selector was refreshed through the authorized Chrome
route. The page reported:

```text
You have a 5.0 min window which closes at Wed Jul 1 11:45:51 2026 to ssh to <tpac-host>.
```

Helper smoke after selector refresh:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; date -u +%Y-%m-%dT%H:%M:%SZ'
<tpac-host>
/u/bwbrook
2026-07-01T01:41:08Z
__CODEX_STATUS__=0
```

Staged files:

```text
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/xraise_grid_smoke.py
/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_late_age_axis_extension.pbs
```

Remote staged hashes:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
6f96e26435fc25eeed726618932e0e2ebe35eae0b35411b9214dfd219592d526  c_hi_late_age_axis_extension.pbs
remote_hash_verification=passed
remote_bash_syntax=passed
```

Remote runtime inputs:

```text
4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5  /u/bwbrook/codex_kunanyi/xraise_runtime/xraise.py
e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3  /u/bwbrook/codex_kunanyi/xraise_runtime/apec_corrections.txt
64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747  /u/bwbrook/codex_kunanyi/xraise_runtime/gaunt_lut_2d.npz
```

Remote HDF5/input preflight passed:

```text
hdf5_preflight=passed output=48 timestep=Timestep_48 expected_myr=46.999852 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=14410.221814328825
hdf5_preflight=passed output=50 timestep=Timestep_50 expected_myr=48.999418 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=15023.29040598768
hdf5_preflight=passed output=51 timestep=Timestep_51 expected_myr=50.000000 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676 time_code=15330.069689399999
hdf5_shape_consistency=passed shape_nz_ny_nx=(1014, 960, 960)
remote_preflight=passed
```

PBS submission:

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

Expected output paths:

```text
stage=/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension
analysis_root=/scratch/bwbrook/xray_cavities_analysis/2026-07-01-c-hi-bounded-age-axis-extension
archive=/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
stdout=/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_late_age_axis_extension.out
stderr=/u/bwbrook/codex_kunanyi/goal021_c_hi_bounded_age_axis_extension/c_hi_late_age_axis_extension.err
```

Stop rule invoked: no polling, retrieval, finalizer, or packaging is authorized
until Barry reports the PBS completion email or X-ray Cavities explicitly asks
for a re-check.

## 2026-07-01 Completion Retrieval / Packaging

Barry reported the PBS completion email:

```text
PBS Job Id: 718233.kunanyi-ohpc
Job Name:   c_hi_ageext
Execution terminated
Exit_status=0
resources_used.cpupercent=98
resources_used.cput=00:38:08
resources_used.mem=1337596kb
resources_used.ncpus=1
resources_used.vmem=1770088kb
resources_used.walltime=00:52:48
```

Continuation boundary:

- retrieve/check/package only the already-completed Goal 021 job outputs;
- no new PBS submission, finalizer, HDF5/XRAiSE rerun, endpoint rerun,
  source-age substitution, early `5/10 Myr` branch, `C-LO`, `G-LO`,
  comparison-case processing, PLUTO/PRAiSE/radio/cavity work,
  scientific-default change, commit, push, cleanup, or `agent_comms` edit.

Repo-local `AGENTS.md` was read first for the continuation.

Final read-only remote completion evidence:

```text
Job Id: 718233.kunanyi-ohpc
    Job_Name = c_hi_ageext
    resources_used.cpupercent = 98
    resources_used.cput = 00:38:08
    resources_used.mem = 1337596kb
    resources_used.ncpus = 1
    resources_used.vmem = 1770088kb
    resources_used.walltime = 00:52:48
    job_state = F
    Stageout_status = 1
    Exit_status = 0
```

`Stageout_status = 1` is retained as a scheduler caveat. The stage archive,
stdout, and stderr were retrieved directly and validated locally.

Retrieved files:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_late_age_axis_extension.out
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_late_age_axis_extension.err
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/qstat_718233_excerpt.txt
```

Hashes:

```text
8147e945034df15510e831f85e0393c7b88c74cd8d70ae1fa16ca025b86e71e7  c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
24057dc3a96b92335234780e0777d42870daa956f71624d9224f1a363e06be4f  c_hi_late_age_axis_extension.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  c_hi_late_age_axis_extension.err
```

Archive readability:

```text
tar -tzf docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/remote_logs/c_hi_bounded_age_axis_extension_2026-07-01.tar.gz
passed
```

Stdout validation markers showed all six intended products passed:

```text
48/0deg  direct_y_axis_sum                       empty columns 0/0/0
48/45deg edge_overlap_uniform_cell_projection    empty columns 0/0/0
48/90deg edge_overlap_uniform_cell_projection    empty columns 0/0/0
50/0deg  direct_y_axis_sum                       empty columns 0/0/0
50/45deg edge_overlap_uniform_cell_projection    empty columns 0/0/0
50/90deg edge_overlap_uniform_cell_projection    empty columns 0/0/0
```

Created science note:

```text
docs/science/c_hi_bounded_age_axis_extension_2026-07-01.md
```

Created local review asset bundle:

```text
docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/
```

Machine-readable assets:

```text
per_age_view_comparison.csv
goal021_product_validation.csv
age_axis_trend_summary.csv
product_provenance.csv
next_step_recommendation.csv
bounded_age_axis_extension_metadata.json
```

Key packaged result:

- outputs `48` and `50` fill the late-axis gap between accepted `46/49` pilot
  context and endpoint `51`;
- all Goal 021 products are finite/positive with complete projected support;
- nonzero views use `edge_overlap_uniform_cell_projection`;
- corrected X-ray sums move smoothly toward the endpoint across
  `46 -> 48 -> 49 -> 50 -> 51` within each view.

Decision label:

```text
BOUNDED_LATE_AXIS_EXTENSION_COMPLETE_REVIEW_READY
```

Recommended next goal shape:

```text
local-only late age-axis consolidation/decision gate using outputs 46/48/49/50
plus endpoint 51 before any additional sampling or broadening.
```

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

Final status:

```text
complete_product_retrieved_and_packaged
```
