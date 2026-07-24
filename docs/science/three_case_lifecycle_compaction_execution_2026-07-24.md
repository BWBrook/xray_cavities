# Three-Case Lifecycle Compaction Execution

## Status

`submitted_waiting_pbs_completion`

Decision label:
`GOAL047_ATTEMPT1_FAILED_CLOSED_NO_MUTATION_NAMESPACE_REPAIR_GREEN`.

## Authority

The permanent-deletion authority is unchanged:

```text
ledger_sha256=df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
delete_hdf5_rows=148
delete_xmf_rows=148
allocated_bytes=6845659111424
```

Barry approved this exact list on 2026-07-24. The first attempt did not mutate
it, so the approval remains valid for an exact retry. The `968` analysis rows
held as `HOLD_REGENERATION_UNPROVEN`, radio-held rows, protected rows,
ambiguous symlinks, compact provenance, and all paths outside the frozen
allowlist remain excluded.

## Attempt 1 Outcome

PBS job `775752.kunanyi-ohpc` (`tri_compact`) exited `1` after `12` seconds.
The executor passed packet, manifest, approval, lock, and first qstat gates,
then failed before opening candidates or deleting data.

Authoritative evidence reports:

```text
status=FAILED_CLOSED_NO_MUTATION
deleted_row_count=0
deleted_hdf5_count=0
deleted_xmf_count=0
recovered_allocated_bytes=0
mutation_outcome_unknown=false
```

The five-record transcript hash chain terminates at
`terminal_failure`. The original scheduler record, stdout/stderr, transcript,
failure receipt, staged manifest, and executor evidence are preserved under
this note's asset bundle.

## Diagnosis

The first mismatch was a retained Goal 019 CSV, not a deletion candidate:

```text
frozen device=46
compute-node device=44
later login-node device=69
inode=3298535258375
size=180
allocated=512
sha256=d72f6af1535004f3c4ef81e8eaff239134bee8d6d440d16e2aaf4a49ed554c0f
```

The inode, size, allocation, mtime, and full hash agreed. Observation therefore
supports the inference that Kunanyi presents different numeric `st_dev`
identifiers for the same shared export in different client mount namespaces.
Treating frozen `st_dev` as a cross-node invariant caused the safe false
positive.

## Repair

The repaired executor excludes only `device` from frozen-to-live cross-node
comparison. It still:

- records frozen/live device namespace mappings;
- compares every candidate descriptor against the same job's pre-delete live
  snapshot using device, inode, size, allocation, mtime, and file type;
- requires the frozen full SHA-256 for every candidate;
- retains descriptor-stability and immediate pre-unlink path/descriptor
  checks; and
- requires every retained post-scan row to equal the same job's pre-delete
  row across all 14 live fields, including device.

Regression tests cover both permitted cross-node device drift and prohibited
device drift within one job.

## Retry Isolation

Attempt 1 remains immutable. Retry 1 is rebound to:

```text
stage=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction_retry1
evidence=/scratch/bwbrook/xray_cavities_analysis/2026-07-24-three-case-lifecycle-compaction-execution-retry1
job_name=tri_compact_r1
```

The updated staged-input manifest binds the repaired executor and retry
wrapper. All ledger rows, hashes, counts, byte totals, protected contracts,
and the approval token are unchanged.

After all fresh remote hashes, packet/completed manifests, zero-symlink,
no-clobber, Python/HDF5, wrapper, and immediate zero-active-job gates passed,
retry 1 was submitted:

```text
pbs_job_id=775763.kunanyi-ohpc
job_name=tri_compact_r1
queue=normal
state=Q
requested=1 node, 8 CPUs, 64 GB, 48:00:00
```

The PBS stop rule is active. No remote command or poll follows the queued-state
proof; completion review waits for Barry's PBS email.

## Verification

Root validation passed with `93 passed, 1 skipped`; the skip is the known
macOS FIFO limitation. An independent audit passed eight focused
positive/negative controls and its `84 passed, 1 skipped` Runbook suite.
Python compilation, PBS syntax, manifest checks, and `git diff --check`
passed.

The audit returned `GO` on the repair and confirmed that the original exact
approval carries forward. Retry remains conditional on fresh staged-hash,
zero-symlink, zero-active-job, and in-job self-only qstat gates.

Residual uncertainty is unchanged: PBS cannot observe an out-of-band writer,
real NFS unlink failure semantics remain partly synthetic, and recovered
`st_blocks` need not immediately equal a quota-report delta.
