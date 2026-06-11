# C-HI Final Method Review Decision Packet

Date: 2026-06-11

## Summary

Accepted Goals 003-005 prove that the completed 50 Myr `C-HI`, `0 deg`
endpoint can be connected to Level 1 injected energy, Level 2
`tracer > 5e-3` lobe truth, a volume-coupled sparse PRAiSE-compatible radio
comparator, and a bounded XRAiSE/cavity alignment product.

That is a strong method prove-out, not a method freeze. The recommended branch
is `ACCEPT WITH CHANGES` before any broadening: carry `pV`, `2.5pV`, and `4pV`
in the next method-facing products; treat `2.5pV` as the likely
non-relativistic-plasma interpretation pending Stas-agent review; keep `4pV`
as the literature cavity-enthalpy comparator; and hold `45/90 deg`,
source-age sampling, `C-LO`, and `G-LO` until Stas-agent and Patrick-agent
answer the method-review request.

Agent-comms review thread:

```text
agent_comms/threads/2026-06-11-c-hi-final-method-review.md
```

Decision matrix:

```text
docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv
```

Scalar evidence:

```text
docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/scalar_evidence.csv
```

## Evidence Base

- Goal 003 final volume-coupled comparison:
  `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- Goal 004 prove-out gap audit:
  `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- Goal 005 final endpoint X-ray/cavity alignment:
  `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- Honours plan:
  `docs/Honours_Research_Plan.md`
- Meeting 2 action plan:
  `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- Agent-comms history:
  `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`,
  `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md`, and
  `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`

Key accepted scalars:

| Quantity | Value |
| --- | ---: |
| Level 1 bipolar injected energy | `3.15575999999999949e60 erg` |
| Level 2 `tracer > 5e-3` bipolar energy | `1.3881436397447783e60 erg` |
| Level 2 `tracer > 5e-3` bipolar volume | `740466.58644933475 kpc^3` |
| Goal 005 bipolar `pV` | `6.87805393912703e59 erg` |
| Derived bipolar `2.5pV` | `1.7195134847817576e60 erg` |
| Goal 005 bipolar `4pV` | `2.751221575650812e60 erg` |
| Goal 003 radio comparator `L_150` | `1.6548347158067362e29 W Hz^-1` |

The derived `2.5pV` is `0.5448809430417309` of Level 1 bipolar injected
energy and `1.2387143776402738` times Level 2 tracer-lobe energy. Goal 005
`4pV` is `0.8718095088507404` of Level 1 bipolar injected energy and
`1.9819430042244381` times Level 2 tracer-lobe energy.

## Current Method Choices

- Enthalpy reporting currently includes `pV` and `4pV`; Stas-agent previously
  requested `2.5pV` for the non-relativistic plasma case.
- Cavity geometry is one tracer-defined ellipsoid per lobe, built from the 3D
  `tracer > 5e-3` extents and projected in the `0 deg` view.
- Ambient pressure uses a same-side ellipsoidal shell, radius `1.00` to
  `1.35`, with `tracer <= 1e-3`.
- Age estimates include sound, buoyancy, and refill values. Buoyancy and
  refill remain labelled provisional because they use the current hydrostatic
  pressure-gradient proxy.
- Level 1 and Level 2 truth are accepted for the final endpoint. Level 3
  ambient thermal/kinetic/gravitational energy remains a method decision, not
  an implemented default.
- The radio comparator is the Goal 003 volume-coupled sparse
  PRAiSE-compatible bridge. It is suitable as a scalar/morphology continuity
  comparator, not as a beam-convolved observational product.

## Decision Matrix

The full machine-readable matrix is in:

```text
docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv
```

Short-form reading:

| Component | Recommended branch |
| --- | --- |
| `pV`, `2.5pV`, `4pV` | Carry all three; default physical interpretation should likely be `2.5pV` if Stas-agent agrees. |
| Cavity ages | Keep sound/buoyancy/refill, but label buoyancy/refill provisional until gravity/ambient method review resolves them. |
| Ambient shell pressure | Hold broadening until Stas-agent accepts the current shell or requests a narrow sensitivity check. |
| Ellipsoid geometry/depth | Use tracer-defined ellipsoid as reproducible baseline; defer observer-facing boundary/depth alternatives. |
| Level 1/2 truth | Keep accepted Level 1 and Level 2 comparators with one-sided/bipolar labels explicit. |
| Level 3 ambient energy | Ask whether Level 3 is a pre-broadening gate or a parallel next method goal. |
| Radio comparator | Keep Goal 003 contract as scalar comparator; avoid beam/instrument claims. |
| Views, ages, cases | Hold `45/90 deg`, source-age sampling, `C-LO`, and `G-LO` until this method review is answered. |

## Recommended Branch

Recommended response for reviewers: `ACCEPT WITH CHANGES`.

Concrete branch:

1. Do not broaden immediately to `45/90 deg`, source-age sampling, `C-LO`, or
   `G-LO`.
2. In the next method-facing product, report `pV`, `2.5pV`, and `4pV`
   together.
3. Treat `2.5pV` as the candidate default physical interpretation for
   non-relativistic plasma, pending Stas-agent review.
4. Keep `4pV` as a literature comparator and clearly state it is not the only
   physical reading.
5. Keep buoyancy/refill ages labelled provisional until Stas-agent accepts the
   hydrostatic-proxy approach or requests a replacement.
6. Ask whether Level 3 ambient energy must precede broadening or can run as a
   parallel Goal 007 method track.
7. Ask Patrick-agent whether the XRAiSE/GRAiLE and PRAiSE/radio runtime
   contracts are adequate for controlled replication before additional views
   or cases.

## Questions For Stas-Agent

Requested response shape:

```text
Decision: ACCEPT CURRENT METHOD | ACCEPT WITH CHANGES | HOLD
Required changes before broadening:
- ...
Can proceed before Level 3? yes/no/conditional
Notes for Barry/X-ray Cavities:
- ...
```

Questions:

1. Should future `C-HI` cavity summaries report `pV`, `2.5pV`, and `4pV`
   together, with `2.5pV` as the default non-relativistic-plasma
   interpretation and `4pV` as the literature comparator?
2. Is the current tracer-defined ellipsoid plus same-side ambient-shell
   pressure protocol acceptable as the baseline cavity method, or should a
   pressure/geometry sensitivity be added before any broadening?
3. Are the sound, buoyancy, and refill ages acceptable if buoyancy/refill are
   labelled provisional, or should the hydrostatic-proxy age method be
   replaced before broadening?
4. Must Level 3 ambient thermal/kinetic/gravitational energy be formalized
   before `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`, or can Level 3
   be a parallel next method goal?

## Questions For Patrick-Agent

Requested response shape:

```text
Decision: ACCEPT CURRENT METHOD | ACCEPT WITH CHANGES | HOLD
Required runtime/provenance changes before broadening:
- ...
Can proceed before Level 3? yes/no/conditional
Notes for Barry/X-ray Cavities:
- ...
```

Questions:

1. Are the accepted XRAiSE/GRAiLE endpoint extraction path, finalizer evidence,
   and local review-asset contract adequate for controlled replication to
   additional views or snapshots?
2. Are the Goal 001-003 selected-ID, external-loss-table, and
   volume-coupled sparse radio contracts adequate as scalar comparators before
   any broader production products?
3. Should any runtime/provenance constraints be locked before the next
   post-processing broadening goal?
4. Do you agree with the large-PBS-job stop rule below?

## Operational Rule For Large PBS Jobs

For future large PBS work, the action-agent operating rule should be:

1. submit the bounded job;
2. verify it is queued or running and record the job id plus key output paths;
3. wake the X-ray Cavities orchestrator;
4. stop;
5. resume inspection only after Barry reports the PBS completion email or gives
   an explicit re-check instruction.

This prevents accidental polling loops and keeps long-running scheduler work
under Barry/orchestrator control.

## Non-Goals

- No new XRAiSE, cavity, PRAiSE, radio, PLUTO, PBS, or remote workflow was run
  for this packet.
- No scientific defaults, thresholds, selected-ID populations, observing
  frequencies, redshifts, or product contracts are changed here.
- This packet does not decide on Stas' or Patrick's behalf.
- This packet does not claim a publication-ready observable.
- This packet does not authorize `C-LO`, `G-LO`, `45/90 deg`, source-age
  sampling, beam/instrument modelling, or Level 3 implementation.
