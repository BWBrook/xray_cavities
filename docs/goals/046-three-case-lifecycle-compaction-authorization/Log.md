# Goal 046 Log: Three-Case Lifecycle Compaction Authorization

## 2026-07-23 Approved Start

Status: `in_progress_local_implementation`.

Starting state:

```text
cwd: /Users/bwbrook/papers/xray_cavities
branch: main
HEAD: 92f4df4
status: clean and synchronized with origin/main
```

Barry approved Goal 046 after Goal 045 resolved the Goal 044 X-ray recovery
hold. The approved tranche refreshes the unexecuted Goal 042 design and covers
the full three-case lifecycle inventory, but stops before deletion.

The contract was revised to use risk-tiered identity verification:

- fresh full SHA-256 for every deletion candidate and any canonical counterpart
  whose identity makes deletion safe;
- trusted existing hashes or two stable metadata/HDF5 identity snapshots for
  untouched large protected payloads; and
- fail-closed handling for changed files, hash failures, unresolved symlinks,
  active jobs, and dependency ambiguity.

Native subagents were assigned non-overlapping work:

- read-only provenance/root reconnaissance;
- an independent scientific retention-policy review;
- deterministic contract construction; and
- mechanically verifiable read-only inventory implementation.

No remote command, Open OnDemand action, SSH, PBS submission, data mutation,
commit, or push had occurred at this checkpoint.

## 2026-07-23 Inventory Submission

Status: `submitted_waiting_pbs_completion`.

An independent audit returned `NO-GO` on the first implementation and found
five material fail-closed defects: the wrong protected G-LO source restart,
incomplete metadata enforcement for identity-only large HDF5 files, symlink
escape risk, incomplete contract/output binding, and no inventory-wide
mutation check. The implementation was repaired before any PBS submission.

The final contract protects `65` exact paths across `25` allowlisted roots,
including `29` HDF5 files. The corrected G-LO source restart is the accepted
Goal 038 source tuple under the original 2026-07-07 production root. Protected
large HDF5 files may use stable identity only when timestep, time, shape, and
dataset expectations are complete; otherwise they require a full hash.
Protected symlinks are rejected, all other symlink targets are resolved and
confined, contract files are bound to metadata digest
`706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d`,
outputs use no-clobber reservations, and a whole-tree pre/post identity
snapshot fails on added, removed, or changed entries.

The real PLUTO HDF5 preflight exposed a legitimate nested field layout
(`Timestep_n/vars/<field>`). A test-first repair now accepts either that
layout or the direct synthetic layout while rejecting ambiguous duplicate
field basenames.

Final local validation:

```text
uv run pytest tests/test_three_case_lifecycle_contract.py \
  tests/test_three_case_lifecycle_inventory.py \
  tests/test_three_case_lifecycle_inventory_wrapper.py -q
28 passed, 1 skipped

uv run python -m py_compile \
  scripts/science/build_three_case_lifecycle_contract.py \
  scripts/science/inventory_three_case_lifecycle.py
bash -n scripts/kunanyi/three_case_lifecycle_inventory.pbs
git diff --check
```

All passed. The staged scanner SHA-256 is
`52525b151a351dfccbfe372c7dde231f482b8bad22770432c2118089d67c081c`;
the wrapper SHA-256 is
`740e0bd7483415dc4a947948314aae7ec3bcf5558d1920e3c4bbf37521418387`.

Remote read-only preflight passed:

```text
contract_digest=passed sha256=706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d
root_contract_rows=25 roots_present=22 optional_missing=3
protected_paths=65
protected_hdf5_metadata_read=29
remote_preflight=passed
```

Exactly one inventory job was submitted:

```text
job_id=775619.kunanyi-ohpc
Job_Name = tri_lifeinv
job_state = Q
queue = normal
qtime = Thu Jul 23 16:54:11 2026
Resource_List.select = 1:ncpus=8:mpiprocs=1:mem=64gb
Resource_List.walltime = 48:00:00
```

Expected products:

- analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-23-three-case-lifecycle-inventory`;
- archive:
  `/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory/three_case_lifecycle_inventory_2026-07-23.tar.gz`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory/three_case_lifecycle_inventory.{out,err}`.

The PBS stop rule was invoked immediately after queued-state verification.
No polling, deletion, move, truncation, permission change, cleanup, commit, or
push occurred. Resume only after Barry reports the PBS completion email or
explicitly authorizes a status check.

## 2026-07-24 Failure Diagnosis And Repair Submission

Status: `repair_submitted_waiting_pbs_completion`.

Barry reported that `775619.kunanyi-ohpc` / `tri_lifeinv` ended with
`Exit_status=2` after `07:28:19`. Retrieval confirmed that the scanner failed
closed before producing reports or an archive:

```text
inventory_error: inventory-wide identity drift in goal045_analysis:
added=[] removed=[] changed=['/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-recovery-method-refinement']
```

The failed run performed no deletion or mutation. Its stdout and stderr are
preserved under
`docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/failed_run/remote_logs/`.
Their SHA-256 values are:

```text
bdf06deb317ca0ff1f6a7f22f9abf88b8ae5a5037bcabd65d58b1b34c4839fdc  three_case_lifecycle_inventory.out
37ad9817c2a930da2c1f0f6d07c1b3a698381e4916f7226b3dceb64e0f9fafcd  three_case_lifecycle_inventory.err
```

Read-only inspection found the Goal 045 root unchanged in membership and file
identity, with all recorded mtimes predating the Goal 046 job. Five immediate
tree snapshots were identical and no active reference was found. The best
supported diagnosis is NFS directory `st_size` instability: the original
snapshot signature included directory size even though directory size is not a
stable content-identity field on this filesystem. This is an inference because
the original diagnostic did not print the before/after tuples.

A test-first repair now excludes `st_size` only for directories. It continues
to compare device, inode, nanosecond mtime, and mode for directories, and the
full previous identity tuple including size for all non-directory entries.
Added, removed, renamed, type-changed, and file-content/identity changes still
fail closed. Future drift diagnostics include the exact before/after tuples.

An independent methodological audit returned a conditional `GO` for one
read-only rerun after this repair. It retained the residual limitation that the
inventory is a strong fail-closed traversal rather than an atomic filesystem
snapshot; the separate lifecycle ledger review and Barry approval remain
mandatory before any deletion.

Final repair validation:

```text
uv run pytest tests/test_three_case_lifecycle_contract.py \
  tests/test_three_case_lifecycle_inventory.py \
  tests/test_three_case_lifecycle_inventory_wrapper.py -q
35 passed, 1 skipped

uv run python -m py_compile \
  scripts/science/build_three_case_lifecycle_contract.py \
  scripts/science/inventory_three_case_lifecycle.py
bash -n scripts/kunanyi/three_case_lifecycle_inventory.pbs
bash -n scripts/kunanyi/three_case_lifecycle_inventory_repair.pbs
git diff --check
```

All passed. The repaired scanner SHA-256 is
`406cb85b27a18068a80fc1afef82dbb25200a2ab3a0b350013c8e2e9d046516c`;
the distinct repair wrapper SHA-256 is
`5250b1c68566ea49729feeaf60f207df44013f86d597c1a3b9ac1246989b9cc4`.
The contract digest remains
`706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d`.

Remote repair preflight passed the staged hashes, both wrapper syntax checks,
the unchanged contract digest, `22` present plus `3` optional-missing roots,
all `65` protected paths, and metadata reads for all `29` protected HDF5
files. The original failed stage and analysis paths were preserved.

Exactly one repair job was submitted:

```text
job_id=775729.kunanyi-ohpc
Job_Name = tri_liferep
job_state = Q
queue = normal
qtime = Fri Jul 24 00:44:12 2026
Resource_List.select = 1:ncpus=8:mpiprocs=1:mem=64gb
Resource_List.walltime = 48:00:00
```

Expected repair products:

- analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-24-three-case-lifecycle-inventory-repair`;
- archive:
  `/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory_repair/three_case_lifecycle_inventory_repair_2026-07-24.tar.gz`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory_repair/three_case_lifecycle_inventory_repair.{out,err}`.

The PBS stop rule was invoked after queued-state verification. Do not poll.
Resume only after Barry reports the completion email or explicitly requests a
status check.

## 2026-07-24 Repaired Inventory Completion And Approval Packet

Status: `approval_packet_ready`.

Barry reported that repair job `775729.kunanyi-ohpc` / `tri_liferep` completed
with `Exit_status=0` after `07:32:33`. Final scheduler evidence also records
`job_state=F` and `Stageout_status=1`. The compact stage-root archive, stdout,
and empty stderr were retrieved without a new PBS job or any remote mutation.

Retrieved archive SHA-256:

```text
4fc216392c9d32b6cc4d9b74ab4f58cdb3f5aa77a3a92516c18b99b962ea8ea0
```

The archive lists `12` compact members. All covered member checksums passed.
Ten separately retrieved HDF5 catalogues also matched their recorded hashes.
The original archive manifest measured `archive_file_list.txt` before its
final manifest entry was appended (`315` versus `338` bytes). The mismatch is
recorded as a metadata-only packaging defect; the intact archive is externally
hash-bound, and the base wrapper now uses a stable content/file-list contract.
No rerun was justified.

Inventory result:

```text
roots=25
payload_rows=17153
regular_rows=17150
symlinks=3
protected_rows=65
radio_hold_rows=5501
candidate_review_rows=1264
allocated_bytes=8375466742272
```

The first generated ledger proposed deleting `968` analysis rows as
regenerable. A Sol Max independent audit returned `NO-GO` because those rows
lacked per-row lineage and included compact provenance-like files. They
represented only `3,868,320,256` allocated bytes, or `0.0565%` of proposed
recovery. The focused repair holds them as
`HOLD_REGENERATION_UNPROVEN`, preserving `99.9435%` of the recovery forecast.

Final action counts:

```text
DELETE_PROPOSED_UNIQUE_RAW=148
DELETE_PROPOSED_METADATA_ONLY=148
HOLD_REGENERATION_UNPROVEN=968
HOLD_RADIO_UNRESOLVED=5501
HOLD_AMBIGUOUS=3
KEEP_PROTECTED=65
KEEP_PROVENANCE=10320
```

The production proposal recovers `6,845,659,111,424` allocated bytes. Every
proposed HDF5 is full-hashed, stable, readable, catalogued, unprotected, and
paired with its proposed XMF sidecar. The deletion/protected/held anti-join is
empty.

The current Plan and Runbook now bind Goal 047 to a mandatory approved digest,
fresh qstat and identity/hash gates, exact nonrecursive file-by-file mutation,
stop-on-first mismatch, append-only transcripts, and protected-source/restart/
hold/provenance post-delete validation.

Final proposed ledger SHA-256:

```text
df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
```

Goal 046 performed no deletion, move, truncation, overwrite, permission
change, cleanup, commit, or push. Stop for Barry's explicit approval,
amendment, or rejection of this exact digest before Goal 047.

## 2026-07-24 Exact Ledger Approval

Status: `approved_for_goal047_execution`.

Barry explicitly approved permanent loss of the raw production files bound to
ledger SHA-256:

```text
df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
```

The approval covers exactly `148` `DELETE_PROPOSED_UNIQUE_RAW` HDF5 rows and
their `148` `DELETE_PROPOSED_METADATA_ONLY` XMF sidecars, with forecast
recovery of `6,845,659,111,424` allocated bytes. It does not cover the `968`
`HOLD_REGENERATION_UNPROVEN` analysis rows, radio-held particles, ambiguous
symlinks, protected sources, or compact provenance.

Goal 047 may now implement and submit the separately audited executor. It must
refresh active-job state, validate every row against the immutable packet and
full hash, fail before mutation on any mismatch, delete only exact files
nonrecursively, and complete the Runbook's protected-source and post-delete
checks. This approval does not alter or regenerate the Goal 046 authorization
packet.
