# Handover Note: 2026-05-01 kunanyi PLUTO Jet smoke

## Session Context

- Machine used: MacBook Neo as control plane
- Remote access: TPAC jumpbox window opened via Open OnDemand
- Local repo path: `/Users/bwbrook/papers/xray_cavities`

## What Was Done

- Added a tiny official PLUTO `HD/Jet` PBS smoke script:
  `scripts/kunanyi/pluto_jet_smoke.pbs`.
- Submitted it to the `test` queue on `kunanyi`.
- Used the scratch PLUTO tree already unpacked at:
  `/scratch/bwbrook/git/utas-agn/pluto`.
- Built the jet problem with `Kunanyi.defs`, MPI, and HDF5 enabled.
- Ran a deliberately tiny two-rank simulation to validate the jet-specific
  setup, boundary, and init path.

## PBS Job

Submitted job:

```text
688926.kunanyi-ohpc
```

Run details:

```text
queue: test
compute node: n001.kunanyi
resources: select=1:ncpus=2, walltime=00:10:00
workdir: /scratch/bwbrook/pluto_smoke/jet_hd
run dir: /scratch/bwbrook/pluto_smoke/jet_hd/run
```

The job used:

```text
module load HDF5/1.14.0-gompi-2023a
ARCH = Kunanyi.defs
mpicc = /share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpicc
mpirun = /share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpirun
HDF5_DIR = /share/apps/software/HDF5/1.14.0-gompi-2023a
```

## Tiny Jet Configuration

This was a smoke, not the full Patrick/Krause worksheet rerun.

```text
problem: PLUTO Test_Problems/HD/Jet
dimensions: 2
geometry: CYLINDRICAL
grid: 16 x 48
domain: r = 0..4, z = 0..12
tstop: 1.0
output interval: 0.5
ETA: 10.0
external Mach target: 20.0
PLUTO MACH parameter: 20 / sqrt(10) = 6.32455532034
MPI ranks: 2
```

Run command:

```bash
mpirun -np 2 ./pluto -i pluto.ini
```

## Validation Output

Key outputs:

```text
pluto           314K
data.0000.dbl    30K
data.0001.dbl    30K
data.0002.dbl    30K
dbl.out          213
grid.out         3.4K
pluto.0.log      5.7K
restart.out      384
```

`dbl.out`:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 4.929819e-01 1.550904e-02 74 single_file little rho vx1 vx2 vx3 prs
2 1.000000e+00 9.293902e-04 108 single_file little rho vx1 vx2 vx3 prs
```

Rank-0 PLUTO log confirmed:

```text
Number of processors: 2
Proc size:            16 X 24
Parallel Directions:  X1/X2
Writing file #0 (dbl) to disk...
Starting computation...
```

The job exited with status `0` and produced the final `t = 1.0` output.

## PBS Sizing Notes

TPAC notes and observed jobs indicate a node exposes 28 CPUs to jobs. For
single-node MPI jobs:

```pbs
#PBS -l select=1:ncpus=28:mpiprocs=28
```

For a multi-node MPI job:

```pbs
#PBS -l select=4:ncpus=28:mpiprocs=28
```

This requests 4 nodes and 112 MPI ranks if launched with:

```bash
mpirun -np 112 ./pluto -i pluto.ini
```

For future serious PLUTO 3D jobs, confirm the correct production queue,
walltime limit, and any TPAC policy around full-node or shared-node jobs before
launching.

## Current State

- PLUTO `HD/Sod` and a tiny official `HD/Jet` both build and run under PBS on
  `kunanyi`.
- The current scratch PLUTO tree is sufficient for the next small PBS tests.
- Next useful rung is either:
  - a slightly larger 2D official jet run on `kunanyi`, or
  - first `jet-setup`/full-3D smoke path on `kunanyi`.
