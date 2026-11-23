# The entropy update adds energy to the low-power cluster jet and removes it in the group

Both low-power restart pairs reproduced their production controls and completed at 12 Myr. Over 10–12 Myr the solver’s entropy update added **3.884% of labelled input** to the gas outside the maintained injector in C-LO and removed **1.961%** in G-LO. The earlier high-power pairs showed losses of 4.615% in C-HI and 9.213% in G-HI over the same ages. The numerical correction can therefore have either sign, even at the same jet power. [Frozen low-power protocol](low_power_entropy_restart_protocol_2026-11-23.md) · [High-power budgets](entropy_restart_result_2026-11-22.md)

## How the forecasts scored

Each percentage uses the case’s labelled bipolar power, $2\times10^{43}$ erg s$^{-1}$, times the actual elapsed time. Positive values denote a net addition by the switch. The switch-on measurement sums its signed energy changes at each accepted solver stage. The switch-off comparison reconstructs the exterior balance independently from energy storage, delivery across the injector surface and transport through the grid boundary.

| Case | Age (Myr) | Forecast range (% of label) | Measured switch-on correction (% of label) |
| --- | ---: | ---: | ---: |
| C-LO | 10–11 | +2.5 to +3.5 | +3.058 |
| C-LO | 11–12 | +4.2 to +5.2 | +4.709 |
| G-LO | 10–11 | −2.2 to −1.2 | −1.747 |
| G-LO | 11–12 | −2.7 to −1.7 | −2.175 |

All four predictions fell within their registered bands. C-LO exceeded the separate +1% refutation threshold in both 1-Myr windows and across the full experiment. With the switch off, **all 38 scored 0.1-Myr intervals** lay within the registered ±0.2% band. The largest absolute residual was 0.0297% of its interval’s label in C-LO and 0.0263% in G-LO. The excluded first intervals are retained in the table and measured −0.1085% and −0.0984%, respectively. [Switch-on scores](assets/low_power_entropy_result_2026-11-23/on_counter_windows.csv) · [All 40 switch-off intervals](assets/low_power_entropy_result_2026-11-23/off_interval_scores.csv)

| 10–12 Myr, percent of labelled input | C-LO | G-LO |
| --- | ---: | ---: |
| Energy added by entropy recovery, summed over positive cell visits | +30.378 | +35.958 |
| Energy removed, summed over negative cell visits | −26.494 | −37.920 |
| Net entropy change, switch on | +3.8837 | −1.9613 |
| Reconstructed exterior balance, switch on | +3.8843 | −1.9613 |
| Reconstructed exterior balance, switch off | +0.0188 | +0.0197 |

The distinction between the two atmospheres is visible in jet-rich gas. In gas containing more than 50% jet material, entropy recovery removed 10.22% of labelled input in C-LO and 15.92% in G-LO. Gas with 0.5–50% jet material gained almost the same amount in the two runs, 12.53% and 12.58%. These are sums over cell visits classified when the solver changed their energy. The sums cannot establish how much ambient gas was permanently heated. With the switch off, ordinary pressure-floor repairs added 0.0244% and 0.0258% of label in C-LO and G-LO, respectively. The corresponding native entropy counters were zero. [Energy components and transport](assets/low_power_entropy_result_2026-11-23/budget/primary_windows.csv) · [Stage tables and tracer bins](assets/low_power_entropy_result_2026-11-23/compact_inputs.zip)

The C-LO control is particularly informative. Across the two Myr the grid stored 11.384 units of labelled energy while the integrated outward boundary flux was −10.228 units. After the much larger boundary inflow and the injector’s delivery are accounted for, the remaining +0.038843 agrees with the solver’s independently counted +0.038837. The difference between methods is 0.00057 percentage points of labelled input in C-LO and 0.000016 points in G-LO. [Interval balances](assets/low_power_entropy_result_2026-11-23/budget/primary_intervals.csv) · [Independent verification](assets/low_power_entropy_result_2026-11-23/independent_verification.json)

## How much of the difference appears in the lobe?

After scoring the forecasts we measured pressure and volume in the two shared 10-Myr seeds and all four low-power 12-Myr endpoints. The table uses the same quantity in all four runs: the increase in $2.5\int p\,dV$ in the tracer-defined lobe divided by the gas energy delivered in that arm during 10–12 Myr. The last column compares absolute lobe enthalpies at 12 Myr. The primary lobe includes cells with more than 0.1% jet material by mass. [Low-power lobe measurements](assets/low_power_entropy_result_2026-11-23/lobe_measurements.csv) · [High-power interval calculation](assets/entropy_lobe_review_2026-11-23/summary.json)

| Case | Enthalpy gain / delivered gas energy, switch on | Switch off | Change in absolute 12-Myr enthalpy, off vs on |
| --- | ---: | ---: | ---: |
| G-HI (group) | 41.69% | 51.14% | +3.56% |
| G-LO (group) | 67.62% | 72.59% | +1.46% |
| C-HI (cluster) | 50.77% | 63.43% | +4.25% |
| C-LO (cluster) | 89.40% | 88.83% | −0.21% |

In C-LO the sign of the small lobe response depends on where the lobe edge is drawn. Raising the tracer threshold to 0.5% and 1% changes the 12-Myr enthalpy contrast to +0.064% and +0.362%. The corresponding changes in the intervention-window ratio are −0.575, +0.397 and +1.285 percentage points across the three cuts. In G-LO the ratio rises at every cut, by 4.97 to 6.35 percentage points. Thus C-LO shows a clear numerical addition to the gas outside the injector alongside a small, boundary-sensitive lobe enthalpy contrast. Each case has one restart pair. These measurements cover the two Myr after the common checkpoint and leave the difference at 20–50 Myr open. [Threshold comparisons and both denominators](assets/low_power_entropy_result_2026-11-23/lobe_paired_effects.csv) · [Native source and rate checks](assets/low_power_entropy_result_2026-11-23/lobe_verification.json)

## Controls and public replay

The 11-Myr controls reproduced every value in all six production fluid fields in both cases. The four arms retained all 20 new native states, 201 particle files including the seed and a final double checkpoint each. All seven PBS jobs and all 16 measurement workers finished with exit 0. The published inputs include 82 grid and 82 injector measurements, the two production controls and the stage reductions from 405,171 native ledger rows. A separate calculation reconstructed all 80 exterior budgets from the saved stocks and signed fluxes, and checked the raw positive and negative solver corrections with their native run-stage weights. The largest difference between the two exterior calculations was $4.31\times10^{-15}$ of labelled input. [PBS and native receipts](assets/low_power_entropy_result_2026-11-23/pbs-completion.json) · [Public replay program](../../scripts/science/replay_low_power_entropy.py) · [Independent implementation](../../scripts/science/verify_low_power_entropy.py)

From the repository root, use a new or empty output directory. The compact ZIP reproduces the six budget tables and three forecast products byte for byte.

```sh
inputs=docs/science/assets/low_power_entropy_result_2026-11-23/compact_inputs.zip
out=$(mktemp -d)
.venv/bin/python scripts/science/replay_low_power_entropy.py replay "$inputs" "$out"
.venv/bin/python scripts/science/verify_low_power_entropy.py "$inputs" --compare-scored "$out"
.venv/bin/python scripts/science/reduce_low_power_entropy_lobes.py --output "$out/lobes"
```

The original four per-step ledgers, seed checks and catalogues are retained in the project archive as `turn25_entropy_2026-11-23/native-receipts.tar.gz` (SHA-256 `659148e1f3f860233cb3cb710ffa620ab4f97a31277dc340b1bc2ade5d3e4d21`). For the full per-step check, extract that archive and give its directory to the independent verifier with `--raw-native`. The native score packet and all file digests are archived alongside it. [Run and custody record](../exchange/logs/2026-11-23-low-power-entropy-results.md)
