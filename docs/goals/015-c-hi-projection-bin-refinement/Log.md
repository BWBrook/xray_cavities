# Log: Goal 015 C-HI Projection-Bin Refinement

## 2026-06-24 - start state

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
a3369cf

git fetch --prune origin
<no output>

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
a3369cf
```

Repo-local `AGENTS.md` was read before project work. The worktree was clean at
start and no fast-forward was needed.

## 2026-06-24 - evidence and code read

Read scoped, repo-local evidence/code:

- `docs/exchange/current_status.md`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv`
- `scripts/science/diagnose_90deg_xray_striping.py`
- `tests/test_90deg_xray_striping_diagnostic.py`
- `scripts/science/xraise_grid_smoke.py`
- `tests/test_xraise_grid_smoke_projection.py`
- Goal 011 and Goal 012 notes/assets only enough to preserve context and avoid
  touching accepted historical products

Relevant Goal 014 evidence:

- `90 deg` raw/corrected/correction-ratio X-ray layers each had `400/960`
  all-zero projected columns.
- `45 deg` raw/corrected/correction-ratio X-ray layers each had `22/960`
  all-zero projected columns.
- `0 deg` corrected X-ray had no all-zero projected columns.
- The `90 deg` raw/corrected/correction-ratio positive masks were identical.
- The `90 deg` `x_kpc.tsv`/`u_kpc.tsv` identity was expected by the current
  nonzero-view writer and was not itself suspicious.

## 2026-06-24 - implementation

Updated `scripts/science/xraise_grid_smoke.py`:

- added `projected_overlap_contributions`;
- changed nonzero-view chunk accumulation from center-bin assignment to
  projected source-cell interval overlap;
- used full-grid `x_edges` and chunk-sliced `y_edges` in the real run path;
- preserved the normal `0 deg` direct y-axis sum path; and
- recorded `projection.projected_accumulation` in future metadata.

The refined nonzero-view method deposits each source cell into every output
`u` bin overlapped by that cell's projected `u_min/u_max` interval, with
weights proportional to overlap length and normalized by projected source-cell
width and output-bin width.

Updated `tests/test_xraise_grid_smoke_projection.py`:

- added a small legacy center-bin reproducer for the old failure mode;
- proved a stretched near-90-degree synthetic grid leaves many empty bins under
  center-bin assignment;
- proved the refined method removes those bins;
- proved raw/corrected integrated path weights are conserved;
- strengthened the existing 45-degree conservation test with nonempty
  projected-bin occupancy; and
- preserved the existing 0-degree direct-projection expectation.

## 2026-06-24 - diagnostic assets

Created `scripts/science/diagnose_projection_bin_refinement.py`.

Generated:

- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/synthetic_occupancy_comparison.csv`
- `docs/science/assets/c_hi_projection_bin_refinement_2026-06-24/method_comparison.csv`

Key generated rows:

```text
near90_stretched_grid legacy_center_bin empty_bins=18/24
near90_stretched_grid edge_overlap_uniform_cell_projection empty_bins=0/24
nonpathological_45deg_grid legacy_center_bin empty_bins=1/4
nonpathological_45deg_grid edge_overlap_uniform_cell_projection empty_bins=0/4
```

All synthetic rows have `relative_conservation_error=0`.

## 2026-06-24 - docs and status package

Created:

- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/exchange/logs/2026-06-24-c-hi-projection-bin-refinement.md`
- this Goal 015 log

Updated:

- `docs/exchange/current_status.md`

No `agent_comms` files were changed.

## 2026-06-24 - decision

Decision label:

```text
LOCAL_METHOD_REFINED_READY_FOR_BOUNDED_RERUN
```

The synthetic/local proof supports a later bounded existing-output rerun for
the affected X-ray/tracer projection products, primarily final `C-HI`,
`90 deg`, with a `45 deg` sanity rerun if authorized. It does not authorize a
source-age sweep, `C-LO`, `G-LO`, comparison-case processing, radio observable
generation, or publication-ready claims.

## 2026-06-24 - validation and closeout

Validation:

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

targeted unresolved-marker scan over the new note, exchange log, current
status, and Goal 015 log
<no matches>
```

Final status:

```text
complete_method_refinement
```

Boundary confirmation: no remote commands, Open OnDemand, SSH/SCP, PBS jobs,
finalizers, Kunanyi staging, remote retrieval, real HDF5 post-processing rerun,
PLUTO production, PRAiSE/radio/cavity product regeneration, source-age sweep,
`C-LO`, `G-LO`, comparison-case processing, broad batch work, document builds,
commits, pushes, scientific-default changes, external human/agent contact, or
`agent_comms` changes occurred. Accepted Goal 011/012 product assets were not
overwritten.
