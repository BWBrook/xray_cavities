# Codebase Simplification Audit

Date: 2026-08-05
Scope: read-only architecture and retention review, followed by one focused
implementation tranche.

## Promise and protected invariants

This repository is a private scientific control-plane shell. Its job is to
make the active analysis path legible, reproducible, and auditable; it is not
an enterprise compatibility product. The protected invariants are:

- scientific source data and accepted derived products are not silently
  overwritten;
- remote jobs remain explicit, inspectable, and fail closed;
- compact products retain enough provenance to explain how they were made;
- historical goal evidence remains discoverable in its dated goal, exchange,
  and science records.

## Measured shape

The repository currently contains 78 science scripts (42,482 lines), 98 PBS
wrappers (11,994 lines), and 81 test files (16,309 lines). A static AST pass
found 1,914 functions and 63 classes. The largest files are several thousand
lines long, while the active workflow is mostly a sequence of small
preflight, product, validation, and packaging steps.

The main architectural burden is therefore not missing capability. It is
repetition and historical accumulation:

- `docs/exchange/current_status.md` had grown to roughly 5,800 lines, mixing a
  short handoff with a long historical ledger;
- 98 PBS wrappers repeat archive, checksum, and file-list logic;
- the science asset tree contains many exact duplicate groups, especially
  transport copies and repeated coordinate/selection tables;
- oversized diagnostic scripts often combine input validation, computation,
  interpretation, and packaging in one file or function.

## Disposition

| Surface | Disposition | Rationale |
| --- | --- | --- |
| Living status handoff | Simplify | Keep only active decisions, holds, and resume pointers. |
| Dated goal/exchange/science records | Retain | These are the historical provenance record. |
| Repeated archive contract | Simplify | One small fail-closed helper is preferable to wrapper-local copies. |
| Exact duplicate assets | Defer deletion | Map first; delete only with a verified canonical owner and no live reference. |
| Large diagnostic scripts | Defer structural refactor | Start with one representative path after measuring its call graph and tests. |
| Backwards-compatibility layers | Delete when encountered | This private repository has no external compatibility promise. |

## Asset retention map

| Class | Canonical treatment | Action in this tranche |
| --- | --- | --- |
| Accepted science notes and compact tables | Keep under the dated goal/science path | Protected; no deletion. |
| Raw HDF5, particle, and production payloads | Keep remotely while an active analysis depends on them | No local bulk copy; no deletion here. |
| Retrieved archives and remote logs | Keep as immutable transport provenance until the compact product is accepted | Preserve; do not overwrite on rerun. |
| `remote_stage` or copied scripts/wrappers | Transport provenance only | Candidate for later pruning after reference search. |
| Byte-identical axes, selection inputs, and repeated TSVs | Generated/review duplicates | Candidate for canonical-owner consolidation, not automatic deletion. |
| Failure and repaired bundles | Keep until the repaired result is accepted and indexed | Preserve current Goal 051–054 evidence. |

The existing data-lifecycle strategy remains the governing deletion policy. This
note is a map for decisions, not a second ledger.

## Tranche result and next cut

This tranche shortens the living handoff, extracts one representative archive
contract, and separates the pressure-method execution/checkpoint phase from
the larger G-LO diagnostic orchestrator. It does not touch science results or
remote data. The remaining diagnostic script is still large; any further
split should wait for a named consumer or a material maintenance failure.
