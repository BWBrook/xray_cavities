# Goal 012: C-HI Final 90-Degree Viewing-Angle Broadening

## Objective

Complete the controlled final-endpoint `C-HI` viewing-angle trio by adding one
new post-processing-only target: `90 deg`.

This goal is complete in one of two acceptable states:

1. `complete_product`: a compact local science package contains the final
   `C-HI`, `90 deg` product and a reviewer-facing `0/45/90 deg` comparison
   against the accepted Goal 005 `0 deg` baseline and accepted Goal 011
   `45 deg` product; or
2. `submitted_waiting_pbs_completion`: if a bounded Kunanyi post-processing job
   is required and submitted, the job is staged, submitted, verified queued or
   running, and `jet` wakes X-ray Cavities with job id and retrieval
   instructions, then stops without polling.

Do not launch a new PLUTO production run. Do not add source-age sampling,
`C-LO`, `G-LO`, comparison-case processing, or any broad batch beyond the
single final `90 deg` endpoint needed here.

## Decision Basis

Goal 012 follows the accepted Goal 011 product:

- Goal 011 completed a final `C-HI`, `45 deg` projection-sensitivity product,
  with corrected X-ray pixel-sum diagnostic `45/0 = 0.44636214774306926` and
  corrected X-ray max `45/0 = 0.11475003428628802`.
- Goal 011 preserved the required caveats: projection-sensitivity only,
  connected-envelope/X-ray-topology caveat, sparse-radio diagnostic caveat,
  Level 3 gravity tracked gap, and Stas-agent's `pV`/`2.5pV`/`4pV`
  convention.
- Goal 010 review remains the authorization basis: Patrick-agent accepted one
  narrow post-processing-only `C-HI` broadening path with caveats, and
  Stas-agent said the gravity convention does not block controlled broadening.

The orchestrator has chosen `90 deg` now because `0`, `45`, and `90 deg` are
the pre-declared post-processing viewing angles in the Meeting 2 action plan.
The `90 deg` endpoint completes the first projection-sensitivity trio while
still holding run, endpoint, source age, and comparison case fixed.

## Required Product

The preferred complete product should include:

- a dated science note, likely:
  `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`;
- a compact asset directory, likely:
  `docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/`;
- at least one reviewer-facing visual comparison spanning final `0`, `45`, and
  `90 deg`, or a clear `90 deg` product plus an explicit companion table to the
  accepted `0/45 deg` products;
- machine-readable scalar/provenance tables for:
  - the `90 deg` product;
  - direct `90 deg` versus accepted `0 deg`;
  - combined `0/45/90 deg` comparison;
  - product provenance and caveats;
- a dated exchange log under `docs/exchange/logs/`;
- a compact `docs/exchange/current_status.md` update;
- `docs/goals/012-c-hi-final-90deg-viewing-angle-broadening/Log.md` updated
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

- Read existing repo-local evidence and accepted products from Goals 005,
  010, and 011.
- Reuse or adapt the Goal 011 projection infrastructure for a final `C-HI`,
  `90 deg`, post-processing product.
- Add or extend local scripts/tests only as needed for `90 deg` packaging and
  the `0/45/90 deg` comparison.
- Add a Kunanyi PBS wrapper only if full-grid data are required and the work is
  bounded post-processing on existing final `C-HI` outputs.
- Submit a bounded Kunanyi post-processing job only if needed for the `90 deg`
  product, then obey the PBS stop rule.
- Retrieve and package compact outputs only after a job has completed or if no
  PBS stop is triggered.
- Update docs, assets, exchange logs, and goal log inside this repo.

## Out Of Scope

- No new PLUTO production simulation.
- No new 48-hour or multi-day production compute commitment.
- No source-age sampling.
- No `C-LO` or `G-LO`.
- No broad batch of views, snapshots, or cases.
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
- stage under a clear Goal 012 namespace such as
  `/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle`;
- write outputs under a dated scratch path such as
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening`;
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
- `docs/goals/011-c-hi-final-45deg-viewing-angle-broadening/Log.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/final_45deg_viewing_angle_metadata.json`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/viewing_angle_comparison.csv`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/projection_metrics.csv`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/cavity_energy_convention.csv`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid/xraise_grid_smoke_summary.csv`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
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
orchestrator Goal 012 packet commit.

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
- `0/45/90 deg` comparison highlights if complete;
- scientific caveats and recommended next step;
- current `git status --short --branch`;
- confirmation that no new PLUTO production run, no source-age/comparison-case
  broadening, no commits, and no pushes occurred.
