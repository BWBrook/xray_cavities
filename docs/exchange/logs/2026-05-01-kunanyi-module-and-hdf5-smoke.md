# Handover Note: 2026-05-01 kunanyi module inventory and HDF5 smoke

## Session Context

- Machine used: MacBook Neo as control plane
- Remote access: TPAC jumpbox window opened via Open OnDemand
- Local repo path: `/Users/bwbrook/papers/xray_cavities`

## What Was Done

- Fixed the local `expect` wrapper used by `scripts/kunanyi/run_on_kunanyi.sh`.
- Ran targeted module inventory using `scripts/kunanyi/module_inventory.sh`.
- Submitted a small PBS batch job to the `test` queue that:
  - loaded the HDF5/gompi stack,
  - compiled a two-rank MPI + parallel-HDF5 C smoke program with `h5pcc`,
  - ran it with `mpirun -np 2`,
  - wrote and inspected an HDF5 file.

## Module Inventory

Best current stack for PLUTO/HDF5 smoke work:

```text
HDF5/1.14.0-gompi-2023a
```

This pulls in:

```text
GCC/12.3.0
OpenMPI/4.1.5-GCC-12.3.0
gompi/2023a
HDF5/1.14.0-gompi-2023a
```

Other useful modules visible:

- `CMake/3.26.3-GCCcore-12.3.0`
- `Python/3.11.3-GCCcore-12.3.0`
- `git/2.41.0-GCCcore-12.3.0-nodocs`
- `netCDF/4.9.2-gompi-2023a`
- `netCDF-C++4/4.3.1-gompi-2023a`
- `netCDF-Fortran/4.6.1-gompi-2023a`

## PBS HDF5 Smoke

Submitted job:

```text
688922.kunanyi-ohpc
```

Run details:

```text
queue: test
host: n001.kunanyi
workdir: /scratch/bwbrook/codex_hdf5_probe
resources: select=1:ncpus=2, walltime=00:05:00
```

Confirmed paths:

```text
gcc=/share/apps/software/GCCcore/12.3.0/bin/gcc
mpicc=/share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpicc
mpirun=/share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpirun
h5pcc=/share/apps/software/HDF5/1.14.0-gompi-2023a/bin/h5pcc
h5dump=/share/apps/software/HDF5/1.14.0-gompi-2023a/bin/h5dump
```

Validation output:

```text
mpirun (Open MPI) 4.1.5
MPI ranks: 2
Parallel HDF5 file created.
HDF5 "mpi_hdf5_smoke.h5" {
GROUP "/" {
}
}
```

The output file was created successfully:

```text
mpi_hdf5_smoke.h5 800 bytes
```

## Current State

- Direct command execution through jumpbox and `kunanyi` works via
  `scripts/kunanyi/run_on_kunanyi.sh`.
- Targeted module inventory is green.
- PBS compile/run on a compute node is green for MPI + parallel HDF5.
- Locale warnings persist (`C.UTF-8` unavailable), but they did not block SSH,
  module loading, compilation, MPI, HDF5, or PBS.

## Next Recommended Step

Build and run a tiny PLUTO test case under PBS using the
`HDF5/1.14.0-gompi-2023a` module stack.
