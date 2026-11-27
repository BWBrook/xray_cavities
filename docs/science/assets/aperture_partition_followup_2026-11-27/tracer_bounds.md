# Archived tracer checks at 30 Myr

The G-HI ambient thermal gain inside R100 rises from 31.4% of net injector delivery under the published binary mask to **47.57–47.82%** when each cell's thermal change receives weight `1 − tr1`. The interval follows from the archived pressure and tracer sums. C-HI and G-LO also increase under the continuous assignment. In C-LO the interval contains the binary result.

| Case | Whole-grid share of tracer mass in cells with tr1 ≤ 0.001 | R100 ambient thermal gain, binary (% of delivery) | R100 ambient thermal gain, continuous bounds (% of delivery) |
|---|---:|---:|---:|
| C-HI | 0.529% | 51.50 | 56.91–59.61 |
| C-LO | 1.657% | 91.37 | 86.70–96.46 |
| G-HI | 0.427% | 31.40 | 47.57–47.82 |
| G-LO | 1.415% | 66.13 | 68.74–80.55 |

Interval endpoints are rounded outward. The denominator for thermal gains is cumulative net gas energy delivered through the injector at the actual snapshot time. Thermal change compares the pressure of the same cells at the current age and time zero using the current tracer mask or weight. Gravitational potential does not enter this component. Continuous weighting is a convention for assigning the cell's thermal energy in proportion to its mass tracer. The simulation stores one pressure per cell and does not track the heat of jet and atmospheric material separately.

## Tracer mass

The four native outer-tracer receipts in `outer_30myr.zip` contain the full-grid integrals of `rho × tr1 × V` for all positive tracer and for `0 < tr1 < 0.001`. Each case's precision receipt records zero cells exactly equal to 0.001 when the stored floats are promoted to double precision. Each aperture encloses every cell above that threshold. Any tracer beyond the aperture therefore reduces the dilute numerator and the total denominator by the same mass when restricting the count to R100. The whole-grid shares are exact native totals up to summation precision and give upper limits for the corresponding shares inside R100. A tracer-mass share alone does not specify local thermal energy.

## Bounds on the pressure-weighted tracer

For each of the two pressure fields, write `u = p/(γ − 1)`, `F = Σ tr1 u V` for the whole grid, `T = Σ u V`, and `B(a) = Σ u V` over cells with `tr1 > a`. The selected-age census gives all of these using centre-derived cell widths and the same current tracer. Each of the three binary cohorts is enclosed by R100. Inside the sphere the positive tracer-weighted thermal energy is therefore at least

```text
0.001 B(0.001) + 0.004 B(0.005) + 0.005 B(0.01).
```

Since all exterior cells have `tr1 ≤ 0.001`, the enclosed amount is also at least `F − 0.001 [T − B(0.001)]`. Its upper limit is `F`. For the exact native volumes, multiply the larger lower limit by the minimum cellwise native-to-centre-derived volume ratio (0.9943281) and the upper limit by the maximum (1.0126177). The common grid is identified by the axes hash in each case's aperture registration.

Let the resulting intervals be `[L_now, U_now]` and `[L_initial, U_initial]`. Subtracting the tracer-assigned change from the measured all-cell R100 thermal change `S` gives the continuous ambient interval `[S − U_now + L_initial, S − L_now + U_initial]`. Positivity applies to each pressure inventory separately. No sign assumption is made about pressure changes inside or outside the aperture.

An exact continuous R100 value requires its tracer-weighted pressure change. The archived cross moment covers the whole grid. The stricter binary mask requires the same-cell pressure change specifically in `0.0001 < tr1 ≤ 0.001` inside R100. The archived binary census has its lowest threshold at 0.001. Both exact contrasts can be recovered with a native snapshot read.

## Reproduction

Run `python scripts/science/bound_ambient_tracer_partition.py` in the repository environment. The script joins the released aperture registration and sphere stocks, selected-age pressure moments and precision tables, native axes, and the four original outer receipts. With a local copy of `production_injector_201.tar.gz`, pass `--source-archive PATH` to verify its SHA-256 against the production release and compare all four packaged receipts byte for byte. Full precision and receipt identities appear in [thermal_tracer_30myr.csv](thermal_tracer_30myr.csv).
