# 2026-05-22 C-HI Full-Grid Retry Walltime Kill

## Summary

Retry job `692504.kunanyi-ohpc` (`c_hi_fg_retry`) ran for the full requested
`8` hour walltime and was killed by PBS:

```text
Exit_status=271
resources_used.walltime=08:00:52
resources_used.ncpus=2240
resources_used.cpupercent=2818
```

The exit status is explained by PBS stderr:

```text
=>> PBS: job killed: walltime 28842 exceeded limit 28800
```

## What Worked

The retry used the intended restart and transport settings:

```text
RUN_KIND=h5_restart_0
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 3.5 -h5restart 0
OMPI_MCA_pml=ob1
OMPI_MCA_btl=self,vader,tcp
OMPI_MCA_btl_tcp_if_exclude=lo
OMPI_MCA_oob_tcp_if_exclude=lo
```

The job reused the existing full-grid run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles
```

## What Did Not Work

The retry made no useful physical-time progress beyond the initial output
created by the first job:

```text
dbl.h5.out: 0 0.000000e+00 1.000000e-05 ...
flt.h5.out: 0 0.000000e+00 1.000000e-05 ...
data h5 count: 2
particle dbl count: 1
```

Only these science outputs exist:

```text
data.0000.dbl.h5
data.0000.flt.h5
particles.0000.dbl
```

The main redirected MPI log for job `692504` contains signal-15 termination
noise and an `mpirun` finalization segfault after PBS killed the job. It does
not show the previous UCX UD timeout signature.

## Interpretation

This was not a PLUTO setup/configuration failure. The retry restarted from the
initial HDF5 checkpoint correctly and then exhausted walltime before producing
any additional output.

The OB1/TCP fallback avoided the first job's UCX UD transport abort, but it is
not a viable `80` node production transport path for this full-grid PLUTO
case. The low effective CPU use relative to the `2240` allocated ranks is
consistent with MPI transport/collective stalls rather than a productive
simulation segment.

## Marker Issue

The remote marker directory showed a misleading `DONE` marker even though PBS
reported `Exit_status=271`:

```text
markers/DONE
status=done
pbs_jobid=692504.kunanyi-ohpc
```

The local production template has been patched after this diagnosis so future
non-zero `mpirun` exits and TERM/INT signals write `FAILED` and remove stale
`DONE` markers.

## Recommended Next Move

Do not rerun the `80` node full-grid case with plain TCP.

Recommended sequence:

1. Ask TPAC about the UCX/OpenMPI failure from job `692369.kunanyi-ohpc`,
   especially the repeated `UD endpoint ... unhandled timeout error` on nodes
   around `n161`, `n163`, and `n164`.
2. Test a smaller transport ladder or an alternate UCX configuration that
   avoids UD without falling all the way back to TCP.
3. Keep the existing `data.0000.dbl.h5` checkpoint, but treat it only as a
   startup artifact until a reliable transport path advances beyond output `0`.
