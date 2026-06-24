# Log: Goal 014 C-HI 90-Degree X-Ray Striping Projection Diagnostic

## 2026-06-24 - start state

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
cb87524

git fetch --prune origin
<no output>

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
cb87524
```

Repo-local `AGENTS.md` was read before project work. The worktree was clean at
start and no fast-forward was needed.

## 2026-06-24 - evidence and code read

Read scoped, repo-local evidence:

- `docs/exchange/current_status.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23.md`
- Goal 005, Goal 011, and Goal 012 logs and compact product assets sufficient
  for the accepted `0/45/90 deg` viewing-angle trio
- Goal 012 metadata, review figure, projection metrics, trio comparison, XRAiSE
  summary, and map TSV assets
- Goal 013 decision note and matrix, scoped to current recommendation context
- `scripts/science/xraise_grid_smoke.py`
- `scripts/science/build_final_45deg_viewing_angle_broadening.py`
- `scripts/science/build_final_90deg_viewing_angle_broadening.py`
- visual inspection of
  `docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/c_hi_final_90deg_viewing_angle_broadening.png`

Key findings from code inspection:

- `xraise_grid_smoke.py` writes `x_kpc.tsv` and `u_kpc.tsv` as the same
  projected sky-horizontal axis for nonzero projected views. This makes
  product-local `x/u` identity expected for `45 deg` and `90 deg`.
- Projected views use uniform projected bins and center-bin accumulation.
- At `90 deg`, the projected horizontal coordinate is effectively the original
  `y` direction with sign reversal, so the current method can create empty bins
  on a stretched/nonuniform source grid.

## 2026-06-24 - diagnostic helper and assets

Created:

- `scripts/science/diagnose_90deg_xray_striping.py`
- `tests/test_90deg_xray_striping_diagnostic.py`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/next_step_recommendation.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/column_positive_fraction_profiles.png`

The helper quantifies finite/positive cell fractions, all-zero and near-empty
projected columns, adjacent-column versus adjacent-row contrast, raw/corrected
mask equality, and axis regularity. The generated recommendation was:

```text
recommendation_label=X_RAY_METHOD_REFINEMENT_FIRST
status=complete_diagnostic
```

Key diagnostics:

- `90 deg` raw/corrected/correction-ratio X-ray layers each have `400/960`
  all-zero projected columns.
- `45 deg` raw/corrected/correction-ratio X-ray layers each have `22/960`
  all-zero projected columns.
- `0 deg` corrected X-ray has `0/960` all-zero columns.
- `90 deg` raw/corrected/correction-ratio positive masks are identical.
- The `90 deg` `x_kpc.tsv` and `u_kpc.tsv` identity is expected by the current
  writer and is not by itself suspicious.

## 2026-06-24 - docs and status package

Created:

- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/exchange/logs/2026-06-24-c-hi-90deg-xray-striping-projection-diagnostic.md`
- this Goal 014 log

Updated:

- `docs/exchange/current_status.md`

No `agent_comms` files were changed. Q-018 and Q-019 remain useful review
inputs but are no longer treated as blockers for a local X-ray/projection-method
refinement next goal.

## 2026-06-24 - interpretation

The local evidence supports:

```text
projection/binning occupancy issue
```

It does not support:

- display-only artifact;
- APEC/Gaunt correction-only artifact;
- physically meaningful cavity feature;
- immediate escalation to Stas-agent or Patrick-agent.

Decision output:

```text
X_RAY_METHOD_REFINEMENT_FIRST
```

Recommended next step: write a local X-ray/projection-method refinement goal
that reproduces the empty-bin failure with a synthetic stretched grid, revises
the near-90-degree projected binning/accumulation method, and reruns only
bounded existing-output post-processing if the local method test passes and
X-ray Cavities authorizes it.

## 2026-06-24 - validation and closeout

Validation:

```text
uv run pytest tests/test_90deg_xray_striping_diagnostic.py -q
3 passed

uv run python scripts/science/diagnose_90deg_xray_striping.py
recommendation_label=X_RAY_METHOD_REFINEMENT_FIRST
status=complete_diagnostic

CSV parse and expected-column checks
striping_diagnostics.csv rows=10 columns_ok=18
projection_axis_diagnostics.csv rows=8 columns_ok=15
next_step_recommendation.csv rows=1 columns_ok=7

git diff --check
<no output>

targeted unresolved-marker scan over the new note, exchange log, current
status, and Goal 014 log
<no matches>
```

Final status:

```text
complete_diagnostic
```

Boundary confirmation: no remote commands, Open OnDemand, SSH/SCP, PBS jobs,
finalizers, Kunanyi staging, PLUTO production, XRAiSE/PRAiSE/radio/cavity
product regeneration from HDF5, source-age sweep, `C-LO`, `G-LO`,
comparison-case processing, broad batch work, document builds, commits, pushes,
scientific-default changes, external human/agent contact, or `agent_comms`
changes occurred.
