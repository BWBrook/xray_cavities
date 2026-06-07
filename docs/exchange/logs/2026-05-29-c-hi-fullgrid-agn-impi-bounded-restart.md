# 2026-05-29 C-HI Full-Grid AGN Intel/IMPI Bounded Restart

## Session Context

- Machine used: Mac Mini
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- Target: `kunanyi` via the usual TPAC jumpbox route
- Reason: test Patrick's AGN Intel/IMPI/HDF5/ZFP stack on the real full-grid
  `C-HI` particles case before spending another 80-node continuation.

## Local Scripts

The bounded restart used:

```bash
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_bounded_restart.sh
scripts/kunanyi/c_hi_fullgrid_agn_impi_bounded_restart.pbs
scripts/kunanyi/jet_setup_production_template.pbs
```

The production template now supports `KUNANYI_MODULE_STACK=agn_intel_impi`,
`MPI_FLAVOR=intelmpi`, and `FORCE_REBUILD=1` so the full-grid executable can be
rebuilt under Intel/IMPI while preserving existing restart outputs.

## Pre-Submit State

The existing run directory was:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles
```

The stage helper verified the expected full-grid restart state:

```text
data.0000.dbl.h5
data.0000.flt.h5
particles.0000.dbl
dbl.h5.out
```

The latest restart index was `0`:

```text
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
```

An old `DONE` marker from the previous walltime retry was archived to
`markers/history/` before submission.

## Submission

Command used:

```bash
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_bounded_restart.sh
```

Remote module/compiler evidence:

```text
intel/18.0.1.163
impi/2018.1.163
hdf5/1.12.1p
zfp/0.5.5
AGN_BOUNDED_MPICC=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
AGN_BOUNDED_MPIRUN=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
AGN_BOUNDED_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
AGN_BOUNDED_RESTART_INDEX=0
AGN_BOUNDED_RESTART_FILE=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/data.0000.dbl.h5
```

PBS job:

```text
Job Id: 696086.kunanyi-ohpc
Job_Name = c_hi_fg_agn8
queue = normal
Resource_List.select = 8:ncpus=28:mpiprocs=28
Resource_List.walltime = 02:00:00
```

## Result

The job completed successfully:

```text
resources_used.walltime = 00:39:20
Exit_status = 0
```

Key PBS stdout lines:

```text
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
FORCE_REBUILD=1
PLUTO_MAXTIME_HOURS=0.5
NRANKS=224
FORCE_REBUILD=1: removing built executable and source tree while preserving outputs
RUN_KIND=h5_restart_0
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 0
MPI_EXIT_CODE=0
```

Rank 0 log showed the expected restart and clean end:

```text
Number of processors: 224
> restarting from file #0 (dbl.h5)
Restarting from Particle File : ./outputs/particles.0000.dbl, idCounter = 32
Restarted with 0 local particles
> Starting computation...
step:0; t = 0.0000e+00; dt = 1.0000e-05; 0.0 %
step:100; t = 1.3780e+00; dt = 1.3781e-01; 0.0 %
> Writing file #1 (dbl.h5) to disk...
> Writing file #1 (flt.h5) to disk...
> Elapsed time 0d:0h:37m:54s
> Done
```

`dbl.h5.out` and `flt.h5.out` now both include output `1`:

```text
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.011234e+01 2.777278e-01 135 single_file little rho vx1 vx2 vx3 prs tr1
```

Fresh full-grid outputs:

```text
data.0001.dbl.h5
data.0001.dbl.xmf
data.0001.flt.h5
data.0001.flt.xmf
particles.0001.dbl
particles.0002.dbl
particles.0003.dbl
particles.0004.dbl
restart.out
```

## Error Scan

Absent signatures:

```text
Fatal: UD endpoint ... unhandled timeout error
MPI_ABORT
Segmentation fault
```

Non-fatal known caveats:

```text
Lmod has detected the following error: You can only have one compiler module loaded at a time.
/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem: line 11: git: command not found
SetOutputVar(): var_name 'energy' cannot be set/unset for writing
```

## Interpretation

Patrick's AGN Intel/IMPI path is now validated beyond tiny smoke: it can rebuild
PLUTO, restart the real full-grid `C-HI` particles case, write fresh HDF5 and
particle outputs, and exit cleanly on 8 `kunanyi` nodes / 224 ranks. The next
production choice is scale: run one more intermediate `16`/`32` node step, or
move to a bounded 80-node AGN Intel/IMPI continuation.
