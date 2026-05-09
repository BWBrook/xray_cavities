# 2026-05-08 - C-HI Single-Node Particle Segment Launch

## Summary

The first jet-bearing, particles-enabled `C-HI` run has been launched on
`kunanyi` as a one-node production rehearsal. This is not the final multi-node
production grid. It is a controlled single-node shakedown to verify the
particle build, HDF5 output path, restart-capable `dbl.h5` files, and early
jet/particle startup behaviour before spending larger allocations.

Active job:

```text
690426.kunanyi-ohpc
```

Submission shape:

```text
job name: c_hi_1node
queue: normal
resources: select=1:ncpus=28:mpiprocs=28
walltime: 02:00:00
PLUTO_MAXTIME_HOURS: 1.5
restart policy: force-fresh
run root: /scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment
case config: /u/bwbrook/codex_kunanyi/stage_2026-05-08/xray_cavities_cases/C-HI/particles
```

The staged launch tarball used for the successful run has SHA-256:

```text
ab7c51e15acb69c78da157d6e242c9db19f64b98cd348e5ed13815b607578bdc
```

## Configuration

Physics and jet settings are the locked `C-HI` values:

```text
JET_PWR = 1e45 erg/s
JET_SPD = 0.1 c
JET_CHI = 1.0
JET_OA_PRIMARY = 15.0 deg
JET_OA_SECONDARY = 15.0 deg
JET_INITIAL_RADIUS = 0.1 kpc
JET_INJECTION_HEIGHT = 0.75 kpc
JET_RELATIVISTIC_DENSITY = NO
PARTICLES = PARTICLES_LP
PARTICLES_LP_RAISE = YES
Nparticles = -1 16.0
PART_INJECT_FREQUENCY = 0.01 Myr
```

Outputs are:

```text
flt.h5 every 1 Myr
-dbl disabled
dbl.h5 every 5 Myr
particles_dbl every 0.01 Myr
Checkpoint_interval disabled
```

The single-node shakedown grid is:

```text
X1-grid     5   -200 72 s -10 80 s -2.5 100 u 2.5 80 s 10 72 s 200
X2-grid     5   -200 72 s -10 80 s -2.5 100 u 2.5 80 s 10 72 s 200
X3-grid     5   -250 96 s -10 80 s -2.5 100 u 2.5 80 s 10 96 s 250
```

PLUTO decomposed this as:

```text
Global grid:
X1: [-200.0000, 200.0000], 404 point(s), 3 ghosts
X2: [-200.0000, 200.0000], 404 point(s), 3 ghosts
X3: [-250.0000, 250.0000], 452 point(s), 3 ghosts

Rank-local example:
Proc size: 202 X 202 X 65
```

The grid keeps the original central `-2.5..2.5 kpc` uniform patch at `100`
cells, so inlet resolution is still `0.05 kpc`. The outer stretched patches are
coarsened deliberately to make the run fit one Kunanyi node. The full
supervisor grid remains the production target and will need more resources.

## Failed Attempts And Fixes

### `690424.kunanyi-ohpc`

The first submission failed during the particle build:

```text
fatal error: particles.h: No such file or directory
Exit_status = 2
```

Fix: `scripts/kunanyi/jet_setup_production_template.pbs` now writes generated
`local_make` with:

```make
-include Particles/makefile
```

This adds the particle include path and particle objects when `PARTICLES_LP` is
enabled.

### `690425.kunanyi-ohpc`

The second submission used the full supervisor `stewart_stretched_250` grid.
PLUTO parsed it as approximately:

```text
X1: 960 cells
X2: 960 cells
X3: 1014 cells
```

It was killed during memory allocation:

```text
mpirun noticed that process rank 3 exited on signal 9 (Killed)
Exit_status = 1
```

Fix: add the `kunanyi_single_node_250` grid preset for the one-node shakedown.
The full `stewart_stretched_250` grid remains the production/multi-node target.

## Live Poll Evidence

At the final pre-handoff poll, `690426.kunanyi-ohpc` was still running:

```text
job_state = R
exec_host = n033/0*28
resources_used.walltime = 00:11:29
resources_used.cput = 03:47:39
resources_used.mem = 30426628kb
resources_used.cpupercent = 2153
```

No `FAILED` marker was present.

The run had written:

```text
data.0000.dbl.h5 5318067316 bytes
data.0000.dbl.xmf 2992 bytes
data.0000.flt.h5 3547500148 bytes
data.0000.flt.xmf 2992 bytes
particles.0000.dbl 2457 bytes
dbl.h5.out
flt.h5.out
restart.out
grid.out
```

The rank-0 log had reached actual computation:

```text
> Writing particle file #0 (dbl) to disk...
> Starting computation...

step:0; t = 0.0000e+00; dt = 1.0000e-05; 0.0 %
        [Mach = 23.412091]
        [Nparticles/tot: 0 / 48; Nsub = 1; <Ek> = 2.8608e-03]
```

## Completion

`690426.kunanyi-ohpc` completed cleanly.

PBS accounting:

```text
Exit_status = 0
resources_used.cpupercent = 2800
resources_used.cput = 44:04:38
resources_used.mem = 30525360kb
resources_used.ncpus = 28
resources_used.vmem = 39726444kb
resources_used.walltime = 01:39:28
exec_host = n033/0*28
```

The run wrote a `DONE` marker:

```text
status=done
case_id=C-HI
case_variant=particles
pbs_jobid=690426.kunanyi-ohpc
finished_utc=2026-05-08T14:15:17Z
```

PLUTO stopped through the requested `-maxtime` path rather than being killed by
PBS:

```text
> Max time 1.500000 hours reached.
> Writing file #1 (dbl.h5) to disk...
> Writing file #1 (flt.h5) to disk...
> Writing particle file #45 (dbl) to disk...
> Done
```

Output checks:

```text
data.0000.dbl.h5 5.0G
data.0001.dbl.h5 5.0G
data.0000.flt.h5 3.4G
data.0001.flt.h5 3.4G
particles.0000.dbl through particles.0045.dbl
output directory footprint: 17G
```

`dbl.h5.out` and `flt.h5.out` both record the final forced output as:

```text
1 1.371692e+02 2.988724e-01 583 single_file little rho vx1 vx2 vx3 prs tr1
```

The HDF5 files were readable via `h5ls`; the selected files exposed the
expected `Timestep_*`, `cell_coords`, and `node_coords` groups.

The generated grid for this one-node shakedown was:

```text
X1: 404 cells, [-200, 200], min dx 0.05 kpc, max dx 11.0828 kpc
X2: 404 cells, [-200, 200], min dx 0.05 kpc, max dx 11.0828 kpc
X3: 452 cells, [-250, 250], min dx 0.05 kpc, max dx 10.4413 kpc
```

The central inlet-scale patch remains well resolved. The outer grid is
deliberately coarse because this was the one-node particle shakedown, not the
final supervisor-grade multi-node grid.

Compact evidence was retrieved to the Mac at:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_1node_690426_compact_results_2026-05-09.tar.gz
```

SHA-256:

```text
bba6a6505bd29cb832d419ae54d38471676f3f1e8b131bf9d6592c2de7477d26
```

## Result

This shakedown passed the intended infrastructure gate:

- particle-enabled PLUTO builds now work on `kunanyi`
- HDF5 static-grid outputs are written and readable
- the `-maxtime` shutdown path writes a final restart-capable output set
- particle files are produced beyond the initial file
- the PBS template writes durable `DONE`/`FAILED` markers

It should not be treated as a science result yet. The final time is an early
segment, and the grid is the one-node rehearsal grid. The next move is to run
quick-look diagnostics on the early `C-HI` HDF5 and particle outputs, then
decide whether to continue this run from restart, launch a longer one-node
segment, or promote to an intermediate multi-node rehearsal.
