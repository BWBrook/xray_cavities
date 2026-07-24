# Goal 047 Log: Three-Case Lifecycle Compaction Execution

## 2026-07-24 Approved Start

Status: `in_progress_local_implementation`.

Starting state:

```text
cwd: /Users/bwbrook/papers/xray_cavities
branch: main
HEAD: 1e9866bae48dec72347db1ffa9fa097147d93669
status: clean and synchronized with origin/main
```

Barry explicitly approved permanent loss of the raw production files bound to
ledger SHA-256
`df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92`.
The authorization covers exactly `148` HDF5 files and their `148` XMF
sidecars, forecasting `6,845,659,111,424` allocated bytes recovered.

Goal 046 was committed and pushed at `1e9866b`. Its full focused suite,
required-digest validator, 15-file packet manifest, and an independent final
mechanical audit passed before Goal 047 started.

Two independent Goal 047 design reviews found the contract implementable and
returned a conditional GO. The required implementation keeps all candidate
file descriptors open from full hash through no-follow `unlinkat`, permits
only the current PBS job at two active-job gates, writes a hash-chained fsynced
transcript, and performs an exact post-inventory reconciliation. No remote
command, browser action, PBS submission, or data mutation has occurred in Goal
047 at this checkpoint.

## 2026-07-24 Local Gate And Independent Audit

Status: `prepared_for_remote_preflight`.

The completed local implementation was independently audited after one focused
repair pass. Final verdict: `GO`, conditional on the recorded zero-symlink
stage gate, zero active Barry jobs immediately before submission, and both
in-job self-only job gates.

Final audited code hashes:

```text
executor=cf93d052e6d4860bb4e598fd84cc28063e615235a09cf96af2e9b1aadce5ae41
wrapper=ffbb9f2fcc96aa5a0075c4aada379de1d9955536471c74f08fb092dafcf3a3e7
```

Fresh validation:

```text
full Goal 046/047 suite: 81 passed, 1 skipped
focused final Goal 047 suite: 42 passed
Python compilation: passed
PBS wrapper syntax: passed
Goal 046 packet manifest: 15 entries verified
Goal 046 completed-evidence manifest: 27 entries verified
Goal 047 staged-input manifest: 50 immutable inputs bound
git diff --check: passed
```

The single skip is an unrelated macOS FIFO-creation limitation. The staged
manifest binds the exact authorization packet, completed evidence, approval
receipt, audited executor and wrapper, and read-only inventory/validation
helpers. The residual assumptions are an out-of-band writer not visible to
PBS, real NFS unlink failure semantics beyond local simulation, and possible
delay or mismatch between deleted `st_blocks` and an immediately observed
quota report.

No remote command, browser action, PBS submission, or data mutation has
occurred at this checkpoint.

## 2026-07-24 Attempt 1 Failed Closed

Status: `failed_closed_no_mutation`.

After all local, staged-hash, zero-symlink, wrapper, approval, and zero-active-
job gates passed, PBS job `775752.kunanyi-ohpc` (`tri_compact`) was submitted
and verified queued. It completed with `Exit_status=1` after `00:00:12`.

The executor passed the authorization packet, staged inputs, lock, and first
self-only qstat gate. It then failed at the frozen/live estate comparison:

```text
status=FAILED_CLOSED_NO_MUTATION
deleted_row_count=0
deleted_hdf5_count=0
deleted_xmf_count=0
recovered_allocated_bytes=0
mutation_outcome_unknown=false
```

The first mismatch was only `device=('46','44')` on a retained
`HOLD_REGENERATION_UNPROVEN` CSV. No candidate was opened and no mutation was
attempted. The five-record transcript, status, failure receipt, qstat,
stdout/stderr, submission transcripts, and completion diagnostic were
retrieved and preserved locally. No archive was created.

## 2026-07-24 Namespace Repair And Retry Isolation

Status: `repair_audited_retry1_prepared_local`.

Diagnostic evidence showed the same retained file as `st_dev=46` in the frozen
inventory, `44` on compute node `n196`, and `69` on the login node, while its
inode, size, allocated bytes, mtime, and full SHA-256 agreed. The failure is
therefore a cross-client mount-namespace false positive, not data drift.

The repaired executor excludes only frozen `device` from cross-node
comparison. It adds:

- explicit frozen/live device namespace mappings;
- full same-job candidate descriptor comparison against the pre-delete live
  snapshot, including device and file type; and
- exact pre/post equality for every retained live row across all 14 fields,
  including device.

Full candidate SHA-256, descriptor stability, immediate pre-unlink identity,
active-job, pair, protected/restart, and post-delete gates remain unchanged.
New regressions prove cross-node device drift is permitted while a same-job
device change fails before mutation or at post-check.

Root validation passed with `93 passed, 1 skipped`. The independent auditor
passed eight focused controls and `84 passed, 1 skipped`, plus Python
compilation, wrapper syntax, ledger/count/byte reconciliation, and
`git diff --check`. The auditor returned `GO` on the repair and confirmed that
Barry's exact-list approval carries forward because attempt 1 deleted zero
rows.

Attempt 1 remains immutable. Retry 1 uses fresh paths:

```text
stage=/u/bwbrook/codex_kunanyi/goal047_three_case_lifecycle_compaction_retry1
evidence=/scratch/bwbrook/xray_cavities_analysis/2026-07-24-three-case-lifecycle-compaction-execution-retry1
job_name=tri_compact_r1
```

The retry staged-input manifest binds the repaired executor and retry wrapper.
The frozen ledger digest, `296` rows, `6,845,659,111,424` allocated bytes,
approval receipt, and protected/held scope remain unchanged. No retry has been
staged or submitted at this checkpoint.

## 2026-07-24 Retry 1 Submission

Status: `submitted_waiting_pbs_completion`.

Commit `920eb0d` was pushed before renewed remote action. Chrome/Open OnDemand
opened the authorized SSH window. The fresh retry stage passed:

```text
retry no-clobber gate: passed
recursive symlink count: 0
staged manifest: 50/50
authorization packet manifest: 15/15
completed evidence manifest: 27/27
remote syntax/compile/HDF5 gate: passed
immediate active Barry jobs: 0
```

A first shell-side submission command stopped before `qsub` because its fresh
login session exposed Python 2 to an f-string parser. Its transcript was
preserved; no job, PBS log, execution evidence, or data mutation resulted.
The corrected command explicitly loaded Anaconda Python 3 and repeated the
no-clobber and zero-active-job gates.

Exactly one retry was submitted:

```text
job_id=775763.kunanyi-ohpc
job_name=tri_compact_r1
queue=normal
state=Q
select=1:ncpus=8:mpiprocs=1:mem=64gb
walltime=48:00:00
qtime=Fri Jul 24 13:30:20 2026
```

The PBS stop rule was invoked immediately after the single queued-state
verification. No polling, completion retrieval, additional submission,
cleanup, or further remote command occurred.
