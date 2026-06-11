# Goal 004: C-HI Final Production Prove-out Gap Audit

## Objective

Re-anchor the project after Goals 001-003 by auditing what the first full
50 Myr `C-HI` production run and its current post-processing products have
actually proven, what remains provisional, and what concrete prove-out goal
should come next.

This goal is complete when the repo contains a compact, reviewable
production-prove-out audit that reconciles:

- the Meeting 2 action plan;
- the Honours research plan and Stas feedback;
- the accepted Goal 001-003 products;
- the current full `C-HI` endpoint evidence;
- the remaining gates before broader production runs or scientific
  interpretation.

## Why This Matters

Goals 001-003 successfully advanced a narrow radio/truth bridge for the first
full `C-HI` endpoint. They did not prove the whole Honours workflow, the full
synthetic-observable pipeline, or readiness for manuscript-facing
interpretation.

Barry corrected the next-goal framing after Goal 003: the project is still in
the current prove-out of the first full production run, with major future work
and new production runs still ahead. Goal 004 should therefore make the state
of play sharply visible before the next technical goal is launched.

## Operating Mode

Docs/audit only. Local repo inspection only.

Do not run remote jobs, launch new analyses, regenerate large products, or
stage anything to `kunanyi`. Do not contact supervisors or other agents. Use
existing repo-local documentation, logs, scripts, tests, and compact artefacts
as evidence.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- the prove-out audit note;
- any machine-readable readiness matrix or checklist;
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`;
- the corrected `docs/exchange/current_status.md` next-action wording;
- the final recommended Goal 005 shape.

## Scope

In scope:

- Create a concise dated audit note under `docs/science/`, likely:
  `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`.
- Create a small machine-readable readiness matrix under
  `docs/science/assets/`, likely:
  `docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv`.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/exchange/current_status.md` so the latest next action is
  production-prove-out aligned, not manuscript-facing.
- Reconcile the current state against Meeting 2 phases:
  - `C-HI` first-run setup;
  - early diagnostics;
  - restart/output catalogue;
  - final full-grid endpoint integrity;
  - truth diagnostics;
  - X-ray path;
  - cavity protocol;
  - radio/PRAiSE path;
  - viewing-angle and source-age sampling;
  - mandatory comparison-suite implications.
- Reconcile the current state against Honours plan gates A-F and the
  supervisor emphasis that Step 11 is mandatory, not optional.
- Explicitly separate:
  - proven;
  - green but narrow/provisional;
  - proxy-only;
  - missing;
  - blocked on physics/supervisor decision;
  - likely next action.
- Identify the next Goal 005 recommendation in enough detail for the
  orchestrator and Barry to approve or modify.

Out of scope:

- Do not run `uv run pytest` merely to revalidate existing code unless a local
  doc-generation helper is added.
- Do not run new scripts, data workflows, document builds, manuscript builds,
  validation suites, or remote commands.
- Do not launch or prepare a new PLUTO production run.
- Do not generate new X-ray, radio, truth, cavity, or comparison products.
- Do not change scientific defaults, thresholds, or product contracts.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, or sibling project repos.
- Do not edit local UTAS AGN source checkouts under
  `/Users/bwbrook/git/utas-agn`.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/Honours_Research_Plan.md`
- `docs/Honours_research_plan_feedback_SS_260424.txt`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/exchange/logs/2026-05-07-supervisor-meeting-2-plan-update.md`
- `docs/codex_utas_phys_hons_meeting_3_transcript.md`, only enough to capture
  any still-current statement that Meeting 2 remains the working plan
- `docs/goals/001-sparse-praise-loss-interface/Log.md`
- `docs/goals/002-final-sparse-praise-loss-table/Log.md`
- `docs/goals/003-final-volume-coupled-comparison/Log.md`
- `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`
- `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
- `docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- compact current-status or science notes needed to classify X-ray/cavity,
  truth, radio, and production-run evidence

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `6a35952`, clean against
`origin/main`, unless X-ray Cavities has fast-forwarded the repo before
delegation.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Required Work

- Build a compact evidence table with rows such as:
  - production endpoint integrity;
  - output catalogue/restart provenance;
  - early diagnostic coverage;
  - final quick-look maps/profiles;
  - Level 1 injected energy;
  - Level 2 tracer-lobe truth;
  - Level 3 ambient-medium energy;
  - XRAiSE/GRAiLE final X-ray path;
  - cavity measurement protocol;
  - radio/PRAiSE loss table;
  - radio volume coupling;
  - beam/instrument treatment;
  - viewing angles;
  - source-age sampling;
  - comparison-suite readiness.
- For each row, record:
  - status category;
  - current best evidence file or remote pointer;
  - why the state is sufficient or insufficient;
  - nearest next action.
- Write a synthesis that answers:
  - what Goals 001-003 proved;
  - what they did not prove;
  - whether the first full `C-HI` run is a credible anchor for continued
    prove-out;
  - which missing gate should be attacked next;
  - what should be deferred until after another goal or supervisor decision.
- Correct stale “final-observable/manuscript-facing” next-action wording in
  `docs/exchange/current_status.md`.

## Validation Gates

Because this is docs/audit only, validation is hygiene and evidence coverage:

```bash
git diff --check
for marker in TB''D TO''DO place''holder; do
  rg -n "$marker" \
    docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md \
    docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
    docs/exchange/current_status.md
done
rg -n "manuscript-facing|publication-ready" \
  docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
  docs/exchange/current_status.md
```

The final `rg` command should return no matches unless the exchange log quotes
the stale wording to explain why it was corrected. If you add a local helper
script, run focused tests for it and record those commands in `Log.md`.
Otherwise, do not run the project test suite just to make the audit look
busier.

## Deliverables

Successful path deliverables:

- Dated prove-out audit note under `docs/science/`.
- Small machine-readable prove-out matrix under `docs/science/assets/`.
- Dated exchange log under `docs/exchange/logs/`.
- Updated `docs/exchange/current_status.md`.
- Updated `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`.
- Final wake-up to X-ray Cavities with:
  - changed files;
  - validation result;
  - current git status;
  - headline audit conclusion;
  - recommended Goal 005 shape;
  - any questions for Barry/Stas/Patrick.

Blocked path deliverables:

- A concise note explaining which required evidence could not be found.
- Specific filenames or repo areas searched.
- Whether the blocker is missing documentation, missing analysis, or a
  supervisor-science decision.
- Updated `Log.md` and final wake-up.

## Decision Authority

You may decide:

- exact audit table row labels and status categories;
- whether the matrix is CSV, Markdown table, or both;
- which existing science notes are the best evidence pointers;
- the recommended Goal 005 shape, provided it is framed as prove-out work and
  not manuscript preparation.

Pause and ask X-ray Cavities before:

- recommending a new major production run as the immediate next action;
- changing scientific defaults or contracts;
- running remote jobs or new data workflows;
- treating the first full `C-HI` endpoint as scientifically sufficient for
  broader project conclusions;
- committing or pushing.

## Stop Conditions

Stop when one of these is true:

- the prove-out audit is complete and ready for orchestrator review;
- evidence is missing in a way that prevents a credible audit;
- the next-action recommendation requires a strategic or supervisor-science
  decision before it can be stated responsibly.
