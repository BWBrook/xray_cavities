# C-LO Endpoint-Oriented Continuation Completion Review

Date: 2026-07-07

Goal 035 retrieved compact completion evidence for the endpoint-oriented
`C-LO` continuation job `750947.kunanyi-ohpc`. The job completed with
`Exit_status=0`, and the compact run catalogues support calling the C-LO
50 Myr endpoint reached. This package is an endpoint-status review only; no
C-LO post-processing or observable product generation was started.

## Decision

Status:
`complete_endpoint_review`.

Decision label:
`C_LO_ENDPOINT_ORIENTED_RUN_REACHED_ENDPOINT_COMPACT_EVIDENCE_GREEN`.

PBS result:

```text
Job id: 750947.kunanyi-ohpc
Job name: c_lo_endpt
Exit_status: 0
Job state: F
resources_used.walltime: 24:47:37
resources_used.cput: 692:21:26
resources_used.ncpus: 1792
resources_used.mem: 9891168kb
Resource_List.select: 64:ncpus=28:mpiprocs=28
Resource_List.walltime: 48:00:00
```

`qstat` reports `Stageout_status=1`; this remains visible as a scheduler
caveat. The requested stage-root stdout/stderr, final `qstat`, submission
preflight transcript, and compact run-root inventories were present and
retrieved as text/CSV evidence.

## Endpoint Evidence

The endpoint-oriented run root is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles
```

Compact evidence shows:

- `markers/DONE` present.
- `markers/FAILED` absent.
- wrapper stdout contains `MPI_EXIT_CODE=0`.
- stderr contains the known nonfatal `setup-problem: git: command not found`
  warning.
- latest `dbl.h5.out` row:
  `13 1.533007e+04 2.422549e-03 57029`.
- latest `flt.h5.out` row:
  `53 1.533007e+04 2.422549e-03 57029`.
- latest remote double checkpoint inventory row:
  `data.0013.dbl.h5`.
- latest remote float output inventory row:
  `data.0053.flt.h5`.
- latest remote particle restart inventory row:
  `particles.5003.dbl`.
- remote inventory count: `41` HDF5 files and `3392` particle restart files.
- remote output directory size: `1.9T`.

The configured endpoint target remains `15330.06968940` code-time units. The
latest compact catalogue time is `15330.07`, giving a remaining gap of
`-0.000310600000375` code-time units and an endpoint fraction of
`1.00000002026`. Within the compact catalogue precision, the endpoint target is
therefore reached.

Remote HDF5 and particle payloads were inventoried by count, path, and size
only. They were not copied locally and were not post-processed.

## Assets

Compact assets live under:

```text
docs/science/assets/c_lo_endpoint_oriented_continuation_completion_2026-07-07/
```

Key files:

- `qstat_final.csv`
- `completion_summary.csv`
- `run_output_inventory.csv`
- `run_output_inventory_summary.csv`
- `remote_log_inventory.csv`
- `local_asset_manifest.sha256`
- `next_step_recommendation.csv`
- `c_lo_endpoint_oriented_continuation_completion_metadata.json`
- `remote_logs/`

The `remote_logs/` directory contains compact text evidence only: final qstat,
stdout, stderr, submission preflight transcript, remote completion summary, and
run-root inventory CSVs. It contains no `.h5`, `data.*`, or particle payload
files.

## Caveats

- This package resolves endpoint status only; it is not C-LO science
  post-processing.
- No XRAiSE, PRAiSE, radio, cavity, source-age, endpoint-comparison, or
  observable-generation workflows were run.
- `Stageout_status=1` remains visible as a scheduler caveat, although the
  needed compact stage-root logs were available.
- The stderr `git: command not found` warning is carried as a nonfatal
  runtime-environment caveat because `MPI_EXIT_CODE=0` and `Exit_status=0`
  both passed.
- `G-LO` remains untouched and outside this goal.

## Recommendation

The next goal should be a bounded C-LO endpoint post-processing preflight or
inspection packet. It should start from the now endpoint-complete C-LO run root,
define exactly which compact endpoint products are needed first, and preserve
the no-overwrite and PBS stop-rule discipline. Do not start C-LO science
post-processing until X-ray Cavities accepts this endpoint-status package.
