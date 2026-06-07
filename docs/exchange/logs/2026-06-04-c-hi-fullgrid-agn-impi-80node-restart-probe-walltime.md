# 2026-06-04 - C-HI AGN Intel/IMPI 80-node restart probe walltime

## Summary

PBS job `696911.kunanyi-ohpc` (`c_hi_fg_r9probe`) reproduced the full-scale
restart blocker. It restarted from the clean fresh-run double-precision HDF5
output `data.0009.dbl.h5` under the AGN Intel/IMPI/HDF5/ZFP stack with
`HDF5_USE_FILE_LOCKING=FALSE`, but was killed at the 2-hour walltime before
reaching computation or writing any new products.

## PBS Result

```text
Job Id: 696911.kunanyi-ohpc
Job_Name = c_hi_fg_r9probe
resources_used.cpupercent = 2815
resources_used.cput = 56:05:35
resources_used.mem = 4231440kb
resources_used.ncpus = 2240
resources_used.vmem = 23486976kb
resources_used.walltime = 02:01:12
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 02:00:00
Exit_status = 271
```

PBS stderr ended with:

```text
=>> PBS: job killed: walltime 7262 exceeded limit 7200
Terminated
```

## Launch State

```text
JOB_START=2026-06-03T05:21:21Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=2240
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
JOB_SIGNAL=TERM
JOB_END=2026-06-03T07:22:18Z
```

The marker directory contained only `FAILED`:

```text
status=failed
case_id=C-HI
case_variant=particles
pbs_jobid=696911.kunanyi-ohpc
exit_code=143
signal=TERM
finished_utc=2026-06-03T07:22:18Z
```

## Product State

No new restart output was written.

```text
dbl.h5.out_lines=10
flt.h5.out_lines=44
missing data.0010.dbl.h5
missing data.0044.flt.h5
missing particles.4278.dbl
dbl_h5_count=10
flt_h5_count=44
particle_count=4278
```

`dbl.h5.out` still ends at output `9`:

```text
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

`flt.h5.out` still ends at output `43`:

```text
43 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

## Rank Log Evidence

The run has `2240` per-rank PLUTO logs, about `1.03 GB` total. Full all-rank
content scans were slow on remote scratch, so the final classification used
direct deterministic rank samples plus the unchanged output catalogues.

Sampled ranks:

```text
pluto.0.log
pluto.1.log
pluto.27.log
pluto.28.log
pluto.1119.log
pluto.1120.log
pluto.2238.log
pluto.2239.log
```

All sampled rank logs ended at:

```text
> Number of processors: 2240
> Proc size:            ...
> Parallel Directions:  X1/X2/X3
> restarting from file #9 (dbl.h5)
```

No sampled tail showed a subsequent `Starting computation`, particle restart,
`step:`, or write line after the restart line.

## Interpretation

This is a clean reproduction of the full-scale restart-specific blocker from a
known-good fresh output. The previous fresh 80-node job `696619.kunanyi-ohpc`
completed, the final HDF5 products were readable, and this restart probe used
the same AGN Intel/IMPI/HDF5/ZFP stack with `HDF5_USE_FILE_LOCKING=FALSE`.

The failure is therefore best framed as a 2240-rank parallel HDF5 restart read
stall or restart-triggered MPI-IO/filesystem-scale issue, not a general
inability to run the full-grid case and not the old OpenMPI/UCX abort
signature.

## Recommendation

Do not rerun the same 80-node restart path unchanged. Escalate the evidence to
Patrick/TPAC. If further probing is useful before support action, run a bounded
node-count ladder from the same clean output `9` to find the restart threshold.
The fresh full-duration path remains viable; segmented full-scale restart does
not yet.
