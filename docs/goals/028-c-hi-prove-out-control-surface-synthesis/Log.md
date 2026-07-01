# Goal 028 Log - C-HI Prove-Out Control-Surface Synthesis

Date: 2026-07-01

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `d60368f`.
- Git status at start: `## main...origin/main`.
- Update check: `git pull --ff-only` reported already up to date.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

This goal is local-only. No remote commands, Open OnDemand, SSH/SCP, `qstat`,
Kunanyi staging, PBS jobs, finalizers, retrieval, remote file reads,
HDF5/XRAiSE reruns, PLUTO, PRAiSE, radio, cavity regeneration, endpoint rerun,
source-age substitution, `C-LO`, `G-LO`, comparison-case processing,
early-age branch, broad source-age sweep, publication-facing claims,
scientific-default changes, commits, pushes, cleanup, or `agent_comms` edits
are authorized.

## Evidence Read

- `docs/exchange/current_status.md`.
- Goal 027 conditional endpoint topology application note, log, metadata, and
  compact CSV assets.
- Goal 026 and Goal 025 topology-control notes/assets as provenance for the
  threshold-sensitive connected-core result.
- Goal 022 late-age axis decision note, log, metadata, and decision assets.
- Goal 021 and Goal 020 notes/assets for the full late-age evidence surface.
- Goal 016 and Goal 017 notes/assets for refined nonzero-view projection and
  endpoint viewing-angle context.
- Goal 009 Level 3 remote extraction closeout note/assets for the thermal,
  kinetic, and gravitational-energy caveat.
- Goal 005 final endpoint X-ray/cavity alignment note/assets.
- Goal 007 observational-product readiness note/assets for topology and radio
  observable caveats.
- `docs/Honours_Research_Plan.md`,
  `docs/codex_utas_phys_hons_meeting_2_action_plan.md`, and
  `docs/science/three_case_spec.md` only enough to align next-branch options.

## Work Completed

- Created the Goal 028 science synthesis note:
  `docs/science/c_hi_prove_out_control_surface_synthesis_2026-07-01.md`.
- Created the Goal 028 compact asset bundle:
  `docs/science/assets/c_hi_prove_out_control_surface_synthesis_2026-07-01/`.
- Created machine-readable control-surface, caveat, decision, escalation, and
  recommendation tables plus metadata JSON.
- Created the dated exchange log:
  `docs/exchange/logs/2026-07-01-c-hi-prove-out-control-surface-synthesis.md`.
- Updated `docs/exchange/current_status.md` with the Goal 028 handoff.

## Decision

Decision label:
`C_HI_PROVE_OUT_CONTROL_SURFACE_READY_COMPARISON_PREP_NEXT`.

The accepted C-HI endpoint, refined viewing-angle products, late-age axis, and
conditional topology control surface are sufficient to treat C-HI as the first
credible full-production prove-out control case. The selected next branch is a
local comparison-case readiness gate for `C-LO` and `G-LO` preparation, not a
remote run or production submission.

## Validation

- No helper code was added, so no project tests were needed for Goal 028.
- `uv run python -m json.tool docs/science/assets/c_hi_prove_out_control_surface_synthesis_2026-07-01/prove_out_control_surface_metadata.json`
  passed.
- CSV parse, expected-column, and nonempty checks passed for:
  - `control_surface_register.csv`
  - `remaining_caveat_register.csv`
  - `next_branch_decision_matrix.csv`
  - `expert_escalation_thresholds.csv`
  - `next_step_recommendation.csv`
- `git diff --check` passed.
- Targeted unresolved-marker scan over the science note, exchange log, Goal
  log, and `docs/exchange/current_status.md` returned no matches.
