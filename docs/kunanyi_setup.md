# kunanyi Setup Notes

Last updated: 2026-04-30

These notes record the first successful MacBook control-plane access path to
TPAC's `kunanyi` HPC.

## Access Model

Direct SSH uses a short-lived jumpbox access window opened from the Open
OnDemand portal.

1. Open the TPAC Open OnDemand portal.
2. Enable the 5-minute jumpbox SSH window.
3. SSH to the jumpbox:

```bash
ssh tpac-jumpbox
```

4. From the jumpbox, SSH to the `kunanyi` login node:

```bash
ssh kunanyi
```

Local Mac SSH aliases are configured in `~/.ssh/config`:

```sshconfig
Host tpac-jumpbox
  HostName <tpac-host>
  User bwbrook
  ServerAliveInterval 30

Host kunanyi
  HostName kunanyi
  User bwbrook
  ProxyJump tpac-jumpbox
  ServerAliveInterval 30
```

The first successful login path landed on:

- jumpbox: `jumpbox-2`
- login node: `<tpac-host>`

## Secret Location

The Mac stores TPAC credentials outside the repo at:

```text
/Users/bwbrook/.config/tpac/kunanyi.env
```

Expected contents:

```bash
TPAC_USER='bwbrook'
TPAC_PASSWORD='...'
```

The file should remain mode `600`.

## Filesystems

TPAC-provided paths:

- home: `/u/bwbrook`
- scratch: `/scratch/bwbrook`

Use scratch for job working directories. It is not backed up.

## Login Node Inventory

Confirmed on `kunanyi-00`:

- shell: `/bin/bash`
- `qsub`: `/opt/pbs/bin/qsub`
- `qstat`: `/opt/pbs/bin/qstat`
- PBS server: `kunanyi-ohpc`
- PBS status: active
- Lmod is available:
  - `Modules based on Lua: Version 8.1.18`

Observed queues included:

- `test`
- `normal`
- `express`
- `LARGE_MEM`
- `MEM512GB`

Do not run simulations or compiles on the login node. Submit work through PBS,
or request an interactive job for builds.

## First PBS Smoke Test

The first clean PBS compute-node smoke used:

- script: `scripts/kunanyi/smoke_job.pbs`
- remote scratch directory: `/scratch/bwbrook/codex_smoke`
- queue: `test`
- resources: `select=1:ncpus=1`, `walltime=00:02:00`

Submission result:

```text
SUBMITTED=688913.kunanyi-ohpc
```

Output confirmed execution on a compute node:

```text
HOST=n001.kunanyi
USER=bwbrook
PWD=/scratch/bwbrook/codex_smoke
PBS_JOBID=688913.kunanyi-ohpc
PBS_O_WORKDIR=/scratch/bwbrook/codex_smoke
PBS_QUEUE=test
PBS_NODEFILE=/var/spool/pbs/aux/688913.kunanyi-ohpc
NODEFILE_CONTENTS=n001.kunanyi
NCPUS=28
```

The job printed locale warnings to stderr:

```text
setlocale: LC_ALL: cannot change locale (C.UTF-8)
```

These warnings did not prevent job execution. If they become noisy in later
automation, set a compatible locale before SSH/PBS submission.

## Next HPC Smoke Steps

1. Clone or sync the UTAS AGN repos into `/scratch/bwbrook` or another agreed
   working location.
2. Build a tiny PLUTO case under PBS.
3. Retrieve artifacts back through jumpbox/home.

The local helper for targeted module inventory is:

```bash
scripts/kunanyi/module_inventory.sh
```

It expects an active TPAC jumpbox SSH window and reads credentials from
`/Users/bwbrook/.config/tpac/kunanyi.env`.

## Module Inventory

Confirmed on `2026-05-01`:

- `HDF5/1.14.0-gompi-2023a`
- `OpenMPI/4.1.5-GCC-12.3.0`
- `GCC/12.3.0`
- `CMake/3.26.3-GCCcore-12.3.0`
- `Python/3.11.3-GCCcore-12.3.0`
- `git/2.41.0-GCCcore-12.3.0-nodocs`
- `netCDF/4.9.2-gompi-2023a`

The best first PLUTO/HDF5 stack is:

```bash
module purge
module load HDF5/1.14.0-gompi-2023a
```

This loads the GCC 12.3 / OpenMPI 4.1.5 / HDF5 1.14.0 `gompi/2023a`
environment.

## MPI + Parallel HDF5 Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/hdf5_probe.pbs`
- job id: `688922.kunanyi-ohpc`
- queue: `test`
- compute node: `n001.kunanyi`
- scratch workdir: `/scratch/bwbrook/codex_hdf5_probe`

The job loaded `HDF5/1.14.0-gompi-2023a`, compiled a C smoke program with
`h5pcc`, ran it with `mpirun -np 2`, and created/dumped
`mpi_hdf5_smoke.h5`.

Key output:

```text
mpirun (Open MPI) 4.1.5
MPI ranks: 2
Parallel HDF5 file created.
```

This validates that the core compiler/MPI/HDF5 stack needed for PLUTO HDF5
smoke work is available and works on a compute node.
