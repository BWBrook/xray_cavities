# 2026-05-20 C-HI Full-Grid Startup Submitted

## Summary

The first full-grid `C-HI` startup/checkpoint gate was staged to `kunanyi` and
submitted from campus/`eduroam`.

This is the bounded full-grid startup/restart-output gate, not the full
48-hour science production segment.

## Submission

Command run locally:

```bash
cd /Users/bwbrook/papers/xray_cavities
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
```

The stage/submit helper:

- opened the TPAC Open OnDemand jumpbox SSH window in Safari
- prepared `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19`
- copied the full-grid `C-HI` rendered config bundle
- copied `jet_setup_production_template.pbs`
- copied `c_hi_fullgrid_startup_checkpoint.pbs`
- verified the remote render before submission
- submitted the PBS job with `qsub`

## PBS Job

```text
PBS job id: 692369.kunanyi-ohpc
PBS name: c_hi_fg_start
Initial state: Q
Queue: normal
Mail users: barry.brook@utas.edu.au
Resource_List.select: 80:ncpus=28:mpiprocs=28
Resource_List.walltime: 04:00:00
```

## Remote Validation Before Submission

```text
REMOTE_RENDER_VALIDATION_OK=1
NPARTICLES=32.0
```

## Runtime Shape

The wrapper exports:

```text
CASE_ID=C-HI
CASE_VARIANT=particles
CASE_CONFIG_DIR=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19/C-HI/particles
RUN_ROOT=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup
PLUTO_MAXTIME_HOURS=3.5
RESTART_POLICY=force-fresh
ALLOW_DONE_RERUN=1
BUILD_JOBS=28
```

The requested run shape is:

```text
select=80:ncpus=28:mpiprocs=28
walltime=04:00:00
```

## Expected Next Action

Wait for the PBS email notification. Once the job has ended, retrieve or
inspect:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_checkpoint.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_checkpoint.err
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup
```

Acceptance checks for this gate:

- PLUTO problem setup/build completed
- MPI startup used the expected nodefile/rank count
- HDF5 output catalogue exists
- at least one restart-capable `dbl.h5` output exists, or a clear failure log
  explains why startup ended earlier
- source provenance logs exist
- `DONE` or `FAILED` marker exists
