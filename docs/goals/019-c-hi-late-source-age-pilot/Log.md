# Log: Goal 019 C-HI Late Source-Age Pilot

## Start

Goal authorized:

```text
Goal 019: post-maintenance bounded C-HI late-source-age pilot preflight and submission.
```

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
63f980e
```

Fast-forward check:

```text
git fetch --prune origin
git merge --ff-only origin/main
Already up to date.
```

Repo-local `AGENTS.md` was read first.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_source_age_sampling_plan_2026-06-25.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/`
- `docs/goals/018-c-hi-source-age-sampling-plan/Log.md`
- Goal 016/017 notes/assets/logs sufficient to preserve the refined-projection
  and endpoint-control contracts
- `agent_comms/threads/2026-06-23-c-hi-viewing-angle-trio-next-step.md`
- `agent_comms/requests/open_questions.md`
- `scripts/kunanyi/c_hi_refined_projection_viewing_rerun.pbs`
- `scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs`
- `scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs`
- `scripts/science/xraise_grid_smoke.py`
- `tests/test_xraise_grid_smoke_projection.py`

Context captured:

- Patrick-agent `Q-019` is answered: the old `90 deg` striping was a blocker,
  but the later refined projection rerun addressed the method step for planning.
- Stas-agent `Q-018` remains open/useful context, but Goal 019 is a narrow
  bounded post-processing pilot already authorized by X-ray Cavities/Barry.

## Local Deliverables

Added PBS wrapper:

```text
scripts/kunanyi/c_hi_late_source_age_pilot.pbs
```

Added wrapper contract tests:

```text
tests/test_late_source_age_pilot_wrapper.py
```

Planned exchange log:

```text
docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md
```

## Wrapper Contract

The wrapper is post-processing only. It preflights `prod64` HDF5 products:

- `data.0046.flt.h5::Timestep_46`
- `data.0049.flt.h5::Timestep_49`
- endpoint-control check only: `data.0051.flt.h5::Timestep_51`

It processes only the two new source ages, outputs `46` and `49`.

For each new source age it writes compact projection products:

- `0 deg`: `direct_y_axis_sum`
- `45 deg`: `edge_overlap_uniform_cell_projection`
- `90 deg`: `edge_overlap_uniform_cell_projection`

The endpoint control is reused from accepted Goal 005/016 products and is not
rerun by default.

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot
```

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

## Local Validation

Focused tests:

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_late_source_age_pilot_wrapper.py -q
.............                                                            [100%]
13 passed in 0.34s
```

PBS syntax:

```text
bash -n scripts/kunanyi/c_hi_late_source_age_pilot.pbs
```

Whitespace:

```text
git diff --check
```

Both syntax and whitespace checks passed.

Targeted unresolved-marker scan over the Goal 019 log, exchange log, and
`current_status.md` passed with no matches.

## Remote Preflight / Submission

Status:

```text
blocked_preflight
```

Chrome/Open OnDemand selector evidence:

```text
Enable SSH page reached at https://<tpac-host>/pun/sys/enable_ssh/
Visible status: You have a 5.0 min window which closes at Tue Jun 30 20:52:23 2026 to ssh to <tpac-host>.
```

Terminal helper smoke attempted:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; date -u +%Y-%m-%dT%H:%M:%SZ'
```

Result:

```text
jumpbox access succeeded, but inner ssh to kunanyi failed before command execution
```

Blocker text:

```text
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@    WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!     @
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
The fingerprint for the ED25519 key sent by the remote host is
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI.
Offending ECDSA key in /u/bwbrook/.ssh/known_hosts:2
remove with:
ssh-keygen -f "/u/bwbrook/.ssh/known_hosts" -R "kunanyi"
Host key for kunanyi has changed and you have requested strict checking.
Host key verification failed.
```

No remote preflight checks reached Kunanyi. No files were staged and no PBS job
was submitted.

I did not remove or edit `/u/bwbrook/.ssh/known_hosts`, and I did not bypass
host-key verification. That operational repair is outside the Goal 019
submission boundary unless X-ray Cavities explicitly authorizes it after
reviewing the post-maintenance host-key change.

The stuck local helper/expect/SSH process tree from the failed attempt was
terminated locally. No cleanup was performed on remote systems.

## Authorized Host-Key Repair / Submission Continuation

X-ray Cavities/Barry accepted the post-maintenance Kunanyi ED25519 fingerprint
and authorized a narrow operational host-key repair:

```text
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI
```

Host-key repair evidence:

```text
jumpbox scanned ED25519 fingerprint:
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI

jumpbox backup:
/u/bwbrook/.ssh/known_hosts.goal019_pre_kunanyi_repair_20260630T105724Z
backup SHA-256:
90c638295e8e9c9461177e954b75fa27f1709087d58e5ab8cd73c030e5c72aa1

local scanned ED25519 fingerprint through jumpbox:
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI

local backup:
/Users/bwbrook/.ssh/known_hosts.goal019_pre_kunanyi_repair_20260630T105949Z
backup SHA-256:
03287b5ee2099f789222346b05f7f5e08331a998630ab09d315b87a560a5a8ba
```

Only stale `kunanyi` host-key entries were removed and replaced after the
fingerprint matched the accepted value. No `StrictHostKeyChecking=no`,
`UserKnownHostsFile=/dev/null`, or equivalent bypass was used.

Helper smoke after repair:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; date -u +%Y-%m-%dT%H:%M:%SZ'
<tpac-host>
/u/bwbrook
2026-06-30T10:57:37Z
__CODEX_STATUS__=0
```

Chrome/Open OnDemand selector was refreshed once for the local `scp`
known-host repair and staging path:

```text
Visible status: You have a 5.0 min window which closes at Tue Jun 30 21:04:18 2026 to ssh to <tpac-host>.
```

Staged files:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/xraise_grid_smoke.py
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot.pbs
```

Remote staged hashes:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
468aeaaa07e05a2cc077c089ab9999dced8dd9490a31bd63cfe6a8a2463e5550  c_hi_late_source_age_pilot.pbs
remote_hash_verification=passed
remote_bash_syntax=passed
```

Remote runtime inputs:

```text
4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5  /u/bwbrook/codex_kunanyi/xraise_runtime/xraise.py
e0f53a9f276a956f347af0e4fe627ee152762abc8b5116fc458070ee5f0925e3  /u/bwbrook/codex_kunanyi/xraise_runtime/apec_corrections.txt
64df88d39896f14064bb799fd5b70c6f68d20bcbdc5a15d19e2e4fd15b22f747  /u/bwbrook/codex_kunanyi/xraise_runtime/gaunt_lut_2d.npz
```

Remote HDF5 preflight passed:

```text
hdf5_preflight=passed output=46 timestep=Timestep_46 expected_myr=44.999274 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676
hdf5_preflight=passed output=49 timestep=Timestep_49 expected_myr=47.999129 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676
hdf5_preflight=passed output=51 timestep=Timestep_51 expected_myr=50.000000 shape_nz_ny_nx=(1014, 960, 960) size_bytes=44890581676
hdf5_shape_consistency=passed shape_nz_ny_nx=(1014, 960, 960)
remote_preflight=passed
```

PBS submission:

```text
pbs_job_id=706130.kunanyi-ohpc
Job_Name = c_hi_lsapil
job_state = Q
queue = normal
Resource_List.mem = 96gb
Resource_List.ncpus = 1
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 04:00:00
qtime = Tue Jun 30 21:01:36 2026
```

Current status:

```text
submitted_waiting_pbs_completion
```

Stop rule invoked: no polling, retrieval, finalizer, or packaging is authorized
until Barry reports the PBS completion email or X-ray Cavities explicitly asks
for a re-check.

## Failure Closeout Continuation

Barry reported the PBS completion email:

```text
PBS Job Id: 706130.kunanyi-ohpc
Job Name:   c_hi_lsapil
Execution terminated
Exit_status=1
resources_used.cpupercent=98
resources_used.cput=00:36:52
resources_used.mem=1338348kb
resources_used.ncpus=1
resources_used.vmem=1770104kb
resources_used.walltime=00:49:52
```

Start state for failure closeout:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main
 M docs/exchange/current_status.md
?? docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md
?? docs/goals/019-c-hi-late-source-age-pilot/
?? scripts/kunanyi/c_hi_late_source_age_pilot.pbs
?? tests/test_late_source_age_pilot_wrapper.py

git rev-parse --short HEAD
63f980e
```

Repo-local `AGENTS.md`, this log, the Goal 019 exchange log, and the PBS wrapper
were reread before remote retrieval. No fast-forward, commit, push, git stage,
or cleanup was performed.

Retrieved failure bundle:

```text
docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/
```

Bundle contents:

```text
failure_summary.csv
failure_summary.json
partial_output_inventory.csv
remote_file_checksums.csv
remote_logs/qstat_listing_706130.txt
remote_logs/qstat_706130_excerpt.txt
remote_logs/c_hi_late_source_age_pilot.out
remote_logs/c_hi_late_source_age_pilot.err
remote_logs/c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

Science/failure note:

```text
docs/science/c_hi_late_source_age_pilot_failure_2026-07-01.md
```

Qstat evidence:

```text
Job Id: 706130.kunanyi-ohpc
Job_Name = c_hi_lsapil
job_state = F
resources_used.cpupercent = 98
resources_used.cput = 00:36:52
resources_used.mem = 1338348kb
resources_used.ncpus = 1
resources_used.vmem = 1770104kb
resources_used.walltime = 00:49:52
Stageout_status = 1
Exit_status = 1
```

Retrieved remote checksums:

```text
34b9c1f807c7ba039b6d749caf7e3039cf201ff7baf4cf6348af2c2d061432fc  c_hi_late_source_age_pilot.out
27b2f90d91cd26de321900928de81164a44029836e037a7c039f0ca83fec6d72  c_hi_late_source_age_pilot.err
ad3863ca7e0d249a566b246da6927cf7677db5ab5182b51d6b7e88188b84e60f  c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

First failure point:

```text
tar: 2026-06-30-c-hi-late-source-age-pilot/remote_logs: file changed as we read it
tar: 2026-06-30-c-hi-late-source-age-pilot/output0049_Timestep_49: file changed as we read it
```

All six intended view validations had already passed before the `tar` failure:

```text
xray_validation=passed output=46 timestep=Timestep_46 view=0deg accumulator=direct_y_axis_sum
xray_validation=passed output=46 timestep=Timestep_46 view=45deg accumulator=edge_overlap_uniform_cell_projection
xray_validation=passed output=46 timestep=Timestep_46 view=90deg accumulator=edge_overlap_uniform_cell_projection
xray_validation=passed output=49 timestep=Timestep_49 view=0deg accumulator=direct_y_axis_sum
xray_validation=passed output=49 timestep=Timestep_49 view=45deg accumulator=edge_overlap_uniform_cell_projection
xray_validation=passed output=49 timestep=Timestep_49 view=90deg accumulator=edge_overlap_uniform_cell_projection
```

Diagnosis:

- The wrapper reached and validated all planned `46/49 x 0/45/90 deg` products.
- The retrieved archive is readable with `tar -tzf` and contains required compact
  files for all six source-age/view rows.
- The PBS job failed because the live analysis directory changed while `tar`
  was reading it. With `set -euo pipefail`, that nonzero tar status propagated
  to PBS `Exit_status=1`.
- This is best classified as `wrapper_archive_race_live_directory_changed_during_tar`,
  not as a missing HDF5 input, XRAiSE runtime/table failure, projection
  validation failure, or science-default issue.
- Because the scheduler reported `Exit_status=1`, this remains a failure
  closeout until X-ray Cavities reviews whether to accept the retrieved archive
  with caveat or authorize a no-rerun repackage/finalizer.

Recommendation:

- Do not rerun the HDF5/XRAiSE projections first.
- Patch the wrapper archive contract so `tar` uses a stable manifest/snapshot,
  excludes live `remote_logs`, or closes/snapshots logs before archive creation.
- Add a focused wrapper-contract test for the archive race.
- If a clean remote closeout is required, authorize only a tiny no-rerun
  repackage/finalizer against the existing analysis root, or a targeted rerun
  only if review finds the existing archive insufficient.

Status:

```text
failed_diagnostic_complete
```

Boundary confirmation:

- retrieval and diagnosis were limited to the already-completed Goal 019 job;
- no new PBS submission, rerun, finalizer, or polling loop;
- no endpoint rerun;
- no source-age substitution;
- no PLUTO production;
- no early `5/10 Myr` branch;
- no `C-LO`, `G-LO`, comparison-case processing, PRAiSE/radio/cavity
  regeneration, broad batch, 48-hour production commitment, or
  scientific-default change;
- no commits, pushes, cleanup, Stas/Patrick escalation, or `agent_comms`
  changes;
- accepted Goal 005/011/012/016/017/018 assets were not overwritten.

## Repair Iteration: Archive Race Patch And No-Rerun Repackage

X-ray Cavities authorized a narrow repair iteration after the failure closeout:

- patch the wrapper archive race;
- add focused wrapper-contract tests;
- if feasible, run only a tiny no-rerun finalizer/repackage against existing
  Goal 019 outputs.

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git branch --show-current
main

git rev-parse --short HEAD
63f980e

git status --short --branch
## main...origin/main
 M .gitattributes
 M docs/exchange/current_status.md
?? docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md
?? docs/goals/019-c-hi-late-source-age-pilot/
?? docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/
?? docs/science/c_hi_late_source_age_pilot_failure_2026-07-01.md
?? scripts/kunanyi/c_hi_late_source_age_pilot.pbs
?? tests/test_late_source_age_pilot_wrapper.py
```

Evidence reread before editing:

- `docs/science/c_hi_late_source_age_pilot_failure_2026-07-01.md`
- `docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/failure_summary.json`
- `docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/partial_output_inventory.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/remote_logs/c_hi_late_source_age_pilot.err`
- this Goal 019 log
- `docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md`
- `scripts/kunanyi/c_hi_late_source_age_pilot.pbs`
- `tests/test_late_source_age_pilot_wrapper.py`

Test-first archive repair:

```text
uv run pytest tests/test_late_source_age_pilot_wrapper.py -q
...FF
2 failed, 3 passed
```

The failing tests required a stable archive snapshot instead of live-root tar.
After patching the wrapper to snapshot completed products and copied logs:

```text
uv run pytest tests/test_late_source_age_pilot_wrapper.py -q
.....                                                                    [100%]
5 passed in 0.00s
```

No-rerun repackage attempt 1:

```text
repackage_validation=passed rows=6
tar: 2026-06-30-c-hi-late-source-age-pilot/output0049_Timestep_49: file changed as we read it
__CODEX_STATUS__=1
```

This showed that even recursive tar over a copied snapshot directory can trip
on directory metadata on the remote filesystem. I added a stronger test and
wrapper contract requiring an explicit archive file list:

```text
uv run pytest tests/test_late_source_age_pilot_wrapper.py -q
...F.
1 failed, 4 passed
```

After updating the wrapper to write `archive_file_list.txt` and run `tar` with
`--files-from`:

```text
uv run pytest tests/test_late_source_age_pilot_wrapper.py -q
.....                                                                    [100%]
5 passed in 0.00s
```

Final no-rerun repackage evidence:

```text
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot
archive=/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
repackage_validation=passed rows=6
ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110  /u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
66
__CODEX_STATUS__=0
```

Clean archive local copy:

```text
docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/remote_logs/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

Clean archive SHA-256:

```text
ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110
```

New repair note:

```text
docs/science/c_hi_late_source_age_pilot_repair_2026-07-01.md
```

New repair bundle:

```text
docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/
```

Machine-readable repair assets:

```text
repair_summary.json
repackage_validation_summary.csv
repackage_validation_summary.json
product_inventory.csv
repackage_manifest.tsv
repackage_checksums.sha256
repackage_archive_file_list.txt
remote_logs/no_rerun_repackage.stdout.log
remote_logs/no_rerun_repackage.stderr.log
remote_logs/no_rerun_repackage_filelist.stdout.log
remote_logs/no_rerun_repackage_filelist.stderr.log
remote_logs/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

Repair validation summary:

- six existing products validated;
- `46/Timestep_46` and `49/Timestep_49` each have `0deg`, `45deg`, and
  `90deg` products;
- nonzero views report `edge_overlap_uniform_cell_projection`;
- raw X-ray, corrected X-ray, and correction-ratio empty projected columns are
  all zero in `repackage_validation_summary.csv`;
- `tar -tzf` on the clean archive reports `66` entries.

Status:

```text
repair_complete_no_rerun_package_ready
```

Caveat:

- original PBS job `706130.kunanyi-ohpc` remains `Exit_status=1`; this repair
  creates a clean no-rerun package from already-produced outputs rather than
  rewriting the scheduler outcome.

Boundary confirmation:

- no new PBS submission;
- no HDF5/XRAiSE rerun;
- no endpoint rerun;
- no source-age substitution;
- no early `5/10 Myr` branch;
- no PLUTO production;
- no `C-LO`, `G-LO`, comparison-case processing, PRAiSE/radio/cavity
  regeneration, broad batch, 48-hour production commitment, or
  scientific-default change;
- no commits, pushes, cleanup, Stas/Patrick escalation, or `agent_comms`
  changes;
- accepted Goal 005/011/012/016/017/018 assets and the existing Goal 019
  failure bundle were not overwritten.
