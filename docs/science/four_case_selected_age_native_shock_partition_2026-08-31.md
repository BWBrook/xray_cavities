# Four-case selected-age native shock-energy partition

## Status

Decision label:
`SELECTED_AGE_NATIVE_SHOCK_PARTITION_GREEN_C_LO_LATE_FAIL_CLOSED`.

The prespecified native three-dimensional shock-energy surface is complete.
All four case workers finished successfully, and the recovered compact product
contains all `171` required case-age-side-threshold rows. Of the `19` primary
bipolar case-age rows, `15` are quantitative and four late `C-LO` rows fail
closed because one accepted axial front is non-supersonic.

PBS `789813.kunanyi-ohpc` nevertheless ended `F/1`. The failure occurred after
the science workers had completed: the wrapper's final validator requested
`volume_kpc3`, whereas the frozen output schema correctly names that field
`mask_volume_kpc3`. The wrapper and its regression test are repaired. A
file-list finalizer validated and archived the existing compact outputs only;
no production HDF5 file was reopened and no shock calculation was rerun.

## Question and method

The calculation asks how much of the known injected energy appears as a net
thermal, kinetic, and gravitational energy change in the native shocked
ambient region, and how much irreversible heating is diagnosed there.

The frozen method uses the exact same-grid `t=0` production state, Stas's
centre-zero fixed gravitational potential, and a 26-connected ambient
entropy-excess region anchored to the accepted compressed axial front. Each
jet side must pass independently before a bipolar result is reported. The
primary threshold factor is `1`; factors `0.5` and `2` are sensitivity tests.
Cluster and group no-jet runs calibrate dimensionless noise thresholds only.
They are coarser than the production grids and are not subtracted cell by
cell.

## Primary results

The net shock-region energy and irreversible-heating diagnostics, each divided
by known injected energy, are:

| Case | Quantitative / selected ages | Net shock-region fraction | Irreversible-heating fraction |
| --- | ---: | ---: | ---: |
| `C-HI` | `5 / 5` | `0.728 [0.678, 0.804]` | `0.250 [0.214, 0.274]` |
| `C-LO` | `1 / 5` | `0.225` at `10 Myr` | `0.268` at `10 Myr` |
| `G-HI` | `4 / 4` | `0.677 [0.583, 0.728]` | `0.318 [0.307, 0.332]` |
| `G-LO` | `5 / 5` | `0.809 [0.579, 0.874]` | `0.213 [0.172, 0.313]` |

Values are medians and full selected-age ranges where more than one age is
quantitative. `C-LO/20`, `/30`, `/40`, and `/50` are explicitly
`unresolved_bilateral_gate`, not zeros or imputed estimates.

The irreversible-heating diagnostic is not an additive subcomponent of the
net thermal-plus-kinetic-plus-gravitational change. It is an entropy-based
measure of irreversible heating, so its exceeding the net shock-region change
for `C-LO/10` is not an energy-ledger contradiction.

## Threshold sensitivity and controls

Both no-jet control environments passed: six snapshots each, zero sampled
joint exceedances, and adopted physical floors of `0.05`, `0.03`, and `0.02`
for pressure, density, and entropy excess.

- `G-HI` is effectively invariant to the half/double threshold treatment.
- `C-HI` is moderately stable: the median half- and double-threshold ratios
  are `1.055` and `0.923`.
- `G-LO` is more sensitive, especially late: the full half-threshold ratio
  reaches `1.361`, while the double-threshold ratio falls to `0.666`.
- The single quantitative `C-LO` age is threshold sensitive (`1.582` and
  `0.658`), reinforcing its limited interpretive role.

This sensitivity is carried into the product rather than hidden by selecting
a preferred threshold after seeing the result.

## Relation to Goal 066

The Goal 067 shock surface was joined to the accepted Goal 066 native and
observer ledgers without changing their validity flags. For the primary
observer method (`2.5pV`, geometric depth, ellipsoid-volume-averaged
pressure), usable rows with a quantitative shock result have median
X-ray-cavity-enthalpy to native-shock-energy ratios of:

- `0.0161` for `C-HI` (`11` usable views);
- `0.00449` for `G-HI` (`6` usable views);
- `0.1015` for `G-LO` (`10` usable views).

There is no jointly quantitative primary `C-LO` row: its `10 Myr` shock row
passes, but its observer topology does not, while its later shock rows fail
closed.

**Observation:** where both ledgers are quantitative, X-ray cavity enthalpy is
a small fraction of the energy change in the selected shocked ambient region.
The shock-region fraction itself is large in the three well-resolved case
series, while the X-ray lobe-enthalpy recovery remains strongly case- and
view-dependent.

**Inference:** adding the native shock term materially changes the
whole-outburst context: cavity enthalpy alone does not represent most of the
energetic disturbance. It does not overturn Goal 066's narrower result that
the bias in recovering native lobe enthalpy is dominated by cavity
geometry/topology rather than the inferred ambient pressure. The two results
address different denominators and should both be retained.

The selected ages are sufficient for this decision. The observed trends and
prespecified sensitivity bounds do not justify opening an annual native-shock
or observer extension by default.

## Products

- Review products:
  `docs/science/assets/four_case_selected_age_native_shock_partition_2026-08-31/review_products/`.
- Retrieved per-case compact outputs:
  `docs/science/assets/four_case_selected_age_native_shock_partition_2026-08-31/remote_analysis/`.
- Immutable recovered archive and scheduler logs:
  `docs/science/assets/four_case_selected_age_native_shock_partition_2026-08-31/remote_logs/`.
- Recovered archive SHA-256:
  `1287c74a2a9c2891ba2feb6d641128460f9a546828e2380daed901c40b73182d`.

## Boundaries

- Selected ages only: `10/20/30/40/50 Myr` for `C-HI`, `C-LO`, and `G-LO`;
  `10/20/30/40 Myr` for `G-HI`.
- `G-HI/50` remains excluded.
- Late `C-LO` shock fractions remain scientifically censored.
- The mask is native-grid truth, not an observable X-ray shock model.
- Coarser no-jet controls do not provide native-resolution cellwise
  background subtraction.
- Radial advection and boundary flux remain outside this regional partition.
- These products are analysis evidence, not publication-ready observables by
  implication.
