# Turn-15 completion check

Live check: 11 November 2026, starting at 09:57 UTC (20:57 AEDT).
Barry requested the scheduler check after waiting without email. Scheduler
records and small completion receipts were read through the authenticated
cluster terminal.

All six jobs are terminal with exit status zero:

| Analysis | Job | State / exit | Start, AEDT | Wall time |
| --- | --- | --- | --- | --- |
| C-HI history | 876542 | F / 0 | 5 Nov 09:36:34 | 12:37:05 |
| C-LO history | 876543 | F / 0 | 5 Nov 22:13:39 | 10:25:16 |
| G-LO history | 876544 | F / 0 | 6 Nov 08:38:55 | 11:06:50 |
| G-HI history except index 20 | 876552 | F / 0 | 5 Nov 10:02:02 | 12:04:42 |
| G-HI index 20 | 876555 | F / 0 | 5 Nov 16:06:16 | 00:23:39 |
| G-HI emission/filling | 876556 | F / 0 | 5 Nov 16:29:55 | 01:20:43 |

The `qstat -xf` records show `Mail_Points = n` for every job. The original
submission receipts also specify `-m n`; absence of email therefore provides
no evidence that a job is pending. No job was changed or resubmitted during
this check.

## Receipt checks

Small aggregate completion JSON files were read directly from the retained
analysis stages. Assertions verified case identity, completion status, exact
requested/completed index lists and per-snapshot product counts.

- C-HI: 50 requested history points plus the separately reviewed smoke at
  index 1 cover exactly 0--50, with no missing index.
- C-LO and G-LO: each covers exactly 0--50.
- G-HI: the 47-point history plus the separate index-20 result cover exactly
  0--47. Snapshots 48--50 remain outside the accepted retained range.
- Total native coverage: 201 snapshots across the four cases.
- All three G-HI phase receipts report
  `completed_frozen_GHI_analysis_phase`: history binds 143 files, first20
  binds six, and emission binds 36.
- The emission completion receipt reports
  `completed_GHI20_source_emission_diagnostic`, case G-HI, index 20. Its
  `scientific_qualification.qualified` field remains false.

The emission completion receipt SHA-256 observed in this check is
`4ca1a4f445ae1d65d6a7aa7619ccea7745d545266656875ddfb469487affd31e`.
Historical submission states and source pins remain in
`../../science/assets/turn15_spherical_budgets_2026-11-05/execution/submission_summary.json`;
that dated receipt has not been rewritten.

## Interpretation and next work

These are scheduler and aggregate-receipt checks. They establish execution
completion and complete declared coverage, without a fresh hash audit of every
output or scientific acceptance of the new numerical/emission results. Only
the earlier C-HI snapshot-1 result has the independent scientific review
reported in the turn-15 handover. Emission qualification holds remain in force.

Next: retrieve the compact products into the project's ignored incoming
directory, verify their source/input/product receipts, review the four-case
histories and G-HI/20 diagnostic, then update the component/proxy comparisons.
