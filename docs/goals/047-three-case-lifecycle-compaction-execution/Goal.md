# Goal 047: Three-Case Lifecycle Compaction Execution

## Objective

Execute the exact Barry-approved Goal 046 production-file deletion ledger on
Kunanyi, prove that no unapproved path changed, and preserve a compact,
hash-bound preflight, mutation, and post-delete evidence package.

## Authority

Barry approved permanent loss of the raw production files bound to:

```text
payload_ledger.csv SHA-256:
df05b1b2176cc326ab4297a4291ae0a303eb8a96bb478329e2f483df06a6ce92

approved rows:
148 DELETE_PROPOSED_UNIQUE_RAW HDF5
148 DELETE_PROPOSED_METADATA_ONLY XMF

approved allocated-byte forecast:
6,845,659,111,424
```

Approval is exact and non-transferable. It does not authorize a regenerated
ledger, the `968` `HOLD_REGENERATION_UNPROVEN` analysis rows, radio-held
particles, ambiguous symlinks, protected sources, compact provenance,
directories, or any path outside the Goal 046 allowlist.

## Required Execution

Goal 047 must:

1. start from committed Goal 046 evidence at Git commit
   `1e9866bae48dec72347db1ffa9fa097147d93669`;
2. capture a zero-active-job pre-submission gate;
3. inside PBS, acquire an atomic lock and allow only its own job in two fresh
   active-job gates, including one after all hashing and immediately before
   mutation;
4. validate the complete immutable packet, exact ledger, source inventory,
   path allowlist, protected and held anti-joins, HDF5/XMF pairs, and
   catalogue membership;
5. preflight all `296` rows before any deletion using no-follow file
   descriptors, exact identity, single-link status, and full SHA-256;
6. delete exact files nonrecursively, HDF5 before its XMF, with a hash-chained
   fsynced transcript and stop-on-first failure;
7. reinventory every allowlisted root and prove that exactly the approved
   paths disappeared while all `16,857` retained rows remained unchanged;
8. reopen all protected HDF5 files, validate protected restart tuples and all
   holds/provenance, reconcile recovered allocated bytes, and run an
   out-of-root scratch write/read/remove probe; and
9. package only compact evidence. No raw HDF5 or particle payload may be
   copied into the repo.

## Completion States

- `submitted_waiting_pbs_completion`: one guarded job is verified queued or
  running and the PBS stop rule is active.
- `deletion_complete_postcheck_green`: exact deletion and every post-delete
  gate passed.
- `failed_closed_no_mutation`: a preflight gate failed before deletion.
- `failed_closed_partial_mutation`: at least one deletion occurred and a later
  deletion failed; no retry is authorized without a new reconciliation.
- `failed_closed_postcheck`: all planned deletion ended but a required
  post-delete check failed.
- `blocked_preflight`: access, staging, active jobs, changed identity, packet
  mismatch, or an implementation audit prevents submission.

## Stop Rule

After the PBS job is verified queued or running, report the job id, expected
evidence, and retrieval command, then stop without polling. Resume only after
Barry reports the PBS completion email or explicitly requests a status check.
