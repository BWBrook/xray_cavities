# Plan: Goal 010 C-HI Level 3 Broadening Decision Packet

## Intended Shape

Create a decision surface, not a data product:

```text
Goal 007 Patrick clearance
  + Goal 009 thermal/kinetic Level 3 closeout
  + gravitational blocker
  + Q-012/Q-013/Q-015 review history
  -> concise broadening decision matrix
  -> science note
  -> agent_comms request to Stas-agent and Patrick-agent
  -> next-goal recommendation
```

The packet should let collaborator agents answer whether the next goal may
broaden `C-HI` in a controlled way, or whether gravitational Level 3 must be
settled first.

## Likely Files

Create:

- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/broadening_decision_matrix.csv`
- optionally `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/level3_evidence_summary.csv`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `docs/exchange/logs/2026-06-18-c-hi-level3-broadening-decision-packet.md`

Modify, if useful:

- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `docs/exchange/current_status.md`
- `docs/goals/010-c-hi-level3-broadening-decision-packet/Log.md`

Avoid code changes and avoid generated science products.

## Work Plan

1. Record starting state in `Log.md`.
2. Read the Goal 010 packet and required context.
3. Extract decision-relevant facts from Goals 006-009 and `agent_comms`.
4. Draft the broadening decision matrix.
5. Write the concise science decision note.
6. Create the `agent_comms` thread with response shape and canonical links.
7. Add open questions for Stas-agent and Patrick-agent if useful.
8. Add an exchange log and compact current-status update.
9. Update `Log.md`.
10. Run docs/CSV validation gates.
11. Wake X-ray Cavities.

## Expected Recommendation

Recommended candidate branch:

```text
PROCEED WITH CHANGES
```

Rationale:

- Goal 009 appears to satisfy the thermal/kinetic part of Stas-agent's Level 3
  prerequisite.
- The gravitational component remains transparently blocked, so Stas-agent must
  decide whether that is a hold or an acceptable known gap for the first
  controlled broadening step.
- Patrick-agent has already accepted the Goal 007 X-ray product as adequate,
  while preserving topology and radio-observable caveats.

The likely next implementation goal, if reviewers agree, should be controlled
`C-HI` broadening as post-processing only, not new PLUTO production: probably a
small, auditable first pass over additional viewing angle(s) or a tightly
bounded source-age slice. The packet should not choose the exact broadening
implementation on behalf of reviewers unless the evidence makes the branch
obvious.

## Non-Goals

Do not start broadening. Do not create new observables. Do not submit remote
jobs. Do not solve gravitational energy. Do not frame this as manuscript work.
