# Goal 046: Three-Case Lifecycle Compaction Authorization

## Objective

Inventory the accepted C-HI, C-LO, and G-LO production and analysis estate on
Kunanyi read-only, reconcile every payload against the accepted scientific
dependency union, and produce an exact approval packet for later compaction.

Goal 046 supersedes the unexecuted Goal 042 proposal while preserving its
two-key safety boundary. It may construct and test a dry-run executor, but it
must not delete, move, truncate, overwrite, or change permissions on any
inventoried payload.

## Approved Decision

Barry approved Goal 046 on 2026-07-23.

The goal covers the full three-case estate in one inventory tranche. The only
mandatory handoff is before irreversible deletion. A later Goal 047 may execute
only exact rows bound to the ledger digest Barry approves.

On 2026-07-24 Barry explicitly approved permanent loss of the raw production
files represented by ledger SHA-256
`df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92`.
That approval authorizes Goal 047 to delete exactly its `296` proposed
production rows, subject to every pre-delete, stop-on-mismatch, transcript, and
post-delete validation gate in the Goal 046 Runbook. It does not authorize
deletion of the `968` `HOLD_REGENERATION_UNPROVEN` analysis rows or any other
held or protected path.

## Acceptable Completion States

1. `submitted_waiting_pbs_completion`: a read-only inventory job was submitted,
   verified queued or running, and the PBS stop rule was invoked;
2. `approval_packet_ready`: the inventory was retrieved and an exact
   dependency-aware retention/deletion proposal plus Goal 047 contract is ready
   for Barry's approval;
3. `blocked_inventory`: access, active jobs, changed identity, unresolved
   ownership, missing evidence, or an incomplete inventory prevents a
   defensible proposal.

`deletion_complete` is not an allowed Goal 046 state.

## Scientific Dependency Union

Protect at least:

- immutable configuration, catalogues, scheduler evidence, source and asset
  hashes, logs, manifests, accepted compact products, and decision records;
- exact Goal 041 baseline and nominal 10/20/30/40/50 Myr fluid sources for
  C-HI, C-LO, and G-LO;
- accepted C-HI late-age fluid outputs 46, 48, 49, 50, and endpoint 51;
- accepted endpoint restart tuples, their source restart, and the immediately
  preceding validated restart where distinct;
- all particle payloads while radio/raytracing source retention remains
  unresolved;
- baseline and endpoint fluid sources required by the unresolved Level 3
  gravitational-energy convention.

Goal 045 retires the Goal 044 X-ray-validation lifecycle hold. The completed
three-case synthesis retires the comparison and active-production holds.
Publication-method uncertainty remains a scientific caveat, but it does not
create an unbounded raw-data hold beyond explicitly protected sources.

## Classification Priority

Assign one final lifecycle action in this order:

1. `KEEP_PROTECTED`;
2. `HOLD_RADIO_UNRESOLVED`;
3. `HOLD_ACTIVE_OR_MUTABLE`;
4. `HOLD_AMBIGUOUS`;
5. `QUARANTINE`;
6. `DELETE_PROPOSED_INVALID`;
7. `DELETE_PROPOSED_DUPLICATE`;
8. `DELETE_PROPOSED_REGENERABLE`;
9. `DELETE_PROPOSED_METADATA_ONLY`;
10. `DELETE_PROPOSED_UNIQUE_RAW`;
11. unmatched rows default to `HOLD_UNCLASSIFIED`.

Legitimate zero-byte provenance, such as an empty successful stderr file, is
not invalid debris. Homogeneous groups may summarize the inventory, but every
future executable deletion must resolve to an exact file row.

## Risk-Tiered Identity Policy

Require a fresh full SHA-256 for:

- every deletion candidate;
- every retained canonical counterpart whose identity makes a deletion safe;
- compact immutable provenance when hashing is inexpensive.

Untouched large `KEEP` or `HOLD` payloads may instead use an existing trusted
hash or two stable read-only identity snapshots containing:

- `lstat` path, type, device, inode, size, allocated bytes, and nanosecond
  modification time;
- catalogue membership;
- HDF5 timestep, time, dataset names, and shapes where applicable; and
- an explicit identity method, status, hash provenance, and verification time.

A changed file, failed candidate hash, missing protected source, unresolved
symlink, or identity conflict fails closed.

## Remote Scope

Build the allowlist only from accepted repo evidence. It may cover:

- canonical and historical production/continuation roots needed to resolve
  current ownership;
- Goal 019 and Goal 021 accepted C-HI late-age analysis/stage roots;
- Goal 040 and Goal 041 endpoint/common-age analysis and stage roots;
- Goal 044 and Goal 045 validation analysis/stage roots; and
- absent historical roots when absence itself is lifecycle evidence.

Do not scan `/scratch/bwbrook` or `/u/bwbrook` broadly.

## Required Inventory Outputs

The remote inventory must produce:

- `remote_root_inventory.csv`;
- `payload_inventory.csv`;
- `inventory_summary.csv`;
- `inventory_metadata.json`;
- a deterministic manifest digest;
- compact stdout/stderr and scheduler evidence; and
- a stable file-list archive containing only compact inventory evidence.

The later local authorization packet must add:

- protected-path and active-hold registers;
- the exact payload ledger;
- duplicate/canonical evidence;
- deletion-candidate and retention summaries;
- recovery forecasts by case, root, class, and action;
- no-delete conditions;
- an independently recomputed ledger digest; and
- a dry-run-only Goal 047 execution contract.

## Hard No-Delete Conditions

No row may be proposed for deletion when:

- a queued or running job references its root;
- it intersects the protected dependency union;
- particle/fluid radio dependency is unresolved;
- path ownership, symlink target, catalogue membership, HDF5 identity, or
  canonical copy is ambiguous;
- the payload changed during inventory;
- a unique nonzero partial or corrupt payload lacks explicit disposition;
- a duplicate lacks matching full hashes and a readable canonical copy;
- rollback or regeneration consequences are unstated;
- the exact executable file list or ledger digest is missing; or
- post-deletion validation is not specified.

## Validation

- Test inventory traversal on synthetic trees without mutating source files.
- Reject overlapping roots, output paths inside inventoried roots, symlink
  following, duplicate contract paths, and changed files.
- Parse every CSV/JSON output and reject duplicate headers or missing columns.
- Validate protected-source joins against accepted manifests.
- Independently anti-join every deletion candidate against all protected and
  held rows.
- Independently recompute row and byte totals.
- Test future dry-run collision, symlink, changed-file, and digest-mismatch
  failures.
- Run focused tests, Python compilation, wrapper syntax checks, manifest
  verification, unresolved-marker scans, and `git diff --check`.
- Keep raw HDF5 and particle payloads out of the local repo.

## Stop Rule

After a PBS inventory submission is verified queued or running, wake Barry
with the job id, expected products, and retrieval instructions, then stop
without polling. After completion, retrieve compact evidence and stop again at
the exact deletion approval surface.
