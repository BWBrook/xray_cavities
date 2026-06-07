# C-HI full-grid AGN/IMPI 64-node production continuation complete

Date: 2026-06-07

## Summary

The 64-node production continuation submitted as `697298.kunanyi-ohpc`
completed with `Exit_status=0`. Although the PBS walltime used was under eight
hours, this was a normal PLUTO completion: the run reached the configured C-HI
`tstop`, wrote final products, and all ranks ended cleanly.

The requested `48:00:00` walltime and `PLUTO_MAXTIME_HOURS=47.5` were upper
bounds. They were not expected to be consumed if the simulation reached `tstop`
first.

## PBS Result

```text
PBS Job Id: 697298.kunanyi-ohpc
Job Name:   c_hi_r9_p64
Exit_status=0
resources_used.cpupercent=2819
resources_used.cput=217:45:08
resources_used.mem=9820192kb
resources_used.ncpus=1792
resources_used.vmem=27589808kb
resources_used.walltime=07:49:58
Resource_List.select=64:ncpus=28:mpiprocs=28
Resource_List.walltime=48:00:00
```

Marker:

```text
DONE=status=done
case_id=C-HI
case_variant=particles
pbs_jobid=697298.kunanyi-ohpc
finished_utc=2026-06-06T11:22:11Z
```

## Launch State

```text
JOB_START=2026-06-06T03:32:30Z
JOB_END=2026-06-06T11:22:11Z
KUNANYI_MODULE_STACK=agn_intel_impi
MPI_FLAVOR=intelmpi
MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
HDF5_USE_FILE_LOCKING=FALSE
PLUTO_MAXTIME_HOURS=47.5
NRANKS=1792
RUN_KIND=h5_restart_9
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5 -h5restart 9
MPI_EXIT_CODE=0
```

The active `pluto.ini` time block contains:

```text
[Time]
CFL              0.33
CFL_max_var      1.1
tstop            15330.06968940
first_dt         1.0e-5
```

## Product Evidence

Production endpoint:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles
```

The output tree volume reported by the PBS stdout summary was:

```text
475G
```

The restart catalogue ended at the configured endpoint:

```text
dbl.h5.out lines=12
9  1.311314e+04 3.139112e-01 42194 single_file little rho vx1 vx2 vx3 prs tr1
10 1.379684e+04 3.139112e-01 44372 single_file little rho vx1 vx2 vx3 prs tr1
11 1.533007e+04 1.377728e-01 49253 single_file little rho vx1 vx2 vx3 prs tr1
```

The float catalogue likewise ended at the endpoint:

```text
flt.h5.out lines=52
49 1.471660e+04 3.139112e-01 47302 single_file little rho vx1 vx2 vx3 prs tr1
50 1.502329e+04 3.139112e-01 48279 single_file little rho vx1 vx2 vx3 prs tr1
51 1.533007e+04 1.377728e-01 49253 single_file little rho vx1 vx2 vx3 prs tr1
```

New regular products include:

```text
data.0010.dbl.h5
data.0011.dbl.h5
data.0044.flt.h5 through data.0051.flt.h5
particles.4278.dbl through particles.5000.dbl
```

The source restart inputs remain as the intended symlinks from the clean fresh
run:

```text
data.0009.dbl.h5
particles.4277.dbl
```

## Rank Log Evidence

Sampled ranks `0`, `1`, `27`, `28`, `895`, `896`, `1790`, and `1791` all:

- restarted from file `#9`
- wrote `data.0011.dbl.h5`
- wrote `data.0051.flt.h5`
- wrote `particles.5000.dbl`
- reported elapsed time `0d:7h:47m:36s`
- ended with `> Done`

Exact all-rank scan:

```text
TOTAL=1792
DONE_LAST=1792
RESTART_SEEN=1792
DONE_SEEN=1792
WRITE11_SEEN=1792
OTHER_LAST=0
```

## Interpretation

The short PBS runtime is benign. The 64-node production continuation consumed
the remaining interval from clean fresh output `9` to the configured C-HI
endpoint at `tstop = 15330.06968940`.

Treat the `2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64` tree as the current
completed science production endpoint. The next step is a product integrity and
quick-look pass, followed by the science analysis/figure workflow.
