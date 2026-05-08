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

## Next

Wait for the PBS completion email for `690426.kunanyi-ohpc`. After completion,
open a jumpgate and inspect:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/markers/
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem/outputs/
/u/bwbrook/codex_kunanyi/c_hi_1node.out
/u/bwbrook/codex_kunanyi/c_hi_1node.err
```

Pass criteria for this shakedown are:

- exit status `0`, or clean `-maxtime` stop with restartable HDF5 output
- `DONE` marker written
- later `dbl.h5` and `flt.h5` outputs beyond file `0`
- particle outputs beyond `particles.0000.dbl`
- no restart/output-path surprises
