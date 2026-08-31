# Four-case selected-age dual-space energetics audit

## Status

Decision label:
`SELECTED_AGE_DUAL_SPACE_PROOF_GREEN_VOLUME_TOPOLOGY_BIAS_DOMINATES`.

The independent native-grid and observer-like X-ray ledgers now join cleanly
across the accepted selected-age surface. This is a decision-grade proof of
the decomposition, not the final annual energetics audit. It supports moving
next to the native three-dimensional shock-energy partition rather than
expanding the observer cadence first.

## Question

When an X-ray cavity enthalpy differs from the native lobe enthalpy, how much
of the discrepancy comes from the inferred cavity volume and how much comes
from the inferred ambient pressure?

For the primary non-relativistic comparison,

```text
H_X / H_lobe,grid
  = (V_X / V_lobe) * (p_X / p_lobe).
```

The native path uses fractional tracer and cell-wise initial-state
subtraction. The observer path uses X-ray-only cavity topology, synthetic
X-ray deprojection, geometric line-of-sight depth, an ellipsoid-volume-
averaged ambient pressure, and `2.5pV`. The two paths were joined only after
both had completed independently.

## Numerical repair

The first completed projection job was scientifically rejected after local
review. Its deprojection penalty of `0.03` over-smoothed the high-contrast
temperature numerator, most visibly in `G-HI`, producing profile residuals
near `0.47` and false near-zero pressures. Those joined tables remain under
`diagnostic_original_regularization/` as invalid diagnostic evidence.

The accepted repair uses regularization `1e-6` and treats temperature-
numerator or emissivity support below `1e-12` of the fitted maximum as
numerically unconstrained. Isolated unsupported shells are explicitly
interpolated. PBS `789809.kunanyi-ohpc` completed `F/0`; all `57` case-age-view
products passed, the maximum reconstruction residual was
`1.651000166245975e-4`, and no view required more than one interpolated shell.
The repaired archive SHA-256 is
`1f540882174ab2a705a07fe830c450ca54e7b497f7e16ae75498c5cce640cf59`.

## Primary results

Of the `57` selected case-age views, `37` passed the X-ray topology gate and
`20` remained unresolved. Primary medians and full ranges over the usable
views are:

| Case | Usable / failed views | Volume recovery | Pressure recovery | X-ray / native lobe enthalpy |
| --- | ---: | ---: | ---: | ---: |
| `C-HI` | `11 / 4` | `0.0961 [0.0308, 0.910]` | `1.153 [0.994, 1.503]` | `0.1076 [0.0455, 0.956]` |
| `C-LO` | `10 / 5` | `6.511 [5.893, 10.954]` | `1.030 [0.990, 1.074]` | `6.762 [6.250, 10.845]` |
| `G-HI` | `6 / 6` | `0.0555 [0.0128, 0.324]` | `0.655 [0.351, 0.946]` | `0.0363 [0.0121, 0.114]` |
| `G-LO` | `10 / 5` | `0.432 [0.313, 1.314]` | `1.045 [0.701, 1.189]` | `0.4559 [0.369, 0.938]` |

Pressure recovery lies within the descriptive factor-of-two band for `36/37`
usable views. Volume recovery does so for only `5/37`, and lobe-enthalpy
recovery consequently does so for only `5/37`. The exact factorization closes
to numerical precision for every quantitative row.

Changing from minor to geometric to major depth, or from midpoint to
ellipsoid-volume-averaged pressure, changes magnitudes but not the case-level
interpretation. Across those method combinations, median lobe recovery spans
approximately `0.078--0.130` for `C-HI`, `5.61--8.08` for `C-LO`,
`0.026--0.058` for `G-HI`, and `0.417--0.518` for `G-LO`.

The topology failures are also physical evidence rather than missing values:

- `C-HI`: four multiple or one-sided component views;
- `C-LO`: four connected cross-midplane views and one view with no significant
  component;
- `G-HI`: six multiple or one-sided component views;
- `G-LO`: two connected cross-midplane, two multiple or one-sided, and one
  no-component view.

## Interpretation

**Observation:** on this selected surface, the X-ray-deprojected ambient
pressure is usually close to the tracer-weighted native lobe pressure, whereas
the X-ray cavity volume can be much smaller or larger than the native lobe
volume.

**Inference:** the dominant source of X-ray lobe-enthalpy bias is the inferred
geometry and topology, not the pressure estimate. This conclusion is robust
to the retained depth and pressure-method sensitivities. `C-HI` and `G-HI`
generally recover only a small compact part of the native lobe, `C-LO` admits
a much larger deficit region than the tracer-weighted lobe, and `G-LO` is
intermediate.

This does not yet answer whether cavity enthalpy measures the whole outburst.
Ratios to retained and injected energy remain descriptive because boundary
flux is unresolved, the native shock-energy fraction has not yet been
calculated, and `C-LO` ambient energetics remain background dominated without
the matched no-jet correction. No closure residual is assigned a physical
meaning here.

## Decision

The selected-age proof has done enough to expose the governing bias. An annual
X-ray extension would add cadence but is unlikely to change the current
decision. The next high-value tranche is the prespecified selected-age native
three-dimensional shock partition, with no-jet controls and threshold
sensitivity. That tranche should quantify shock-region thermal, kinetic,
gravitational, and irreversible-heating terms and then test whether shock
fraction changes the interpretation of `H_X/E_retained` and
`H_X/E_injected`.

Only if that result reveals decision-relevant time structure should the full
annual observer audit be opened. This keeps rigour at the scientific decision
boundary without expanding the computational surface by default.

## Products

- Accepted audit tables:
  `docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/audit_products/`.
- Repaired pressure archive and logs:
  `docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/pressure_repair_remote_logs/`.
- Original projection archive and logs:
  `docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/remote_logs/`.
- Rejected first join:
  `docs/science/assets/four_case_selected_age_dual_space_energetics_2026-08-31/diagnostic_original_regularization/`.

## Boundaries

- Selected ages only: `10/20/30/40/50 Myr` for `C-HI`, `C-LO`, and `G-LO`,
  and `10/20/30/40 Myr` for `G-HI`.
- `G-HI/50` remains excluded.
- X-ray topology failures remain censored, not repaired with tracer.
- Tracer is native truth and post-hoc recovery evidence only; it does not
  define the observer cavity.
- `2.5pV` is primary; `4pV` remains a convention-matched comparator.
- Native shock fraction, no-jet background subtraction, and boundary flux are
  not claimed in this package.
