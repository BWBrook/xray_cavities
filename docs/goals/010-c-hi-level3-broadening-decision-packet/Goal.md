# Goal 010: C-HI Level 3 Broadening Decision Packet

## Objective

Create a concise docs and `agent_comms` decision packet that asks Stas-agent and
Patrick-agent whether the accepted Goal 009 thermal/kinetic Level 3 closeout is
sufficient to unblock the first controlled `C-HI` broadening goal while
gravitational Level 3 remains `blocked_missing_potential`.

This goal is complete when the repo contains a reviewer-facing packet that:

- presents the accepted Goal 009 Level 3 evidence without overclaiming;
- asks Stas-agent whether thermal+kinetic Level 3 satisfies the `Q-013`
  pre-broadening requirement, or whether a gravitational potential/profile
  convention is required first;
- asks Patrick-agent whether the Goal 007 observational-product clearance plus
  Goal 009 Level 3 closeout are sufficient to open controlled broadening, and
  whether any runtime/provenance constraints need locking first;
- recommends the next project branch: controlled broadening, gravitational
  convention, or another explicit hold/change path.

Do not run new analysis, remote commands, PBS jobs, or product generation in
this goal.

## Why This Matters

The project has now cleared two previous blockers:

- Patrick-agent accepted the Goal 007 X-ray visual-context product as
  `PRODUCT ADEQUATE`, while preserving the caveat that radio products remain
  particle-emissivity diagnostics and X-ray topology needs later X-ray-based
  cavity-fit confirmation.
- Stas-agent required Level 3 before broadening; Goal 009 has now produced a
  green thermal/kinetic Level 3 closeout for the accepted final `C-HI`, `0 deg`
  endpoint, with a transparent gravitational blocker.

The next decision is strategic and scientific, not computational: is
thermal+kinetic Level 3 enough to open the first controlled broadening step, or
must the project first define gravitational Level 3?

## Operating Mode

Docs, evidence synthesis, and agent-comms only.

Use accepted repo-local artefacts from Goals 006-009, current `agent_comms`
threads, and the existing project plan. Do not run scripts, tests beyond
docs/CSV hygiene checks, remote commands, PBS jobs, XRAiSE/PRAiSE/radio
workflows, PLUTO workflows, document builds, or any new data processing.

This is not permission to broaden. It prepares the review request that lets
Stas/Patrick/Barry decide whether broadening can open next.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- the science decision note;
- any machine-readable decision/evidence tables;
- the new or updated `agent_comms/threads/` review request;
- updates to `agent_comms/requests/open_questions.md`;
- the dated exchange log;
- `docs/goals/010-c-hi-level3-broadening-decision-packet/Log.md`;
- final validation and recommendation.

## Scope

In scope:

- Create a dated decision note, likely:
  `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`.
- Create a compact asset directory, likely:
  `docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/`.
- Include a small machine-readable table such as:
  - `broadening_decision_matrix.csv`;
  - optional `level3_evidence_summary.csv`.
- Create a new `agent_comms` thread, likely:
  `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`.
- Update `agent_comms/requests/open_questions.md` with new open questions after
  `Q-015`, if helpful for discoverability.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `agent_comms/threads/README.md` and `docs/exchange/current_status.md`
  if the practical handoff state changes.
- Synthesize, without recomputing, evidence from:
  - Goal 006 method-review decision packet;
  - Goal 007 observational-product readiness package and Patrick-agent `Q-015`;
  - Goal 008 method gate;
  - Goal 009 Level 3 remote extraction closeout;
  - Stas-agent `Q-012` and `Q-013`;
  - Patrick-agent `Q-014`/`Q-015`;
  - Honours research plan and Meeting 2 action plan as needed for the broader
    staged-project context.
- Make the recommended next branch explicit:
  - controlled `C-HI` broadening can open;
  - controlled broadening can open with changes/guardrails;
  - hold for gravitational Level 3 convention;
  - hold for another named method blocker.

Out of scope:

- Do not run XRAiSE, PRAiSE, radio, cavity, PLUTO, PBS, or remote workflows.
- Do not regenerate figures, maps, data tables, or archives.
- Do not stage, submit, poll, retrieve, or inspect remote jobs.
- Do not broaden to `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`.
- Do not solve gravitational Level 3 or create a potential/profile convention.
- Do not create final radio observables.
- Do not change scientific defaults, thresholds, unit conversions, or accepted
  product contracts.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or external UTAS
  AGN source checkouts.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/README.md`
- `agent_comms/AGENTS.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`
- `docs/goals/007-c-hi-observational-product-readiness-gate/Log.md`
- `docs/goals/008-c-hi-level3-ambient-energy/Log.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Log.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_ambient_energy.csv`
- `docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_method_decisions.csv`
- `docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_metadata.json`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`

Read other repo-local files only as needed to verify exact evidence paths or
the agent-comms protocol. Do not read outside this repo.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at the orchestrator packet
commit, clean against `origin/main`.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Required Work

- Build a compact decision matrix with rows for:
  - Stas-agent `Q-012` enthalpy convention;
  - Stas-agent `Q-013` Level 3 prerequisite;
  - Patrick-agent `Q-015` observational-product adequacy;
  - Goal 009 thermal/kinetic Level 3 values and comparator ratios;
  - gravitational Level 3 blocker;
  - X-ray topology caveat;
  - radio-observable caveat;
  - controlled broadening candidate;
  - large-PBS-job stop rule and compute-boundary guardrail.
- Write a decision note that is short enough for collaborator agents to review
  quickly and concrete enough to support a go/hold/change decision.
- Create an `agent_comms/threads/` review request with:
  - context;
  - canonical artefact links;
  - concise message from `jet` to `stas-agent`, `patrick-agent`, and `all`;
  - requested response shape:

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

- Add separate explicit questions:
  - Stas-agent: is `partial_green_with_gravitational_blocker` sufficient to
    satisfy `Q-013`, or is gravitational Level 3 required first?
  - Patrick-agent: do Goal 007 plus Goal 009 remove the remaining
    pre-broadening blockers from the observational/runtime side?
- Update the open-question queue if doing so improves discoverability.
- Write an exchange log recording the packet and exact agent-comms asks.
- Update `current_status.md` only with a compact post-Goal-010 handoff.
- Update `Log.md` with evidence read, changed files, validation, and final
  recommendation.

## Validation Gates

Because this is docs/agent-comms only, validation is hygiene and structured-file
checks:

```bash
git diff --check
rg -n 'TB''D|TO''DO|FIX''ME|place''holder' \
  docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md \
  docs/exchange/logs/2026-06-18-c-hi-level3-broadening-decision-packet.md \
  agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md \
  docs/exchange/current_status.md \
  agent_comms/requests/open_questions.md
```

For CSV assets, run a parse/column check, for example:

```bash
uv run python - <<'PY'
import csv
from pathlib import Path
path = Path("docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18/broadening_decision_matrix.csv")
rows = list(csv.DictReader(path.open()))
required = {"component", "current_evidence", "risk_or_caveat", "decision_needed", "recommended_branch", "reviewer"}
missing = required - set(rows[0])
if missing:
    raise SystemExit(f"missing columns: {sorted(missing)}")
if len(rows) < 8:
    raise SystemExit(f"too few rows: {len(rows)}")
print(f"broadening_decision_matrix_rows={len(rows)}")
PY
```

Do not run project tests or remote validation suites merely to make the goal
look busier.

## Deliverables

Successful path deliverables:

- Dated science decision note under `docs/science/`.
- Small machine-readable decision/evidence table(s) under `docs/science/assets/`.
- New `agent_comms/threads/` review request.
- Updated `agent_comms/requests/open_questions.md`, if useful.
- Updated `agent_comms/threads/README.md`, if a new thread is added.
- Dated exchange log under `docs/exchange/logs/`.
- Compact `docs/exchange/current_status.md` update if practical state changes.
- Completed Goal 010 `Log.md`.
- Final wake-up to X-ray Cavities with:
  - changed files;
  - validation results;
  - current git status;
  - agent-comms thread path;
  - new open-question IDs;
  - headline recommendation;
  - whether the packet asks for controlled broadening, gravity-first hold, or
    another branch.
