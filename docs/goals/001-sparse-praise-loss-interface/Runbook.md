# Runbook: Goal 001 Sparse PRAiSE-Compatible Loss Interface

## Launch

Start from:

```bash
cd /Users/bwbrook/papers/xray_cavities
pwd
git status --short --branch
git rev-parse --short HEAD
```

Record the output in `Log.md`.

## Read Order

Read:

```text
docs/goals/001-sparse-praise-loss-interface/Goal.md
docs/goals/001-sparse-praise-loss-interface/Plan.md
AGENTS.md
docs/exchange/current_status.md
docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge.md
docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md
docs/science/c_hi_particle_loss_smoke_2026-05-10.md
docs/science/c_hi_particle_radio_smoke_2026-05-10.md
scripts/science/sparse_particle_radio_bridge.py
scripts/science/xraise_particle_loss_smoke.py
scripts/science/xraise_particle_radio_smoke.py
tests/test_sparse_particle_radio_bridge.py
```

## Validation

Primary validation:

```bash
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Only if the Kunanyi sparse radio PBS wrapper is edited:

```bash
bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs
```

## Wake-Up Rule

When complete or blocked, send a short wake-up to the X-ray Cavities
orchestrator thread. Include:

- status: complete or blocked;
- changed files;
- validation result;
- current git status;
- one-sentence recommendation for the next orchestrator review step.

## Hard Stops

Stop immediately before:

- running remote jobs;
- enabling TPAC jumpbox access;
- creating dense all-history particle HDF5 caches;
- editing `/Users/bwbrook/chief_of_staff`;
- editing `/Users/bwbrook/work/goal_composer`;
- editing `/Users/bwbrook/git/utas-agn`;
- committing or pushing.
