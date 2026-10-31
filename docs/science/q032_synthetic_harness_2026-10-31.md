# Q-032 synthetic cavity harness and production-caller regression

Date: 2026-10-31. Author: Claude (Opus 5.5), Q-032 stream; ownership is set out in
board thread 29, messages 2644, 2647 and 2655.

## Purpose

Patrick and Stas asked (30 October; `agent_comms/decisions/README.md`) for
independent recovery and null tests of the X-ray cavity methods, and for tests
on the actual production caller, before any method replaces the selected-age
1% area selection. This note covers the parts that need no retained maps. It
contains:

- a synthetic map generator;
- a three-method ladder with interchangeable backgrounds;
- a regression test on `build_selected_age_xray_cavity.build_product`;
- a runner that applies the same ladder to the 60 retained selected-age views
  where they live.

No production product, threshold or manuscript statement changes here.

## Correction (r2, same day)

Codex's independent review (`docs/science/q032_independent_review_2026-10-31.md`;
board 2680–2681) found that the first results misdescribed the rim and
aggregated one row inconsistently. Every point was confirmed and corrected in
commit `800ceaa`:

- **Rim thermodynamics.** The r1 "isothermal" ×2 rim was in fact isobaric at
  half the ambient temperature, because the emissivity divided temperature by
  every density factor. Temperature is now an explicit factor, and r2 runs four
  rim arms (below). The r1 claim that a rim limits recovery mainly in the
  cluster is withdrawn: it came from the isobaric convention.
- **Aggregation.** Every median now runs over all eight sides, with
  nondetections counted as zero. Detection counts are reported alongside, and
  detected-only medians are kept in `summary_by_size.csv`. The r1 entry 0.27
  at a = 10 kpc was a detected-only median (6/8 sides); the all-sides value is
  0.198.
- **Manifest.** The r1 CSVs were hashed with CRLF line endings, which Git
  normalised to LF on commit. They are restored to their recorded bytes under
  a `-text` attribute, and `results/manifest.sha256` now verifies after
  checkout. New products are written with LF.
- **Topology and backgrounds.** Both are now stated explicitly (below).

The r1 products in `results/` stay unchanged as the record. Read r2 in
`results_r2/` (code commit `800ceaa`, 1,984 per-side rows, 124 scenarios).

## View geometry

All three production views rotate the line of sight in the simulation x-y plane.
The `xraise_grid_smoke_metadata.json` files record
`u = x*cos(theta) - y*sin(theta)`, so the jet axis lies in the sky plane at
0, 45 and 90 degrees. The view set therefore samples azimuth about the jet, not
inclination. Two consequences follow:

- Projected lobes never overlap the nucleus along the line of sight.
- A solid of revolution about the projected jet axis is a natural volume
  estimator for any view.

Topology censoring at 90 degrees cannot come from foreshortening.

## Components

| File | Role |
| --- | --- |
| `scripts/science/xray_cavity_synthetic.py` | Projects the tabulated cluster (002003) and group (002031) atmospheres through the production box on the production pixel axes, with pressure-matched spheroidal cavities on the jet axis and optional isothermal compressed rims. Emissivity is n² T^-1/2 exp(-1 keV/kT). Cavity and rim chords are integrated analytically. |
| `scripts/science/xray_cavity_method_ladder.py` | `legacy_area_1pct` (bit-identical to the production observer mask, tested), `seed_grow_goal045` and `deficit_threshold`, each against its observer background or a supplied one. Returns per-side masks split at z = 0, production topology class, and per-side volumes: minor/geometric/major ellipse depths, plus the Pappus revolution volume π Σ\|u\| dA. |
| `scripts/science/build_q032_synthetic_harness.py` | Runs the ladder on 64 scenarios: 2 atmospheres × 2 views × (null + 5 sizes × 3 variants). |
| `scripts/science/build_q032_selected_age_method_ladder.py` | Runs the ladder beside retained maps and returns compact rows, packed masks and one postage stamp per view, including rejected views. |
| `tests/test_xray_cavity_production_caller.py` | Drives `build_product` on a synthetic C-HI tree; pins that production binds the legacy method; strict xfail on recovering a large cavity within 30%. |

Environment tables are vendored under
`docs/science/assets/q032_synthetic_harness_2026-10-31/inputs/` with SHA-256
checksums, because `env/` is not tracked.

## Results (r2)

Outputs: `docs/science/assets/q032_synthetic_harness_2026-10-31/results_r2/`
(code commit `800ceaa`, 1,984 per-side rows, stride-2 production axes). The
tables below come straight from `summary_by_size.csv`.

- **Scenarios.** Cavity pairs touch the nucleus and have an across/along
  semiaxis ratio of 0.6, with semiaxis a = 10, 20, 40, 60 or 90 kpc along the
  jet. True volumes run from 1.5e3 to 1.1e6 kpc³ per side.
- **Ratios.** Every ratio is the recovered volume divided by the true volume,
  using the revolution estimator. The median runs over all eight sides
  (2 atmospheres × 2 views × 2 sides), with a nondetection counted as zero.
  Detected sides are shown in brackets wherever fewer than 8 of 8 were
  detected. The minor-depth ellipse agrees within a few per cent wherever a
  detection is coherent.

**Null maps.** These are four cavity-free maps (2 atmospheres × 2 views), each
with two sides, so eight sides in all.

- The legacy 1% method reports a cavity on 8/8 sides, whether it uses its own
  background or the oracle.
- Seed-and-grow and every threshold rung report nothing on 8/8.

**Legacy 1% area (production).** Retained area stays at 1% of the 120-kpc
aperture whatever the cavity size, so recovery falls as true volume rises:

| Semiaxis a (kpc) | Recovered / true |
| ---: | ---: |
| 20 | 0.17 |
| 40 | 0.025 |
| 60 | 0.008 |
| 90 | 0.003 |

At a = 10 kpc it overshoots: the minor-depth volume is 0.8 of truth and the
median revolution volume is ×19. With a perfect background it ties at zero
deficit and selects an arbitrary region. **The legacy method is a fixed-area
selector, not a cavity detector.** Changing its background does not help.

**Evacuated cavities.** Partly filled (ρ = 0.3 ρ_amb) cavities give the same
numbers within 0.01–0.05, because a pressure-matched hot fill is nearly
X-ray dark at 1 keV.

| Method / background | a=10 | 20 | 40 | 60 | 90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seed-and-grow / own polynomial | 0 (0/8) | 0.16 (4/8) | 0.86 | 0.63 | 0.03 |
| Seed-and-grow / oracle | 1.00 | 1.00 | 1.00 | 1.00 | 0.70 |
| Deficit > 0.05 / oracle | 0.76 | 0.93 | 0.97 | 0.98 | 0.69 |
| Deficit > 0.10 / oracle | 0.22 (4/8) | 0.73 | 0.89 | 0.93 | 0.68 |
| Deficit > null-calibrated / radial median | 0.20 (6/8) | 0.70 | 0.87 | 0.89 | 0.63 |

- **Aperture.** At a = 90 kpc only 68% of the true projected area lies inside
  120 kpc. Every method, even with a perfect background, is capped near 0.7.
  The aperture alone truncates.
- **Seed-and-grow.** With its own background it works only near a = 40 kpc. A
  degree-6 log-polynomial plus the 120–180 kpc outer-annulus threshold absorb
  large cavities, since the annulus then contains cavity. The polynomial
  background is its failure point. The oracle rung shows its selection logic
  is sound.
- **Thresholds.** The null-calibrated thresholds are 0.05 in three
  atmosphere-views and 0.094 in the cluster at 45°, where the box chord makes
  the radial median misfit. The simplest observer method (azimuthal-median
  background with a physical deficit threshold) is the most robust across
  sizes. Its losses come mainly from the threshold at small sizes and the
  aperture at large sizes.

**Compressed rims.** Every arm encloses an evacuated cavity. Mass ratios are
the rim's excess mass over the displaced cavity mass, integrated through the
stratified atmosphere (`rim_mass_budget.csv`).

| Arm | n/n_amb | T/T_amb | Width | Rim/displaced mass |
| --- | ---: | ---: | --- | ---: |
| `rim_isobaric_x2` (r1 rim) | 2 | 0.5 | 0.15a | 0.76–0.80 |
| `rim_isothermal_x2` | 2 | 1 | 0.15a | 0.76–0.80 |
| `rim_shock_m1p5` | 1.71 | 1.49 | 0.15a | 0.54–0.57 |
| `rim_shock_m1p5_mass_matched` | 1.71 | 1.49 | 0.24–0.25a | 1.00 |

The Mach 1.5 arms use the γ = 5/3 Rankine–Hugoniot jump. That makes them
overpressured shells, not pressure-matched ones.

Seed-and-grow against the oracle background isolates the rim's projection
effect from detector error. Values are recovered over true volume at a = 40 kpc,
with the full a = 10–90 kpc range in brackets:

| Arm | Cluster | Group |
| --- | ---: | ---: |
| Isobaric ×2 | 0.36 (0.29–0.40) | 0.90 (0.67–0.95) |
| Isothermal ×2 | 0.24 (0.17–0.28) | 0.28 (0.18–0.33) |
| Mach 1.5, 0.15a | 0.54 (0.44–0.56) | 0.35 (0.31–0.35) |
| Mach 1.5, mass-matched | 0.28 (0.23–0.31) | 0.08 (0.02–0.12) |

What changes from r1:

- **The cluster–group contrast came from the convention.** The cool isobaric
  shell is much less luminous at 1 keV in the ~1 keV group than in the hotter
  cluster. Every hot or isothermal arm removes that contrast.
- **Shock-heated rims hide more of the cavity in the group, not less.** Heating
  group gas towards and past 1 keV raises its 1 keV emissivity steeply.
- **The physical limit holds in both environments, and is stronger than r1
  said.** Against a perfect background, a mass-conserving Mach 1.5 shell
  leaves only 0.23–0.31 (cluster) and 0.02–0.12 (group) of the cavity volume
  as a measurable deficit.
- **Recovery depends on the shell prescription by up to an order of
  magnitude.** No deficit-defined volume from a shocked case can be read as a
  cavity volume until the simulated shells are measured directly.

**Rims also break the observer radial background.** The bright shell raises
the azimuthal median at its radii. The radial-median threshold then marks
off-cavity sky as deficit:

- In the group, purity falls to 0.07–0.41 and recovered "volumes" reach 4–16×
  truth, for example 16× in the mass-matched group arm at a = 20 kpc.
- With evacuated cavities its purity is 1.0 everywhere.

Higher recovery numbers for this method with rims are therefore false
positives, not better recovery.

**Topology.** Seed-and-grow against the oracle recovers a touching evacuated
pair almost exactly, yet labels 8/8 sides at every size as
`connected_cross_midplane_component`. Production accepts only
`two_separate_components`, so the energy path would reject every ideal
touching pair. Per-side volumes split at z = 0 are diagnostic only until a
topology rule is decided and validated.

**Real maps (local smoke only).**

- **C-LO 50 Myr (2026-07-07 endpoint maps).** The tracer outline as a solid of
  revolution gives 8.2–9.1e3 kpc³ per side. Recovery against it:
  - legacy: 2.2–2.3e3 kpc³ per side;
  - seed-and-grow: 4.7–5.6e3;
  - deficit > 0.05: 4.2–6.0e3.

  All have purity 1.0. The deepest deficit is below 0.20.
- **C-HI 50 Myr at 0° (2026-06-11 endpoint map).** Only 56–58% of the
  projected tracer area lies inside 120 kpc, because the cocoon reaches
  ±220 kpc.
- **C-HI 90° (2026-06-23 map).** This map shows the known vertical striping.
  It is superseded by the edge-overlap projection used in the selected-age
  products and is not interpreted here.

Recommendation for the next rung (r2):

1. Retire the legacy selector as a cavity detector. That conclusion is
   unchanged.
2. Adopt no replacement yet. Seed-and-grow with its polynomial background
   fails at most sizes. The radial-median threshold is reliable only without
   bright shells. The oracle rung needs an evolved counterfactual that does not
   exist.
3. Run the retained-map ladder as a blinded diagnostic. Preserve every
   method, view, rejected topology and aperture coverage, and pass t=0 maps
   with `--baseline` when they exist.
4. Measure the simulated shells before interpreting any deficit volume. The
   tools are native cocoon and shocked-ambient path lengths plus shell density
   and temperature. These, not a better detector, decide how much of the
   high-power volume deficit is physical projection.
5. Decide the topology rule for midplane-connected but bilaterally recoverable
   masks, and settle the aperture.

## Limits

- The synthetic atmospheres are the initial tabulated profiles. They contain no
  boundary drift, no shocked-ambient shells beyond the simple rim, no
  turbulence and no Poisson noise. Null-calibrated thresholds therefore measure
  background-model error only.
- Three backgrounds must be kept distinct:
  - The **synthetic oracle** is the matched cavity-free map of the same
    static atmosphere.
  - A **t=0 render** is the initial-state reference. The runner labels it
    `t0_baseline`.
  - An **evolved no-jet control** would be the true counterfactual. It does
    not exist, and Q-031's boundary-energy drift implies the background
    evolves without jets.

  The oracle results show that selection and volume estimation can recover
  an idealised spheroid. They do not validate t=0 subtraction on retained
  simulations.
- The null-calibrated thresholds come from noiseless initial profiles, so
  they measure background-model error only. They are not a false-positive
  rate under projection structure, Poisson noise or evolved dynamics.
- The rim arms are controlled sensitivity cases. Even the mass-matched shock
  is a uniform shell, not a simulated shocked layer.
- Tracer masks on real maps are evaluation references
  (`tr1 >= 1e-3` maximum along the line of sight), not cavity truth.

## Next

1. Run `build_q032_selected_age_method_ladder.py --base <retained root>` beside
   the 60 retained views and return its compact outputs.
2. Render t=0 XRAiSE maps for the cluster and group at 0/45/90 degrees, as the
   labelled initial-state baseline (`--baseline ENV:VIEW:DIR`).
3. Add projected path-length maps (cocoon, shocked ambient, ambient total), per
   the interface in board message 2647, to test depth and shell filling
   directly.
4. Decide the topology rule; then choose and validate the production
   replacement; flip the strict xfail;
   refresh pressure sampling, enthalpies, ages and powers.
