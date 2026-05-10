# 2026-05-09 - C-HI Restart Segment And 1 Myr Quick-look

## Summary

The first restart-continuation segment for the particles-enabled `C-HI`
one-node shakedown completed cleanly on `kunanyi`.

This validates the static-grid HDF5 restart path for the current
particles-enabled Stewart-cluster setup:

```text
RUN_KIND=h5_restart_1
RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 1.5 -h5restart 1
```

## Restart Job

PBS accounting:

```text
PBS Job Id: 690452.kunanyi-ohpc
Job Name:   c_hi_restart
Exit_status=0
resources_used.cpupercent=2800
resources_used.cput=44:14:47
resources_used.mem=30588076kb
resources_used.ncpus=28
resources_used.vmem=39767548kb
resources_used.walltime=01:40:09
exec_host=n129/0*28
```

The job wrote:

```text
data.0002.dbl.h5  t = 309.7147 code units = 1.0101 Myr
data.0002.flt.h5  t = 306.2961 code units = 0.9990 Myr
data.0003.flt.h5  t = 309.7147 code units = 1.0101 Myr
particles.0103.dbl
```

The output directory footprint is now about `29 GB`.

The successful marker is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/markers/DONE
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=690452.kunanyi-ohpc
finished_utc=2026-05-09T05:39:55Z
```

## Quick-look Job

A small compute-node extraction was run on the nominal `1 Myr` float output:

```text
PBS Job Id: 690479.kunanyi-ohpc
Job Name:   c_hi_ql_1myr
Exit_status=0
resources_used.walltime=00:00:19
input_h5=data.0002.flt.h5
timestep=Timestep_2
```

The local plotted outputs are under:

```text
docs/science/assets/c_hi_restart_quicklook_2026-05-09/
```

The summary report is:

```text
docs/science/c_hi_restart_quicklook_2026-05-09.md
```

## Compact Evidence

Compact run and quick-look evidence has been retrieved locally:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_restart_690452_quicklook_690479_compact_2026-05-09.tar.gz
```

SHA-256:

```text
fe6c5259dcbe95d759d965d5b2e574e323af168dd127469a9c39d404e2cec2f2
```

## Result

This gate is green:

- HDF5 restart from `data.0001.dbl.h5` works.
- The second `-maxtime` shutdown wrote a new restart-capable double output.
- The nominal 1 Myr float output can be extracted and plotted.
- Particle output continued across the restart.
- The tracer region remains compact and symmetric in the one-node shakedown
  grid.

Next recommended rung: an intermediate multi-node rehearsal of the same
restartable `C-HI` workflow before any long production job.
