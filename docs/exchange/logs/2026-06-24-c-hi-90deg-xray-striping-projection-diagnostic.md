# C-HI 90-Degree X-Ray Striping Projection Diagnostic

Date: 2026-06-24
Agent: `jet`
Goal: `014-c-hi-90deg-xray-striping-projection-diagnostic`
Status: `complete_diagnostic`

## Summary

Created a local-only diagnostic package for the visible vertical striping in
the Goal 012 `90 deg` corrected X-ray panel.

Recommendation label:

```text
X_RAY_METHOD_REFINEMENT_FIRST
```

The evidence points to a projection/binning occupancy issue at or near
`90 deg`. The symptom is in the local matrix data, not just the rendered
figure, and it is shared by raw X-ray, corrected X-ray, and correction-ratio
layers.

## Evidence Read

- `AGENTS.md`
- `docs/exchange/current_status.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23.md`
- Goal 005, Goal 011, Goal 012, and Goal 013 compact assets sufficient for the
  current `0/45/90 deg` decision context
- `scripts/science/xraise_grid_smoke.py`
- `scripts/science/build_final_45deg_viewing_angle_broadening.py`
- `scripts/science/build_final_90deg_viewing_angle_broadening.py`
- Visual inspection of the Goal 012 review figure

## Files Created Or Updated

- `scripts/science/diagnose_90deg_xray_striping.py`
- `tests/test_90deg_xray_striping_diagnostic.py`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/next_step_recommendation.csv`
- `docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/column_positive_fraction_profiles.png`
- `docs/exchange/logs/2026-06-24-c-hi-90deg-xray-striping-projection-diagnostic.md`
- `docs/goals/014-c-hi-90deg-xray-striping-projection-diagnostic/Log.md`
- `docs/exchange/current_status.md`

No `agent_comms` files were changed.

## Key Evidence

- `90 deg` raw, corrected, and correction-ratio X-ray layers each have
  `400/960` all-zero projected columns.
- `45 deg` raw, corrected, and correction-ratio X-ray layers each have
  `22/960` all-zero projected columns, consistent with a small edge occupancy
  effect.
- `0 deg` corrected X-ray has no all-zero columns.
- The `90 deg` raw/corrected/correction-ratio positive masks are identical.
- The `90 deg` `x_kpc.tsv` and `u_kpc.tsv` identity is expected from the
  current writer for nonzero projected views and is not itself suspicious.

## Interpretation

The evidence does not support a display-only issue, a correction-only issue,
or a physically meaningful cavity feature. It supports a local projection/
binning occupancy issue for near-exact side-on projection with the existing
uniform projected-bin, center-accumulation method.

## Validation

Validation was run after creating the package:

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

targeted unresolved-marker scan
<no matches>
```

## Boundary Confirmation

No remote commands, Open OnDemand, SSH/SCP, PBS jobs, finalizers, Kunanyi
staging, PLUTO production, XRAiSE/PRAiSE/radio/cavity product regeneration
from HDF5, source-age sweep, `C-LO`, `G-LO`, comparison-case processing, broad
batch work, document builds, commits, pushes, scientific-default changes,
external human/agent contact, or `agent_comms` changes occurred.

## Recommended Next Step

Write Goal 015 as a local X-ray/projection-method refinement goal. Q-018 and
Q-019 can remain non-blocking review inputs while X-ray Cavities handles this
diagnostic autonomously.
