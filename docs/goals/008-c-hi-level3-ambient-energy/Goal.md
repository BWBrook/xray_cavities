# Goal 008: C-HI Level 3 Ambient Energy Method Gate

## Objective

Define, implement, and package the first Level 3 ambient-energy diagnostic for
the accepted final 50 Myr `C-HI` endpoint.

This goal is complete when the repo contains a tested, reviewable
post-processing product that either:

- reports a coherent Level 3 ambient thermal/kinetic/gravitational energy
  comparison for the existing final `C-HI` endpoint; or
- proves, with exact missing inputs, which part of the Level 3 method cannot
  yet be computed and what the next bounded goal must supply.

Level 3 is now a required pre-broadening method step. Do not broaden to
`45/90 deg`, source-age sampling, `C-LO`, or `G-LO` before this gate is
reviewed.

## Why This Matters

Stas-agent has answered `Q-013`: Level 3 ambient energy must be completed
before the project broadens. Patrick-agent has accepted the Goal 007 X-ray
visual-context product as adequate, while still requiring that topology and
radio-observable work remain clearly labelled. Stas-agent has also answered
`Q-012`: future summaries should carry `pV`, `2.5pV`, and `4pV`, with `2.5pV`
as the adopted non-relativistic interpretation and `4pV` as the literature
comparison.

The next useful step is therefore not another production simulation and not a
viewing-angle sweep. It is a bounded post-processing method gate for ambient
gas-coupled energy on the already-completed `C-HI` final endpoint.

## Operating Mode

Post-processing autonomy is authorized. New production simulation is not.

Use local development for tests, parsing, table assembly, method notes, and
compact figure/report generation. Use Kunanyi only for bounded post-processing
against existing outputs if the required full-grid HDF5 products cannot be
processed locally.

No new PLUTO production run, no `48 h` simulation job, no new comparison case,
and no broadening job is authorized. If the work appears to require a new
large production run or a multi-day compute commitment, stop and wake X-ray
Cavities with a concrete reason.

For any authorized remote post-processing job that is submitted and verified
queued/running, use the project stop rule: wake X-ray Cavities with job id,
queue state, staged paths, and the resume command, then stop until Barry
reports the PBS completion email or explicitly asks for a re-check.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- any new or changed C/Python helpers;
- any new or changed PBS wrappers or staging helpers;
- focused tests;
- `docs/goals/008-c-hi-level3-ambient-energy/Log.md`;
- remote stdout/stderr excerpts, job IDs, checksums, and resource evidence if a
  remote post-processing job is used;
- compact local artefacts under `docs/science/` and `docs/science/assets/`;
- the science note's Level 3 definition, caveats, and recommendation.

## Scope

In scope:

- Define a first Level 3 method for the existing final 50 Myr `C-HI` endpoint:
  ambient-medium thermal, kinetic, and gravitational energy change relative to
  an auditable pre-jet or initial-state reference.
- Start from the accepted final endpoint:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`,
  timestep `Timestep_51`.
- Locate and validate the best available baseline/reference state for the same
  run family. Prefer the earliest full-grid initial output from the same
  production chain if available. Record the exact path, timestep, time, and
  shape.
- Use accepted Level 1/2 and Goal 005/007 products as context:
  - Level 1 injected energy;
  - Level 2 `tracer > 5e-3` lobe energy and volume;
  - Goal 005 cavity `pV` and `4pV`;
  - derived `2.5pV` as the adopted non-relativistic interpretation;
  - Goal 007 connected-envelope/topology note.
- Implement the smallest reliable extractor or packaging helper needed to
  compute and validate Level 3 candidate products.
- Compute or explicitly block each Level 3 component:
  - ambient thermal energy change;
  - ambient kinetic energy change;
  - ambient gravitational energy change.
- Separate ambient gas from jet/lobe material using an explicit tracer rule.
  The default ambient exclusion should be compatible with the existing
  `tracer > 5e-3` Level 2 lobe truth convention unless the evidence strongly
  supports a different reviewed threshold. Record the threshold and rationale.
- Include side-aware and bipolar rows if the method supports them cleanly.
- Include a method-decision table explaining:
  - reference state;
  - spatial mask;
  - tracer exclusion;
  - thermal formula;
  - kinetic formula;
  - gravitational formula or blocker;
  - how the result should be compared with Level 1, Level 2, `2.5pV`, and
    `4pV`.
- Produce a dated science note and exchange log.
- Update `docs/exchange/current_status.md` with a compact post-Goal-008
  handoff if the practical state changes.

Out of scope:

- Do not launch a new PLUTO production run.
- Do not submit a `48 h` or multi-day production job.
- Do not broaden to `45 deg`, `90 deg`, source-age sampling, `C-LO`, or
  `G-LO`.
- Do not generate new final radio observables.
- Do not change scientific defaults for jet power, active time, tracer
  threshold, selected IDs, PRAiSE parameters, XRAiSE physics, PLUTO inputs, or
  production-run configuration.
- Do not claim the Level 3 method is frozen for all cases unless the evidence
  and note explicitly support that narrow conclusion.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or UTAS AGN
  source checkouts outside this repo.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `scripts/science/pluto_h5_truth_extract.c`
- `scripts/science/build_final_volume_coupled_comparison.py`
- `tests/test_final_volume_coupled_comparison.py`
- relevant existing PBS wrappers under `scripts/kunanyi/`, especially
  `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs` and
  `scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs`.

Read other repo-local files only as needed to verify exact paths, HDF5
contracts, or unit conventions. Do not read outside this repo unless this goal
explicitly names the path and the access is necessary for existing-output
post-processing.

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

- Build a concise Level 3 method decision from the available evidence. Do not
  let this become a broad literature review.
- Identify the final HDF5 input and candidate baseline/reference HDF5 input.
  If a valid baseline cannot be found, stop after producing a blocker note that
  names the missing file/path and why it is required.
- Determine whether the HDF5 products contain all fields needed for thermal
  and kinetic energy changes. If they do, compute them. If they do not, name
  the missing datasets.
- Determine whether gravitational energy can be computed from repo/remote
  inputs already available to this project. If it can, compute it. If it
  cannot, record a `gravitational_component_status = blocked_input` result
  with the exact missing potential/profile/convention.
- Validate that final and baseline grids are compatible before subtracting or
  comparing cell-wise quantities.
- Produce machine-readable Level 3 outputs, likely:
  - `level3_ambient_energy.csv`;
  - `level3_method_decisions.csv`;
  - `level3_metadata.json` or `.txt`;
  - optional compact figure or comparison table if it improves review.
- Compare Level 3 quantities against:
  - Level 1 bipolar injected energy;
  - Level 2 `tracer > 5e-3` bipolar lobe energy;
  - Goal 005/006 `pV`, `2.5pV`, and `4pV`.
- Make clear whether the result is:
  - `green_for_c_hi_endpoint_review`;
  - `partial_green_with_gravitational_blocker`;
  - `blocked_missing_baseline`;
  - `blocked_missing_fields`;
  - or another precise state.
- Add focused tests for parsing, mask/threshold logic, baseline compatibility,
  component-status handling, and ratio calculations.
- If a PBS wrapper is created or edited, run `bash -n` on it.
- If remote post-processing is needed, record:
  - job id;
  - stage directory;
  - output root;
  - input HDF5 paths;
  - module/compiler environment;
  - stdout/stderr excerpts;
  - checksums of compact products;
  - whether the stop rule was invoked after submission.

## Validation Gates

Local gates before remote work:

```bash
uv run pytest tests/test_final_volume_coupled_comparison.py -q
```

Also run focused tests for any new helper, for example:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py -q
```

For every new or edited PBS wrapper listed by:

```bash
git diff --name-only -- 'scripts/kunanyi/*.pbs'
```

run `bash -n` on that exact file and record the result.

Final hygiene:

```bash
git diff --check
```

Do not run broad validation suites merely to make the goal look larger.

## Deliverables

Successful or partial-success deliverables:

- Code/helper changes needed to compute or package Level 3 ambient energy.
- Focused tests.
- Remote wrapper/staging artefacts if needed for bounded existing-output
  post-processing.
- Compact Level 3 outputs under a dated
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/` directory
  or a later date if the goal spans days.
- A science note under
  `docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md` or a later
  date if the goal spans days.
- A dated exchange log under `docs/exchange/logs/`.
- Updated `docs/exchange/current_status.md` if the practical state changes.
- Completed Goal 008 `Log.md`.

Blocked deliverables:

- Minimal failing command or preflight result.
- Exact missing file, dataset, environment profile, potential convention, or
  remote access requirement.
- A concise recommendation for whether the next step is a data-location task,
  a method decision for Stas/Patrick, or a bounded remote post-processing job.

## Completion Report

When complete or blocked, wake X-ray Cavities with:

- status;
- changed files;
- validation commands and results;
- current `git status --short --branch`;
- Level 3 result status;
- product asset paths;
- any remote job id and whether the stop rule was invoked;
- residual scientific caveats;
- recommended next goal.
