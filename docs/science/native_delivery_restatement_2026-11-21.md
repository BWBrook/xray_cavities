# Native enthalpy divided by matched cumulative gas delivery

Status: new denominator restatement awaiting independent review. The previously reviewed native numerator and pressure-to-storage comparison retain their evidence; this calculation changes their external normalization. Claims NAT-01 and NAT-07 remain provisional for the new restatement. This note does not promote detector, boundary or physical-closure claims.

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

At 30 Myr, changing only left/trapezoidal/right time weighting gives 2.5pV/net-gas ranges 0.471227–0.471524, 0.870605–0.872284, 0.404193–0.404461 and 0.666779–0.667861. First-order states give smaller fractions (trapezoidal: 0.448121, 0.833413, 0.384368 and 0.637642). Forced HLL/HLLC variants retain the broad high-/low-power separation. Across all 228 selected case-age/method/rule rows C-LO remains below unity, with a maximum 0.989571. These numerical sensitivities do not bound error from unsaved solver states. [All method and time-rule rows](assets/native_delivery_restatement_2026-11-21/selected_age_scenarios.csv)

The historical Q029 native numerators differ from the exact-volume turn-15 numerators by at most 0.007015%; both are retained in the table. No physical explanation for that small historical difference is assumed here. The new primary numerator uses the turn-15 table consistently. Switching to 4pV simply multiplies every proxy ratio by 1.6.

Startup, missing intermediate Runge–Kutta states and the unsaved terminal velocity dip limit the saved-state cumulative estimate. Negative stationary-region gas flux, especially in C-LO, is absorption and must not be dropped. Tracer-mass closure is useful for timing diagnostics but does not give a gas-energy error bound. Four unreplicated runs do not justify a population correction. No headline about an ambient share of total stored energy is reinstated.

## Reproduction and evidence pins

```sh
.venv/bin/python scripts/science/restate_native_delivery.py
.venv/bin/python scripts/claims/check_claims.py
```

Inputs are pinned in the ledger: the public injector archive and its receipt at `1b3de17`; four turn-15 native measurement tables at `3e9646e`; historical Q029 comparisons at `5e34fa3`; and the unchanged storage/gauge reconciliation at `06f9a2d`. The calculation verifies the injector ZIP and all receipt-listed members, actual-age matches, label energies, signed cone-plus-stationary sums and two independent cumulative routes. Its [receipt](assets/native_delivery_restatement_2026-11-21/verification.json) records 20,667 numerical comparisons with a maximum relative residual of 6.09e-16, input/member hashes and the calculation source hash. Re-running the numerical product needs no private data or remote computation.

The derived tables, figure, script and brief are new work awaiting an integration evidence commit; no uncommitted path is assigned a fictitious commit. An independent reader should recompute the 19 primary and 228 sensitivity rows, check the brief's rounded values, and then pin the new products before changing the new restatement's review status. Existing upstream simulation, extraction and review credits are unchanged. This matched calculation and the scoped paper draft were prepared by Codex (OpenAI, GPT-6).

The focused brief uses `settings/native_energy_brief.yaml` with makedoc 2.0.1 and builds to one A4 page, including its figure and sources. The article draft and brief passed configuration/lint/citation checks and strict PDF builds; the changed pages were rendered and inspected. The existing ledger test passed. Targeted failure checks rejected a modified archive, a duplicate snapshot key and an incorrect interval start index. The repository's older Makefile still calls the retired makedoc-v1 interface; this task used the local v2 CLI directly and did not migrate the shared build entry point.

```sh
makedoc check -c settings/native_energy_brief.yaml
makedoc build -c settings/native_energy_brief.yaml --pdf --strict
makedoc build -c settings/build.yaml -p draft --pdf --strict
```

Figure 1 in the article remains the historical **label-normalized comparator**, with an explicit caption. This task changes only NAT-01/NAT-07 and their corresponding native-energy passages, plus the focused brief; unrelated observer and shock results in the working manuscript are outside this restatement and need their own current-evidence reconciliation before release.
