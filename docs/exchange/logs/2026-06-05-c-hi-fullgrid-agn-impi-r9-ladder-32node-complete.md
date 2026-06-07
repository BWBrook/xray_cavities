# 2026-06-05 - C-HI AGN Intel/IMPI output-9 restart ladder 32-node rung complete

## Summary

The 32-node restart-ladder rung completed green. It restarted from the clean
fresh-run output `9` at 32 nodes / 896 ranks under the AGN Intel/IMPI/HDF5/ZFP
stack with `HDF5_USE_FILE_LOCKING=FALSE`, reached computation, and wrote new
isolated outputs.

## PBS Result

```text
PBS Job Id: 697223.kunanyi-ohpc
Job Name:   c_hi_r9_32n
Exit_status=0
resources_used.cpupercent=2797
resources_used.cput=15:27:14
resources_used.mem=14319056kb
resources_used.ncpus=896
resources_used.vmem=29400936kb
resources_used.walltime=00:35:03
```

## Launch and Marker State

```text
LADDER_NODES=32
JOB_START=2026-06-05T06:19:02Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
NRANKS=896
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
MPI_EXIT_CODE=0
JOB_END=2026-06-05T06:53:35Z
```

Marker:

```text
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=697223.kunanyi-ohpc
finished_utc=2026-06-05T06:53:35Z
```

## Products

The rung output tree is isolated from the clean fresh production run:

```text
rung_run_root=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node
rung_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node/C-HI/particles
source_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
```

The input restart files remained symlinks to the known-good fresh run:

```text
data.0009.dbl.h5 -> /scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5
particles.4277.dbl -> /scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/particles.4277.dbl
```

New isolated output products were written:

```text
data.0010.dbl.h5 size=63G
data.0044.flt.h5 size=42G
data.0045.flt.h5
particles.4278.dbl ... particles.4307.dbl
restart.out size=1.4K
```

Catalogue tails:

```text
dbl.h5.out_lines=11
10 1.320512e+04 3.139112e-01 42487 single_file little rho vx1 vx2 vx3 prs tr1

flt.h5.out_lines=46
45 1.320512e+04 3.139112e-01 42487 single_file little rho vx1 vx2 vx3 prs tr1
```

Portable output counts:

```text
dbl_h5_count=2
flt_h5_count=2
particle_count=31
rank_log_files=896
```

`dbl_h5_count=2` includes the symlinked input `data.0009.dbl.h5` plus the new
regular `data.0010.dbl.h5`; `particle_count=31` includes the symlinked input
`particles.4277.dbl` plus new particle outputs `4278` through `4307`.

## Rank Log Evidence

Sampled ranks `0`, `1`, `27`, `28`, `447`, `448`, `894`, and `895` all reached
particle file write `#4307` and ended with `> Done`.

Representative tail content included:

```text
> Writing particle file #4307 (dbl) to disk...
> Elapsed time              0d:0h:33m:13s
> Average time/step         4.69e-02  (sec)
> Local time                Fri Jun  5 16:53:28 2026
> Done
```

## Caveat

PBS stderr still contains the known non-fatal Lmod warning about an attempted
`gnu8/8.3.0` load while `intel` is active. It did not block this run.

## Interpretation

Restart from clean fresh output `9` is valid through 32 nodes / 896 ranks. The
restart failure threshold is therefore above 896 ranks and below or at the
80-node / 2240-rank case that failed in job `696911.kunanyi-ohpc`.

## Next Step

Continue the ladder with the 48-node rung:

```bash
LADDER_NODES=48 scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_restart_ladder.sh
```
