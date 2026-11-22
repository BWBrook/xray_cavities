# Native enthalpy divided by matched cumulative gas delivery

NAT-01 and NAT-07 are supported for the matched quantities reported here. Claude (Anthropic, Fable 5.2) independently recomputed all 19 primary case-age values and all 228 method and time-rule rows from the archived snapshot rates and native measurements. The largest relative difference was below `5e-16` for the ratios and below `6e-16` for the signed energy components. Both calculations start with the same extracted face rates and lobe integrals. [Independent comparison](assets/native_delivery_review_2026-11-21/comparison.json)

The primary quantity is current whole-lobe `2.5 sum(p_i V_i)` divided by the signed net gas energy reconstructed across the maintained injector surface, integrated from the initialized t=0 output to the identical case and actual age. Each lobe cell has `tr1 > 1e-3` and contributes its full exact native volume. Cone and stationary gas fluxes retain their signs. The numerator is absolute current enthalpy; the denominator includes gas internal and kinetic energy plus pressure work and excludes potential transport. These are distinct from current-minus-initial spherical storage. [Estimand and exclusions](assets/native_delivery_restatement_2026-11-21/estimand.md)

## Primary results

The selected surface contains 19 case-age rows: outputs 10/20/30/40/50 for C-HI, C-LO and G-LO, and 10/20/30/40 for G-HI. Every denominator uses the matching actual output time, rather than a rounded age or a pilot-interval multiplier. G-HI 48–50 are neither used nor extrapolated.

| Case | Selected nominal ages (Myr) | 2.5pV / cumulative net gas | 2.5pV / labelled kinetic reference |
| --- | --- | ---: | ---: |
| C-HI | 10–50 | 0.4518–0.4810 | 0.5249–0.5587 |
| C-LO | 10–50 | 0.5827–0.9864 | 0.6309–1.1075 |
| G-HI | 10–40 | 0.4043–0.4306 | 0.4682–0.4983 |
| G-LO | 10–50 | 0.5417–0.6818 | 0.6147–0.7849 |

[Claim ranges](assets/native_delivery_restatement_2026-11-21/claim_ranges.csv) · [All primary rows, including signed cone and stationary energies](assets/native_delivery_restatement_2026-11-21/primary_selected_ages.csv)

Dividing by cone emission alone answers what fraction of the gas energy emitted through the cones appears as lobe enthalpy. Keeping the stationary surface's signed contribution answers the same question for the net supply to freely evolving cells. With cone emission alone the primary ratio spans 0.545–0.956 in C-LO and 0.530–0.677 in G-LO. It changes by less than 0.1 percentage point in either high-power case. In C-LO the stationary surface absorbs energy, particularly early on. Its cumulative contribution is −0.076 of the labelled energy at 10 Myr and −0.035 at 50 Myr. [Independently recomputed cone and net rows](assets/native_delivery_review_2026-11-21/recomputed_rows.csv)

At the common 30-Myr output, in case order C-HI/C-LO/G-HI/G-LO, cumulative net gas delivery is 1.161639/1.113999/1.157990/1.147860 times the labelled kinetic reference. The matched comparison is:

| Case | Actual age (Myr) | Cumulative net gas (erg) | 2.5pV / net gas | R100 storage / net gas | 2.5pV / R100 storage |
| --- | ---: | ---: | ---: | ---: | ---: |
| C-HI | 29.999994 | 2.199511e60 | 0.471375 | 0.932639 | 0.505421 |
| C-LO | 29.999166 | 2.109250e58 | 0.871444 | 1.082088 | 0.805335 |
| G-HI | 29.999367 | 2.192556e60 | 0.404327 | 0.932158 | 0.433754 |
| G-LO | 29.999644 | 2.173397e58 | 0.667319 | 1.019613 | 0.654483 |

[Unrounded matched values](assets/native_delivery_restatement_2026-11-21/matched_30myr.csv)

R100 storage is the signed change in thermal, kinetic and fixed-potential energy relative to the initial fields in the cells of the current aperture. The old 2.5pV/storage values are unchanged by a common external denominator. The apertures are geometrically complete and contain the lobe at this age; that fact does not qualify production boundaries. Storage/gas near unity is not a physical closure result: the aperture changes, its surface transport is unmeasured, and storage retains regional-mass dependence on the gravitational potential zero.

## Quadrature and robustness

The primary method is `linear_snapshot_flags` with the trapezoidal rule. For each interval `i -> i+1`, the gas denominator adds `P_label * (t[i+1]-t[i]) * ((1-w)*r[i] + w*r[i+1])`, where `r` is signed net gas power divided by labelled power. The rule weights are `w=0, 0.5, 1` for left, trapezoidal and right integration. Independently, the script sums each archived interval's `net_gas * labelled_interval_energy`; the two cumulative routes agree. The labelled comparator is labelled bipolar kinetic power times actual active age, capped at 50 Myr, and is never renamed measured delivery.

At 30 Myr, changing only the time weighting gives 2.5pV/net-gas ranges of 0.471227–0.471524, 0.870605–0.872284, 0.404193–0.404461 and 0.666779–0.667861 in the case order above. Forced HLL/HLLC variants retain the broad high-/low-power separation. The first-order face reconstruction fails an independent mass check. In every interval ending at outputs 20 through 47 it overpredicts the tagged-mass balance by 5.6–6.2% of the interval's labelled mass. The primary reconstruction closes to within 0.04% in G-HI and 0.01% in each other run. The first-order rows are retained as a record of this failed test and excluded from the interpretation of uncertainty. [Method and time-rule rows](assets/native_delivery_restatement_2026-11-21/selected_age_scenarios.csv) · [Tagged-mass check](assets/native_delivery_review_2026-11-21/tracer_closure_limits.csv)

The choice of lobe edge matters more in C-LO. At 50 Myr its 2.5pV/net-gas ratio is 0.986, 0.847 or 0.765 when cells must contain more than 0.1%, 0.5% or 1% jet material by mass. Each qualifying cell contributes its full volume. Over the last three 10-Myr intervals the enthalpy gain per unit of new delivery is 1.05, 1.10 and 1.21 at the primary cut, and 0.92–0.98 at the 0.5% cut. The lobe thermal energy is 0.95–1.05 times the initial thermal energy in the same cells at the selected ages. Including mixed gas close to the original pressure can therefore raise the numerator. A cumulative ratio of unity has no special status as an upper bound. [Tracer-cut and thermal-energy comparison](assets/native_delivery_review_2026-11-21/threshold_and_lobe_state.csv) · [Incremental ratios](assets/native_delivery_review_2026-11-21/incremental_ratios.csv)

The historical Q029 native numerators differ from the exact-volume turn-15 numerators by at most 0.007015%; both are retained in the table. No physical explanation for that small historical difference is assumed here. The new primary numerator uses the turn-15 table consistently. Switching to 4pV simply multiplies every proxy ratio by 1.6.

Startup, intermediate Runge–Kutta states and the unsaved terminal velocity dip limit the saved-state integral. In C-LO the tagged-mass residual sums to −0.126 of one interval's labelled mass by 10 Myr and reaches +0.035 in the final interval alone. This sizes a timing discrepancy in mass. The analogous error in gas energy remains unmeasured. [Tagged-mass check](assets/native_delivery_review_2026-11-21/tracer_closure_limits.csv)

The high-power exterior energy budgets also affect the interpretation. After 5 Myr the primary reconstruction gives a shortfall per interval of 6–10% of labelled input in G-HI and 4–23% in C-HI, using the outer active cells for the domain boundary flux. C-HI's shortfall grows with age and is sensitive to the outer-boundary reconstruction. To the extent that this energy would have heated the lobe, the high-power enthalpy fractions could be biased low. Four unreplicated runs cannot calibrate a universal pressure-to-energy conversion. [Injector history archive, `comparison/flagged_sphere_gravity_intervals.csv`](assets/production_injector_histories_2026-11-21/history_tables.zip)

## Reproduction and evidence pins

```sh
.venv/bin/python scripts/science/restate_native_delivery.py
.venv/bin/python scripts/science/review_native_delivery.py
.venv/bin/python scripts/claims/check_claims.py
```

Inputs are pinned in the ledger: the public injector archive and its receipt at `1b3de17`; four turn-15 native measurement tables at `3e9646e`; historical Q029 comparisons at `5e34fa3`; and the unchanged storage/gauge reconciliation at `06f9a2d`. The calculation verifies the injector ZIP and all receipt-listed members, actual-age matches, label energies, signed cone-plus-stationary sums and two independent cumulative routes. Its [receipt](assets/native_delivery_restatement_2026-11-21/verification.json) records 20,667 numerical comparisons with a maximum relative residual of 6.09e-16, input/member hashes and the calculation source hash. Re-running the numerical product needs no private data or remote computation.

Codex (OpenAI, GPT-6) prepared the matched calculation, figure and brief (`58ce7e6`). Claude's independent integration (`e36bf6e`) used snapshot rates without the Codex interval tables or integration code. It also reproduced the twelve 30-Myr storage and enthalpy ratios and the four 20-Myr ambient thermal-plus-kinetic shares. The ledger records the review at `dffd945` and the corrected closure and interpretation limits at `ba284ec`. [Independent review tables](assets/native_delivery_review_2026-11-21)

The focused brief uses `settings/native_energy_brief.yaml` with makedoc 2.0.1 and has a limit of two A4 pages including the figure and sources. The original restatement passed strict PDF builds for the brief and article and the ledger check. Targeted failure checks rejected a modified archive, a duplicate snapshot key and an incorrect interval start index. The local v2 CLI accepts the following commands.

```sh
makedoc check -c settings/native_energy_brief.yaml
makedoc build -c settings/native_energy_brief.yaml --pdf --strict
makedoc build -c settings/build.yaml -p draft --pdf --strict
```

Figure 1 in the article remains the historical **label-normalized comparator**, with an explicit caption. This task changes only NAT-01/NAT-07 and their corresponding native-energy passages, plus the focused brief; unrelated observer and shock results in the working manuscript are outside this restatement and need their own current-evidence reconciliation before release.
