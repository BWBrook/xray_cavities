# Three cavity clocks on native lobe geometry

All three clocks gave ages longer than the elapsed source age on every one of 38 lobe sides. Even with the simulated pressure and volume supplied, the median bipolar powers were **20.1% of mean jet delivery for sound crossing, 25.4% for buoyant rise and 9.3% for refill**. These medians give equal weight to each of the 19 case-ages. The jets were active over the measured histories, and the four runs each provide one realisation. [All side ages and powers](assets/native_clocks_2026-11-28/side_clocks.csv) · [Bipolar powers, true-age controls and delivery](assets/native_clocks_2026-11-28/bipolar_powers.csv)

| Native clock | Effective age / true age, median (range) | Bipolar power / mean delivery, median (range) |
|---|---:|---:|
| Sound crossing | 2.55 (1.37–6.86) | 20.1% (6.3–72.1%) |
| Buoyant rise | 2.41 (1.30–5.51) | 25.4% (7.8–52.6%) |
| Refill | 5.50 (2.03–17.61) | 9.3% (2.4–48.7%) |

At 30 Myr, enthalpy divided by the **true age** gives the first power column below. The remaining columns substitute each clock, giving its effective age in Myr and its fraction of the same mean delivered power. The labelled bipolar kinetic powers are $2\times10^{45}$ erg/s for HI and $2\times10^{43}$ erg/s for LO. Both absolute powers and label-normalised comparisons are in the full table.

| Case | True-age power | Sound crossing | Buoyant rise | Refill |
|---|---:|---:|---:|---:|
| C-HI | 47.1% | 70.5 Myr · 20.1% | 55.6 Myr · 25.4% | 165.1 Myr · 8.6% |
| C-LO | 87.1% | 58.8 Myr · 44.5% | 94.2 Myr · 27.8% | 89.8 Myr · 29.1% |
| G-HI | 40.4% | 159.4 Myr · 7.6% | 95.0 Myr · 12.8% | 294.7 Myr · 4.1% |
| G-LO | 66.7% | 60.6 Myr · 33.0% | 52.0 Myr · 38.5% | 146.8 Myr · 13.6% |

## Geometry, ages and powers

The selected snapshots are near 10, 20, 30, 40 and 50 Myr in C-HI, C-LO and G-LO, and near 10, 20, 30 and 40 Myr in G-HI. We used the actual output time throughout. For each hemisphere we selected the full volume of every native cell with jet tracer greater than 0.001. We measured its volume $V$, distance $R$ from the source to its volume centroid, and enthalpy $H_s=2.5\sum p_i\,\Delta V_i$. All 38 sides fit within the simulation domain. The largest centroid inclination to the outward jet axis was 0.671°. [Native reader](../../scripts/science/measure_native_clock_geometry.py) · [Original site receipts](assets/native_clocks_2026-11-28/native_receipts.zip)

For the drag area $S$ we used the largest occupied cross-sectional area in any one plane perpendicular to the bipolar axis. Disconnected occupied patches in the same plane contribute their actual areas. The effective lobe radius is $r_{\rm eff}=(3V/4\pi)^{1/3}$. We evaluated the three prescriptions separately at the centroid distance, using the sound speed and hydrostatic acceleration of the corresponding native time-zero atmosphere. The drag coefficient is 0.75. [Stas’s clock definitions](../exchange/logs/2026-11-25-cavity-age-scope-without-radio-ageing.md) · [Initial atmospheres](assets/native_clocks_2026-11-28/initial_atmospheres.csv)

$$
t_{\rm sound}=R/c_s(R),\qquad
t_{\rm buoy}=R\sqrt{0.75S/[2g(R)V]},\qquad
t_{\rm refill}=2\sqrt{r_{\rm eff}/g(R)}.
$$

We summed the two side powers for each clock $j$. Their effective age $t_{j,\rm eff}$ is the enthalpy-weighted harmonic mean of the side ages. The reference power is the reconstructed cumulative net **gas** energy passed through the injector, $D$, divided by true elapsed time $t$. This accounts for signed exchange through the moving and stationary parts of the injector. The following identity separates the effect of enthalpy from the effect of age. [Delivery definition and limits](native_delivery_restatement_2026-11-21.md)

$$
Q_j=\sum_s H_s/t_{j,s},\qquad
t_{j,\rm eff}=\frac{\sum_s H_s}{Q_j},\qquad
\frac{Q_j}{D/t}=\frac{\sum_s H_s}{D}\,\frac{t}{t_{j,\rm eff}} .
$$

With the $4pV$ comparator, every power increases by 1.6 and every age is unchanged. One of the 57 powers then exceeds mean delivery, the sound-crossing estimate for C-LO at 50 Myr (115.4%). The age excess holds in every case under either enthalpy convention.

For an irregular lobe, the area exposed to drag can also be represented by its entire silhouette along the outward axis. Counting every occupied transverse column once lowers the median buoyant power from 25.4% to **24.0%** of delivery. The largest reduction in an individual bipolar estimate is 8.0% relative. The primary drag formula formally predicts a terminal speed above the local sound speed on 23 of 38 sides. We used the prescribed formula throughout. Its terminal speed is a model estimate in these actively driven lobes. [Geometry sensitivity and independent recomputation](assets/native_clocks_2026-11-28/clock_review.json)

## X-ray eligibility

We retained the DET-05 requirements of at least 75% lobe area coverage, at least 95% purity and no contact with the 120-kpc aperture. Each image-only rule passed **0 of 108 sides** in the 54 held-out views. Consequently there are **zero qualifying observer estimates** of sound-crossing, buoyant-rise or refill power. G-HI/20 supplied the three development views. It contributes to the native comparison and sits outside the held-out eligibility count. [Eligibility by case, age and method, including nondetections and aperture contacts](assets/native_clocks_2026-11-28/xray_eligibility.csv)

For context, the simulation-assisted seed-and-grow and radial arms passed 6 and 13 sides respectively. Both sides passed in 3 and 6 views. These methods use the simulated gas to change the brightness used for fitting the background. Their scores describe an assisted experiment. [Held-out protocol and scores](heldout_xray_results_2026-11-24.md)

## Verification and replay

All 19 entries in PBS array 885822 exited zero. They read existing production tracer and pressure fields and used 0.652 reserved core-hours in total. The receipt preserves each source binding and each result checksum. Independently, summing the archived path-length images at two perpendicular azimuths recovers the native volume and cross-sectional profile. The historical per-side pressure integrals also bound the exact new side enthalpies. The second calculation reconstructed delivery from the time series of injector rates, formed the three clocks independently from the initial density and pressure profiles, and reproduced all 57 powers within $2\times10^{-14}$ relative. Substituting the original prescribed radial atmosphere for the measured initial-grid profile changes individual ages by at most 0.060%. [Jobs and hashes](assets/native_clocks_2026-11-28/native_run.json) · [Orthogonal profiles and historical pressure check](assets/native_clocks_2026-11-28/ortho_geometry.csv) · [Independent verifier](../../scripts/science/review_native_cavity_clocks.py)

Run these commands from the repository root to reproduce the tables and independent check.

```sh
.venv/bin/python scripts/science/native_cavity_clocks.py
.venv/bin/python scripts/science/review_native_cavity_clocks.py
```

The main replay uses the archived native receipts and compact initial atmospheres. The independent verifier starts from the retained initial density and pressure. Its optional `--axial-archive` checks those columns against the original time-zero profiles. The projection route can be replayed separately with `--archive-only` and a separate output directory. The [projection reader](../../scripts/science/check_native_clock_projections.py) identifies its inputs by the hashes in the [projection manifest](assets/native_clocks_2026-11-28/ortho_geometry_sources.json).

For a fresh native extraction, the reader takes `--stage` pointing to the registered 26 November transport stage, plus `--case`, `--index` and `--output`. It checks the registered snapshot and native axes before integrating pressure and tracer. The [PBS array](../../scripts/kunanyi/native_clock_geometry.pbs) lists the exact case and output assigned to each of its 19 tasks.
