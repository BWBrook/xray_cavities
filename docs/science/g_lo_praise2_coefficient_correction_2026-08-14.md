# G-LO PRAiSE2 coefficient correction

## Decision

`PRAISE2_PUBLISHED_COEFFICIENT_VALIDATED_FOR_PRODUCTION`

PBS `785271.kunanyi-ohpc` (`g_lo_c1cmp`) completed with `Exit_status=0`.
The controlled comparison isolates the missing `4/3` multiplier identified by
Patrick while holding the selected 4096-particle population, histories,
weights, timepoints, frequencies, and all other PRAiSE2 method choices fixed.

The coefficient probe changed by the required factor
`1.3333333292256078`. Both the corrected and uncorrected calculations had zero
non-finite values, and every prescribed validation gate passed. Corrected
`plutokore.radio.praise2.praise(...)` is therefore the production method; the
Goal 056 uncorrected products remain immutable baseline provenance.

## Scientific effect

At the 50 Myr endpoint, the corrected-to-uncorrected population-weighted
emissivity ratios are:

| Frequency (GHz) | Ratio | Change |
|---:|---:|---:|
| 0.15 | 0.999036 | -0.096% |
| 0.5 | 0.998170 | -0.183% |
| 1.4 | 0.996731 | -0.327% |
| 4.5 | 0.993082 | -0.692% |
| 15.0 | 0.973059 | -2.694% |

The effect grows with frequency and age, as expected for a correction to the
radiative-loss coefficient. It is small for integrated low-frequency
luminosity, but it is not scientifically ignorable at high frequency: at
15 GHz and 50 Myr, `21.24%` of analysis weight changes by more than the
prespecified material-ratio threshold and `443/4096` particles change emission
class.

The endpoint map calculation emitted a divide-by-zero warning only when
summarising `log10(corrected/uncorrected)` for pixels whose corrected map value
was exactly zero. The stored ratios, weighted totals, class counts, validation
gates, and decision are unaffected. The local diagnostic now restricts that
display statistic to finite positive ratios; no remote rerun is warranted.

## Provenance

- Corrected plutokore source revisions: tested commit
  `a190f0d96610c781a7ff71860333a0aae3cdfe92` on
  `bwbrook/deep-server-bringup`, integrated independently into `master` as
  `73210e15d4c60e77ffb317b3ee2b9209c049edd4`.
- Retrieved archive SHA-256:
  `2752dd195d6678d81200052ab2c9393725c0eada87d6919418f19c964a10ecbb`.
- The archive has 12 members and its internal manifest/checksum surfaces are
  retained under `review_products/`.
- Remote stderr is empty.
- `completion_summary.csv` records the compact scheduler and decision surface.

## Limits

This is a coefficient-only method validation on the accepted deterministic
G-LO panel. It authorizes corrected PRAiSE2 for later matched radio production;
it is not itself the complete per-snapshot radio product.
