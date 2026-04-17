# Handover Note: 2026-04-17 stage3-jet-checkpoint

## Session Context

- Machine used: WSL control plane + `deep-server` execution
- Operator path: `/home/bwbrook/papers/xray_cavities`
- `xray_cavities` commit at handoff: `0eb240d`
- Relevant UTAS AGN repo branch context:
  - `pluto`: `bwbrook/deep-server-bringup`
  - `jet-setup`: `bwbrook/deep-server-bringup`
  - `plutokore`: `bwbrook/deep-server-bringup`

## What Was Done

- completed the stage-3 onboarding work on `jet-setup`
- documented the basic jet build/run workflow
- ran a first basic jet simulation on `deep-server`
- ran a follow-up 3-case parameter sweep
- reran that sweep on a longer `60 kpc` radial domain so head-position metrics
  were no longer boundary-saturated
- committed and pushed the resulting stage-3 bundle to `xray_cavities`

## Files / Workspaces Touched

Local repo files:

- `docs/onboarding/reports/2026-04-17-jet-setup-basic.qmd`
- `docs/onboarding/reports/2026-04-17-jet-parameter-sweep.qmd`
- `docs/onboarding/assets/jet_setup_basic_2026-04-17/`
- `docs/onboarding/assets/jet_parameter_sweep_2026-04-17/`
- `scripts/pluto_onboarding/jet_setup_basic/`
- `scripts/pluto_onboarding/jet_parameter_sweep/`

Remote `deep-server` workspaces:

- `/home/bwbrook/work/pluto-onboarding/jet_setup_basic`
- `/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep`

## Validation

- remote scripts ran successfully on `deep-server` inside `tmux`
- onboarding Quarto reports rebuilt successfully
- PDFs were copied to the OneDrive reports folder
- the refined sweep produced usable head-position diagnostics:
  - baseline: `13.44 kpc`
  - higher power: `15.62 kpc`
  - wider angle: `13.44 kpc`

## Current State

- stage 3 is complete and checkpointed
- next supervisor-specified onboarding stage has not yet been started
- `deep-server` and `nectar-vm` should both pull `xray_cavities` before using
  these notes, because they were behind at the time of handoff

## Next Recommended Step

1. pull `xray_cavities` on the working machine
2. read `docs/exchange/current_status.md`
3. begin the next onboarding stage from the current clean checkpoint

## Sync Notes

- committed and pushed `xray_cavities`: yes
- `nectar-vm` needs a `git pull --ff-only`: done after this handoff note
- `deep-server` needs a `git pull --ff-only`: still yes, but currently blocked by
  missing GitHub SSH auth on that machine
- exchange docs were therefore synced onto `deep-server` directly from WSL so
  the notes are still available there immediately

## Blockers / Risks

- no active blocker at handoff
- remember that the MacBook usually cannot see `deep-server`, so Nectar should
  be treated as the continuity anchor for cross-machine work
