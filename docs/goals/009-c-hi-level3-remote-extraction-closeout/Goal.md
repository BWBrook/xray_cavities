# Goal 009: C-HI Level 3 Remote Extraction Closeout

## Objective

Close out the bounded Level 3 thermal/kinetic ambient-energy extraction for the
accepted final 50 Myr `C-HI` endpoint using existing remote HDF5 outputs.

This goal is complete when one of these precise states is reached:

- `submitted_waiting_pbs_completion`: a bounded existing-output post-processing
  PBS job has been staged, submitted, and verified queued or running; `jet` has
  woken X-ray Cavities with the job id, paths, and resume instructions, then
  stopped without polling;
- `green_level3_thermal_kinetic_closeout`: the tested extractor has run on the
  accepted baseline/final HDF5 pair, compact outputs have been retrieved
  locally, thermal and kinetic rows are packaged with comparator ratios, and
  local validation passes;
- `blocked_remote_access`: terminal SSH/SCP and any authorized Open OnDemand
  staging/retrieval route are not reliable enough to stage, run, or retrieve
  this bounded existing-output post-processing task;
- another specific blocker state with exact evidence.

This is not a new PLUTO production run, not a broadening run, and not a
gravitational-energy method goal.

## Why This Matters

Goal 008 produced a useful blocked method package: the thermal/kinetic Level 3
formulas are defined, the streaming extractor is locally tested, and the
baseline/final HDF5 pair has passed a remote shape/dataset preflight. Stas-agent
has made Level 3 a required pre-broadening step. The remaining useful work is
therefore to run the tested extractor on the existing HDF5 pair, or to prove
that access/staging remains the blocker.

The Goal 008 review iteration hardened the extractor to compare baseline and
final `X`, `Y`, and `Z` coordinate axes before any cell-wise subtraction. Goal
009 must preserve that contract and must not report thermal/kinetic values if
the remote coordinate check fails.

## Operating Mode

Post-processing autonomy is authorized for existing outputs. New production
simulation is not authorized.

Use local development for wrapper tests, packaging, parsing, and compact note
updates. Use Kunanyi only for bounded post-processing against the existing
baseline/final HDF5 files if local processing is impractical.

If a PBS job is submitted and verified queued or running, wake X-ray Cavities
with exact job details and stop. Do not poll for completion. Resume only after
Barry reports the PBS completion email or X-ray Cavities explicitly asks for a
re-check.

## Scope

In scope:

- Start from the accepted Goal 008 package and reuse:
  - `scripts/science/pluto_h5_level3_ambient_extract.py`;
  - `scripts/science/build_final_level3_ambient_energy.py`;
  - the Goal 008 Level 3 tests.
- Use the existing remote baseline:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5`,
  timestep `Timestep_0`.
- Use the accepted final endpoint:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`,
  timestep `Timestep_51`.
- Confirm the coordinate-compatibility contract is executed on the remote pair
  before thermal/kinetic values are trusted.
- Repair terminal SSH/SCP if possible, or use a reliable Open OnDemand
  staging/retrieval route if terminal access remains blocked.
- If compute-node processing is needed, create the smallest practical PBS
  wrapper for the extractor and follow the submit/verify/stop rule.
- Retrieve or stage only compact products needed for review:
  - extractor CSV;
  - stdout/stderr or validation transcript;
  - checksums;
  - optional resource summary.
- Package a local closeout note and assets under a new dated Goal 009 surface.
- Update `docs/exchange/current_status.md` and add a dated exchange log if the
  practical state changes.

Out of scope:

- Do not launch or modify a PLUTO production simulation.
- Do not submit a `48 h` or multi-day production job.
- Do not broaden to `45 deg`, `90 deg`, source-age sampling, `C-LO`, or
  `G-LO`.
- Do not generate new final radio observables.
- Do not change scientific defaults for tracer thresholds, unit conversions,
  `pV`/`2.5pV`/`4pV` interpretation, PRAiSE parameters, XRAiSE physics, PLUTO
  inputs, or production-run configuration.
- Do not attempt to solve gravitational Level 3 energy unless Stas/Patrick have
  provided a reviewed potential/profile convention inside authorized evidence.
  Keep gravitational status blocked if no such convention exists.
- Do not read `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or UTAS AGN source
  checkouts outside this repo.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Goal.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Plan.md`
- `docs/goals/009-c-hi-level3-remote-extraction-closeout/Runbook.md`
- `docs/goals/008-c-hi-level3-ambient-energy/Goal.md`
- `docs/goals/008-c-hi-level3-ambient-energy/Log.md`
- `docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md`
- `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_ambient_energy.csv`
- `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_method_decisions.csv`
- `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_metadata.json`
- `scripts/science/pluto_h5_level3_ambient_extract.py`
- `scripts/science/build_final_level3_ambient_energy.py`
- `tests/test_pluto_h5_level3_ambient_extract.py`
- `tests/test_final_level3_ambient_energy.py`
- relevant existing Kunanyi PBS wrappers under `scripts/kunanyi/` for style and
  environment only.

Read other repo-local files only as needed for exact path, packaging, or
validation details.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch is `main` at the orchestrator packet commit, clean
against `origin/main`.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Required Work

- Confirm Goal 008 local validation still passes before remote staging.
- Confirm the remote input paths are still present before any compute work.
- Make no claim from shape alone. The extractor coordinate check must run on
  the remote pair before values are accepted.
- Decide the smallest reliable staging route:
  - terminal SSH/SCP if repaired;
  - otherwise Open OnDemand web shell/file route if reliable enough;
  - otherwise stop with `blocked_remote_access`.
- If remote extraction can run immediately and finish within the active session
  without inappropriate login-node load, retrieve compact outputs and package
  the local closeout.
- If a PBS job is needed:
  - stage a wrapper and input paths;
  - submit the bounded post-processing job;
  - verify it is queued or running;
  - wake X-ray Cavities with job id, stage directory, output root, exact resume
    instructions, and expected compact products;
  - stop without polling.
- When compact outputs are available, package:
  - computed thermal, kinetic, and thermal-plus-kinetic rows;
  - side-aware and bipolar rows if available from the extractor;
  - ratios to Level 1, Level 2, `pV`, `2.5pV`, and `4pV`;
  - coordinate-check status;
  - gravitational status retained as blocked unless a reviewed convention is
    available.
- Produce a dated science note and exchange log.
- Update current status with a compact post-Goal-009 handoff.

## Validation Gates

Before remote staging:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
```

For every new or edited PBS wrapper listed by:

```bash
git diff --name-only -- 'scripts/kunanyi/*.pbs'
```

run `bash -n` on that exact file and record the result.

After local packaging, run the focused tests again and parse any JSON metadata:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
uv run python -m json.tool <metadata-json>
git diff --check
```

Do not run broad validation suites merely to enlarge the evidence.

## Deliverables

Depending on the state reached:

- If submitted and waiting:
  - completed Goal 009 `Log.md` up to submission;
  - staged wrapper or command transcript;
  - job id and queue/running evidence;
  - stage and output paths;
  - exact resume/retrieval instructions;
  - wake-up to X-ray Cavities, then stop.
- If extraction is completed:
  - compact local Goal 009 Level 3 closeout assets;
  - science note under `docs/science/`;
  - dated exchange log under `docs/exchange/logs/`;
  - updated `docs/exchange/current_status.md`;
  - focused tests and wrapper checks;
  - completed Goal 009 `Log.md`.
- If blocked:
  - precise blocker note with attempted access route, failure text, and the
    smallest next unblock action.
