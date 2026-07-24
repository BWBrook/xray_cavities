# Runbook: Goal 046 And Future Goal 047

## Authority Boundary

Goal 046 is read-only. It prepares an approval packet and a dry-run validator;
it cannot delete, move, truncate, overwrite, or change permissions.

Future Goal 047 may execute only after Barry supplies the exact approved
`payload_ledger.csv` SHA-256. The approval digest is mandatory, not optional.
Approval of one digest does not authorize a regenerated or amended ledger.

## Current Evidence

Use:

- `authorization_packet/payload_ledger.csv`;
- `authorization_packet/inventory_metadata.json`;
- `authorization_packet/remote_root_allowlist.csv`;
- `authorization_packet/protected_path_contract.csv`;
- `authorization_packet/active_hold_register.csv`;
- `authorization_packet/goal047_execution_contract.csv`;
- `authorization_packet/local_asset_manifest.sha256`;
- `completed_run/review_inventory/`;
- `completed_run/catalogue_snapshot/`; and
- compact PBS, archive, and active-job evidence under `completed_run/`.

All paths above are relative to:

```text
docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/
```

## Goal 046 Validation

Run the focused suite and require the exact approved digest:

```bash
uv run pytest \
  tests/test_three_case_lifecycle_contract.py \
  tests/test_three_case_lifecycle_inventory.py \
  tests/test_three_case_lifecycle_inventory_wrapper.py \
  tests/test_three_case_lifecycle_authorization.py -q

uv run python scripts/science/validate_three_case_lifecycle_dry_run.py \
  --packet docs/science/assets/three_case_lifecycle_compaction_authorization_2026-07-23/authorization_packet \
  --expected-digest <BARRY_APPROVED_LEDGER_SHA256>
```

The validator must fail if the digest is absent or mismatched.

## Immediate Pre-Execution Gate

Before Goal 047 is allowed to mutate any path:

1. Refresh the TPAC selector through Chrome if required.
2. Capture hostname, UTC time, exact `qstat -u bwbrook` command, exit status,
   and raw output.
3. Stop if any queued or running job references an allowlisted root.
4. Re-read the approved ledger and verify its exact SHA-256.
5. Verify the packet manifest has complete expected-name coverage.
6. Reconcile all ledger source fields against the frozen source inventory.
7. Anti-join proposed deletion rows against the protected and held unions.
8. Recompute production HDF5/XMF pairs and catalogue membership.
9. For every approved deletion row, use `lstat` without following symlinks and
   revalidate absolute normalized path, allowlisted root, type, device, inode,
   size, nanosecond mtime, and full SHA-256.

Any mismatch stops the entire execution before deletion.

## Exact Mutation Contract

Goal 047 must:

- accept only rows whose action is explicitly approved for deletion;
- use exact normalized file paths from the approved ledger;
- never follow a symlink;
- never recursively delete a directory;
- delete files one at a time;
- stop on the first mismatch or failed deletion;
- record pre-action identity, expected hash, observed hash, action result, and
  recovered allocated bytes in an append-only transcript; and
- preserve the transcript remotely and retrieve a compact local copy.

Unique production HDF5 deletion has no sanctioned rollback. Recovery requires
rerunning PLUTO, and fine-cadence trajectory reconstruction is lost.

## Mandatory Post-Deletion Validation

Before Goal 047 may be called complete:

1. Reinventory every allowlisted root and reconcile exact deleted and retained
   paths.
2. Confirm all approved deleted paths are absent and no other path changed.
3. Reopen every protected HDF5 file and revalidate timestep, code time, shape,
   and required datasets.
4. Resolve every protected endpoint, source, and preceding restart tuple.
5. Confirm all radio-held particle rows, ambiguous symlinks, compact
   provenance, manifests, catalogues, configuration, and accepted products
   still exist.
6. Recompute actual recovered allocated bytes and compare them with the
   approved forecast.
7. Run a scratch write/read/remove probe outside protected roots.
8. Package the pre/post inventories, transcript, validation results, and
   checksums without copying raw HDF5 or particle payloads locally.

Any failed post-delete check yields a failed-closed completion state and
requires immediate reporting; do not continue with further deletion.

## Stop And Return

Goal 046 returns the exact ledger digest and waits for Barry's explicit
approval, amendment, or rejection. Goal 047 must separately stop after any PBS
submission, and again after post-delete validation, under the normal PBS
handoff rule.
