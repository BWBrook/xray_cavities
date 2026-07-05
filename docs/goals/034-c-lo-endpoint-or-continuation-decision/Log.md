# Goal 034 Log - C-LO Endpoint-Or-Continuation Decision

Date: 2026-07-05

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `ab40275`.
- Git status at start: `## main...origin/main`.
- Fast-forward state: local checkout already matched `origin/main` at
  `ab40275`.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 034 authorizes a C-LO endpoint-or-next-continuation decision and at most
one bounded C-LO continuation PBS submission if the checkpoint gate is clean.
It does not authorize `G-LO`, post-processing, endpoint observables,
XRAiSE/PRAiSE, radio or cavity workflows, source-age products, broad
continuation ladders, scientific-default changes, commits, pushes, cleanup, or
`agent_comms` edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 033 log, exchange log, completion science note, and compact assets,
  especially `completion_summary.csv`, `run_output_inventory_summary.csv`,
  `next_step_recommendation.csv`, and
  `c_lo_checkpoint_continuation_completion_metadata.json`.
- Goal 033 wrapper and focused tests:
  `scripts/kunanyi/c_lo_checkpoint_continuation.pbs` and
  `tests/test_c_lo_checkpoint_continuation_wrapper.py`.
- Production template:
  `scripts/kunanyi/jet_setup_production_template.pbs`.

## Checkpoint Gate

The local compact Goal 033 evidence said the continuation completed cleanly but
was not endpoint-complete. A live read-only Kunanyi checkpoint gate was then
run against:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO/particles
```

The first helper retry hit an expired TPAC selector. The authorized
Chrome/Open OnDemand route was used only for the selector, and the portal
reported a live window closing at `Sun Jul 5 17:42:29 2026`. Safari was not
used.

Live checkpoint evidence:

- `markers/DONE` present.
- `markers/FAILED` absent.
- Latest `dbl.h5.out` row:
  `4 3.270555e+03 2.680126e-01 12349 single_file little rho vx1 vx2 vx3 prs tr1`.
- Latest `flt.h5.out` row:
  `12 3.270555e+03 2.680126e-01 12349 single_file little rho vx1 vx2 vx3 prs tr1`.
- Endpoint target retained from accepted C-LO config contract:
  `15330.06968940` code-time units.
- Latest code time: `3270.555`.
- Endpoint fraction: `0.21334247`.
- Endpoint-complete flag: `False`.
- Required restart files present:
  `data.0004.dbl.h5`, `data.0004.dbl.xmf`, `data.0012.flt.h5`,
  `data.0012.flt.xmf`, `particles.1068.dbl`, `restart.out`,
  `dbl.h5.out`, `flt.h5.out`, and `grid.out`.
- Remote inventory counts: `8` HDF5 files and `567` particle restart files.
- New continuation-2 run root did not exist before staging:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2`.
- Correct remote source dependencies under `/scratch/bwbrook/git/utas-agn/`
  were present, Goal 033 rendered config/template were present, and the AGN
  Intel/IMPI/HDF5 module probe passed.

An initial particle-catalogue check expected `particles.dbl.out`, but Goal 033
inventory and the live output listing show this run uses `restart.out` plus
the `particles.NNNN.dbl` restart sequence rather than a separate
`particles.dbl.out` catalogue. The presence of `particles.1068.dbl` and
`restart.out` is therefore treated as the particle restart gate.

## Local Work

- Added `scripts/kunanyi/c_lo_endpoint_or_continuation.pbs`.
- Added focused wrapper tests in
  `tests/test_c_lo_endpoint_or_continuation_wrapper.py`.
- Added compact Goal 034 science note/assets under:
  `docs/science/c_lo_endpoint_or_continuation_decision_2026-07-05.md` and
  `docs/science/assets/c_lo_endpoint_or_continuation_decision_2026-07-05/`.

## Local Validation Before Submission

- `uv run pytest tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed: `12 passed in 0.01s`.
- `bash -n scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` passed.
- `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for
  `docs/science/assets/c_lo_endpoint_or_continuation_decision_2026-07-05/c_lo_endpoint_or_continuation_metadata.json`.
- CSV parse/expected-column checks passed for the Goal 034 asset tables.
- `git diff --check` passed before remote submission.

## Remote Staging And Submission

Remote staging used:

```text
/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation
```

The continuation-2 run root is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2
```

Remote staged hashes passed:

- wrapper:
  `5571c0eb1f84ca0872aa6874fef74b8e2b9f33f4c6f4df08387cd4e64f1ab681`;
- production template:
  `9085e64fe1ca58010909790f3b6fa01abed7962c752d7d106f260bd3403356fc`;
- `case_manifest.json`:
  `019cb4eda5b9d1009d4a73e57a7b1ac5ca6f15b24eaf583a4b480b5d6a593c3b`;
- `pluto.ini`:
  `3c6b127b716f3c8d112a5cccd37f42d13aee10962e869a6d1ac0e8b5e3485341`;
- `environment.ini`:
  `3b49690db1185c70742400925fb19f3f51abead2967f0e46a732b9734c86630b`;
- `definitions_overrides.json`:
  `a65fbd272dd4d4f49d02efc7b54b8cf26f2356e6dd5bcfcaf402cf00cc48660c`;
- Stewart CSV:
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`.

Remote wrapper and template `bash -n` passed. The final remote gate also
confirmed:

- prepared restart catalogue row:
  `4 3.270555e+03 2.680126e-01 12349 single_file little rho vx1 vx2 vx3 prs tr1`;
- required staged restart surfaces present;
- source paths present;
- AGN module stack loaded:
  `intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5`;
- `mpicc` and `mpirun` resolved from the accepted Intel/IMPI stack.

Two pre-qsub gate retries stopped safely before submission: one used the wrong
config filename (`definitions_overrides.h` instead of
`definitions_overrides.json`), and one used generic public module names instead
of the accepted AGN modulefile contract. Neither retry reached `qsub`.

The final gate submitted exactly one PBS job:

- job id: `750944.kunanyi-ohpc`;
- job name: `c_lo_cont2`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `mem=128gb`, `walltime=04:00:00`;
- stdout:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.out`;
- stderr:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.err`;
- final remote preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/remote_logs/submission_preflight_2026-07-05_final.txt`;
- submission record:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/remote_logs/submission_record_2026-07-05.txt`.

Remote activity stopped immediately after `qstat -f` verified state `R`.

## Final Local Validation

After the submitted-waiting documentation updates:

- `uv run pytest tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed: `12 passed in 0.01s`.
- `bash -n scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` passed.
- `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for
  `docs/science/assets/c_lo_endpoint_or_continuation_decision_2026-07-05/c_lo_endpoint_or_continuation_metadata.json`.
- CSV parse/expected-column checks passed for:
  `endpoint_decision.csv`, `checkpoint_gate.csv`,
  `restart_surface_manifest.csv`, `continuation_submission_preflight.csv`, and
  `next_step_recommendation.csv`.
- `git diff --check` passed.
- Targeted unresolved-marker scan passed for the new science note, Goal log,
  exchange log, and the new top `current_status.md` section. A whole-file scan
  of `current_status.md` still finds older historical handoff-state terms
  unrelated to Goal 034.
- The Goal 034 local asset bundle contains no `.h5`, `data.*`,
  `particles.*`, or files larger than `5 MB`.

## Final Status

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_CHECKPOINT_CLEAN_NOT_ENDPOINT_CONTINUATION2_SUBMITTED`.

No polling, retrieval, post-processing, endpoint products, `G-LO`,
scientific-default changes, commits, pushes, cleanup, `agent_comms` edits, or
accepted-asset overwrites occurred.

## Completion Retrieval And Endpoint Review

Barry reported the PBS completion email for `750944.kunanyi-ohpc`:

- job name: `c_lo_cont2`;
- `Exit_status=0`;
- `resources_used.cpupercent=2815`;
- `resources_used.cput=98:38:39`;
- `resources_used.mem=9868484kb`;
- `resources_used.ncpus=1792`;
- `resources_used.vmem=27590612kb`;
- `resources_used.walltime=03:32:55`.

The Goal 034 continuation-2 retrieval/review pass stayed compact and
read-only. It retrieved or generated only scheduler records, stdout/stderr,
preflight transcript, catalogue tails, marker status, and file-count/size
inventories. No `.h5`, `data.*`, or particle payload files were copied
locally.

The repo-local helper route initially worked for retrieval. When a later
read-only inventory summary found the TPAC selector expired, the authorized
Chrome/Open OnDemand page was used only to refresh the 5-minute SSH window; the
page reported a live window closing at `Sun Jul 5 22:05:07 2026`. Safari was
not used.

Retrieved compact evidence:

- final `qstat -x -f` record:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/remote_logs/qstat_final_2026-07-05.txt`;
- stdout:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/remote_logs/c_lo_endpoint_or_continuation.out`;
- stderr:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/remote_logs/c_lo_endpoint_or_continuation.err`;
- final preflight transcript:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/remote_logs/submission_preflight_2026-07-05_final.txt`;
- compact remote completion inventory:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/remote_logs/completion_inventory_2026-07-05.txt`;
- compact machine-readable package:
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/`.

Completion evidence:

- `qstat` final state `F`, `Exit_status=0`, `Stageout_status=1`.
- `markers/DONE` present and `markers/FAILED` absent.
- wrapper stdout reports `MPI_EXIT_CODE=0`.
- stderr is non-empty only because
  `/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem` reported
  `git: command not found`; this is carried as a nonfatal runtime-environment
  caveat because scheduler and MPI exit status are green.
- latest `dbl.h5.out` row:
  `6 4.930755e+03 2.678869e-01 18546 single_file little rho vx1 vx2 vx3 prs tr1`.
- latest `flt.h5.out` row:
  `19 4.930755e+03 2.678869e-01 18546 single_file little rho vx1 vx2 vx3 prs tr1`.
- latest remote double checkpoint: `data.0006.dbl.h5`.
- latest remote float output: `data.0019.flt.h5`.
- latest remote particle restart: `particles.1611.dbl`.
- compact inventory counts: `9` HDF5 files and `543` particle restart files;
  the output directory is `422G`.

Endpoint interpretation:

- configured endpoint target remains `15330.06968940` code-time units;
- latest compact catalogue time is `4930.755`;
- endpoint fraction is `0.32163944`;
- remaining code-time gap is about `10399.314689`.

Status after review: `complete_checkpoint_review`.

Decision label:
`C_LO_CONTINUATION2_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

Recommended next goal shape: another bounded `C-LO`
endpoint-or-next-continuation decision. Do not start C-LO post-processing until
endpoint status is explicitly resolved.

## Completion Review Validation

After the completion-review package updates:

- `uv run pytest tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed: `12 passed in 0.01s`.
- `bash -n scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` passed.
- `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for
  `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/c_lo_endpoint_or_continuation_completion_metadata.json`.
- CSV parse/expected-column checks passed for:
  `qstat_final.csv`, `completion_summary.csv`, `run_output_inventory.csv`,
  `run_output_inventory_summary.csv`, `remote_log_inventory.csv`, and
  `next_step_recommendation.csv`.
- `git diff --check` passed.
- Targeted unresolved-marker scan passed for the completion science note,
  Goal log, exchange log, and `current_status.md`.
- No-bulky guard passed for the completion asset bundle: no `.h5`,
  `data.*`, `particles.*`, or files larger than `5 MB` are present locally.

No new PBS job, retry, continuation, polling loop, XRAiSE/PRAiSE, radio,
cavity, source-age, endpoint-comparison, observable workflow, `G-LO`,
scientific-default change, bulky payload retrieval, commit, push, cleanup,
Stas/Patrick contact, `agent_comms` edit, or accepted-asset overwrite occurred
in the completion-review pass.
