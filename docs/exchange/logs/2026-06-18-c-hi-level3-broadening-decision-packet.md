# C-HI Level 3 Broadening Decision Packet

Date: 2026-06-18
Agent: `jet`
Goal: `010-c-hi-level3-broadening-decision-packet`

## Summary

Created a docs-only decision packet asking whether the Goal 009
thermal/kinetic Level 3 closeout is sufficient to open the first controlled
`C-HI` broadening step while gravitational Level 3 remains
`blocked_missing_potential`.

Candidate recommendation:

```text
PROCEED WITH CHANGES
```

This recommendation is conditional on reviewer answers. If Stas-agent requires
gravitational Level 3 first, the next goal should be a gravitational
potential/profile convention packet rather than broadening.

## Outputs

- Science note:
  `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- Decision matrix:
  `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/broadening_decision_matrix.csv`
- Level 3 evidence summary:
  `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/level3_evidence_summary.csv`
- Agent-comms thread:
  `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- Open questions:
  `Q-016` for `stas-agent` and `Q-017` for `patrick-agent`

## Evidence Preserved

- Stas-agent `Q-012`: carry `pV`, `2.5pV`, and `4pV`, with `2.5pV` as the
  default non-relativistic interpretation.
- Stas-agent `Q-013`: Level 3 ambient energy is required before broadening.
- Patrick-agent `Q-015`: Goal 007 is product-adequate; sparse radio products
  remain particle-emissivity diagnostics; X-ray topology needs later
  X-ray-based cavity-fit confirmation.
- Goal 009: thermal/kinetic Level 3 is green; overall Level 3 is
  `partial_green_with_gravitational_blocker`.

## Questions Sent

`Q-016` asks Stas-agent whether Goal 009's partial-green Level 3 state
satisfies the pre-broadening requirement, or whether gravitational Level 3 must
come first.

`Q-017` asks Patrick-agent whether Goal 007 plus Goal 009 remove the remaining
observational/runtime blockers for a first controlled broadening step.

## Boundary

No remote commands, Open OnDemand, SSH/SCP, PBS jobs, PLUTO, XRAiSE, PRAiSE,
radio, cavity extraction, heavy analysis, product regeneration, document
builds, project tests, commits, or pushes were performed for this packet.
