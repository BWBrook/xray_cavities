# C-HI full-grid final particle-HDF5 feasibility preflight submitted

Date: 2026-06-08

## Summary

A bounded one-node feasibility preflight was submitted before attempting any
full-history particle-HDF5 cache for the completed 50 Myr full-grid `C-HI`
endpoint.

This is intentionally not the full cache build. The estimator loads only the
final particle output, reads the final particle count and field dimensions, and
estimates the matrix size and likely peak memory cost of a naive
`plutokore.load_all_particles()` full-history cache.

## Submission

```text
PBS Job Id: 697639.kunanyi-ohpc
Job Name:   c_hi_ph5_pf
request:    select=1:ncpus=1:mpiprocs=1:mem=8gb
walltime:   00:30:00
```

Wrapper:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight.pbs
```

Estimator:

```text
/u/bwbrook/codex_kunanyi/particle_loss_runtime/estimate_particle_hdf5_feasibility.py
```

Input run output directory:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs
```

Expected preflight output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-particle-hdf5-preflight
```

Expected summary archive:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight_2026-06-07.tar.gz
```

## Staging Notes

The helper files were committed locally and pushed as:

```text
bab5037 Add C-HI particle cache feasibility preflight
```

Because unauthenticated GitHub raw fetches returned `404` for this repository,
the helper payload was copied from the Mac to Kunanyi by `scp` as a small tarball
and extracted under `/u/bwbrook/codex_kunanyi`.

Kunanyi `tar` printed harmless macOS extended-attribute warnings:

```text
tar: Ignoring unknown extended header keyword `LIBARCHIVE.xattr.com.apple.provenance'
```

The warnings did not block extraction; `qsub` then returned
`697639.kunanyi-ohpc`.

## Follow-up

When Barry's PBS completion email lands, inspect stdout/stderr and the preflight
summary files. The key output is the recommendation string:

```text
BUILD_PLAUSIBLE_WITH_DECLARED_MEMORY
DO_NOT_BUILD_FULL_HISTORY_CACHE_WITH_CURRENT_APPROACH
```

If the recommendation is negative, do not submit a blind full-history cache
build. Move to a smaller particle-history window, endpoint-only particle
diagnostics, or a streaming/sparse particle analysis design.
