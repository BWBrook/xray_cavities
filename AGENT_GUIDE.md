# Agent guide to xray_cavities

This guide is for an AI agent joining the project with no prior context. It
aims to give you, in one read, what a long-serving collaborator knows: what
the work claims and on what evidence, which conventions matter, which
approaches have already failed and why, and what is still open. It is one of
three products drawn from the same claims ledger, alongside the journal
article and a two-page brief for general readers.

Draft of 2 November 2026 by Claude (Opus 5.5, `claude-opus-5-5`), awaiting
critique from Codex (GPT-6). Its form is an experiment; see the end.

## The question

How well do X-ray cavities measure the energy that radio jets deposit in
hot cluster and group atmospheres? Observers estimate jet power from the
enthalpy of X-ray cavities divided by an estimated age. This project tests
that chain against simulations in which the injected energy, the true age
and the full 3D state are known.

The answer is organised as a product of three factors:

```text
Q_cav / Q_true = (H_native / E_inj) × (H_X / H_native) × (t_true / t_est)
                 physical proxy       measurement        clock
```

Each factor is tested separately, holding the others at truth.

## The experiment

- **Design.** Four PLUTO 4.4 hydrodynamic jet simulations, two atmospheres
  by two powers: C-HI, C-LO, G-HI and G-LO (Cluster or Group; jet power
  2e45 or 2e43 erg/s bipolar). The source code lives in the UTAS AGN
  `pluto` and `jet-setup` repositories; see the README section
  "Relationship to UTAS AGN".
- **Grid.** Stretched Cartesian grid, 0.05 kpc cells at the centre and about
  1.7–2.1 kpc at the edges. The box is ±200 kpc in x and y and ±250 kpc in
  z, with outflow (zero-gradient) boundaries on every face.
- **Snapshots.** Selected ages of about 10, 20, 30, 40 and 50 Myr. G-HI at
  50 Myr is excluded from science summaries, as its packaging receipt
  requires.
- **Synthetic observations.** XRAiSE 1 keV X-ray maps and PRAiSE2 radio maps
  at viewing angles of 0°, 45° and 90°.
- **Where data lives.**
  - Raw outputs stay on TPAC's kunanyi cluster.
  - Compact products are in `docs/science/assets/`.
  - Bulk regenerable files are at `nectar:/data/share/xray_cavities/` (see
    the README, "Bulk data").

## What we know: the claims

`claims/claims.yaml` is authoritative. It gives each claim's evidence at a
pinned commit, its reproduce command and its caveats. In summary:

**Native energetics (the physical-proxy factor).**
- Native binary-cocoon enthalpy 2.5pV is roughly 0.47–0.79 of injected
  energy in three cases, and 0.63–1.11 in C-LO. <!-- claims: NAT-01 -->
- Enthalpy is not the energy change of the cocoon region, and the
  shock-processed ambient gas holds a comparable share.
  <!-- claims: NAT-02 NAT-03 -->
- The numerical bookkeeping closes to 2e-14 of injected energy.
  <!-- claims: NAT-04 -->

**Physical closure.**
- The whole grid gains more energy than was injected in every case, by
  6–24× in C-LO. <!-- claims: BND-01 -->
- The leading explanation is inflow through the outflow boundaries. A
  prediction was recorded before the paired controls ran, and its test is in
  progress. <!-- claims: BND-02 BND-03 -->

**Measurement (the observer factor).** Nothing is established yet.
- The legacy detector is refuted, and the recovery numbers in the
  6 September draft are withdrawn. <!-- claims: OBS-01 OBS-02 -->
- No rung of the current method ladder is adoptable. <!-- claims: DET-01 -->
- Three diagnostic lessons stand. <!-- claims: DET-02 DET-03 DET-04 -->

**Emission.**
- The emissivity extrapolation above 10 keV is safe for the range in use.
  <!-- claims: XR-01 -->
- An emission-defined native reference is the next major input.
  <!-- claims: XR-02 -->

**Clock factor.** Not yet re-established. Its earlier results rest on the
withdrawn observer numbers.

## Conventions you must apply

- **Native cocoon.** All cells with tracer `tr1 > 1e-3`, after promoting the
  stored tracer to double precision, each at full cell weight. Ambient gas is
  the exact complement. Do not use fractional tracer weighting as the
  primary definition. <!-- claims: NAT-05 -->
- **Enthalpy.** `H = α ∫ p dV`, with α = 2.5 as the primary value and α = 4
  only as a literature comparator.
- **Energy ledger.** Thermal, kinetic and gravitational energy, each as a
  same-cell change from the actual initial fields; the gravitational term
  uses the fixed initial potential, which is zero at the centre. Injected
  energy is `E_inj = Q_bipolar × t`.
- **Observer volumes.**
  - Use the revolution volume `π Σ|u| dA` for each hemisphere.
  - Count an undetected side as zero, never as missing.
  - Report completeness and purity side by side, never only as medians over
    detected sides.
- **Independence.** The native and observer routes stay separate. Tracer
  information never repairs or selects an observed cavity.
- **Standing constraints.**
  - No new PLUTO simulation without Barry's authorisation.
  - No data deletion.
  - Raw data stays remote.
  - Observer conclusions stay provisional until a detector passes.

## Traps and dead ends

- **The "accepted" detector was never the one in production.** The
  production caller ran a fixed 1%-area selection, not seed-and-grow. It
  reports cavities on cavity-free maps, and its recovery falls as cavities
  grow. Any number traced to it is unusable. <!-- claims: OBS-01 OBS-02 -->
- **The native definition can flip a conclusion.** C-LO's X-ray/native
  ratio moved from 6.76 under fractional tracer to 0.494 under the binary
  definition, from the denominator alone. <!-- claims: NAT-05 -->
- **Volume agreement can be cancellation.** Check geometry before trusting a
  ratio near 1. <!-- claims: DET-02 -->
- **The 120 kpc aperture clips late high-power lobes.** <!-- claims: DET-03 -->
- **The May 2026 no-jet controls do not match production.** They use
  reflective boundaries on a uniform 1 kpc grid, whereas production uses
  outflow boundaries on a stretched grid. Their quietness says nothing about
  production boundary inflow. <!-- claims: BND-03 -->
- **Stale paths.** Many older notes, `AGENTS.md` and the README's Docs list
  give paths from a retired machine (`/home/bwbrook/...`, `deep-server`),
  and some handover notes point to files withheld from the public
  repository. Trust `claims/claims.yaml` and dated notes in `docs/science/`
  over them.

## How to reproduce

- Python runs from the repository's `uv` environment (`uv sync`, then
  `uv run ...`); Python is pinned to 3.12.
- Each claim's `reproduce` field gives its command. Several need the bulk
  data restored first.
- Check the ledger with `uv run python scripts/claims/check_claims.py`.
- Run the test suite with `uv run pytest`. Tests that need bulk data are
  skipped when it is absent.

## Open questions, in priority order

1. **Does BND-02 hold?** The paired no-jet controls decide whether the
   closure excess is a boundary artefact. That changes how C-LO energetics,
   and the closure statement in the article, can be written.
2. **The emission-defined native reference (XR-02).** Without it, detector
   tests compare against tracer cocoons, which are not what X-ray cavities
   trace.
3. **A detector that passes.** It must be judged on per-side completeness,
   purity and the four-case contrasts. The next rungs, in order: a t = 0
   baseline, aperture sensitivity, a background-merge guard, and topology
   validation.
4. **Re-running the clock factor** on whichever detector passes.
5. **Whether α = 4 should be primary.** That depends on lobe composition: if
   the lobe plasma is mostly electron–positron pairs it is relativistic, and
   4pV is the appropriate enthalpy.

## People and venues

- **Barry Brook** leads the project and makes the decisions only a person
  can: authorisation, taste, release.
- **Claude** (Anthropic) and **Codex** (OpenAI) are collaborators with equal
  implementation priority.
- **Stas and Patrick**, of the UTAS AGN group, review the simulation and
  detector work.
- Discussion happens on a private correspondence board. Reviewed snapshots
  are published in `docs/correspondence/`, which records the reasoning behind
  most decisions here.
- Living status is in `docs/exchange/current_status.md`.

## Testing this guide

The test of this guide is whether a fresh agent, given only the repository
and this file, answers a fixed set of project questions correctly and avoids
the traps above. The question set and scoring will be agreed with Codex.
Until then, treat any gap you hit as a defect: report it, or fix it here and
in the ledger.
