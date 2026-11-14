# Accounting pilot review evidence

Reviewed 14 November 2026. See the
[scientific note](../../turn18_pilot_review_2026-11-14.md) for interpretation.
These are two fixed-budget pilots at approximately 20 Myr and one G-LO
startup flux interval, not the full four-case accounting histories.

- `fixed_pilot_summary.csv`: five spatial regions for C-LO/20 and G-HI/20,
  with total/component storage, initial/current/delta mass, current-region
  mass changes, ambient shares and an illustrative potential shift.
- `fixed_audit.json`: 460 independent compact identity and old-aperture
  comparisons; input product hashes and precise reconciliation residuals.
- `flux_audit.json`, `endpoint_flux_and_storage.csv`, `startup_scenarios.csv`:
  2,500 independent lower-level balance checks and all quadrature ranges.
  These are sensitivity scenarios, not confidence or error bounds.
- `verification_summary.json`: bounded acceptance, 1,254 provenance checks,
  source/manifest pins, captured inventories and dated full-job states.
- `replay_receipt.json`: all three independent audits pass again after a
  fresh restoration of the 138-member audit archive, using source bytes
  checked against commit 8177795. No native field reintegration occurred.

All energy ratios use labelled bipolar power times actual age. Regional
storage uses current binary tracer masks on the same initial/current cells;
it is not a Lagrangian deposited-energy fraction. Potential shifts obey
DeltaUg(Phi+c) = DeltaUg(Phi) + c DeltaM. Full-cell inset faces and operational
coverage are retained in the archived native products. Initial fluxes are
zero at every saved surface, so the startup time-integration sensitivity
must accompany any outside-nozzle residual.

## Archive and reproduction

All packages are retained at
`nectar:/data/share/xray_cavities/turn18_pilot_review_2026-11-14/`.
Fresh remote readback matches these SHA-256 hashes:

| Archive | Bytes | SHA-256 |
| --- | ---: | --- |
| `turn18_pilot_results_capture_2026-11-14_r1.tar.gz` | 111306 | `1ee2e47dc449761d231f98caf5a0b1f3369aa1065708a75931c1af7b9d9f0241` |
| `turn18_full_submissions_capture_2026-11-14_r1.tar.gz` | 30750 | `d7608cbb21b93879d848f5a25ac857b5fa07150c741dbbdbded65104a4295e0e` |
| `turn18_pilot_review_audit_2026-11-14_r1.tar.gz` | 596553 | `32cc0883508a3091af5d1dfa310c1a6413f542c40004f6d9816b7c680ff3d714` |

Use a fresh project checkout with the scientific Python environment. Verify
the audit archive hash and safe regular member paths, then extract it at the
repository root. Its members already have repository-relative private paths.
It includes both captures, the original R2 package/archive, selected earlier
native contracts and receipts, and the independent scripts/reports. Raw
native HDF5 fields are absent. Access details in raw scheduler/receipt records
remain private; this is not a public paper supplement.

With analysis source matching commit **8177795**, and the accepted earlier
`docs/science/assets/turn15_review_2026-11-11/budgets/` CSVs present, run:

```bash
.venv/bin/python private_archive/turn18_pilot_review_2026-11-14/audit_fixed_pilots.py
.venv/bin/python private_archive/turn18_pilot_review_2026-11-14/flux_audit/independent_flux_audit.py
.venv/bin/python private_archive/turn18_pilot_review_2026-11-14/provenance_audit/audit.py
```

The scripts rewrite audit reports in that fresh restoration. Preserve the
archived originals. The source-dependent provenance audit also compares
working source hashes with the pinned committed bytes, so later source
changes require an appropriate checkout rather than weakening its gate.
The public fixed and flux summaries are copies of the successful audit outputs;
startup scenario minima/maxima are taken from `flux_audit.json`.
