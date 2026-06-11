# Goal 001: Sparse PRAiSE-Compatible Loss Interface

## Objective

Create a tested local interface that lets the final sparse-particle radio bridge
consume either the existing pressure-history proxy or an externally supplied
per-particle PRAiSE-compatible loss table keyed by selected particle ID.

This goal is complete when the sparse radio bridge can produce clearly labelled
proxy and external-loss products from deterministic local fixtures, with
metadata that prevents either path being mistaken for a final science product.

## Why This Matters

The current 50 Myr `C-HI` sparse radio bridge is green, but it is explicitly a
morphology/continuity product. Its loss term is:

```text
clip(final pressure / maximum positive pressure across sparse window, 0, 1)
```

The next scientific step is to replace that pressure-history proxy with a true
sparse PRAiSE-compatible loss path. Before running any remote job, the action
repo needs a clean local seam between sparse particle trajectories, loss
factors, radio-map construction, and provenance.

## Operating Mode

Implementation sprint with local targeted validation.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- updated tests;
- the final `Log.md`;
- validation command output;
- any short design/decision memo produced by the goal.

## Scope

In scope:

- Update `scripts/science/sparse_particle_radio_bridge.py` or add a narrowly
  scoped helper module if that keeps the loss-model boundary clearer.
- Preserve the existing pressure-history proxy path as an explicitly labelled
  fallback.
- Add an externally supplied loss-table path keyed by selected particle ID.
- Make loss-model metadata explicit enough that products cannot be overclaimed.
- Extend local fixture tests in `tests/test_sparse_particle_radio_bridge.py`.
- Add a short repo-local note under `docs/science/` explaining how this
  interface connects the June sparse bridge to the earlier May XRAiSE/PRAiSE
  smoke path.

Out of scope:

- Do not run Kunanyi, Nectar, `deep-server`, or any remote job.
- Do not use Chrome or Computer Use to enable TPAC jumpbox access.
- Do not build a dense all-history particle HDF5 cache.
- Do not claim a final PRAiSE radio product.
- Do not build the final observable comparison page.
- Do not edit UTAS AGN source repos under `/Users/bwbrook/git/utas-agn`.
- Do not commit or push.

## Read First

- `AGENTS.md` - repo-local instructions and branch/remote norms.
- `README.md` - role of this repo as project shell.
- `docs/exchange/current_status.md` - newest current state and stated next
  action.
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge.md`
  - latest bridge handoff.
- `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md` -
  current bridge method, caveats, and output contract.
- `docs/science/c_hi_particle_loss_smoke_2026-05-10.md` - earlier PRAiSE loss
  runtime gate.
- `docs/science/c_hi_particle_radio_smoke_2026-05-10.md` - earlier
  particle-loss-aware radio smoke.
- `scripts/science/sparse_particle_radio_bridge.py` - current implementation.
- `scripts/science/xraise_particle_loss_smoke.py` - previous PRAiSE loss call.
- `scripts/science/xraise_particle_radio_smoke.py` - previous full-loss radio
  smoke.
- `tests/test_sparse_particle_radio_bridge.py` - existing local fixture tests.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `e29606e`, clean against
`origin/main`, unless the repo has been fast-forwarded by X-ray Cavities before
delegation.

## Git And Publication Policy

- You may edit files needed for this goal.
- Do not stage, commit, push, merge, or open a pull request.
- Leave the working tree dirty for orchestrator review.
- If unexpected pre-existing dirty state is present before you start, stop and
  wake X-ray Cavities before editing.

## Data, Compute, And Staging Policy

- Use only local deterministic fixtures and repo-local files.
- Do not create large generated artefacts.
- Temporary test output under pytest temp directories is fine.
- No remote staging is authorized.
- Future Kunanyi work may require Chrome or Computer Use to enable the TPAC
  five-minute "Enable Jumpbox SSH" selector, but that is explicitly out of
  scope for this goal.

## Required Work

- Keep the existing pressure-history proxy route working and labelled.
- Add a loss-model interface that can consume an external table with particle
  IDs and loss factors.
- Define clear behavior for missing, duplicate, non-finite, or negative loss
  factors.
- Make output filenames and metadata distinguish proxy loss from external
  PRAiSE-compatible loss.
- Add tests proving the external-loss path is ID-keyed rather than row-order
  dependent.
- Add tests proving unsafe loss-table values are rejected or handled
  explicitly.
- Add a short design/decision note for the next remote/PRAiSE goal.

## Validation Gates

The goal is not complete until these pass locally:

```bash
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

If you touch a PBS wrapper, also run:

```bash
bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs
```

Do not run remote validation.

## Deliverables

- Code changes implementing the local loss-model interface.
- Updated tests.
- A short note under `docs/science/` describing the interface and the next
  remote/PRAiSE step.
- Updated `docs/goals/001-sparse-praise-loss-interface/Log.md`.
- Final response to X-ray Cavities with git status, files changed, validation
  commands/results, and remaining risks.
- A short wake-up message to the X-ray Cavities thread when done or blocked.

## Decision Authority

You may decide:

- whether to keep the interface inside `sparse_particle_radio_bridge.py` or add
  one small helper module;
- exact column names for the external loss table, provided they are documented
  and tested;
- whether unsafe loss factors should fail fast or be clipped, provided the
  choice is explicit and tested.

Pause and ask X-ray Cavities before:

- changing scientific defaults such as `eta`, `s`, `gmin`, `gmax`, frequency,
  redshift, tracer threshold, or volume assumptions;
- editing UTAS AGN source repos;
- running remote jobs;
- building dense particle caches;
- producing a final science claim rather than an interface/validation result.

## Stop Conditions

Stop when one of these is true:

- validation gates pass and all deliverables are ready for orchestrator review;
- unexpected dirty state exists before editing;
- the PRAiSE-compatible interface requires remote data or a scientific decision
  not authorized by this goal;
- the same blocker repeats and no meaningful local progress is possible.

## Final Response Requirements

Report:

- what changed;
- which files changed;
- validation commands and exact outcomes;
- current `git status --short --branch`;
- any untracked files;
- what remains scientifically provisional;
- whether a follow-up remote/PRAiSE goal is ready to be framed.
