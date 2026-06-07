# C-HI full-grid AGN IMPI restart ladder, 80-node rung submitted

Date: 2026-06-06

## Summary

Because the 64-node rung completed cleanly, the 80-node restart-ladder rung was
staged and submitted from the same successful fresh full-grid output `9`.

This is the key comparison rung against the earlier 80-node restart probe
`696911.kunanyi-ohpc`, which stalled at 2240 ranks.

## PBS Submission

```text
SUBMITTED_JOB_ID=697285.kunanyi-ohpc
Job Id: 697285.kunanyi-ohpc
Job_Name = c_hi_r9_80n
job_state = Q
queue = normal
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 02:00:00
Mail_Users = barry.brook@utas.edu.au
```

## Paths

```text
wrapper=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs
stdout=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_80node.out
stderr=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_80node.err
source_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
rung_run_root=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node
rung_workdir=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node/C-HI/particles
```

## Pre-Submit Validation

```text
AGN_RESTART_LADDER_NODES=80
AGN_RESTART_LADDER_SELECT=80:ncpus=28:mpiprocs=28
AGN_RESTART_LADDER_WALLTIME=02:00:00
AGN_RESTART_LADDER_PLUTO_MAXTIME_HOURS=0.5
AGN_RESTART_LADDER_MPICC=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
AGN_RESTART_LADDER_MPIRUN=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
AGN_RESTART_LADDER_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
AGN_RESTART_LADDER_HDF5_USE_FILE_LOCKING=FALSE
AGN_RESTART_LADDER_REMOTE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-80node/C-HI/particles
AGN_RESTART_LADDER_SOURCE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
AGN_RESTART_LADDER_RESTART_INDEX=9
AGN_RESTART_LADDER_RESTART_FILE=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5
AGN_RESTART_LADDER_PARTICLE_FILE=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/particles.4277.dbl
```

Catalog source tails before submission:

```text
dbl.h5.out:
5 7.664898e+03 3.139112e-01 24838 single_file little rho vx1 vx2 vx3 prs tr1
6 9.198040e+03 3.139112e-01 29722 single_file little rho vx1 vx2 vx3 prs tr1
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1

flt.h5.out:
39 1.195732e+04 3.139112e-01 38512 single_file little rho vx1 vx2 vx3 prs tr1
40 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
41 1.257039e+04 3.139112e-01 40465 single_file little rho vx1 vx2 vx3 prs tr1
42 1.287708e+04 3.139112e-01 41442 single_file little rho vx1 vx2 vx3 prs tr1
43 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

## Expected Follow-Up

When Barry's PBS completion email arrives for `697285.kunanyi-ohpc`, inspect
whether the 80-node restart reaches computation and writes new isolated outputs.
If it stalls, package the 64-node pass / 80-node fail threshold for Patrick and
TPAC. If it is green, compare directly against the earlier 80-node restart probe
`696911.kunanyi-ohpc` before deciding whether the previous failure was transient
or setup-specific.
