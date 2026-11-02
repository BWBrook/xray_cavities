# READ THIS FIRST: xray_cavities MacBook handover

Last updated: 2026-04-24

This is the cross-machine handover for Barry's accelerated Honours project on
AGN jet energetics, X-ray cavities, and radio lobes. It is written for a fresh
Codex agent on the MacBook, after cloning or pulling this repository from
GitHub.

The short version: the project planning, onboarding, literature ingestion, and
meeting materials are complete. The real research phase is just about to begin.
The next agent should preserve the pilot-first plan, keep the supervisors'
11-step workflow visible, and start converting the plan into executable research
tasks.

## First commands on the MacBook

Start by getting the repository current:

```bash
git clone git@github.com:BWBrook/xray_cavities.git
cd xray_cavities
git pull --ff-only
```

If the repository is already cloned:

```bash
cd /path/to/xray_cavities
git status --short --branch
git pull --ff-only
```

Then read, in order:

1. `AGENTS.md`
2. `docs/READ_THIS_FIRST.md` (this file)
3. `docs/Honours_Research_Plan.md`
4. `docs/Honours_Research_Meeting_Brief.md`
5. `docs/Honours_Research_Meeting_Slides.qmd`
6. `docs/exchange/current_status.md`
7. `docs/deep_server_setup.md`
8. `docs/onboarding/reports/2026-04-18-onboarding-synthesis.qmd`

The current research-plan PDFs were exported on WSL to:

```text
/mnt/c/Temp/xray_cavities_meeting/
```

That Windows path will not exist on the MacBook. Re-render locally if needed.
The committed sources are the important portable artifacts.

## Repository purpose

This repository is the project shell, not the main simulation source tree.

It contains:

- the repo-local Python/Quarto documentation environment;
- onboarding and machine-state notes;
- literature converted to Markdown under `sci_lit/` (local only, not published: publisher copyright);
- the accelerated Honours research plan, meeting brief, and slide source;
- scripts and notes for working against the UTAS AGN codebase.

The main simulation and analysis source repos live separately under the UTAS AGN
GitLab namespace. On WSL they were located at:

```text
/home/bwbrook/git/utas-agn/pluto
/home/bwbrook/git/utas-agn/jet-setup
/home/bwbrook/git/utas-agn/plutokore
/home/bwbrook/git/utas-agn/jet-setup.wiki
```

On the MacBook, equivalent paths may differ. Do not hard-code the WSL paths
unless working over SSH on the WSL/deep-server side.

## Current scientific goal

The project asks:

> For a controlled low-power AGN jet in a stable cluster atmosphere, how do
> standard X-ray cavity measurements and radio-lobe observables bias estimates
> of injected and coupled jet energy as functions of source age and viewing
> angle?

The target is a PASA-style paper and arXiv submission after a six-calendar-week
accelerated Honours workflow. Week 1 has already been used for preparation,
onboarding, setup, literature ingestion, and proposal writing. Five weeks remain
for execution.

The project is intentionally pilot-first. The core deliverable is one rigorous
end-to-end experiment, not an immediate full parameter grid.

## Core pilot experiment

The supervisor-specified first science case is:

- jet power: `1e36 W`
- jet speed: `0.1c`
- launch: cluster centre
- environment: stable radially averaged cluster atmosphere from the Stewart
  workflow
- opening angle: still to be fixed with Stas and Patrick
- outputs: a small, pre-declared set of snapshots and viewing angles

The reason for the pilot-first strategy is practical and scientific. The
low-power, slow source may be the difficult case where observable recovery is
most interesting, but it may also be weak or ambiguous for initial pipeline
validation. The plan therefore keeps a higher-visibility validation case as a
fallback if the X-ray/radio/energy pipeline needs to be proven before the
low-power case can be interpreted.

## Relationship to the supervisors' 11-step workflow

Stas and Patrick proposed an 11-step workflow. The current plan keeps those
steps, but stages them carefully.

1. Learn the jet setup from Yates-Jones et al. 2021.
2. Learn jet implementation as a boundary condition.
3. Simulate a `1e36 W`, `0.1c` central cluster jet in a stable Stewart
   environment.
4. Learn radio emissivity via the PLUTO particle method and X-ray emissivity via
   GRAiLE.
5. Calculate radio emission for the slow cluster jet.
6. Calculate X-ray emissivity for each snapshot and 3D point using GRAiLE.
7. Calculate X-ray-observable energetics across observing geometries.
8. Calculate true lobe energy and energy coupled to the gas.
9. Compare true jet energy with X-ray-derived estimates.
10. Integrate radio emission over roughly `10 MHz` to `10 GHz` and compare radio
    and X-ray energies.
11. Repeat for a broader jet grid.

The current proposal turns steps 1-10 into the first end-to-end pilot pass, and
treats step 11 as a gated expansion after the baseline workflow is secure.

This is the key diplomatic balance: follow the supervisors' workflow visibly,
while keeping the scope tight enough to produce a credible result in six weeks.

## Truth definitions to preserve

The plan uses three nested levels of simulation truth.

Level 1: injected energy

- `E_inj = Q * t_active`
- must state one-sided versus total bipolar conventions explicitly
- robust and immediately available

Level 2: tracer-defined lobe energy

- measured within a transparent jet-material mask
- core physical comparator for X-ray and radio observables
- needs validation and threshold-sensitivity tests

Level 3: ambient-medium energy change

- thermal, kinetic, and gravitational components relative to the pre-jet
  atmosphere
- high-value feedback-coupling target
- not assumed turnkey; treat as a methodological deliverable

Do not let "true energetic impact" stay vague. Every comparison should say which
truth level is being used.

## Synthetic observables and measurements

X-ray products are the first priority because they are closest to the earlier
summer project and central to cavity energetics.

The baseline X-ray task is:

- produce projected X-ray maps for selected snapshots and viewing angles;
- freeze a reproducible cavity-measurement protocol;
- measure cavity boundary, volume, pressure, age, energy, and power;
- compare `pV` and `4pV` estimates against Level 1 and Level 2 truth.

Radio products are valuable, but should start as a geometry aid:

- use PLUTO particles and `plutokore`/PRAiSE-style logic if available;
- first test whether radio-defined lobe boundaries improve cavity recovery;
- defer broad-band spectra and detailed spectral ageing unless the particle
  workflow validates quickly.

The broad-band radio comparison, roughly `10 MHz` to `10 GHz`, remains part of
the supervisors' program, but it should not derail the first X-ray/truth
comparison.

## What has already been done

Repository and environment:

- `xray_cavities` was initialized and pushed as a private GitHub repository.
- The repo-local `uv` environment was established.
- Converted literature lives in `sci_lit/` in local checkouts (not published).
- Onboarding reports and exchange notes are committed.
- The latest planning package was committed and pushed before this handover.

UTAS AGN onboarding:

- PLUTO shock-tube and instability exercises were completed.
- `jet-setup` was unpacked and run.
- A small jet parameter sweep was completed.
- A pure-Python `plutokore` analysis lane was established, avoiding reliance on
  `pyPLUTO`.
- A Krause-style capstone compared tracer-defined lobes for baseline and
  higher-power mini-runs.
- Serial PLUTO, representative MPI, and local docs builds were validated on the
  WSL/deep-server setup.

Research planning:

- An earlier summer project's proposal and final report were imported under
  `docs/` (kept locally only; not published).
- A full Honours research plan was drafted, externally reviewed by another AI
  model, and revised.
- The revised plan was narrowed to a pilot-first minimum viable experiment.
- A one-page meeting brief and an 11-slide supervisor meeting deck were created.

Key committed files:

```text
docs/Honours_Research_Plan.md
docs/Honours_Research_Meeting_Brief.md
docs/Honours_Research_Meeting_Slides.qmd
docs/deep_server_setup.md
docs/exchange/current_status.md
docs/onboarding/reports/2026-04-18-onboarding-synthesis.qmd
```

## Important uncommitted/local-only note on WSL

At the time this handover was written, WSL still had this untracked input file:

```text
docs/feedback_on_draft_hons_research_plan.md
```

It contained the external AI critique that shaped the revised proposal. It was
not committed because it is an input artifact rather than a project output. The
important critique points are already incorporated into
`docs/Honours_Research_Plan.md` and summarized in this handover.

If the MacBook agent cannot see that file, this is expected.

## Current committed planning materials

The main plan is:

```text
docs/Honours_Research_Plan.md
```

Use this as the authoritative version of the project scope.

The short meeting brief is:

```text
docs/Honours_Research_Meeting_Brief.md
```

Use this when discussing the project with Stas and Patrick.

The slide deck source is:

```text
docs/Honours_Research_Meeting_Slides.qmd
```

Render it with:

```bash
cd docs
quarto render Honours_Research_Meeting_Slides.qmd --to beamer
```

If Quarto or LaTeX is missing on the MacBook, the fastest path is usually to use
the Markdown brief instead of spending time on local rendering.

## Current timeline

The accelerated schedule is:

- Week 1 complete: onboarding, setup validation, literature synthesis, draft and
  revised research plan
- Week 2: lock pilot design and run the first project-specific 3D simulation
- Week 3: produce first synthetic X-ray maps and freeze the cavity protocol
- Week 4: implement Level 1 and Level 2 truth diagnostics and compare with
  observables
- Week 5: add radio-lobe geometry test and one contrast case if feasible
- Week 6: write the PASA-style manuscript draft and prepare the arXiv submission
  package

Depending on what happens in the supervisor meeting, the first MacBook task may
be to update the plan and then start Week 2 execution planning.

## Likely next tasks after the supervisor meeting

1. Record the supervisors' decisions.

   Create or update a dated note under `docs/exchange/logs/`, and if the
   decisions change scope, update `docs/Honours_Research_Plan.md`.

2. Lock the baseline simulation specification.

   The main unknowns are opening angle, active time, output cadence, resolution,
   environment file, solver/physics flags, and whether a higher-visibility
   validation case should be nominated.

3. Confirm MacBook access to required remote or source repositories.

   For writing and planning, `xray_cavities` is enough. For simulation work,
   confirm access to the UTAS AGN GitLab repos and whichever execution machine
   will actually run PLUTO.

4. Decide the Week 2 execution target.

   The practical choices are:

   - work locally on MacBook only for planning, configuration, and scripts;
   - use Nectar as the execution node while travelling;
   - use WSL/deep-server indirectly if accessible over SSH;
   - defer heavy runs until back on WSL and use the trip for method/pipeline
     preparation.

5. Start turning the pilot design into concrete run directories and notebooks.

   Keep the first implementation small: one pilot configuration, one snapshot
   inspection path, one first synthetic-observable path.

## Machine and access caveats

WSL/deep-server state:

- WSL was the main control plane.
- `deep-server` was the primary execution machine for PLUTO runs.
- `deep-server` had validated serial and MPI runs, but some GitHub/GitLab SSH
  auth issues were documented in exchange notes.

Nectar state:

- `nectar-vm` was previously brought forward as a secondary execution node and
  exchange hub.
- It had UTAS AGN clones and parallel HDF5 support documented in
  `docs/nectar_vm_setup.md`.

MacBook state:

- Unknown at the time of this handover.
- Do not assume the UTAS AGN GitLab repos are already cloned.
- Do not assume Quarto/LaTeX or `uv` are configured until checked.
- If simulation work is needed during the trip, first establish whether the
  MacBook should submit/drive work on Nectar rather than trying to run PLUTO
  locally.

## Git and branch conventions

For this GitHub repo:

- default branch: `main`
- remote: `github.com/BWBrook/xray_cavities`
- commit/push handovers promptly so WSL and MacBook stay synchronized

For the UTAS AGN GitLab repos on WSL, the intended fork workflow was:

- `origin`: Barry's personal GitLab fork
- `upstream`: canonical `utas-agn` repository
- use `git fetch upstream` for lab changes
- push Barry's work to `origin`, not directly to canonical repos unless
  explicitly decided

Working branches noted in `AGENTS.md`:

```text
pluto: bwbrook/deep-server-bringup
jet-setup: bwbrook/deep-server-bringup
plutokore: bwbrook/deep-server-bringup
```

Check the current branch on any cloned UTAS AGN repo before editing.

## Do not lose these project decisions

- The project is an accelerated six-week Honours, not a normal year-scale plan.
- Week 1 is already spent.
- The target is a PASA-style paper and arXiv submission.
- The plan must remain visibly aligned with Stas and Patrick's 11 steps.
- The real deliverable is a rigorous pilot, not an immediate broad grid.
- Step 11, the broad grid, is retained as gated expansion.
- Radio is valuable, but first as lobe geometry; broader radio energetics are
  secondary until the particle workflow is validated.
- Level 3 ambient-energy coupling is scientifically important, but not assumed
  turnkey.
- If the low-power pilot is too ambiguous for initial validation, use a clearer
  fallback case to validate the pipeline before interpreting the difficult case.

## Suggested first prompt to the MacBook agent

Paste something like this after cloning:

```text
We are continuing Barry's accelerated Honours project from the WSL
xray_cavities repo. Read AGENTS.md and docs/READ_THIS_FIRST.md first. Then
summarize the current state, check the worktree and remotes, and help me process
any supervisor feedback from the meeting into a Week 2 execution plan. Do not
start broad implementation until the pilot simulation specification is locked.
```

## Return handoff back to WSL

When the trip is over, the MacBook agent should create a dated handoff note for
the WSL agent. Recommended path:

```text
docs/exchange/logs/YYYY-MM-DD-macbook-trip-handoff.md
```

That note should include:

- decisions from Stas and Patrick;
- files changed on the MacBook;
- commits pushed from the MacBook;
- any MacBook-specific setup performed;
- any remote runs launched or completed;
- any data locations created outside this GitHub repo;
- the next recommended WSL action.

Before handing back to WSL:

```bash
git status --short --branch
git pull --ff-only
git push
```

On return to WSL, the first WSL action should be:

```bash
cd /home/bwbrook/papers/xray_cavities
git pull --ff-only
```

Then read the MacBook handoff note before doing new work.

