# 2026-06-05 - C-HI AGN Intel/IMPI output-9 restart ladder 8-node rung complete

## Summary

The first node-count ladder rung completed green. It restarted from the clean
fresh-run output `9` at 8 nodes / 224 ranks under the AGN Intel/IMPI/HDF5/ZFP
stack with `HDF5_USE_FILE_LOCKING=FALSE`, reached computation, and wrote new
isolated outputs.

## PBS Result

```text
PBS Job Id: 697160.kunanyi-ohpc
Job Name:   c_hi_r9_08n
Exit_status=0
resources_used.cpupercent=2802
resources_used.cput=17:40:28
resources_used.mem=46453576kb
resources_used.ncpus=224
resources_used.vmem=59770212kb
resources_used.walltime=00:39:50
```

## Launch and Marker State

```text
LADDER_NODES=8
JOB_START=2026-06-05T03:31:51Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=224
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
MPI_EXIT_CODE=0
JOB_END=2026-06-05T04:10:41Z
```

Marker:

```text
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=697160.kunanyi-ohpc
finished_utc=2026-06-05T04:10:41Z
```

## Products

The rung output tree is isolated from the clean fresh production run:

```text
rung_run_root=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node
rung_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node/C-HI/particles
source_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
```

The input restart files remained symlinks to the known-good fresh run:

```text
data.0009.dbl.h5 -> /scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5
particles.4277.dbl -> /scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/particles.4277.dbl
```

New isolated output products were written:

```text
data.0010.dbl.h5 size=67318639276
data.0044.flt.h5 size=44890581676
particles.4278.dbl ... particles.4287.dbl
restart.out size=1408
```

Catalogue tails:

```text
dbl.h5.out_lines=11
10 1.314390e+04 3.139112e-01 42292 single_file little rho vx1 vx2 vx3 prs tr1

flt.h5.out_lines=45
44 1.314390e+04 3.139112e-01 42292 single_file little rho vx1 vx2 vx3 prs tr1
```

Portable output counts:

```text
dbl_h5_count=2
flt_h5_count=1
particle_count=11
rank_log_files=224
```

`dbl_h5_count=2` includes the symlinked input `data.0009.dbl.h5` plus the new
regular `data.0010.dbl.h5`; `particle_count=11` includes the symlinked input
`particles.4277.dbl` plus new particle outputs `4278` through `4287`.

## Rank Log Evidence

Sampled ranks `0`, `1`, `27`, `28`, `111`, `112`, `222`, and `223` all reached
the expected writes and ended with `> Done`.

Representative tail content included:

```text
> Max time 0.500000 hours reached.
> Writing file #10 (dbl.h5) to disk...
> Writing file #44 (flt.h5) to disk...
> Writing particle file #4287 (dbl) to disk...
> Elapsed time 0d:0h:38m:4s
> Done
```

## Interpretation

Restart from clean fresh output `9` is valid at 8 nodes / 224 ranks. The
restart failure threshold is therefore above 224 ranks and below or at the
80-node / 2240-rank case that failed in job `696911.kunanyi-ohpc`.

## Next Step

Continue the ladder with the 16-node rung:

```bash
LADDER_NODES=16 scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_restart_ladder.sh
```
