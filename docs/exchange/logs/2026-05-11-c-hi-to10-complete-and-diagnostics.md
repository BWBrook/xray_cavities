# C-HI 2-Node Continuation Complete And To-10 Myr Diagnostics

Date: 2026-05-11

## Completed Run

PBS job:

```text
690650.kunanyi-ohpc
```

Job name:

```text
c_hi_to10
```

Barry reported the PBS completion email:

```text
Exit_status=0
resources_used.cpupercent=2814
resources_used.cput=180:52:36
resources_used.mem=18634336kb
resources_used.ncpus=56
resources_used.vmem=26998152kb
resources_used.walltime=06:44:13
```

The job was run as the reduced-grid `C-HI` particles continuation on:

```text
select=2:ncpus=28:mpiprocs=28
```

## Remote Output Check

Direct MacBook jumpbox access worked again after Barry refreshed the TPAC
Open OnDemand SSH window.

The run wrote a successful `DONE` marker:

```text
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=690650.kunanyi-ohpc
finished_utc=2026-05-10T17:46:44Z
```

Problem directory:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem
```

Output volume after this continuation:

```text
95G
```

The regular `flt.h5` catalogue now extends through the intended nominal
`10 Myr` block:

| Output | Code time | Approx. Myr | Step |
|---:|---:|---:|---:|
| 10 | 1839.525 | 5.999728 | 6027 |
| 11 | 2145.902 | 6.998996 | 7003 |
| 12 | 2452.594 | 7.999292 | 7980 |
| 13 | 2759.285 | 8.999584 | 8957 |
| 14 | 3065.976 | 9.999876 | 9934 |
| 15 | 3151.360 | 10.278362 | 10206 |

`data.0015.flt.h5` is the walltime-stop output. For regular science-cadence
diagnostics, use outputs `10-14`.

The restart-capable `dbl.h5` catalogue now includes:

| Output | Code time | Approx. Myr | Step |
|---:|---:|---:|---:|
| 6 | 3065.976 | 9.999876 | 9934 |
| 7 | 3151.360 | 10.278362 | 10206 |

The next restart should therefore use `-h5restart 7` if continuing from the
walltime-stop checkpoint, or `-h5restart 6` if deliberately restarting from the
nominal `10 Myr` checkpoint.

## Follow-Up Diagnostics Submitted

Two follow-up PBS jobs were submitted as a dependency chain:

```text
690680.kunanyi-ohpc  c_hi_ph5_10
690681.kunanyi-ohpc  c_hi_s10
```

`690680` rebuilds the particle HDF5 cache through the new particle outputs:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-05-11-c-hi-to10-particles-hdf5/C-HI.to10.particles.hdf5
```

`690681` is held on `afterok:690680.kunanyi-ohpc` and, if the particle cache
job succeeds, will run the compact scalar diagnostics for regular grid outputs:

```text
10 11 12 13 14
```

The expected scalar-series output root is:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-05-11-c-hi-to10-snapshot-series
```

The expected summary archives are:

```text
/u/bwbrook/codex_kunanyi/c_hi_to10_particle_hdf5_2026-05-11.tar.gz
/u/bwbrook/codex_kunanyi/c_hi_to10_snapshot_series_2026-05-11.tar.gz
```

## Local Wrapper Scripts

Two thin wrappers were added locally and staged to `/u/bwbrook/codex_kunanyi`:

- `scripts/kunanyi/c_hi_to10_particle_hdf5.pbs`
- `scripts/kunanyi/c_hi_to10_snapshot_series.pbs`

They reuse the previously validated particle-HDF5 and early-snapshot scalar
series scripts, but pin the `to10` output roots and snapshot list.
