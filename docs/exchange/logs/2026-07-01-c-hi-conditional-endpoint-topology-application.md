# 2026-07-01 C-HI Conditional Endpoint Topology Application

## Summary

Goal 027 created a bounded local conditional endpoint topology application
package. The decision label is
`CONDITIONAL_CONNECTED_CORE_APPLICATION_NO_FINAL_FREEZE`.

The package selects the `1` percent residual-core mask as the representative
conditional connected-core application, carries Goal 026 threshold sensitivity
as first-class evidence, and states explicitly that final observational
endpoint topology is not frozen.

## Files

Science note:

- `docs/science/c_hi_conditional_endpoint_topology_application_2026-07-01.md`

Builder/tests:

- `scripts/science/build_conditional_endpoint_topology_application.py`
- `tests/test_conditional_endpoint_topology_application.py`

Asset bundle:

- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/conditional_topology_application_summary.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/selected_threshold_component_summary.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/threshold_sensitivity_carried_forward.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/accepted_product_relationship.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/caveat_register.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/conditional_endpoint_topology_application_metadata.json`

Goal log:

- `docs/goals/027-c-hi-conditional-endpoint-topology-application/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 026 science note/assets/log and builder.
- Goal 025 science note/assets/log and application-design result.
- Goal 024 helper/tests for classification provenance.
- Goal 005 endpoint science note/assets for accepted endpoint provenance and
  pV/2.5pV/4pV context.
- Goal 007 observational-product readiness note/assets for topology-context
  provenance.

## Result

Selected application:

```text
1 percent residual-core mask
```

Observed topology class:

```text
connected_envelope_single_system
```

The selected mask has one seeded component spanning both tracer-proxy side
labels, six significant unlabelled residual islands retained as caveats, and
the Goal 026 threshold sensitivity carried forward beside it.

## Boundary Confirmation

This was local-only. No remote commands, Open OnDemand, SSH/SCP, `qstat`,
Kunanyi staging, PBS jobs, finalizers, retrieval, HDF5/XRAiSE reruns, PLUTO,
PRAiSE, radio, cavity regeneration, endpoint rerun, source-age substitution,
`C-LO`, `G-LO`, comparison-case processing, early-age branch, broad source-age
sweep, publication-facing claims, scientific-default changes, commits, pushes,
cleanup, `agent_comms` edits, or accepted-asset overwrites occurred.

## Validation

Local validation passed:

- `uv run pytest tests/test_conditional_endpoint_topology_application.py tests/test_residual_threshold_sensitivity_review.py tests/test_hybrid_xray_cavity_topology.py -q`
- `uv run python scripts/science/build_conditional_endpoint_topology_application.py`
- JSON parse for `conditional_endpoint_topology_application_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for all six new CSV
  assets.
- Referenced Goal 026 PNG exists and is nonempty.
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.
