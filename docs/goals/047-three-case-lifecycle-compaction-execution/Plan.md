# Plan: Goal 047

## Phase 1 - Freeze And Audit

- Commit and push the exact approved Goal 046 packet.
- Implement the executor, PBS wrapper, and synthetic destructive tests.
- Require the exact ledger digest, action counts, byte forecast, confirmation
  token, and approval receipt.
- Independently audit code paths that can mutate remote data.

Stop before remote staging on any unresolved destructive-risk finding.

## Phase 2 - Remote Preflight

- Refresh the TPAC selector through Chrome when needed.
- Stage only Git-anchored source, the immutable Goal 046 packet and frozen
  completed evidence, and the Goal 047 approval receipt.
- Verify every staged SHA-256, Python compilation, wrapper syntax, no-overwrite
  output reservations, and the exact ledger digest.
- Capture `qstat -u bwbrook` and require zero active jobs before `qsub`.

## Phase 3 - Submit Once

- Submit one `normal`-queue, one-node, eight-CPU, `64gb`, `48:00:00` PBS job.
- Verify it is queued or running.
- Invoke the PBS stop rule immediately; do not poll.

## Phase 4 - Complete And Reconcile

After Barry reports completion:

- retrieve final scheduler, stdout, stderr, authoritative transcript, and
  compact archive;
- verify archive and internal manifests;
- reconcile deleted rows, recovered bytes, protected/HDF5/restart/hold checks,
  and post-inventory evidence; and
- report either `deletion_complete_postcheck_green` or the exact failed-closed
  state. Never retry a partial mutation without a new approved reconciliation.
