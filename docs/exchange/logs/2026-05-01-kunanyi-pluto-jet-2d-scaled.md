# Handover Note: 2026-05-01 kunanyi scaled PLUTO 2D Jet smoke

## Summary

Completed the next `kunanyi` rung after the tiny official PLUTO `HD/Jet` smoke:
a larger, still conservative, single-node 2D jet run.

## What Changed

- Added `scripts/kunanyi/pluto_jet_2d_scaled.pbs`.
- Submitted the script to the `test` queue on `kunanyi`.
- Used the scratch PLUTO tree at `/scratch/bwbrook/git/utas-agn/pluto`.
- Built and ran the official PLUTO `Test_Problems/HD/Jet` case with
  `Kunanyi.defs`, MPI, and the `HDF5/1.14.0-gompi-2023a` stack.

## PBS Job

```text
job id: 688930.kunanyi-ohpc
queue: test
compute node: n001.kunanyi
resources: select=1:ncpus=8:mpiprocs=8, walltime=00:20:00
exit status: 0
resources_used.walltime: 00:00:21
exec_host: n001/3*8
```

## Configuration

```text
problem: PLUTO Test_Problems/HD/Jet
geometry: cylindrical 2D
grid: 64 x 192
domain: r = 0..4, z = 0..12
tstop: 2.0
output interval: 0.5
ETA: 10.0
external Mach target: 20.0
PLUTO MACH: 6.32455532034
MPI ranks: 8
```

The run command was:

```bash
mpirun -np 8 ./pluto -i pluto.ini
```

## Outputs

Run directory:

```text
/scratch/bwbrook/pluto_smoke/jet_hd_2d_scaled/run
```

Key files:

```text
data.0000.dbl
data.0001.dbl
data.0002.dbl
data.0003.dbl
data.0004.dbl
dbl.out
grid.out
pluto.0.log
restart.out
```

`dbl.out` recorded:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 4.980701e-01 3.908019e-03 158 single_file little rho vx1 vx2 vx3 prs
2 9.979077e-01 4.112735e-03 282 single_file little rho vx1 vx2 vx3 prs
3 1.497833e+00 4.037600e-03 405 single_file little rho vx1 vx2 vx3 prs
4 2.000000e+00 1.844065e-03 530 single_file little rho vx1 vx2 vx3 prs
```

The rank-0 PLUTO log ended with:

```text
> Total allocated memory    0.50 Mb (proc #0)
> Elapsed time              0d:0h:0m:4s
> Average time/step         7.55e-03  (sec)
> Done
```

## Current State

- The official PLUTO `HD/Jet` path now works on `kunanyi` at both tiny and
  modest single-node 2D scales.
- The next planned rung is a one-node `jet-setup` tiny 3D smoke.
- After the one-node `jet-setup` smoke, test multi-node MPI parallelisation
  explicitly before any serious full-3D job.
