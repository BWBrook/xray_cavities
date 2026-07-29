# G-LO stable full-loss recurrence gate

Date: 2026-07-28

## Status

`complete_science_gate_green`

PBS `779729.kunanyi-ohpc` / `g_lo_flloss` finished with `Exit_status=0`.
The archive, stdout, and empty stderr were retrieved and independently
validated.

## Purpose

Goal 050 tests whether the retained Goal 049 G-LO failure panel supports a
stable scaled/log-domain implementation of RAiSE II equations A10-A11 without
silently retaining a prior Lorentz factor. A PASS authorizes only the later
deterministic 4096-row method-value comparison.

## Local gate

- Stable recurrence uses `lambda = a2 / t1**b` and explicit removable limits.
- Physical and `gamma_inf` cutoffs are explicit no-emission states.
- Any relevant `subrelativistic` state fails the decision and is rejected by
  emissivity reconstruction.
- Runtime analytic checks replace the former hard-coded limit pass.
- Focused tests: `16 passed`.
- Related Goal 048-050 regression tests: `161 passed in 8.61s`.
- Wrapper `bash -n`, `shellcheck`, and `git diff --check` passed.
- An independent scientific audit returned GO for the 64-trace diagnostic.

## Remote evidence

- Stage:
  `/u/bwbrook/codex_kunanyi/goal050_g_lo_stable_full_loss_recurrence_gate`.
- Immutable cache:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate/cache/g_lo_history.h5`.
- Cache size: `33191119360` bytes.
- Staged manifest: 107 entries; SHA-256
  `c39b31665adc2d0857a3d87ef066277ac3deb9f792785dd53d1f199ee240f7d9`.
- Diagnostic SHA-256:
  `5281a07b20cef6e1c8c74110e4369bc0a199686de38743c141120bc93c924e81`.
- Wrapper SHA-256:
  `39ba17966e152f9e87696e81fc8cb66b92b26f32d9812391c9630197469f856e`.
- Full staged-manifest, immutable-input, wrapper-syntax, runtime-import,
  analytic-self-check, queue, and no-overwrite preflights passed.

## Completion result

- Final scheduler state: `F`; `Exit_status=0`; `Stageout_status=1`.
- Runtime: `00:50:28`; CPU time: `02:51:50`; memory: `949788kb`.
- Archive SHA-256:
  `fee130640fb1573c82c38b46c6e212def3c1210cb9dd11ad9f9b5e498cf03d01`.
- Stderr: zero bytes.
- All 11 scientific gates passed.
- `22,737` pinned raw-`a2` NaN intervals reproduced, but every scaled
  coefficient was finite.
- All `431,744` gamma states were finite and reference matched.
- Stable silent fallbacks: `0`; relevant subrelativistic states: `0`.
- Maximum relative high-precision difference:
  `3.5644138821173953e-13`.
- All 256 endpoint emissivities were finite and non-negative.

Decision label:
`G_LO_STABLE_FULL_LOSS_RECURRENCE_GREEN_4096_COMPARISON_JUSTIFIED`.

An independent completion review returned GO for only the deterministic
4096-row method-value comparison.

## PBS submission

```text
job_id=779729.kunanyi-ohpc
Job_Name=g_lo_flloss
job_state=Q
queue=normal
qtime=Tue Jul 28 23:09:49 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=64gb
Resource_List.walltime=12:00:00
```

The submission used a persistent atomic `qsub_once.lock`.

## Retained package

- Completion note:
  `docs/science/g_lo_stable_full_loss_recurrence_gate_completion_2026-07-29.md`.
- Completion assets:
  `docs/science/assets/g_lo_stable_full_loss_recurrence_gate_completion_2026-07-29/`.
- The immutable archive retains the complete row-level evidence. Redundant
  extracted large tables were removed after validation.

## Boundaries

No 4096-row comparison, raytracing, PLUTO production, C-HI/C-LO work,
pinned-source change, scientific-default change, commit, or push occurred.
