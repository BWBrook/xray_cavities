# Goal 051 log

## 2026-07-29 — packet prepared

- Opened the bounded deterministic stable method-value comparison authorized by
  the Goal 050 completion gate.
- Reused the exact 4096-row weighted selection and immutable cache contract;
  no raw data were modified.
- Added the PBS execution wrapper, focused wrapper contract tests, and the
  Goal/ science / exchange evidence bundle.
- Submission was withheld at this checkpoint until the core, wrapper, and
  parent gates were complete.

## 2026-07-29 — exactly one diagnostic submitted

- Core, schema, wrapper, and parent review gates passed.
- Remote preflight established fresh targets, the exact clean `41`-entry
  manifest and hashes, no staged bytecode, pinned cache and selection hashes,
  the exact `4096`-row selection, staged `bash -n`, runtime/import closure
  including `g_lo_particle_history`, and a `48h` queue walltime ceiling.
- Remote `shellcheck` was unavailable; the byte-identical wrapper passed local
  `shellcheck`.
- Submitted PBS `779913.kunanyi-ohpc` / `g_lo_stmv` exactly once.
- At the handoff stop point it was `R` on `normal`, with queue time
  `Wed Jul 29 11:30:17 2026`, allocation
  `select=1:ncpus=16:mpiprocs=1:mem=96gb`, and walltime `12:00:00`.
- Stage:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison`
- Analysis:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison`
- Expected archive:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/g_lo_stable_method_value_comparison_2026-07-29.tar.gz`
- Submission transcript:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/remote_logs/submission_preflight_2026-07-29.txt`

Status is `submitted_waiting_pbs_completion`. The stop rule was invoked
immediately after running-state proof: no polling, retrieval, repeat
submission, production work, raytracing, or scientific inference is
authorized before Barry reports completion.

## 2026-07-29 — completion reported; retrieval pending

- Barry reported PBS `779913.kunanyi-ohpc` / `g_lo_stmv` completed with
  `Exit_status=3`, walltime `05:12:08`, CPU time `49:26:11`, `16` CPUs,
  memory `3008872kb`, and virtual memory `5674728kb`.
- The wrapper contract maps exit `3` to either scientific `FAIL` or
  `HOLD_FOR_CUTOFF_REVIEW` after evidence archival.
- The exact result remains unclaimed because the archive and
  `stable_method_value_summary.json` have not yet been retrieved.
- The TPAC route currently stops at Microsoft sign-in in Chrome. No repeat
  submission or alternative unreviewed access route was attempted.

Status is `completion_reported_scientific_exit_3_retrieval_pending`.

## 2026-07-29/30 — retrieved false-negative gate and submitted one repair retry

- Chrome/Open OnDemand access was restored and a final scheduler record
  confirmed `job_state=F`, `Exit_status=3`, `Stageout_status=1`, walltime
  `05:12:08`, and CPU time `49:26:11`.
- Retrieved archive SHA-256:
  `4f7b689fb30bc44f1d35557fbbfd32272f895acd41a7f730a3be8eeb907ec27c`.
- The structured result was `G_LO_STABLE_METHOD_VALUE_FAIL`, with all
  infrastructure gates green and exact selection count `4096`.
- The primary unsmoothed stable adiabatic endpoint gate passed. Relevant
  non-finite, fallback, and nonpositive-time counts were zero. The only
  triggering count was eight finite algebraic-form differences in the first
  group processed.
- Root-cause review found a Goal 051 contract mismatch: the shared adiabatic
  helper and accepted tests treat those finite representation-level
  differences as diagnostic-only, but Goal 051 required the count to be zero
  in both its per-group and aggregate gates.
- Added a regression that failed under the original code, removed only the
  diagnostic count from the fatal criteria, and kept it in the reported
  summary.
- Related verification passed `77` tests, Python compilation, wrapper
  `bash -n`, `shellcheck`, and `git diff --check`.
- Independent review reproduced the prior 32 marginal differences among
  `431744` retained cells and confirmed the pressure-primary recurrence still
  passed the declared high-precision tolerance.
- Staged a fresh bytecode-free retry surface with exact hashes and a distinct
  no-overwrite analysis root.
- Submitted PBS `780137.kunanyi-ohpc` / `g_lo_stmv_r1` exactly once. It was
  verified `Q` on `normal` at `Thu Jul 30 00:02:12 2026`, with `16` CPUs,
  `96gb`, and `12:00:00`.

Status is `repair_retry_submitted_waiting_pbs_completion`. The stop rule is
active. If the retry encounters a different material scientific gate, stop
rather than begin another incremental repair cycle.

## 2026-07-30 — retry complete; numerical repair green; concentration gate fails

- Barry reported PBS `780137.kunanyi-ohpc` / `g_lo_stmv_r1` completed with
  `Exit_status=3`, walltime `09:54:05`, CPU time `96:55:00`, `16` CPUs,
  memory `3583696kb`, and virtual memory `6062712kb`.
- Final scheduler inspection confirmed `job_state=F`, `Exit_status=3`, and
  `Stageout_status=1`. The requested stage-root archive and logs were present
  despite the scheduler stageout caveat.
- Retrieved the retry archive into a distinct no-overwrite local subdirectory.
  SHA-256 is
  `abd34c707197f6b984d5ea9e34c07731abcb7565223e8fc01f2c6900ddc5ca62`;
  it has 12 members and all eight declared Goal 051 outputs.
- CSV schema and row-count checks passed. The two NPZ bundles contain the
  expected finite `4096 x 2` branch arrays. JSON parsing, identity contracts,
  branch reconstruction, determinism, cutoff handling, aggregate difference,
  ordering, radiative suppression, and spectral-index gates passed.
- The repair succeeded: finite algebraic-form disagreement counts remain
  reported but no longer cause the false negative.
- The formal result remains `G_LO_STABLE_METHOD_VALUE_FAIL` because the sole
  failed gate is `comparison_discrepancy_concentration`.
- The top `1%` of represented population weight accounts for
  `0.951162697227638` of total absolute pressure-method discrepancy, above the
  predeclared maximum `0.5`.
- Two eight-record, immediately post-shock histories contribute
  `0.8339063192288018` of weighted discrepancy and
  `0.8039975607832786` before weights. Weighting modestly amplifies but does not
  create the concentration.
- The two are half of the four ordinary hash-sampled histories representing a
  249-row component of the 262-row dominant stratum. An influence diagnostic
  excluding only those two reduces the aggregate method shift from about
  `4.4%` to below `0.6%`.
- Kept the predeclared formal failure and stopped the retry ladder. No
  threshold was weakened post hoc and no new PBS job was submitted.

Status is `complete_comparison_gate_fail_discrepancy_concentration`. The next
justified analysis is a full 262-row census of the critical stratum from the
existing immutable cache, not another Goal 051 rerun or production job.
