# C-HI full-grid AGN IMPI restart ladder, 48-node rung complete

Date: 2026-06-05

## Summary

The 48-node restart-ladder rung completed cleanly from the successful fresh
full-grid output `9` under the AGN Intel/IMPI/HDF5/ZFP stack.

This extends the known-good restart scale to 48 nodes / 1344 ranks. The known
80-node restart probe still failed/stalled at 2240 ranks, so the current failure
threshold is above 1344 ranks and below or at 2240 ranks.

## PBS Result

```text
PBS Job Id: 697235.kunanyi-ohpc
Job Name:   c_hi_r9_48n
Exit_status=0
resources_used.cpupercent=2792
resources_used.cput=15:09:47
resources_used.mem=11132116kb
resources_used.ncpus=1344
resources_used.vmem=27543320kb
resources_used.walltime=00:34:58
Resource_List.select=48:ncpus=28:mpiprocs=28
Resource_List.walltime=02:00:00
```

## Launch Evidence

```text
LADDER_NODES=48
JOB_START=2026-06-05T07:33:33Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=1344
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
MPI_EXIT_CODE=0
JOB_END=2026-06-05T08:07:58Z
```

Marker state:

```text
DONE=status=done
case_id=C-HI
case_variant=particles
pbs_jobid=697235.kunanyi-ohpc
finished_utc=2026-06-05T08:07:58Z
```

## Product Evidence

Run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-48node
```

Source fresh run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh
```

New isolated products:

```text
data.0010.dbl.h5 63G
data.0044.flt.h5 42G
data.0045.flt.h5 42G
particles.4278.dbl ... particles.4320.dbl
```

Catalog tails:

```text
dbl.h5.out:
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
10 1.324467e+04 3.139112e-01 42613 single_file little rho vx1 vx2 vx3 prs tr1

flt.h5.out:
44 1.318377e+04 3.139112e-01 42419 single_file little rho vx1 vx2 vx3 prs tr1
45 1.324467e+04 3.139112e-01 42613 single_file little rho vx1 vx2 vx3 prs tr1
```

The source restart inputs remained symlinks:

```text
data.0009.dbl.h5 -> 2026-06-01 fresh run data.0009.dbl.h5
particles.4277.dbl -> 2026-06-01 fresh run particles.4277.dbl
```

## Rank Log Evidence

There are `1344` per-rank logs under:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-48node/C-HI/particles/problem/outputs/logs
```

Files are named `pluto.<rank>.log`. Sampled ranks `0`, `1`, `27`, `28`,
`671`, `672`, `1342`, and `1343` all reached particle write `#4320` and ended
with:

```text
> Done
```

A full non-done scan over `pluto.*.log` returned no paths.

## Notes

The only stderr content was the recurring non-fatal Lmod warning about loading
`gnu8/8.3.0` while `intel` is active through the default `ohpc` module path.
The active stack reported in stdout remained the intended AGN Intel/IMPI stack.
