# Retained flux measurements and safe migration resume — 31 October 2026

Barry's instruction in Codex chat: “Go ahead with the boundary and nozzle flux
measurements using the retained outputs, and resume the migration safely from
its checkpoint. Keep coordinating with Claude.” Q-032 remains Claude's stream;
Codex owns these Q-031 diagnostics and migration/handover files.

## Migration repair and evidence

The frozen 16 October source, plan, tests and PBS wrapper remain unchanged.
The original production job 820961 exceeded its 48-hour allocation after eight
complete units; C-HI was copied with verification unfinished, C-LO unstarted.
The 31 October login-node preflight stopped because symlinks exposed an extra
SELinux label. On copy node n001 within PBS 870297 the original symlink
metadata matched. C-HI still stopped the source identity guard: all 7,129
entries had manifest device 46 versus current device 45. Entry set, type,
inode, size (except the accepted directory accounting exclusion), mtime,
ctime, mode, ownership, xattrs and symlink targets otherwise matched.

The exact NFS4 exports were verified on n001:

- `/scratch/bwbrook`: `<nfs-ip>:/hpc-kunanyi/scratch/bwbrook`, FSROOT `/`.
- `/u/bwbrook`: `<nfs-ip>:/hpc-kunanyi/home/bwbrook`, FSROOT `/`.

`resume_xray_migration_device_transition.py` binds this one transition to unit
8, its immutable manifest and exact mount identities. It changes expected
device values only in memory. A new receipt-bound epoch requires fresh
source/archive SHA-256 matches for every C-HI regular file; all original
verification records are ignored for that pass. Interrupted fresh hashing can
resume only with unchanged full signatures and the same transition receipt.
Frozen rename, compatibility-link, destination and deletion-ledger guards
remain. Units 0–7 and C-LO use the frozen implementation.

Independent review found no safety blocker. It additionally modified a promoted
archive file to different bytes of the same size and restored mtime: cleanup
rejected the changed full signature and retained the tombstone. Thirty local
migration tests plus ten subtests passed. On n001, both original and new
unittest suites and file/directory fsync probes passed before submission.
The node's old util-linux required raw `findmnt` output rather than JSON;
the parser requires exactly one line and four fields.

Remote stage: `/u/bwbrook/codex_kunanyi/scratch_home_migration_2026-10-16`.

- Source-inspection SHA-256:
  `de5a8aa7d9c050a3294635ba86e20fbe6e94125827e23bbfc098752e0f8bbe5b`.
- Repair bundle SHA-256:
  `fefc773c37741c24291198d05aae30f9a6dbbee9322df1fc74e76385750e7da7`.
- Pre-resume state/log archive `pre_device_transition_state_20261031.tar.gz`:
  `7dbf18b18b61e7c01e8df078226736e8ec1eb0b109dee4e7e1e92c213884f510`.

The new checksum manifest covers the frozen files, three repair files and
source inspection. Old logs/state are preserved in the pre-resume archive;
the frozen original logs also remain in place. The first submission attempt
was rejected because the interactive preflight occupied the copy queue's
per-user CPU allowance; it created no migration job. The completed preflight
allocation was then released. Resume PBS `870323.kunanyi-ohpc` was accepted
from the login node with 72 hours on the copy queue.

## Flux implementation and smoke

See `docs/science/q031_retained_flux_measurements_2026-10-31.md` for estimands,
geometry, reconstruction/time/padding sensitivity and interpretation limits.
Thirteen local analytic/provenance tests pass after the explicit-NO correction.

First smoke 870316 failed the configuration validator after passing ten remote
synthetic tests. Preserve its entire stage
`/u/bwbrook/codex_kunanyi/q031_flux_measurements_2026-10-31`.
Corrected smoke 870321 uses a fresh `_r3` stage with package SHA-256
`9e9f3e03c86d63677de92b9ee6ca8614957d98cbe7402faaa5ecad5b5ab8974a`.
The full four-case measurement must depend on successful migration and smoke,
and independently recheck all ten completion states, links and no-tombstone
conditions before reading C-HI/C-LO. No scientific closure is claimed on
scheduler acceptance alone. No scheduled monitoring was created.

## Initial submitted state (superseded flux jobs)

- `870323.kunanyi-ohpc`: running on n001, copy queue, 1 CPU / 4 GB / 72 h;
  new checksum/test/fsync gates passed and C-HI reached verification.
- `870321.kunanyi-ohpc`: running, normal queue, 2 CPUs / 8 GB / 4 h;
  all thirteen synthetic tests passed and two retained G-LO snapshots are being
  processed on the exact node grid.
- `870334.kunanyi-ohpc`: full four-case flux job, submitted with
  `depend=afterok:870321.kunanyi-ohpc:870323.kunanyi-ohpc`, 2 CPUs / 8 GB / 48 h.
  A prior 72-hour request was rejected by the normal queue's 48-hour maximum
  and created no job. The archived r3 wrapper retains its original 72-hour
  directive; the accepted submission overrides it explicitly with 48 hours.
  The maintained repository wrapper now defaults to that verified limit.

Scheduler state is execution evidence only. Require per-case compact manifests
and scientific review for flux conclusions; require all ten migration receipts,
archive links and no tombstones plus fresh scratch accounting for completion.
The 72-hour migration can still need a further safe resume; no guarantee of
finishing the remaining multi-terabyte verification/copy is implied.

## Flux I/O refinement

Smoke 870321 completed its first retained G-LO snapshot in 433.087 seconds.
The contiguous HDF5 layout made repeated x-plane selections costly. The code
now caches exactly the outer two active planes on each domain face during the
existing storage scan. The 437.7-MiB cache preserves the reconstructed values,
face shapes, summation order and output schema. Direct versus cached rows agree
exactly on a varied, nonuniform synthetic fixture with nonzero potential; the
cache also works after closing the HDF5 file and rejects incomplete contents.
Fifteen focused flux tests pass.

Codex cancelled only flux smoke 870321 and its held dependent 870334 to replace
them with this version. Migration 870323 was left running. The r3 stage and its
partial snapshot are retained. Fresh r4 bundle SHA-256:
`d4cda060ae0e3a3e8e9d7434e52590818461faeb27c756ae544bf0a1f2a57f17`.

Independent cache review checked coordinate-encoded planes across five unequal
and minimum-dimension shapes, including negative boundary indices. All arrays
matched exactly; the nonuniform HDF5 output dictionaries also matched. The
fully touched cache process peaked at 479.4 MiB RSS. Reordering storage before
face fluxes changes no mutable scientific state or output order. No blocker
was found. The fifteen-test suite and syntax checks passed.

## Replacement submitted state

- Smoke `870352.kunanyi-ohpc`: running on n001, 2 CPUs / 8 GB / 4 h; all 15
  remote tests passed. Fresh stage
  `/u/bwbrook/codex_kunanyi/q031_flux_measurements_2026-10-31_r4`.
- Full four-case `870353.kunanyi-ohpc`: submitted with
  `depend=afterok:870352.kunanyi-ohpc:870323.kunanyi-ohpc`, 2 CPUs / 8 GB / 48 h.
- Migration `870323.kunanyi-ohpc` continues unchanged on the copy queue.
- Superseded smoke `870321` finished after cancellation with exit 143; held
  full job `870334` is also finished. Their outputs remain in the r3 stage.

## Claude coordination

Correspondence discussion 29 records the work split and reciprocal review.
Codex sent the launch revision and cache-equivalence evidence in message 2673.
Claude's Q-032 synthetic results remain reported results pending independent
branch/product audit. The next separate remote tranche is the existing 60-map
method ladder; it does not promote a replacement production detector.

The method discussion preserves three distinctions: enthalpy flux already
includes pressure work; a prescribed dense rim can mask a synthetic cavity but
needs mass/temperature/emissivity and native-path-length checks before explaining
a real run; initial-state maps are not automatically a matched evolved no-jet
counterfactual. The saved viewing angles are azimuths, not jet inclinations.
