# 2026-07-01 C-HI Residual-Threshold Sensitivity Review

## Summary

Goal 026 created a local residual-threshold topology sensitivity review
package. The decision label is
`CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL`.

The narrow residual-core masks at `0.5`, `1`, and `2` percent classify as
`connected_envelope_single_system`; the `3`, `5`, `10`, and `20` percent masks
become `ambiguous_needs_review` because broader masks mix the connected core
with side-specific seeded structure and unlabelled residual islands.

## Files

Science note:

- `docs/science/c_hi_residual_threshold_sensitivity_review_2026-07-01.md`

Builder/tests:

- `scripts/science/build_residual_threshold_sensitivity_review.py`
- `tests/test_residual_threshold_sensitivity_review.py`

Asset bundle:

- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_component_sensitivity.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/mask_seed_overlap_summary.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/figure_provenance.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity_metadata.json`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.png`

Goal log:

- `docs/goals/026-c-hi-residual-threshold-sensitivity-review/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 025 science note/assets/log and
  `scripts/science/build_existing_asset_topology_application_design.py`.
- Goal 024 helper/tests, including direct-mask and seeded-only classification
  behavior.
- Goal 005 corrected X-ray, tracer max LOS, and axis compact assets.
- Goal 007 observational-product readiness metadata/topology context as
  residual-display provenance.

## Result

The connected residual core is preserved at the narrow residual thresholds and
should remain visible as a conditional method result. The threshold transition
at `3` percent prevents a final endpoint topology claim.

Recommended next step:

```text
bounded_conditional_endpoint_topology_application_package
```

The package should remain no-overwrite and should present the threshold
sensitivity as part of the result, not hide it.

## Boundary Confirmation

This was local-only. No remote commands, Open OnDemand, SSH/SCP, `qstat`,
Kunanyi staging, PBS jobs, finalizers, retrieval, HDF5/XRAiSE reruns, PLUTO,
PRAiSE, radio, cavity regeneration, endpoint rerun, source-age substitution,
`C-LO`, `G-LO`, comparison-case processing, early-age branch, broad source-age
sweep, publication-facing claims, scientific-default changes, commits, pushes,
cleanup, `agent_comms` edits, or accepted-asset overwrites occurred.

## Validation

Local validation passed:

- `uv run pytest tests/test_residual_threshold_sensitivity_review.py tests/test_hybrid_xray_cavity_topology.py -q`
- `uv run python scripts/science/build_residual_threshold_sensitivity_review.py`
- JSON parse for `residual_threshold_sensitivity_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for the five new CSV
  assets.
- PNG existence/nonempty and image-open check for
  `residual_threshold_sensitivity.png`.
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.
