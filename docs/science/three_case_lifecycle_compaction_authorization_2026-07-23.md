# Three-Case Lifecycle Compaction Authorization

Date: 2026-07-23

Status: `approval_packet_ready`

## Purpose

Goal 046 inventories the full accepted C-HI, C-LO, and G-LO remote data estate
against an explicit scientific dependency union. It is the evidence-building
step between the project's promote-prove-prune policy and any later
irreversible cleanup.

This goal has no deletion capability. Its completion target is an exact,
digest-bound approval packet that quantifies what must remain, what may be
deleted, why, and how many bytes each proposed action would recover.

## Protected Scientific Surface

The contract contains `25` exact roots and `65` protected paths, including
`29` HDF5 files. It protects accepted configurations and provenance; common-age
and late-age fluid sources; endpoint/source/preceding restart tuples; all
particle payloads while radio retention remains unresolved; and baseline plus
endpoint fluid sources required by the open Level 3 gravity convention.

Goal 045 retired the X-ray recovery-validation raw-data hold. The final
observational topology remains a methods caveat but does not justify retaining
every intermediate raw file.

## Safety Design

The inventory is allowlist-only and never follows symlinks. Protected symlinks
are rejected. Paths resolving outside an allowed root fail closed.

Every deletion candidate and any retained canonical counterpart required to
prove a duplicate must receive a fresh full SHA-256. A protected HDF5 file
larger than 64 MiB may use stable identity instead only when its expected
timestep, code time, shape, and datasets are all specified and validated.
Incomplete identity contracts fall back to full hashing.

Contract metadata binds both CSV contracts to digest:

```text
706155240b2cf59c57dd446ff929f5963e0c64ecb221e09e8cf8db110510ea3d
```

Output directories and archives are reserved without overwrite. Pre/post
whole-tree `lstat` snapshots fail if any entry is added, removed, or changed
during the inventory.

## Verification

The initial implementation failed an independent audit and was repaired before
submission. The audit identified the wrong G-LO source restart, incomplete
large-HDF5 metadata enforcement, symlink escape risk, weak contract/output
binding, and absent inventory-wide mutation detection.

The real remote preflight then exposed a valid PLUTO layout not represented by
the synthetic fixtures: fields live under `Timestep_n/vars/<field>`. The
scanner now accepts either that layout or `Timestep_n/<field>` and rejects
ambiguous duplicate basenames.

Final local tests passed:

```text
28 passed, 1 skipped
```

Remote preflight passed the exact contract digest, all `65` protected paths,
and all `29` protected HDF5 metadata contracts. Of the `25` roots, `22` are
present and the three absent roots are explicitly optional historical C-LO
roots removed by the earlier accepted compaction.

## Remote Inventory Outcome

The original inventory job `775619.kunanyi-ohpc` failed closed with
`Exit_status=2`. It reported a changed identity signature for the Goal 045
analysis-root directory but no added or removed paths. No inventory reports,
archive, deletion, or mutation were accepted from that run.

Read-only diagnosis found stable membership and file identity, all mtimes
predating the job, and five identical immediate snapshots. The best-supported
cause is the original use of NFS directory `st_size`, which is not a stable
directory-content identity field. This remains an inference because the old
error did not capture its before/after tuple.

The repair removes only directory size from snapshot comparison. Directory
device, inode, nanosecond mtime, and mode remain checked; files retain size and
the full previous identity tuple. Persistent additions, deletions, renames,
type changes, and file mutations still fail closed.

Repair job `775729.kunanyi-ohpc` (`tri_liferep`) then completed:

```text
job_state=F
Exit_status=0
Stageout_status=1
resources_used.walltime=07:32:33
resources_used.cput=10:38:11
resources_used.ncpus=8
resources_used.mem=104220kb
```

The stageout status is retained as a scheduler caveat. The requested archive,
stdout, and empty stderr were present at the stage root and retrieved directly.
The archive is readable with `12` compact members and SHA-256:

```text
4fc216392c9d32b6cc4d9b74ab4f58cdb3f5aa77a3a92516c18b99b962ea8ea0
```

All nine substantive archive members and all ten independently retrieved
catalogue snapshots match their recorded hashes. The original archive
manifest records `archive_file_list.txt` at `315` bytes although the final
archived file is `338` bytes because the wrapper appended its own manifest
entry after measuring the list. This is a metadata-only packaging defect: the
archive is intact, its bytes and members are externally bound, and the wrapper
is patched for future runs without repeating the seven-hour inventory.

## Inventory And Proposal

The repaired scan contains:

```text
25 roots
17,153 payload rows
17,150 regular files
3 symlinks
8,375,461,988,950 apparent bytes
8,375,466,742,272 allocated bytes
```

Every production HDF5 file in scope has catalogue membership. The proposed
production deletion core is:

| Action | Rows | Apparent bytes | Allocated bytes |
| --- | ---: | ---: | ---: |
| `DELETE_PROPOSED_UNIQUE_RAW` | 148 | 6,845,658,606,448 | 6,845,658,656,768 |
| `DELETE_PROPOSED_METADATA_ONLY` | 148 | 445,412 | 454,656 |
| **Total** | **296** | **6,845,659,051,860** | **6,845,659,111,424** |

All `148` HDF5 files are regular, stable, freshly full-hashed, HDF5-readable,
catalogued, and paired with their `148` XMF sidecars. The deletion set has no
overlap with protected or held rows.

The packet retains:

- `65` exact protected paths, including all `29` protected HDF5 sources;
- `5,501` radio-held particle/source rows;
- `3` ambiguous C-HI continuation symlinks;
- `10,320` compact provenance rows; and
- `968` analysis rows as `HOLD_REGENERATION_UNPROVEN`.

The final hold is deliberately conservative. An initial packet proposed those
analysis rows as regenerable without per-row lineage evidence. An independent
destructive-risk audit rejected that digest. Holding them gives up only
`3,868,320,256` allocated bytes while preserving `99.9435%` of the original
recovery forecast.

## Approval And Risk

The exhaustive `17,153`-row ledger is bound to:

```text
df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92
```

The dry-run validator requires that digest and the frozen inventory evidence.
It independently checks source-row equality, protected and hold registers,
normalized allowlisted paths, HDF5/XMF action consistency, catalogue
membership, active-job transcript freshness, archive evidence, and complete
packet-manifest coverage. It has no execute or deletion surface.

The current approval-time job check ran on
`<tpac-host>` at `2026-07-23T22:48:47Z`;
`qstat -u bwbrook` exited `0` with zero active rows. Goal 047 must repeat that
gate immediately before any mutation.

Deleting the proposed HDF5 files knowingly removes unselected fine-cadence
trajectory information. There is no sanctioned rollback; recovery requires
rerunning PLUTO. The accepted selected-age and endpoint inference surface
remains protected, but future questions about short-lived phenomena between
retained ages would require new production compute.

Goal 046 performed no deletion.

## Approval Recorded

On 2026-07-24 Barry explicitly approved permanent loss of the raw production
files represented by the exact ledger digest above. Goal 047 is therefore
authorized to execute only the `296` proposed production rows, provided it
satisfies every fresh active-job, exact identity/hash, protected-path,
stop-on-mismatch, transcript, and post-delete validation gate in the Goal 046
Runbook.

The approval does not extend to the `968` lineage-unproven analysis rows or any
other held or protected payload. The hash-locked Goal 046 authorization packet
was not regenerated or amended when this approval was recorded.
