# 2026-05-08 - kunanyi Stewart Environment Gates

## Summary

The production-like no-jet Stewart tabulated environment/MPI/HDF5 gate has now
passed for both confirmed radially averaged Stewart environments:
`cluster_002003` and `group_002031`.

This is the first full-size Kunanyi check of the confirmed radially averaged
Stewart environment path, using:

- one Kunanyi node
- `28` MPI ranks
- `HDF5/1.14.0-gompi-2023a`
- `OpenMPI/4.1.5-GCC-12.3.0`
- static-grid `dbl.h5` outputs
- `-maxtime 0.75` inside a `01:00:00` PBS walltime

A compact results bundle containing logs, grids, restart metadata, output
manifests, configuration files, and `DONE` markers for both gates was staged on
Kunanyi and retrieved locally:

```text
remote: /u/bwbrook/codex_kunanyi/stage_2026-05-08/stewart_gate_compact_results_2026-05-08.tar.gz
local:  build/science/kunanyi_stage_2026-05-08/stewart_gate_compact_results_2026-05-08.tar.gz
sha256: adb099cd1557b192d23f48b6d5a1976225a607ebce9df7c2854b66d44a125c80
```

## Cluster Gate: `cluster_002003`

PBS job:

```text
690366.kunanyi-ohpc
```

PBS accounting from the completion email:

```text
Exit_status=0
resources_used.cpupercent=2775
resources_used.cput=19:50:58
resources_used.mem=24518028kb
resources_used.ncpus=28
resources_used.vmem=33716072kb
resources_used.walltime=00:48:57
```

Remote marker:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/results/cluster_002003/markers/DONE.cluster_002003
```

The run completed the 50 Myr gate and wrote six full-grid `dbl.h5` outputs:

```text
data.0000.dbl.h5
data.0001.dbl.h5
data.0002.dbl.h5
data.0003.dbl.h5
data.0004.dbl.h5
data.0005.dbl.h5
```

Each full-grid HDF5 file is about `5.37 GB`; the live run directory is about
`33 GB`.

Output cadence from `dbl.h5.out`:

```text
0 0.000000e+00 3.066014e+00 0 single_file little rho vx1 vx2 vx3 prs tr1
1 3.060755e+03 1.310581e+02 53 single_file little rho vx1 vx2 vx3 prs tr1
2 6.075075e+03 1.310564e+02 76 single_file little rho vx1 vx2 vx3 prs tr1
3 9.089351e+03 1.310545e+02 99 single_file little rho vx1 vx2 vx3 prs tr1
4 1.223464e+04 1.310528e+02 123 single_file little rho vx1 vx2 vx3 prs tr1
5 1.533007e+04 8.934682e+01 147 single_file little rho vx1 vx2 vx3 prs tr1
```

The generated grid confirms the intended gate dimensions:

```text
X1: [-200.000000,  200.000000], 400 point(s), 3 ghosts
X2: [-200.000000,  200.000000], 400 point(s), 3 ghosts
X3: [-250.000000,  250.000000], 500 point(s), 3 ghosts
```

HDF5 metadata smoke on the final file:

```text
data.0005.dbl.h5
Timestep_5   Group
cell_coords  Group
node_coords  Group
```

## Script Fixes Captured

The first cluster gate used a one-off remote PBS script. During the run, PLUTO
wrote HDF5 files in the problem root while the script's result checks expected
an `outputs/` directory. The live run was rescued with symlinks so the job could
finish and mark `DONE`.

The durable fix is now in the repo:

- `scripts/science/render_stewart_environment_gate_tests.py` renders
  `log_dir ./outputs/logs` and `output_dir ./outputs`.
- `scripts/kunanyi/stewart_environment_gate.pbs` is the reusable no-jet
  Stewart gate launcher.

The refreshed transfer bundle was staged to Kunanyi with SHA-256:

```text
d3605bc6d1b4426c077205ee93f2e550eed2c03b06b9553bdce62665f5ecbee3
```

## Group Gate: `group_002031`

PBS job:

```text
690371.kunanyi-ohpc
```

PBS accounting from the completion email:

```text
Exit_status=0
resources_used.cpupercent=2755
resources_used.cput=18:13:04
resources_used.mem=24520976kb
resources_used.ncpus=28
resources_used.vmem=33710492kb
resources_used.walltime=00:45:22
```

Remote marker:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/results/group_002031/markers/DONE.group_002031
```

Marker contents:

```text
status=done
case=group_002031
jobid=690371.kunanyi-ohpc
finished_utc=2026-05-08T12:05:09Z
```

The run completed the 50 Myr gate and wrote six full-grid `dbl.h5` outputs
under `outputs/`:

```text
data.0000.dbl.h5
data.0001.dbl.h5
data.0002.dbl.h5
data.0003.dbl.h5
data.0004.dbl.h5
data.0005.dbl.h5
```

Each full-grid HDF5 file is about `5.37 GB`; the live run directory is about
`33 GB`.

Output cadence from `dbl.h5.out`:

```text
0 0.000000e+00 3.066014e+00 0 single_file little rho vx1 vx2 vx3 prs tr1
1 3.007818e+03 2.013615e+02 49 single_file little rho vx1 vx2 vx3 prs tr1
2 6.028202e+03 2.013557e+02 64 single_file little rho vx1 vx2 vx3 prs tr1
3 9.048493e+03 2.013492e+02 79 single_file little rho vx1 vx2 vx3 prs tr1
4 1.206869e+04 2.013434e+02 94 single_file little rho vx1 vx2 vx3 prs tr1
5 1.533007e+04 4.390816e+01 111 single_file little rho vx1 vx2 vx3 prs tr1
```

The generated grid matches the intended gate dimensions:

```text
X1: [-200.000000,  200.000000], 400 point(s), 3 ghosts
X2: [-200.000000,  200.000000], 400 point(s), 3 ghosts
X3: [-250.000000,  250.000000], 500 point(s), 3 ghosts
```

HDF5 metadata smoke on the final file:

```text
outputs/data.0005.dbl.h5
Timestep_5   Group
cell_coords  Group
node_coords  Group
```

## Next

The environment/MPI/HDF5 path is green for both confirmed Stewart tabulated
environments. The next science move is an early, restartable,
particles-enabled `C-HI` segment using the locked configuration package and the
production template's `-maxtime`/`dbl.h5` restart path.
