# C-LO Checkpoint Continuation Completion Review

Date: 2026-07-05

Goal 033 retrieved compact completion evidence for the bounded `C-LO`
continuation job `750931.kunanyi-ohpc`. The job completed cleanly as a
checkpoint/continuation surface, but the compact catalogues do not support
calling it the 50 Myr endpoint.

## Decision

Decision label:
`C_LO_CONTINUATION_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

Status:
`complete_checkpoint_review`.

PBS result:

```text
Job id: 750931.kunanyi-ohpc
Job name: c_lo_cont
Exit_status: 0
Job state: F
resources_used.walltime: 03:33:08
resources_used.cput: 98:54:40
resources_used.ncpus: 1792
resources_used.mem: 9870960kb
Resource_List.select: 64:ncpus=28:mpiprocs=28
Resource_List.walltime: 04:00:00
```

`qstat` reports `Stageout_status=1`; this is carried as a scheduler caveat.
The requested stage-root stdout/stderr and submission preflight transcript were
present and retrieved or reconstructed into the local compact evidence bundle.

## Checkpoint Evidence

The continuation run root is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO/particles
```

Compact evidence shows:

- `markers/DONE` present.
- `markers/FAILED` absent.
- wrapper stdout contains `MPI_EXIT_CODE=0`.
- stderr is empty (`0` bytes).
- latest `dbl.h5.out` row:
  `4 3.270555e+03 2.680126e-01 12349`.
- latest `flt.h5.out` row:
  `12 3.270555e+03 2.680126e-01 12349`.
- latest remote double checkpoint inventory row:
  `problem/outputs/data.0004.dbl.h5`.
- latest remote float output inventory row:
  `problem/outputs/data.0012.flt.h5`.
- latest remote particle restart inventory row:
  `problem/outputs/particles.1068.dbl`.
- remote inventory count: `8` HDF5 files and `567` particle restart files.

The remote HDF5 and particle files were inventoried by path, role, and size
only. They were not copied locally and were not post-processed.

## Interpretation

This is a green continuation checkpoint surface. It advanced the `C-LO`
checkpoint from the accepted Goal 032 restart time near `1.533095e+03`
code-time units to `3.270555e+03` code-time units.

It is not the 50 Myr endpoint. The compact catalogue evidence is still far
short of the configured 50 Myr target (`15330.06968940` code-time units in the
accepted C-LO config contract). No endpoint products or observables are
claimed.

## Assets

Compact assets live under:

```text
docs/science/assets/c_lo_checkpoint_continuation_completion_2026-07-05/
```

Key files:

- `qstat_final.csv`
- `completion_summary.csv`
- `run_output_inventory.csv`
- `run_output_inventory_summary.csv`
- `remote_log_inventory.csv`
- `local_asset_manifest.sha256`
- `next_step_recommendation.csv`
- `c_lo_checkpoint_continuation_completion_metadata.json`
- `remote_logs/`

The `remote_logs/` directory contains compact text evidence only: final qstat,
stdout, empty stderr, submission preflight transcript, retrieval manifest, and
a sanitized completion inventory. It contains no `.h5`, `data.*`, or particle
payload files.

The source-stage `retrieval_manifest_2026-07-05.sha256` is preserved as remote
provenance. The local review copies of text logs normalize line-end whitespace
for clean review diffs; `local_asset_manifest.sha256` records the hashes of the
local packaged files.

## Caveats

- This package is a checkpoint review, not C-LO science post-processing.
- No XRAiSE, PRAiSE, radio, cavity, source-age, endpoint-comparison, or
  observable-generation workflows were run.
- `Stageout_status=1` remains visible as a scheduler caveat, although the
  needed compact stage-root logs were available.
- The C-LO endpoint remains unresolved until a later authorized decision either
  continues the run or deliberately accepts a shorter checkpoint target.

## Recommendation

The next goal should be a bounded `C-LO` endpoint-or-next-continuation decision
from the compact checkpoint catalogues. Do not start C-LO post-processing until
endpoint status is explicitly resolved.
