# Goal 061 log

## 2026-08-23 - cadence mismatch reviewed; matched G-LO rerun submitted

- Committed and pushed the completed Goal 060 G-HI package to `main` as
  `7da978e`, establishing a clean production baseline.
- Audited the live four-case raw inventory. `C-HI`, `C-LO`, and canonical
  split-root `G-HI` each provide the matched `51/11/5001`
  float/double/particle surface. Historical `G-LO` provides complete particle
  histories but only six accepted fluid ages at `0/10/20/30/40/50 Myr`.
- Determined that six ages remain sufficient for coarse common-age work but
  under-sample the planned shock, cavity-recovery, and transition analyses.
  With compute and home quota available, one final matched-cadence rerun is
  justified rather than encoding this imbalance into downstream methods.
- Added a fresh G-LO production wrapper and three focused contract tests. The
  wrapper pins output to home, uses the proven 64-node/1792-rank scale,
  requests `48:00:00`, retains the progress watchdog, rejects overwrite, and
  includes no analysis, compaction, deletion, or follow-on submission.
- Rendered the accepted group `002_031`, `1e43 erg s^-1`, `0.1c`, `50 Myr`
  configuration with `1/5/0.01 Myr` float/double/particle cadences.
- Local focused tests passed (`10 passed`); wrapper syntax and
  `git diff --check` passed.
- Staged the SHA-matched inputs under
  `/u/bwbrook/codex_kunanyi/goal061_g_lo_matched_full_history_production`.
- Remote no-overwrite, home-headroom, `16 MiB` write-and-fsync, hash, syntax,
  rendered-contract, atmosphere, source/module, and queue gates passed. Home
  usage was `2,394,234,566,848` bytes against the `20 TiB` quota.
- Submitted exactly one PBS job: `786516.kunanyi-ohpc` / `g_lo_hist2`.
  Verified state `Q` in `normal`, `64` nodes / `1792` ranks, and `48:00:00`
  walltime.
- Invoked the PBS stop rule immediately. No polling, post-processing,
  compaction, deletion, retry, or second job followed.

Decision: `G_LO_MATCHED_FULL_HISTORY_PRODUCTION_SUBMITTED`.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-25 - matched G-LO endpoint accepted

- Barry reported PBS `786516.kunanyi-ohpc` / `g_lo_hist2` completed with
  `Exit_status=0`, `30:01:35` walltime, `838:17:26` CPU time, and `1792`
  CPUs. Final qstat confirmed state `F`; `Stageout_status=1` remains a
  scheduler caveat.
- Retrieved compact qstat, stdout/stderr, marker, catalogues, restart record,
  and validation JSON only. Remote and local SHA-256 values matched for every
  retrieved file; no raw HDF5 or particle payload was copied.
- The run has `DONE`, no `FAILED`, `RUN_KIND=fresh`, and `MPI_EXIT_CODE=0`.
  Stderr contains only the known nonfatal 93-byte missing-`git` warning.
- Validated continuous non-empty sequences: `51` float HDF5 files (`0..50`),
  `11` double HDF5 files (`0..10`), and `5001` particle histories (`0..5000`).
- Both fluid endpoints carry exact code time `15330.0696894`, all six required
  fields, shape `1014 x 960 x 960`, and finite boundary samples.
- The endpoint restart validator bound double index `10` to particle index
  `5000` at step `49462` and exact matching time. All `197,568` particle
  records passed schema, file-size, finite-content, and unique-ID checks.
- The remote raw output occupies approximately `2.9 TiB`. Goal 061 now becomes
  the canonical G-LO source for matched analysis; the older compacted roots
  remain protected historical provenance.
- No post-processing, compaction, deletion, retry, or follow-on submission
  occurred.

Decision:
`G_LO_MATCHED_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_MATCHED_RAW_FACTORIAL_COMPLETE`.

Status: `complete_matched_full_history_endpoint_green`.
