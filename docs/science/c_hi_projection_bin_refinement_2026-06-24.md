# C-HI Projection-Bin Refinement

Date: 2026-06-24

## Summary

Goal 015 refines the local projected-view X-ray accumulation method used by
`scripts/science/xraise_grid_smoke.py`. The change addresses the Goal 014
diagnosis that the accepted Goal 012 `90 deg` product has pathological
all-zero projected columns from center-bin accumulation on a stretched/
nonuniform source grid.

Decision label:

```text
LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN
```

The new local method is an edge-overlap projected-bin accumulator. Each source
cell is projected into a finite `u` interval, contributes to every overlapping
projected output bin, and preserves the integrated path-weight scalar. The
normal `0 deg` run path remains the direct y-axis sum.

This goal did not rerun real HDF5 products. It just changes and proves the
local projection method with synthetic diagnostics. A later bounded
existing-output rerun is now justified for `90 deg`, with a `45 deg` sanity
check if X-ray Cavities authorizes it.

## Context

Goal 014 found:

- `90 deg` raw/corrected/correction-ratio X-ray layers each have `400/960`
  all-zero projected columns.
- `45 deg` raw/corrected/correction-ratio X-ray layers each have `22/960`
  all-zero projected columns.
- `0 deg` corrected X-ray has no all-zero projected columns.
- the `90 deg` raw/corrected/correction-ratio positive masks are identical.
- product-local `x_kpc.tsv`/`u_kpc.tsv` identity is expected from the current
  nonzero-view writer and is not itself suspicious.

That points to a local projection/binning occupancy issue, not a display-only
artifact, correction-only artifact, physical cavity feature, or immediate
Stas/Patrick escalation.

## Method Change

Previous nonzero-view path:

1. compute each source cell center's projected coordinate
   `u = x*cos(theta) - y*sin(theta)`;
2. assign the entire cell area/path contribution to the one projected bin
   containing that center; and
3. scale by source-cell area divided by output-bin width.

This can leave empty projected bins when the output `u` bins are finer or
phase-shifted relative to a stretched/nonuniform source grid, especially near
`90 deg` where the projected coordinate is effectively the original `y`
direction.

New nonzero-view path:

1. compute source-cell edges from the coordinate centres;
2. project all four source-cell corners into `u`;
3. use the projected `u_min/u_max` interval for that source cell;
4. deposit the cell contribution into every output bin that overlaps the
   projected interval; and
5. weight each contribution by
   `source_cell_area * overlap_length / (projected_cell_width * output_bin_width)`.

This is a deterministic first-order finite-volume remap over the projected
cell interval. It is deliberately conservative: it preserves integrated
path-weight scalars and removes empty-bin artifacts without changing XRAiSE
physics, APEC/Gaunt correction semantics, PLUTO inputs, tracer thresholds,
cavity methods, PRAiSE/radio contracts, or energy conventions.

For nonzero views, new metadata records:

```text
projection.projected_accumulation=edge_overlap_uniform_cell_projection
```

For `0 deg`, metadata records:

```text
projection.projected_accumulation=direct_y_axis_sum
```

## Synthetic Proof

Compact synthetic assets:

```text
docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/synthetic_occupancy_comparison.csv
docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/method_comparison.csv
```

The synthetic near-90-degree stretched-grid case reproduces the old pathology:

| Scenario | Method | Projected bins | Positive bins | Empty bins | Empty fraction | Conservation error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| near90 stretched grid | legacy center bin | `24` | `6` | `18` | `0.75` | `0` |
| near90 stretched grid | edge-overlap refinement | `24` | `24` | `0` | `0` | `0` |

The nonpathological 45-degree synthetic case remains sane:

| Scenario | Method | Projected bins | Positive bins | Empty bins | Empty fraction | Conservation error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| nonpathological 45-degree grid | legacy center bin | `4` | `3` | `1` | `0.25` | `0` |
| nonpathological 45-degree grid | edge-overlap refinement | `4` | `4` | `0` | `0` | `0` |

Focused tests also prove:

- the old center-bin behavior reproduces pathological empty bins on a stretched
  near-90-degree grid;
- the refined overlap method removes those empty bins;
- raw and corrected integrated path weights are conserved;
- tracer occupancy follows overlapping projected cells;
- `0 deg` accumulation still matches the direct y-projection expectation; and
- `45 deg` projected accumulation remains finite, nonempty, and conservative.

## Decision

The local method is refined enough to justify a later bounded existing-output
rerun:

```text
LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN
```

Recommended next goal:

1. rerun only the bounded existing-output X-ray/tracer post-processing for
   final `C-HI`, `90 deg` with the refined accumulator;
2. include a `45 deg` sanity rerun if runtime and packet boundaries allow;
3. regenerate only the affected compact comparison/diagnostic assets; and
4. compare before/after empty-bin occupancy and scalar X-ray summaries before
   deciding whether source-age sampling can proceed.

The later rerun should remain bounded and should not open source-age sampling,
`C-LO`, `G-LO`, comparison-case processing, radio observables, broad batch
work, or publication-ready claims by implication.

## Caveats

- The refined method is locally and synthetically proven, but it has not yet
  been applied to the real Goal 012 HDF5-derived product.
- The method is a first-order uniform remap over each cell's projected
  interval. It is conservative and removes the diagnosed occupancy pathology,
  but it is not a claim of final instrument-grade X-ray projection.
- The connected-envelope/X-ray topology caveat remains active.
- Sparse-radio products remain diagnostics, not validated radio observables.
- Level 3 gravity remains `blocked_missing_potential`.
- Q-018 and Q-019 remain useful review inputs but are not blockers for a
  local bounded rerun/refinement path.

## Non-Claims

- No accepted Goal 011/012 product assets were overwritten.
- No real HDF5 post-processing was rerun.
- No remote commands, Open OnDemand, SSH/SCP, PBS jobs, finalizers, Kunanyi
  staging, PLUTO production, PRAiSE/radio/cavity product regeneration,
  source-age sweep, `C-LO`, `G-LO`, comparison-case processing, broad batch
  work, document builds, commits, pushes, scientific-default changes, or
  external human/agent contact occurred.
