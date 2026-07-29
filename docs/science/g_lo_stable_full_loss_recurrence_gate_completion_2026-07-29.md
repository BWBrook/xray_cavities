# G-LO Stable Full-Loss Recurrence Gate Completion

Date: 2026-07-29

Status: `complete_science_gate_green`

Decision label:
`G_LO_STABLE_FULL_LOSS_RECURRENCE_GREEN_4096_COMPARISON_JUSTIFIED`

## Decision

Goal 050 passes. PBS `779729.kunanyi-ohpc` completed with `Exit_status=0`,
the compact evidence archive was retrieved byte-for-byte, and every declared
scientific gate is green.

This result authorizes only the deterministic 4096-row method-value
comparison. It does not authorize production adoption, raytracing,
publication-facing radio interpretation, or a change to pinned PRAiSE.

## Observations

- The retrieved archive has SHA-256
  `fee130640fb1573c82c38b46c6e212def3c1210cb9dd11ad9f9b5e498cf03d01`
  and contains 10 members.
- Remote and local stderr are empty. Stdout finishes with
  `stable_full_loss_science_gate=PASS evidence_archived=1`.
- All 11 required gates passed, including analytic limits, independent
  high-precision agreement, exact state classification, one-ULP boundary
  conditioning, deterministic repeat, zero silent fallbacks, and zero
  subrelativistic states.
- The 64-trace panel contains 215,872 relevant intervals. Raw dimensional
  `a2` is NaN in exactly 22,737 intervals, reproducing the pinned failure.
  The scaled/log-domain coefficient is finite in every interval.
- All 431,744 frequency-specific gamma updates are finite and classification
  matched to the 80-digit reference. The maximum relative gamma difference is
  `3.5644138821173953e-13`.
- The pinned method's 45,474 frequency-specific retained-gamma fallbacks
  reproduce exactly. The stable implementation uses zero silent fallbacks.
- All 256 reconstructed emissivities are finite and non-negative: 248 finite
  trajectory reconstructions and eight recent-shock instantaneous values.
- The staged diagnostic and wrapper hashes match the reviewed local files, and
  the pinned `plutokore` commit remains
  `e80252cf35ff5a06166240e2867d3d485aaf6956`.

## Interpretation

On this deterministic panel, the prior failure is numerical overflow in the
raw dimensional intermediate `a2`, not evidence that the scaled recurrence
lacks a finite solution. Evaluating the coefficient actually used by the
gamma denominator in scaled/log-domain form removes that overflow without
discarding rows, retaining a previous gamma, or altering the physical model.

The real panel did not contain a physical or `gamma_inf` cutoff. Those
explicit no-emission policies are therefore supported here by reviewed code,
analytic checks, and synthetic tests rather than by an observed real-panel
cutoff. The 4096-row comparison must retain fail-closed classification and
stop if it exposes subrelativistic states, boundary instability, state
disagreement, or unexpected cutoff prevalence.

## Independent Review

An independent completion review recomputed the CSV row counts, class
distributions, finite-value checks, and maximum discrepancies; verified
archive and staged-source identity; and reran the 16 focused tests plus wrapper
syntax and `shellcheck`. It returned `GO` for the 4096-row comparison only.
No further escalation is justified before that comparison.

## Provenance And Retention

The scheduler reports `Stageout_status=1`, but the archive, stdout, and stderr
were present at the stage root and retrieved with remote/local SHA agreement.
This is retained as a scheduler caveat, not a product failure.

The local completion bundle retains the immutable 11 MB archive, compact gate
summaries, panel definition, emissivity summary, staged-source manifest, and
logs. Redundant extracted copies of the 38 MB gamma table, 17 MB interval
table, and already-retained Goal 049 non-finite record table were removed
after validation; all remain losslessly recoverable from the archive.

## Next Step

Goal 051 should execute the already-authorized deterministic 4096-row
method-value comparison using the same immutable cache, pressure modes,
frequencies, state semantics, scaled recurrence, and fail-closed gates.
It should compare the stable full-loss result with the matched adiabatic and
lossless branches, but it must not imply a production default or start
raytracing.
