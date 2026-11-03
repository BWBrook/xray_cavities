# PBS stocktake and review of the 3-November updates

Date: 4 November 2026 AEDT. Codex turn #6.
Source checkout: `0f8bf2b`, refreshed by a clean fast-forward.

Barry requested current PBS status and consideration of the new updates with
Claude. This is a status/review handoff; it does not report new scientific
extractions or a change to the detector or simulation physics.

## Live accounting and completion receipts

Observed 23:33–23:35 UTC on 3 November:

| Job | Work | State / exit | Walltime |
| --- | --- | --- | --- |
| 872733 | Cluster reflective, 50 Myr | F / 0 | 01:02:29 |
| 872734 | Cluster outflow, 50 Myr | F / 0 | 01:00:30 |
| 872735 | Group reflective, 50 Myr | F / 0 | 00:55:31 |
| 872736 | Group outflow, 50 Myr | F / 0 | 00:55:26 |
| 870323 | Scratch-to-home migration | F / 0 | 51:03:27 |
| 870374 | Flux analysis | H, system hold | Not started |
| 871717 | Native emission pilot | H, system hold | Not started |

The five finished jobs each recorded `Stageout_status=1`; exit status and
product evidence were inspected separately.

All four control run directories contain `output_receipt.json` with status
`validated_paired_control_run` and `budget_receipt.json` with status
`validated_paired_control_budget`. Each has six snapshots, zero-byte
`launcher.err`, and `final_stage_checksums.txt` containing 740 successful checks.
Saved ages, rounded to six decimals, are:

- Cluster twins: 0, 9.982848, 19.814243, 29.645500, 39.904056, 50 Myr.
- Group twins: 0, 9.810191, 19.661365, 29.512236, 39.362797, 50 Myr.

These are inspected run-time receipts and recorded checksum results, not a
fresh independent read/hash of the native arrays. Full pair validation and
repair/residual materiality still precede causal interpretation.

The migration's `state/verified-manifest.json` and ten `unit-*/status.json`
records all report complete, totalling 8,796,208,343,281 logical bytes. Assertions
passed for every source being a symlink resolving to its existing archive
directory, and for every tombstone being absent. No payload hashes were rerun,
no source data were deleted, and no quota claim is made.

The remaining flux dependency is `afterok:870373`, despite that prerequisite
being F/0. The completed migration has left its afterok list. The native pilot
still lists the smoke, migration and flux prerequisites. Both holds are type
`s`. This establishes an apparently stale dependency, not its scheduler-level
cause. Next operational step: revalidate existing flux smoke/packaging receipts
and reconcile the hold without bypassing validation or creating duplicates.

## Scientific review sent to Claude

The independent review covered `25b9bcb`, `8f97bb8` and `0f8bf2b`; 56 focused
interior/output-validator tests passed. No material code blocker was found.
No code was changed in this review.

Correspondence thread 29 messages 2868–2869 record the proposed sequence:

1. Validate full paired products and apply the supplied interior cuts. Keep
   40 kpc conditional. Define negligible on a scientifically relevant energy
   scale before inspecting interior results; retain signed and cell-L1
   component contrasts and each twin's drift from its own initial state.
2. Implement separate R100/R300 budgets for all valid snapshots of all four
   jet cases, with full-speed radii, same-cell initial subtraction, binary
   tracer partition and explicit boundary coverage. Changing apertures require
   care in conservation interpretations.
3. Implement the G-HI 20-Myr path-length/emission/shock diagnostic separately
   from the frozen 40-Myr pilot. Validate lateral shock geometry from local
   hydrodynamics, retain fixed/refitted background replacement tests, and
   distinguish 5% deficit arcs from bright-shell contours.

Claude's adjudication is pending. No interior acceptance, spherical-budget
result, bow-shock alignment, shell-filling result or new detector is adopted.
The full production-matched simulation remains held.
