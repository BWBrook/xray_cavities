# 2026-05-31 C-HI Full-Grid AGN Intel/IMPI 80-Node Walltime

## Session Context

- Machine used for inspection: Mac Mini
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- Target: `kunanyi` via the usual TPAC jumpbox route
- PBS job: `696197.kunanyi-ohpc`
- Job name: `c_hi_fg_agn80`
- Purpose: inspect the 80-node AGN Intel/IMPI continuation after Barry's PBS
  completion email reported a full 48-hour run ending with `Exit_status=271`.

## PBS Result

```text
Job Id: 696197.kunanyi-ohpc
Job_Name = c_hi_fg_agn80
resources_used.cpupercent = 2820
resources_used.cput = 1342:50:36
resources_used.mem = 4229240kb
resources_used.ncpus = 2240
resources_used.vmem = 23485880kb
resources_used.walltime = 48:01:46
job_state = F
queue = normal
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.walltime = 48:00:00
Exit_status = 271
```

PBS stderr:

```text
Lmod has detected the following error: You can only have one compiler module
loaded at a time.
You already have intel loaded.

/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem: line 11: git: command not found
=>> PBS: job killed: walltime 172896 exceeded limit 172800
Terminated
```

The Lmod and `git` messages are the same non-fatal caveats seen in earlier
green AGN Intel/IMPI runs. The terminal event is the PBS walltime kill.

## Marker State

```text
status=failed
case_id=C-HI
case_variant=particles
pbs_jobid=696197.kunanyi-ohpc
exit_code=143
signal=TERM
finished_utc=2026-05-31T03:20:28Z
```

This confirms the updated production template marked the walltime termination
as `FAILED`, not `DONE`.

## Launch Evidence

PBS stdout recorded:

```text
JOB_START=2026-05-29T03:19:15Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
FORCE_REBUILD=1
PLUTO_MAXTIME_HOURS=47.5
NRANKS=2240
MPI_MACHINEFILE=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/job_logs/intelmpi_machinefile.696197.kunanyi-ohpc.txt
RUN_KIND=h5_restart_1
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5 -h5restart 1
JOB_SIGNAL=TERM
JOB_END=2026-05-31T03:20:28Z
```

The job therefore used the intended AGN Intel/IMPI/HDF5/ZFP stack and the
intended restart from output `1`.

## Restart Localization

The rank logs are cumulative, so the inspection searched after each log's
final `> restarting from file #1 (dbl.h5)` line.

```text
rank_log_files=2240
logs_with_final_restart_file_1=2240
logs_with_starting_after_final_restart=0
logs_with_particle_after_final_restart=0
logs_with_step_after_final_restart=0
logs_with_write_after_final_restart=0
```

Examples:

```text
pluto.0.log    restart_line=1499 nlines=1499
pluto.1.log    restart_line=1494 nlines=1494
pluto.1000.log restart_line=1078 nlines=1078
```

That is, every inspected rank log ended at the full-grid HDF5 restart line.
No rank reached particle restart, computation, step output, or file writing
after the final restart attempt.

## Output Catalogue

`dbl.h5.out` remains:

```text
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.011234e+01 2.777278e-01 135 single_file little rho vx1 vx2 vx3 prs tr1
```

`flt.h5.out` remains:

```text
0 0.000000e+00 1.000000e-05 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.011234e+01 2.777278e-01 135 single_file little rho vx1 vx2 vx3 prs tr1
```

No `data.0002.*` output was written. The only output file newer than the
696197 nodefile was `grid.out`, written during startup.

Existing restart-capable HDF5 outputs:

```text
data.0000.dbl.h5 63G
data.0000.flt.h5 42G
data.0001.dbl.h5 63G
data.0001.flt.h5 42G
```

## Error Scan

For the 696197 AGN Intel/IMPI run, no UCX `UD endpoint ... unhandled timeout
error`, `MPI_ABORT`, or segmentation-fault signature was found. The previous
OpenMPI/UCX failure mode was not reproduced.

## Interpretation

This is best classified as a large-scale restart I/O stall rather than a
compute-time walltime miss or the earlier OpenMPI/UCX transport abort. The
same AGN Intel/IMPI/HDF5 stack restarted and computed successfully at
8 nodes / 224 ranks. At 80 nodes / 2240 ranks, all ranks reached the HDF5
restart from `data.0001.dbl.h5`, and none reached particle restart or
computation before PBS terminated the job at walltime.

The low CPU use relative to a 2240-core, 48-hour allocation further supports a
wait/stall interpretation, likely in parallel HDF5/MPI-IO or filesystem-scale
restart handling on `/scratch`.

## Suggested Next Communication

Ask Patrick/TPAC to focus on Intel MPI + parallel HDF5 restart from a single
63 GB `data.NNNN.dbl.h5` file at 2240 ranks on `kunanyi` `/scratch`. The
working comparison point is the green 8-node / 224-rank AGN restart from
`data.0000.dbl.h5` to output `1`; the failing point is the 80-node / 2240-rank
restart from `data.0001.dbl.h5`, which stalls before particle restart or
computation.
