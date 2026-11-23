# Prospective entropy-switch test in the two low-power jets

Barry approved the C-LO and G-LO 10–12 Myr restart pairs on 23 November 2026. The estimate is approximately 13,000 core-hours for the four simulation arms. Claude recorded the quantitative predictions before this approval, in board message 3665. Message 3666 corrects two statements about the high-power spatial results and preserves the low-power forecasts. [Frozen forecast](../correspondence/thread-0029.md#message-3665--claudemini-claude-fable-52--evidence) · [High-power protocol](entropy_restart_protocol_2026-11-21.md)

## Quantities and tests

Each entry below is signed and normalized by the low-power bipolar label, 2 × 10⁴³ erg/s times the actual elapsed time. Positive values mean the numerical operation adds energy to the freely evolving gas. The first two columns use the native, RK2-weighted changes made by the switch outside maintained injector cells. For the last column we calculate the signed exterior residual from the storage and flux of the switch-off run, using the registered domain-face, injector and time rules.

| Case | Switch-on entropy change, 10–11 Myr | Switch-on entropy change, 11–12 Myr | Switch-off residual, each 0.1-Myr interval after the first |
|---|---:|---:|---:|
| C-LO, cluster | +0.030 ± 0.005 | +0.047 ± 0.005 | within ±0.002 |
| G-LO, group | −0.017 ± 0.005 | −0.022 ± 0.005 | within ±0.002 |

Claude also specified that a C-LO net below +0.01 refutes the switch as the source of its excess. Report both 1-Myr sums and the duration-weighted 10–12 Myr result alongside this threshold. Score the two annual predictions and all 19 post-startup intervals separately. Retain the first 0.1-Myr interval and the gross positive and negative changes in the tables. Sum energies in erg before dividing by actual labelled input. No measured low-power result enters this forecast.

## Checkpoints and controls

The archived integrator record for each 10-Myr state identifies double index 2, float index 10 and particle index 1000. The seed, its native float companion and the 11-Myr comparison file were present on 23 November. The two doubles each contain six float64 fluid fields on the 1014 × 960 × 960 production grid and are 67,318,639,276 bytes. Both production runs used 64 nodes with 28 MPI ranks per node.

| Case | 10-Myr seed step | Seed particles | 11-Myr production step | SHA-256 of 11-Myr reference float |
|---|---:|---:|---:|---|
| C-LO | 11,585 | 46,060 | 12,729 | `fc03993609b51ac4cb208ade551d2113fd1ddce24b32af3d55c151b0392097b6` |
| G-LO | 10,578 | 42,032 | 11,526 | `fa7d48233007223f29b274fbba07847579cb563654d42e397e06a25337ecaf8c` |

The paired experiment preserves the production geometry, build recipe and runtime inputs. Both switch-on simulations must complete and pass their own 11-Myr production comparisons before either switch-off simulation starts. Apply the high-power protocol's native float conversion, particle restoration and six-field checks. The full-grid component tolerance is 0.5% of the **low-power** 10–11 Myr labelled input, and the affected-region primitive tolerance is 1% of each original norm. Keep all 20 new native float outputs in each arm, the particle series, solver stage counters and final double checkpoint.

The registered primary budget uses piecewise-linear injector states with the configured shock flags, outer active-cell boundary states, centre-referenced potential energy and trapezoidal integration. Report other reconstruction choices as diagnostics of transfer from the high-power calibration. The low-power cluster boundary term is large in units of its own label, making the switch-off control especially important.

The high-power lobe follow-up uses existing outputs from the two previous pairs. It measures tracer-defined volume, $2.5\int p\,dV$, and the change in stored energy relative to production time zero inside each snapshot's current 100 km/s sphere. It measures the effect of changing the switch after age 10 Myr. Origins of the 30–50 Myr enthalpy fractions require observations or experiments at those ages.
