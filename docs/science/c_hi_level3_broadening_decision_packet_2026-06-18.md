# C-HI Level 3 Broadening Decision Packet

Date: 2026-06-18

## Summary

Goal 010 asks whether the accepted Goal 009 thermal/kinetic Level 3 closeout is
enough to open the first controlled `C-HI` broadening step while gravitational
Level 3 remains `blocked_missing_potential`.

Candidate recommendation for reviewers:

```text
PROCEED WITH CHANGES
```

This is not a permission slip for broadening. It is a decision packet for
Stas-agent, Patrick-agent, and X-ray Cavities. The core branch is: proceed only
if Stas-agent agrees that `partial_green_with_gravitational_blocker` satisfies
the `Q-013` Level 3 prerequisite for the first controlled step, and if
Patrick-agent agrees that the Goal 007 product clearance plus Goal 009 Level 3
evidence leave no remaining observational/runtime hold.

Agent-comms thread:

```text
agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md
```

Decision matrix:

```text
docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/broadening_decision_matrix.csv
```

Level 3 evidence summary:

```text
docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/level3_evidence_summary.csv
```

## Evidence Base

- Stas-agent `Q-012`: future summaries should carry `pV`, `2.5pV`, and `4pV`,
  with `2.5pV` as the default non-relativistic interpretation and `4pV` as the
  literature comparison.
- Stas-agent `Q-013`: Level 3 ambient energy must be completed before
  broadening to `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`.
- Patrick-agent `Q-015`: Goal 007 is product-adequate; no further X-ray
  visual-context changes are required before broadening; topology is visually a
  connected envelope or single lobe pending later X-ray-based cavity-fit
  confirmation; sparse radio products remain particle-emissivity diagnostics.
- Goal 009: thermal and kinetic Level 3 are green for the accepted final 50 Myr
  `C-HI`, `0 deg` endpoint, and gravitational Level 3 remains blocked by
  missing potential/profile convention.
- The Honours plan and Meeting 2 action plan support viewing angle and
  source-age broadening as post-processing axes only after the baseline method
  and review gates are locked.

## Goal 009 Level 3 Result

Goal 009 status:

```text
thermal/kinetic: green_level3_thermal_kinetic_closeout
overall: partial_green_with_gravitational_blocker
gravitational: blocked_missing_potential
```

Headline bipolar values:

| Quantity | Value |
| --- | ---: |
| Ambient thermal delta | `2.259405474647962e60 erg` |
| Ambient kinetic delta | `5.422582705702232e59 erg` |
| Ambient thermal plus kinetic delta | `2.8016637452181852e60 erg` |
| Ratio to Level 1 bipolar injected energy | `0.887793667838551` |
| Ratio to Level 2 tracer-lobe energy | `2.018280864459599` |
| Ratio to adopted `2.5pV` | `1.6293351404416438` |
| Ratio to literature-comparison `4pV` | `1.0183344627760273` |

The coordinate-compatibility contract executed inside the remote extractor
before streaming subtraction. The gravitational component was not computed and
should not be inferred.

## Decision Matrix

The machine-readable matrix is in:

```text
docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/broadening_decision_matrix.csv
```

Short-form reading:

| Component | Decision needed | Candidate branch |
| --- | --- | --- |
| `Q-012` enthalpy convention | Keep `pV`, `2.5pV`, and `4pV`; use `2.5pV` as default non-relativistic interpretation. | `PROCEED WITH CHANGES` |
| `Q-013` Level 3 prerequisite | Decide if thermal+kinetic Level 3 is enough while gravity is blocked. | `PROCEED WITH CHANGES` if Stas-agent agrees |
| Patrick-agent `Q-015` | Confirm no observational/runtime hold remains before the first controlled step. | `PROCEED WITH CHANGES` |
| Goal 009 values | Accept the thermal/kinetic closeout as reviewable. | `PROCEED WITH CHANGES` |
| Gravitational blocker | Decide whether gravity-first convention is mandatory. | `HOLD IF REQUIRED` |
| X-ray topology | Preserve connected-envelope caveat and avoid X-ray-fitted cavity claims. | `PROCEED WITH CHANGES` |
| Radio observables | Keep sparse products labelled as particle-emissivity diagnostics. | `PROCEED WITH CHANGES` |
| First broadening target | Choose one narrow post-processing-only `C-HI` target if not held. | `PROCEED WITH CHANGES` |
| PBS guardrail | Carry the submit, verify, wake, stop rule into future large jobs. | `PROCEED WITH CHANGES` |

## Questions For Stas-Agent

Requested response shape:

```text
Decision: PROCEED TO CONTROLLED BROADENING | PROCEED WITH CHANGES | HOLD
Required changes before broadening:
- State required changes, or `none`.
Gravity convention required first? yes/no/conditional
Recommended first broadening target:
- State the first narrow target, or `hold`.
Notes for Barry/X-ray Cavities:
- State any caveats or review priorities.
```

Specific question:

```text
Does Goal 009's thermal+kinetic Level 3 closeout, with overall status
partial_green_with_gravitational_blocker, satisfy Q-013 for the first
controlled C-HI broadening step, or must a gravitational potential/profile
convention be defined before any broadening?
```

## Questions For Patrick-Agent

Requested response shape:

```text
Decision: PROCEED TO CONTROLLED BROADENING | PROCEED WITH CHANGES | HOLD
Required changes before broadening:
- State required changes, or `none`.
Gravity convention required first? yes/no/conditional
Recommended first broadening target:
- State the first narrow target, or `hold`.
Notes for Barry/X-ray Cavities:
- State any caveats or review priorities.
```

Specific question:

```text
Do Goal 007's accepted observational-product package plus Goal 009's
thermal/kinetic Level 3 closeout remove the remaining pre-broadening blockers
from the observational/runtime side, provided the next goal preserves topology
and radio-observable caveats?
```

## Candidate Next Goal Shape

If Stas-agent and Patrick-agent answer `PROCEED TO CONTROLLED BROADENING` or
`PROCEED WITH CHANGES`, the next goal should be a small, auditable
post-processing-only `C-HI` broadening step. It should choose one first narrow
target, preserve all accepted thresholds and product contracts, keep sparse
radio products labelled as diagnostics, and carry the large-PBS-job stop rule.

If Stas-agent answers that gravitational Level 3 is required first, the next
goal should be a gravitational potential/profile convention packet, not
broadening.

## Non-Claims

- This packet does not broaden to `45/90 deg`, source-age sampling, `C-LO`, or
  `G-LO`.
- This packet does not run remote commands, PBS jobs, PLUTO, XRAiSE, PRAiSE,
  radio, cavity extraction, product regeneration, or project tests.
- This packet does not define gravitational Level 3.
- This packet does not change scientific defaults, thresholds, unit
  conversions, selected IDs, or accepted product contracts.
- This packet does not claim a final publication-ready observable product.
