# Goal 025 Log: C-HI Existing-Asset Topology Application Design

## Start State

Date: 2026-07-01

Working directory:

`/Users/bwbrook/papers/xray_cavities`

Git state at start:

```text
branch: main
HEAD: dd5b736
status: ## main...origin/main
```

Repo-local `AGENTS.md` was read first. The work stayed inside
`/Users/bwbrook/papers/xray_cavities`.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01.md`
- `docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/`
- `docs/goals/024-c-hi-hybrid-xray-cavity-topology-gate/Log.md`
- `scripts/science/hybrid_xray_cavity_topology.py`
- `tests/test_hybrid_xray_cavity_topology.py`
- `docs/science/c_hi_xray_cavity_topology_method_decision_2026-07-01.md`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/go_no_go_criteria.csv`
- Goal 005 endpoint assets:
  - corrected X-ray TSV
  - tracer max LOS TSV
  - `x_kpc.tsv`
  - `z_kpc.tsv`
  - cavity ellipse boundary TSV
  - lobe/scalar tables
  - metadata
- Goal 007 observational-product readiness note/assets, including topology
  readiness and residual-display metadata.
- Goal 014/015/016 projection-refinement context as guardrail.

## TDD Record

Red phase for the Goal 025 helper extension:

```text
uv run pytest tests/test_hybrid_xray_cavity_topology.py -q
3 failed, 5 passed
```

The expected red failures were missing direct-mask, tracer side-seed, and
boxcar-residual helper functions.

Second red phase:

```text
uv run pytest tests/test_hybrid_xray_cavity_topology.py -q
1 failed, 8 passed
```

The expected red failure was the missing seeded-only direct-mask option for
ignoring unlabelled residual islands during tracer-seeded topology
classification.

Green phase:

```text
uv run pytest tests/test_hybrid_xray_cavity_topology.py -q
9 passed
```

## Work Performed

Extended:

- `scripts/science/hybrid_xray_cavity_topology.py`
- `tests/test_hybrid_xray_cavity_topology.py`

Added builder:

- `scripts/science/build_existing_asset_topology_application_design.py`

Created science note:

- `docs/science/c_hi_existing_asset_topology_application_design_2026-07-01.md`

Created asset bundle:

- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/input_asset_contract.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/side_seed_protocol.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/xray_mask_protocol.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/application_readiness_decision.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/topology_application_result.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/topology_component_summary.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/existing_asset_topology_application_metadata.json`

Created exchange log:

- `docs/exchange/logs/2026-07-01-c-hi-existing-asset-topology-application-design.md`

Updated:

- `docs/exchange/current_status.md`

## Decision

Decision label:

`CONDITIONAL_LOCAL_APPLICATION_CONNECTED_CORE_NOT_FINAL`

Endpoint application status:

`conditional_local_application_made_not_final_topology`

Headline result:

Existing Goal 005/007 compact assets support a deterministic conditional
residual-core application. The selected 1 percent residual-core mask classifies
as `connected_envelope_single_system`, but broader threshold sensitivity
becomes mixed/ambiguous. This is not a final endpoint topology claim.

Recommended next goal:

`local_residual_threshold_sensitivity_review_package`

## Validation

Local validation passed:

- `uv run pytest tests/test_hybrid_xray_cavity_topology.py -q`
  (`9 passed`)
- `uv run python scripts/science/build_existing_asset_topology_application_design.py`
- `python3 -m json.tool docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/existing_asset_topology_application_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for:
  - `input_asset_contract.csv` (`8` rows)
  - `side_seed_protocol.csv` (`2` rows)
  - `xray_mask_protocol.csv` (`5` rows)
  - `application_readiness_decision.csv` (`1` row)
  - `topology_application_result.csv` (`5` rows)
  - `topology_component_summary.csv` (`7` rows)
  - `next_step_recommendation.csv` (`3` rows)
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
