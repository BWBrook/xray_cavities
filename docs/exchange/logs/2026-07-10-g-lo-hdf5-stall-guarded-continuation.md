# 2026-07-10 - G-LO HDF5-Stall Guarded Continuation

Goal 038 recovered the exact valid Goal 037 restart, implemented a fail-closed
no-output watchdog, executed Barry-approved scratch compaction, and submitted
one endpoint-oriented G-LO continuation.

## Status

Status: `submitted_waiting_pbs_completion`.

Decision label:
`G_LO_GUARDED_CONTINUATION_SUBMITTED_WAITING_PBS_COMPLETION`.

## Restart And Watchdog Gate

The submitted contract requires:

- exact three-record `restart.out` mapping `{dbl:2, flt:10, particle:1000}`;
- fluid and particle step 10578 and matching code time;
- full 42,032-particle payload validation;
- exact 67,318,639,276-byte `data.0002.dbl.h5::Timestep_2`, required
  `1014 x 960 x 960` datasets, scalar samples, and unique catalogue row;
- compute-node trusted-source/staged HDF5 SHA equality plus SHA binding of the
  catalogue, restart record, and particle input; and
- a 90-minute output-only watchdog that TERM/KILLs the complete launcher
  process group and records `no_progress_watchdog_timeout` distinctly.

Independent red-green review hardened wrapper target pinning, catalogue
parsing, four-surface binding, and process-group termination. Final review
reported no correctness or launch-safety finding.

## Scratch Compaction

Barry explicitly approved the retention plan after the first staging attempt
hit an apparent scratch quota. The tested Goal-038-specific utility completed
two idempotent passes. The orchestrator-observed remote summaries reported:

```text
2344938776583 + 465358011179 = 2810296787762 bytes
```

It preserved accepted endpoints, production float-HDF5 age surfaces, required
restart tuples, the Level 3 baseline, catalogues/configuration, and compact
provenance. It removed superseded scale/prove-out roots, redundant checkpoint
payloads, the invalid G-LO double HDF5, and the zero-byte partial Goal 038
root. A 16 MiB scratch write probe passed after compaction. The corrective raw
manifests remain remote-only; the first-pass manifest may have been overwritten
by the second execution, so the local exact-byte sum remains a derivative
orchestrator handoff claim rather than independently reconstructable evidence.

The one-off compactor is not a general cleanup tool. Future raw/processed data
retention follows
`docs/science/xray_cavities_data_lifecycle_strategy_2026-07-10.md`.
Under that prospective policy, Goal 038 is a pre-policy capacity exception and
would be red or unquantified after the 20 percent safety factor and
particle/log growth; it is not a precedent for another submission.

## Submission

```text
job_id=751292.kunanyi-ohpc
Job_Name=g_lo_guard
job_state=Q
queue=normal
ctime=Fri Jul 10 15:04:00 2026
select=64:ncpus=28:mpiprocs=28
walltime=48:00:00
```

Stage root:
`/u/bwbrook/codex_kunanyi/goal038_g_lo_hdf5_stall_guarded_continuation`.

Run root:
`/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation`.

Exactly one job was submitted. The PBS stop rule was invoked immediately after
queued proof; no polling or retrieval followed.

## Validation

- Integrated local suite: `89 passed in 13.01s`.
- Goal 038 shell syntax: passed.
- Final remote SHA, inventory, catalogue, particle/HDF5, module, and queue
  preflight: observed passed in the submission session; the raw
  post-compaction transcript remains remote-only pending completion retrieval.
- JSON/CSV parsing and `git diff --check`: passed.

## Resume

Wait for Barry's PBS completion email for `751292.kunanyi-ohpc`. Then perform
one compact completion/endpoint review. Do not begin G-LO post-processing until
endpoint status and output integrity are proven.
