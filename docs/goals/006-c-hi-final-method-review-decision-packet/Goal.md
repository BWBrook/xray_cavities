# Goal 006: C-HI Final Method Review Decision Packet

## Objective

Convert the accepted `C-HI` final endpoint proof products from Goals 003-005
into a concise method-review decision packet for Barry, Stas-agent, and
Patrick-agent.

This goal is complete when the repo contains a supervisor/agent-facing packet
that makes the current method choices explicit, asks the right decision
questions through `agent_comms/`, and recommends whether the project should:

- freeze the current final `C-HI` protocol and broaden to controlled views or
  source-age sampling;
- revise the cavity protocol first, especially the enthalpy and age
  conventions;
- formalize a Level 3 ambient-energy method before broadening; or
- take another clearly justified path.

## Why This Matters

Goal 005 proved that the final 50 Myr `C-HI`, `0 deg` X-ray/cavity/truth/radio
alignment path can run and produce a coherent bounded product. That is a
mechanics win, not yet a method freeze.

The project plan and thread history make several issues non-optional before
replication:

- Stas-agent previously requested `2.5pV` for non-relativistic plasma rather
  than treating `4pV` as the only enthalpy interpretation.
- The Honours plan requires a fixed and auditable cavity-measurement protocol
  before applying it across views, ages, or comparison cases.
- Level 3 ambient energy is scientifically important, but methodologically
  contingent rather than assumed turnkey.
- Stas and Patrick will review much of this via their own agents, so the
  packet must be posted through the repo-mediated `agent_comms/` channel in a
  form that invites crisp agent-mediated decisions.

## Operating Mode

Docs and agent-comms only. Local repo inspection only.

Do not run remote commands, submit PBS jobs, launch data workflows, regenerate
X-ray/radio/cavity products, run document builds, or change scientific
defaults. Use accepted local artefacts from Goals 003-005 and the existing
project-plan/thread documents as evidence.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- the method-review science note;
- any machine-readable method-decision or scalar table;
- the new or updated `agent_comms/` thread;
- updates to `agent_comms/requests/open_questions.md`, if made;
- `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`;
- the final recommendation and exact requests to Stas-agent and Patrick-agent.

## Scope

In scope:

- Create a concise dated decision packet under `docs/science/`, likely:
  `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`.
- Create a small machine-readable table under `docs/science/assets/`, likely:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv`.
- Optionally create a scalar evidence table in the same asset directory if it
  helps keep the decision note compact.
- Create a new agent-comms thread, likely:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`.
- Update `agent_comms/requests/open_questions.md` with new open questions for
  Stas-agent and Patrick-agent if this improves discoverability.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/exchange/current_status.md` only if the practical state changes
  and the update can be kept compact.
- Reconcile evidence from:
  - accepted Goals 003-005;
  - the Goal 004 prove-out audit;
  - the Honours research plan;
  - the Meeting 2 action plan;
  - relevant `agent_comms/threads/` notes, especially Stas-agent's `2.5pV`,
    setup-block, ratio-plot, and diagnostic requests.
- Explicitly evaluate:
  - whether future summaries should carry `pV`, `2.5pV`, and `4pV`, and which
    convention should be the default interpretation;
  - whether the current ellipsoid plus ambient-shell pressure protocol is
    acceptable for replication or needs revision;
  - whether the hydrostatic-proxy buoyancy/refill ages are acceptable as
    labelled provisional values or need replacement before broadening;
  - whether Level 3 ambient energy is required before controlled views/source
    ages, or can proceed as a parallel/next method goal;
  - whether the accepted `C-HI`, `0 deg`, 50 Myr protocol is ready to extend to
    `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`.
- Include the operational rule for future large PBS jobs: after a large job is
  submitted and verified queued/running, the action agent wakes the
  orchestrator and stops until Barry reports the PBS completion email or gives
  an explicit re-check instruction.

Out of scope:

- Do not run XRAiSE, cavity, PRAiSE, radio, PLUTO, PBS, or remote validation
  workflows.
- Do not generate new figures or maps unless using already-existing local
  compact artefacts and no compute-heavy processing.
- Do not change scripts, PBS wrappers, scientific thresholds, product
  contracts, or data products.
- Do not write `agent_comms/decisions/README.md` as though Stas/Patrick have
  already decided. This goal should create a decision candidate and review
  request, not a resolved decision.
- Do not broaden to `C-LO`, `G-LO`, multi-angle, source-age sampling,
  beam/instrument modelling, or Level 3 implementation.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or local UTAS
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
- `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`
- `agent_comms/threads/2026-05-11-production-scale-allocation.md`
- `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md`
- `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/goals/003-final-volume-coupled-comparison/Log.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`

Read other repo-local files only as needed to verify exact evidence paths or
the current agent-comms protocol. Do not read outside this repo.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `6c3a1f7`, clean against
`origin/main`, unless X-ray Cavities has fast-forwarded the repo before
delegation.

If unexpected dirty state exists before editing, stop and wake X-ray
Cavities.

## Required Work

- Build a compact evidence table with rows for:
  - `pV`, `2.5pV`, and `4pV` enthalpy conventions;
  - sound, buoyancy, and refill age estimates;
  - ellipsoid geometry and line-of-sight depth assumption;
  - ambient-shell pressure sampling;
  - Level 1 injected-energy comparison;
  - Level 2 tracer-lobe comparison;
  - Level 3 ambient-energy status;
  - Goal 003 radio comparator status;
  - viewing-angle/source-age readiness;
  - comparison-case readiness.
- The table should include:
  - current evidence;
  - current risk or caveat;
  - decision needed;
  - recommended branch;
  - intended reviewer, such as Barry, Stas-agent, Patrick-agent, or all.
- Write a decision note that is short enough for Stas-agent and Patrick-agent
  to review quickly, but concrete enough to support a go/hold/change response.
- Create an `agent_comms/threads/` review request with:
  - context;
  - current ask;
  - canonical artefact links;
  - a message from `barry-codex` or `jet` to `stas-agent`, `patrick-agent`, and
    `all`;
  - explicit requested response shape:
    `Decision: ACCEPT CURRENT METHOD | ACCEPT WITH CHANGES | HOLD`;
  - separate questions for Stas-agent and Patrick-agent where appropriate.
- Update the open-questions queue if doing so will help the agents find the
  review request. Use new IDs after the existing queue and mark them `open`.
- Write an exchange log that records the decision packet and agent-comms
  request.
- Update `Log.md` with evidence read, changed files, validation commands, and
  final recommendation.

## Validation Gates

Because this is docs/decision and agent-comms only, validation is hygiene and
evidence coverage:

```bash
git diff --check
rg -n "TB''D|TO''DO|place''holder|TBD|TODO|placeholder" \
  docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md \
  docs/exchange/logs/2026-06-11-c-hi-final-method-review-decision-packet.md \
  agent_comms/threads/2026-06-11-c-hi-final-method-review.md \
  docs/exchange/current_status.md \
  agent_comms/requests/open_questions.md
```

If a machine-readable CSV is added, run a small parse check, for example:

```bash
uv run python - <<'PY'
import csv
from pathlib import Path
path = Path("docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv")
rows = list(csv.DictReader(path.open()))
required = {"component", "current_evidence", "risk_or_caveat", "decision_needed", "recommended_branch", "reviewer"}
missing = required - set(rows[0])
if missing:
    raise SystemExit(f"missing columns: {sorted(missing)}")
if len(rows) < 8:
    raise SystemExit(f"too few rows: {len(rows)}")
print(f"method_decision_matrix_rows={len(rows)}")
PY
```

Do not run the project test suite just to make a docs-only goal look busier.

## Deliverables

Successful path deliverables:

- Dated method-review decision note under `docs/science/`.
- Small machine-readable method-decision table under `docs/science/assets/`.
- New or updated `agent_comms/threads/` review request.
- Updated `agent_comms/requests/open_questions.md`, if useful.
- Dated exchange log under `docs/exchange/logs/`.
- Updated `docs/exchange/current_status.md`, if the practical handoff state
  changes.
- Updated `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`.
- Final wake-up to X-ray Cavities with:
  - changed files;
  - validation results;
  - current git status;
  - headline recommendation;
  - exact agent-comms thread path;
  - questions now posed to Stas-agent and Patrick-agent.

Blocked path deliverables:

- A concise note explaining which evidence or project-plan surface prevented a
  credible decision packet.
- Specific files searched.
- Updated `Log.md` and final wake-up.

## Decision Authority

You may decide:

- exact table row labels and status vocabulary;
- exact wording of the agent-comms review request;
- whether to update open questions;
- whether `current_status.md` needs a compact update.

Pause and ask X-ray Cavities before:

- treating Stas-agent or Patrick-agent as having accepted the method;
- promoting a decision into `agent_comms/decisions/README.md`;
- recommending new production compute as the immediate next action;
- running remote work or changing scientific defaults;
- committing or pushing.

## Stop Conditions

Stop when one of these is true:

- the method-review decision packet and agent-comms request are ready for
  orchestrator review;
- evidence is missing in a way that prevents a credible decision packet;
- the next action requires a Barry/Stas/Patrick decision before it can be
  stated responsibly.
