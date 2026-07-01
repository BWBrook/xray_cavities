# 2026-07-01 C-HI Hybrid X-ray/Cavity Topology Gate

## Summary

Goal 024 implemented a local hybrid tracer-seeded, X-ray-constrained topology
helper and tested it on synthetic/local fixtures. The decision label is
`HYBRID_TOPOLOGY_SYNTHETIC_GATE_PASSED_LOCAL_APPLICATION_PROTOCOL_NEXT`.

The helper explicitly separates tracer-proxy side labels from X-ray topology
class. Synthetic cases show the method can distinguish
`two_separate_cavities` from `connected_envelope_single_system` and can fail an
ambiguous unsupported case as `ambiguous_needs_review`.

## Files

Science note:

- `docs/science/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01.md`

Helper and tests:

- `scripts/science/hybrid_xray_cavity_topology.py`
- `tests/test_hybrid_xray_cavity_topology.py`

Asset bundle:

- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/synthetic_topology_cases.csv`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/topology_gate_results.csv`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/method_parameters.csv`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/accepted_asset_application_readiness.csv`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/hybrid_topology_gate_metadata.json`

Goal log:

- `docs/goals/024-c-hi-hybrid-xray-cavity-topology-gate/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 023 science note/assets/log, especially `method_option_matrix.csv` and
  `go_no_go_criteria.csv`.
- Goal 005 endpoint X-ray/cavity alignment note/assets.
- Goal 007 observational-product readiness note/assets.
- Goals 014/015/016 projection diagnostic/refinement/rerun notes/assets.
- Goal 006 method-review context and Goal 009 Level 3 closeout context for
  caveat preservation.

## Result

The synthetic/local gate passes. Existing compact Goal 005/007 assets are
available but only partially sufficient for a real endpoint application,
because Goal 024 still lacks a deterministic side-seed derivation table and a
parseable X-ray residual/topology layer. The recommended next goal is local
existing-asset application design, not a rerun.

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
  (`5 passed`)
- `python3 scripts/science/hybrid_xray_cavity_topology.py`
- JSON parse for `hybrid_topology_gate_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for all five new CSV
  assets.
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.
