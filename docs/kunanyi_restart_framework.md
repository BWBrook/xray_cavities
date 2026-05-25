# Kunanyi Restart Framework

Last updated: 2026-05-25

This note describes the restart-first operating pattern for long PLUTO jobs on
`kunanyi`. The key principle is simple: PBS jobs are disposable segments; the
simulation state is the restart catalogue and the corresponding `dbl.h5`
files.

## Current Default Route

From the home-network MacBook, use the Tailscale/deep-server route:

```bash
TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep
TPAC_SCP_HOST=kunanyi-via-deep
```

The generic Kunanyi helpers now default to that route:

- `scripts/kunanyi/run_on_kunanyi.sh`
- `scripts/kunanyi/copy_to_kunanyi.sh`
- `scripts/kunanyi/fetch_from_kunanyi.sh`

Campus/direct and Nectar fallback routes remain available by overriding the
environment variables:

```bash
TPAC_JUMPBOX_ALIAS=tpac-jumpbox TPAC_SCP_HOST=kunanyi ...
TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar TPAC_SCP_HOST=kunanyi-via-nectar ...
```

The TPAC Open OnDemand jumpbox window is still required.

## What Counts As Simulation State

For static-grid PLUTO, restart-capable outputs are `*.dbl.h5` files. The
authoritative restart catalogue is:

```text
<problem>/outputs/dbl.h5.out
```

The production template now verifies that the latest numeric catalogue entry
has a corresponding file before trying to restart from it:

```text
data.NNNN.dbl.h5
```

For the current full-grid `C-HI` startup path, the run directory is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles
```

## Inspect After A PBS Email

When Barry receives a PBS email, first inspect the remote state:

```bash
scripts/kunanyi/inspect_c_hi_fullgrid_restart_state.sh <jobid>
```

This reports:

- `qstat -xf` summary, if the job is still queryable
- `DONE`/`FAILED` markers and marker history
- latest restart catalogue entries and whether the referenced files exist
- output counts and sizes
- recent MPI/PLUTO log signatures

Interpretation rules:

- PBS `Exit_status = 0` plus `DONE` means the segment ended cleanly.
- PBS non-zero status is authoritative even if an old marker says `DONE`.
- `FAILED` marker reason `ucx_ud_endpoint_timeout` points to OpenMPI/UCX
  transport/fabric trouble, not a PLUTO science configuration problem.
- `FAILED` marker reason `mpi_signal_15_or_walltime` usually means PBS or
  transport termination; check PBS stderr and walltime.
- If only output `0` exists, the full-grid run has not yet advanced beyond
  the startup checkpoint.

## Submit A Continuation Segment

The standard continuation wrapper is:

```text
scripts/kunanyi/c_hi_fullgrid_continue.pbs
```

It uses:

```text
select=80:ncpus=28:mpiprocs=28
walltime=48:00:00
RESTART_POLICY=auto
PLUTO_MAXTIME_HOURS=47.5
```

The local stage/submit helper is:

```bash
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh
```

Before submission, the helper:

- stages the current production template and continuation wrapper
- verifies that `problem/pluto` exists
- verifies that `dbl.h5.out` exists
- verifies that the latest `dbl.h5.out` index has a corresponding
  `data.NNNN.dbl.h5` file
- archives and clears stale `DONE`/`FAILED` markers into `markers/history/`
- submits the PBS wrapper

To require at least a particular restart index:

```bash
MIN_RESTART_INDEX=1 scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh
```

For the current full-grid `C-HI` lane, do not submit another 80-node segment
until the OpenMPI/UCX transport question has been resolved with Stas/Patrick or
TPAC. Plain OB1/TCP avoided the UCX UD timeout but was too slow to be useful.

## Production Template Guarantees

`scripts/kunanyi/jet_setup_production_template.pbs` now:

- chooses the latest valid `dbl.h5` restart file when `RESTART_POLICY=auto`
- logs `RUN_KIND` and `RUN_ARGS`
- exports OpenMPI/UCX tuning variables to MPI ranks
- records `MPI_EXIT_CODE`
- classifies common MPI failures:
  - `ucx_ud_endpoint_timeout`
  - `mpi_signal_15_or_walltime`
  - `segmentation_fault`
  - `mpi_abort`
  - `hdf5_related_mpi_failure`
- writes `DONE` only after a zero exit
- writes `FAILED` on non-zero exit or TERM/INT
- removes stale `DONE` when a failure lands

## Current Lessons From Jobs 692369 And 692504

Job `692369.kunanyi-ohpc`:

- built and initialized successfully
- wrote initial HDF5 output
- failed in UCX/OpenMPI with repeated
  `Fatal: UD endpoint ... unhandled timeout error`
- first fatal messages were concentrated around `n161`, `n163`, and `n164`

Job `692504.kunanyi-ohpc`:

- restarted with `RUN_KIND=h5_restart_0`
- forced `OMPI_MCA_pml=ob1` and `OMPI_MCA_btl=self,vader,tcp`
- avoided the UCX UD signature
- made no useful progress beyond output `0`
- was killed by PBS walltime at `08:00:52`

The conclusion is not that the PLUTO configuration is wrong. The conclusion is
that the full-grid production lane must be restartable and transport-aware
before we spend multi-day allocations.
