# X-ray scratch to home migration — 2026-10-16

Status checked 2026-10-31: production migration PBS `820961.kunanyi-ohpc` stopped at its 48-hour limit on 18 October. Eight units are complete; C-HI is copied but awaiting completed verification; C-LO has not started. Full completion and reclaimed quota remain unconfirmed. The dated launch history below is preserved.

Barry authorized moving the X-ray scratch data into home and then cleaning verified scratch duplicates. All scientific payloads are retained byte-for-byte; this is a storage migration, not the Q-028 compression rollout or a change to any scientific result. Stas and Patrick feedback on the remaining scientific questions is still pending.

## Scope and capacity

- Source scope: `xray_cavities_runs` (eight run directories), `xray_cavities_analysis`, and `xray_cavities_gates` under `/scratch/bwbrook`. Other projects and small smoke-test trees are excluded.
- Destination archive: `/u/bwbrook/xray_cavities_scratch_archive_2026-10-16`. Existing home G-HI continuation and G-LO production trees remain distinct.
- Control stage: `/u/bwbrook/codex_kunanyi/scratch_home_migration_2026-10-16`.
- PBS preflight `820951.kunanyi-ohpc` completed its inventory on a copy-queue allocation.
- Inventory: 35,865 regular files, 13 symbolic links, 8,796,208,343,281 logical bytes (8.00010 TiB). No hardlinks or special objects were found.
- Home directory accounting before copying: 5,716,776,206,277 bytes (5.199 TiB). Projected home after all copies: 13.199 TiB against the recorded 20 TiB allocation.
- `quota_status.sh` remains silent because its quota configuration file is absent. Home usage comes from the directory accounting used by that site helper; the allocation ceiling is the previously confirmed 20 TiB contract. Filesystem-wide `df` is not treated as a user quota.

## Migration order

| Source relative to `/scratch/bwbrook` | Logical GiB | Files |
| --- | ---: | ---: |
| `xray_cavities_gates` | 64.45 | 424 |
| `xray_cavities_analysis` | 80.37 | 2,061 |
| `xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production` | 151.95 | 3,498 |
| `xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh` | 272.72 | 2,458 |
| `xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64` | 271.90 | 1,821 |
| `xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation` | 346.98 | 5,823 |
| `xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation` | 376.92 | 2,011 |
| `xray_cavities_runs/2026-08-20-g-hi-full-history-production` | 862.05 | 3,531 |
| `xray_cavities_runs/2026-08-17-c-hi-full-history-rerun` | 2878.04 | 7,119 |
| `xray_cavities_runs/2026-08-17-c-lo-full-history-rerun` | 2886.72 | 7,119 |

Each destination is the archive root plus the same relative path. June 1 precedes June 6 because three June 6 symlinks point into the June 1 source. Their home copies will point directly to the corresponding home paths. The ten gates symlinks use relative paths within their unit.

## Safety and evidence

The migration inventories each unit and refuses destination collisions, unknown object types, unexpected file changes, and checksum differences. It records original filesystem metadata, preserves file timestamps and readable non-access attributes, verifies regular-file SHA-256 values on both sides, records durable per-file and per-unit receipts, and promotes only a verified tree. The original unit path becomes a symlink to home. Cleanup removes only inventoried, unchanged tombstone entries; it does not recursively delete arbitrary paths. A stopped or failed unit retains its originals or its already verified home replacements.

X-ray production and analysis are idle. The source trees are under maintenance during migration: no process should write them. File identity, size, mtime and ctime checks detect ordinary concurrent changes; the workflow does not claim protection against hostile same-account manipulation. Other projects can use the released scratch capacity.

Compatibility links preserve ordinary direct opens and the historical path strings in immutable scientific manifests. They do not make symlink-blind `find`/`du` operations behave like physical source directories. New analysis should use the home mappings. Existing checksum-bound scientific manifests are retained unchanged.

## Execution and handoff

The PBS wrapper runs focused migration tests on the allocation before it touches production data. The migration state, verification ledgers, stdout and stderr are retained under the control stage. On interruption, inspect the failure and resume the same frozen plan/state; never start a second copy or remove a tombstone manually.

Transfer job, verification results, and final reclaimed bytes will be recorded here after they are observed.

### Acceptance and access checkpoint

- Independent mechanical review found no remaining unsafe-deletion blocker after 12 local tests, including nested symlinks, completed-copy damage, and interruption during root removal. The remote acceptance test remains a launch gate.
- Remote synthetic test job `820952.kunanyi-ohpc` failed safely before production access. The NFS server advertises `system.nfs4_acl` but rejects reading it with `EOPNOTSUPP`. `getfacl` on the real source and home control root showed ordinary user/group/other permissions only. The revised implementation records this exact unavailable virtual attribute as JSON null, compares availability on both sides, and preserves/verifies all readable attributes and ordinary modes/ownership. It does not claim to have copied an unreadable ACL value.
- The revised local suite passes 13 tests. File/directory fsync and metadata round trips still require the rerun on the actual NFS allocation.
- At the next upload, TPAC rejected SSH because the portal authorization expired. The portal on the Mac mini requires UTAS sign-in; Barry has been asked to enable SSH again. `stage_v1.tar.gz` remains the original tested bundle remotely; the attempted `stage_v2.tar.gz` upload did not complete. The current local bundle will be uploaded under a fresh revision name after access returns.
- There is no production migration job and no active migration state yet. Do not describe the data as moved or scratch capacity as reclaimed.

### Filesystem acceptance revisions

Barry restored TPAC access. Synthetic jobs `820956` and `820957` stopped before production access and exposed two further NFS properties:

- Directory `st_size` is recursive accounting and can update asynchronously without directory content or other metadata changing. The source-stability check excludes directory size only; the exact entry set, regular-file sizes, timestamps and identity checks remain.
- Originals can belong to `hpcadmin` (gid 1001), while the account's primary group is `hpcusers` (gid 1003). The account cannot recreate the former group or its setgid directory bit. A direct toy-file probe confirmed `chown` fails with `EPERM`; this was not tested by changing any production file.

The frozen plan therefore requires `metadata_policy=private_archive`. Home directories use mode `0700`; regular files retain their original owner permissions only (`source_mode & 0700`); destination ownership is the executing uid and primary gid. Original ownership and modes remain in the immutable inventory, with the transformation documented in a durable unit receipt. Readable access ACLs/security attributes fail closed rather than being silently dropped. All payload hashes, file sizes, timestamps, link mappings, source-stability checks and deletion gates remain required. This limits archive access to Barry without granting the broader primary group access through copied group bits.

### Production launch

- Synthetic acceptance `820960.kunanyi-ohpc` finished with exit 0: all 20 tests passed on NFS in 17.4 seconds, followed by successful file/read-descriptor/directory fsync probes. The preceding `820959` run exposed unsupported path-based `chmod(..., follow_symlinks=False)`; this is now descriptor-based `O_NOFOLLOW`/`fstat`/`fchmod`.
- Independent review approved the frozen source `c70a56abf22e071da63a8c51a7eac80742b14f3d9bcbddeec3e2915a0ad4db6e`, conditional on that remote acceptance. Real/effective uid are both 145812 and real/effective gid both 1003.
- Production job `820961.kunanyi-ohpc` was submitted once on 16 October at approximately 22:52 AEDT and observed running in the copy queue. It requests one CPU, 4 GiB and 48 hours; PBS rerun is disabled. The wrapper repeats the tests before executing the frozen migration plan.
- Before submission, archive and migration state were absent. Home accounting was 5,717,812,516,834 bytes; scratch accounting was 8,796,423,717,628 bytes. The only other visible job was `q012_fit`, staged outside the X-ray roots.
- Acceptance receipts, launch inventory and frozen checksums are retained under `docs/science/assets/scratch_home_migration_2026-10-16/acceptance/`. Full original PBS receipts and each staged revision remain on Kunanyi.
- Monitor `migration.live.out`, `state/unit-*/status.json`, and the PBS job. A queued/running job is not migration completion; require the final state summary, every unit complete, matching compatibility links and actual scratch accounting before claiming reclamation.

Barry declined scheduled checks. No automation was created. PBS continues the transfer and verified cleanup independently; inspect its state at the next requested check. At handoff the first unit was still copying, so no scratch reclamation had yet been confirmed.

### 31 October inspection

The authenticated TPAC portal shell returned PBS state `F`, exit `271`, used
walltime `48:01:51` against `48:00:00`, ending 18 October at 22:54 AEDT.
`migration.err` reads `=>> PBS: job killed: walltime 172911 exceeded limit 172800`.
The first eight units are `complete`, with exact expected source-link targets,
present destinations and policy receipts, and absent tombstones. Their retained
logical payload totals 2,606,334,382,194 bytes. No new quota measurement was made.

The ninth unit (17 August C-HI rerun) is `copied`; both source and destination
directories exist, the original is not a link, no tombstone exists, and no
policy receipt has been issued. The final C-LO unit has no status record and no
destination; its original scratch directory remains. The frozen-checksum file
matches the retained acceptance copy. No large payload was rehashed in this
metadata inspection, and no migration resume or manual cleanup was performed.

The inspection JSON and its transfer checksum are retained under
`docs/science/assets/q031_q032_handoff_2026-10-31/`. See the 31 October exchange
log for the independent home-map inventory, which is available despite the
unfinished two production-tree migrations.
