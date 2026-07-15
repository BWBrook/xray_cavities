# Plan: Goal 042

## Phase 0 - Lock Provenance And Starting State

- Record `pwd`, branch, short HEAD, and `git status --short --branch`.
- Require the Goal 041 synthesis and Goal 042 packet to be committed/pushed,
  or record Barry's explicit waiver.
- Revalidate Goal 041 synthesis and compact case manifests.
- Read the lifecycle strategy, source manifests, endpoint/restart evidence,
  C-HI late-age source selections, and open science holds.
- Construct an exact remote-root allowlist from accepted repo evidence.

Stop if provenance is not locked, the allowlist is ambiguous, or a root is
outside the X-ray Cavities project namespaces.

## Phase 1 - Read-Only Remote Inventory

- Refresh the TPAC selector through Chrome only if needed.
- Check for active jobs referencing any candidate root.
- Inventory regular files, symlinks, allocated/apparent bytes, inode/device,
  timestamps, resolved canonical targets, and catalogue membership.
- Read HDF5 headers/time/dataset shapes without copying payloads locally.
- Record particle inventory and catalogue/time evidence, but classify every
  particle payload as radio-held.
- Use a PBS inventory/hash job if complete hashing is unsuitable for the login
  node. Submit, verify queued/running, wake, and stop without polling.

No mutation is permitted in this phase.

## Phase 2 - Build The Dependency Ledger

- Form the union of all accepted source sets, not only Goal 041:
  - case baselines;
  - common ages 10/20/30/40/50 Myr;
  - C-HI accepted late ages from outputs 46/48/49/50/51;
  - endpoint and preceding restart tuples;
  - open radio, topology, and gravity holds.
- Resolve segmented/continuation ownership and symlink relationships.
- Assign exactly one lifecycle action to each payload.
- Compute full SHA-256 for all keep, hold, duplicate, quarantine, and proposed
  deletion rows before the approval packet is declared complete.
- Record an honest regeneration or rollback statement per action class.

## Phase 3 - Derive The Compaction Proposal

- Summarize bytes by case, root, data class, and action.
- Separate automatically eligible invalid/duplicate files from unique
  science-data deletion proposals.
- Flag reproducible analysis intermediates separately from expensive raw
  production snapshots.
- Keep particle recovery at zero while the radio hold is active.
- Generate exact allowlisted file lists and the proposed Goal 043 ledger
  digest.
- Construct a dry-run-only compactor and test it against synthetic trees,
  including symlink, collision, changed-file, partial-file, and digest-mismatch
  failures.

## Phase 4 - Independent Acceptance Checks

- Independently recompute all byte totals from the payload ledger.
- Verify protected source/time joins and endpoint/restart tuples.
- Verify duplicate hashes and canonical readability.
- Confirm every unique partial is quarantined.
- Confirm no action follows symlinks or crosses an allowlisted root.
- Confirm no actual remote mutation occurred.

## Phase 5 - Package And Stop

- Write the dated science/operations note and machine-readable assets.
- Update the exchange log, current status, and Goal 042 log.
- Report the exact ledger digest and proposed recovered bytes.
- Stop at `approval_packet_ready` and ask Barry to approve, amend, or reject
  the exact Goal 043 deletion ledger.

Do not execute Goal 043 within Goal 042.

