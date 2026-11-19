# Agent guide to xray_cavities

This guide is for an AI agent joining the project with no prior context. It
aims to give you, in one read, what a long-serving collaborator knows: what
the work claims and on what evidence, which conventions matter, which
approaches have already failed and why, and what is still open. It is one of
three products drawn from the same claims ledger, alongside the journal
article and a two-page brief for general readers.

Draft of 2 November 2026 by Claude (Opus 5.5, `claude-opus-5-5`), updated
11 November with the independently checked turn-15 results by Codex GPT-6.1
Sol, with accounting-pilot results added on 14 November and the full C-LO
accounting review on 16 November by Codex (GPT-6).
The new bounded scientific synthesis awaits collaboration adjudication.
Its form is an experiment; see the end.

## The question

How well do X-ray cavities measure the energy that radio jets deposit in
hot cluster and group atmospheres? Observers estimate jet power from the
enthalpy of X-ray cavities divided by an estimated age. This project tests
that chain against simulations with known labelled power, true age and full
3D state. Realised nozzle delivery still needs measurement.

The answer is organised as a product of three factors:

```text
Q_cav / Q_true = (H_native / E_inj) × (H_X / H_native) × (t_true / t_est)
                 physical proxy       measurement        clock
```

Each factor is tested separately, holding the others at truth.
Until delivery is measured, the numerical denominator uses labelled bipolar
power times actual age; it must not be presented as measured true injection.

## The experiment

- **Design.** Four PLUTO 4.4 hydrodynamic jet simulations, two atmospheres
  by two powers: C-HI, C-LO, G-HI and G-LO (Cluster or Group; jet power
  2e45 or 2e43 erg/s bipolar, labelled as kinetic flux). The source code lives in the UTAS AGN
  `pluto` and `jet-setup` repositories; see the README section
  "Relationship to UTAS AGN".
- **Grid.** Stretched Cartesian grid, 0.05 kpc cells at the centre and about
  1.7–2.1 kpc at the edges. The box is ±200 kpc in x and y and ±250 kpc in
  z, with outflow (zero-gradient) boundaries on every face.
- **Snapshots.** Selected ages of about 10, 20, 30, 40 and 50 Myr. G-HI at
  50 Myr is excluded from all science summaries: its lobe reaches the z
  boundary. From snapshot 48 the axial edge pressure rises to 140–315 times
  its initial value, and the final margin is 1.05 kpc
  (`docs/science/four_case_boundary_spectral_field_review_2026-08-28.md`).
  Selected G-HI ages therefore end at 40 Myr.
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
  energy in three cases, and 0.63–1.11 in C-LO. Treat the C-LO values as
  exposed to boundary inflow until BND-02 is settled. <!-- claims: NAT-01 -->
- Enthalpy is not the energy change of the cocoon region, and the
  shock-processed ambient gas holds a comparable share.
  <!-- claims: NAT-02 NAT-03 -->
- The numerical bookkeeping closes to 2e-14 of injected energy.
  <!-- claims: NAT-04 -->

**Physical closure.**
- The whole grid gains more energy than the labelled input in every case, by
  6–24× in C-LO. <!-- claims: BND-01 -->
- Most of that excess is a boundary artefact (BND-02, supported on coarse
  controls). Zero-gradient outflow faces on the stratified atmosphere drive
  jet-independent inflow that grows as t². By 50 Myr it adds 7.0e59 erg in
  the cluster and 1.2e58 erg in the group, which is 22.2 and 0.385 times
  the low-power injected energy. The prediction was frozen before the paired
  controls were read
  (`docs/science/paired_nojet_boundary_prediction_2026-11-02.md`), and the
  measurement matched it to within 2–7%
  (`docs/science/paired_boundary_results_2026-11-04.md`).
  <!-- claims: BND-02 BND-03 -->
- The boundary contrast is confined to the outer 40–50 kpc (cluster) and
  20 kpc (group). The cellwise absolute drift that both twins share is not,
  so no cluster cut is certified as quiet. Its size, about 1.5% of the
  low-power scale, is an error bar for any aperture inside the cut.
  <!-- claims: BND-04 -->
- R100 storage and whole-grid-minus-boundary accounting agree closely
  (BND-05, provisional). At 11 selected complete, 40-kpc-inset-contained
  case/ages, differences from the production-mass-scaled estimate are below
  0.002837 E_label. C-HI/G-HI comparisons include 10/20/30 Myr and G-LO
  includes 10--50 Myr. The unscaled G-LO endpoint differs by up to 0.01390;
  C-HI/40 and G-HI/40 fail geometric eligibility. This strengthens the
  numerical-accounting investigation, but shared production/potential
  conventions and unmeasured transport prevent a measured delivered-energy
  correction. C-LO/50's 23.25% aperture storage excess is not yet a rigorous
  delivered-energy floor. Nozzle and in-grid source terms remain candidates.
  <!-- claims: BND-05 -->

**Measurement (the observer factor).** No observer method is adopted yet.
- The legacy detector is refuted, and the recovery numbers in the
  6 September draft are withdrawn. <!-- claims: OBS-01 OBS-02 -->
- No rung of the current method ladder is adoptable. <!-- claims: DET-01 -->
- Three diagnostic lessons stand. <!-- claims: DET-02 DET-03 DET-04 -->

**Emission.**
- The retained correction's table-edge behaviour has been checked; this
  does not establish its physical correctness. G-HI/20 now quantifies its
  region-specific sign/domain contributions and correction sensitivity.
  <!-- claims: XR-01 XR-04 -->
- An emission-defined native reference is the next major input.
  <!-- claims: XR-02 -->

**Clock factor.** Not yet re-established. Its earlier results rest on the
withdrawn observer numbers.

## Turn-15 results reviewed on 11 November

[The review note](docs/science/turn15_energy_emission_review_2026-11-11.md)
links compact tables, inspected figures and the bulk archive. The
[reconciliation](docs/science/turn18_review_reconciliation_2026-11-11.md)
corrects the primary convention, mass/gauge and emission headline. Source/product
identities pass for all 201 snapshots, as do independent compact energy and
emission arithmetic. Native fields were not independently reintegrated.
The following synthesis remains provisional for collaboration adjudication;
the raw comparisons can be used with their stated definitions.

- **True-volume pV is not total stored change.** At 30 Myr, primary native
  2.5pV/R100 storage is 0.5054/0.8053/0.4338/0.6545 in C-HI/C-LO/G-HI/G-LO;
  4pV is the comparator. At 20 Myr, ambient thermal-plus-kinetic shares are
  69.14/89.64/51.67/77.09%. The old total ambient-share headline is retired
  unless accompanied by regional mass measurements (now available for the
  C-LO history and G-HI/20): a potential-zero shift changes
  gravitational storage by that shift times regional mass change. These
  are signed Eulerian comparisons, not delivery/deposition efficiencies.
  <!-- claims: NAT-07 -->
- **Aperture and sign matter.** C-LO/50's ambient shell between R300 and
  R100 contains about 25% of the R100 stored change despite both apertures
  containing every lobe cell. Negative current-cocoon change can coexist
  with positive absolute pV. Late high-power spheres become geometrically
  incomplete; candidate inset clipping is not a certified correction.
  <!-- claims: NAT-08 -->
- **Volume agreement can hide the wrong material.** G-HI/20's 5% outlines
  at 45/90 degrees recover nearly the native volume while containing
  59.63/49.53% non-lobe cells by volume. These are three side-on azimuths of
  one snapshot, with bipolar W+/W- pooling and full-cell binary membership.
  <!-- claims: XR-03 -->
- **Ambient brightening and background fitting matter.** Moving ambient
  cancels 37--44% of the lobe deficit; its magnitude is 39--84% of the net
  observed deficit. Background effects exceed the tested correction/velocity
  sensitivities. The favorable ambient-replaced refit uses native truth;
  frozen protocol c352554 tests it as a diagnostic separately from the
  existing observer-only comparator. Moving ambient is not a shock label;
  below-cut gas is not physically static. Neither detector is promoted.
  <!-- claims: XR-04 -->

## Accounting pilots reviewed on 14 November

The [pilot review](docs/science/turn18_pilot_review_2026-11-14.md) accepts
three completed jobs for continued existing-output accounting. The fixed
C-LO/G-HI 20-Myr boxes store 1.157066/1.074883 labelled-input units. Their
R100/R300 energy components reproduce the old measurements to numerical
precision. Regional mass now accompanies these two case/ages: an illustrative
+1e15 cm²/s² potential shift changes R100 ambient total shares from
97.52%/53.55% to 105.32%/55.17%. These are signed same-cell contributions,
not deposition efficiencies. The full C-LO review follows below. NAT-11 compares all four histories.
<!-- claims: NAT-09 -->

G-LO's first saved flux interval does not localise a numerical source.
Initial surface fluxes are zero. The outside-nozzle source balance spans
1.06434–1.08083, 0.51807–0.54738 and −0.02821–0.01393 labelled-input units
under left, trapezoid and right quadratures. The roughly half-label trapezoid
residual is not measured in-grid heating. These are scenarios, not formal
error bounds; full histories cannot recover the missing startup trajectory.
<!-- claims: BND-06 -->

Full fixed/flux jobs 879902–879909 are submitted in a serial I/O chain with
verified completion/abort mail. G-HI requests stop at index 47. The frozen
emission cohort remains unscored. See the current status before interpreting
these dated scheduler observations as current execution state.

## Full C-LO accounting history reviewed on 16 November

Both jobs completed F/0 with exact indices 0–50 and 110 completion products.
The [history review](docs/science/turn18_clo_history_review_2026-11-16.md)
and [evidence guide](docs/science/assets/turn18_clo_review_2026-11-16/README.md)
record independent fixed, flux, cross-storage and provenance checks, all
replayed successfully from a fresh archive restoration. This accepts compact
arithmetic and receipt/source bindings, not native reintegration or physical
energy closure.

- **The early aperture explanation is not rescued.** At 1 Myr the fixed box
  stores 0.922559 labelled-input units versus R100's 0.926351. The added
  region has negative net signed storage, so enlarging to this box does not
  explain the early deficit as omitted positive energy. The registered
  prediction remains failed. Energy beyond the box and cancellation of
  positive/negative contributions remain separate questions.
- **Late storage excess is larger in the box.** At 50 Myr, fixed-box/R100
  storage is 1.288860/1.232527 labelled-input units. Regional mass accompanies
  the full history; R100 ambient signed total share is then 112.98%, changing
  to 123.42% under the illustrative +1e15 cm²/s² potential shift.
- **Coverage is operational, not causal.** Cocoon and speed≥100-km/s cells
  remain inset-contained, but speed≥30 containment fails from index 26 and
  1% thermodynamic containment from index 5, with domain-face contact.
  Neither a quiet production interior nor a delivered-energy floor follows.
  <!-- claims: NAT-10 -->
- **The source remains unlocalised through the full history.** At 50 Myr,
  changing only outer-face reconstruction changes the trapezoidal whole-grid
  source by 1.54355 labelled-input units. Outside-nozzle balances span
  −1.85036 to +0.65619 across the scenarios; the final interval also has sign
  ambiguity. Nozzle-control cumulative inferred source spans 1.092215–1.128000,
  but is a continuum snapshot balance, not measured solver delivery. Scenario
  spreads are not confidence intervals or certified error bounds.
  <!-- claims: BND-07 -->

## Four fixed histories reviewed by 18 November

The last fixed job, G-LO, brings the total to 201 snapshots. Its fixed-box
storage at 50 Myr is 1.17814 times labelled input. G-LO's R100 sphere and
current lobe are inside the box throughout. Thermodynamic changes reach
the domain faces from index 8. At ~20 and ~30 Myr, the change in energy
outside the inset box agrees to within 0.008% between HI and LO **within
each atmosphere**, despite the hundredfold difference in labelled power.
Mass and thermal-plus-kinetic changes show the same pattern. The discrepancy
grows at late high-power ages as lobe material leaves the fixed aperture.
The [four-case review](docs/science/four_case_fixed_histories_2026-11-18.md)
gives component tables, geometry and the archive replay.
<!-- claims: NAT-11 -->

## Flux histories from the original accounting batch

G-LO flux finished with 51 snapshots. At its 50-Myr endpoint, the cumulative
outside-nozzle balance spans −0.03464 to +0.07091 times labelled input.
The final individual interval is negative across the tested choices. It
uses the input during that one interval. At the common 30-Myr age the two
low-power cumulative balances span zero, and both high-power balances are
negative across all 36 choices. The four endpoint nozzle-control balances
exceed labelled input across the scenarios. This is a reconstructed source
in a control volume containing the nozzle. Assessing discrete jet supply
requires separate overwrite and solver transport accounting.

The [flux comparison](docs/science/four_case_flux_histories_2026-11-18.md)
records the complete original batch. G-HI ends at 46 Myr because its outer
linear reconstruction failed at 47. The [separate endpoint measurement](docs/science/ghi_flux_endpoint_2026-11-19.md)
recovers 18 outer-active-cell and six linear left-rectangle estimates.
Every available cumulative outside-nozzle balance is negative. The
linear trapezoid and right rectangle require a 47 Myr face value where
linear extrapolation gives negative pressures. BND-05 remains provisional.
<!-- claims: BND-08 -->

The known-input nozzle calibration uses the native cell coordinates, the
three original padded surfaces and the original two face reconstructions.
The spherical injection branch sets the cone offset to zero. On G-HI the
largest synthetic reading is 1.0345 times the label across two encodings
of a steady jet. The six matched production sources at 29–30 Myr are
1.1305–1.1494. On C-LO the centred estimate at the widest box reads 1.2312
from point samples and falls below one on volume-averaged conserved
quantities. The calibration measures a dependence on unresolved structure
and supplies no common correction to production. G-HI's cumulative
whole-grid excess is 7.8–8.0% at 30, 40 and 46 Myr under all six outer-face
and time rules. Use the measured outside balance as an accounting difference.
The [calibration report and replay](docs/science/nozzle_flux_calibration_2026-11-19.md)
give the case-specific references, component and refinement checks, and the
matched final intervals.
<!-- claims: BND-08 BND-09 -->

The manufactured nozzle test falls below production in C-HI, G-HI and G-LO.
C-LO admits a reconstruction error of the observed size. The gas adjacent
to the production jet can differ from the gas in either manufactured
representation. [Case-by-case comparison](docs/science/nozzle_flux_calibration_2026-11-19.md)
<!-- claims: BND-09 -->

For jet mass history use the whole-grid sum of density times the stored
tracer fraction and cell volume, subtract its measured initial value, and
compare with twice the bipolar labelled kinetic energy divided by speed
squared. The retained-to-labelled mass ratios at 30 Myr are 1.1554,
1.1047, 1.1516 and 1.1326 in C-HI, C-LO, G-HI and G-LO. The archive replay
checks native volume bounds, all 201 raw tracer ranges, net total-gas mass
through the nozzle boxes, and sampled outer-face bounds. The 2 November
HI-minus-LO total-mass difference includes complementary gas. The marked
mass supports excess mass loading in G-HI and leaves the kinetic
energy per unit numerical transfer open. [Tracer-mass test and replay](docs/science/tracer_mass_budget_2026-11-19.md)
<!-- claims: BND-10 -->

The cap geometry gives a direct control. Its 64 lateral faces add 14.2% of the
continuum mass rate when the prescribed radial state is evaluated at their
centres. The public fixture reproduces the geometry, and the compiled PLUTO
comparisons establish how the exterior changes cap transport. For production,
compare the signed cap and stationary fluxes with the tracer inventory,
including storage in the maintained sphere and transport through the outer
faces. The zero outward rates through 30 Myr apply at saved times.
Potential-energy accounting supplies a comparison for the direct gravity-work
integral. [Injector inputs and replay](docs/science/injector_faces_2026-11-19.md) · [Boundary and gravitational work](docs/science/outer_tracer_gravity_2026-11-19.md)
<!-- claims: BND-08 BND-10 BND-11 -->

## Conventions you must apply

- **Native cocoon.** All cells with tracer `tr1 > 1e-3`, after promoting the
  stored tracer to double precision, each at full cell weight. Ambient gas is
  the exact complement. Do not use fractional tracer weighting as the
  primary definition. <!-- claims: NAT-05 -->
- **Enthalpy.** `H = α ∫ p dV`, with α = 2.5 as the primary value and α = 4
  only as a literature comparator.
- **Energy ledger.** Thermal, kinetic and gravitational energy, each as a
  same-cell change from the actual initial fields; the gravitational term
  uses the fixed initial potential, which is zero at the centre. The
  labelled-input normalization is `E_inj = Q_bipolar × t`; realised delivery
  remains unmeasured. This applies to historical fractions labelled injected
  energy: do not apply an unmeasured 1.08--1.23 correction.
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

1. **What causes the excess stored energy (BND-05)?** Q-031 reconstructs face transport
   and control-volume balances from saved states; it does not directly
   measure numerical nozzle overwrite or solver-step delivery. The startup
   pilot is cadence-ambiguous (BND-06); the full C-LO history also remains
   reconstruction/cadence-ambiguous (BND-07). All four fixed histories are now available (NAT-11). BND-08 covers
   the original flux batch and G-HI endpoint addendum. BND-09 tests the
   nozzle reconstruction on known flows. BND-10 measures net marked-mass
   accumulation independently. A trend with control radius can arise from
   changing reconstruction error or from real energy exchange. Interpreting
   a radial comparison requires storage and mass transport as well as
   energy transport. Write
   physical closure as "boundary-dominated, with an unexplained residual".
   The 100/300 km/s spherical budgets (Stas's priority of 4 November)
   measure storage inside speed-defined apertures, retaining boundary and
   coverage flags rather than imposing an uncertified cut. All four histories
   are now reviewed (201 snapshots); their component/proxy and aperture
   comparisons are above. Slower disturbance remains outside. Realised
   delivery, aperture transport and production-boundary qualification remain
   the highest-value accounting measurements. The C-LO fixed-box history
   measures signed storage beyond R100 without rescuing its early prediction.
   <!-- claims: NAT-06 NAT-07 NAT-08 NAT-09 NAT-10 BND-06 BND-07 BND-08 BND-09 BND-10 -->
2. **The emission-defined native reference (XR-02).** Without it, detector
   tests compare against tracer cocoons, which are not what X-ray cavities
   trace. The new G-HI/20 C/moving-ambient/below-cut diagnostic is useful
   evidence, but supplies neither a validated shock label nor an adopted
   four-case reference. <!-- claims: XR-02 XR-03 XR-04 -->
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
the traps above. The procedure is in `claims/guide_eval/README.md`. If you are
the agent under test, do not open `claims/guide_eval/`. Treat any gap you hit
as a defect: report it, or fix it here and in the ledger.
