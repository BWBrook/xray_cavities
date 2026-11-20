# Full injector histories and gravity comparison, 21 November 2026

All four native-history jobs finished with exit 0 on 20 November. The initial comparison failed after 22 seconds. Its replacement finished with exit 0 at 10:49 AEDT on 21 November. The end and abort mail settings matched the configured recipient and the terminal notifications arrived for all six jobs listed below. This completes the existing-output analysis requested in board message 3607. [Science report and public replay](../../science/production_injector_histories_2026-11-21.md) · [Verification receipt](../../science/assets/production_injector_histories_2026-11-21/verification.json)

| PBS job | Work | Wall time | Exit |
| ---: | --- | ---: | ---: |
| 882246 | G-HI, 48 outputs | 02:45:32 | 0 |
| 882247 | C-LO, 51 outputs | 02:44:34 | 0 |
| 882248 | C-HI, 51 outputs | 03:15:17 | 0 |
| 882249 | G-LO, 51 outputs | 02:47:21 | 0 |
| 882251 | Original comparison | 00:00:22 | 1 |
| 882661 | Repaired comparison, reusing all four histories | 00:00:15 | 0 |

## Why the comparison stopped

The original check rejected the left-endpoint gravity balance for the first G-HI interval outside the second padded box. The original sums outside the second and fourth boxes at startup contain the same cancellation. The whole-grid and interior powers both round to −1.9217576543160226 × 10³⁸ erg/s. The producer subtracts them before converting to cgs and stores an exterior net of +2.228690990728549 × 10²² erg/s, just **1.11 × 10⁻²³ of labelled power**. Both stored exterior directional sums round to zero.

The repaired check verifies the inward/outward decomposition of each parent and checks each exterior field against the difference of the original parent fields, allowing for independent floating-point rounding. Across 201 outputs and all three boxes, every difference agrees within one unit in the last place of the parent scale. The original small exterior net is preserved. The regression reproduces the actual startup values and rejects corrupt exterior and parent values. Only the compact comparison code changed in the replacement job bundle. [Comparison implementation](../../science/assets/outer_tracer_gravity_2026-11-19/replay_compact.py) · [Regression test](../../../tests/test_measure_outer_tracer_gravity.py)

## Verification and archive

The original collection matched 616 member hashes, including 201 cutouts, 402 source-bound receipts, eight case tables and five job logs. The final export matched all 619 member hashes. Its 611 native source members matched the four successful jobs byte for byte. Each receipt was tied back to the staged case, index, time, historical native digest and analysis code. The local replay reproduced all 2,364 injector interval rows, all 4,720 flagged-sphere gravity comparisons, all 7,080 rectangular-box comparisons and all 591 signed tracer transports. The only numerical differences in the remaining tables were at most 1.62 × 10⁻¹⁶ on a scale of one or the magnitude of the value, whichever is larger.

An independent numerical reduction checked per-case energy and tracer budgets in 44,344 scalar comparisons. A separate C implementation reproduced fluxes at 863,496 native interfaces, and a separate Cartesian-volume implementation reproduced the 4,720 flagged-sphere gravity comparisons to within 2.0 × 10⁻¹⁴ of labelled interval energy. [Energy review](../../science/assets/production_injector_histories_2026-11-21/energy_audit_receipt.json) · [Solver review](../../science/assets/production_injector_histories_2026-11-21/c_solver_receipt.json) · [Gravity review](../../science/assets/production_injector_histories_2026-11-21/gravity_audit_receipt.json)

All bulk evidence is in the shared project archive under `turn21_injector_2026-11-19/`.

| Artifact | SHA-256 |
| --- | --- |
| Original four histories and failed job log, `native_and_summaries_201.tar.gz` | `2369b45c02d8ae9eec5c2981edf44bf081a713452dcabcaa0e071764a3b2463e` |
| Repaired job bundle, `injector_join_d00be96fb42d.tar.gz` | `fdc7ea2bf9e305707fefedfc28e4b9998446719a325644aad95f53bcb8669719` |
| Final result, `production_injector_201.tar.gz` | `2e2e7646535aca9885f9e1c4fc408200e4898129c930a70cb10a9fd83de745c2` |
| Independent verification scripts and numerical checks, `independent_full_reviews_2026-11-21.tar.gz` | `5a51800e0b56ccdc97fb1d2c4d7e8f6a4a3a3658ca89bac79629ab6797b41fe2` |

For native replay, extract the final result and the original successful analysis stage recorded in the [pilot handoff](2026-11-19-production-injector-pilot.md). Set `STAGE` to the analysis directory, `RESULT` to the extracted final result directory and `OUT` to a fresh output directory. Run from the repository root with its Python environment.

```sh
python scripts/science/reduce_injector_patches.py "$STAGE/requests" "$RESULT/native/results" \
  "$STAGE/tagged_mass_intervals.csv" "$OUT/injector" --domain-balances "$STAGE/domain_interval_energy.csv" --require-outer
python scripts/science/compare_injector_gravity.py "$STAGE/requests" "$RESULT/native/results" \
  "$RESULT/native/summary" "$OUT/sphere" --require-outer
python docs/science/assets/outer_tracer_gravity_2026-11-19/replay_compact.py \
  --native-root "$RESULT/native/results" --output "$OUT/outer"
```
