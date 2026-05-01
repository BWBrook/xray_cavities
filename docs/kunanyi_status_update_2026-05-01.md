---
title: "kunanyi Readiness Update"
subtitle: "X-ray cavities Honours project"
author: "Barry W. Brook"
date: "1 May 2026"
geometry: margin=22mm
fontsize: 11pt
---

# Summary

The TPAC `kunanyi` path is now ready at the infrastructure level for full 3D
jobs once the science cases and production scripts are properly prepared.

The MacBook is acting as a control plane only. Compute work is being staged on
remote systems: Nectar for tests, 2D runs, and micro-3D smoke tests; `kunanyi`
for production-scale 3D simulations.

# What Has Been Validated

- SSH access through the TPAC jumpbox and onward to the `kunanyi` login node.
- PBS submission from `kunanyi`, with jobs continuing independently after
  disconnecting from the jumpbox.
- PBS email alerts to `barry.brook@utas.edu.au`.
- The working compiler/MPI/HDF5 stack:
  `HDF5/1.14.0-gompi-2023a`, providing GCC 12.3, OpenMPI 4.1.5, and parallel
  HDF5 1.14.0.
- PLUTO build and execution under PBS.
- `jet-setup` build and execution under PBS.
- One-node and two-node MPI execution.
- Rank count derived from `PBS_NODEFILE`, which is the pattern needed for
  scalable production scripts.

# Smoke Test Ladder

The following `kunanyi` tests have completed successfully.

| Step | Job | Resource shape | Result |
|---|---:|---|---|
| Basic PBS compute-node smoke | 688913 | 1 core | completed |
| MPI + parallel HDF5 smoke | 688922 | 2 ranks | completed |
| PLUTO Sod build/run | 688924 | 2 ranks | completed |
| PLUTO `HD/Jet` smoke | 688926 | 2 ranks | completed |
| Scaled PLUTO 2D jet | 688930 | 1 node, 8 ranks | completed |
| `jet-setup` tiny 3D Cartesian | 688935 | 1 node, 8 ranks | completed |
| PBS email notification smoke | 688936 | 1 core | completed, email received |
| `jet-setup` tiny 3D multi-node | 688937 | 2 nodes, 16 ranks | completed |

The multi-node `jet-setup` smoke ran the same tiny 3D Cartesian case across
`n010.kunanyi` and `n011.kunanyi` using:

```bash
#PBS -l select=2:ncpus=8:mpiprocs=8
NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

It produced the expected `data.0000.dbl` through `data.0002.dbl`, `dbl.out`,
`grid.out`, and 16 per-rank PLUTO logs, and exited cleanly with
`Exit_status = 0`.

# Current Readiness

The remaining work is no longer basic HPC access or module discovery. The next
task is to package production-safe science jobs.

The expected full-node production pattern is:

```bash
#PBS -l select=N:ncpus=28:mpiprocs=28
#PBS -M barry.brook@utas.edu.au
#PBS -m ae

NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

Email should be treated as a useful notification layer. The source of truth
remains PBS history, stdout/stderr logs, run-directory markers, and simulation
outputs.

# Before Full 3D Jobs

Before launching 48-hour multi-node runs, the production package still needs:

1. A locked case specification: physics switches, jet parameters, environment,
   grid, domain, output cadence, final time, and required radio/X-ray/truth
   products.
2. A production PBS template using full-node resource requests and robust
   logging.
3. Restart/resume handling, including checkpoint cadence and simple
   `DONE`/`FAILED` markers.
4. An output-volume and retention plan for scratch, home, MacBook/Nectar
   retrieval, and cleanup.
5. One intermediate-size rehearsal that exercises the production script,
   checkpoints, restart path, email alerts, and artifact retrieval.

Once those gates are green, `kunanyi` is ready for the serious 3D simulation
suite.
