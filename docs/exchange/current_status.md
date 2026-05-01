# Current Status

Last updated: 2026-05-01
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
- The next MacBook-side task is to turn the revised three-case plan into a
  concrete pilot/comparison specification and begin execution-path smoke tests,
  especially on resized `nectar-vm` and `kunanyi`.
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

MacBook follow-up after Stas' 2026-04-24 feedback:

- Stas' plan feedback was added at
  `docs/Honours_research_plan_feedback_SS_260424.txt`
- `docs/Honours_Research_Plan.md` was revised so that:
  - jet power and environment are the primary variables
  - source age and viewing angle are secondary sampling axes
  - radio synchrotron products are part of the core project
  - Step 11 is mandatory rather than optional
  - the minimum comparison suite is now three simulations:
    low-power cluster, high-power cluster, and low-power group
  - the fully relativistic `0.98c` branch is explicitly out of current scope
- the MacBook has local UTAS AGN mirrors under `/Users/bwbrook/git/utas-agn`
  for context and light editing, but simulation work should still be offloaded
  to resized `nectar-vm` and then `kunanyi`
- MacBook GitLab SSH auth has been checked and now works

MacBook follow-up after Patrick's jet-assignment materials:

- Patrick supplied the missing official Martin Krause jet assignment plus
  companion jet-theory slides, unpacked locally under ignored
  `docs/jet-theory/`
- the prior "Krause-style" capstone remains a useful pure-Python analysis
  precursor, but the official worksheet is now the canonical next warm-up task
- the immediate recommended execution path is:
  - run PLUTO `Test_Problems/HD/Jet` on resized `nectar-vm`
  - use external Mach `20`, pressure equilibrium, and two resolutions
    (`10` and `20` cells per beam radius)
  - produce the worksheet's density snapshots and shock/instability/backflow
    diagnostics
  - then repeat the diagnostic exercise as a small full-3D Cartesian
    `jet-setup` run before returning to the three-case science suite
- details are in
  `docs/exchange/logs/2026-04-30-patrick-jet-assignment.md`

MacBook/Nectar follow-up after official assignment execution:

- `nectar-vm` was resized to `c3.3xlarge` and used as the execution host
- Patrick's official PLUTO `HD/Jet` assignment was run at `10` and `20` cells
  per beam radius, with external Mach `20`, pressure equilibrium, and four
  nonzero density snapshots for each resolution
- the resulting report and artifacts are:
  - `docs/onboarding/reports/2026-04-30-official-jet-assignment.qmd`
  - `docs/onboarding/assets/official_jet_assignment_2026-04-30/`
- a tiny full-3D Cartesian `jet-setup` smoke was also run on resized Nectar:
  HD, particles off, King environment, `48 x 48 x 72`, final time `300`
- the resulting report and artifacts are:
  - `docs/onboarding/reports/2026-04-30-jet-setup-tiny-3d-cart.qmd`
  - `docs/onboarding/assets/jet_setup_tiny_3d_cart_2026-04-30/`
- details are in
  `docs/exchange/logs/2026-04-30-nectar-official-jet-and-3d-smoke.md`
- after the run, `nectar-vm` was parked back on `c3.xsmall`

MacBook/kunanyi follow-up:

- TPAC jumpbox access was tested successfully via the Open OnDemand 5-minute
  SSH window
- local SSH aliases now include `tpac-jumpbox` and `kunanyi`
- `ssh kunanyi` via jumpbox lands on `<tpac-host>`
- PBS tools are visible on the login node:
  - `qsub`: `/opt/pbs/bin/qsub`
  - `qstat`: `/opt/pbs/bin/qstat`
- the first clean PBS smoke job completed on compute node `n001.kunanyi`:
  - job id `688913.kunanyi-ohpc`
  - queue `test`
  - scratch workdir `/scratch/bwbrook/codex_smoke`
- details are in:
  - `docs/kunanyi_setup.md`
  - `docs/exchange/logs/2026-04-30-kunanyi-first-pbs-smoke.md`

MacBook/kunanyi follow-up on 2026-05-01:

- targeted module inventory completed successfully via
  `scripts/kunanyi/module_inventory.sh`
- best first PLUTO/HDF5 stack identified as:
  `HDF5/1.14.0-gompi-2023a`
- this stack provides GCC 12.3, OpenMPI 4.1.5, and parallel HDF5 1.14.0
- a PBS compile/run smoke completed on compute node `n001.kunanyi`:
  - job id `688922.kunanyi-ohpc`
  - queue `test`
  - workdir `/scratch/bwbrook/codex_hdf5_probe`
  - compiled with `h5pcc`
  - ran with `mpirun -np 2`
  - created and inspected `mpi_hdf5_smoke.h5`
- next kunanyi step is a tiny PLUTO build/run under PBS using this module stack
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-module-and-hdf5-smoke.md`

Second MacBook/kunanyi follow-up on 2026-05-01:

- no existing UTAS AGN source checkout was found under `/u/bwbrook` or
  `/scratch/bwbrook`
- a clean PLUTO source bundle was transferred through jumpbox to TPAC home and
  unpacked to `/scratch/bwbrook/git/utas-agn/pluto`
- PLUTO's Python 3 `--no-curses` setup path needed a scratch-only
  `raw_input = input` compatibility patch in `Tools/Python/menu.py`
- a tiny PLUTO `HD/Sod` smoke built and ran under PBS:
  - job id `688924.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - run command `mpirun -np 2 ./pluto -i pluto.ini`
  - outputs included `data.0000.dbl`, `data.0001.dbl`, `dbl.out`, `grid.out`,
    and `pluto.0.log`
- next kunanyi step is a tiny official PLUTO `HD/Jet` PBS run
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-sod-smoke.md`

Third MacBook/kunanyi follow-up on 2026-05-01:

- a tiny official PLUTO `HD/Jet` PBS smoke completed successfully:
  - job id `688926.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `16 x 48`, cylindrical 2D
  - `ETA = 10`, external Mach target `20`, PLUTO `MACH = 6.32455532034`
  - run command `mpirun -np 2 ./pluto -i pluto.ini`
  - outputs included `data.0000.dbl`, `data.0001.dbl`, `data.0002.dbl`,
    `dbl.out`, `grid.out`, and `pluto.0.log`
- PBS resource sizing notes were added for single-node and multi-node runs:
  `select=N:ncpus=28:mpiprocs=28`
- next kunanyi rung is either a larger 2D official jet run or the first
  `jet-setup` / tiny 3D smoke path on `kunanyi`
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-jet-smoke.md`

Fourth MacBook/kunanyi follow-up on 2026-05-01:

- a scaled official PLUTO `HD/Jet` 2D PBS smoke completed successfully:
  - job id `688930.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - resources `select=1:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `64 x 192`, cylindrical 2D
  - `ETA = 10`, external Mach target `20`, PLUTO `MACH = 6.32455532034`
  - run command `mpirun -np 8 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:00:21`
  - outputs included `data.0000.dbl` through `data.0004.dbl`, `dbl.out`,
    `grid.out`, and `pluto.0.log`
- next kunanyi rung is the first `jet-setup` / tiny 3D smoke path on one node
- after that, test multi-node parallelisation explicitly
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-jet-2d-scaled.md`

Fifth MacBook/kunanyi follow-up on 2026-05-01:

- a tiny full-3D Cartesian `jet-setup` PBS smoke completed successfully on one
  `kunanyi` node:
  - job id `688935.kunanyi-ohpc`
  - queue `test`
  - compute node `n010.kunanyi`
  - resources `select=1:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `48 x 48 x 72`, Cartesian 3D
  - King atmosphere, HD, particles off
  - `tstop = 300`
  - run command `mpirun -np 8 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:01:26`, `cput = 00:04:55`, and
    peak memory about `342 MB`
  - outputs included `data.0000.dbl` through `data.0002.dbl`, `dbl.out`,
    `grid.out`, and eight per-rank PLUTO logs
- the first attempt, job `688934.kunanyi-ohpc`, failed because the current
  `jet-setup` `definitions.h` does not define `COMPONENTS`; the PBS script now
  leaves that absent define alone
- next kunanyi rung is an explicit multi-node MPI test
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-jet-setup-tiny-3d-cart.md`

Sixth MacBook/kunanyi follow-up on 2026-05-01:

- PBS email notifications were tested successfully:
  - script `scripts/kunanyi/email_notify_smoke.pbs`
  - job id `688936.kunanyi-ohpc`
  - mail recipient `barry.brook@utas.edu.au`
  - mail points `abe`
  - completed with `Exit_status = 0`
  - Barry confirmed receipt of the PBS completion email
- a two-node `jet-setup` 3D MPI smoke completed successfully:
  - script `scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs`
  - job id `688937.kunanyi-ohpc`
  - queue `test`
  - compute nodes `n010.kunanyi` and `n011.kunanyi`
  - resources `select=2:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - `NRANKS` was computed from `PBS_NODEFILE` as `16`
  - run command `mpirun -np 16 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:00:54`, `cput = 00:05:40`, and
    peak memory about `617 MB`
  - outputs included `data.0000.dbl` through `data.0002.dbl`, `dbl.out`,
    `grid.out`, and 16 per-rank PLUTO logs
- the core launch pattern for production jobs is now validated:
  `select=N:ncpus=28:mpiprocs=28`, derive ranks from `PBS_NODEFILE`, run with
  `mpirun -np "$NRANKS"`, and use `#PBS -M barry.brook@utas.edu.au` plus
  `#PBS -m ae` for completion/failure notifications
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-email-and-multinode-smoke.md`

Production-prep follow-up on 2026-05-01:

- `kunanyi` is now infrastructure-ready for full jobs once the science cases
  are properly packaged
- `docs/kunanyi_setup.md` now records the remaining preparation passes before
  any serious 48-hour multi-node production run:
  - lock the case specification
  - build a production PBS template
  - add restart/resume handling and `DONE`/`FAILED` markers
  - confirm output volume and data retention/transfer plan
  - run an intermediate-size rehearsal
  - then launch production jobs
- a short collaborator-facing status update was added as:
  - `docs/kunanyi_status_update_2026-05-01.md`
  - `docs/kunanyi_status_update_2026-05-01.pdf`
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-production-prep.md`

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

The next move should be to lock the revised three-case comparison specification
and begin execution-path smoke tests, using:

- `jet-setup` for new simulation runs
- the pure-Python `plutokore` lane for analysis
- the MacBook as a control/orchestration machine only
- resized `nectar-vm` for tests, 2D runs, and micro-3D smoke runs
- `kunanyi` for full 3D production once its access/module/build/submission path
  has been smoke-tested

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
