# Goal 038 Log - G-LO HDF5-Stall Guarded Continuation

Date: 2026-07-10

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD: `main` at `bdd9b1e`.
- Initial git status: `## main...origin/main`.
- Repo-local `AGENTS.md` and Goal 037 completion evidence were read first.
- Persistent `jet` was retired; Goal 038 used short-lived explorer, worker,
  strategy, and reviewer agents under direct orchestrator control.

## Objective

Recover boldly but safely from Goal 037's parallel double-HDF5 stall: validate
the exact fluid/particle restart, build a fail-closed output-progress watchdog,
resolve the scratch-capacity blocker under Barry's explicit approval, stage an
isolated 64-node continuation, and submit one endpoint-oriented 48-hour job.

## Boundary

No use of partial `data.0003.dbl.h5`; no in-place mutation of the accepted
Goal 037 source; no post-processing before a proven G-LO endpoint; no follow-on
job; stop after queued/running proof. Destructive science-data retention
changes required and received explicit Barry approval.

## Local Implementation

Added:

- `scripts/science/validate_pluto_particle_restart_pair.py`;
- `scripts/kunanyi/run_with_progress_watchdog.sh`;
- `scripts/kunanyi/g_lo_hdf5_stall_guarded_continuation.pbs`;
- `scripts/kunanyi/compact_xray_cavities_scratch_goal038.py`;
- focused validator, watchdog, wrapper, template, and compaction tests.

Updated `scripts/kunanyi/jet_setup_production_template.pbs` with opt-in explicit
HDF5 restart and watchdog paths. Defaults remain unchanged when the new
environment variables are absent.

## TDD And Review

Initial focused implementation passed 63 tests. Independent reviewers then
found material gaps in wrapper enforcement, HDF5/catalogue binding, direct
fluid/particle step comparison, exact record/slot locking, process-group
termination, wrapper override handling, and catalogue validation.

Every gap was reproduced red-first and fixed. The hardened design:

- invokes restart/HDF5 validation from the PBS wrapper before the production
  template;
- requires exactly three restart records and slot mapping 2/3/8 to
  2/10/1000;
- directly compares particle `stepNumber` to fluid `nstep`;
- validates HDF5 size, timestep, shape, datasets, time, scalar samples, and the
  unique `dbl.h5.out` index/time/step row;
- SHA-binds HDF5, catalogue, `restart.out`, and particle inputs;
- pins the case, variant, run root, restart policy/index, resources, and module
  stack; and
- starts the launcher in a dedicated process group and TERM/KILLs that group.

A final independent reviewer found no correctness or launch-safety defects.

## Initial Remote Blocker

The first remote pass failed on the old module Python. The second used Python
3.11, validated all 42,032 particle records, and then stopped while copying the
929,856-byte executable with `Disk quota exceeded`. No `qsub` was reached and
the partial root contained only directories plus a zero-byte `pluto`.

The pre-compaction scratch inventory was 8,797,984,508,061 bytes, about
1.89 GB above an inferred 8 TiB boundary. The shared filesystem itself was
49 percent used, so the evidence pointed to a user allocation limit rather
than global capacity.

## Approved Compaction

Barry explicitly approved the documented retention plan. The one-off
compaction utility was implemented red-first and tested for dry-run
non-mutation, collision failure before mutation, exact keep/remove behavior,
and idempotent resumption.

Remote execution used Anaconda 2024 Python 3.11. The orchestrator-observed
initial summary reported 2,344,938,776,583 bytes freed. A test-driven
correction expanded the endpoint-root C-LO cleanup to the complete approved
contract and an idempotent second summary reported 465,358,011,179 bytes.
Total manifest-based reclaimed payload reported remotely:

```text
2810296787762 bytes
```

The corrective-pass raw pre/post manifests remain under the remote Goal 038
stage root and were not copied locally before the PBS stop rule. The first-pass
files may have been overwritten by the second execution, so the exact summed
total is an orchestrator-observed handoff value rather than independently
reconstructable local provenance.

The resulting C-LO endpoint root retains all 54 float-HDF5/XMF age surfaces,
double checkpoints 6 and 13, and particle restarts 1611 and 5003. Required
C-HI age surfaces/endpoints/restart tuples, the Level 3 baseline, catalogues,
configuration, and compact provenance were retained. Six scale ladders, two
May prove-outs, superseded C-HI/C-LO checkpoint payloads, the invalid G-LO
double HDF5, and the zero-byte partial Goal 038 root were removed. A 16 MiB
scratch write probe passed afterward.

The data-lifecycle strategy adopted during closeout classifies this as a
pre-policy exception: the reclaimed bytes do not establish the prospective
20-percent-safety headroom gate after particle/log growth. No future large job
may use this evidence as a green or amber precedent.

## Final Remote Gate

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal038_g_lo_hdf5_stall_guarded_continuation
```

Source root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles
```

Isolated run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation
```

The isolated root was recreated cleanly. It contains the exact Goal 037
executable/configuration and only the selected HDF5/XMF, restart record,
particle restart, grid, and truncated catalogues. No stale marker or higher
restart payload is present.

The submission session observed passing pre-submission checks:

- staged code SHA-256 equality and remote `bash -n`;
- exact source/destination executable and configuration SHA equality;
- exact inventory, sizes, catalogue indices, and no-overwrite contract;
- full particle and HDF5 structure/time/shape/dataset validation;
- AGN Intel/IMPI/HDF5/ZFP stack plus `mpicc`/`mpirun` availability; and
- enabled `normal` queue with 48-hour maximum walltime.

The wrapper now computes the trusted Goal 037 HDF5 SHA on the compute node and
requires the staged HDF5 to match before `mpirun`, avoiding a login-node hash
of the 67 GB file while preserving fail-closed source equality.

The post-compaction raw preflight and qstat transcripts remain in the remote
stage root and were not retrieved before the stop rule. Local tables are
derivative handoff records rather than substitutes for those transcripts.

## Submission

Exactly one PBS job was submitted:

```text
job_id=751292.kunanyi-ohpc
Job_Name=g_lo_guard
job_state=Q
queue=normal
ctime=Fri Jul 10 15:04:00 2026
Resource_List.select=64:ncpus=28:mpiprocs=28
Resource_List.walltime=48:00:00
```

The stop rule was invoked immediately after queued proof. No subsequent
remote command, qstat poll, or retrieval was run.

## Validation

Final integrated validation:

```text
uv run pytest tests/test_goal038_scratch_compaction.py \
  tests/test_g_lo_hdf5_stall_guarded_continuation_wrapper.py \
  tests/test_jet_setup_production_template_watchdog.py \
  tests/test_progress_watchdog.py \
  tests/test_validate_pluto_particle_restart_pair.py \
  tests/test_g_lo_endpoint_oriented_production_wrapper.py \
  tests/test_c_lo_endpoint_oriented_continuation_wrapper.py \
  tests/test_c_lo_bounded_execution_wrapper.py -q
89 passed in 13.01s
```

All three Goal 038 shell surfaces pass `bash -n`; JSON and CSV assets parse;
`git diff --check` is clean.

## Current Status

```text
submitted_waiting_pbs_completion
```

Decision label:

```text
G_LO_GUARDED_CONTINUATION_SUBMITTED_WAITING_PBS_COMPLETION
```

## Resume Contract

After Barry reports the completion email for `751292.kunanyi-ohpc`, or
explicitly authorizes a re-check:

1. Read final `qstat -x -f` once.
2. Retrieve compact stdout/stderr/watchdog/preflight/catalogue evidence only.
3. Determine whether endpoint completion, a watchdog stop, or another failure
   occurred before considering any follow-on compute.
4. Do not begin G-LO science post-processing until endpoint status and output
   integrity are proven.

## Boundary Confirmation

One approved scratch compaction and one PBS submission occurred. No
post-submission polling, retrieval, follow-on job, post-processing, endpoint
product, XRAiSE/PRAiSE/radio/cavity work, commit, push, scientific-default
change, or accepted Goal 037 source mutation occurred.
