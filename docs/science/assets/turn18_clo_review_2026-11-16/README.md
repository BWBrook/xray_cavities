# C-LO full accounting history evidence

Reviewed 16 November 2026. The
[scientific note](../../turn18_clo_history_review_2026-11-16.md) gives the
interpretation. This is one case's 51-snapshot fixed-budget and flux history,
not acceptance of all four cases or physical energy closure.

- `fixed_history.csv`, `regional_mass_energy.csv`, `coverage.csv`: signed
  storage, initial/current/delta mass, potential-shift identities and
  operational containment at indices 0–50. Input-normalized ratios are
  undefined at index 0 and left blank.
- `fixed_audit.json`: 11,511 compact arithmetic and older-aperture comparisons.
- `cumulative_flux_scenarios.csv`, `selected_flux_scenarios.csv`: 300 cumulative
  reconstruction/quadrature summaries and 48 selected scenario summaries.
  Minima/maxima span nozzle-control padding/reconstruction variants.
- `flux_audit.json`: 140,640 scalar and 15 hash checks. The direct first-pass
  report, `flux_direct_firstpass.json`, preserves 122 cumulative mass flags.
  Sequential-versus-fsum cancellation differences are covered by propagated
  summation/rounding bounds in the final audit; producer data were unchanged.
- `fixed_flux_storage_comparison.json`: 306 cross-reduction storage checks.
- `verification_summary.json`: bounded acceptance, 20,393 provenance checks,
  source/manifest pins, complete inventories and dated scheduler observations.
- `replay_receipt.json`: all four audit scripts pass after a fresh restoration
  of the 294-member audit archive, with source checked against commit 8177795.
- `figures/`: inspected PNG/PDF and a renderer/input hash receipt.
- `manifest.json`: byte counts and SHA-256 hashes for these public files,
  the scientific note and renderer; the manifest excludes itself.

Energy ratios use labelled bipolar power times actual age, not measured
numerical delivery. Regional storage uses current masks on the same
initial/current cells in a fixed centre-zero potential. Signed shares are
not deposition efficiencies. Scenario ranges are sensitivity comparisons,
not confidence intervals or certified physical error bounds.

## Archive and reproduction

Both packages are retained at
`nectar:/data/share/xray_cavities/turn18_clo_review_2026-11-16/`.
Fresh remote readback matches these SHA-256 hashes:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `turn18_clo_history_capture_2026-11-16_r1.tar.gz` | 2340494 | `00401e3040412831336de7b9f4e4d8e9bcca5cfa5311560d71fb63e7ff07ef29` |
| `turn18_clo_review_audit_2026-11-16_r1.tar.gz` | 5089577 | `eda2015ef144e92ac7a319aa652ae838c8b3399bd058961fbd316f256cb4571c` |

Verify the audit archive hash and safe regular member paths, then extract
into a fresh project checkout. Its members already have repository-relative
private paths. It includes the capture, original R2 package/archive, selected
earlier contracts and completion records, and independent scripts/reports.
Raw HDF5 fields are absent. Raw access/scheduler records remain private.

With analysis source matching **8177795** and the accepted earlier
`docs/science/assets/turn15_review_2026-11-11/budgets/C-LO/measurements.csv`
present, run from the repository root:

```bash
.venv/bin/python private_archive/turn18_clo_review_2026-11-16/audit_fixed_history.py
.venv/bin/python private_archive/turn18_clo_review_2026-11-16/flux_audit/independent_flux_history_audit.py
.venv/bin/python private_archive/turn18_clo_review_2026-11-16/flux_audit/compare_fixed_whole_grid.py
.venv/bin/python private_archive/turn18_clo_review_2026-11-16/provenance_audit/audit.py
```

These scripts rewrite reports in that fresh restoration; preserve archived
originals. The provenance audit checks working source against pinned Git
bytes. Later source changes require the matching checkout rather than a
weakened gate. These are compact audits and saved-receipt bindings, not
independent native reintegration or solver-step source measurements.

Re-render the public figure with the scientific Python environment:

```bash
.venv/bin/python scripts/science/render_clo_history_review.py \
  --inputs docs/science/assets/turn18_clo_review_2026-11-16 \
  --output /private/tmp/clo-history-figure
```

The top panel has 50 nonzero-input epochs. Each lower-panel envelope spans
all three time quadratures and all nozzle variants for one outer-face
reconstruction. The receipt binds the two input CSVs and renderer; PDF
metadata can change on rerendering.
