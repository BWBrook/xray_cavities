# C-HI 2-Node Continuation Toward 10 Myr

Date: 2026-05-10

## Purpose

Continue the existing particles-enabled high-power cluster run from the latest
restartable HDF5 checkpoint toward the next block of regular science outputs.
This is still the reduced-grid `kunanyi` shakedown lane, not the final full-grid
science production allocation.

## Access Route

Direct MacBook SSH to `<tpac-host>` timed out again from the current
network path, so the submission used the validated Nectar-bastion route:

```text
MacBook -> nectar-codex -> tpac-jumpbox-via-nectar -> kunanyi-via-nectar
```

The TPAC Open OnDemand SSH window was refreshed with
`scripts/kunanyi/enable_jumpbox_ssh_safari.sh`.

## Preflight

Remote problem directory:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem
```

Preflight confirmed:

- `./pluto` exists and is executable
- latest restart-capable HDF5 checkpoint is `outputs/data.0005.dbl.h5`
- `outputs/dbl.h5.out` ends at output `5`, code time `1.672524e+03`,
  nominal step `5495`
- the corresponding physical time is about `5.455 Myr`
- regular `flt.h5` outputs exist through output `9`, the walltime stop output
  associated with the same final time

## Submitted Job

PBS job:

```text
690650.kunanyi-ohpc
```

Job name:

```text
c_hi_to10
```

Submission overrides:

```text
queue: normal
select: 2:ncpus=28:mpiprocs=28
walltime: 07:00:00
PLUTO_MAXTIME_HOURS: 6.5
RUN_ROOT: /scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment
CASE_ID: C-HI
CASE_VARIANT: particles
RESTART_POLICY: auto
ALLOW_DONE_RERUN: 1
```

The production template should auto-detect the latest HDF5 restart and run:

```text
./pluto -i pluto.ini -e environment.ini -maxtime 6.5 -h5restart 5
```

## Initial Monitor

The job entered `R` state on:

```text
n093/0*28 + n103/0*28
```

Early `qstat -f` monitoring showed:

```text
job_state = R
resources_used.ncpus = 56
Resource_List.select = 2:ncpus=28:mpiprocs=28
Resource_List.walltime = 07:00:00
```

After a short startup interval, the job had allocated about `17 GB` job memory
and was accumulating CPU time. The PLUTO log was present at:

```text
/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment/C-HI/particles/problem/outputs/logs/pluto_690650.kunanyi-ohpc.log
```

## Expected Follow-Up

When the PBS email lands, retrieve and check:

- PBS exit status and resource use
- tail of `outputs/flt.h5.out`
- tail of `outputs/dbl.h5.out`
- final PLUTO log
- whether regular outputs now cover the next target block, ideally through
  about `10 Myr`

Then run the same compact diagnostics used for the early snapshot series on the
new outputs before extending again.

## Full-Grid Production Allocation Note

The meeting transcript contains a much larger supervisor-side production
reference point than the reduced-grid shakedown jobs. Stas described a standard
run as about:

```text
80 nodes x 28 cores per node
```

with roughly three `48 h` chunks to reach `100 Myr` at the desired resolution.
Therefore the true full-grid `C-HI` 50 Myr production run should be planned
around that scale, after a short scaling confirmation, rather than around the
current 2-node shakedown allocation.
