# Exchange log — Goal 051 G-LO stable method-value comparison

Date: 2026-07-29
Status: `complete_comparison_gate_fail_discrepancy_concentration`

Goal 050 authorized one bounded deterministic 4096-row comparison. The packet
now binds the immutable cache and selection hashes and the pinned plutokore
commit, with stable full-loss, stable adiabatic, and actual pinned no-loss
branches across both pressure modes and frequencies.

The output contract contains eight files, including
`stable_method_value_cutoff_records.csv` for the separate physical and
`gamma_inf` tri-state cutoff evidence.

All eight are required for a completed `PASS` or `HOLD_FOR_CUTOFF_REVIEW`; an
early scientific `FAIL` may archive partial diagnostic evidence, while a
missing summary or malformed schema is an infrastructure failure.

The PBS wrapper requests `normal`, one node, `16` CPUs, `96gb`, and `12:00:00`.
It enforces a persistent stage lock, immutable-input checks, no-overwrite
guards, runtime import checks, explicit output archiving, and a schema-aware
scientific/infrastructure exit contract.

Core, wrapper, and parent gates passed. Remote preflight then established
fresh targets, the exact clean 41-entry bytecode-free manifest and hashes,
pinned cache/selection hashes, exact 4096-row selection, staged `bash -n`,
runtime imports including `g_lo_particle_history`, and the `48h` queue
walltime ceiling. Remote `shellcheck` was unavailable; the identical wrapper
passed local `shellcheck`.

Exactly one job was submitted: PBS `779913.kunanyi-ohpc` / `g_lo_stmv`. It was
verified `R` on `normal` at the stop point, with queue time
`Wed Jul 29 11:30:17 2026`, allocation
`select=1:ncpus=16:mpiprocs=1:mem=96gb`, and walltime `12:00:00`.

- Stage:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison`
- Analysis:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison`
- Expected archive:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/g_lo_stable_method_value_comparison_2026-07-29.tar.gz`
- Stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/g_lo_stable_method_value_comparison.{out,err}`
- Submission transcript:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/remote_logs/submission_preflight_2026-07-29.txt`

Barry reported PBS `779913.kunanyi-ohpc` completed with `Exit_status=3`,
walltime `05:12:08`, and `16` CPUs. That code means scientific `FAIL` or
`HOLD_FOR_CUTOFF_REVIEW` after evidence archival; it does not distinguish the
two.

The archive was retrieved after Chrome/Open OnDemand access was restored.
SHA-256 is
`4f7b689fb30bc44f1d35557fbbfd32272f895acd41a7f730a3be8eeb907ec27c`.
The structured decision was `FAIL`, with all infrastructure gates passed.

The failure was a false-negative Goal 051 gate mismatch. The primary stable
adiabatic endpoint gate passed with zero relevant non-finite states,
fallbacks, and nonpositive times. Eight finite pressure-primary versus
time-diagnostic differences in the first processed history group triggered a
hard stop, even though the shared helper and accepted Goal 049 contract retain
those representation-level differences as diagnostics.

The repair removes only this diagnostic count from the fatal group and
aggregate criteria. The count remains reported. A test reproduced the false
failure before the change; the repaired related suite passed `77` tests.
Independent review reproduced the accepted prior marginal-difference evidence
and recommended one fresh retry.

Exactly one no-overwrite retry, PBS `780137.kunanyi-ohpc` /
`g_lo_stmv_r1`, was verified queued on `normal` at
`Thu Jul 30 00:02:12 2026`, requesting `16` CPUs, `96gb`, and `12:00:00`.
Its stage is
`/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison_r1`
and its analysis root is
`/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison-r1`.

Barry reported retry PBS `780137.kunanyi-ohpc` completed with `Exit_status=3`,
walltime `09:54:05`, and CPU time `96:55:00`. The retry archive was retrieved
without overwriting the original failure evidence. Its SHA-256 is
`abd34c707197f6b984d5ea9e34c07731abcb7565223e8fc01f2c6900ddc5ca62`.

All eight declared outputs are present. CSV schemas are unique, both NPZ
branch bundles have the expected finite `4096 x 2` arrays, the JSON decision
is parseable, and there are no cutoffs. The gate-contract repair is green; the
original algebraic-form diagnostic no longer causes a false stop.

The retry formal decision remains `G_LO_STABLE_METHOD_VALUE_FAIL` because the
sole failed gate is `comparison_discrepancy_concentration`. The top `1%` of
represented population weight contributes `0.951162697227638` of discrepancy.
Two histories contribute `0.8339063192288018` with weights and
`0.8039975607832786` without weights. Both are eight-record, immediately
post-shock histories affected by linear smoothing.

This is a localized scientific sensitivity, not a new implementation failure.
No additional Goal 051 PBS retry is justified. The recommended next step is a
complete evaluation of the 262-row critical stratum from the existing cache,
before any production-method decision. PRAiSE2 promotion remains on hold.
