# Turn 11: validated flux release

Barry authorised resolving the stale flux dependency so flux and native
emission could proceed, keeping validation gates intact. Claude's response
on discussion 29, message 2870, was read. The later scientific sequence is
BND-02 whole-grid paired contrasts, interior cuts, then production spherical
budgets and the independent 20-Myr shock/emission diagnostic. None of those
new analyses was performed in this release turn.

## Repair and verification

The frozen r5 flux wrapper compared the raw migration plan against the
normalized binding, which additionally contains schema version 2. That check
would fail after releasing the stale hold. `prepare_q031_flux_release.py`
creates a separate immutable launch overlay using the already-tested native
migration validator. Science code, source checks, smoke gates, packaging,
output locations and resource limits remain unchanged. The overlay refuses
existing destinations and stale wrapper sources and checks its own payloads
before execution. An independent reconstruction matched its complete manifest.

- Flux stage: 8 checksum entries passed; native stage: 41; runtime: 3.
- All ten migration units, plan binding, receipts, links and final event passed.
  This is small-file/state validation, not another hash of all 8.8 TB.
- Recovered flux-smoke archive contents and exact receipt passed revalidation.
- Native smoke receipt and its runtime binding passed: 104 tests, zero skips.
- Local release, migration and packaging suites: 41 passed.
- Target startup: 18 passed; `MIGRATION_COMPLETE_GATE_OK` observed.

Reproduce the local focused checks with:

```sh
.venv/bin/python -m pytest -q tests/test_q031_flux_release.py tests/test_q031_native_dependencies.py tests/test_q031_flux_packaging.py
```

## Scheduler outcome

At 00:01:46 UTC on 4 November, replacement flux **876162** was running with
no hold (2 CPUs, 8 GB, 48-hour limit). Native pilot **871717** was system-held
on exactly `afterok:876162`; its own migration, flux-result, smoke and source
validation gates remain active.

The old job **870374** is renamed `superseded_flux` and user-held. PBS retained
its reverse references to 870719 and 871717 after the forward dependency was
changed; attempts to clear with an empty dependency were rejected, and
replacing the afterok list did not remove beforeok references. Cancellation
was therefore withheld to avoid affecting the live successor. Do not release
this obsolete job. After the native job is terminal, check all successors
before removing it. No duplicate analysis is running.

The downloaded capture contains 23 payloads, all locally hash-verified, and
is 30,396 bytes with SHA-256
`1468815f0609c16687b5f23960e144efb90a32f2225097577fd50560d78db6fb`.
Unredacted scheduler receipts are retained in ignored
`private_archive/q031_flux_release_2026-11-04/`; the publishable receipt is
`docs/science/assets/q031_flux_release_2026-11-04/release_summary.json`.
No flux production completion or native-pilot result is claimed.

## Scientific review follow-up

Message 2871 flags two corrections before subsequent analysis: the adopted
scale at 0.25 Myr is 1.58e56 erg, not 1.58e54; an absolute allowance of
0.01 E_inj cannot guarantee second-significant-figure accuracy for a regional
value of 0.013 E_inj (the allowance is about 77% of that value). The L1 bound
is an absolute error budget. The shock finder's claimed discrimination remains
conditional on its required synthetic validation. These issues do not change
the already-defined flux/native pilot. No scientific criterion was edited.
