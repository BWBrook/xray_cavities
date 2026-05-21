# 2026-05-21 - C-HI Full-Grid Retry Submitted

## Context

The first full-grid `C-HI` startup/checkpoint job failed:

```text
692369.kunanyi-ohpc  c_hi_fg_start  Exit_status=1
```

Follow-up diagnosis found that PLUTO had built, initialized, written the
initial `dbl.h5` and `flt.h5` files, and reached step 0. The failure was a
UCX/OpenMPI transport abort:

```text
Fatal: UD endpoint ... unhandled timeout error
```

with stack traces in `MPI_Allreduce` / `MPI_Allgather`, concentrated first on
nodes `n161`, `n163`, and `n164`.

Detailed evidence is in:

```text
agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md
```

## Retry Preparation

The production template now records and exports explicit MPI/UCX/OpenMPI tuning
environment variables through `mpirun`.

New retry wrapper:

```text
scripts/kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.pbs
```

New stage/submit helper:

```text
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_retry_ob1_tcp.sh
```

The retry deliberately differs from the first startup job:

- `RESTART_POLICY=auto`, so it should restart from the existing
  `data.0000.dbl.h5` checkpoint through `dbl.h5.out`
- same run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
- `walltime=08:00:00`, allowing for slower TCP transport
- OpenMPI forced away from UCX:
  - `OMPI_MCA_pml=ob1`
  - `OMPI_MCA_btl=self,vader,tcp`
  - `OMPI_MCA_btl_tcp_if_exclude=lo`
  - `OMPI_MCA_oob_tcp_if_exclude=lo`

## Submission

The first staging attempt accidentally used the default `kunanyi-via-nectar`
SCP route and failed with:

```text
ssh: connect to host <campus-ip> port 22: No route to host
```

The helper was rerun successfully with the direct jumpbox route:

```bash
TPAC_JUMPBOX_ALIAS=tpac-jumpbox \
TPAC_SCP_HOST=kunanyi \
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_retry_ob1_tcp.sh
```

Pre-submit remote checks passed:

```text
RETRY_REMOTE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles
RETRY_OUTPUT_HEAD=
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
```

Submitted job:

```text
SUBMITTED_JOB_ID=692504.kunanyi-ohpc
Job_Name = c_hi_fg_retry
job_state = Q
queue = normal
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 08:00:00
Mail_Users = barry.brook@utas.edu.au
```

## Follow-Up

After the PBS email lands, inspect:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.err
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/markers/
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/
```

Key questions:

- Did the wrapper select `RUN_KIND=h5_restart_0`?
- Did the MPI tuning environment show the `ob1`/TCP settings?
- Did the job reach a `DONE` marker?
- If it failed, did it fail with the same UCX signature, a TCP/OpenMPI
  signature, or a PLUTO/application-level issue?
