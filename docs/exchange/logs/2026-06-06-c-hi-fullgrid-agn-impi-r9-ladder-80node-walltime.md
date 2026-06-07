# C-HI full-grid AGN IMPI restart ladder, 80-node rung walltime

Date: 2026-06-06

## Summary

The 80-node restart-ladder rung reproduced the restart stall at 2240 ranks. It
was killed by PBS walltime before reaching computation or writing any new
isolated output.

This confirms the node-count threshold found by the ladder: 64 nodes / 1792
ranks is clean, while 80 nodes / 2240 ranks stalls during HDF5 restart read.

## PBS Result

```text
PBS Job Id: 697285.kunanyi-ohpc
Job Name:   c_hi_r9_80n
Exit_status=271
resources_used.cpupercent=2816
resources_used.cput=55:16:36
resources_used.mem=4232952kb
resources_used.ncpus=2240
resources_used.vmem=23487404kb
resources_used.walltime=02:01:12
Resource_List.select=80:ncpus=28:mpiprocs=28
Resource_List.walltime=02:00:00
```

PBS stderr:

```text
=>> PBS: job killed: walltime 7262 exceeded limit 7200
Terminated
```

## Launch Evidence

```text
LADDER_NODES=80
JOB_START=2026-06-06T00:10:53Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=2240
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
JOB_SIGNAL=TERM
JOB_END=2026-06-06T02:11:45Z
```

No `MPI_EXIT_CODE` was emitted.

Marker state:

```text
FAILED=status=failed
case_id=C-HI
case_variant=particles
pbs_jobid=697285.kunanyi-ohpc
exit_code=143
signal=TERM
finished_utc=2026-06-06T02:11:45Z
```

## Product Evidence

Run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node
```

The run did not write new products:

```text
missing data.0010.dbl.h5
missing data.0044.flt.h5
missing data.0045.flt.h5
missing particles.4278.dbl
counts dbl_h5=0
counts flt_h5=0
counts particles=1
```

Only the source restart symlinks existed:

```text
data.0009.dbl.h5 -> 2026-06-01 fresh run data.0009.dbl.h5
particles.4277.dbl -> 2026-06-01 fresh run particles.4277.dbl
```

The output catalogues remained at their source lengths:

```text
dbl.h5.out lines=10
flt.h5.out lines=44
restart.out lines=11
```

## Rank Log Evidence

There are `2240` per-rank logs under:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node/C-HI/particles/problem/outputs/logs
```

Sampled ranks `0`, `1`, `27`, `28`, `1119`, `1120`, `2238`, and `2239` all
ended at:

```text
> restarting from file #9 (dbl.h5)
```

Aggregate scan:

```text
TOTAL=2240
RESTART_LAST=2240
DONE_LAST=0
WRITING_LAST=0
OTHER_LAST=0
RESTART_SEEN=2240
DONE_SEEN=0
WRITING_SEEN=0
```

## Interpretation

The 80-node restart stall is reproducible under the AGN Intel/IMPI/HDF5 stack
from the clean fresh output `9`. Since 64 nodes / 1792 ranks completes cleanly,
64 nodes is the current production sweet spot for C-HI restarts.

The failure boundary lies between 64 and 80 nodes and appears to be a parallel
HDF5 restart-read / MPI-IO / filesystem-scale issue rather than a simulation
compute issue.
