# Goal 042 Cover Note: Three-Case Lifecycle Compaction Packet

Date: 2026-07-15
Status: `proposed_awaiting_barry_approval`

## Recommendation

Approve Goal 042 as drafted.

Goal 042 is an **inventory and authorization-packet goal**, not a deletion
goal. It will inspect the accepted C-HI, C-LO, and G-LO production chains and
the Goal 041 analysis roots read-only, construct an exact dependency-aware
keep/hold/delete-proposed ledger, quantify recoverable bytes, and then stop for
your approval. It cannot delete, move, truncate, overwrite, or compact any
remote payload.

Actual deletion would be a separate Goal 043 using the exact approved ledger
digest. This is deliberate: general approval to manage scratch is not a safe
substitute for approving an explicit list of unique scientific files after
their dependencies and byte totals are known.

## What Goal 042 Will Authorize

- read-only Kunanyi inventory of the known three-case production chains and
  Goal 041 analysis roots;
- a read-only PBS inventory/hash job if login-node inspection would be too
  expensive;
- classification of every payload as `KEEP`, `HOLD`, `DELETE_PROPOSED`,
  `DUPLICATE_PROPOSED`, or `QUARANTINE`;
- full path, size, hash, provenance, dependency, regeneration, and approval
  evidence for every deletion proposal;
- a byte-recovery forecast and an executable-but-not-executed Goal 043 plan;
- compact local documentation and machine-readable ledgers in this repo.

It will **not** authorize deletion, a PLUTO run, science post-processing, a new
observable, a method/default change, or any data movement to an unproven
archive.

## Conservative Scientific Holds

The draft deliberately protects:

- baseline, common-age, endpoint, and previously accepted C-HI late-age fluid
  HDF5 sources needed to reproduce existing products or revisit topology;
- endpoint restart tuples and one preceding known-good restart tuple per case;
- all particle payloads while the radio/raytracing source-retention contract is
  unresolved;
- compact catalogues, configuration, code/asset hashes, qstat, stdout/stderr,
  manifests, and decision records;
- any unique nonzero partial payload, which must be quarantined rather than
  silently deleted.

This means Goal 042 may identify substantial recoverable space from
superseded fluid checkpoints, duplicate continuation surfaces, failed analysis
roots, and reproducible Goal 041 full-map intermediates, but it will not claim
particle-space recovery until the radio hold is resolved.

## Honest Recovery Statement

There is currently no proven sanctioned archive and therefore no general
rollback for unique scratch data. Reproducible analysis intermediates can be
regenerated from retained raw sources. Byte-identical duplicates retain a
verified canonical copy. Deleted unique production snapshots would require a
new production run and may not be bitwise reproducible. That is why Goal 042
only proposes deletion and Goal 043 must receive an exact second approval.

## Precondition

Before Goal 042 performs remote inventory, the completed Goal 041 synthesis
and this approved goal packet must be committed and pushed, or Barry must
explicitly waive that provenance-lock precondition. The publication requested
for Patrick's review is intended to satisfy this lock; execution must still
confirm that local `HEAD` equals `origin/main` before remote inventory.

## Approval Choices

Barry can respond in the task with one of:

1. **Approve Goal 042 as drafted.** This authorizes read-only inventory and
   approval-packet construction only.
2. **Approve with amendments.** State any roots, holds, hash requirements, or
   desired aggressiveness to change.
3. **Hold Goal 042.** No remote inventory or deletion planning will occur.

Approval of Goal 042 is not approval of Goal 043 or any deletion ledger.
