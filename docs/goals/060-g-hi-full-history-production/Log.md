# Goal 060 log

## 2026-08-20 - G-HI submitted

- Goal 059 was committed and pushed to `main` as `27325d5`, leaving a clean
  baseline for the final production case.
- Rechecked the authenticated TPAC storage gate: `20 TiB` allocated and
  `8 TiB` occupied. The `2.819 TiB` conservative G-HI forecast fits; a
  temporary `16 MiB` scratch write probe passed and was removed.
- Added `G-HI` to the deterministic configuration renderer as group
  `002_031`, one-sided jet power `1e45 erg s^-1`, and speed `0.1c`.
- Rendered and validated the matched `50 Myr`, `1/5 Myr` fluid, and `0.01 Myr`
  particle-history contract from the trusted group table.
- Added a fresh, no-overwrite 64-node wrapper using `1792` ranks,
  `48:00:00` PBS walltime, `47.5` PLUTO runtime hours, and the established
  progress watchdog. It contains no follow-on, analysis, compaction, or
  deletion work.
- Local syntax and `26` focused tests passed.
- Staged the SHA-matched wrapper, production template, watchdog, rendered
  config, and group atmosphere under
  `/u/bwbrook/codex_kunanyi/goal060_g_hi_full_history_production`.
- Remote hash, syntax, case/asset, no-overwrite, source, module, scratch-write,
  and queue gates passed.
- Submitted exactly one job: PBS `786189.kunanyi-ohpc` / `g_hi_hist`.
  Verified state `Q` in `normal`, `64` nodes, `1792` CPUs, and `48:00:00`
  walltime.
- Invoked the PBS stop rule immediately. No polling, post-processing,
  compaction, source deletion, retry, or second job followed.

Decision: `G_HI_FULL_HISTORY_PRODUCTION_SUBMITTED`.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-20 - Quota stop diagnosed

- Barry reported PBS `786189.kunanyi-ohpc` completed with `Exit_status=124`,
  `11:06:32` walltime, and `1792` CPUs.
- Final qstat confirmed state `F`, `Stageout_status=1`, and the reported
  resource use. Stage stdout records `MPI_EXIT_CODE=124` and
  `FAILURE_REASON=no_progress_watchdog_timeout`.
- The run was scientifically normal through float HDF5 index `14` and
  particle history `1499`, then stopped while writing the uncatalogued,
  incomplete `data.0003.dbl.h5` at `15 Myr`.
- A live `1 MiB` scratch write-and-fsync probe failed with `Disk quota
  exceeded` while the global filesystem remained `50%` full. The project run
  tree occupied approximately `7.9 TiB`. This identifies quota enforcement as
  the underlying failure, not a numerical instability.
- The portal continued to display unlabeled exact `20 TiB` and `8 TiB` byte
  values. That display is inconsistent with live scratch enforcement and
  requires TPAC clarification or repair.
- The `10 Myr` restart tuple passed the established structural validator:
  HDF5 index `2`, float companion `10`, particle index `1000`, step `10011`,
  matching times, required datasets, `1014 x 960 x 960` shape, and `39,764`
  finite uniquely identified particle records.
- Retrieved only compact stdout/stderr, watchdog, catalogues, and launch logs.
  No raw data was copied, changed, compacted, or deleted. No retry was
  submitted.

Decision: `G_HI_QUOTA_STOP_RESTART_SURFACE_GREEN_NO_RETRY_BEFORE_QUOTA_REPAIR`.

Status: `blocked_scratch_quota_enforcement_mismatch_restart_ready`.

## 2026-08-21 - Quota-domain correction

- Patrick clarified that the portal values are separate quotas, not allocation
  and usage: home `/u/bwbrook` has `20 TiB`; scratch `/scratch/bwbrook` remains
  capped at `8 TiB`.
- Confirmed Goal 060 explicitly wrote its heavy run tree under scratch. Live
  usage was `8,796,423,717,628` bytes on scratch versus only
  `2,636,233,412` bytes in home.
- A disposable `16 MiB` home write, `fsync`, checksum, and cleanup passed.
- `/usr/local/bin/quota_status.sh` currently exits without a report because
  `/u/bwbrook/.tpac-quota` is absent. This site-helper metadata defect is not a
  write blocker.
- The validated 10 Myr restart remains unchanged. No retry or raw-data mutation
  occurred during this correction.

Decision: `G_HI_SCRATCH_QUOTA_STOP_HOME_CONTINUATION_READY`.

Status: `restart_ready_home_destination_verified`.

## 2026-08-21 - Home continuation submitted

- Added a dedicated home-resident continuation wrapper and four focused tests.
  The integrated restart/watchdog suite passed `76` tests; local and remote
  shell syntax passed.
- Staged the SHA-matched wrapper, production template, watchdog, validator, and
  accepted G-HI configuration under
  `/u/bwbrook/codex_kunanyi/goal060_g_hi_full_history_home_continuation`.
- Prepared an isolated target under
  `/u/bwbrook/xray_cavities_runs/2026-08-21-g-hi-full-history-home-continuation`.
  It contains compact problem state and only the selected double index `2`,
  float index `10`, and particle index `1000` restart surfaces. Partial double
  index `3` is absent.
- The wrapper pins the home path, rechecks a `16 MiB` write-and-fsync gate, and
  revalidates the exact fluid/particle tuple on the compute node before MPI.
- Submitted exactly one recovery job: PBS `786326.kunanyi-ohpc` /
  `g_hi_hist_r1`. Verified state `Q` in `normal`, `64` nodes / `1792` CPUs,
  and `48:00:00` walltime.
- Invoked the stop rule immediately. No polling, deletion, compaction,
  post-processing, or second job followed.

Decision: `G_HI_HOME_CONTINUATION_SUBMITTED`.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-23 - Home continuation completed

- Barry reported PBS `786326.kunanyi-ohpc` / `g_hi_hist_r1` completed with
  `Exit_status=0`, `28:08:03` walltime, and `1792` CPUs. Final qstat confirmed
  state `F`; `Stageout_status=1` remains a scheduler caveat.
- The target has `markers/DONE`, no `markers/FAILED`, empty stderr, and stdout
  markers for the home write gate, restart-pair validation, HDF5 restart 2,
  and `MPI_EXIT_CODE=0`.
- The endpoint HDF5 and particle files both have exact code time
  `15330.0696894`. The HDF5 carries all six required `1014 x 960 x 960`
  fields; particle index `5000` contains `193,741` structurally valid records.
- A compact split-root audit proved complete, nonempty canonical sequences:
  double HDF5 `0..2` from scratch plus `3..10` from home; float HDF5 `0..10`
  plus `11..50`; particles `0..1000` plus `1001..5000`.
- Retrieved only compact qstat, stdout/stderr, catalogues, watchdog, manifests,
  and JSON/CSV validation evidence. No raw HDF5 or particle payload was copied
  or changed.
- The home continuation occupies approximately `2.2 TiB`. The failed scratch
  root remains required for the canonical early segment and must be preserved
  until those selected files are reduced or moved.

Decision: `G_HI_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_RAW_FACTORIAL_COMPLETE`.

Status: `complete_full_history_endpoint_split_root_canonical_sequence_green`.
