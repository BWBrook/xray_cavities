# C-HI Projection-Bin Refinement

Date: 2026-06-24
Agent: `jet`
Goal: `015-c-hi-projection-bin-refinement`
Status: `complete_method_refinement`

## Summary

Refined the local nonzero-view X-ray projection accumulator so near-90-degree
views do not create pathological all-zero projected columns from center-only
cell assignment on stretched/nonuniform grids.

Decision label:

```text
LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN
```

## Evidence Read

- `AGENTS.md`
- `docs/exchange/current_status.md`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv`
- `scripts/science/diagnose_90deg_xray_striping.py`
- `tests/test_90deg_xray_striping_diagnostic.py`
- `scripts/science/xraise_grid_smoke.py`
- `tests/test_xraise_grid_smoke_projection.py`
- Goal 011/012 notes and compact asset context sufficient to preserve the
  accepted historical-product boundary

## Files Created Or Updated

- `scripts/science/xraise_grid_smoke.py`
- `tests/test_xraise_grid_smoke_projection.py`
- `scripts/science/diagnose_projection_bin_refinement.py`
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/synthetic_occupancy_comparison.csv`
- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/method_comparison.csv`
- `docs/exchange/current_status.md`
- `docs/exchange/logs/2026-06-24-c-hi-projection-bin-refinement.md`
- `docs/goals/015-c-hi-projection-bin-refinement/Log.md`

No `agent_comms` files were changed.

## Implementation Summary

The nonzero-view accumulator now:

1. derives source-cell edges from coordinate centres;
2. projects all source-cell corners into the sky-horizontal `u` coordinate;
3. deposits each source cell into every overlapping projected output bin; and
4. weights by interval overlap while conserving integrated path weight.

The normal `0 deg` product path remains the direct y-axis sum.

## Synthetic Result

The generated diagnostic assets show:

```text
near90_stretched_grid legacy_center_bin empty_bins=18/24
near90_stretched_grid edge_overlap_uniform_cell_projection empty_bins=0/24
nonpathological_45deg_grid edge_overlap_uniform_cell_projection empty_bins=0/4
relative_conservation_error=0 for all synthetic rows
```

## Validation

Validation was run after creating the package:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py tests/test_90deg_xray_striping_diagnostic.py -q
7 passed

uv run python scripts/science/diagnose_projection_bin_refinement.py
decision_label=LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN
status=complete_diagnostic

CSV parse and expected-column checks
synthetic_occupancy_comparison.csv rows=4 columns_ok=10
method_comparison.csv rows=1 columns_ok=8

git diff --check
<no output>

targeted unresolved-marker scan
<no matches>
```

## Boundary Confirmation

No remote commands, Open OnDemand, SSH/SCP, PBS jobs, finalizers, Kunanyi
staging, remote retrieval, real HDF5 post-processing rerun, PLUTO production,
PRAiSE/radio/cavity product regeneration, source-age sweep, `C-LO`, `G-LO`,
comparison-case processing, broad batch work, document builds, commits,
pushes, scientific-default changes, external human/agent contact, or
`agent_comms` changes occurred.

Accepted Goal 011/012 product assets were read as historical evidence only and
were not overwritten.

## Recommended Next Step

Write the next goal as a bounded existing-output rerun for the affected
projection products, primarily final `C-HI`, `90 deg`, with a `45 deg` sanity
rerun if authorized. The rerun should compare before/after empty-bin occupancy
and scalar X-ray summaries before deciding whether source-age sampling can
proceed.
