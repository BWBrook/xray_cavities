# G-LO stable method-value comparison — 2026-07-29

Status: `submitted_waiting_pbs_completion`
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

The stop rule was invoked immediately after running-state proof. No completion
polling or retrieval has occurred, and no scientific decision is available.

## Expected evidence

The eight declared outputs are listed in `Goal.md`. A completed `PASS` or
`HOLD_FOR_CUTOFF_REVIEW` comparison must contain all eight. An early scientific
`FAIL` may archive the available partial diagnostic evidence, but a missing
summary or malformed output schema is an infrastructure failure. The wrapper
archives evidence together with the staged manifest, plutokore commit proof,
selection input, and explicit archive file list. No archive is generated in
the local handoff; the remote archive is expected only after job completion.

## Operational hazards

The pinned actual branch can contain non-finite adiabatic cells; those values
must remain visible. Stable adiabatic recovery is therefore a required branch,
not an optional finite fallback. The run must remain bounded at 4096 rows and
must not trigger all-row high-precision evaluation, production history
generation, raytracing, or any pinned-code modification.
