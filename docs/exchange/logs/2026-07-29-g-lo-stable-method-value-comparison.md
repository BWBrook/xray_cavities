# Exchange log — Goal 051 G-LO stable method-value comparison

Date: 2026-07-29
Status: `submitted_waiting_pbs_completion`

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

The PBS stop rule was invoked immediately after running-state proof. No
polling, retrieval, repeat submission, production run, raytrace, or scientific
inference has occurred. Wait for Barry's completion notification before a
bounded retrieval.
