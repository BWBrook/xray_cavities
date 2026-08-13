# Goal 056 log

## 2026-08-10 - submitted and waiting

- Fast-forwarded to supervisor commits `bbbd8cb` and `2f5a405` before work.
- Implemented Patrick's deterministic latest-shock-only comparison across
  pinned PRAiSE1, native PRAiSE2, common-input PRAiSE2, and the Goal 050
  diagnostic comparator.
- Bound the immutable 4096-particle selection, comparator, 33 GB history cache,
  and pinned `plutokore` commit by SHA-256/provenance checks.
- Added per-particle pressure, Lorentz-factor, spectra, method-ratio, cutoff,
  divergence, and population-summary outputs with readable 2x2 figures.
- Local focused validation passed: `13 passed`; wrapper syntax and
  `git diff --check` passed.
- The first remote import gate caught that only one of the established Kunanyi
  compatibility shims had been staged. No job had been submitted and no
  analysis root existed.
- Required and staged the existing `contextlib2.py`, `hdf5plugin.py`, and
  import-only `yt.py` shims; regenerated and verified the complete remote
  manifest; the remote import gate then passed.
- Submitted `784909.kunanyi-ohpc` and verified `g_lo_lstcmp` queued in `normal`
  with `1:ncpus=16:mem=96gb`, walltime `24:00:00`.
- Invoked the PBS stop rule immediately after queued-state verification.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-11 - first attempt failed; repaired retry submitted

- PBS `784909.kunanyi-ohpc` finished with `Exit_status=1`. Staged hashes,
  cache/input checks, and runtime imports passed before the diagnostic failed.
- The first scientific-code failure was an invalid gate requiring every
  irregular source timestep to survive PRAiSE2's 0.01 Myr nearest-source
  resampling. Omitted intermediate source indices are expected behaviour.
- The wrapper then failed to archive the diagnostic evidence because the
  byte-preserved helper had mode `0600` and was invoked directly.
- Focused review found the associated replay also smoothed the irregular
  source history before resampling, whereas pinned PRAiSE2 resamples first,
  backfills, and only then smooths pressure and density.
- Added one shared single-particle contract and explicit source-index mapping
  so the actual call and diagnostic replay use identical preprocessing.
- Local validation passed: `15 passed`; wrapper syntax and `git diff --check`
  passed. A Kunanyi-side synthetic irregular-history test also reproduced
  pinned PRAiSE2 for native smoothing while intentionally omitting one source
  timestep.
- Preserved the original stage and failure logs. Staged the repair at
  `/u/bwbrook/codex_kunanyi/goal056_g_lo_praise_last_shock_comparison_r1` and
  bound fresh analysis root
  `/scratch/bwbrook/xray_cavities_analysis/2026-08-11-g-lo-praise-last-shock-comparison-r1`.
- Submitted exactly one retry, PBS `784931.kunanyi-ohpc` / `g_lo_lstcmp_r1`,
  and verified it queued in `normal` with one node, 16 CPUs, 96 GB, and
  `24:00:00` walltime. Invoked the stop rule immediately.

Status: `repair_submitted_waiting_pbs_completion`.

## 2026-08-11 - retry failed; state-aware comparator repair submitted

- PBS `784931.kunanyi-ohpc` finished with `Exit_status=2`. Its inputs,
  imports, PRAiSE2 preprocessing, and population work progressed to the
  representative detailed panel before failure.
- The failure was the contextual Goal 050 comparator treating every frequency
  as finite despite Goal 050 already carrying per-frequency cutoff,
  subrelativistic, and unavailable states. No Goal 056 science decision was
  produced.
- Retrieved the successful compact failure archive plus stdout/stderr and
  preserved the retry stage unchanged. The archive SHA-256 is
  `c3ef7c511814f69e413d7ddacf8197ce999dc7597f6da82214c685cf7f752662`.
- Added a narrow state-aware reconstruction: explicit cutoffs remain zero,
  finite states are reconstructed, and non-finite/subrelativistic comparator
  states are retained as unavailable. PRAiSE2 gates are unchanged.
- Local focused validation passed (`16 passed`). The staged Kunanyi manifest,
  wrapper syntax, SHA match, and exact synthetic state-aware comparator proof
  also passed.
- Submitted one final retry, PBS `784939.kunanyi-ohpc` / `g_lo_lstcmp_r2`,
  under fresh stage and analysis paths. It was verified queued in `normal`
  with one node, 16 CPUs, 96 GB, and walltime `24:00:00`; the stop rule was
  invoked immediately.

Status: `repair2_submitted_waiting_pbs_completion`.

## 2026-08-11 - final run completed; science hold reassessed locally

- PBS `784939.kunanyi-ohpc` finished with `Exit_status=3` after `02:16:15`.
  This was the wrapper's intentional science-hold exit; the diagnostic and
  archive completed successfully.
- Retrieved and validated the 31-member archive, stdout, stderr, and run log.
  Archive SHA-256:
  `17f829a509822960dabd6f6ae799dd9cc9636d46331436fc359023989ca644b4`.
- Native retained pressures were all positive and no native numerical failure
  occurred. `62/62` applicable direct full-loss replay checks matched exactly.
- The two raw replay failures were native/common views of one width-one
  representative history. The population path already uses the approved
  lossless-equals-full singleton convention; the detailed path accidentally
  invoked full loss directly. Singleton histories are `48/4096` and only
  `0.0243%` of represented weight.
- Corrected that local diagnostic contract and added a regression test. No
  fourth remote run was submitted; the immutable original product retains its
  hold label and the local review records the reassessment.
- Common-input PRAiSE2 differences from PRAiSE1 persist materially for
  `17.96%` of weight at `0.15 GHz`, `27.17%` at `1.4 GHz`, and `12.79%` by
  spectral index. Native smoothing alone is material for only `0.756%` of
  weight and `0%` by spectral index.
- Decision:
  `PRAISE2_USABLE_METHOD_DIFFERENCE_PERSISTS_PATRICK_CONFIRMATION_REQUIRED`.
  Request Patrick's confirmation before matched history production.

Status: `complete_diagnostic_review_requested`.

## 2026-08-13 - Patrick accepted Goal 056; coefficient follow-up opened

- Patrick accepted the latest-shock-only validation and selected PRAiSE2 as
  the published-method reference.
- The current pinned PRAiSE2 result remains immutable baseline provenance.
- The published equation (3) radiative term contains `4 sigma_T/(3 m_e c)`,
  while the pinned PRAiSE2 coefficient is `0.7500000023105955` of that value.
- Opened `Q-027` to restore the missing `4/3` multiplier, isolate its effects
  on particle spectra, emissivity, luminosity, surface brightness, spectral
  index, and cutoff state, and validate the corrected implementation.
- Corrected PRAiSE2 becomes the production radio method after that bounded
  coefficient validation passes; matched production must not use the
  uncorrected coefficient.

Status: `complete_reference_accepted_coefficient_followup_required`.
