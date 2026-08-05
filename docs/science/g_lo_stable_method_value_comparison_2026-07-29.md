# G-LO stable method-value comparison — 2026-07-29

Status: `complete_comparison_gate_fail_discrepancy_concentration`
Decision scope: deterministic scientific diagnostic only; no production claim.

## Question and boundary

On the fixed weighted sample of exactly 4096 particles, how do the stable
full-loss and stable adiabatic branches compare with the actual pinned
`losses="none"` branch under the two pressure treatments and two radio
frequencies? This comparison is descriptive. It does not establish transfer
to production history runs, causal superiority, or publication-facing
interpretation.

The Goal 050 recurrence gate is the prerequisite: it supports this bounded
comparison after reproducing the raw-`a2` failure and pinned fallback strata,
while leaving production adoption on hold.

## Branches and provenance

- Stable full-loss: pressure-ratio recurrence and stable gamma trajectory from
  the Goal 050 implementation.
- Stable adiabatic: bounded stable recovery trajectory with explicit endpoint
  and state checks.
- Actual `losses="none"`: pinned method output, retained exactly including any
  non-finite values; no clipping, replacement, or finite-only filtering.
- Pressure modes: unsmoothed and log-Savitzky-Golay.
- Frequencies: both configured radio frequencies.

The cache and selection hashes, staged source manifest, and pinned plutokore
commit are recorded in the companion assets. A mismatch is an infrastructure
failure, not a scientific result.

## Required gates

The diagnostic must report exact selection count and branch dimensions,
finite stable states, finite actual no-loss values, no silent fallback, no
subrelativistic state, boundary/state agreement, and a deterministic repeat.
Cutoff evidence is tri-state and is reported separately for physical and
`gamma_inf` cutoffs: zero verified cutoffs may pass; any verified real cutoff
returns `HOLD_FOR_CUTOFF_REVIEW`; malformed, unstable, or
reference-disagreeing evidence fails. Scientific ordering is reported only
when those gates are explicit and auditable. Any scientific failure or hold is
archived before the wrapper exits with status `3`; infrastructure or schema
failure exits with status `2`.

## Submission state

Exactly one bounded diagnostic, PBS `779913.kunanyi-ohpc` / `g_lo_stmv`, was
submitted to `normal`. It was verified `R` at the stop point, with queue time
`Wed Jul 29 11:30:17 2026`, allocation
`select=1:ncpus=16:mpiprocs=1:mem=96gb`, and walltime `12:00:00`.

Remote preflight passed fresh-target guards, the exact clean 41-entry
bytecode-free manifest and hashes, pinned cache and selection hashes, the exact
4096-row selection, staged `bash -n`, runtime/import closure including
`g_lo_particle_history`, and the queue's `48h` maximum walltime check. Remote
`shellcheck` was unavailable; the identical wrapper passed local `shellcheck`.

The stage is
`/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison`; the
analysis target is
`/scratch/bwbrook/xray_cavities_analysis/2026-07-29-g-lo-stable-method-value-comparison`.
Expected evidence paths are:

- archive:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/g_lo_stable_method_value_comparison_2026-07-29.tar.gz`
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/g_lo_stable_method_value_comparison.{out,err}`
- submission transcript:
  `/u/bwbrook/codex_kunanyi/goal051_g_lo_stable_method_value_comparison/remote_logs/submission_preflight_2026-07-29.txt`

Barry subsequently reported `Exit_status=3`, walltime `05:12:08`, CPU time
`49:26:11`, and `16` CPUs. The archive was retrieved and validated after
Chrome/Open OnDemand access was restored. Its structured result was `FAIL`.

The primary stable adiabatic endpoint gate passed with zero relevant
non-finite states, fallbacks, and nonpositive times. The run stopped on eight
finite differences between the accepted pressure-ratio primary form and the
algebraically equivalent time-ratio diagnostic in the first processed history
group. This was a Goal 051 gate-contract false negative: the shared adiabatic
implementation and tests report these representation-level differences but
do not make them fatal.

The repaired gate retains the disagreement count and excludes it only from
the fatal criteria. A test reproduced the original failure and passed after
the repair; `77` related tests and the shell/Python checks passed. Exactly one
fresh no-overwrite retry, PBS `780137.kunanyi-ohpc` / `g_lo_stmv_r1`, was
verified queued on `normal` at `Thu Jul 30 00:02:12 2026`.

The retry uses the same immutable cache, exact selection, pinned plutokore
commit, and wrapper. Its repaired diagnostic script SHA-256 is
`4d8d093d95fef7681d1f778e999bf0ef255bc6264881321f449ca24bc3d177e1`.

## Retry completion

PBS `780137.kunanyi-ohpc` / `g_lo_stmv_r1` finished with `Exit_status=3`,
walltime `09:54:05`, and CPU time `96:55:00`. The retrieved archive has
SHA-256
`abd34c707197f6b984d5ea9e34c07731abcb7565223e8fc01f2c6900ddc5ca62`
and contains all eight declared outputs plus the staged provenance inputs.
The archive, JSON, CSV, and NPZ contracts passed local validation; all numeric
branch arrays are finite.

The gate repair worked. All infrastructure, stable-branch, reconstruction,
conditioning, repeatability, cutoff, aggregate-difference, direction,
radiative-suppression, and spectral-index gates passed. The finite
algebraic-form disagreement counts remained visible (`30` unsmoothed and `2`
log-Savitzky-Golay) without incorrectly stopping the accepted primary
trajectory. No physical or `gamma_inf` cutoffs were found.

The formal result is nevertheless `G_LO_STABLE_METHOD_VALUE_FAIL`. The sole
failed gate is the predeclared discrepancy-concentration limit:

- the top `1%` of represented population weight contributes
  `0.951162697227638` of total absolute full-loss difference between
  log-Savitzky-Golay and unsmoothed pressure treatments;
- the allowed maximum was `0.5`;
- the fractional boundary row is used only to reach exactly `1%` population
  weight and does not create the concentration;
- two histories alone contribute `0.8339063192288018` of weighted discrepancy
  and `0.8039975607832786` without weights.

Both dominant histories are linear-smoothing affected, have only eight
history records, and sit immediately after a shock. Their analysis weights
modestly amplify the result, but do not cause it. Together they are two of the
four ordinary hash-sampled histories representing a 249-row component of a
262-row critical stratum. The full stratum represents only `0.1326%` of the
population but contributes `83.4%` of weighted discrepancy.

The aggregate pressure-method effect is modest but high-leverage. Across all
rows, log-Savitzky-Golay full-loss emissivity is about `4.4%` higher than the
unsmoothed value at both frequencies. Removing only the two dominant histories
as an influence diagnostic reduces the shift below `0.6%`; removing the first
41 ranked rows reduces it below `0.05%`. These deletions are sensitivity
diagnostics, not replacement scientific estimates.

## Decision

Retain the formal predeclared `FAIL`. Do not relax the `0.5` threshold after
seeing the result, and do not rerun Goal 051. The stable numerical
reconstruction is green, but the comparison does not yet support a
population-general pressure-method claim.

The next justified analysis is a complete 262-row census of the critical
recent-shock, lowest-history-quantile stratum using the existing immutable
cache and the same two pressure treatments and frequencies. This is the
smallest analysis that can distinguish a physically real young-particle regime
from a high-leverage extrapolation based on two sampled histories. Production
adoption and PRAiSE2 promotion remain on hold.

## Operational hazards

The pinned actual branch can contain non-finite adiabatic cells; those values
must remain visible. Stable adiabatic recovery is therefore a required branch,
not an optional finite fallback. The run must remain bounded at 4096 rows and
must not trigger all-row high-precision evaluation, production history
generation, raytracing, or any pinned-code modification.
