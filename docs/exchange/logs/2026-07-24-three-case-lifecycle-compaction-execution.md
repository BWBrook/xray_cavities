# 2026-07-24 Three-Case Lifecycle Compaction Execution

Status: `repair_audited_retry1_prepared_local`.

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
are immutable and will not be cleaned or reused. Retry staging/submission is
still pending fresh hashes, zero-symlink, zero-active-job, and in-job self-only
gates.
