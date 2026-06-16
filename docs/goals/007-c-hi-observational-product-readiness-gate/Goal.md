# Goal 007: C-HI Observational Product Readiness Gate

## Objective

Turn Patrick-agent's `Q-014` `HOLD` response into a bounded, reviewable
observational-product package for the accepted final 50 Myr `C-HI`, `0 deg`
endpoint.

This goal is complete when the repo contains a reproducible local diagnostic
package that shows whether the existing XRAiSE/GRAiLE X-ray product can support
a production-quality cavity/shell interpretation before the project broadens to
new viewing angles, source ages, `C-LO`, or `G-LO`.

The highest-priority correction is visual and methodological: the current Goal
005 review figure is too narrow in projected `x` to make the shocked
shell/cavity context clear. The next product must show enough of the simulation
grid and enough X-ray contrast structure for Barry, Patrick-agent, and
Stas-agent to judge the cavity topology.

## Why This Matters

Goal 005 proved that the final endpoint X-ray/cavity mechanics run and produce
finite products. Patrick-agent has now clarified that this is not enough for
broadening: the current figure does not yet read as a production-quality
observational product, and the radio maps remain particle-emissivity
diagnostics rather than validated radio observables.

The project should not spend further production effort on more views, ages, or
comparison cases until the final `C-HI` endpoint is visually and procedurally
legible as an observational X-ray/cavity product.

## Operating Mode

Local-first product and documentation goal.

Use the accepted local compact assets from Goals 003 and 005. Do not submit PBS
jobs. Do not run PLUTO. Do not run a new heavy XRAiSE, cavity, PRAiSE, or radio
workflow. If a missing input can only be obtained through a new remote job or a
large remote retrieval, stop and wake X-ray Cavities with the exact missing
input and why it is needed.

Small local plotting, tabulation, and test commands are allowed. A light read
of already-versioned local artefacts is expected.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- any new or changed helper script;
- focused tests for figure/product metadata;
- the generated observational-product assets;
- the science note and exchange log;
- the `agent_comms/` update asking Patrick-agent to review the new product;
- `docs/goals/007-c-hi-observational-product-readiness-gate/Log.md`;
- validation evidence.

## Scope

In scope:

- Create a reproducible local builder, likely:
  `scripts/science/build_final_observational_product_readiness.py`.
- Create focused tests, likely:
  `tests/test_final_observational_product_readiness.py`.
- Create a dated science note, likely:
  `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`.
- Create compact assets under:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/`.
- Create or update an `agent_comms/threads/` review request for
  Patrick-agent. Prefer a new thread if the product-review topic is clearer as
  a distinct follow-up to `Q-014`.
- Update `agent_comms/requests/open_questions.md` if a new Patrick-agent review
  question is added.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/exchange/current_status.md` with a compact note that
  Patrick-agent answered `Q-014` and Goal 007 is the active response.

The product package should include:

- A wide-field X-ray surface-brightness figure using the full available local
  `x_kpc`/`z_kpc` support or a clearly justified production field of view. It
  must not silently reuse the Goal 005 `xlim = +/-45 kpc` view as the main
  product.
- At least one cavity-focused X-ray panel, paired with the wide-field panel, so
  reviewers can see both context and detail.
- Tracer-mask and current cavity-boundary overlays used as diagnostics, not as
  proof that the cavity fit was performed on X-ray data.
- A contrast, residual, or unsharp-mask X-ray diagnostic derived from the
  corrected X-ray surface-brightness map, with the method recorded in metadata.
- A topology statement addressing Patrick-agent's concern that the X-ray
  shocked shell/cavity may be visually connected even though the current
  method reports two tracer-defined north/south ellipsoids.
- A clear distinction among:
  - what is seen directly in the X-ray product;
  - what comes from tracer/hydro diagnostics;
  - what remains an unvalidated observational fit.
- A radio-status section that relabels the existing sparse PRAiSE/particle maps
  as particle-emissivity diagnostics, not validated radio observables.
- A concrete next-step recommendation for full raytraced radio
  surface-brightness products at two or more frequencies. If this can be
  produced properly from existing local contracts without heavy remote work,
  include it; otherwise record it as the next bounded method/product goal rather
  than fabricating a radio-observable claim.
- A provenance table recording at least:
  snapshot, timestep, projection angle, X-ray map file, tracer file, cavity
  boundary file, field-of-view choices, color/stretch choices, contrast method,
  selected-ID/loss-table hashes where radio diagnostics are referenced, and the
  current limitation on X-ray-based cavity fitting.

Out of scope:

- Do not broaden to `45 deg`, `90 deg`, source-age sampling, `C-LO`, or `G-LO`.
- Do not formalize Level 3 ambient energy in this goal.
- Do not change scientific thresholds, selected-ID choices, PRAiSE parameters,
  XRAiSE physics, PLUTO inputs, or production-run defaults.
- Do not claim the current sparse particle-binned radio maps are validated
  radio observables.
- Do not perform a new X-ray cavity fit on hydro or tracer variables and label
  it as an observational X-ray fit.
- Do not treat this as manuscript preparation or project closeout.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or UTAS AGN source
  checkouts outside this repo.
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
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Goal.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
- `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `scripts/science/build_final_xray_cavity_alignment.py`
- `tests/test_final_xray_cavity_alignment.py`

Read other repo-local files only as needed to verify exact input paths,
metadata, or existing plotting conventions. Do not read outside this repo.

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

- Inspect the Goal 005 local asset bundle and verify that the X-ray axes span
  the broader local field. The accepted local X-ray product currently includes:
  `xraise_grid/x_kpc.tsv`, `xraise_grid/z_kpc.tsv`,
  `xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv`, and
  `xraise_grid/tracer_max_los.tsv`.
- Build the observational-product package from those accepted local inputs,
  keeping any derived products compact enough for version control.
- Ensure the main X-ray diagnostic exposes the wider grid context. If the
  product chooses a narrower field of view, it must also include a wide-field
  companion panel and metadata explaining the crop.
- Derive a documented contrast/residual/unsharp-mask view from the corrected
  X-ray map and include parameter values in machine-readable metadata.
- Overlay tracer and existing cavity boundaries only as aids. The note must
  state that the current ellipses are tracer-defined, not X-ray-fitted.
- Add a topology table or paragraph that says whether the X-ray product most
  naturally reads as two independent lobes, one connected shocked-shell
  envelope, or unresolved with current diagnostics. Do not overclaim.
- Add a radio-readiness table that separates existing sparse
  particle-emissivity diagnostics from the not-yet-validated full raytraced
  radio surface-brightness requirement.
- Post the product review request through `agent_comms/` in a shape that
  Patrick-agent can review via agent-mediated communication.
- Update `docs/exchange/current_status.md` compactly so a future agent sees
  that `Q-014` is answered and this product gate is the response.
- Update `Log.md` with evidence read, changed files, validation commands, final
  recommendation, and any blocker or follow-up goal.

## Validation Gates

Run focused validation, not broad proof-by-bulk:

```bash
uv run pytest tests/test_final_observational_product_readiness.py tests/test_final_xray_cavity_alignment.py -q
git diff --check
```

If no helper script is added, replace the pytest command with the narrowest
local checks that prove the new assets are parseable, nonblank, and have the
declared field of view.

If a PBS wrapper is edited, which is not expected, run `bash -n` on that exact
wrapper. Do not submit a PBS job.

## Deliverables

Successful path deliverables:

- A dated observational-product readiness science note under `docs/science/`.
- A compact asset bundle under `docs/science/assets/` containing figure(s),
  metadata, and machine-readable product/provenance tables.
- A focused script and tests if new product generation logic is added.
- An `agent_comms/` Patrick-agent review request.
- Updated open-question queue if useful.
- Updated current status and dated exchange log.
- Completed Goal 007 `Log.md`.

## Completion Report

When complete or blocked, wake X-ray Cavities with:

- status;
- changed files;
- validation commands and results;
- current `git status --short --branch`;
- product asset paths;
- agent-comms thread path;
- whether Patrick-agent's X-ray product concern appears addressed, unresolved,
  or blocked;
- radio-observable status and recommended next goal.
