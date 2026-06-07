# 2026-05-29 C-HI Full-Grid AGN Intel/IMPI 80-Node Continue Submitted

## Session Context

- Machine used: Mac Mini
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- Target: `kunanyi` via the usual TPAC jumpbox route
- Reason: go straight from the green 8-node AGN Intel/IMPI full-grid restart
  to an 80-node continuation. This should either reproduce a large-scale
  transport/runtime failure under the AGN stack or validate the stack for
  production continuation.

## Local Scripts

Added and used:

```bash
scripts/kunanyi/c_hi_fullgrid_agn_impi_80node_continue.pbs
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_80node_continue.sh
```

The wrapper requests:

```text
select=80:ncpus=28:mpiprocs=28
walltime=48:00:00
PLUTO_MAXTIME_HOURS=47.5
RESTART_POLICY=auto
ALLOW_DONE_RERUN=1
FORCE_REBUILD=1
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
```

The stage helper requires `MIN_RESTART_INDEX=1` by default so this launch
cannot silently fall back to the initial output `0` checkpoint.

## Submission

Command used:

```bash
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_80node_continue.sh
```

The helper verified the intended AGN stack immediately before `qsub`:

```text
intel/18.0.1.163
impi/2018.1.163
hdf5/1.12.1p
zfp/0.5.5
AGN_80_MPICC=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
AGN_80_MPIRUN=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
AGN_80_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
```

Verified restart state:

```text
AGN_80_REMOTE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles
AGN_80_REMOTE_CONFIG_DIR=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19/C-HI/particles
AGN_80_RESTART_INDEX=1
AGN_80_RESTART_FILE=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/data.0001.dbl.h5
```

`dbl.h5.out` submit tail:

```text
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.011234e+01 2.777278e-01 135 single_file little rho vx1 vx2 vx3 prs tr1
```

PBS state at submit:

```text
SUBMITTED_JOB_ID=696197.kunanyi-ohpc
Job_Name = c_hi_fg_agn80
job_state = Q
queue = normal
Mail_Users = barry.brook@utas.edu.au
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 48:00:00
```

Remote artifacts:

```text
/u/bwbrook/codex_kunanyi/jet_setup_production_template_latest.pbs
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.pbs
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.err
```

## Follow-Up

Barry will report back after the PBS completion email. First inspection target:

```bash
qstat -x -f 696197.kunanyi-ohpc
```

Then inspect the remote stdout/stderr and PLUTO logs under:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/logs/
```
