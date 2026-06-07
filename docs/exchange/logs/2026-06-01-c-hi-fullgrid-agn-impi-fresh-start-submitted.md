# 2026-06-01 C-HI Full-Grid AGN IMPI Fresh Start Submitted

## Context

Patrick advised a fresh run rather than a restart from previous outputs. He
also suggested using `HDF5_USE_FILE_LOCKING=FALSE` if PLUTO hangs while writing
HDF5 on the older HDF5 stack. The previous 80-node AGN Intel/IMPI continuation
job `696197.kunanyi-ohpc` ran to the 48-hour walltime limit and localized to a
parallel HDF5 restart stall from `data.0001.dbl.h5`.

## Local Changes

- `scripts/kunanyi/jet_setup_production_template.pbs` now propagates
  `HDF5_USE_FILE_LOCKING` into both OpenMPI (`-x`) and Intel MPI (`-genv`)
  launches when the variable is set.
- `scripts/kunanyi/c_hi_fullgrid_agn_impi_fresh_start.pbs` defines the fresh
  full-grid 80-node production wrapper.
- `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_fresh_start.sh`
  stages the updated template/wrapper, verifies the config payload, refuses to
  reuse an output-containing fresh run root, validates the AGN module stack, and
  submits the wrapper.

## Submission Evidence

```text
AGN_FRESH_MODULE_LIST_BEGIN

Currently Loaded Modules:
  1) intel/18.0.1.163   2) impi/2018.1.163   3) hdf5/1.12.1p   4) zfp/0.5.5

AGN_FRESH_MODULE_LIST_END
AGN_FRESH_MPICC=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
AGN_FRESH_MPIRUN=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
AGN_FRESH_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
AGN_FRESH_REMOTE_WORKDIR=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles
AGN_FRESH_REMOTE_CONFIG_DIR=/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19/C-HI/particles
AGN_FRESH_HDF5_USE_FILE_LOCKING=FALSE
SUBMITTED_JOB_ID=696619.kunanyi-ohpc
Job Id: 696619.kunanyi-ohpc
    Job_Name = c_hi_fg_fresh
    job_state = Q
    queue = normal
    Mail_Users = barry.brook@utas.edu.au
    Resource_List.select = 80:ncpus=28:mpiprocs=28
    Resource_List.walltime = 48:00:00
```

## Run Parameters

- PBS job: `696619.kunanyi-ohpc`
- Job name: `c_hi_fg_fresh`
- Queue/state at submit: `normal` / `Q`
- Resource request: `select=80:ncpus=28:mpiprocs=28`
- Walltime: `48:00:00`
- Wrapper:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.pbs`
- Template:
  `/u/bwbrook/codex_kunanyi/jet_setup_production_template_latest.pbs`
- Run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh`
- Config source:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19/C-HI/particles`
- Stdout:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.out`
- Stderr:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.err`
- `RESTART_POLICY=force-fresh`
- `HDF5_USE_FILE_LOCKING=FALSE`
- `KUNANYI_MODULE_STACK=agn_intel_impi`
- `MPI_FLAVOR=intelmpi`

## Notes

This fresh run root avoids altering the existing
`/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
evidence tree. If the job succeeds, Patrick's fresh-run pathway is validated at
80 nodes. If it stalls again, restart-from-HDF5 is no longer the primary
explanation and the failure package for Patrick/TPAC is cleaner.
