# 2026-05-01 kunanyi `jet-setup` Tiny 3D Cartesian Smoke

## Summary

The next `kunanyi` rung is green: a tiny full-3D Cartesian `jet-setup` case
completed under PBS on one compute node using eight MPI ranks.

This follows the scaled official PLUTO 2D jet smoke and confirms that the
project-specific `jet-setup` path can scaffold, build, and run on `kunanyi`,
not only the upstream PLUTO test problems.

## Source Staging

The local MacBook `jet-setup` checkout was bundled without `.git`, caches,
test-output folders, or build artifacts and transferred through jumpbox to:

```text
/u/bwbrook/jet_setup_source_2026-05-01.tgz
```

It was unpacked on the login node to:

```text
/scratch/bwbrook/git/utas-agn/jet-setup
```

The scratch PLUTO tree from the prior smoke tests remained at:

```text
/scratch/bwbrook/git/utas-agn/pluto
```

## PBS Script

The new runner is:

```text
scripts/kunanyi/jet_setup_tiny_3d_cart.pbs
```

It requests:

```text
queue: test
resources: select=1:ncpus=8:mpiprocs=8
walltime: 00:20:00
module stack: HDF5/1.14.0-gompi-2023a
```

The script scaffolds a `jet-setup` problem, patches the problem definitions,
generates a `Kunanyi.defs` PLUTO makefile, builds with `make -j8`, and runs:

```bash
mpirun -np 8 ./pluto -i pluto.ini
```

The case settings are deliberately tiny:

```text
grid: 48 x 48 x 72
domain: x = -12..12, y = -12..12, z = -18..18
physics: HD
geometry: Cartesian 3D
environment: King
particles: off
tstop: 300.0
```

## First Attempt

Job `688934.kunanyi-ohpc` failed quickly with:

```text
missing define COMPONENTS in /scratch/bwbrook/jet_setup_smoke/tiny_3d_cart/problem/src/definitions.h
```

The local script had inherited a patch step from the Nectar tiny-3D smoke, but
the current `jet-setup` `definitions.h` on this branch does not define
`COMPONENTS`. The fix was to remove that patch step and let the existing source
layout control component configuration.

The same stderr also reported:

```text
/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem: line 11: git: command not found
```

That warning comes from `tools/setup-problem` trying to describe the source
version. It did not block the subsequent successful run.

## Successful Run

Job `688935.kunanyi-ohpc` completed successfully:

```text
job id: 688935.kunanyi-ohpc
queue: test
compute node: n010.kunanyi
exec host: n010/1*8
resources: select=1:ncpus=8:mpiprocs=8
Exit_status: 0
resources_used.walltime: 00:01:26
resources_used.cput: 00:04:55
resources_used.mem: 342164kb
resources_used.vmem: 3225936kb
```

The PBS output confirmed the expected toolchain:

```text
mpicc=/share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpicc
mpirun=/share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpirun
ARCH         = Kunanyi.defs
PLUTO_DIR    = /scratch/bwbrook/git/utas-agn/pluto
```

The run produced:

```text
data.0000.dbl
data.0001.dbl
data.0002.dbl
dbl.out
grid.out
logs/pluto.0.log
logs/pluto.1.log
logs/pluto.2.log
logs/pluto.3.log
logs/pluto.4.log
logs/pluto.5.log
logs/pluto.6.log
logs/pluto.7.log
logs/pluto.log
restart.out
```

The three double dumps are each about `7.6 MB`. `dbl.out` recorded:

```text
0 0.000000e+00 1.000000e-03 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.497451e+02 6.727975e-01 282 single_file little rho vx1 vx2 vx3 prs tr1
2 3.000000e+02 2.431960e-01 506 single_file little rho vx1 vx2 vx3 prs tr1
```

Rank 0 reached the final output and closed cleanly:

```text
> Writing file #2 (dbl) to disk...
> Elapsed time              0d:0h:0m:34s
> Done
```

## Next Rung

The next useful `kunanyi` smoke is an explicit multi-node MPI test. A modest
starting point is the same tiny 3D `jet-setup` case with:

```text
select=2:ncpus=8:mpiprocs=8
mpirun -np 16 ./pluto -i pluto.ini
```

For production-scale full 3D runs, the likely shape is closer to:

```text
select=N:ncpus=28:mpiprocs=28
mpirun -np $((N * 28)) ./pluto -i pluto.ini
```

but that should wait until the two-node smoke path is boringly green.
