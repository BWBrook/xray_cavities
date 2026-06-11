# 2026-06-11 C-HI Final Method Review Decision Packet

## Why This Packet Was Opened

Goal 005 accepted a bounded final 50 Myr `C-HI`, `0 deg` X-ray/cavity
alignment gate as green. That proves the mechanics of the final endpoint
alignment path, but it does not freeze the method for broader views, source-age
sampling, or comparison cases.

Goal 006 therefore creates a decision packet for Barry, Stas-agent, and
Patrick-agent before any broadening.

## Evidence Read

- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`
- `agent_comms/threads/2026-05-11-production-scale-allocation.md`
- `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md`
- `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- accepted Goal 003-005 logs

## Deliverables

- Decision note:
  `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- Decision matrix:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv`
- Scalar evidence:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/scalar_evidence.csv`
- Agent-comms review thread:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- Open-question queue updates:
  `agent_comms/requests/open_questions.md`

## Headline Recommendation

Recommended branch: `ACCEPT WITH CHANGES` before broadening.

The packet recommends carrying `pV`, `2.5pV`, and `4pV`; treating `2.5pV` as
the likely non-relativistic-plasma interpretation pending Stas-agent review;
preserving `4pV` as the literature comparator; and holding `45/90 deg`,
source-age sampling, `C-LO`, and `G-LO` until Stas-agent and Patrick-agent
answer the method-review request.

The packet also asks whether Level 3 ambient-energy method work is a required
pre-broadening gate or can proceed in parallel.

## Agent-Comms Requests

Open questions added:

- `Q-012` to `stas-agent`: enthalpy convention and `2.5pV` default.
- `Q-013` to `stas-agent`: Level 3 ambient-energy timing.
- `Q-014` to `patrick-agent`: XRAiSE/GRAiLE and sparse PRAiSE/radio runtime
  contracts before controlled replication.

## Validation

Validation commands are recorded in the Goal 006 log:

```text
git diff --check
unresolved-marker search over the decision note, exchange log, agent-comms
thread, current status, and open-question queue
uv run python <CSV parse check>
```

This was a docs/decision and agent-comms-only goal. No remote commands, PBS
jobs, data workflows, regenerated products, scientific-default changes,
commits, or pushes occurred.
