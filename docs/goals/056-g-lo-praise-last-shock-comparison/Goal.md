# Goal 056 - G-LO last-shock PRAiSE comparison

Date opened: 2026-08-10
Status: `submitted_waiting_pbs_completion`

## Objective

Implement Patrick's requested deterministic, particle-level comparison of the
pinned PRAiSE1 and PRAiSE2 methods on identical G-LO inputs, using only each
particle's latest-shock-to-evaluation interval for the scientific comparison.
Keep the Goal 050 recurrence as a diagnostic comparator rather than a new
reference method.

The report must distinguish native-method behaviour from controlled
common-input behaviour and include representative pressure, Lorentz-factor,
cutoff, spectrum, emissivity, ratio, divergence, and population evidence.

## Scientific Gate

The matched three-case radio calculation remains on hold until this comparison
shows whether pinned PRAiSE2 is numerically usable and scientifically
interpretable over retained post-shock emitting intervals.

Predeclared gates require:

- the exact deterministic 4096-particle selection and Goal 050 comparator;
- positive retained native PRAiSE2 pressure histories;
- no native PRAiSE2 numerical failures in the retained interval; and
- exact agreement between instrumented PRAiSE2 replay and its high-level call.

PRAiSE2 is the intended reference implementation. This goal records method
differences; it does not alter PRAiSE2 to reproduce PRAiSE1 or Goal 050.

## Remote Job

- Job: `784909.kunanyi-ohpc` (`g_lo_lstcmp`)
- State at stop: `Q` in `normal`
- Resources: `1` node, `16` CPUs, `96 GB`, `24:00:00`
- Stage:
  `/u/bwbrook/codex_kunanyi/goal056_g_lo_praise_last_shock_comparison`
- Analysis:
  `/scratch/bwbrook/xray_cavities_analysis/2026-08-10-g-lo-praise-last-shock-comparison`

## Boundaries

This is post-processing of the immutable G-LO history cache. It does not rerun
PLUTO, change a scientific default, launch matched radio production, or compute
the separately defined Level 3 gravitational-energy component.
