# Tracer at the grid faces and gravitational work outside the nozzle

Across 31 saved times in each of the four simulations, from startup through 30 Myr, **none of the 744 outer-face measurements contains any outward gas flow**. The nearest cell with jet tracer above 0.001 stays more than 100 kpc from a domain face throughout that interval. These two observations address different questions. The first fixes sampled outward transport even for very dilute jet gas. The second bounds how much tracer could enter with the inward flow. [All 201 saved times](assets/outer_tracer_gravity_2026-11-19/saved_tracer_clearance.csv)

| Case | Closest cell with tracer >0.001 through 30 Myr, kpc | Largest allowed cumulative tagged inflow through 30 Myr, % of labelled mass |
| --- | ---: | ---: |
| C-HI | 104.72 | 4.34 |
| C-LO | 187.51 | 434.12 |
| G-HI | 100.96 | 0.216 |
| G-LO | 186.97 | 21.59 |

Each minimum occurs at the final saved time in this interval. Distances run from the nearest edge of a selected cell to the nearest of six domain faces. Inflow limits use the most permissive of left, trapezoidal and right integration over the actual dump times. The inflow boundary copies adjacent primitives and can therefore transport subthreshold tracer into the box. At all later accepted times the gross outward gas rate also remains zero, with one exception. G-HI first shows outward flow and above-threshold tracer contact at 47 Myr. [Signed face-transport bounds](assets/tracer_mass_budget_2026-11-19/sampled_tracer_boundary_integral_bounds.csv)

## Gravity at 29–30 Myr

The saved energy records support a second estimate of the work done by gravity. For the volume outside a fixed nozzle box, let \(U_\Phi=\int\rho\Phi\,dV\) and \(F_\Phi=\oint\rho\Phi\mathbf v\cdot\mathbf n\,dA\). The surface integral takes the whole-grid face flux minus the nozzle-box face flux. For a static gravitational potential and mass conserved in that exterior, the continuity equation gives \(W_\Phi=-\Delta U_\Phi-\int F_\Phi\,dt\). Negative work means the gas has moved uphill overall. Both energies below use each interval’s labelled bipolar kinetic input, \(2P_{\rm jet}\Delta t\).

| Case | Inferred gravitational work, % of labelled input | Measured exterior total-energy balance, % of labelled input |
| --- | ---: | ---: |
| C-HI | −6.57 to −5.28 | −13.28 to −8.87 |
| C-LO | −4.17 to +124.54 | −190.11 to +61.37 |
| G-HI | −2.13 to −2.08 | −7.57 to −5.60 |
| G-LO | −8.46 to −3.75 | −2.90 to +5.63 |

These ranges span 36 matched choices of nozzle padding, nozzle and domain face reconstruction, and time integration. G-HI gives the clearest scale comparison. Its signed work is 27–38% of the absolute exterior balance under paired methods. In C-LO even the sign of the work is unresolved. With two cells of padding, centred nozzle primitives, outer active cells and trapezoidal time integration, C-LO’s change in potential-energy storage is +13.456 interval labels and its outward potential-energy transport is −13.644. The inferred work depends on their difference. [All 197 intervals and method ranges](assets/outer_tracer_gravity_2026-11-19/potential_work_intervals.csv)

Gravity transfers energy between kinetic and potential forms. The measured exterior balance already includes potential energy. A comparison of that balance with the signed physical work alone cannot identify a numerical gravity error. The source-free continuum identity also assumes closed mass accounting. Changing the zero of potential by \(C\) changes this work estimate by \(-C(\Delta M+\int F_m\,dt)\). The interval table gives this mass residual for the reference method and uses the project’s centre-zero potential.

## Comparison with the native fields

The native measurement evaluates \(W_v=\int dt\int\rho\,\mathbf v\cdot\mathbf g\,dV\) from saved cell-centre states. The four production environments use Cartesian gravity centred on the origin. Their source linearly interpolates the signed sixth atmosphere column at the spherical radius and multiplies by the Cartesian radial unit vector. The measurement reports signed work for inward and outward radial motion separately for the whole grid and inside and outside each of the three original fixed boxes with one, two and four padding cells. It uses the solver’s radius normalisation for interpolation and the existing flux ledger’s cgs conversions for mass, volume and velocity. [Native measurement](../../scripts/science/measure_outer_tracer_gravity.py)

Joining two consecutive native outputs to the earlier face records gives \(W_v-W_\Phi\) and the exterior energy balance less that difference, using the same box and time rule. The former compares the two ways of booking gravitational work. Face reconstruction, the 1-Myr sampling, finite spatial resolution and the common potential convention all enter the comparison. The retained PLUTO source applies directional gravity to the average of the **two numerical interface mass fluxes** at each solver stage. Replacing those fluxes by cell-centre momentum at saved times changes the quantity measured. Determining the actual gravity contribution to the solver’s energy error would require its stage-resolved mass fluxes and gravitational increments or an equivalent exact reconstruction. [Matched native comparison code](assets/outer_tracer_gravity_2026-11-19/replay_compact.py)

The same native pass measures the raw positive tracer, including float32 subnormals, its cell-edge clearance, and the tracer-weighted mass with \(0<{\rm tr1}<0.001\) within 20 kpc of a face. A boundary-straddling cell contributes its exact geometric overlap with the union of the six layers at its saved density and tracer fraction. Edges and corners enter the shell once. Each face separately reports its adjacent-cell tracer extrema, positive area, positive cell volume, and signed inward and outward mass rates from the actual density, tracer and normal velocity. Only adjacent native times enter transport integrals. Cumulative values require continuous coverage from startup. Sampling leaves possible excursions between dumps unconstrained.

The compact replay rechecks each retained total-energy balance and reconstructs 7,080 matched exterior intervals. The final G-HI endpoint supports 24 choices because linear outer-face extrapolation fails there. The left rule for that reconstruction needs only the 46-Myr face. The public input package contains the storage, flux and comparison records and their original receipt hashes. Adding `--native-root` with the native results root writes the direct work comparison and signed tracer transport tables. [Compact numeric inputs](assets/outer_tracer_gravity_2026-11-19/compact_inputs.zip)

```sh
python3 docs/science/assets/outer_tracer_gravity_2026-11-19/replay_compact.py \
  --output /tmp/xray-outer-gravity-review
```
