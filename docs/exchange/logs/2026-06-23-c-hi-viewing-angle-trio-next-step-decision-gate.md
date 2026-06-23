# C-HI Viewing-Angle Trio Next-Step Decision Gate

Date: 2026-06-23
Agent: `jet`
Goal: `013-c-hi-viewing-angle-trio-next-step-decision-gate`
Status: `complete_decision_packet`

## Summary

Created a docs/evidence/agent-comms decision packet after X-ray Cavities
accepted the completed final `C-HI` `0/45/90 deg` projection-sensitivity trio.

Headline recommendation:

```text
PROCEED WITH REVIEWED NEXT STEP, NOT BROAD BATCH
```

The next decision should be between:

1. X-ray topology/cavity-method refinement before more sampling; or
2. a tightly bounded `C-HI` source-age sampling plan with current caveats
   carried explicitly.

The Goal 012 `90 deg` corrected X-ray panel has visible vertical striping. This
is recorded as review-significant evidence, not hidden and not overstated as a
proven calculation error.

## Evidence Read

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/README.md`
- `agent_comms/AGENTS.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`
- Goal 005/011/012 logs, scoped to final/retrieval/acceptance sections
- Goal 011/012 viewing-angle CSV assets and Goal 012 trio/projection/energy
  tables
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- Goal 009/010 logs, scoped to Level 3 closeout and broadening-review context
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `docs/science/three_case_spec.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- Visual inspection of
  `docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/c_hi_final_90deg_viewing_angle_broadening.png`

## Files Created Or Updated

- `docs/science/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23.md`
- `docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/trio_evidence_summary.csv`
- `docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/next_step_decision_matrix.csv`
- `agent_comms/threads/2026-06-23-c-hi-viewing-angle-trio-next-step.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `docs/exchange/current_status.md`
- `docs/exchange/logs/2026-06-23-c-hi-viewing-angle-trio-next-step-decision-gate.md`
- `docs/goals/013-c-hi-viewing-angle-trio-next-step-decision-gate/Log.md`

## New Questions

- `Q-018` to `stas-agent`: choose the next science move after the completed
  trio: X-ray topology/cavity-method refinement, limited `C-HI` source-age
  sampling, gravitational Level 3 convention work, or hold.
- `Q-019` to `patrick-agent`: decide whether visible 90-degree striping and
  unresolved X-ray-fitted topology require method refinement before source-age
  sampling, or whether a caveated limited `C-HI` source-age probe is acceptable.

## Boundaries

No remote commands, Open OnDemand, SSH/SCP, PBS jobs, finalizers, Kunanyi
staging, PLUTO production, XRAiSE/PRAiSE/radio/cavity product regeneration,
source-age sweep, `C-LO`, `G-LO`, comparison-case processing, broad batch work,
document builds, commits, pushes, scientific-default changes, or external
human contact occurred.

## Validation

```text
git diff --check
<no output>

placeholder/unresolved-marker scan
<no matches>

CSV parse and expected-column checks
trio_evidence_summary.csv_rows=20 columns_ok=7
next_step_decision_matrix.csv_rows=6 columns_ok=8
```

No project tests were run because no executable helper code was introduced.
