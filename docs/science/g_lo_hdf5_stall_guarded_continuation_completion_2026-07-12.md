# G-LO HDF5-Stall Guarded Continuation Completion Review

Date: 2026-07-12

Goal 038 recovered the validated 10 Myr `G-LO` restart after Goal 037's
parallel-HDF5 stall, used a fail-closed progress watchdog, and reached the
configured 50 Myr endpoint. This closeout establishes production endpoint
integrity. It does not yet claim a G-LO science product or observable.

## Decision

Status: `complete_endpoint_review`.

Decision label: `G_LO_GUARDED_CONTINUATION_REACHED_ENDPOINT_GREEN`.

The production result is green because the scheduler, wrapper, marker,
watchdog, catalogue, fluid-HDF5, and particle-restart evidence agree:

- PBS job `751292.kunanyi-ohpc` / `g_lo_guard` finished with `Exit_status=0`;
- stdout records `RUN_KIND=h5_restart_2`, `MPI_EXIT_CODE=0`, and a clean job
  end; stderr is empty;
- `markers/DONE` is present and no failed marker is present;
- the watchdog recorded 1,133 rows, including 1,126 progress events and one
  `command_exit` with exit code zero; no trigger was created;
- the double catalogue ends at index 10, code time `15330.07`, step `49462`;
- the float catalogue ends at index 50 at the same time and step; and
- the endpoint restart validator matched `data.0010.dbl.h5::Timestep_10` and
  `particles.5000.dbl` exactly at code time `15330.0696894` and step `49462`.

## Endpoint Integrity

The endpoint fluid HDF5 is `67,318,639,276` bytes with shape
`1014 x 960 x 960` and datasets `rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3`.
Its code time equals the configured target exactly in the HDF5 metadata.

The paired particle restart contains 197,568 particles. A full scan found IDs
1 through 197,568 with 197,568 unique IDs. Fluid and particle restart records
therefore agree on time and step, rather than being paired by filename or
mtime alone.

The compact remote inventory records 9 double HDF5 files, 40 float HDF5
files, and 4,001 particle restart files in the guarded continuation root. The
raw production root is approximately 2.3 TB and remains on Kunanyi. No HDF5 or
particle payload was copied into this repository.

## Scheduler And Watchdog Caveats

PBS reports `Stageout_status=1`. This is retained as a scheduler caveat, but
the required stage-root stdout, empty stderr, final qstat, preflight evidence,
watchdog log, catalogues, compaction provenance, and endpoint validator output
were present and retrieved directly. It does not overturn the independent
run-integrity gates.

The final watchdog observation briefly saw `data.0010.dbl.h5` while its write
was still in progress. The command then exited zero, and the subsequent
endpoint validator inspected the completed 67 GB HDF5 structure and the full
particle restart. The endpoint conclusion relies on that post-run validator,
not on the watchdog's transient file size.

## Data Lifecycle

Goal 038's approved compaction evidence is now locally retained. Its final
recorded pass freed `465,358,011,179` manifest bytes, while the earlier
orchestrator-observed total across two passes remains documented separately.
The completed G-LO endpoint is now a protected production surface: do not
delete its endpoint HDF5, paired particle restart, catalogues, configuration,
or provenance until endpoint products have been generated, validated, and
promoted under the data-lifecycle policy.

The appropriate next move is ambitious post-processing, not another PLUTO
production rung: generate G-LO endpoint X-ray/tracer products at `0/45/90 deg`
with the refined nonzero-view projection, then build the first coherent
`C-HI`/`C-LO`/`G-LO` endpoint comparison. Raw pruning should follow only after
those products and restart holds are explicit.

## Assets

Compact evidence and derived tables live under:

```text
docs/science/assets/g_lo_hdf5_stall_guarded_continuation_completion_2026-07-12/
```

Key files include:

- `g_lo_guarded_continuation_completion_metadata.json`;
- `completion_summary.csv`;
- `qstat_final.csv`;
- `watchdog_summary.csv`;
- `run_output_inventory_summary.csv`;
- `next_step_recommendation.csv`;
- `local_asset_manifest.sha256`; and
- the retrieved compact source evidence under `remote_stage/`.

## Boundary

This completion turn used Chrome/Open OnDemand only to refresh the TPAC SSH
selector, then used repo-local terminal helpers for read-only completion
inspection and compact retrieval. It submitted no new PBS job and ran no
XRAiSE, PRAiSE, radio, cavity, source-age, or endpoint-comparison workflow. It
retrieved no bulky production payload and made no scientific-default change.
