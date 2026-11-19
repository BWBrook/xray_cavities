# Where excess jet mass crosses the injector

Across four production simulations, the side faces of the cells that inject the jet carried **79.9–81.9% of the excess marked-mass flux above the label**. The 104 faces perpendicular to the jet axis already supplied 1.027–1.032 times the prescribed mass rate at 30 Myr. The 64 lateral faces added 0.124–0.128. Their centres fall outside the mathematical cones. The evolving simulations thus carry most of the extra gas across the sides of the grid cells used to represent the cones. [Production face measurements](assets/production_injector_pilot_2026-11-19/cap_direction_and_waves.csv) · [Grid geometry and steady-flow controls](injector_faces_2026-11-19.md)
<!-- claims: BND-11 BND-12 -->

## What the injector delivered

The table gives fluxes averaged over the saved states at 29 and 30 Myr. Energy columns use the labelled bipolar kinetic energy over the actual interval. Marked mass uses the mass that this label and a jet speed of 0.1c imply. A negative stationary-region entry measures energy absorbed from the surrounding gas.

| Case | Gas energy from jet cones | Gas energy from stationary region | Net gas energy | Net marked mass at injector | Marked mass gained on whole grid |
| --- | ---: | ---: | ---: | ---: | ---: |
| C-HI | 1.1606 | +0.0014 | 1.1620 | 1.1553 | 1.1554 |
| C-LO | 1.1577 | −0.0216 | 1.1361 | 1.1567 | 1.1568 |
| G-HI | 1.1569 | +0.0014 | 1.1584 | 1.1516 | 1.1516 |
| G-LO | 1.1587 | −0.0034 | 1.1553 | 1.1540 | 1.1541 |

The outgoing cone gas carried 4.493–4.515 × 10¹⁸ erg per gram at the 16 sampled epochs, within 0.47% of the nominal kinetic energy per gram. The stationary region absorbed 2.16% of labelled power in C-LO and 0.34% in G-LO over 29–30 Myr. It supplied about 0.14% in each high-power case. At 19–20 Myr its contribution had the same sign in every case. Across all eight case-intervals the net marked transfer plus the change of tracer stored inside the injector agreed with the independent whole-grid census to within 0.00018 of labelled mass, before applying any outer-boundary correction. [Signed gas and mass rates](assets/production_injector_pilot_2026-11-19/signed_rates.csv) · [All primary interval balances](assets/production_injector_pilot_2026-11-19/signed_intervals.csv)

An independent build of the PLUTO solver found both wave speeds directed outward on every one of the 2,688 cone face measurements. Each face therefore used the reconstructed jet-side state. The hot exterior controlled an inward wave on zero sampled cap faces, and the shock switch selected HLL on zero cap faces. Neighbouring gas can still affect the slope used to reconstruct the jet-side state. [Face directions, wave bounds and mass split](assets/production_injector_pilot_2026-11-19/cap_direction_and_waves.csv)

## Energy outside the injector

Subtracting the net injector transfer and the energy change inside its maintained cells from the whole-grid source gives the following exterior balances. Each pair uses the outermost active cell and a linear extrapolation to the physical boundary, respectively. Each uses the same simulated injector, potential convention and trapezoidal time rule.

| Case | 19–20 Myr, % of labelled input | 29–30 Myr, % of labelled input |
| --- | ---: | ---: |
| C-HI | −9.00 / −10.58 | −12.11 / −13.71 |
| C-LO | +13.65 / −144.86 | +15.40 / −144.58 |
| G-HI | −6.85 / −6.91 | −8.40 / −8.45 |
| G-LO | +4.49 / −1.07 | +3.61 / −1.86 |

In G-HI the independently checked injector delivers about 16% above label at the sampled times. A negative balance remains outside it under both boundary reconstructions and all three time rules. The two pilot intervals and the previously measured 7.8–8.0% cumulative whole-grid excess describe different time spans. C-HI also has a negative exterior balance. The strong boundary inflow in the low-power runs makes even the sign depend on how energy transport at the outer boundary is estimated. [Complete production tables, including the sensitivity calculations](assets/production_injector_pilot_2026-11-19/pilot_tables.zip) · [Cumulative G-HI whole-grid record](ghi_flux_endpoint_2026-11-19.md)

For the same G-HI exterior and the same 29–30 Myr interval, the change in stored gravitational potential energy and its transport imply gravitational work of −2.09% to −2.12% of labelled input with trapezoidal weighting. The corresponding total-energy residual is −8.40% to −8.45%. The total-energy balance already counts the potential energy gained by gas moving uphill. Testing for a numerical error in the gravity update therefore requires comparing two independently evaluated work terms. The full histories measure the second term, the volume integral of force times velocity, at each saved time. [Matched potential and residual measurements](assets/production_injector_pilot_2026-11-19/flagged_sphere_gravity_intervals.csv) · [Exact-volume comparison](../../scripts/science/compare_injector_gravity.py)

## Scope and reproduction

The pilot read indices 19, 20, 29 and 30 from all four production histories. For each snapshot the primary calculation reconstructed the state on both sides of all 4,296 injector faces with the production piecewise-linear limiter, shock switch and HLLC solver. Applying first-order reconstruction instead raises the pilot net gas energy to 1.185–1.222 times label. The archived tables retain first-order, forced-HLL and forced-HLLC calculations as sensitivity tests. The saved primitive states omit intermediate Runge–Kutta stages and rapid changes between outputs. Exact solver-step delivery and the physical origin of the exterior residual therefore remain open.

Across 68,736 interface measurements the independent PLUTO C implementation reproduced every wave and fallback classification. Its largest face-flux difference was 3.28 × 10⁻¹⁶ of the largest face flux in the corresponding field. It reproduced the eight interval budgets under left, right and trapezoidal weighting to within 3.34 × 10⁻¹⁵ of label. Using the original grid coordinates instead of the floating-point coordinates stored in the outputs changed zero wave or fallback classifications and shifted signed regional gas power by at most 7.57 × 10⁻⁸ of label. The executable and case headers are traceable. The provenance of the C core comes from the retained source revision and manifest. [C comparison receipt](assets/production_injector_pilot_2026-11-19/public_comparison_receipt.json) · [Coordinate sensitivity](assets/production_injector_pilot_2026-11-19/native_mesh_sensitivity.csv) · [Independent local replay of the PBS tables](assets/production_injector_pilot_2026-11-19/scheduler_pilot_replay.json)

Run the following from the repository root to verify the archived production tables, match the signed rates to the independent C reduction, and print both interval budgets. The native reconstruction uses the 16 source-bound cutouts preserved with the project. [Run and archive record](../exchange/logs/2026-11-19-production-injector-pilot.md)

```sh
python3 docs/science/assets/production_injector_pilot_2026-11-19/replay.py
```
