# 2026-06-05 - C-HI AGN Intel/IMPI output-9 restart ladder 32-node rung submitted

## Summary

The 16-node rung completed green, so the next node-count ladder rung has been
staged and submitted. It tests restart from the same clean fresh-run output `9`
at 32 nodes / 896 ranks under the AGN Intel/IMPI/HDF5/ZFP stack with
`HDF5_USE_FILE_LOCKING=FALSE`.

As with the earlier rungs, this job is isolated from the successful fresh
production tree: the helper copies small catalogues and metadata, then symlinks
the large HDF5 and particle restart inputs.

## Submission

```text
SUBMITTED_JOB_ID=697223.kunanyi-ohpc
Job Id: 697223.kunanyi-ohpc
    Job_Name = c_hi_r9_32n
    job_state = Q
    queue = normal
    Mail_Users = barry.brook@utas.edu.au
    Resource_List.select = 32:ncpus=28:mpiprocs=28
    Resource_List.walltime = 02:00:00
```

## Paths

```text
wrapper=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs
stdout=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_32node.out
stderr=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_32node.err
source_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
rung_run_root=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node
rung_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node/C-HI/particles
```

## Pre-Submit Validation

```text
AGN_RESTART_LADDER_NODES=32
AGN_RESTART_LADDER_SELECT=32:ncpus=28:mpiprocs=28
AGN_RESTART_LADDER_WALLTIME=02:00:00
AGN_RESTART_LADDER_PLUTO_MAXTIME_HOURS=0.5
AGN_RESTART_LADDER_MPICC=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
AGN_RESTART_LADDER_MPIRUN=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
AGN_RESTART_LADDER_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
AGN_RESTART_LADDER_HDF5_USE_FILE_LOCKING=FALSE
AGN_RESTART_LADDER_REMOTE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node/C-HI/particles
AGN_RESTART_LADDER_SOURCE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
AGN_RESTART_LADDER_RESTART_INDEX=9
AGN_RESTART_LADDER_RESTART_FILE=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5
AGN_RESTART_LADDER_PARTICLE_FILE=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/particles.4277.dbl
```

`dbl.h5.out` tail at submit:

```text
5 7.664898e+03 3.139112e-01 24838 single_file little rho vx1 vx2 vx3 prs tr1
6 9.198040e+03 3.139112e-01 29722 single_file little rho vx1 vx2 vx3 prs tr1
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

`flt.h5.out` tail at submit:

```text
39 1.195732e+04 3.139112e-01 38512 single_file little rho vx1 vx2 vx3 prs tr1
40 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
41 1.257039e+04 3.139112e-01 40465 single_file little rho vx1 vx2 vx3 prs tr1
42 1.287708e+04 3.139112e-01 41442 single_file little rho vx1 vx2 vx3 prs tr1
43 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

## Expected Follow-Up

When Barry's PBS email lands for `697223.kunanyi-ohpc`, inspect:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_32node.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_32node.err
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node/C-HI/particles/markers
/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-32node/C-HI/particles/problem/outputs
```

Pass criterion: PLUTO gets past `> restarting from file #9 (dbl.h5)`, reaches
computation, and writes a new isolated output such as `data.0010.dbl.h5`.

If this rung is green, continue with:

```bash
LADDER_NODES=48 scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_restart_ladder.sh
```

If this rung stalls, package the 16-node pass / 32-node fail threshold for
Patrick and TPAC.
