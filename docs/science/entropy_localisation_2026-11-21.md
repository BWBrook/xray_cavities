# Where is the exterior energy deficit?

At 10–12 Myr G-HI has a reconstructed exterior deficit of 9.21% of the labelled jet input. The first 0.10 kpc outside the injector accounts for 2.25 percentage points in the primary reconstruction. The other 6.96 points fall outside 0.85 kpc. Every combination of the four injector-flux reconstructions, three time rules and two domain-boundary reconstructions leaves a deficit beyond 0.85 kpc. The retained data locate part of the discrepancy but do not record the entropy switch's energy exchanges. [Fixed-shell balances](assets/entropy_localisation_2026-11-21/entropy_localisation_near_spheres.csv)

## How large is gravitational work?

The work and the residual cover exactly the same cells, all active cells outside the flagged 0.75-kpc sphere. The work is the signed volume integral of density times velocity dotted with gravitational acceleration. The residual is the change in thermal, kinetic and gravitational energy, plus outward transport through the domain faces, minus net transport out of the injector. The primary estimates use linear reconstruction with the saved pressure-shock proxy for HLL fallback, outer active cells at the domain faces and trapezoidal time integration. The combined 10–12 Myr row uses the sum of the interval energies before division.

| Case | Myr | Net work (% of label) | Residual (% of label) | Absolute work / absolute residual | Range across matched choices |
| --- | --- | ---: | ---: | ---: | ---: |
| C-HI | 10–11 | −1.398 | −4.619 | 0.303 | 0.109–0.307 |
| C-HI | 11–12 | −1.625 | −4.610 | 0.352 | 0.128–0.361 |
| C-HI | 10–12 | −1.512 | −4.615 | 0.328 | 0.119–0.334 |
| C-HI | 29–30 | −6.282 | −12.108 | 0.519 | 0.318–0.529 |
| G-HI | 10–12 | −0.790 | −9.213 | 0.086 | 0.049–0.090 |
| G-HI | 29–30 | −2.104 | −8.399 | 0.250 | 0.144–0.254 |

Across all 50 C-HI intervals and 24 matched choices, the largest ratio is 0.569 at 33–34 Myr. Replacing net work with the sum of the absolute inward- and outward-motion contributions raises the maximum to 0.659 at 48–49 Myr. In G-HI the corresponding maxima are 0.378 and 0.394. Gravity alone would therefore require errors exceeding even this sampled gross work. In C-HI the size argument is weaker than in G-HI at the proposed restart age. C-HI's exterior deficit is also smaller at 10–12 Myr than G-HI's, then grows larger by 29–30 Myr. [All intervals](assets/entropy_localisation_2026-11-21/entropy_localisation_gravity_ratio.csv)

The direct work minus the work inferred from changes in potential energy and potential transport is +0.0223% of labelled input in C-HI at 10–12 Myr, and +0.0566% at 29–30 Myr. Those differences amount to 0.48% and 0.47% of the respective residuals. They check agreement between two calculations on saved states. A bound on errors in PLUTO's gravity update would require the energy increment actually applied at each solver stage. The formal order of the update gives no quantitative bound at this resolution. [Exact exterior comparison and input tables](assets/production_injector_histories_2026-11-21/history_tables.zip)

## What the fixed shells resolve

The retained native patches enclose complete, cell-centre spheres at 0.75, 0.80 and 0.85 kpc, with a complete reconstruction stencil outside each. For each fixed cell the calculation adds its change in total energy to the time-integrated net outward transport of gas energy and gravitational potential energy. Shared faces cancel when adjacent cells are summed. Subtracting the 0.75–0.85 kpc shell residual from the matched full exterior residual gives the result beyond 0.85 kpc. Here and throughout, positive outward transport offsets a decline in stored energy.

| Case | Myr | 0.75–0.85 kpc (% of label) | 12-choice range | Beyond 0.85 kpc (% of label) | 24-choice range |
| --- | --- | ---: | ---: | ---: | ---: |
| C-HI | 10–12 | −2.248 | −8.123 to −2.248 | −2.366 | −4.490 to −1.934 |
| C-HI | 29–30 | −2.248 | −8.123 to −2.248 | −9.860 | −12.022 to −9.409 |
| G-HI | 10–12 | −2.253 | −8.112 to −2.253 | −6.960 | −7.134 to −6.952 |
| G-HI | 29–30 | −2.253 | −8.112 to −2.253 | −6.146 | −6.319 to −6.138 |

The primary 0.75–0.85 kpc deficit splits about 1.88 percentage points in the inner 0.05 kpc and 0.37 points in the outer 0.05 kpc in both cases. The net and gross gravitational work in that shell each have magnitude 4.1–4.2 × 10⁻⁸ of the labelled input at both ages. The reconstructed shell deficit is more than 500,000 times that sampled work. The near-injector signal hardly changes between the two ages. Most of the age dependence in C-HI occurs farther out. The variation between face reconstructions shows how uncertain the near-shell amplitude is. Errors shared by the reconstructed fluxes remain possible. Endpoint quadrature also matters during ignition. In the first 0–1 Myr interval it places a large apparent loss in the near shell and a compensating gain farther out. [Storage, signed flux and reconstruction ranges](assets/entropy_localisation_2026-11-21/entropy_localisation_near_spheres.csv)

For the three individual intervals 10–11, 11–12 and 29–30 Myr in each case, 464 of the 6,344 cells in the near shell have intermediate tracer concentration at both saved endpoints, defined here as `0.001 < tr1 < 0.999`. They account for 99.1% of the primary signed near-shell residual, and 69.1–99.1% across reconstructions. Requiring a much stronger mixture, `0.1 < tr1 < 0.9` at both endpoints, leaves 256 cells in C-HI and 240 in G-HI. These still account for 95.9% and 95.4% of the respective primary shell residuals. The other 5,880 cells in the original three-class split divide into 5,672 with `tr1 ≤ 0.001` and 208 with `tr1 ≥ 0.999` at both endpoints. No cell changes category between those endpoints. Each category includes flux across all of its cell faces, including its interfaces with the other tracer classes. This locates a mismatch in fixed cells containing partly marked gas near the injector. The gas flowing through those cells and its tracer concentration can change between outputs. The shock flag used for HLL selection is separate from the code path that reconstructs energy from entropy. [Tracer-resolved cell balances](assets/entropy_localisation_2026-11-21/entropy_localisation_near_tracer.csv)

## What the wide apertures measure

At each of 10, 11, 12, 29 and 30 Myr in both cases, the complete 300-km/s sphere contains every cell with `tr1 > 0.001`. The outermost cell reaching 100 km/s lies only 0.013–0.328 kpc farther out. The ambient gas between the two spheres accounts for at most 0.00070% of the cumulative labelled input in initial-to-current stored energy. The broader storage partition is substantial. At 30 Myr, for example, G-HI's cells with `tr1 > 0.001` inside the 300-km/s sphere store 0.451 labelled inputs above their initial energy, and the complementary cells store 0.629. In C-HI the corresponding values are 0.227 and 0.856. The table includes the corresponding mass changes because regional gravitational energies depend on the potential zero. [Mass and energy by speed sphere and tracer](assets/entropy_localisation_2026-11-21/entropy_localisation_large_spheres.csv)

These snapshots give stocks in an aperture defined anew at each time. Material, pressure work and energy move between the lobe and shell, and a cell can enter an aperture or cross a tracer threshold. Measuring a local sink requires either a direct record of the energy operation or a balance that accounts for every boundary flux and change in membership. The wide-aperture stocks cannot distinguish a loss inside the cocoon from energy carried into the shell.

## Localising the effect in the paired restarts

The matched ON/OFF difference in the full exterior balance measures the total effect of changing the entropy switch once the ON restart reproduces its production control. To identify the cells where the switch itself adds or removes energy, accumulate the signed conservative gas-energy change immediately across its entropy-to-energy operation, by fixed radius and tracer concentration at that operation. Count and measure pressure or density repairs separately, with the effective weight of each accepted Runge–Kutta stage and active physical cells only. A radial sum can then be tested against the change in the whole exterior residual, with actual face transport, gravity and injector overwrite recorded separately. A difference between two late snapshots alone also incorporates the downstream changes in gas motion and pressure.

## Reproduction

Run from the checkout. The first command uses the verified public archive only. The second also reads the retained production patches, case requests, atmosphere tables and pre-existing fixed-aperture receipts. The script accepts `--native`, `--requests` and `--fixed` for their locations.

```shell
.venv/bin/python scripts/science/entropy_localisation.py /tmp/entropy_localisation_public --gravity-only
.venv/bin/python scripts/science/entropy_localisation.py /tmp/entropy_localisation_all
.venv/bin/python -m pytest -q tests/test_entropy_localisation.py tests/test_measure_injector_faces.py
```

The calculation verifies the archived source tables, the 99 high-power patches against their published SHA-256 digests, and the ten native stock receipts against their frozen records. The cellwise outward sum at the injector agrees with the archived 396 surface rates to within 3 × 10⁻¹⁵ of the labelled power. At 0.80 and 0.85 kpc an independent surface-only sum agrees to within 3.1 × 10⁻¹⁵ across 64 checks covering both cases at 0, 10, 12 and 30 Myr and all four face reconstructions. The regression test checks the sign and magnitude of each cell's transport in a constant flow through an analytic quadratic potential. [Reduction script](../../scripts/science/entropy_localisation.py) · [Analytic check](../../tests/test_entropy_localisation.py)
