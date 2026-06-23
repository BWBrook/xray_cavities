# Goal 011: C-HI Final 45-Degree Viewing-Angle Broadening

## Objective

Create the first controlled post-processing-only broadening product for the
accepted final `C-HI` endpoint by adding one new viewing angle: `45 deg`.

This goal is complete in one of two acceptable states:

1. `complete_product`: a compact local science package compares the new final
   `C-HI`, `45 deg` product against the accepted final `0 deg` baseline, with
   validation evidence and no overclaiming; or
2. `submitted_waiting_pbs_completion`: if a bounded Kunanyi post-processing job
   is required and submitted, the job is staged, submitted, verified queued or
   running, and `jet` wakes X-ray Cavities with job id and retrieval
   instructions, then stops without polling.

Do not launch a new PLUTO production run. Do not broaden to `90 deg`, source-age
sampling, `C-LO`, or `G-LO` in this goal.

## Decision Basis

This goal acts on the answered Goal 010 review packet:

- Patrick-agent `Q-017`: `PROCEED WITH CHANGES` from the
  observational/runtime side for one narrow post-processing-only `C-HI`
  broadening step, while preserving topology, radio-observable, and large-PBS
  guardrails.
- Stas-agent `Q-016`: `PROCEED TO CONTROLLED BROADENING`; gravitational Level
  3 is not required first for the simulation/broadening step, and remaining
  energy-accounting details should be handled in post-processing.
- Stas-agent `Q-003`/`Q-004`/`Q-005`: length/volume evolution, midplane
  snapshots, radio observables, X-ray observables, and energy fractions remain
  the right validation themes, but radio luminosity and energetics can be
  adjusted in post-processing rather than blocking this first controlled step.

The orchestrator has chosen `45 deg` as the first target because it changes one
post-processing axis while holding run, endpoint, source age, and comparison
case fixed. It directly probes the projection-sensitivity question without
opening a time-series or comparison-case bundle.

## Required Product

The preferred complete product should include:

- a dated science note, likely:
  `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`;
- a compact asset directory, likely:
  `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/`;
- at least one reviewer-facing visual comparison that places the final `45 deg`
  product beside the accepted final `0 deg` baseline or otherwise makes the
  difference interpretable;
- machine-readable scalar/provenance tables for:
  - the `45 deg` product;
  - direct `45 deg` versus accepted `0 deg` comparison;
  - product provenance and caveats;
- a dated exchange log under `docs/exchange/logs/`;
- a compact `docs/exchange/current_status.md` update;
- `docs/goals/011-c-hi-final-45deg-viewing-angle-broadening/Log.md` updated
  with evidence read, work performed, validation, and final status.

The exact implementation path is left to `jet`, but the product must preserve
these interpretive boundaries:

- the new product is a controlled projection-sensitivity probe, not a
  publication-ready observable claim;
- current X-ray topology remains a connected-envelope/single-lobe caveat until
  an X-ray-based cavity-fit method confirms it;
- sparse PRAiSE and particle-binned radio products remain diagnostics, not
  validated radio observables;
- Level 3 gravitational energy remains a tracked gap unless a separately
  reviewed potential/profile convention is supplied;
- Stas-agent's energy convention should be carried through: report `pV`,
  adopted non-relativistic `2.5pV`, and literature-comparison `4pV` where
  cavity-energy quantities are reported.

## In Scope

- Read existing repo-local evidence and accepted products from Goals 005-010.
- Add or extend local scripts/tests for a final `C-HI`, `45 deg`,
  post-processing product.
- Add a Kunanyi PBS wrapper only if full-grid data are required and the work is
  bounded post-processing on existing outputs.
- Submit a bounded Kunanyi post-processing job only if needed for the `45 deg`
  product, then obey the PBS stop rule.
- Retrieve and package compact outputs only after a job has completed or if no
  PBS stop is triggered.
- Update docs, assets, exchange logs, and goal log inside this repo.

## Out Of Scope

- No new PLUTO production simulation.
- No new 48-hour or multi-day production compute commitment.
- No `90 deg`, source-age sampling, `C-LO`, or `G-LO`.
- No broad batch of viewing angles or snapshots.
- No gravitational Level 3 convention design.
- No final radio-observable claim or full radio-observable suite unless it is
  already a lightweight byproduct needed for provenance.
- No scientific-default changes, threshold changes, selected-ID changes, or
  unit-convention changes.
- No manuscript-writing or publication-readiness claim.
- No commits or pushes.

## Remote And PBS Rules

If remote full-grid post-processing is needed:

- use the repo-local Kunanyi helper route, especially
  `scripts/kunanyi/run_on_kunanyi.sh`, after the Open OnDemand jumpbox SSH
  selector is active;
- do not use Safari for Open OnDemand authentication;
- if Chrome or Computer Use access to the selector is unavailable, wake X-ray
  Cavities rather than improvising a browser route;
- stage under a clear Goal 011 namespace such as
  `/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle`;
- write outputs under a dated scratch path such as
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening`;
- verify staged file hashes and wrapper syntax before submission;
- after `qsub`, verify the job is queued or running, wake X-ray Cavities with
  job id, queue state, expected outputs, and retrieval instructions, then stop
  without polling.

If the remote post-processing completes without requiring a queued-wait state,
package compact outputs locally and report full validation evidence.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`
- `agent_comms/threads/2026-05-11-onboarding-and-current-state.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
- `docs/goals/007-c-hi-observational-product-readiness-gate/Log.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Log.md`
- `docs/goals/010-c-hi-level3-broadening-decision-packet/Log.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`

Read other repo-local files only as needed to implement this narrow product.
Do not read outside this repo.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at launch is clean `main...origin/main` at the
orchestrator Goal 011 packet commit.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Validation

Choose validation proportional to the path taken:

- always run `git diff --check`;
- run focused local tests for any new or changed helper scripts;
- run `bash -n` for any new or changed PBS wrapper;
- parse JSON/CSV outputs produced by the package;
- if a remote job is submitted, record staged file SHA-256, wrapper syntax,
  job id, queue state, and expected output paths;
- if a complete product is packaged, verify compact assets are readable and
  non-empty.

Do not run broad project test suites, document builds, or remote validation
jobs merely to make the closeout look busier.

## Wake-Up Requirements

When complete or blocked, wake X-ray Cavities with:

- final status: `complete_product`, `submitted_waiting_pbs_completion`, or a
  specific blocker;
- changed files;
- validation evidence;
- remote job id and queue state if submitted;
- product paths if complete;
- scientific caveats and recommended next step;
- current `git status --short --branch`;
- confirmation that no new PLUTO production run, broadening beyond `45 deg`,
  commits, or pushes occurred.
