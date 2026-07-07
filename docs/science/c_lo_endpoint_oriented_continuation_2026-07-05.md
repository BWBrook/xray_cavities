# C-LO Endpoint-Oriented Continuation

Date: 2026-07-05

## Status

This packet submits a single endpoint-oriented C-LO continuation from the
accepted Goal 034 checkpoint surface. It responds to the project decision that
another default 3.5-hour rung is too incremental.

The restart gate is clean: `markers/DONE` is present, `markers/FAILED` is
absent, and the latest accepted Goal 034 catalogues report `data.0006.dbl.h5`
at code time `4930.755`, or `0.32163944` of the configured endpoint target
`15330.06968940`.

## Resource Decision

The `normal` queue reports a `48:00:00` walltime ceiling, and Barry clarified
that Kunanyi generally accepts jobs up to 48 hours. Goal 035 therefore uses
the preferred endpoint-oriented continuation target:

- `select=64:ncpus=28:mpiprocs=28`;
- `walltime=48:00:00`;
- `PLUTO_MAXTIME_HOURS=47.5`;
- fresh no-overwrite run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation`.

The 64-node scale is retained as the preferred restart scale because accepted
restart evidence flagged 80 nodes as a restart-stall risk. The 48-hour walltime
is intended to reach the 50 Myr endpoint in one production continuation if
restart performance remains comparable, while preserving a clean checkpoint
margin below the scheduler walltime.

## Boundaries

This is a continuation submission packet only. It does not authorize C-LO
post-processing, endpoint observables, XRAiSE, PRAiSE, radio, cavity,
source-age products, `G-LO`, scientific-default changes, bulky local retrieval,
commits, pushes, cleanup, or `agent_comms` edits.

If submitted, remote work stops immediately after qstat verifies the job is
queued or running. Retrieval waits for Barry's PBS completion email or explicit
X-ray Cavities authorization.

## Submission

After local and remote preflight gates passed, Goal 035 submitted exactly one
PBS job:

- job id: `750947.kunanyi-ohpc`;
- job name: `c_lo_endpt`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `walltime=48:00:00`;
- stage root:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation`;
- run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.out`
  and
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.err`;
- preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_preflight_2026-07-05_endpoint_oriented.txt`.

Remote work stopped after qstat showed `R`. Retrieval waits for Barry's PBS
completion email.

## Assets

Machine-readable assets live under:

`docs/science/assets/c_lo_endpoint_oriented_continuation_2026-07-05/`

The key tables are:

- `restart_gate.csv`;
- `queue_resource_decision.csv`;
- `continuation_submission_preflight.csv`;
- `next_step_recommendation.csv`;
- `c_lo_endpoint_oriented_continuation_metadata.json`.
