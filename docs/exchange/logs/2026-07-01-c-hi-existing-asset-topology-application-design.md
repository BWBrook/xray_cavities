# 2026-07-01 C-HI Existing-Asset Topology Application Design

## Summary

Goal 025 created a local existing-asset topology application design package.
The decision label is `CONDITIONAL_LOCAL_APPLICATION_CONNECTED_CORE_NOT_FINAL`.

Existing Goal 005/007 compact arrays are sufficient for a deterministic
conditional residual-core application of the Goal 024 helper, but not enough
to make a final observational endpoint topology claim. The selected 1 percent
residual-core mask classifies as `connected_envelope_single_system`; broader
residual thresholds become mixed/ambiguous.

## Files

Science note:

- `docs/science/c_hi_existing_asset_topology_application_design_2026-07-01.md`

Builder/helper/tests:

- `scripts/science/build_existing_asset_topology_application_design.py`
- `scripts/science/hybrid_xray_cavity_topology.py`
- `tests/test_hybrid_xray_cavity_topology.py`

Asset bundle:

- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/input_asset_contract.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/side_seed_protocol.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/xray_mask_protocol.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/application_readiness_decision.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/topology_application_result.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/topology_component_summary.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/existing_asset_topology_application_metadata.json`

Goal log:

- `docs/goals/025-c-hi-existing-asset-topology-application-design/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 024 helper/tests/science note/assets/log.
- Goal 023 method-decision note/assets/log, especially go/no-go criteria.
- Goal 005 endpoint corrected X-ray, tracer max LOS, axes, cavity ellipse
  boundary, lobe/scalar tables, and metadata.
- Goal 007 observational-product readiness note/assets, especially topology
  readiness and residual-display metadata.
- Goal 014/015/016 projection-refinement context as guardrail.

## Result

Endpoint application was made as a conditional local residual-core probe:

- side seed: `tracer_max_los >= 5e-3`, split by `z_kpc` sign;
- X-ray mask: Goal 007-style 41-pixel boxcar unsharp residual, selected at
  the 1st percentile;
- selected result: `connected_envelope_single_system`;
- final observational topology claim: `false`.

Threshold sensitivity prevents a final topology freeze from this goal: 1-2%
residual cores classify as connected-envelope, while 5/10/20% masks become
`ambiguous_needs_review`.

## Boundary Confirmation

This was local-only. No remote commands, Open OnDemand, SSH/SCP, `qstat`,
Kunanyi staging, PBS jobs, finalizers, retrieval, HDF5/XRAiSE reruns, PLUTO,
PRAiSE, radio, cavity regeneration, endpoint rerun, source-age substitution,
`C-LO`, `G-LO`, comparison-case processing, early-age branch, broad source-age
sweep, publication-facing claims, scientific-default changes, commits, pushes,
cleanup, `agent_comms` edits, or accepted-asset overwrites occurred.

## Validation

Local validation passed:

- `uv run pytest tests/test_hybrid_xray_cavity_topology.py -q`
  (`9 passed`)
- `uv run python scripts/science/build_existing_asset_topology_application_design.py`
- JSON parse for `existing_asset_topology_application_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for all seven new CSV
  assets.
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.
