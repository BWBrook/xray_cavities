# Corrected four-case scientific synthesis

## Simulation and analysis contract

| Element | Prespecified setup |
| --- | --- |
| Factorial | Cluster/group environments crossed with high/low jet power: `C-HI`, `C-LO`, `G-HI`, `G-LO` |
| Environments | Stewart cluster `002003` and group `002031` atmospheres |
| Grid/domain | Cartesian `960 x 960 x 1014`; X1/X2 `-200..200 kpc`, X3 `-250..250 kpc`; central `0.05 kpc` cells with stretched outer zones |
| Jet power | One-sided `1e45 erg/s` for `*-HI` and `1e43 erg/s` for `*-LO`; known bipolar powers `2e45` and `2e43 erg/s` |
| Jet geometry | Speed `0.1c`; two `15 deg` cones; initial radius `0.1 kpc`; injection height `0.75 kpc`; centred launch |
| Particles | `32` particles per injection event; injection and output cadence approximately `0.01 Myr` |
| Simulation time | Jets active for the 50 Myr runs; exact 50 Myr fluid endpoints retained |
| Fluid cadence | Float output approximately every `1 Myr`; double restart output approximately every `5 Myr` |
| Tracer | Fractional jet tracer; accepted thresholds and side definitions retained from Goals 062--064 |
| X-ray | Thermal X-ray surface at `1 keV` and `z=0.05`, using the supplied APEC/Gaunt correction tables; no abundance parameter was varied separately |
| Radio | Corrected PRAiSE2 continuous-injection model; `z=0.05`, `eta=0.03`, electron index `s=2.2`, Lorentz-factor range `500..1e5`, and `0.15/0.5/1.4/4.5/15 GHz` |
| Views | `0/45/90 deg`; nonzero views use `edge_overlap_uniform_cell_projection` |
| Science ages | `10/20/30/40/50 Myr`, except boundary-contaminated `G-HI/50`, which is excluded from every scientific surface |

## Purpose

Goal 065 joins the accepted Goal 062 fluid, gravitational, tracer, and shock
surface; Goal 063 background and validity gates; Goal 064 selected-age X-ray,
cavity, and corrected-PRAiSE2 products; and the 2026-08-28 boundary,
spectral-field, and seven-method cavity-age corrections. It answers three
prespecified paper tests using one deterministic simulation per factorial
cell. The analysis is descriptive: ages and views are repeated measurements,
not independent replicates, and no population-level p-values are claimed.

## Consequential gates

- `G-HI/50` is archival only. Its lobe/shock reaches the X3 boundary and
  contaminates the edge pressure; it is absent from every table and summary.
- Cavity quantities are quantitative only for exactly two non-crossing,
  opposite-side X-ray components. The retained surface has `37` case-age-view
  rows and `74` side components.
- Cavity enthalpy retains `2.5pV` as the primary non-relativistic convention
  and `4pV` as the literature comparator.
- The current ambient pressure is a tracer-shell midpoint proxy, not an
  X-ray-inferred pressure. This limitation motivates the next dual-space
  audit.
- Corrected PRAiSE2 full-loss luminosity is primary; lossless luminosity is a
  comparator.
- Spectral breaks above `15 GHz` are age upper limits and inferred-power lower
  limits. Censored rows are excluded from ordinary medians and counted
  explicitly.
- The seven clocks remain separate: true source age, sound crossing, buoyant
  rise, refill, bilateral supersonic shock, mean-pressure spectral, and
  emissivity-weighted spectral age. The calculated buoyant age is not replaced
  by a fixed multiple of sound-crossing age.
- The `C-LO` whole-domain ambient-energy change remains background dominated;
  its inside-100-kpc value is an upper bound, not a corrected efficiency.

## Physical context

The last valid direct tracer-defined lobe-energy fractions of injected energy
are `0.1676` for `C-HI` at 50 Myr, `0.06047` for `C-LO` at 50 Myr, `0.1987`
for `G-HI` at 40 Myr, and `0.1281` for `G-LO` at 50 Myr. These are native-grid
truth diagnostics, not observer-recovered cavity energies.

## Test 1: cavity bias versus shock strength

**Observation.** Within each viewing angle, the pooled association between
`2.5pV / injected energy` and valid kinematic shock Mach is strongly negative:

| View | Spearman rho | Raw slope (dex per Mach) |
| --- | ---: | ---: |
| `0deg` | `-0.888` | `-0.307` |
| `45deg` | `-0.881` | `-0.175` |
| `90deg` | `-0.868` | `-0.232` |

A descriptive model with case and view fixed effects gives a much smaller
Mach slope of `-0.0402 dex per Mach`; Mach adds only `0.0031` to model
R-squared. Leave-one-case-out slopes change sign.

**Inference.** The pooled anticorrelation is clear on this simulation surface,
but it is not a case-robust independent Mach effect. Jet power, environment,
age, and morphology jointly structure the relationship. Decision:
`strong_pooled_negative_pattern_not_case_robust`.

## Test 2: seven cavity-age estimators

For the primary `2.5pV` convention, true-age median inferred-to-known bipolar
power ratios are:

| Case | Quantitative rows | True-age median recovery | Mean-pressure spectral recovery |
| --- | ---: | ---: | ---: |
| `C-HI` | `11` | `0.00810` | `0.0124` exact median |
| `C-LO` | `10` | `0.628` | `1.05` exact median |
| `G-HI` | `6` | `0.00437` | `>0.00321` median lower bound |
| `G-LO` | `10` | `0.0731` | `>0.0871` median lower bound |

The mean-pressure spectral method has `20/37` censored rows. Both group cases
contain only lower limits for that method, so ordinary medians would be
scientifically invalid. Emissivity-weighted spectral ages are retained only as
the prespecified sensitivity surface.

**Inference.** Clock choice changes inferred power by factors of a few, but it
cannot explain the much larger high-power cavity-energy deficit. The primary
problem is therefore not simply choosing the wrong age estimator. Decision:
`age_method_bias_modulates_not_explains_cavity_energy_deficit`.

## Test 3: radio-luminosity power relations

Median full-loss inferred-to-known power ratios are:

| Case | 150 MHz relation | 1.4 GHz relation |
| --- | ---: | ---: |
| `C-HI` | `0.937` | `5.10` |
| `C-LO` | `7.34` | `15.85` |
| `G-HI` | `0.520` | `2.36` |
| `G-LO` | `4.03` | `7.02` |

**Inference.** The standard radio scalings have structured jet-power and
environment dependence rather than a common unbiased recovery. The 150 MHz
relation is closest for the high-power simulations, while both relations
substantially overestimate the low-power simulations. Published scatter is
retained, but four controlled simulations are not a sampled population.
Decision: `radio_scalings_power_and_environment_dependent`.

## Decision and residual uncertainty

Decision label: `FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT`.

The corrected synthesis supports three stable conclusions:

1. The pooled Mach association is descriptive, not independently identified.
2. Age-estimator bias modulates inferred cavity power but does not explain the
   severe high-power deficit.
3. Radio power recovery depends materially on jet power and environment.

The decision-relevant uncertainty is now the origin of the cavity-energy
deficit. Stas's method directive requires two independent paths: native-grid
truth using fractional tracer and cell-wise initial-state subtraction, and an
observer-like X-ray path using X-ray-only geometry and pressure. They must be
joined only after each is complete, with volume bias, pressure bias, lobe
enthalpy bias, and missing shock/outburst energy reported separately. Existing
selected ages are sufficient for a proof-of-method audit before annual
extension; no new PLUTO or observable production is required.

## Outputs

- Figure: `four_case_scientific_synthesis.png`
- Native physical surface: `case_age_physics.csv`
- X-ray cavity recovery and Mach tests: `cavity_energy_recovery.csv` and
  `shock_cavity_test_summary.csv`
- Seven-age-method surface: `xray_cavity_age_geometry.csv`,
  `age_method_comparison.csv`, `cavity_power_method_comparison.csv`, and
  `age_power_method_summary.csv`
- Radio and spectral inference: `radio_power_inference.csv`,
  `radio_power_recovery_summary.csv`, and `spectral_fits.csv`
- Descriptive factorial contrasts: `factorial_effects.csv`
- Decisions, provenance, and metadata: `scientific_decision_summary.csv`,
  `input_provenance.csv`, `four_case_scientific_synthesis_metadata.json`, and
  `local_asset_manifest.sha256`

All assets are under
`docs/science/assets/four_case_scientific_synthesis_2026-08-26/`.

## Validation

- The corrected builder regenerates the bundle from accepted compact inputs.
- Focused tests enforce exact case-age coverage, complete removal of
  `G-HI/50`, fail-closed topology and shock gates, seven distinct age methods,
  censor-aware summaries, and corrected radio row counts.
- JSON/CSV schemas, finite-value requirements, asset checksums, and the
  synthesis figure are checked in the final validation pass.
- No remote compute, raw HDF5, particle-history access, or observable rerun is
  required for this correction.
