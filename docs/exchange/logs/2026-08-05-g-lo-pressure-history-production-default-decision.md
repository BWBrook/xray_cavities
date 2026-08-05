# Exchange log - Goal 055 G-LO pressure-history production-default decision

Date: 2026-08-05
Status: `complete_local_method_decision`

Goal 055 interpreted the existing Goals 049-054 evidence without new
scientific computation or remote work.

Published PRAiSE smooths interpolated pressure and density histories with a
five-sample, third-order Savitzky-Golay filter to reduce sampling noise. The
same linear-domain pressure treatment is not admissible on the current G-LO
cache: it creates `216035` non-positive values across `99108/197398` eligible
histories. Project log-SG preserves positivity but is an adaptation rather than
the published operation.

The census-replaced G-LO population shows that log-SG changes the no-loss
integrated amplitude by `1.80646%` and the full-loss amplitudes by `1.89273%`
and `1.94849%` at 0.15 and 1.4 GHz. Full ageing therefore adds only `0.08626`
and `0.14203` percentage points beyond the endpoint/amplitude effect. The
full-loss spectral-index change is `-0.00024496`.

Decision:

```text
UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE
```

Stable unsmoothed pressure is retained as the provisional project primary;
log-SG is required sensitivity analysis. Linear SG is rejected for this cache,
PRAiSE2 remains on hold, no further census is justified, and the observed
shift is method sensitivity rather than physical uncertainty.

One focused Patrick/Stas review is recommended before this convention drives
new C-HI/C-LO history production or a publication-facing radio comparison.
