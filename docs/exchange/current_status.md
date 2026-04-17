# Current Status

Last updated: 2026-04-17
Primary checkpoint repo: `/home/bwbrook/papers/xray_cavities`

## Read This First

Before trusting anything below, pull the latest `xray_cavities` on the machine
you are using:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

Known repo heads when this note was written:

- WSL `xray_cavities`: `0eb240d`
- `deep-server` `xray_cavities`: `0801eb5` before pulling
- `nectar-vm` `xray_cavities`: `eb89e0d` before pulling

That means both remote machines should pull `origin/main` before a fresh agent
starts relying on these notes.

Follow-up on the same day:

- `nectar-vm` was successfully pulled forward to the exchange-hub commit
- `deep-server` could not `git pull` from GitHub because its GitHub SSH auth is
  not configured yet
- to keep continuity intact anyway, the exchange docs were synced onto
  `deep-server` directly from WSL

## Project Structure

Working model:

- WSL laptop = control plane
- `deep-server` = primary execution machine for simulation work
- `nectar-vm` = secondary execution machine and exchange hub
- `xray_cavities` = versioned environment/docs/workflow shell
- `/home/*/git/utas-agn` = actual UTAS AGN source tree

Primary branch context on all three main UTAS AGN repos:

- `pluto`: `bwbrook/deep-server-bringup`
- `jet-setup`: `bwbrook/deep-server-bringup`
- `plutokore`: `bwbrook/deep-server-bringup`

## Onboarding Progress

Completed satisfactorily:

1. PLUTO Sod shock tube, including solver and resolution comparisons
2. PLUTO instability-resolution comparisons
   - RT: `flat/euler`, `linear/hancock`, `parabolic/rk3`
   - KH: `flat/euler`, `linear/rk2`, `parabolic/rk3`
3. `jet-setup` familiarization and first basic jet run
4. small follow-up jet parameter sweep with a refined long-domain rerun

Current onboarding reports are under:

- `/home/bwbrook/papers/xray_cavities/docs/onboarding/reports/`

Most recent stage-3 reports:

- `2026-04-17-jet-setup-basic.qmd`
- `2026-04-17-jet-parameter-sweep.qmd`

Shareable PDFs are built under `_build/reports/` and copied to:

- `/mnt/c/Users/bwbrook/OneDrive - University of Tasmania/EXCHANGE/xray_cavities_files/reports`

## Remote Execution State

Important remote workspaces already exist on `deep-server`:

- `/home/bwbrook/work/pluto-onboarding/sod_hd`
- `/home/bwbrook/work/pluto-onboarding/rt_instability`
- `/home/bwbrook/work/pluto-onboarding/kh_instability`
- `/home/bwbrook/work/pluto-onboarding/jet_setup_basic`
- `/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep`

Nectar is now a valid secondary execution node with:

- `uv`
- Open MPI
- parallel HDF5
- UTAS AGN clones under `/home/ubuntu/git/utas-agn`
- `xray_cavities` under `/home/ubuntu/papers/xray_cavities`

For production-style HDF5 builds on Nectar, use the Nectar-specific PLUTO defs:

- `Config/Nectar.gcc.defs`
- `Config/Nectar.mpicc.defs`

## Most Recent Meaningful Result

The refined long-domain jet sweep is the latest science-facing checkpoint.

Summary:

- `higher_power` cleanly advances the jet head farther than the other two cases
- `wider_angle` mainly broadens the cavity rather than advancing the head at the
  same final time
- the longer `60 kpc` radial box fixed the earlier saturated head-position proxy

Key metrics from the final sweep:

- baseline: head peak radius `13.44 kpc`
- higher power: head peak radius `15.62 kpc`
- wider angle: head peak radius `13.44 kpc`

Repo-scoped artifact:

- `docs/onboarding/assets/jet_parameter_sweep_2026-04-17/jet_parameter_sweep_metrics.csv`

## Next Recommended Step

The next move is to begin the next supervisor-specified onboarding stage.

This has not been started yet in the code or reports.

## Resume Checklist For A Fresh Agent

1. pull `xray_cavities`
2. read `AGENTS.md`
3. read `docs/exchange/current_status.md`
4. read the newest note under `docs/exchange/logs/`
5. if simulation work is needed, confirm access to:
   - `deep-server` from WSL, or
   - `nectar-vm` from the MacBook
6. if using `deep-server`, prefer existing remote workspaces rather than making
   new scratch directories without a reason
7. if using `nectar-vm`, pull `xray_cavities` and the UTAS AGN repos before
   assuming parity with WSL

## Handover Checklist

Before stopping on any machine:

1. update this file if project state changed
2. add a dated note under `docs/exchange/logs/`
3. commit and push the exchange docs if they changed
4. if the work matters for MacBook continuity, pull the updated repo on
   `nectar-vm`

## Known Non-Issue

`xray_cavities` may still show unrelated untracked `sci_lit/` files locally.
Those are intentionally out of scope for the UTAS AGN onboarding workflow unless
the user explicitly asks to work on them.
