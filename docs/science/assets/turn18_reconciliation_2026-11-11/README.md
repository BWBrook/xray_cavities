# Review reconciliation evidence

These tables support
[the reconciliation note](../../turn18_review_reconciliation_2026-11-11.md).
They use existing committed compact products only. No new native measurement
or held-out refit performance is reported here.

- `sphere_residual_reconciliation.csv`: every selected case/age with a
  whole-grid comparison, both transferred boundary estimates, R100 excess,
  exact geometry eligibility and discrepancies. Do not discard the failed
  geometry rows without retaining their flags.
- `emission_denominators.csv`: the six primary bipolar masks, with ambient
  cancellation divided separately by lobe and observed deficits, and the
  complement of binary-lobe volume filling.
- `primary_proxy_and_gauge_independent_components.csv`: 30-Myr 2.5pV and 4pV
  ratios and 20-Myr ambient thermal-plus-kinetic shares.
- `input_manifest.json`: SHA-256 of the exact original public tables.
- `reconciliation_receipt.json`: scoped verdict and limitations.

The independent reconstruction script and detailed review are retained in
`private_archive/turn18_reconciliation_2026-11-12/review/`. Its `reconcile.py`
runs from the repository root with the project Python and rewrites that
private directory's two comparison CSVs from the input-manifest paths.
The primary proxy ratio is `native_enthalpy_2.5_over_injected /
all_total_over_injected`, selecting index30 and threshold100. The component
share is `(ambient_thermal + ambient_kinetic) / (all_thermal + all_kinetic)`
at index20/threshold100; columns use the common labelled-input normalization.

The independent residual uses the exact whole-grid age to scale the matched
coarse H+P contrast by `(actual_age / nominal_age)^2`. Its mass-scaled variant
multiplies that contrast by the published production/coarse 50-Myr mass
ratio. It then subtracts from whole-grid stored change/labelled input minus
one. Sources are pinned at the earlier evidence commits referenced by the
ledger; `review_manifest.json` binds this directory and archive pointers.

The bulk audit is retained at
`nectar:/data/share/xray_cavities/turn18_reconciliation_2026-11-11/`.
Both archive hashes were freshly read back after transfer:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `turn18_reconciliation_2026-11-11_r1.tar.gz` | 27416 | `1273c6848bab1e3e6f990c38202d4d4ac36276410a160598070f9081d857ad38` |
| `turn18_accounting_2026-11-11_r1.tar.gz` | 96297 | `75e565371fbd7a64a7095c83041ee3346a3cfa8adbe5cb988cb28bb6bd43c78d` |

Restore the audit bundle's repository-relative private paths in a fresh
checkout after inspecting its members and verifying its hash. The accounting
stage contains source and immutable requests, not native payloads. Private
archives contain access provenance and are not public paper supplements.

The frozen protocol is `configs/background_refit_blind_2026-11-11.json`
at commit `c352554`. Accounting implementations are pinned at `06d233f`.
Native runs use separate immutable requests and prior input receipts; their
job acceptance is operational evidence, not a result in these tables.
