# G-LO Endpoint-Oriented Production Completion Review

Date: 2026-07-10

Goal 037 reviewed the already-fetched compact completion evidence for the
endpoint-oriented `G-LO` production job `751105.kunanyi-ohpc`. PBS terminated
the job at the walltime limit, but the comparative timing audit identifies the
strongest supported root cause as a stalled parallel double-HDF5 write at the
regular 15 Myr output. The run did not reach the configured endpoint and
produced no science product. A valid 10 Myr fluid checkpoint is preserved, but
restart execution is conditional on particle/content preflight and a
fail-closed no-progress watchdog.

## Decision

Status:
`complete_failure_diagnosis_checkpoint_preserved`.

Decision label:
`G_LO_HDF5_WRITE_STALL_SAFE_FLUID_CHECKPOINT_PRESERVED_RESTART_PREFLIGHT_REQUIRED`.

Classification:

- scheduler outcome: `walltime_termination_symptom`;
- strongest root cause: `parallel_double_hdf5_write_stall_at_regular_15_myr_output`;
- fluid checkpoint: `validated_10_myr_fluid_checkpoint_preserved`;
- full fluid/particle restart: `conditional_on_explicit_preflight_and_watchdog`;
- endpoint status: `not_endpoint`;
- science-product status: `not_science_product`.

## Scheduler Outcome

Final PBS evidence:

```text
Job id: 751105.kunanyi-ohpc
Job name: g_lo_endpt
Job state: F
Exit_status: 271
Stageout_status: 1
resources_used.walltime: 48:01:33
resources_used.cput: 1343:30:34
resources_used.ncpus: 1792
resources_used.mem: 8534012kb
Resource_List.select: 64:ncpus=28:mpiprocs=28
Resource_List.walltime: 48:00:00
```

Stderr records:

```text
=>> PBS: job killed: walltime 172883 exceeded limit 172800
Terminated
```

Stdout records `RUN_KIND=fresh`,
`RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5`, and
`JOB_SIGNAL=TERM`. It does not record `MPI_EXIT_CODE=0`. The intended
`-maxtime 47.5` margin therefore did not yield a completed wrapper before PBS
terminated the job. This is not a clean bounded completion. The scheduler
walltime termination is the final symptom, not the strongest root-cause
classification.

`markers/DONE` is absent. `markers/FAILED` exists, but the retrieved marker is
zero bytes because termination interrupted marker writing. Its empty contents
do not convert the outcome into a clean run; the scheduler record, stderr, and
TERM signal establish the failed-run classification.

## Root-Cause Timing

`data.0003.dbl.h5` has remote mtime `2026-07-08 00:13:04 +1000`, while
stdout records `JOB_START=2026-07-07T03:50:30Z`. The partial file therefore
stopped changing about `10:22:34` after launch, then remained unchanged for
about `37:38:48` before wrapper termination at the 48-hour boundary.

Because index `3` is the regular 15 Myr double output, is partial, has no XMF,
and has no corresponding `dbl.h5.out` row, the strongest supported root cause
is a stalled parallel double-HDF5 write at that regular output. The
`PLUTO_MAXTIME_HOURS=47.5` setting is not the cause: the stall began only about
10.4 hours after launch, long before the maxtime guard could apply. The compact
evidence demonstrates no physics failure.

## Conditional Restart Guardrail

The preserved valid fluid checkpoint is:

```text
data.0002.dbl.h5
```

Compact evidence for that checkpoint:

- size: `67,318,639,276` bytes;
- matching XMF: `data.0002.dbl.xmf`, present;
- matching `dbl.h5.out` row index: `2`;
- catalogue time: `3065.935`;
- catalogue step: `10578`.

The candidate paired particle restart is `particles.1000.dbl`, size
`5,044,387` bytes. Its remote mtime is 44 seconds after the safe fluid HDF5,
so it is the closest particle file by remote mtime. This is an mtime-based
pairing only. Its contents and restart compatibility have not been validated,
and an explicit content/pairing preflight is required before any restart
submission. Restart execution also requires a fail-closed no-progress
watchdog; the preserved fluid checkpoint alone is not an unconditional green
restart surface.

The newest inventoried double file is `data.0003.dbl.h5`, but it is only
`44,741,404,952` bytes, versus `67,318,639,276` bytes for each of
`data.0000.dbl.h5` through `data.0002.dbl.h5`. It has no corresponding
`dbl.h5.out` row. It is an incomplete termination artifact and must not be
used for restart.

The catalogue/file offset is therefore intentional and must be preserved:
the latest inventoried double file index is `3`, while the latest validated
restart catalogue/file index is `2`.

## Progress And Endpoint Status

Latest compact catalogue rows:

- double row:
  `2 3.065935e+03 3.213700e-01 10578`;
- float row:
  `14 4.292332e+03 3.164317e-01 14424`.

The latest float output is `data.0014.flt.h5` at code time `4292.332`, or
`0.279994291413` of the configured endpoint `15330.06968940`. The remaining
gap is `11037.73768940` code-time units. The run is not at the endpoint, and
this completion package is not a G-LO science product.

Remote inventory, by path and size only:

- output size: `863G`;
- HDF5 files: `19` total, comprising `4` double and `15` float files;
- particle restart files: `1500`;
- latest inventoried float file: `data.0014.flt.h5`;
- latest inventoried particle file: `particles.1499.dbl`.

No HDF5, `data.*`, or particle payload was copied into this package.

## Assets

Compact completion assets live under:

```text
docs/science/assets/g_lo_endpoint_oriented_production_completion_2026-07-10/
```

Key files:

- `qstat_final.csv`;
- `completion_summary.csv`;
- `run_output_inventory.csv`;
- `run_output_inventory_summary.csv`;
- `remote_log_inventory.csv`;
- `next_step_recommendation.csv`;
- `g_lo_endpoint_oriented_production_completion_metadata.json`;
- `local_asset_manifest.sha256`;
- unchanged compact source evidence under `remote_logs/`.

Two provenance details are deliberate:

- `remote_logs/safe_restart_surface_2026-07-10.txt` contains literal
  backslash-`n` sequences from remote generation and is preserved unchanged;
  the reviewed local CSV/JSON summaries normalize those fields.
- `remote_logs/remote_compact_evidence_manifest_2026-07-10.sha256` predates
  `safe_restart_surface_2026-07-10.txt` and the empty PLUTO diagnostic
  extracts. It remains raw remote provenance; `local_asset_manifest.sha256`
  covers the complete final local bundle.

## Recommendation

After Barry explicitly authorizes it, prepare one further 64-node, 48-hour
G-LO restart with explicit `-h5restart 2`. Stage `data.0002.dbl.h5` and its
matching XMF; exclude partial `data.0003.dbl.h5`; retain the 5 Myr double
cadence; and preflight the mtime-paired `particles.1000.dbl` for content and
restart compatibility. The run must use a fail-closed no-progress watchdog.
Do not submit a restart, generate endpoint products, or claim G-LO science
products from this closeout alone.

## Boundary

The Goal 037 completion turn used Chrome/Open OnDemand for access, remote
read-only final `qstat` and compact inventory generation, and compact evidence
retrieval. It submitted no new PBS job and retrieved no bulky HDF5, `data.*`,
or particle payload. This closeout performed no staging, cleanup, commit, push,
post-processing, XRAiSE/PRAiSE, radio, cavity, source-age, endpoint-product,
or other science-product work.
