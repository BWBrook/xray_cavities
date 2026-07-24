# Three-Case Lifecycle Compaction Execution

## Status

`complete_compaction_postcheck_green`

Decision label:
`THREE_CASE_LIFECYCLE_COMPACTION_COMPLETE_POSTCHECK_GREEN`.

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

The PBS stop rule was active until Barry reported completion. No polling
occurred between queued-state proof and that report.

## Retry 1 Completion

PBS job `775763.kunanyi-ohpc` (`tri_compact_r1`) finished with
`Exit_status=0` after `02:56:45`. Scheduler `Stageout_status=1` remains a
caveat, but the requested archive, stdout, empty stderr, transcript, final
qstat, and compact executor evidence were all present at the stage root and
retrieved directly.

The executor's authoritative status is:

```text
status=DELETION_COMPLETE_POSTCHECK_GREEN
ledger_sha256=df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
deleted_rows=296
deleted_hdf5=148
deleted_xmf=148
recovered_allocated_bytes=6845659111424
retained_rows=16857
protected_hdf5_validated=29
restart_tuples_validated=7
unexpected_nfs_rows=0
```

The `602`-record transcript hash chain terminates at
`4dcf872142be02329a41a4c8760fc5e69e6ffca1e5744bb733c533b7154f8a76`.
Every unlink attempt matched the approved ledger path, action, full SHA-256,
and allocated-byte value. Every unlink completion reported the original path
absent, the held descriptor closed, and pre-close link count one.

The post-delete inventory contains exactly the frozen `17,153`-row estate
minus the `296` approved candidates. All retained rows match their frozen
non-device identity fields, while the executor's stronger same-job pre/post
comparison also included device. The recorded cross-client namespace mappings
are `46 -> 45` for `16,582` retained rows and `47 -> 46` for `275`.

The compact archive SHA-256 is
`94c930d15c3e9002c6eded7b92ae07b8369affef1791abc122544f6598b76ca9`.
All internal archive checksums passed. Attempt 1 remains preserved separately
as the immutable failed-closed, zero-mutation record.

## Verification

Root validation before submission passed with `93 passed, 1 skipped`; the skip
is the known macOS FIFO limitation. An independent repair audit passed eight
focused positive/negative controls and its `84 passed, 1 skipped` Runbook
suite. Python compilation, PBS syntax, manifest checks, and
`git diff --check` passed.

Completion validation then independently replayed the archive checksum
manifest, the full transcript hash chain, the exact candidate path/hash/action
set, the frozen-minus-candidates post-delete estate, both self-only in-job
qstat gates, protected/restart counts, scratch probe, and no-NFS-remnant gate.
An independent final audit returned `GO`, additionally confirming all `65`
protected paths remained present and that no further computational work is
justified.

Residual limitations are narrow: PBS cannot observe an out-of-band writer,
and recovered bytes are the exact approved sum of deleted `st_blocks`, not a
promise of an immediately identical quota-report delta. These do not weaken
the observed exact deletion and post-scan reconciliation.
