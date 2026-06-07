# C-HI full-grid final quick-look extraction submitted

Date: 2026-06-07

## Summary

A compact quick-look extraction job was submitted against the final float HDF5
product from the completed 64-node `prod64` endpoint.

## Submission

```text
PBS Job Id: 697386.kunanyi-ohpc
Job Name:   c_hi_final_ql
queue:      normal
request:    select=1:ncpus=1:mpiprocs=1:mem=32gb
walltime:   01:00:00
```

Input:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
```

Timestep:

```text
Timestep_51
```

Extractor and wrapper staged on Kunanyi:

```text
/u/bwbrook/codex_kunanyi/pluto_h5_quicklook_extract.c
/u/bwbrook/codex_kunanyi/c_hi_quicklook_extract.pbs
```

Compact output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-quicklook
```

PBS stdout/stderr:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_quicklook.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_quicklook.err
```

## Initial State

The job entered the running state promptly:

```text
job_state = R
comment = Job run at Sun Jun 07 at 14:58 on (n004:ncpus=1:mem=33554432kb)
resources_used.walltime = 00:01:50
resources_used.mem = 22188kb
```

At that poll, stdout/stderr files were not yet populated.

## Follow-up

When the job completes, fetch the compact quick-look directory, render local
plots with `scripts/science/plot_pluto_h5_quicklook.py`, and add the final
science quick-look report under `docs/science/`.
