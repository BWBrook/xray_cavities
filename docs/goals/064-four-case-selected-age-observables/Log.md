# Goal 064 log

## 2026-08-26 - opened and implemented

- Accepted Goal 063 and locked the common paper-analysis ages at
  `10/20/30/40/50 Myr` for all four matched cases.
- Prespecified the first complete factorial observable surface: X-ray/cavity
  and corrected PRAiSE2 at `0/45/90 deg`, with five radio frequencies and
  actual source times retained.
- Kept the two paper tests at the centre of the tranche: cavity-energy bias
  versus valid shock Mach, and inferred versus known bipolar jet power.
- Generalized the accepted corrected-PRAiSE2 selected-age implementation to
  all four cases. Structural pressure-history validation remains fail-closed;
  only G-LO-specific aggregate counts were replaced by recorded case-specific
  counts.
- Added a deterministic four-case X-ray/cavity assembler. Tracer remains a
  post-hoc comparator; quantitative energy requires exactly two non-crossing
  opposite-side X-ray components.
- Added one four-core X-ray wrapper and one reusable case-isolated radio
  wrapper. The planned execution is one X-ray job plus four independent radio
  jobs, split at genuine restart boundaries rather than exploratory rungs.
- Focused tests passed: `52 passed`. Both PBS wrappers passed `bash -n`.

## 2026-08-26 - remote preflight and submission

- Refreshed the authorized TPAC Open OnDemand SSH selector through Chrome,
  then returned to the repository helpers for all terminal operations.
- Staged the exact reviewed scripts, wrappers, corrected PRAiSE2 source at
  commit `73210e15d4c60e77ffb317b3ee2b9209c049edd4`, and Python compatibility
  layer under
  `/u/bwbrook/codex_kunanyi/goal064_four_case_selected_age_observables`.
- Remote hashes and wrapper syntax passed. The final auditable preflight
  validated all four exact `5001`-file particle sequences, all four Goal 062
  fluid manifests, all `20` selected HDF5 surfaces with shape
  `(1014, 960, 960)`, the PRAiSE2 source hash/import, the no-overwrite target,
  and the enabled `normal` queue with maximum walltime `48:00:00`.
- Submitted and verified running exactly five jobs:
  `787293.kunanyi-ohpc` (`four_xcav`), `787294.kunanyi-ohpc`
  (`c_hi_selrad`), `787295.kunanyi-ohpc` (`c_lo_selrad`),
  `787296.kunanyi-ohpc` (`g_hi_selrad`), and `787297.kunanyi-ohpc`
  (`g_lo_selrad`).
- Invoked the PBS stop rule immediately after the running-state proof; no
  post-submission polling or retrieval occurred.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-26 - launch failure, repair, and resubmission

- Barry reported all five first-attempt jobs returned `Exit_status=1`.
- Retrieved the compact scheduler and stage logs. The four radio jobs directly
  failed with `Errno 122` while writing their first manifests to the scratch
  analysis root. The X-ray job failed in the same launch window with empty
  case outputs, supporting the same operational diagnosis.
- Classified the event as `scratch_analysis_root_quota_exhausted`. No science
  computation started and there were no reusable partial products.
- Preserved the original logs and qstat evidence in `failed_attempt_1/` and a
  stable file-list archive with SHA-256
  `266c29b736e6e0d88b991f87daa4b29fbc7f584d918e543cba5462fbe99246ef`.
- Changed only the transient analysis-root defaults in both Goal 064 wrappers
  from scratch to the enlarged home allocation. Added regression tests for
  that placement; no scientific parameter or raw input changed.
- Revalidated local and remote wrapper syntax and hashes, confirmed the new
  no-overwrite home root was absent, and submitted five replacements.
- Verified running once on `normal`: `787301` (`four_xcav_r1`), `787302`
  (`c_hi_selr1`), `787303` (`c_lo_selr1`), `787304` (`g_hi_selr1`), and
  `787305` (`g_lo_selr1`).
- Invoked the PBS stop rule immediately after the replacement running-state
  proof; no further polling occurred.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-26 - radio dependency failure and cache-resume repair

- The authorized scheduler snapshot showed `C-HI` (`787302`), `G-HI`
  (`787304`), and `G-LO` (`787305`) finished with `Exit_status=1`; X-ray
  (`787301`) and `C-LO` (`787303`) remained running at that snapshot.
- Retrieved the three compact stdout/stderr pairs. Each failed on the same
  missing `plutokore.radio.praise` import after successfully completing its
  history cache.
- Verified all three caches have `next_output=5001`, `5001` time columns, and
  finite endpoint populations. No radio analysis root or archive had been
  created, so the caches were safe to resume without overwrite.
- Patched the wrapper to require `praise.py` and `raytracing.py` and to import
  their required APIs before any cache construction. Added a static regression
  test and validated the APIs locally.
- Created a separate repair stage rather than mutating the stage still used by
  the running `C-LO` job. Staged the two support modules from plutokore commit
  `73210e15d4c60e77ffb317b3ee2b9209c049edd4`; remote hashes, syntax, imports,
  caches, and no-overwrite gates passed.
- Submitted cache-resume jobs `787310` (`c_hi_selr2`), `787311`
  (`g_hi_selr2`), and `787312` (`g_lo_selr2`). All were verified running once
  on `normal`; the PBS stop rule was then invoked.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-26 - C-LO dependency failure and cache resume

- Barry reported `C-LO` job `787303` completed with `Exit_status=1`. Retrieved
  stdout/stderr confirmed the same missing `plutokore.radio.praise` import as
  the other radio cases, after `particle_manifest_validation=passed` for all
  `5001` outputs.
- The interrupted submission command had completed successfully: the repair
  stage recorded `787329.kunanyi-ohpc` (`c_lo_selr2`), and one scheduler check
  verified it running on `normal`.
- No duplicate job was submitted. The C-LO cache was reused, the original
  stage was not mutated, and the PBS stop rule was invoked immediately after
  the running-state proof.

Status: `submitted_waiting_pbs_completion`.
