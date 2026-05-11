# C-HI 80-Node Production-Scale Allocation Smoke

Date: 2026-05-11

## Purpose

Move from the reduced-grid `C-HI` shakedown lane toward production-scale
`kunanyi` usage by testing a supervisor-scale allocation shape without running
a science PLUTO segment yet.

The meeting transcript records Stas' standard-run ballpark as:

```text
80 nodes x 28 cores per node
```

This smoke therefore requests that exact allocation shape and validates:

- PBS can queue the allocation
- `$PBS_NODEFILE` expands to the expected `2240` slots
- OpenMPI can launch with an explicit hostfile derived from `$PBS_NODEFILE`
- the validated `HDF5/1.14.0-gompi-2023a` module stack supports a collective
  parallel-HDF5 write at that rank count

It does not run PLUTO science.

## PBS Script

Local and staged script:

```text
scripts/kunanyi/c_hi_80node_allocation_smoke.pbs
/u/bwbrook/codex_kunanyi/c_hi_80node_allocation_smoke.pbs
```

PBS request:

```pbs
#PBS -N c_hi_80alloc
#PBS -q normal
#PBS -l select=80:ncpus=28:mpiprocs=28
#PBS -l walltime=00:20:00
#PBS -M barry.brook@utas.edu.au
#PBS -m abe
```

`#PBS -m abe` is intentional: Barry should receive begin, abort, and end
emails, which is useful while this job waits for 80 free nodes.

## Queue Policy Check

Live queue inspection before submission showed:

```text
normal resources_max.walltime = 48:00:00
normal max_queued_res.ncpus = [u:PBS_GENERIC=7000]
express max_queued_res.ncpus = [u:PBS_GENERIC=980]
```

So the production-scale smoke belongs on `normal`, not `express`.

## Submitted Job

PBS job:

```text
690703.kunanyi-ohpc
```

Initial `qstat`:

```text
Job_Name = c_hi_80alloc
job_state = Q
queue = normal
Resource_List.select = 80:ncpus=28:mpiprocs=28
Resource_List.ncpus = 2240
Resource_List.mpiprocs = 2240
Resource_List.nodect = 80
Resource_List.walltime = 00:20:00
comment = Not Running: Not enough free nodes available
```

This is a normal queued state for an 80-node request on a busy cluster.

## Expected Outputs

If the job starts and completes successfully, it should create:

```text
/u/bwbrook/codex_kunanyi/c_hi_80node_allocation_smoke.out
/u/bwbrook/codex_kunanyi/c_hi_80node_allocation_smoke_690703.kunanyi-ohpc.tar.gz
/scratch/bwbrook/xray_cavities_alloc_smokes/690703.kunanyi-ohpc/
```

The summary archive should contain:

- `allocation_summary.txt`
- `pbs_nodefile.txt`
- `ompi_hostfile`
- `mpi_hdf5_alloc_smoke.out`

Pass criteria:

- PBS allocates `80` unique nodes
- PBS exposes `2240` ranks
- MPI reduced rank count equals `2240`
- MPI rank-sum check matches `2240 * 2239 / 2`
- HDF5 file is non-empty after collective write

## Follow-Up

When the PBS email lands, fetch the summary archive and inspect:

- `Exit_status`
- node list and node count
- MPI rank count and rank sum
- HDF5 byte count
- any OpenMPI launch warnings or node-level failures

If this smoke passes, the next production-scale gate should be a short PLUTO
startup/checkpoint test at production rank count before committing to a full
48-hour science segment.
