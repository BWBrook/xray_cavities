# Current Status

Last updated: 2026-04-24
Primary checkpoint repo: `/home/bwbrook/papers/xray_cavities`

## Read This First

Before trusting anything below, pull the latest `xray_cavities` on the machine
you are using:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

This note should be treated as a post-stage-4 handoff. Always pull the latest
`origin/main` before relying on the exact file set or workflow bundle on any
machine.

Update on 2026-04-24:

- Barry is moving active work to a MacBook for a one-week trip.
- A new primary cross-machine handover has been added at
  `docs/READ_THIS_FIRST.md`.
- The current planning package consists of:
  - `docs/Honours_Research_Plan.md`
  - `docs/Honours_Research_Meeting_Brief.md`
  - `docs/Honours_Research_Meeting_Slides.qmd`
- The next MacBook-side task is to process supervisor-meeting feedback and turn
  it into the Week 2 execution plan.
- When the trip ends, the MacBook agent should write a return handoff under
  `docs/exchange/logs/` before WSL resumes the work.

Follow-up on the same day:

- `nectar-vm` was successfully pulled forward to the exchange-hub commit
- `deep-server` could not `git pull` from GitHub because its GitHub SSH auth is
  not configured yet
- to keep continuity intact anyway, the exchange docs were synced onto
  `deep-server` directly from WSL
- after the final stage-4 checkpoint, `nectar-vm` also pulled the updated
  `plutokore` commit cleanly
- `deep-server` ran the stage-4 capstone successfully, but a later
  `plutokore` GitLab pull from that machine failed on SSH auth, so its local
  `plutokore` checkout may remain dirty even though the synced file content used
  for this task is current

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
5. pure-Python Krause-style jet-analysis capstone
   - fresh two-case jet mini-suite on `deep-server`
   - tracer-based lobe diagnostics via `plutokore`
   - remade figures with no `pyPLUTO`

Current onboarding reports are under:

- `/home/bwbrook/papers/xray_cavities/docs/onboarding/reports/`

Most recent stage-3 reports:

- `2026-04-17-jet-setup-basic.qmd`
- `2026-04-17-jet-parameter-sweep.qmd`

Final stage-4 report:

- `2026-04-17-krause-jets-assignment.qmd`

Shareable PDFs are built under `_build/reports/` and copied to:

- `/mnt/c/Users/bwbrook/OneDrive - University of Tasmania/EXCHANGE/xray_cavities_files/reports`

## Remote Execution State

Important remote workspaces already exist on `deep-server`:

- `/home/bwbrook/work/pluto-onboarding/sod_hd`
- `/home/bwbrook/work/pluto-onboarding/rt_instability`
- `/home/bwbrook/work/pluto-onboarding/kh_instability`
- `/home/bwbrook/work/pluto-onboarding/jet_setup_basic`
- `/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep`
- `/home/bwbrook/work/pluto-onboarding/krause_jets_assignment`

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

The final onboarding capstone is now the latest science-facing checkpoint.

Summary:

- the `higher_power` jet produces a larger tracer-defined lobe than the
  baseline case at every sampled output
- by the final output, the higher-power lobe is longer, wider, and about twice
  the tracer-defined volume of the baseline
- this step successfully moved the jet-analysis lane away from `pyPLUTO` and
  onto `plutokore` plus standard Python plotting

Key final metrics at `t = 613.2028`:

- baseline:
  - lobe length `25.89 kpc`
  - lobe width `10.24 kpc`
  - lobe volume `6246.70` code units
- higher power:
  - lobe length `33.36 kpc`
  - lobe width `12.40 kpc`
  - lobe volume `12548.22` code units

Repo-scoped artifacts:

- `docs/onboarding/assets/krause_jets_assignment_2026-04-17/krause_jet_density.png`
- `docs/onboarding/assets/krause_jets_assignment_2026-04-17/krause_jet_tracer.png`
- `docs/onboarding/assets/krause_jets_assignment_2026-04-17/krause_jet_timeseries.png`
- `docs/onboarding/assets/krause_jets_assignment_2026-04-17/krause_jet_metrics.csv`

## Next Recommended Step

The onboarding sequence is now complete.

The next move should be to transition from onboarding into the actual
project-specific research questions, using:

- `jet-setup` for new simulation runs
- the pure-Python `plutokore` lane for analysis
- `deep-server` as the default execution machine
- `nectar-vm` as the continuity node for off-campus or multi-machine work

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
8. read the final onboarding capstone report before proposing new jet-analysis
   work

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
