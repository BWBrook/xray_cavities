# Goal 026 Log: C-HI Residual-Threshold Sensitivity Review

## Start State

Date: 2026-07-01

Working directory:

`/Users/bwbrook/papers/xray_cavities`

Git state at start:

```text
branch: main
HEAD: f64b91b
status: ## main...origin/main
```

Repo-local `AGENTS.md` was read first. `git pull --ff-only` reported the repo
was already up to date. The work stayed inside
`/Users/bwbrook/papers/xray_cavities`.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_existing_asset_topology_application_design_2026-07-01.md`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/`
- `docs/goals/025-c-hi-existing-asset-topology-application-design/Log.md`
- `scripts/science/build_existing_asset_topology_application_design.py`
- `scripts/science/hybrid_xray_cavity_topology.py`
- `tests/test_hybrid_xray_cavity_topology.py`
- Goal 005 endpoint compact assets:
  - corrected X-ray TSV
  - tracer max LOS TSV
  - `x_kpc.tsv`
  - `z_kpc.tsv`
- Goal 007 observational-product readiness metadata/topology context.

## TDD Record

Red phase:

```text
uv run pytest tests/test_residual_threshold_sensitivity_review.py -q
2 failed
```

The expected red failure was the absent Goal 026 builder module.

Green phase:

```text
uv run pytest tests/test_residual_threshold_sensitivity_review.py -q
2 passed
```

The focused tests cover a synthetic residual threshold transition from a
connected core to an ambiguous broader mask, unlabelled residual-island
reporting, and the conditional-not-final recommendation label.

## Work Performed

Added builder:

- `scripts/science/build_residual_threshold_sensitivity_review.py`

Added tests:

- `tests/test_residual_threshold_sensitivity_review.py`

Created science note:

- `docs/science/c_hi_residual_threshold_sensitivity_review_2026-07-01.md`

Created asset bundle:

- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_component_sensitivity.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/mask_seed_overlap_summary.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/figure_provenance.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity_metadata.json`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.png`

Created exchange log:

- `docs/exchange/logs/2026-07-01-c-hi-residual-threshold-sensitivity-review.md`

Updated:

- `docs/exchange/current_status.md`

## Decision

Decision label:

`CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL`

Headline result:

The `0.5`, `1`, and `2` percent residual-core masks classify as
`connected_envelope_single_system`. The `3`, `5`, `10`, and `20` percent masks
classify as `ambiguous_needs_review` because broader masks mix the connected
core with side-specific seeded components and unlabelled residual islands.

Recommended next goal:

`bounded_conditional_endpoint_topology_application_package`

This supports a later bounded no-overwrite conditional application package,
not a final endpoint topology freeze.

## Validation

Local validation passed:

- `uv run pytest tests/test_residual_threshold_sensitivity_review.py tests/test_hybrid_xray_cavity_topology.py -q`
- `uv run python scripts/science/build_residual_threshold_sensitivity_review.py`
- `python3 -m json.tool docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for:
  - `residual_threshold_sensitivity.csv`
  - `residual_component_sensitivity.csv`
  - `mask_seed_overlap_summary.csv`
  - `figure_provenance.csv`
  - `next_step_recommendation.csv`
- PNG existence/nonempty and image-open check for:
  - `residual_threshold_sensitivity.png`
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.

## Boundary Confirmation

No remote commands, Open OnDemand, SSH/SCP, `qstat`, Kunanyi staging, PBS jobs,
finalizers, retrieval, HDF5/XRAiSE reruns, PLUTO, PRAiSE, radio, cavity
regeneration, endpoint rerun, source-age substitution, `C-LO`, `G-LO`,
comparison-case processing, early-age branch, broad source-age sweep,
publication-facing claims, scientific-default changes, commits, pushes,
cleanup, `agent_comms` edits, or accepted-asset overwrites occurred.
