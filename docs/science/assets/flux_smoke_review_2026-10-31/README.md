# Completed G-LO smoke and recovery evidence

Scientific interpretation: `docs/science/q031_flux_smoke_review_2026-10-31.md`.
Execution and coordination: `docs/exchange/logs/2026-10-31-flux-smoke-review-and-recovery.md`.

- `r4_original_compact_smoke.tar.gz` and `results_smoke/`: original downloaded
  r4 archive and extracted files. Numerical outputs completed before PBS failed
  during packaging; each scientific file passes its case manifest.
- `numerical_review.json`: 144 independently recomputed mass/energy balances and
  reported source/nominal ratios.
- `q031_flux_stage_20261031_r5.tar.gz`: exact uploaded packaging-repair bundle.
- `review_evidence_20261031.tar.gz` and `remote_review/`: final downloaded
  scheduler receipts, migration progress snapshot, real-snapshot cache comparison,
  successful packaging-recovery logs, recovered archive and its receipt.

The recovered archive's six members were independently verified locally against
its receipt. `remote_review/migration_progress_review_20261031.json` counts durable
fresh verification receipts and checks source/archive link metadata; it does not
rehash raw files or establish quota recovery.

The directory-local `.gitattributes` preserves downloaded result and receipt bytes so Git
line-ending conversion cannot invalidate the remote manifests. These raw evidence
files are excluded from textual diff checks. `checksums.sha256`
covers all local files except itself. Failed/superseded remote stages remain.
