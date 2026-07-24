# 2026-07-24 Three-Case Lifecycle Compaction Execution

Status: `submitted_waiting_pbs_completion`.

Barry's authority remains the exact Goal 046 ledger SHA-256
`df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92`:
`148` HDF5 files, `148` paired XMF sidecars, and
`6,845,659,111,424` allocated bytes. All protected and held rows remain
excluded.

Attempt 1, PBS `775752.kunanyi-ohpc` / `tri_compact`, exited `1` after
`00:00:12`. It failed closed during the first estate comparison, before
candidate opening or mutation:

```text
status=FAILED_CLOSED_NO_MUTATION
deleted_rows=0
recovered_allocated_bytes=0
mutation_outcome_unknown=false
```

The mismatch was a retained CSV whose numeric `st_dev` was `46` in the frozen
inventory, `44` on the compute node, and later `69` on the login node, while
inode, size, allocation, mtime, and SHA-256 agreed. Attempt-1 compact evidence
is preserved locally.

The repaired executor treats only frozen/live `device` as namespace-local.
Same-job candidate and retained-row checks still include device, and all
candidate hashes, descriptor, pre-unlink, active-job, protected/restart, pair,
and post-delete gates remain mandatory. Root validation passed with
`93 passed, 1 skipped`; independent controls and audit passed. The original
approval carries forward because no row was deleted.

Retry 1 is isolated at:

```text
stage=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction_retry1
evidence=/scratch/bwbrook/xray_cavities_analysis/2026-07-24-three-case-lifecycle-compaction-execution-retry1
```

The retry manifest binds the repaired executor and wrapper. Attempt-1 paths
are immutable and were not cleaned or reused. Fresh staged hashes, packet and
completed-evidence manifests, zero symlinks, no-clobber paths, remote
syntax/compile/HDF5, and immediate zero-active-job gates passed.

Retry PBS `775763.kunanyi-ohpc` / `tri_compact_r1` was submitted to `normal`
and verified `Q`, requesting one node, eight CPUs, 64 GB, and `48:00:00`.
The stop rule is active: no polling or retrieval until Barry reports the PBS
completion email.
