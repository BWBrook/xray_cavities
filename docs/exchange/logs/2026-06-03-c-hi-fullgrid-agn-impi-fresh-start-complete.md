# 2026-06-03 C-HI Full-Grid AGN IMPI Fresh Start Complete

## Summary

The fresh 80-node full-grid `C-HI` particles run submitted as
`696619.kunanyi-ohpc` completed successfully under the AGN
Intel/IMPI/HDF5/ZFP stack with `HDF5_USE_FILE_LOCKING=FALSE`.

This validates Patrick's suggested fresh-run pathway at full 80-node /
2240-rank scale. The earlier 80-node continuation failure is therefore best
kept separate as evidence for a restart-specific or restart-triggered parallel
HDF5/I/O problem.

## PBS Result

```text
Job Id: 696619.kunanyi-ohpc
Job_Name = c_hi_fg_fresh
resources_used.cpupercent = 2822
resources_used.cput = 1329:31:13
resources_used.mem = 7216684kb
resources_used.ncpus = 2240
resources_used.vmem = 26366212kb
resources_used.walltime = 47:33:46
job_state = F
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 48:00:00
Exit_status = 0
```

## Marker and Launch State

```text
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=696619.kunanyi-ohpc
finished_utc=2026-06-03T02:40:14Z
```

```text
JOB_START=2026-06-01T03:06:33Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=2240
RUN_KIND=fresh
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5
MPI_EXIT_CODE=0
JOB_END=2026-06-03T02:40:14Z
```

## Output Evidence

```text
output_volume=2.5T
h5_dbl_count=10
h5_flt_count=44
particle_count=4278
rank_log_files=2240
```

`dbl.h5.out` has 10 lines and ends at output `9`:

```text
5 7.664898e+03 3.139112e-01 24838 single_file little rho vx1 vx2 vx3 prs tr1
6 9.198040e+03 3.139112e-01 29722 single_file little rho vx1 vx2 vx3 prs tr1
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

`flt.h5.out` has 44 lines and ends at output `43`:

```text
39 1.195732e+04 3.139112e-01 38512 single_file little rho vx1 vx2 vx3 prs tr1
40 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
41 1.257039e+04 3.139112e-01 40465 single_file little rho vx1 vx2 vx3 prs tr1
42 1.287708e+04 3.139112e-01 41442 single_file little rho vx1 vx2 vx3 prs tr1
43 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

Final output files include:

```text
2026-06-03 12:39  67318639276 data.0009.dbl.h5
2026-06-03 12:40  44890581676 data.0043.flt.h5
2026-06-03 12:40     20220069 particles.4277.dbl
```

## Log Evidence

Sampled rank logs ended cleanly. For example:

```text
> Writing particle file #4277 (dbl) to disk...
> Total allocated memory  43799.46 Mb (proc #0)
> Elapsed time              1d:23h:32m:51s
> Average time/step         4.06e+00  (sec)
> Local time                Wed Jun  3 12:40:08 2026
> Done
```

The checked stdout/stderr/sample rank-log tails showed no UCX, UD endpoint,
`MPI_ABORT`, segmentation fault, or HDF5 diagnostic signature.

Known non-fatal stderr caveats remain:

- Lmod compiler-module warning while `intel` is active.
- `setup-problem: line 11: git: command not found`.
