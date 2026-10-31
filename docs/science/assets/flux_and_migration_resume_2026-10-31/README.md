# Flux launch and migration-resume evidence, 31 October 2026

See `docs/exchange/logs/2026-10-31-flux-and-migration-resume.md` for the scientific
and operational interpretation. Job submission or running state does not establish
migration completion or energy closure.

- `pre_device_transition_state_20261031.tar.gz`: original state/log checkpoint
  preserved before the new migration epoch; SHA-256 verified after download.
- `source_signature_inspection_n001_20261031.json`: all-entry comparison on the
  actual copy node; only the recorded device-number transition is permitted.
- `device_transition_checksums.sha256`: frozen and repair-file checksums used by
  the remote launch gate. Paths are relative to the remote migration stage.
- `device-transition-tests.out` and `migration.device-transition.live.out`:
  test-only gate and initial migration evidence from the preserved checkpoint.
- `xray_migration_device_transition_20261031.tar.gz`: exact uploaded repair bundle.
- `q031_flux_stage_20261031_r3.tar.gz`: exact first corrected smoke/analysis bundle;
  retained even after replacement by the cache implementation.
- `q031_flux_stage_20261031_r4.tar.gz`: exact cache implementation bundle, with
  the verified 48-hour analysis queue limit.
- `launch_evidence_20261031.txt`: initial scheduler receipts, transition receipt,
  fresh-epoch verification rows and smoke startup log. Historical launch state.
- `launch_evidence_r4_20261031.txt`: final replacement job and cancellation
  receipts, tests, source checksums and startup logs; SHA-256 verified after download.
- `review_summary.md`: bounded independent review and verification record.
- `superseded_resume_preflight_20261031.py`: failed login-node preflight helper;
  retained solely as provenance and not an active migration entry point.

`checksums.sha256` covers this local evidence directory except itself. The
checkpoint archives and exact stage bundles are retained independently of the
maintained scripts. The frozen 16 October migration code, plan and manifests
remain in their original repository location.
