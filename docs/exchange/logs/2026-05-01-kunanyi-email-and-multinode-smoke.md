# 2026-05-01 kunanyi PBS Email and Multi-Node Smoke

## Summary

Two more `kunanyi` launch-path checks are green:

- PBS email notifications work to `barry.brook@utas.edu.au`.
- The tiny `jet-setup` 3D Cartesian smoke runs across two compute nodes.

This means the core production-job control pattern is now validated: submit via
PBS, disconnect from jumpbox, let the scheduler run independently, receive mail
on abort/end, and later reconnect to inspect logs and artifacts.

## Email Notification Smoke

The email test script is:

```text
scripts/kunanyi/email_notify_smoke.pbs
```

It uses:

```bash
#PBS -M barry.brook@utas.edu.au
#PBS -m abe
```

Job `688936.kunanyi-ohpc` completed successfully:

```text
Job_Name = email_notify_smoke
job_state = F
queue = test
exec_host = n004/3
Mail_Points = abe
Mail_Users = barry.brook@utas.edu.au
Exit_status = 0
resources_used.walltime = 00:00:21
```

Barry confirmed receipt of the completion message from
`adm@<tpac-host>`. The email included the job id, job name,
termination status, exit status, and resource usage.

For full production runs, use:

```bash
#PBS -M barry.brook@utas.edu.au
#PBS -m ae
```

The `a` and `e` flags notify on abort and end. The `b` flag is useful while
testing, but begin messages will be noisy for routine production submissions.

## Two-Node `jet-setup` Smoke

The multi-node script is:

```text
scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs
```

It requests:

```text
queue: test
resources: select=2:ncpus=8:mpiprocs=8
walltime: 00:20:00
mail points: ae
```

The script derives rank count from the PBS nodefile:

```bash
NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

Job `688937.kunanyi-ohpc` started across two nodes:

```text
job_state = R
exec_host = n010/1*8+n011/0*8
resources_used.ncpus = 16
Mail_Points = ae
Mail_Users = barry.brook@utas.edu.au
```

It finished successfully:

```text
job_state = F
Exit_status = 0
resources_used.walltime = 00:00:54
resources_used.cput = 00:05:40
resources_used.mem = 616720kb
resources_used.vmem = 5858392kb
```

The run generated the expected three PLUTO double outputs plus logs:

```text
data.0000.dbl
data.0001.dbl
data.0002.dbl
dbl.out
grid.out
logs/pluto.0.log
...
logs/pluto.15.log
restart.out
```

Each double dump is about `7.6 MB`. `dbl.out` recorded:

```text
0 0.000000e+00 1.000000e-03 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.497451e+02 6.727975e-01 282 single_file little rho vx1 vx2 vx3 prs tr1
2 3.000000e+02 2.431960e-01 506 single_file little rho vx1 vx2 vx3 prs tr1
```

Rank 0 reached the final output and closed cleanly:

```text
> Writing file #2 (dbl) to disk...
> Elapsed time              0d:0h:0m:20s
> Done
```

## Production Pattern

For larger runs, use the same structure but scale the PBS select line:

```bash
#PBS -l select=N:ncpus=28:mpiprocs=28
#PBS -M barry.brook@utas.edu.au
#PBS -m ae

NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

The job runs independently after `qsub`; the jumpbox window is only needed to
submit, poll, and retrieve artifacts.
