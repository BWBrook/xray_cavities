# C-LO Endpoint-Or-Continuation Completion Review

Date: 2026-07-05

Goal 034 retrieved compact completion evidence for the bounded `C-LO`
continuation-2 job `750944.kunanyi-ohpc`. The job completed cleanly as a
checkpoint/continuation surface, but the compact catalogues do not support
calling it the 50 Myr endpoint.

## Decision

Status:
`complete_checkpoint_review`.

Decision label:
`C_LO_CONTINUATION2_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

PBS result:

```text
Job id: 750944.kunanyi-ohpc
Job name: c_lo_cont2
Exit_status: 0
Job state: F
resources_used.walltime: 03:32:55
resources_used.cput: 98:38:39
resources_used.ncpus: 1792
resources_used.mem: 9868484kb
Resource_List.select: 64:ncpus=28:mpiprocs=28
Resource_List.walltime: 04:00:00
```

`qstat` reports `Stageout_status=1`; this remains visible as a scheduler
caveat. The requested stage-root stdout/stderr, final preflight transcript,
final `qstat`, and compact run-root inventories were present and retrieved or
generated as text-only evidence.

## Checkpoint Evidence

The continuation-2 run root is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2/C-LO/particles
```

Compact evidence shows:

- `markers/DONE` present.
- `markers/FAILED` absent.
- wrapper stdout contains `MPI_EXIT_CODE=0`.
- stderr is non-empty only because `setup-problem` reported
  `git: command not found`; the wrapper still records `MPI_EXIT_CODE=0`.
- latest `dbl.h5.out` row:
  `6 4.930755e+03 2.678869e-01 18546`.
- latest `flt.h5.out` row:
  `19 4.930755e+03 2.678869e-01 18546`.
- latest remote double checkpoint inventory row:
  `data.0006.dbl.h5`.
- latest remote float output inventory row:
  `data.0019.flt.h5`.
- latest remote particle restart inventory row:
  `particles.1611.dbl`.
- remote inventory count: `9` HDF5 files and `543` particle restart files.
- remote output directory size: `422G`.

The remote HDF5 and particle files were inventoried by count, path, and size
only. They were not copied locally and were not post-processed.

## Endpoint Review

The configured endpoint target remains `15330.06968940` code-time units. The
latest compact catalogue time is `4930.755`, which is `0.32163944` of that
target, leaving about `10399.314689` code-time units.

This is therefore a green continuation checkpoint surface, not the 50 Myr
endpoint. No C-LO endpoint products or observables are claimed.

## Assets

Compact assets live under:

```text
docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/
```

Key files:

- `qstat_final.csv`
- `completion_summary.csv`
- `run_output_inventory.csv`
- `run_output_inventory_summary.csv`
- `remote_log_inventory.csv`
- `local_asset_manifest.sha256`
- `next_step_recommendation.csv`
- `c_lo_endpoint_or_continuation_completion_metadata.json`
- `remote_logs/`

The `remote_logs/` directory contains compact text evidence only: final qstat,
stdout, stderr, submission preflight transcript, remote completion summary, and
run-root inventory text. It contains no `.h5`, `data.*`, or particle payload
files.

## Caveats

- This package is a checkpoint review, not C-LO science post-processing.
- No XRAiSE, PRAiSE, radio, cavity, source-age, endpoint-comparison, or
  observable-generation workflows were run.
- `Stageout_status=1` remains visible as a scheduler caveat, although the
  needed compact stage-root logs were available.
- The stderr `git: command not found` warning is carried as a nonfatal
  runtime-environment caveat because `MPI_EXIT_CODE=0` and `Exit_status=0`
  both passed.
- The C-LO endpoint remains unresolved until a later authorized decision either
  continues the run or deliberately accepts a shorter checkpoint target.

## Recommendation

The next goal should be another bounded `C-LO` endpoint-or-next-continuation
decision from the compact checkpoint catalogues. Do not start C-LO
post-processing until endpoint status is explicitly resolved.
