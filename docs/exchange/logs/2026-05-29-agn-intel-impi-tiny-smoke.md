# 2026-05-29 AGN Intel/IMPI Tiny Smoke

## Session Context

- Machine used: Mac Mini
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- Target checked: `kunanyi` via the usual TPAC jumpbox route
- Reason: Patrick changed `/ds/projects/agn` permissions so Barry's account
  should now be able to traverse the AGN module and library tree.

## Permission / Module Result

Patrick's permission change worked. The AGN project directory now reports:

```text
drwxrwxr-x 10 pmyates agn ... /ds/projects/agn
drwxrwxr-x 12 pmyates agn ... /ds/projects/agn/libraries
drwxrwxr-x  9 pmyates agn ... /ds/projects/agn/modulefiles
```

The exact stack requested by Patrick-agent loaded successfully:

```bash
module purge
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5
```

Recorded module/compiler state:

```text
intel/18.0.1.163
impi/2018.1.163
hdf5/1.12.1p
zfp/0.5.5
mpicc=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc
mpirun=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun
HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi
```

## PBS Smoke

Command used:

```bash
scripts/kunanyi/stage_and_submit_agn_intel_impi_tiny_smoke.sh
```

Submission result:

```text
PBS job: 696012.kunanyi-ohpc
queue: test
request: select=2:ncpus=8:mpiprocs=8
walltime: 00:20:00
nodes: (n166:ncpus=8)+(n190:ncpus=8)
resources_used.walltime: 00:17:39
Exit_status: 0
```

The smoke rebuilt PLUTO with `ARCH = Kunanyi.defs`,
`KUNANYI_MODULE_STACK=agn_intel_impi`, and `MPI_FLAVOR=intelmpi`, then ran the
tiny 3D Cartesian case across 16 ranks.

Output evidence:

```text
data.0000.dbl
data.0001.dbl
data.0002.dbl
grid.out
restart.out
logs/pluto.0.log ... logs/pluto.15.log
```

`dbl.out` reached the expected final output:

```text
0 0.000000e+00 1.000000e-03 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.497451e+02 6.727975e-01 282 single_file little rho vx1 vx2 vx3 prs tr1
2 3.000000e+02 2.431960e-01 506 single_file little rho vx1 vx2 vx3 prs tr1
```

Rank 0 ended normally:

```text
> Writing file #2 (dbl) to disk...
> Elapsed time              0d:0h:0m:24s
> Done
```

## Caveats

PBS stderr contains two non-fatal notes:

```text
Lmod has detected the following error: You can only have one compiler module
loaded at a time.
You already have intel loaded.
```

and:

```text
/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem: line 11: git: command not found
```

Neither prevented the build or run. The error scan did not find the previous
OpenMPI/UCX `UD endpoint ... unhandled timeout error` signature.

## Interpretation

Patrick's permission fix is sufficient for the AGN stack, and the small
Intel/IMPI PLUTO run is green. The next useful step is a larger but still
bounded production-style `C-HI` startup/restart test under this same stack,
before spending another 80-node allocation.
