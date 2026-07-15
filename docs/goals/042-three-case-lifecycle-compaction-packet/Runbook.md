# Runbook: Goal 042

## Start

```bash
cd /Users/bwbrook/papers/xray_cavities
pwd
git branch --show-current
git rev-parse --short HEAD
git status --short --branch
```

Do not fast-forward or reconcile the current dirty Goal 041 worktree unless
Barry has separately authorized the required commit/push or provenance-lock
waiver.

## Read First

- `AGENTS.md`
- `docs/exchange/current_status.md`
- `docs/science/xray_cavities_data_lifecycle_strategy_2026-07-10.md`
- `docs/science/assets/xray_cavities_data_lifecycle_strategy_2026-07-10/`
- `docs/science/three_case_common_age_evolution_2026-07-13.md`
- `docs/science/assets/three_case_common_age_evolution_2026-07-13/`
- `docs/goals/041-three-case-common-age-evolution/Log.md`
- Goal 019/021 C-HI late-age source-selection notes/assets
- Goal 035/038 endpoint and restart completion evidence
- Goal 040 endpoint recovery/truth note/assets
- `docs/science/three_case_spec.md`

## Initial Remote Root Allowlist

The exact discovered list must be written before inventory. Expected roots
include, but are not accepted merely because they appear here:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64
/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production
/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation
/scratch/bwbrook/xray_cavities_analysis/2026-07-13-three-case-common-age-evolution
/scratch/bwbrook/xray_cavities_analysis/2026-07-14-three-case-common-age-evolution-retry1
/u/bwbrook/codex_kunanyi/goal041_three_case_common_age_evolution
```

Do not scan `/scratch/bwbrook` broadly. Each root must have a repo-local
provenance reference and an expected case/purpose before remote inspection.

## Remote Access

Use Chrome/Open OnDemand only to enable the jumpbox SSH selector when needed,
then return to repo-local helpers:

```bash
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; date -u'
```

Do not use Safari. Do not weaken host-key checking. If the selector or host key
fails, stop with a specific blocker.

## Active-Job Gate

Before inventory and again before packaging:

- query current and historical PBS state for the project user;
- reject the packet if any queued/running job references an allowlisted root;
- capture qstat evidence compactly;
- never infer inactivity only from absent email.

## Inventory Record

For every regular file or symlink, record at least:

```text
case
run_id
root_path
path
resolved_path
file_type
device
inode
apparent_bytes
allocated_bytes
mtime_ns
sha256
sha256_status
hdf5_timestep
hdf5_time_code
hdf5_time_myr
grid_shape
catalogue_membership
data_class
lifecycle_state
canonical_path
restart_dependency
common_age_dependency
late_age_dependency
radio_dependency
topology_dependency
level3_gravity_dependency
processed_products
proposed_action
reason
regeneration_or_rollback
approval_authority
```

Use full SHA-256 in the final approval ledger. If hashing cannot complete
within the read-only job, return `blocked_inventory`; do not downgrade to a
path/size-only deletion proposal.

## Canonical Source Union

At minimum protect:

```text
C-HI fluid: baseline; common 10/20/30/40/50 Myr; outputs 46/48/49/50/51;
             endpoint and preceding restart tuples
C-LO fluid: baseline; common 10/20/30/40/50 Myr;
             endpoint and preceding restart tuples
G-LO fluid: baseline; common 10/20/30/40/50 Myr;
             endpoint and preceding restart tuples
All cases: all particle payloads pending radio source-retention decision
```

Resolve exact paths and times from accepted manifests. Do not derive protected
status from filenames alone. The erroneous historical C-HI `jet_power_erg_s`
field does not invalidate its source paths/times, but the correction must be
carried as provenance.

## Classification Rules

Apply in this order:

1. Any accepted dependency -> `KEEP` or `HOLD`.
2. Any particle payload -> `HOLD_RADIO_UNRESOLVED`.
3. Unique nonzero partial/corrupt -> `QUARANTINE`.
4. Proven byte-identical noncanonical copy -> `DUPLICATE_PROPOSED`.
5. Reproducible analysis intermediate with accepted compact output and retained
   raw source -> `DELETE_PROPOSED_REGENERABLE`.
6. Unselected superseded fluid/restart source with no dependency ->
   `DELETE_PROPOSED_UNIQUE_RAW`.
7. Any ambiguity -> `HOLD_AMBIGUOUS`.

No row may carry more than one final action.

## Read-Only PBS Inventory Job

If full hashing is too heavy for the login node, prepare a wrapper that:

- requests one node with modest CPU/memory and at most `48:00:00`;
- reads only the allowlisted roots;
- never calls `rm`, `mv`, `truncate`, `find -delete`, or a write-capable HDF5
  operation;
- writes inventories only under a new Goal 042 analysis/stage root;
- uses no-overwrite outputs and a stable archive/file-list contract;
- validates its own outputs before archive creation.

After `qsub`, verify queued/running state, report the job id and expected
outputs, and stop. Do not poll.

## Goal 043 Dry-Run Contract

Goal 042 may construct but not execute a future compactor. It must require:

```text
--ledger <approved_payload_ledger.csv>
--approval-sha256 <exact digest supplied by Barry>
--mode dry-run|execute
```

The future executor must:

- refuse any digest mismatch;
- refuse paths outside the exact allowlist;
- use `lstat` and never follow symlinks;
- verify path/type/device/inode/size/mtime/hash immediately before action;
- verify every canonical keep path before deleting a duplicate;
- delete only exact ledger rows, file by file;
- never recursively delete a nonempty directory;
- preserve a remote and locally retrieved append-only transcript;
- stop on the first mismatch without continuing;
- write pre/post inventories and recovered-byte totals;
- revalidate protected HDF5 time/datasets, endpoint restart tuples, compact
  manifests, and a scratch write/read/remove probe.

## Approval Packet Validation

Run focused checks that prove:

- CSV/JSON schemas and unique headers;
- per-action row and byte totals;
- disjoint `KEEP`, `HOLD`, `QUARANTINE`, and delete-proposed sets;
- every delete proposal has a full hash and regeneration/rollback statement;
- every duplicate has a full-hash-matched canonical copy;
- every protected source joins to an accepted manifest and remains readable;
- all particles are held;
- no raw payload was copied into Git;
- no remote mutation command appears in executed Goal 042 logs;
- shell syntax, focused tests, manifests, unresolved-marker scan, and
  `git diff --check` pass.

## Stop And Return

At `approval_packet_ready`, return the exact ledger digest, byte totals,
proposed action classes, unresolved holds, and draft Goal 043 contract. State
plainly that no deletion occurred and wait for Barry's exact approval or
amendment.

