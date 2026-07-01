# Goal 027 Log: C-HI Conditional Endpoint Topology Application

## Start State

Date: 2026-07-01

Working directory:

`/Users/bwbrook/papers/xray_cavities`

Git state at start:

```text
branch: main
HEAD: 5784441
status: ## main...origin/main
```

Repo-local `AGENTS.md` was read first. `git pull --ff-only` reported the repo
was already up to date. The work stayed inside
`/Users/bwbrook/papers/xray_cavities`.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_residual_threshold_sensitivity_review_2026-07-01.md`
- `docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/`
- `docs/goals/026-c-hi-residual-threshold-sensitivity-review/Log.md`
- `scripts/science/build_residual_threshold_sensitivity_review.py`
- `docs/science/c_hi_existing_asset_topology_application_design_2026-07-01.md`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/`
- Goal 024 helper/tests for classification provenance.
- Goal 005 endpoint science note/assets for accepted endpoint provenance and
  pV/2.5pV/4pV context.
- Goal 007 observational-product readiness note/assets for topology-context
  provenance.

## TDD Record

Red phase:

```text
uv run pytest tests/test_conditional_endpoint_topology_application.py -q
2 failed
```

The expected red failure was the absent Goal 027 builder module.

Green phase:

```text
uv run pytest tests/test_conditional_endpoint_topology_application.py -q
2 passed
```

The tests cover the selected 1 percent conditional application, supporting
0.5/2 percent narrow-threshold robustness, 3+ percent ambiguity bounds, and
the no-final-freeze application status.

## Work Performed

Added builder:

- `scripts/science/build_conditional_endpoint_topology_application.py`

Added tests:

- `tests/test_conditional_endpoint_topology_application.py`

Created science note:

- `docs/science/c_hi_conditional_endpoint_topology_application_2026-07-01.md`

Created asset bundle:

- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/conditional_topology_application_summary.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/selected_threshold_component_summary.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/threshold_sensitivity_carried_forward.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/accepted_product_relationship.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/caveat_register.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/conditional_endpoint_topology_application_metadata.json`

Created exchange log:

- `docs/exchange/logs/2026-07-01-c-hi-conditional-endpoint-topology-application.md`

Updated:

- `docs/exchange/current_status.md`

## Decision

Decision label:

`CONDITIONAL_CONNECTED_CORE_APPLICATION_NO_FINAL_FREEZE`

Selected application:

`1 percent residual-core mask`

Observed topology class:

`connected_envelope_single_system`

Final observational topology frozen:

`false`

Recommended next goal:

`conditional_topology_application_acceptance_review`

## Validation

Local validation passed:

- `uv run pytest tests/test_conditional_endpoint_topology_application.py tests/test_residual_threshold_sensitivity_review.py tests/test_hybrid_xray_cavity_topology.py -q`
- `uv run python scripts/science/build_conditional_endpoint_topology_application.py`
- `python3 -m json.tool docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/conditional_endpoint_topology_application_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for:
  - `conditional_topology_application_summary.csv`
  - `selected_threshold_component_summary.csv`
  - `threshold_sensitivity_carried_forward.csv`
  - `accepted_product_relationship.csv`
  - `caveat_register.csv`
  - `next_step_recommendation.csv`
- Referenced Goal 026 PNG exists and is nonempty.
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
