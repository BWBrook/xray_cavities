# C-HI Viewing-Angle Trio Next-Step Decision Gate

Date: 2026-06-23

## Summary

Goal 013 is a docs/evidence/agent-comms decision gate after the accepted final
`C-HI` `0/45/90 deg` projection-sensitivity trio. It does not authorize a broad
batch, source-age sweep, comparison-case run, new observables, or
publication-ready claim.

Recommended decision stance:

```text
PROCEED WITH REVIEWED NEXT STEP, NOT BROAD BATCH
```

The next useful move is a reviewer decision between two narrow branches:

1. refine or decide the X-ray topology/cavity-measurement method before more
   sampling; or
2. begin a tightly bounded `C-HI` source-age sampling plan while carrying the
   current topology, radio, and Level 3 gravity caveats.

The new review-significant fact from Goal 012 is that the `90 deg` corrected
X-ray panel has visible vertical striping. This packet treats that as evidence
to review, not as proof of a calculation error. It should not be hidden,
smoothed away in prose, or promoted into a blocker unless reviewers decide the
existing validation evidence is insufficient.

## Evidence Base

Accepted baseline and trio products:

- Goal 005 `0 deg` endpoint:
  `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- Goal 011 `45 deg` product:
  `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- Goal 012 `90 deg` product:
  `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`

Compact CSV assets for this decision gate:

```text
docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/trio_evidence_summary.csv
docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/next_step_decision_matrix.csv
```

Prior method/reviewer context:

- Goal 009 Level 3 closeout:
  `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- Goal 010 broadening decision packet:
  `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- Method review thread:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- Observational readiness thread:
  `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- Level 3 broadening decision thread:
  `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`

Project-scope context:

- `docs/science/three_case_spec.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`

## Trio Result

The final `C-HI` endpoint now has one accepted baseline view and two accepted
additional post-processing views, all holding run, endpoint, case, source age,
physical defaults, and product contracts fixed.

| Metric | `45/0` | `90/0` | `90/45` |
| --- | ---: | ---: | ---: |
| corrected X-ray max | `0.11475003428628802` | `0.16054725535740694` | `1.3991042038110435` |
| corrected X-ray pixel-sum diagnostic | `0.44636214774306926` | `0.6312514030682306` | `1.4142135623730925` |
| positive correction-ratio max | `0.9317941027785449` | `0.9482945230406944` | `1.017708225683063` |

Pixel sums are diagnostic map sums, not luminosity integrals.

The 90-degree product passed remote HDF5 preflight, X-ray validation, and
cavity validation, and remote stderr was zero bytes. The review figure still
shows visible vertical striping in the 90-degree corrected X-ray panel. The
decision question is whether that striping is an acceptable projection/display
feature for a caveated source-age probe, or whether it should trigger
X-ray/cavity-method refinement first.

## Carried Caveats

- Projection-sensitivity only; not publication-ready observables.
- X-ray topology remains a connected-envelope/single-lobe caveat pending a
  later X-ray-based cavity-fit method.
- Current cavity products use tracer-defined side ellipsoids and projected
  overlays, not fitted observational X-ray cavities.
- Sparse PRAiSE and particle-binned radio products remain diagnostics, not
  validated radio observables.
- Level 3 thermal/kinetic ambient energy is green for the accepted final
  endpoint, but gravitational Level 3 remains `blocked_missing_potential`.
- Future energy summaries should carry `pV`, adopted non-relativistic `2.5pV`,
  and literature-comparison `4pV`.

## Decision Alternatives

The machine-readable matrix is in:

```text
docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/next_step_decision_matrix.csv
```

Short-form reading:

| Option | Status | Recommendation |
| --- | --- | --- |
| X-ray topology/cavity-method refinement | `shortlist` | Strong next move if reviewers treat striping/topology as method-significant. |
| Limited `C-HI` source-age sampling | `conditional_next_step` | Viable only if reviewers accept current caveats for an age probe. |
| `C-LO`/`G-LO` or comparison-case preparation | `hold_for_later` | Too broad immediately after one-case projection sensitivity. |
| Radio-observable/raytracing readiness | `method_gap_not_next_default` | Important near-term method gap, but not automatic next broadening. |
| Gravitational Level 3 convention | `tracked_gap` | Keep visible; do not make it the default next goal unless Stas-agent requires it. |
| No-go/hold | `contingency` | Use only if reviewers identify a concrete blocker from the completed trio. |

## Questions For Review

New agent-comms thread:

```text
agent_comms/threads/2026-06-23-c-hi-viewing-angle-trio-next-step.md
```

New open questions:

- `Q-018` to `stas-agent`: after the completed `0/45/90 deg` trio, should the
  next science move be X-ray topology/cavity-method refinement, limited
  `C-HI` source-age sampling, gravitational Level 3 convention work, or hold?
- `Q-019` to `patrick-agent`: does the visible 90-degree X-ray striping and
  unresolved X-ray-fitted topology require method refinement before source-age
  sampling, or is a caveated limited `C-HI` source-age probe acceptable?

Requested response shape:

```text
Decision: X_RAY_METHOD_FIRST | LIMITED_C_HI_SOURCE_AGE | GRAVITY_METHOD_FIRST | HOLD
Required changes before the next goal:
- ...
Is the 90 deg striping a blocker? yes/no/conditional
Recommended next goal shape:
- ...
Notes for Barry/X-ray Cavities:
- ...
```

## Recommendation

Do not open a broad batch. The trio is useful, but it is not a permission slip
for source-age sweeps, `C-LO`, `G-LO`, comparison-case processing, radio
observable claims, or manuscript-facing language.

The next goal should be one of:

1. a bounded X-ray topology/cavity-method refinement packet that decides how to
   handle the connected-envelope interpretation, X-ray-fitted cavity protocol,
   and 90-degree striping; or
2. a tightly bounded `C-HI` source-age sampling plan that explicitly carries
   the existing topology, sparse-radio, Level 3 gravity, and striping caveats.

This packet leans slightly toward reviewer choice between those two rather than
choosing unilaterally. If Patrick-agent treats the 90-degree striping or
topology as method-blocking, choose X-ray/cavity-method refinement first. If
Patrick-agent and Stas-agent both accept the current caveats as sufficient,
choose a small `C-HI` source-age sampling goal next.

## Non-Claims

- No remote commands, Open OnDemand, SSH/SCP, PBS jobs, finalizers, or Kunanyi
  staging were used for this packet.
- No PLUTO production, XRAiSE/PRAiSE/radio/cavity product regeneration,
  source-age sweep, `C-LO`, `G-LO`, comparison-case processing, broad batch
  work, document build, project test, commit, push, or scientific-default
  change occurred.
- This packet does not contact external humans; it writes repo-local
  `agent_comms` review material only.
