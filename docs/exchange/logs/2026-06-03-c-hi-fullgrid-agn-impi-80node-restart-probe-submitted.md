# 2026-06-03 C-HI Full-Grid AGN IMPI 80-Node Restart Probe Submitted

## Summary

A short 80-node restart probe has been submitted from the successful fresh
full-grid run's final double HDF5 output, `data.0009.dbl.h5`.

The purpose is to test whether the full-grid case can restart at 2240 ranks
from a clean fresh-generated HDF5 output under the AGN Intel/IMPI/HDF5/ZFP
stack with `HDF5_USE_FILE_LOCKING=FALSE`.

## Submission

```text
SUBMITTED_JOB_ID=696911.kunanyi-ohpc
Job Id: 696911.kunanyi-ohpc
    Job_Name = c_hi_fg_r9probe
    job_state = Q
    queue = normal
    Mail_Users = barry.brook@utas.edu.au
    Resource_List.select = 80:ncpus=28:mpiprocs=28
    Resource_List.walltime = 02:00:00
```

## Wrapper

- Local wrapper:
  `scripts/kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.pbs`
- Local stage/submit helper:
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_80node_restart_probe.sh`
- Remote wrapper:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.pbs`
- Remote template:
  `/u/bwbrook/codex_kunanyi/jet_setup_production_template_latest.pbs`
- Stdout:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.out`
- Stderr:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.err`

## Run Parameters

```text
RUN_ROOT=/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh
RESTART_POLICY=auto
EXPECTED_RESTART_INDEX=9
PLUTO_MAXTIME_HOURS=0.5
FORCE_REBUILD=0
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
HDF5_USE_FILE_LOCKING=FALSE
```

Expected template launch:

```text
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9
```

## Pre-Submit Validation

The helper verified:

- remote template and wrapper exist
- config payload exists
- built fresh-run `problem/pluto` exists
- `dbl.h5.out`, `flt.h5.out`, `restart.out`, and `particles.4277.dbl` exist
- latest `dbl.h5.out` restart index is exactly `9`
- `data.0009.dbl.h5` exists
- AGN HDF5 tools can read `/Timestep_9/vars/rho` from `data.0009.dbl.h5`

AGN stack at submit:

```text
Currently Loaded Modules:
  1) intel/18.0.1.163   2) impi/2018.1.163   3) hdf5/1.12.1p   4) zfp/0.5.5

AGN_RESTART_PROBE_HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
AGN_RESTART_PROBE_HDF5_USE_FILE_LOCKING=FALSE
```

`dbl.h5.out` tail at submission:

```text
5 7.664898e+03 3.139112e-01 24838 single_file little rho vx1 vx2 vx3 prs tr1
6 9.198040e+03 3.139112e-01 29722 single_file little rho vx1 vx2 vx3 prs tr1
7 1.073087e+04 3.139112e-01 34605 single_file little rho vx1 vx2 vx3 prs tr1
8 1.226401e+04 3.139112e-01 39489 single_file little rho vx1 vx2 vx3 prs tr1
9 1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
```

## Expected Follow-Up

When the PBS completion email lands, inspect `696911.kunanyi-ohpc`, stdout,
stderr, markers, output catalogues, and rank logs. A successful probe should
show `RUN_KIND=h5_restart_9`, `MPI_EXIT_CODE=0`, and a new HDF5 output such as
`data.0010.dbl.h5`.
