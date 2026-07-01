# Goal 023 Log: C-HI X-ray/Cavity Topology Method Decision

## Start State

Date: 2026-07-01

Working directory:

`/Users/bwbrook/papers/xray_cavities`

Git state at start:

```text
branch: main
HEAD: 46f06f2
status: ## main...origin/main
```

Repo-local `AGENTS.md` was read first. The work stayed inside
`/Users/bwbrook/papers/xray_cavities`.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_late_age_axis_decision_gate_2026-07-01.md`
- `docs/science/assets/c_hi_late_age_axis_decision_gate_2026-07-01/`
- `docs/science/c_hi_bounded_age_axis_extension_2026-07-01.md`
- `docs/science/assets/c_hi_bounded_age_axis_extension_2026-07-01/`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
  as existing local evidence only; no `agent_comms` edits were made.
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`
- `docs/science/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24.md`
- `docs/science/c_hi_projection_bin_refinement_2026-06-24.md`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`

## Work Performed

Created the Goal 023 science decision note:

- `docs/science/c_hi_xray_cavity_topology_method_decision_2026-07-01.md`

Created the Goal 023 machine-readable asset bundle:

- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_evidence_register.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/method_option_matrix.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/go_no_go_criteria.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_method_decision_metadata.json`

Created this Goal log and the exchange log:

- `docs/goals/023-c-hi-xray-cavity-topology-method-decision/Log.md`
- `docs/exchange/logs/2026-07-01-c-hi-xray-cavity-topology-method-decision.md`

Updated:

- `docs/exchange/current_status.md`

## Decision

Decision label:

`TRACER_PROXY_OK_HYBRID_XRAY_TOPOLOGY_METHOD_NEXT`

Headline conclusion:

The current tracer-defined side ellipsoids are adequate as reproducible
prove-out/provenance proxies, but should not be frozen as the final
observational X-ray cavity topology method. The next recommended goal is a
local-only hybrid tracer-seeded, X-ray-constrained topology method design and
synthetic/local evidence gate.

## Validation

No helper code was added, so no project tests were required.

Local validation passed:

- `python3 -m json.tool docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_method_decision_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for:
  - `topology_evidence_register.csv` (`7` rows)
  - `method_option_matrix.csv` (`5` rows)
  - `go_no_go_criteria.csv` (`7` rows)
  - `next_step_recommendation.csv` (`4` rows)
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
