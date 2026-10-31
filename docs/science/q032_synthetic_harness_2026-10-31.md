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

## Results

Outputs: `docs/science/assets/q032_synthetic_harness_2026-10-31/results/`
(code commit `134e31b`, 1,024 per-side rows, stride-2 production axes).

- **Scenarios.** Cavity pairs touch the nucleus and have an across/along
  semiaxis ratio of 0.6, with semiaxis a = 10, 20, 40, 60 or 90 kpc along the
  jet. True volumes run from 1.5e3 to 1.1e6 kpc³ per side.
- **Ratios.** Every ratio is the recovered volume divided by the true volume,
  using the revolution estimator. The median is taken over two atmospheres and
  two views. The minor-depth ellipse agrees within a few per cent wherever a
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
revolution volume is up to ×35. With a perfect background it ties at zero
deficit and selects an arbitrary region. **The legacy method is a fixed-area
selector, not a cavity detector.** Changing its background does not help.

**Evacuated cavities.** Partly filled (ρ = 0.3 ρ_amb) cavities give the same
numbers within 0.01–0.05, because a pressure-matched hot fill is nearly
X-ray dark at 1 keV.

| Method / background | a=10 | 20 | 40 | 60 | 90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Seed-and-grow / own polynomial | 0 (0/8 detected) | 0.16 (4/8) | 0.86 | 0.63 | 0.03 |
| Seed-and-grow / oracle | 1.00 | 1.00 | 1.00 | 1.00 | 0.70 |
| Deficit > 0.05 / oracle | 0.76 | 0.93 | 0.97 | 0.98 | 0.69 |
| Deficit > 0.10 / oracle | 0.22 | 0.73 | 0.89 | 0.93 | 0.68 |
| Deficit > null-calibrated / radial median | 0.27 | 0.74 | 0.88 | 0.90 | 0.61 |

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

**Compressed rims.** The rim is ×2 density, 0.15a thick and isothermal.

- In the cluster, the rim's projected emission fills much of the deficit.
  Seed-and-grow with a perfect background recovers 0.35–0.39 of the volume at
  a = 40–60 kpc; observer methods recover 0.03–0.34.
- In the group, the same rim costs only about 10% (0.90–0.95).
- The difference follows the projected contrast. The cluster core is flatter
  and more extended, so the cavity chord is a smaller fraction of the line of
  sight.

Bright shocked shells, which the high-power runs have, are therefore a
physical limit on any deficit-based cavity volume in the cluster. They are not
only a detector problem.

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

Recommendation for the next rung:

1. Retire the legacy selector.
2. Do not adopt seed-and-grow with its polynomial background as the
   replacement.
3. Carry the radial-median deficit threshold (null-calibrated) and the oracle
   seed-and-grow (t=0 background) forward to the retained maps, with aperture
   coverage reported per view.
4. Settle the aperture before the threshold: the 120 kpc limit truncates every
   late high-power cocoon.

## Limits

- The synthetic atmospheres are the initial tabulated profiles. They contain no
  boundary drift, no shocked-ambient shells beyond the simple rim, no
  turbulence and no Poisson noise. Null-calibrated thresholds therefore measure
  background-model error only.
- The oracle background is the matched cavity-free synthetic map. On simulation
  maps the equivalent is a t=0 XRAiSE render of each atmosphere and view, which
  does not yet exist.
- Tracer masks on real maps are evaluation references
  (`tr1 >= 1e-3` maximum along the line of sight), not cavity truth.

## Next

1. Run `build_q032_selected_age_method_ladder.py --base <retained root>` beside
   the 60 retained views and return its compact outputs.
2. Render t=0 XRAiSE maps for the cluster and group at 0/45/90 degrees for the
   oracle rung on simulation maps.
3. Add projected path-length maps (cocoon, shocked ambient, ambient total), per
   the interface in board message 2647, to test depth and shell filling
   directly.
4. Choose and validate the production replacement; flip the strict xfail;
   refresh pressure sampling, enthalpies, ages and powers.
