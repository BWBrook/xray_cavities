# Four-case scientific synthesis

## Purpose

Goal 065 joins the accepted Goal 062 fluid, gravitational, tracer, and shock
surface; the Goal 063 background and shock-validity gates; and the Goal 064
X-ray/cavity and corrected-PRAiSE2 products. It answers the three prespecified
paper tests at common source ages `10/20/30/40/50 Myr` for the matched
`C-HI`, `C-LO`, `G-HI`, and `G-LO` factorial.

This is a descriptive synthesis of one deterministic simulation per factorial
cell. It does not use replicate p-values or claim population-level effects.
Observations and interpretations are kept separate throughout the compact
tables.

## Analysis contract

- Known bipolar jet power is `2e45 erg/s` for `C-HI` and `G-HI`, and
  `2e43 erg/s` for `C-LO` and `G-LO`.
- Cavity energy is quantitative only for exactly two non-crossing,
  opposite-side X-ray components. This leaves `39/60` selected age-view rows.
- The primary cavity convention is `2.5pV`; `pV` and `4pV` remain explicit
  sensitivity surfaces.
- Ambient pressure is the tracer-shell midpoint proxy, not an X-ray-fitted
  pressure.
- Corrected PRAiSE2 full-loss radio luminosity is primary; lossless values are
  retained as a comparator.
- Goal 063 shock validity is fail-closed. The `G-HI` 50 Myr endpoint is valid
  for non-shock observables but excluded from shock-kinematic analysis. This
  leaves `37` quantitative age-view rows in the primary Mach test.
- The `C-LO` whole-domain ambient-energy change is background dominated. Its
  inside-100-kpc value remains an upper bound rather than a corrected coupling
  efficiency.

## Physical context

Direct tracer-defined lobe energy declines as a fraction of injected energy
across the selected late-time surface. At 50 Myr the retained fractions are:

| Case | Direct lobe energy / injected energy |
| --- | ---: |
| `C-HI` | `0.1676` |
| `C-LO` | `0.06047` |
| `G-HI` | `0.1982` |
| `G-LO` | `0.1281` |

These values are simulation-truth diagnostics, not observer-recovered cavity
energies. The apparently extreme `C-LO` whole-domain ambient value remains
excluded from coupling-efficiency interpretation because Goal 063 showed that
`94.61%` of its accounted endpoint change lies beyond 100 kpc and is dominated
by common atmosphere evolution.

## Test 1: cavity bias versus shock strength

**Observation.** Within each viewing angle, pooled cases show a strong
negative association between `2.5pV / injected energy` and valid kinematic
shock Mach:

| View | Spearman rho | Raw slope (dex per Mach) |
| --- | ---: | ---: |
| `0deg` | `-0.888` | `-0.307` |
| `45deg` | `-0.881` | `-0.175` |
| `90deg` | `-0.868` | `-0.232` |

A descriptive model with case and view fixed effects gives a much smaller Mach
slope of `-0.0402 dex per Mach`; Mach adds only `0.0031` to model R-squared.
Leave-one-case-out slopes are `-0.0976`, `-0.0358`, `+0.1142`, and `-0.0393`
when omitting `C-HI`, `C-LO`, `G-HI`, and `G-LO`, respectively.

**Inference.** The pooled anticorrelation is real on this simulation surface,
but it is not a case-robust independent Mach effect. Power, environment, age,
and morphology jointly structure the relationship. The defensible current
claim is `strong_pooled_negative_pattern_not_case_robust`.

## Test 2: cavity energy divided by spectral age

For the adopted `2.5pV` convention and the matched PRAiSE effective-field
treatment, median inferred-to-known bipolar power ratios are:

| Case | Quantitative rows | Median inferred / known power |
| --- | ---: | ---: |
| `C-HI` | `11` | `0.0494` |
| `C-LO` | `10` | `1.55` |
| `G-HI` | `8` | `0.00650` |
| `G-LO` | `10` | `0.0877` |

**Observation.** The estimator is approximately order unity only for `C-LO`.
It substantially under-recovers known power in both high-power cases and in
`G-LO`. Alternative magnetic-field and `4pV` treatments remain available in
the machine-readable sensitivity surface.

**Inference.** `2.5pV / t_spec` is not a universal recovery estimator in this
factorial. This interpretation is conditional because `40/60` integrated
spectra have a break above the observed band and are therefore censored, and
because the pressure surface is a tracer-shell proxy.

## Test 3: radio-luminosity power relations

Median full-loss inferred-to-known power ratios are:

| Case | 150 MHz relation | 1.4 GHz relation |
| --- | ---: | ---: |
| `C-HI` | `0.937` | `5.10` |
| `C-LO` | `7.34` | `15.85` |
| `G-HI` | `0.523` | `2.37` |
| `G-LO` | `4.03` | `7.02` |

**Observation.** The low-power cases are strongly overestimated, especially
by the 1.4 GHz relation. The 150 MHz relation is closest to the known power for
the high-power cases, while the group environment lowers the median recovery
relative to the corresponding cluster case at both power levels.

**Inference.** The standard radio scalings show structured jet-power and
environment dependence rather than a common unbiased recovery. Published
intrinsic scatter is recorded, but these four controlled simulations are not
a sampled population.

## Decision

Decision label:
`FOUR_CASE_SYNTHESIS_COMPLETE_SUPERVISOR_INTERPRETATION_READY`.

The matched factorial now supports the paper-level conclusion that inferred
jet energetics depend materially on age, viewing geometry, jet power, and
environment. It does not support presenting shock Mach as an independently
identified causal driver, nor either cavity-spectral or radio scaling as a
universal unbiased estimator.

No additional PLUTO production or observable recomputation is needed before
supervisor interpretation. The next consequential decision is scientific
framing: whether Mach remains a descriptive covariate, which radio relation is
primary, and how censored spectral ages and tracer-shell pressure are presented
in the paper.

## Outputs

- Figure:
  `docs/science/assets/four_case_scientific_synthesis_2026-08-26/four_case_scientific_synthesis.png`
- Joined physics surface: `case_age_physics.csv`
- Cavity recovery and Mach tests: `cavity_energy_recovery.csv` and
  `shock_cavity_test_summary.csv`
- Radio and spectral inference: `radio_power_inference.csv`,
  `spectral_fits.csv`, and `spectral_cavity_power_inference.csv`
- Cavity age-proxy inference: `cavity_age_power_inference.csv`
- Compact recovery summaries: `jet_power_recovery_summary.csv`
- Descriptive factorial contrasts: `factorial_effects.csv`
- Decision table: `scientific_decision_summary.csv`
- Provenance and metadata: `input_provenance.csv`,
  `four_case_scientific_synthesis_metadata.json`, and
  `local_asset_manifest.sha256`

## Validation

- `uv run pytest tests/test_four_case_scientific_synthesis.py tests/test_snapshot_synthesis.py tests/test_snapshot_inference.py -q`
  passed with `16` tests.
- The builder regenerated the complete output bundle from accepted compact
  Goal 062/063/064 inputs.
- JSON and CSV schema checks, finite-value gates, exact case-age coverage,
  cavity topology gates, shock-validity exclusions, and radio/spectral row
  counts are covered by the focused tests.
- The synthesis figure was inspected after generation; one focused repair
  added an explicit case/view legend and clarified the spectral-power label.
- No raw HDF5, particle history, or remote science payload was read or changed.
