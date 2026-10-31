# Flux smoke review, packaging recovery and migration progress

Barry's Codex instruction on 31 October: “Check how the migration and flux jobs
are progressing, and review any completed results. Keep coordinating with Claude:
they've responded just now.”

## Live execution evidence

At 04:34 UTC (15:34 AEDT), migration 870323 is running, walltime 44m32s. Units
0–7 remain complete with exact compatibility links, existing destinations and
no tombstones. Unit 8 (C-HI) remains copied and is actively verifying; fresh
epoch receipts increased from 67,319,936,967 bytes (11 files) during the first
check to 112,210,521,648 bytes (13 files). Its total regular-file payload is
3,090,276,948,775 bytes, so 3.63% has fresh receipts at the latter capture.
C-LO remains unstarted. No source or tombstone was manually removed and no new
quota-recovery claim is made. Receipt reading does not rehash the raw payloads.

Flux smoke 870352 finished its two numerical snapshots but exited 1 at packaging:
`tar: results_smoke: file changed as we read it`. The dependent full job 870353
finished without running its analyses. The original stage and archive remain.

The original archive and all four manifested scientific files were downloaded
and verified. Independent calculation reproduced 144 scalar balances. The
first snapshot's cached and original direct-read flux/storage rows are exactly
equal, excluding only the different stage-local input symlink path. Results
and interpretation are in `docs/science/q031_flux_smoke_review_2026-10-31.md`.

## Bounded repair and replacement job

`scripts/kunanyi/package_q031_flux_results.py` packages exactly the completion
receipt and each case's manifest plus four scientific outputs. It excludes live
logs, test directories, input symlinks and checkpoints. The finished archive is
reopened and its member list, types, sizes and hashes checked against hashes
accepted during input validation. Same-size mutation after validation fails
closed. Existing outputs cannot be overwritten. Normal runs and recovery use
the same helper; the scientific runner and migration are unchanged.

The local combined suite passed 18 tests. The helper repackaged the actual
completed smoke locally. The new r5 bundle SHA-256 is
`918208ccf437f2ea586beadf773bf8c586fa293ddf2241f36a433a60daae35b2`.
It was uploaded to the retained r4 directory, hash-checked, and extracted into
fresh `/u/bwbrook/codex_kunanyi/q031_flux_measurements_2026-10-31_r5`.

- Recovery 870373: exit 0 after 19 seconds. All three packaging tests passed on
  Kunanyi. The existing r4 science was validated and packaged without rerunning
  either snapshot. The verified six-member archive SHA-256 is
  `9b77439162feaad2550afac06e750c3925c69f34b7a4332f8b6964a178a09e61`.
- Replacement full 870374: held with
  `afterok:870373.kunanyi-ohpc:870323.kunanyi-ohpc`, 2 CPUs / 8 GB / 48 h.
  The existing independent migration completion gates remain in the wrapper.
- Migration 870323: unchanged; still running.

Downloaded evidence bundle SHA-256:
`b368aa371b2bf4853c46857cc3893089c5d94f754086e56c1a96ff51aeedd1af`.
The recovered archive was independently checked again locally against its
six-member receipt. Evidence is under
`docs/science/assets/flux_smoke_review_2026-10-31/`.

## Claude coordination

Read Claude's message 2676 and verified main at fa175db: Q-032 is merged and
HANDOFF is archived. Only current_status.md is updated as the live handover.
Messages 2679 and 2682 report the smoke failure, numerical review and successful
packaging recovery. Messages 2680/2681 send the independent Q-032 audit and
qualify the rim-mass estimate as a local uniform-density approximation.

The Q-032 audit supports the legacy-null failure but identifies a material rim
thermodynamic mismatch, inconsistent summary statistics, a newline-induced
manifest defect and unresolved oracle/topology assumptions. Claude retains
ownership of corrections. The review is in
`docs/science/q032_independent_review_2026-10-31.md`; no replacement detector,
production outputs or manuscript claims were promoted. No scheduled monitoring
or new PLUTO run was created.
