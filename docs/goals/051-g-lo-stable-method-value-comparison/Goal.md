# Goal 051 — G-LO stable method-value comparison

Date opened: 2026-07-29
Status: `submitted_waiting_pbs_completion`

## Objective

Quantify the descriptive value of the stable G-LO loss-method branches on the
fixed deterministic weighted sample of exactly 4096 particles. Compare stable
full-loss recurrence and stable adiabatic recovery with the actual pinned
`losses="none"` branch for both pressure modes and both radio frequencies.

This is a bounded diagnostic gate. It does not authorize production history
generation, raytracing, publication-facing interpretation, or changes to the
pinned PRAiSE/plutokore implementation.

## Inputs and provenance

- Cache: `/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate/cache/g_lo_history.h5`
- Cache SHA-256:
  `f161d55eb860102f2e052b81053c94c0232926e5259cc07e2b4bc57f276ddc30`
- Selection CSV: `pressure_method_selection.csv`
- Selection SHA-256:
  `35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df`
- Expected selected rows: `4096`
- Pinned plutokore commit:
  `e80252cf35ff5a06166240e2867d3d485aaf6956`

The selection, cache, staged source manifest, and commit proof are immutable
inputs. Any mismatch is an infrastructure failure and must stop the run.

## Method and gate contract

The core diagnostic must preserve the actual pinned branch values, including
non-finite cells. Stable full-loss and stable adiabatic trajectories are used
for the corresponding method-value branches; the stable adiabatic branch is
not inferred from a finite-only reconstruction of the old pressure diagnostic.

Required gates include exact selection and branch shape, finite stable states,
finite actual `losses="none"` values, no silent fallback, no subrelativistic
states, boundary/state agreement, and deterministic repeatability. Cutoffs use
a tri-state policy: zero verified cutoffs may pass; any verified real cutoff
returns `HOLD_FOR_CUTOFF_REVIEW`; malformed, unstable, or
reference-disagreeing cutoff evidence fails. Physical and `gamma_inf` cutoff
evidence are reported separately. Scientific ordering is descriptive and must
not be promoted to causal or production validity.

## Output contract

The analysis directory must contain these eight files:

- `stable_method_value_selection.csv`
- `stable_method_value_unsmoothed_branches.npz`
- `stable_method_value_log_savgol_branches.npz`
- `stable_method_value_particle_comparison.csv`
- `stable_method_value_ordering.csv`
- `stable_method_value_cutoff_records.csv`
- `stable_method_value_gate_summary.csv`
- `stable_method_value_summary.json`

The PBS wrapper archives the outputs, staged manifest, commit proof, and input
selection before returning. Exit `0` means scientific `PASS`; exit `3` means a
scientific `FAIL` or `HOLD_FOR_CUTOFF_REVIEW` after evidence archival; and exit
`2` means infrastructure or domain failure. A completed `PASS` or
`HOLD_FOR_CUTOFF_REVIEW` comparison must contain all eight declared outputs. An
early scientific `FAIL` may archive partial diagnostic evidence, while a
missing summary or malformed schema is an infrastructure failure.

## Execution boundary

The wrapper uses one `normal`-queue node (`16` CPUs, `96gb`, `12:00:00`) with
`OMP_NUM_THREADS=16` and `NUMBA_NUM_THREADS=16`.

Exactly one diagnostic was submitted:

- PBS job: `779913.kunanyi-ohpc`
- Job name: `g_lo_stmv`
- Queue/state at the stop point: `normal` / `R`
- Queue time: `Wed Jul 29 11:30:17 2026`
- Allocation: `select=1:ncpus=16:mpiprocs=1:mem=96gb`
- Walltime: `12:00:00`
- Stage:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison`
- Analysis:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison`

Remote preflight passed fresh-target guards, the exact clean 41-entry
bytecode-free manifest and hashes, pinned cache/selection hashes, exact
4096-row selection, staged `bash -n`, runtime imports including
`g_lo_particle_history`, and the queue walltime limit. Remote `shellcheck` was
unavailable; the identical wrapper passed local `shellcheck`.

The PBS stop rule was invoked immediately after the running-state proof. Do
not poll, retrieve, resubmit, or infer a scientific result until Barry reports
completion.
