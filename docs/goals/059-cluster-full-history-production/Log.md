# Goal 059 log

## 2026-08-17 - quota gate opened; matched cluster runs submitted

- Confirmed the approved Kunanyi storage increase on the authenticated TPAC
  dashboard: `20 TiB` allocated and `8 TiB` occupied, implying about `12 TiB`
  headroom before launch.
- Retained Goal 057's conservative forecast of `2.819 TiB` raw per case. The
  two cluster reruns therefore forecast `5.638 TiB` before retention, within
  the approved allocation with operational headroom.
- Restored and validated the ignored Stewart cluster `002_003` atmosphere
  table (`4000` rows, `6` columns; SHA-256
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`).
- Rendered asset-backed `C-HI` and `C-LO` particle configurations under the
  locked `50 Myr`, `1/5 Myr` fluid, and `0.01 Myr` particle-output contract.
- Added fresh, no-overwrite 64-node production wrappers for both cases. Each
  uses `1792` ranks, `48:00:00` PBS walltime, `47.5` PLUTO runtime hours, and
  the established progress watchdog; neither performs post-processing or
  cleanup.
- Local validation passed: both wrappers/template/watchdog parsed, `23`
  focused tests passed, and `git diff --check` was clean before submission.
- Staged the SHA-matched wrappers, production template, watchdog, rendered
  configs, and Stewart table under
  `/u/bwbrook/codex_kunanyi/goal059_cluster_full_history_production`.
- Remote hash, syntax, configuration/asset, no-overwrite, source, module, and
  queue gates passed. The queue supports the requested `48:00:00` walltime.
- Submitted PBS `785822.kunanyi-ohpc` / `c_hi_hist`; verified state `R` in
  `normal`, `64` nodes, `1792` CPUs, and `48:00:00` walltime.
- Submitted PBS `785823.kunanyi-ohpc` / `c_lo_hist`; verified state `Q` in
  `normal`, `64` nodes, `1792` CPUs, and `48:00:00` walltime.
- Invoked the PBS stop rule immediately after scheduler proof. No polling,
  retrieval, compaction, post-processing, source deletion, or `G-HI`
  submission followed.

Decision: `CLUSTER_FULL_HISTORY_PRODUCTION_SUBMITTED_QUOTA_GATE_GREEN`.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-19 - C-HI full-history endpoint accepted

- Barry reported PBS `785822.kunanyi-ohpc` / `c_hi_hist` complete with
  `Exit_status=0`, `32:30:03` walltime, `907:44:00` CPU time, and `1792` CPUs.
- Read-only final scheduler evidence matched and retained
  `Stageout_status=1` as a caveat. Direct stage-root logs were available and
  retrieved; no raw HDF5 or particle files were copied locally.
- Stdout records `RUN_KIND=fresh`, `MPI_EXIT_CODE=0`, and a normal job end.
  The `DONE` marker is present and `FAILED` is absent. Stderr contains only the
  known nonfatal `git: command not found` source-metadata warning.
- Validated continuous and non-empty output indices: `51` float HDF5 files
  (`0..50`), `11` double HDF5 files (`0..10`), and `5001` particle histories
  (`0..5000`).
- Opened both endpoint HDF5 files independently. Their expected timestep
  groups contain `rho/prs/tr1/vx1/vx2/vx3`, common shape
  `(1014, 960, 960)`, and exact code time `15330.069689399999` (`50 Myr`).
- The completed work directory is approximately `2.9 TiB`, agreeing closely
  with the conservative `2.819 TiB` per-case forecast.
- Retrieved only eight compact provenance/catalogue files totalling less than
  `0.5 MiB`; the local asset manifest records their SHA-256 values.
- Did not query `C-LO`, start post-processing, compact/delete source data, or
  submit `G-HI`.

Decision: `C_HI_FULL_HISTORY_ENDPOINT_GREEN_C_LO_STILL_WAITING`.

Status: `c_hi_complete_c_lo_waiting_pbs_completion`.

## 2026-08-20 - C-LO endpoint accepted; matched cluster pair complete

- Barry reported PBS `785823.kunanyi-ohpc` / `c_lo_hist` complete with
  `Exit_status=0`, `31:49:01` walltime, `888:21:39` CPU time, and `1792` CPUs.
- Read-only scheduler, stage-log, marker, catalogue, HDF5-header, and particle
  inventory checks all passed. `Stageout_status=1` remains a caveat, but the
  required compact evidence was directly retrievable.
- Validated continuous, non-empty output indices: `51` float HDF5 files
  (`0..50`), `11` double HDF5 files (`0..10`), and `5001` particle histories
  (`0..5000`).
- Independently opened both endpoint HDF5 files. Each has the expected
  timestep group, all six required fields, common shape `(1014, 960, 960)`,
  and exact code time `15330.069689399999` (`50 Myr`).
- The completed C-LO work directory occupies approximately `2.9 TiB`; the
  matched C-HI/C-LO pair retains approximately `5.8 TiB` in total.
- Retrieved eight compact C-LO provenance/catalogue files totalling `478550`
  bytes. No HDF5 or particle payload was copied, modified, compacted, or
  deleted.
- Did not submit `G-HI` or start cluster post-processing.

Decision: `MATCHED_CLUSTER_FULL_HISTORY_PAIR_GREEN_G_HI_READY`.

Status: `complete_matched_cluster_full_history_production`.
