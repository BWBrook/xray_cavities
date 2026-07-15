# Goal 042: Three-Case Lifecycle Compaction Packet

## Objective

Produce an exact, approval-ready lifecycle compaction packet for the accepted
C-HI, C-LO, and G-LO production and common-age analysis surfaces on Kunanyi.

The goal must inventory the relevant remote payloads read-only, reconcile them
against every active scientific dependency, classify each file or homogeneous
file group, quantify bytes retained and proposed for recovery, and prepare a
hash-locked execution contract for a separate Goal 043. Goal 042 must not
delete or move any remote data.

## Acceptable Completion States

1. `approval_packet_ready`: complete local keep/hold/delete-proposed ledgers,
   verified remote evidence, byte totals, unresolved holds, and a draft Goal
   043 execution contract are ready for Barry's exact approval;
2. `submitted_waiting_pbs_completion`: a read-only inventory/hash PBS job was
   submitted and verified queued/running, then the PBS stop rule was invoked;
3. `blocked_inventory`: a specific access, storage-layout, hashing, provenance,
   or dependency ambiguity prevents a defensible deletion proposal.

`deletion_complete` is not an allowed Goal 042 state.

## Decision Basis

- The project lifecycle policy is `promote, prove, then prune`.
- Goal 041 completed a validated three-case synthesis at nominal
  `10/20/30/40/50 Myr` and `0/45/90 deg`; no further Goal 041 remote compute is
  required.
- Compact Goal 041 archives, case products, synthesis tables, figures,
  manifests, logs, and scheduler evidence are local and validated.
- Full maps, raw HDF5, restart surfaces, and particle payloads remain on
  Kunanyi scratch.
- No sanctioned writable archive is currently proven. Deletion of unique
  scientific data therefore has no general rollback and requires Barry's
  explicit approval of the exact payload.
- Radio/raytracing, final X-ray topology, and Level 3 gravity remain open
  method lanes. Their raw dependencies must not be inferred away merely
  because Goal 041 synthesis is complete.

## Goal Boundary

Goal 042 ends at the deletion decision surface. It may prepare and test a
fail-closed compaction program in dry-run mode, but it must not execute a
destructive action. Goal 043 may execute only the exact ledger later approved
by Barry.

This two-goal boundary is required because the deletion list and recoverable
byte total do not yet exist. Approval must bind to a concrete ledger digest,
not to an estimated class of files.

## Inventory Scope

### Production chains

Inventory the known accepted three-case chains, including segmented and
continuation roots whose unique files or symlinks may contribute to the final
canonical surface:

- C-HI fresh and final `prod64` roots;
- C-LO initial bounded run and all accepted continuation roots through the
  endpoint-oriented completion;
- G-LO endpoint-oriented production and guarded continuation roots.

The exact allowlist must be built from repo evidence and recorded before any
remote job. Discovery may add a root only if it is referenced by accepted
catalogues, manifests, logs, or source-selection tables. Broad `/scratch`
scanning is out of scope.

### Analysis and stage roots

- Goal 041 initial failed analysis roots;
- Goal 041 successful retry analysis roots;
- Goal 041 stage-root archives and logs, inventoried but retained by default;
- other Goal 040/041 compact provenance only where needed to verify an
  accepted dependency.

No unrelated project or user scratch root may be inspected.

## Required Keep Contract

The following are `KEEP` or `HOLD` unless the approval packet provides stronger
case-specific evidence and Barry later approves a change:

1. **Immutable provenance**
   - configuration, executable/source/asset hashes;
   - `grid.out`, restart/output catalogues, qstat, stdout/stderr, markers,
     inventories, and decision notes;
   - retrieved compact archives and their verified local copies.
2. **Fluid science sources**
   - exact zero-time baseline for every case;
   - Goal 041 common-age sources at nominal 10/20/30/40/50 Myr;
   - accepted C-HI late-age sources from Goals 019/021: outputs
     `46`, `48`, `49`, `50`, and endpoint `51`;
   - accepted endpoint fluid source for each case;
   - any additional source explicitly referenced by an unresolved method lane.
3. **Restart safety**
   - accepted endpoint restart tuple per case;
   - one preceding known-good restart tuple per case;
   - all files required to interpret and use those tuples, including matching
     XMF/catalogue/configuration and particle restart surfaces.
4. **Open method lanes**
   - all particle payloads remain `HOLD_RADIO_UNRESOLVED` until a separate
     machine-readable radio source-retention contract selects a safe subset;
   - fluid sources needed for the conditional topology lane;
   - baseline and endpoint fluid surfaces needed for a future Level 3 gravity
     convention.
5. **Ambiguous data**
   - unique nonzero partial/corrupt payloads are `QUARANTINE`, not delete;
   - any file with unresolved symlink/canonical ownership, changed metadata,
     missing hash, or conflicting time/index evidence is `HOLD_AMBIGUOUS`.

## Permitted Delete-Proposal Classes

Goal 042 may propose, but not execute, deletion of:

- zero-byte or proven invalid failed staging artifacts;
- byte-identical noncanonical duplicates with a validated retained canonical
  copy;
- reproducible Goal 041 full-map/transient analysis intermediates after the
  compact archive and local synthesis manifests are revalidated;
- superseded fluid checkpoints not selected by any accepted source manifest,
  restart contract, or active method hold;
- obsolete continuation symlinks or empty directory shells after canonical
  ownership is proven;
- superseded restart payloads older than the endpoint and preceding
  known-good tuples, provided they are not selected science sources.

Particle payloads cannot enter `DELETE_PROPOSED` in Goal 042.

## Required Deliverables

Create a dated local package containing at least:

- `remote_root_inventory.csv`;
- `payload_ledger.csv`;
- `canonical_source_register.csv`;
- `active_hold_register.csv`;
- `duplicate_evidence.csv`;
- `deletion_candidate_summary.csv`;
- `retention_summary.csv`;
- `recovery_forecast.csv`;
- `no_delete_conditions.csv`;
- `goal043_execution_contract.csv`;
- `inventory_metadata.json`;
- `local_asset_manifest.sha256`;
- compact read-only remote logs;
- a science/operations note explaining observations, inferences, assumptions,
  uncertainty, and the recommended deletion decision;
- updates to the exchange log, current status, and this goal log.

The packet must state exact proposed bytes by case, root, data class, and
action. It must include the SHA-256 digest that a later Goal 043 approval would
bind to.

## In Scope

- Local repo evidence review.
- Chrome/Open OnDemand only to enable the TPAC SSH selector if required.
- Read-only remote commands through repo-local Kunanyi helpers.
- One or more read-only PBS inventory/hash jobs if required for safe filesystem
  load and complete hashes.
- Local deterministic ledger construction and dry-run compactor tests.
- Compact evidence retrieval after Barry reports PBS completion or explicitly
  authorizes a re-check.

## Out Of Scope

- No file deletion, move, truncation, overwrite, or permission change.
- No recursive `rm`, cleanup by directory age, or deletion by filename alone.
- No PLUTO production or continuation.
- No XRAiSE, PRAiSE, radio, cavity, Level 3, topology, or comparison rerun.
- No scientific-default or method decision.
- No migration to an unproven archive.
- No source/control repo cleanup.
- No commit or push unless Barry separately authorizes it.

## Hard No-Delete Conditions

The final decision must be `blocked_inventory` or contain zero approved
deletion bytes if any of these remain true for a candidate:

- Goal 041 synthesis and compact manifests are not locked and revalidated;
- an active PBS job references any inventoried root;
- canonical ownership or symlink targets are unresolved;
- path, size, mtime/inode, HDF5 time/index, or hash changed during inventory;
- a source appears in any accepted age, endpoint, restart, radio, topology, or
  gravity dependency set;
- duplicate status lacks matching full SHA-256 and a readable canonical copy;
- the payload is a unique nonzero partial/corrupt file;
- the proposed action cannot be represented as an exact allowlisted file list;
- the final ledger digest differs from the reviewed digest;
- post-deletion validation and provenance retrieval are not fully specified.

## Validation

- Parse every CSV/JSON output and reject duplicate headers or missing required
  columns.
- Validate case/time/source joins against accepted manifests.
- Validate all proposed duplicate hashes and canonical paths.
- Recompute action totals independently from the per-payload ledger.
- Ensure `DELETE_PROPOSED` and every `KEEP`/`HOLD` set are disjoint.
- Test the proposed compactor only in synthetic/local dry-run mode.
- Run focused tests, shell syntax checks, manifest verification, targeted
  unresolved-marker scans, and `git diff --check`.
- Verify the local packet contains no raw HDF5 or particle payloads.

## Final Report

Return:

- final status;
- exact roots inventoried;
- PBS job id/state if an inventory job was submitted;
- retained, held, quarantined, duplicate, and deletion-proposed byte totals;
- all unresolved dependencies and no-delete triggers;
- ledger and metadata paths plus SHA-256 digest;
- draft Goal 043 execution recommendation;
- current git status;
- explicit confirmation that no remote payload was deleted or moved.

