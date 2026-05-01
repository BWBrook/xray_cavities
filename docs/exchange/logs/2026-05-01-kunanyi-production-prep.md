# 2026-05-01 kunanyi Production Preparation Notes

## Summary

The `kunanyi` infrastructure path is now ready for full simulation jobs once
the science cases are properly specified and packaged. The remaining work is
production preparation, not basic HPC access.

The validated launch path now includes:

- jumpbox and login-node access
- PBS submission from `kunanyi`
- scheduler-owned jobs that continue after disconnect
- email notifications to `barry.brook@utas.edu.au`
- GCC/OpenMPI/HDF5 module stack
- PLUTO build/run under PBS
- `jet-setup` build/run under PBS
- one-node and two-node MPI execution
- rank count derived from `PBS_NODEFILE`

## Preparation Passes Added

`docs/kunanyi_setup.md` now records the remaining gates before serious 3D jobs:

1. lock the case specification
2. build a production PBS template
3. add restart/resume handling and `DONE`/`FAILED` markers
4. confirm output volume and data retention/transfer plan
5. run an intermediate-size rehearsal
6. launch production jobs only after the above are green

The expected production resource pattern is:

```bash
#PBS -l select=N:ncpus=28:mpiprocs=28
#PBS -M barry.brook@utas.edu.au
#PBS -m ae

NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

## Collaborator Summary

A short update for Stas and Patrick was added at:

```text
docs/kunanyi_status_update_2026-05-01.md
docs/kunanyi_status_update_2026-05-01.pdf
```

The PDF is intended as a concise status handoff, not a full technical log.
