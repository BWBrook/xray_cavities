# C-LO Checkpoint Continuation Decision

Date: 2026-07-04

Goal 033 inspected the accepted Goal 032 `C-LO` checkpoint surface and found it
clean enough for one bounded continuation submission.

## Decision

Decision label:
`C_LO_CHECKPOINT_SURFACE_CLEAN_CONTINUATION_SUBMITTED`.

Status:
`submitted_waiting_pbs_completion`.

Submitted PBS job:

```text
Job id: 750931.kunanyi-ohpc
Job name: c_lo_cont
Queue/state at stop: normal / Q
Resources: select=64:ncpus=28:mpiprocs=28, walltime=04:00:00
PLUTO_MAXTIME_HOURS: 3.5
```

The PBS stop rule is active. Do not poll or retrieve until Barry reports the
PBS completion email or X-ray Cavities explicitly authorizes a re-check.

## Checkpoint Surface

The source checkpoint is the accepted Goal 032 run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles
```

Inspection found:

- `markers/DONE` present and `markers/FAILED` absent.
- Latest restart HDF5: `data.0002.dbl.h5`.
- Latest HDF5 time: `1.533095e+03` code-time units at step `5920`.
- Latest float HDF5: `data.0006.flt.h5` at the same time/step.
- Latest particle restart surface: `particles.0501.dbl`.
- `dbl.h5.out`, `flt.h5.out`, and `restart.out` present.
- The new continuation workdir did not exist before staging.

The continuation workdir was prepared as an isolated no-overwrite root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO/particles
```

It contains copied compact config/catalogue files and symlinks to the accepted
Goal 032 restart HDF5/XMF and particle restart file. The accepted Goal 032 tree
was not overwritten.

## Resource Choice

The continuation uses `64` nodes / `1792` ranks rather than the `80` nodes used
for the fresh bounded checkpoint. This follows the C-HI restart evidence:
`64` nodes completed cleanly, while `80` nodes / `2240` ranks reproduced an HDF5
restart-read stall. This is a conservative restart choice, not a new scientific
default.

## Caveats

This is a continuation submission, not a completion product. It does not create
or retrieve C-LO science products, endpoint comparisons, XRAiSE/PRAiSE outputs,
radio products, cavity products, or observables.

The C-LO run has still not reached the 50 Myr endpoint. Goal 033 only advances
the bounded restart/continuation ladder after verifying the checkpoint surface.

## Assets

Compact assets live under:

```text
docs/science/assets/c_lo_checkpoint_continuation_2026-07-04/
```

Key tables:

- `checkpoint_inspection.csv`
- `restart_surface_manifest.csv`
- `continuation_submission_preflight.csv`
- `next_step_recommendation.csv`
- `c_lo_checkpoint_continuation_metadata.json`

## Recommendation

Wait for Barry's PBS completion email for `750931.kunanyi-ohpc`. The next goal,
after that email or explicit re-check authorization, should retrieve compact
stdout/stderr/qstat/marker/inventory evidence and decide whether the continuation
surface is clean and how far it advanced toward the C-LO endpoint.
