# Why the injector grid can supply excess jet mass

The subsequent production measurement identifies how much marked mass and gas energy crossed the injector at 19, 20, 29 and 30 Myr in all four runs. The steady fields below give the comparisons used to design that measurement. [Production injector results](production_injector_pilot_2026-11-19.md)

The jet-marked mass in the four production runs grew at 1.152–1.157 times the labelled mass rate during 29–30 Myr. The same excess can arise on the production grid when the jet expands into a smooth radial flow. The geometry has a specific effect. Each moving cap supplies gas through the sides of its grid cells as well as their ends. The gas outside those cells determines how much crosses. Its evolved pressure, density and velocity are the missing inputs to the energy measurement. [Production tracer census](tracer_mass_budget_2026-11-19.md) · [Four-case geometry and mass comparison](assets/injector_faces_2026-11-19/cap_reference_summary.csv)
<!-- claims: BND-10 BND-11 -->

## What crosses the discrete cap

The 0.75-kpc sphere contains 14,328 cells held at prescribed conditions. Of these, 504 belong to the moving, jet-marked cones. The sphere and its freely evolving surroundings share 4,296 faces. The moving caps account for 104 faces perpendicular to the jet axis and 64 side faces. The geometric centre of every one of those side faces falls outside the mathematical cone.

Evaluating a steady radial jet at the centres of the 104 axial faces gives **1.024 times** the analytic bipolar mass flux. The 64 side faces contribute a further **0.142**, bringing the total to **1.166**. Evaluating the radial flow at the centres of the donating cells instead gives 1.215. The factor is a property of the chosen footprint and where the radial field is evaluated. The continuum prescription itself supplies 0.9962–1.0000 of the mass implied by labelled power and speed. [Reproducible grid calculation](assets/injector_faces_2026-11-19/geometry_replay.py)

| Case | Measured tagged growth, 29–30 Myr | Cap flux in smooth radial flow | Cap flux with the cone continuing into a static atmosphere |
| --- | ---: | ---: | ---: |
| C-HI | 1.1554 | 1.1687 | 1.1471 |
| C-LO | 1.1568 | 1.1693 | 1.0269 |
| G-HI | 1.1516 | 1.1649 | 1.1454 |
| G-LO | 1.1541 | 1.1692 | 1.0865 |

All entries use the labelled bipolar mass rate. The first column uses the production tracer inventory and actual interval duration. The smooth control extends the prescribed radial gas state and tracer in all directions and counts only the 168 cap faces. The last column continues only the two jet cones, keeps the rest of the sphere stationary, and puts the original static atmosphere outside them. Both controls use the production reconstruction, shock switch and Riemann solver. Moving from one exterior to the other changes the inferred output most strongly in C-LO. [All sixteen control fields](assets/injector_faces_2026-11-19/compiled_manufactured_controls.csv)

An inward acoustic characteristic alone cannot establish extra mass or energy transfer. In a compiled PLUTO example, stationary gas at equal pressure on the two sides has a four-times-hotter exterior. The inward wave bound is −0.8165 in the test units. HLLC resolves the stationary contact with exactly zero mass and energy flux. Forcing the alternative HLL flux produces a marked-mass flux of 0.3062. The code measures separately the share of outward transport on faces with an inward wave, and the share on which a hotter exterior sets that inward bound. Both shares describe where transport occurs. Neither apportions its cause. [Compiled contact example](assets/injector_faces_2026-11-19/wave_counterexample.csv)
<!-- claims: BND-11 -->

## What the production test will measure

The primary diagnostic uses both sides of each flagged-to-free face, piecewise-linear primitive reconstruction with the minmod limiter, and the configured HD HLLC solver with its shock-triggered HLL fallback. We also evaluate first-order states and force each solver choice to measure sensitivity. First-order values can lie on either side of the linear values. Against the retained PLUTO C source, the implementation reproduced cap membership, shock decisions and inward-wave classifications on all 68,736 manufactured face problems. Its largest flux difference was 4.3 × 10⁻¹⁶ of the largest face flux for that quantity in that field. A separate check covered 2,400 two-sided states. The case headers and executable identities are traceable. The historical build did not record the complete core source tree. [Grid comparison](assets/injector_faces_2026-11-19/compiled_patch_comparison.json) · [Two-sided comparison](assets/injector_faces_2026-11-19/oracle_comparison.json)

The production reduction keeps signed mass, marked mass and gas energy for the caps and the stationary reservoir. It reports energy flux per outward gram on the faces carrying outward mass. A negative reservoir energy flux measures net absorption at that saved state. C-LO's inward all-gas flux on a larger box leaves the sign at the reservoir open. The cap and reservoir fluxes add to the transfer across the sphere. For the comparison with stored energy, we also include the potential transported with the mass and the change of energy inside the maintained cells. For tracer closure we compare the two regions' signed fluxes plus the change of marked mass inside the sphere, less the transport out of the grid, with the change in the whole-grid inventory. [Face solver](../../scripts/science/measure_injector_faces.py) · [Production reduction](../../scripts/science/reduce_injector_patches.py)

The archived records contain whole-grid and control-box sums. The original dumps hold the neighbouring cell values for the injector, the dilute tracer within 20 kpc of the domain faces, and the velocity for a direct gravity-work integral. Their native analysis is staged. No evolved cap specific energy, reservoir power, or net injector power has yet been recovered from it. The available whole-grid energy estimate for G-HI remains 7.8–8.0% above label. Saved primitives allow reconstruction at individual epochs. The internal Runge–Kutta stages and the 0.05-Myr terminal ramp between snapshots are absent. The observed final-interval mass-growth reductions of 3.12%, 3.18% and 3.10% agree with the prescribed 3.18% dip. [Final-interval mass check](assets/injector_faces_2026-11-19/late_tracer_change.csv) · [All saved face clearances and the gravity comparison](outer_tracer_gravity_2026-11-19.md)
<!-- claims: BND-08 BND-10 -->

## Reproduce

These commands run from the repository root. The first calculates the discrete cap area and flux factors from the published axis fixture. The second checks the fluxes, inward-wave fractions and shock-switch counts for all sixteen compiled control fields. The third rebuilds the tracer-clearance and potential-work tables from the archived production reductions.

```sh
python3 docs/science/assets/injector_faces_2026-11-19/geometry_replay.py
.venv/bin/python docs/science/assets/injector_faces_2026-11-19/replay_controls.py
python3 docs/science/assets/outer_tracer_gravity_2026-11-19/replay_compact.py --output /tmp/xray-outer-gravity-review
```

The independent C replay bundle is `private_solver_reference_r1.tar.gz`, SHA-256 `5aad7eee958d7f609dbf2f599fc5eeb10790bd93685920d0617825f51e920bd4`. After extracting it into a fresh directory, run the following command there with a NumPy-enabled project interpreter and a C compiler.

```sh
python private_archive/turn21_injector/solver_check/replay_reference.py --pluto-src reference_pluto/Src
```
