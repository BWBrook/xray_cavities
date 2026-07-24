# Goal 046 Three-Case Lifecycle Compaction Authorization

Date: 2026-07-23
Status: `approval_packet_ready`

Goal 046 has submitted a read-only inventory of the accepted C-HI, C-LO, and
G-LO production and analysis estate. It cannot delete, move, truncate,
overwrite, or change permissions on inventoried payloads.

An independent audit blocked the initial implementation. The repaired package
now protects the correct accepted G-LO restart tuple, enforces complete HDF5
identity contracts, rejects protected symlinks and target escapes, binds both
contract files to a recorded digest, reserves output/archive paths without
clobbering, and detects whole-tree changes during inventory. A further
test-first repair added support for real PLUTO fields under
`Timestep_n/vars/` while retaining fail-closed ambiguity checks.

Local validation passed with `28 passed, 1 skipped`, Python compilation,
wrapper syntax, contract regeneration, and `git diff --check`. Remote
preflight matched contract digest
`706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d`,
found `22` present and `3` expected-optional missing roots, validated all `65`
protected paths, and read/validated metadata from all `29` protected HDF5
files.

PBS job `775619.kunanyi-ohpc` (`tri_lifeinv`) was submitted to `normal` and
verified `Q` at `Thu Jul 23 16:54:11 2026`. It requests one node, eight CPUs,
`64gb`, and `48:00:00`. The stop rule is active; no polling occurred.

Expected archive:

```text
/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory/three_case_lifecycle_inventory_2026-07-23.tar.gz
```

After Barry reports completion, retrieve only the compact archive and logs,
construct the exact dependency-aware retention/deletion ledger locally, and
stop again for Barry's approval before any deletion-capable Goal 047 action.

## 2026-07-24 Fail-Closed Repair Handoff

The original job ended `F` with `Exit_status=2` after `07:28:19`. It stopped
before producing inventory reports or an archive because the Goal 045 analysis
root's snapshot signature changed while its membership did not:

```text
added=[] removed=[] changed=['/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-recovery-method-refinement']
```

The failed stdout/stderr are retained locally. No deletion or mutation
occurred. Read-only diagnosis found stable membership, file identities, and
pre-job mtimes; five immediate snapshots were identical. The most plausible
cause is unstable NFS directory `st_size`, although the original diagnostic
did not retain the exact changed tuple.

The scanner now excludes size only from directory snapshot identities while
retaining device, inode, nanosecond mtime, and mode. Files retain the complete
previous tuple including size. Added, removed, renamed, type-changed, and
file-mutated paths still fail closed, and future errors print exact
before/after tuples.

The repaired suite passed with `35 passed, 1 skipped`; both wrapper syntax
checks, Python compilation, contract regeneration, remote staged hashes,
remote contract/HDF5 preflight, and `git diff --check` passed. An independent
audit supported exactly one read-only rerun, with the lifecycle ledger and
Barry approval still mandatory before deletion.

PBS job `775729.kunanyi-ohpc` (`tri_liferep`) was submitted to `normal` and
verified `Q` at `Fri Jul 24 00:44:12 2026`. It requests one node, eight CPUs,
`64gb`, and `48:00:00`.

Expected repaired archive:

```text
/u/bwbrook/codex_kunanyi/goal046_three_case_lifecycle_inventory_repair/three_case_lifecycle_inventory_repair_2026-07-24.tar.gz
```

The stop rule is active. Wait for Barry's PBS completion email before retrieval
or any further remote check.

## 2026-07-24 Approval Packet

Repair job `775729.kunanyi-ohpc` / `tri_liferep` completed `F` with
`Exit_status=0`, `Stageout_status=1`, and walltime `07:32:33`. The compact
archive, stdout, and empty stderr were retrieved directly from the stage root.
Archive SHA-256:

```text
4fc216392c9d32b6cc4d9b74ab4f58cdb3f5aa77a3a92516c18b99b962ea8ea0
```

The scan covers `17,153` exact rows across `25` roots. It is exhaustive and
read-only. A separately retrieved catalogue snapshot covers all `178`
production HDF5 files in the inventory.

The first local authorization ledger was rejected by an independent
destructive-risk audit because it called `968` analysis rows regenerable
without per-row lineage evidence. Those rows recover only `3,868,320,256`
allocated bytes, so the final packet holds all of them as
`HOLD_REGENERATION_UNPROVEN`.

The approval proposal is now exactly:

```text
148 DELETE_PROPOSED_UNIQUE_RAW HDF5 rows
148 DELETE_PROPOSED_METADATA_ONLY XMF rows
6,845,659,111,424 allocated bytes recoverable
```

Retained or held: `65` protected rows, `5,501` radio-held rows, `3` ambiguous
symlinks, `968` lineage-unproven analysis rows, and `10,320` compact
provenance rows.

Exact ledger SHA-256:

```text
df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
```

The required-digest dry-run validator is bound to the frozen inventory,
contracts, catalogues, active-job transcript, and complete packet manifest.
Goal 046 also now has a current Plan and Runbook specifying immediate
pre-delete gates, exact nonrecursive file-by-file execution, stop-on-first
mismatch, transcript preservation, and mandatory post-delete validation.

No deletion occurred during Goal 046.

## 2026-07-24 Approval

Barry explicitly approved permanent loss of the raw production files bound to
ledger SHA-256
`df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92`.
Goal 047 is authorized for exactly the `296` proposed production rows and the
Runbook's mandatory execution and post-delete gates. The `968`
`HOLD_REGENERATION_UNPROVEN` analysis rows and every other hold/protection
remain outside the authorization. The Goal 046 packet itself remains
unchanged.
