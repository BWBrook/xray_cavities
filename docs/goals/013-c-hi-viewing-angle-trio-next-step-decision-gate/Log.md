# Log: Goal 013 C-HI Viewing-Angle Trio Next-Step Decision Gate

## 2026-06-23 - start state

Start state:

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
8ae40b0

git fetch --prune origin
<no output>

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
8ae40b0
```

Repo-local `AGENTS.md` was read before project work. The worktree was clean at
start and no fast-forward was needed.

## 2026-06-23 - evidence read

Read scoped, repo-local evidence:

- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/README.md`
- `agent_comms/AGENTS.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
  final/acceptance sections
- `docs/goals/011-c-hi-final-45deg-viewing-angle-broadening/Log.md`
  submission/completion sections
- `docs/goals/012-c-hi-final-90deg-viewing-angle-broadening/Log.md`
  completion package sections
- Goal 011 and Goal 012 compact CSV assets:
  `viewing_angle_comparison.csv`,
  `viewing_angle_trio_comparison.csv`, `projection_metrics.csv`, and
  `cavity_energy_convention.csv`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- Goal 009 and Goal 010 log sections sufficient to preserve Level 3 and
  reviewer-decision context
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `docs/science/three_case_spec.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- visual inspection of
  `docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/c_hi_final_90deg_viewing_angle_broadening.png`

Key evidence:

- Goal 005 accepted the final `C-HI`, `0 deg` X-ray/cavity alignment gate as
  green but not publication-ready.
- Goal 011 accepted the `45 deg` projection-sensitivity product with corrected
  X-ray max `45/0 = 0.11475003428628802` and corrected X-ray pixel-sum
  diagnostic `45/0 = 0.44636214774306926`.
- Goal 012 accepted the `90 deg` product and completed the `0/45/90 deg` trio,
  with corrected X-ray max `90/0 = 0.16054725535740694`,
  `90/45 = 1.3991042038110435`, corrected X-ray pixel-sum diagnostic
  `90/0 = 0.6312514030682306`, and `90/45 = 1.4142135623730925`.
- The `90 deg` corrected X-ray panel visibly has vertical striping. The packet
  treats this as review-significant evidence, not as a proven calculation
  defect.
- Goal 009 thermal/kinetic Level 3 is green, with overall status
  `partial_green_with_gravitational_blocker`; gravitational Level 3 remains
  `blocked_missing_potential`.
- Stas-agent `Q-016` allowed controlled broadening without first resolving the
  gravity convention, while preserving updated energy calculations.
- Patrick-agent `Q-017` allowed one narrow `C-HI` post-processing broadening
  step from the observational/runtime side, preserving topology,
  radio-observable, and large-PBS stop-rule caveats.

## 2026-06-23 - packet created

Created:

- `docs/science/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23.md`
- `docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/trio_evidence_summary.csv`
- `docs/science/assets/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23/next_step_decision_matrix.csv`
- `agent_comms/threads/2026-06-23-c-hi-viewing-angle-trio-next-step.md`
- `docs/exchange/logs/2026-06-23-c-hi-viewing-angle-trio-next-step-decision-gate.md`
- this Goal 013 log

Updated:

- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `docs/exchange/current_status.md`

Headline recommendation:

```text
PROCEED WITH REVIEWED NEXT STEP, NOT BROAD BATCH
```

Decision alternatives compared:

- X-ray topology/cavity-method refinement before more sampling;
- limited `C-HI` source-age sampling only;
- comparison-case preparation for `C-LO`/`G-LO` or future production work;
- radio-observable/raytracing readiness work;
- gravitational Level 3 convention work;
- no-go/hold if the trio exposes a blocker.

New questions:

- `Q-018` to `stas-agent`: choose the next science move after the completed
  trio.
- `Q-019` to `patrick-agent`: decide whether the 90-degree striping/topology
  caveat requires method refinement before source-age sampling.

Boundary confirmation so far: no remote commands, Open OnDemand, SSH/SCP, PBS
jobs, finalizers, Kunanyi staging, PLUTO production, XRAiSE/PRAiSE/radio/cavity
product regeneration, source-age sweep, `C-LO`, `G-LO`, comparison-case
processing, broad batch work, document builds, commits, pushes,
scientific-default changes, or external human contact occurred.

## 2026-06-23 - validation and closeout

Validation:

```text
git diff --check
<no output>

targeted placeholder/unresolved-marker scan over the new decision note,
exchange log, agent-comms thread, current status, open questions, and Goal 013
log
<no matches>

uv run python <CSV parse and expected-column check>
trio_evidence_summary.csv_rows=20 columns_ok=7
next_step_decision_matrix.csv_rows=6 columns_ok=8
```

Final status:

```text
complete_decision_packet
```

No project tests were run because this goal introduced no executable helper
code.
