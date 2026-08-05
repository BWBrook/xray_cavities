# Goal 055 log

## 2026-08-05 - local method decision complete

- Audited the Goals 049-054 evidence and the pinned pressure-preparation and
  emissivity paths.
- Checked the published PRAiSE method description: pressure and density
  histories are smoothed to reduce interpolation noise with a five-sample,
  third-order Savitzky-Golay filter.
- Confirmed that the same linear-domain pressure filter is not admissible for
  this G-LO cache because it creates `216035` non-positive values across
  `99108/197398` eligible histories.
- Confirmed that project log-SG is positivity-preserving but is an adaptation,
  not the published linear-domain operation.
- Decomposed the hybrid-population shift: log-SG changes the lossless branch by
  `1.80646%`, compared with `1.89273%` and `1.94849%` in the full-loss branch.
  The extra full-loss shift is only `0.08626` and `0.14203` percentage points.
- Confirmed the full-loss spectral-index change is `-0.00024496`.
- Retained unsmoothed pressure as the provisional project primary and log-SG
  as a required sensitivity. No final publication method is frozen.
- Final decision:
  `UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE`.
- Applied the lean stopping rule: no further census or computation is likely
  to change this internal decision. The remaining material question belongs
  in one focused supervisor method review before expensive three-case radio
  production or publication-facing use.
- Focused validation passed:
  `uv run pytest tests/test_g_lo_pressure_method_synthesis.py -q` returned
  `4 passed`; an independent read-only recalculation reproduced the two
  full-minus-no-loss differences and the spectral-index difference; all three
  new CSVs parsed with exact unique schemas; `git diff --check` and the
  unresolved-marker scan were clean.

Status: `complete_local_method_decision`.
