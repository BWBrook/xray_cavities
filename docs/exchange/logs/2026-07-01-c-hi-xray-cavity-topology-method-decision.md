# 2026-07-01 C-HI X-ray/Cavity Topology Method Decision

## Summary

Goal 023 created a local-only X-ray/cavity topology and method decision package
after the accepted late-age axis gate. The decision label is
`TRACER_PROXY_OK_HYBRID_XRAY_TOPOLOGY_METHOD_NEXT`.

The package concludes that the current tracer-defined side ellipsoids remain
adequate as reproducible prove-out/provenance proxies, but should not be
frozen as the final observational X-ray cavity topology method. The next
recommended goal is a local-only hybrid tracer-seeded, X-ray-constrained
topology method design and synthetic/local evidence gate.

## Files

Science note:

- `docs/science/c_hi_xray_cavity_topology_method_decision_2026-07-01.md`

Asset bundle:

- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_evidence_register.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/method_option_matrix.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/go_no_go_criteria.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_method_decision_metadata.json`

Goal log:

- `docs/goals/023-c-hi-xray-cavity-topology-method-decision/Log.md`

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 022 decision note/assets/log.
- Goal 021 note/assets/log as late-age surface context.
- Goal 007 observational-product readiness note/thread and readiness assets as
  X-ray topology review context.
- Goal 005 endpoint X-ray/cavity alignment note/assets as current side-aware
  cavity proxy context.
- Goal 014/015/016/017 projection diagnostic, projection refinement, refined
  rerun, and consolidation notes/assets.
- Goal 006 method-review packet for `pV`, adopted `2.5pV`, and `4pV`
  convention context.
- Goal 009 Level 3 closeout for ambient-energy caveats.

## Boundary Confirmation

This was a local-only docs/evidence package. No remote commands, Open OnDemand,
SSH/SCP, `qstat`, Kunanyi staging, PBS jobs, finalizers, retrieval, HDF5/XRAiSE
reruns, PLUTO, PRAiSE, radio, cavity regeneration, endpoint rerun, source-age
substitution, `C-LO`, `G-LO`, comparison-case processing, early-age branch,
broad source-age sweep, publication-facing claims, scientific-default changes,
commits, pushes, cleanup, `agent_comms` edits, or accepted-asset overwrites
occurred.

## Validation

No helper code was added, so no project tests were required.

Local validation passed:

- `python3 -m json.tool docs/science/assets/c_hi_xray_cavity_topology_method_decision_2026-07-01/topology_method_decision_metadata.json`
- CSV parse, expected-column, and nonempty-row checks for all four new CSV
  assets.
- `git diff --check`
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and current status.
