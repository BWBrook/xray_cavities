# 2026-07-24 G-LO Radio History, Method, And Value Gate

Status: `submitted_waiting_pbs_completion`

Goal 049 is the G-LO-first discriminator requested by Goal 048. It will use
the retained accepted-lineage particle history to compare matched full-loss
and endpoint-lossless radio products before the project proposes any new
multi-node C-HI/C-LO history-regeneration runs.

Implemented locally:

- canonical lineage audit for initial `0000..0999` plus guarded
  `1000..5000`;
- field-selective, endpoint-ID-keyed history recovery with checkpointed
  chunking and post-injection completeness checks;
- actual pinned
  `plutokore.radio.praise.calculate_praise_emissivity_numba` and
  `plutokore.radio.raytracing.raytrace_particles_multiple_freq` integration;
- matched `150 MHz`/`1.4 GHz`, `0/45/90 deg` full-loss/lossless surfaces;
- beam, threshold, and ray-step sensitivity plus materiality gates; and
- compact no-overwrite packaging that excludes raw particle files and the
  dense history cache.

Validation:

```text
29 focused tests passed
Python compilation passed
actual-function method gate passed
PBS wrapper bash -n passed
git diff --check passed
independent audit: GO WITH TRACKED RESIDUALS
```

The first remote preflight correctly stopped before submission when the
Kunanyi login shell did not expose `git`. A single focused repair replaced
that accidental runtime dependency with a manifest-bound, locally verified
commit proof, while retaining a live-Git cross-check when available. The
failed stage remains preserved separately.

Repaired remote preflight:

```text
initial_count=1500
guarded_count=4001
output1000_sha256=a078189072443623d47a2153b72625448855f9cb20465f12ea5d4048c8764968
free_scratch_kib=3138479165440
staged_manifest_sha256=b2d076ac975c2fb6264dca7c5cf657e6c13d68f3e6c7a6ba6567d26c93576771
plutokore_commit=e80252cf35ff5a06166240e2867d3d485aaf6956
runtime_import_preflight=passed
```

PBS:

```text
job_id=776779.kunanyi-ohpc
Job_Name = g_lo_radhist
job_state = Q
queue = normal
qtime = Fri Jul 24 20:05:26 2026
Resource_List.select = 1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime = 48:00:00
```

Expected outputs:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value_2026-07-24.tar.gz
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value.out
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value.err
/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate/
```

Tracked residuals before any later production decision:

- particle-density/downsampling sensitivity;
- support-partition sensitivity;
- accepted X-ray/truth overlap; and
- review of the entire beam/threshold sensitivity table rather than only the
  machine decision label.

The PBS stop rule is active. No polling, retrieval, new PLUTO production,
C-HI/C-LO regeneration, raw-data deletion, commit, or push followed queued
verification.

## 2026-07-26 walltime checkpoint and resume

PBS `776779.kunanyi-ohpc` reached the 48-hour queue limit and finished with
`Exit_status=271`. Its HDF5 cache is healthy and restartable at output
`1875/5001`, with exact processed indices `0..1874`, strictly increasing
times, and no pending batch.

The cache writer was repaired for the remaining larger particle files:
sequential source reads are unchanged, while HDF5 writes now commit contiguous
time slices through a two-phase pending-batch checkpoint. An exact legacy
checkpoint migration test and crash-recovery tests passed. Provenance records
the old helper SHA-256 for outputs `0..1874` and the new helper SHA-256 for
outputs `1875..5000`.

An independent review found one material wrapper issue before submission:
resume would have truncated the previous analysis log. The wrapper now uses a
unique PBS-job log and refuses a collision. After that single repair, the full
focused gate passed with `34` tests.

Attempt 1 is preserved under:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/remote_logs/attempt1_776779
```

The immutable resume stage and new job are:

```text
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2
job_id=777005.kunanyi-ohpc
Job_Name=g_lo_radhist
state=R
queue=normal
qtime=Sun Jul 26 20:40:38 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
checkpoint_next_output=1875
legacy_helper_sha256=70a865778fbb279ad3f96a34c4f53810256824626fc21f7def1b0657bb76e654
resume_helper_sha256=19500d97e998aab0c40479cee3cffb3a09b5a60f927e821eb01611a203728ba6
```

The PBS stop rule is active. Do not poll; wait for Barry's completion email.

## 2026-07-26 completed-cache failure and repaired second resume

PBS `777005.kunanyi-ohpc` finished with `Exit_status=1` after `00:23:15`.
It nevertheless completed the expensive history phase: the cache is intact at
`next_output=5001`, shape `197568 x 5001`, with no pending write marker.
Attempt-2 scheduler, stream, run-log, archive-reservation, and cache-boundary
evidence is checksum-preserved under:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2/remote_logs/attempt2_777005
```

Two independent failures were diagnosed:

1. The old lifecycle test interpreted particle `164943` as missing at output
   `4152`, although its stored float32-derived injection time differs from
   that output time by only `3.58575e-05` and its first present record at
   output `4153` begins a continuous suffix through the endpoint.
2. Kunanyi's `tar` rejected the GNU-version-specific `--sort=name` option.

The shared cache/downstream validator now requires one absence prefix and one
continuous presence suffix, with a representation-scale injection bracket
that remains strictly capped relative to cadence. It rejects material
post-injection absence, internal gaps, and early presence. Packaging uses the
already sorted explicit file list without `--sort=name`; checksum, validation,
atomic publication, and no-overwrite controls are unchanged.

Focused validation passed (`33` tests), and an independent post-repair review
returned `GO`. Remote preflight then passed the completed cache, exact
particle-boundary smoke, staged hashes, Python/wrapper checks, preserved
attempt-2 evidence manifest, ownership/non-symlink and no-collision gates,
Kunanyi tar portability smoke, scratch reserve, and queue state.

The new immutable stage and queued resume are:

```text
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3
job_id=777006.kunanyi-ohpc
Job_Name=g_lo_radhist
state=Q
queue=normal
qtime=Sun Jul 26 21:57:38 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
cache_next_output=5001
cache_shape=197568x5001
archive=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3/g_lo_radio_history_method_value_2026-07-24.tar.gz
```

The PBS stop rule is active. Do not poll; wait for Barry's completion email.

## 2026-07-26 raw-pressure failure and read-only diagnostic

PBS `777006.kunanyi-ohpc` finished with `Exit_status=2` after `00:08:16`.
The completed cache and lifecycle contract remained intact, but the first
emissivity chunk stopped before smoothing at:

```text
ValueError: pressure history must be positive after injection
```

Attempt-3 stdout, empty stderr, run log, and readable compact archive are
checksum-preserved under
`docs/science/assets/g_lo_radio_history_method_value_gate_failure_2026-07-26/`.

The reviewed local and Kunanyi source-tree files agree that injected PRAiSE
particles begin with zero pressure/density/tracer before fluid interpolation.
That is the leading mechanism, not yet a final classification. A pressure floor
would invent loss history and is not authorized.

The chunked read-only diagnostic passed `38` focused tests plus compilation,
wrapper syntax, local diff hygiene, remote SHA/schema/cache checks, and
no-overwrite gates. PBS `777007.kunanyi-ohpc` / `g_lo_prdiag` was verified
running on `normal` with one CPU, `32 GB`, and `02:00:00`. It will classify
leading zero prefixes versus internal/negative/endpoint defects and perform
bounded canonical raw-source cross-checks. No PRAiSE retry or science mutation
occurred. The PBS stop rule is active.

## 2026-07-26 diagnostic result and pressure-treated resume

PBS `777007.kunanyi-ohpc` completed with `Exit_status=0`. Its complete-cache
scan found `10,032` exact-zero pressure records, no negative or non-finite
records, `10,030` one-record leading-zero histories, no internal non-positive
records, two endpoint-injected no-positive histories, no lifecycle violations,
and `32/32` representative canonical source matches.

The approved primary treatment trims only the joint-zero initialization sample
for the `10,030` eligible histories and excludes the two histories with no
positive state. It preserves injection time and does not floor or interpolate
pressure. A conservative comparator excludes all `10,032` affected histories.
The method remains blocked if the treatment choice changes the final decision.

The wrapper now repeats the diagnostic before PRAiSE, requires the exact count
topology, and verifies the two exceptional rows against canonical raw source
pressure, density, and tracer. Local focused validation passed `54` tests.
Remote preflight passed a fresh `112`-entry immutable manifest, exact hashes,
syntax/compile checks, and completed-cache/no-overwrite gates.

Exactly one repaired resume was submitted:

```text
job_id=777008.kunanyi-ohpc
Job_Name=g_lo_radhist
state=Q
queue=normal
qtime=Sun Jul 26 23:07:46 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v4
```

The completed cache is reused, not regenerated. No polling followed queue
verification. Wait for Barry's completion email.

## 2026-07-26 attempt-4 launch failure and manifest-hardened replacement

PBS `777008.kunanyi-ohpc` finished with `Exit_status=1` and zero CPU, memory,
and walltime usage. Its initial immutable-manifest check found that the v4
stage had bound generated
`scripts/kunanyi/python_compat/__pycache__/hdf5plugin.cpython-311.pyc`.
Preflight compilation had legitimately changed that file after manifest
creation. No diagnostic, source-lineage gate, PRAiSE, raytracing, or science
output ran.

The wrapper now rejects any manifest containing Python bytecode. A clean v5
stage contains `83` manifest entries, zero bytecode entries, and passed a
post-compilation manifest recheck plus the completed-cache and no-overwrite
gates. Focused validation passed `54` tests, Python compilation, both PBS
syntax checks, shellcheck, and `git diff --check`.

Exactly one replacement was submitted:

```text
job_id=777009.kunanyi-ohpc
Job_Name=g_lo_radhist
state=Q
queue=normal
qtime=Sun Jul 26 23:18:27 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v5
```

The completed cache is reused and remains unchanged. The PBS stop rule is
active; wait for Barry's completion email.

## 2026-07-26 endpoint no-positive overlap and replacement

PBS `777009.kunanyi-ohpc` passed the manifest and repeated pressure diagnostic
but finished with `Exit_status=2` before PRAiSE:

```text
PressureTreatmentError: pressure-treatment trim reaches beyond the endpoint
```

The two exceptional histories each contain only one present endpoint record
with joint-zero pressure, density, and tracer. The old vectorized predicate
classified that topology as both a single-leading-zero trim and no-positive,
then attempted to trim from column `5000` to `5001`.

The deterministic repair requires at least one positive record for trim,
leaves no-positive histories excluded, and enforces one treatment category per
row. An exact endpoint regression reproduced the failure before the fix and
passed afterward. The focused suite reports `55 passed`; independent review
returned GO.

A fresh v6 stage passed its `83`-entry bytecode-free post-compilation manifest,
exact runner hash, completed-cache check, and no-overwrite gates. Exactly one
replacement was submitted:

```text
job_id=777011.kunanyi-ohpc
Job_Name=g_lo_radhist
state=R
queue=normal
qtime=Sun Jul 26 23:37:44 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v6
```

No polling followed running-state verification. The completed cache is reused
and remains unchanged.

## 2026-07-27 attempt-6 smoothing failure and read-only diagnostic

PBS `777011.kunanyi-ohpc` passed the immutable stage, runtime imports, repeated
pressure diagnostic, and repaired pressure-treatment plan. It finished with
`Exit_status=2` after `00:08:14`; stderr was empty. The first new failure was:

```text
ValueError: smoothed pressure history must be positive after injection
```

The treatment completed with `197566` active rows, `10030` trimmed
initialization rows, and two excluded no-positive histories. The positive
treated pressure failed only after the current linear Savitzky-Golay filter,
so this is a smoothing-method overshoot rather than another cache, lifecycle,
or treatment defect. No PRAiSE emissivity chunk or raytrace completed.

The attempt-6 archive is readable and has SHA-256
`0049f76ebf915bdf5fc2f99c62b827a73b7e358326c746bc50bae56fff2012f2`.
Its stdout, zero-byte stderr, and archive are preserved under
`remote_logs/attempt6_777011/`.

The next action is evidence collection, not another science retry. A
bounded-memory read-only diagnostic compares unsmoothed pressure, the failing
linear Savitzky-Golay method, log-pressure Savitzky-Golay, and a
positive-kernel triangular comparator. It records invalid output counts,
affected particles and raw stencils, endpoint and ratio changes, and bounded
adiabatic-rate summaries.

Local and remote preflight passed:

```text
focused tests=41 passed
diagnostic_sha256=e82609c1c1b835a54e6533fe0c34ed19fac8db8ba2a2a9672e937b8745befd49
wrapper_sha256=e1b7d9dc65dac45aeef7bdc856013866ca507fa9ea3aada7441321b2a1206da7
cache_shape=197568x5001
cache_next_output=5001
manifest_entries=83
manifest_bytecode_entries=0
```

Exactly one read-only diagnostic was submitted:

```text
job_id=777065.kunanyi-ohpc
Job_Name=g_lo_psdiag
state=Q
queue=normal
qtime=Mon Jul 27 14:18:49 2026
resources=1 CPU, 64 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_smoothing_diagnostic_777011
```

The diagnostic does not call PRAiSE or mutate the cache. No science retry was
submitted. The PBS stop rule is active.

## 2026-07-27 smoothing diagnostic completion

PBS `777065.kunanyi-ohpc` completed the full-cache pressure-smoothing
diagnostic and then exited `1` while packaging. Stdout records
`status=diagnostic_complete`, `197566` active rows, `197398` smoothed rows,
`99108` affected rows, and `smoothing_diagnostic_validation=passed`. Stderr
contains only a GNU tar live-directory change warning.

The diagnostic JSON and `99,108`-row CSV were retrieved directly and match
their remote SHA-256 values. Linear Savitzky-Golay produces `216,035`
non-positive values across `50.21%` of smoothed histories. Log Savitzky-Golay
and the triangular comparator preserve positivity; log smoothing nevertheless
changes endpoint pressure by as much as `-83.42%` and `+25.40%`.

Linear smoothing is blocked. The next step is a deterministic stratified
actual-PRAiSE comparison of explicit `unsmoothed` and `log_savgol` modes, not a
full science retry. The diagnostic archive race is repaired locally with a
stable payload and explicit file list. No diagnostic rerun or science
submission occurred in this closeout.

## 2026-07-27 actual-PRAiSE pressure-method diagnostic

The explicit `unsmoothed` / `log_savgol` actual-function sensitivity was
implemented and independently reviewed. The sample has `4096` rows, mandatory
log-SG extremes are drawn from every active history, and the top-`1%`
concentration gate is defined over represented population mass with a
fractional boundary row. The archive carries its immutable staged-input
manifest.

Local checks passed `59` focused tests, Python compilation, wrapper syntax,
`shellcheck`, and `git diff --check`. A targeted independent review returned
`GO`.

The fresh remote stage passed exact hashes, a `120`-entry bytecode-free
manifest, runtime imports, cache metadata (`197568 x 5001`,
`next_output=5001`), no-overwrite gates, and queue preflight. Exactly one job
was submitted:

```text
job_id=777074.kunanyi-ohpc
Job_Name=g_lo_pmvalue
state=Q
queue=normal
qtime=Mon Jul 27 15:06:53 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-pressure-method-value-diagnostic
```

This is a method-value diagnostic, not a full science retry. No polling
followed queued verification.

## 2026-07-27 non-finite PRAiSE forensic continuation

PBS `777074.kunanyi-ohpc` finished with `Exit_status=2` after `01:01:06`.
Its immutable-input and runtime-import gates passed, stderr is empty, and the
first failure is `PRAiSE returned non-finite endpoint emissivities`. No result
tables were written, so the failed mode, loss branch, frequency, and particle
cannot be inferred from that attempt.

The pinned PRAiSE path uses NaN for an explicit cooled/no-emission state, but
NaN also occurs for unassigned shock states and can arise from numerical
failures. Blanket `nan_to_num`, row deletion, pressure clipping, and pressure
flooring remain prohibited.

One read-only forensic replay was therefore prepared. It runs the same
deterministic `4096` histories under `unsmoothed` and `log_savgol`, records
each mode checkpoint, and proves the exact no-emission branch before labeling
a full-loss NaN as a cutoff candidate. All other non-finites remain blocked.
No values are replaced.

Local validation passed `32` focused tests, Python compilation, wrapper
syntax, and `git diff --check`. Remote preflight passed a `121`-entry
bytecode-free manifest, exact changed-file hashes, runtime imports, immutable
input hashes, and no-overwrite gates. Exactly one job was submitted:

```text
job_id=777213.kunanyi-ohpc
Job_Name=g_lo_pnf
state=Q
queue=normal
qtime=Mon Jul 27 17:11:21 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_praise_nonfinite_forensic
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-praise-nonfinite-forensic
```

No polling followed queued verification. Wait for Barry's completion email.

## 2026-07-27: forensic completion and singleton-repaired method gate

PBS `777213.kunanyi-ohpc` completed green with `Exit_status=0`. The retrieved
forensic package proves that all `384` non-finite cells arise from the same
`48` one-record endpoint histories under both pressure modes, loss branches,
and frequencies. The inputs and replay dynamics are finite; the optimized
zero-interval PRAiSE path leaves injection gamma unassigned.

The local repair adds an explicit, fail-closed
`instantaneous_recent_shock` convention for exact valid singleton histories:
endpoint pressure and current gamma define the injection state, full-loss and
lossless must match, and singleton provenance remains separately auditable.
Exclusion is retained as a conservative comparator.

Local validation passed `75` focused tests and four wrapper syntax checks.
Remote staged hashes, immutable inputs, and no-overwrite gates passed. Exactly
one repaired method-value diagnostic was submitted and verified running:

```text
job_id=778078.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Mon Jul 27 22:06:40 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_singleton_v2
```

No full raytrace or production work was submitted. The PBS stop rule is
active; wait for Barry's completion email.

## 2026-07-27 effective-singleton overlap repair

PBS `778078.kunanyi-ohpc` stopped before PRAiSE with
`single_record=46 expected=48`. Compact logs show the immutable-input and
runtime gates passed and stderr is empty.

The observed `48` consists of `46` untrimmed singleton histories plus two
trim-affected histories that have one effective record after the approved
leading-zero trim. The repaired treatment contract represents effective
singleton status orthogonally, preserves the two-row overlap, hashes the mask,
and checks PRAiSE singleton IDs against the plan.

Local validation passed `76` focused tests, four PBS syntax checks, and
`git diff --check`. A fresh stage passed a `120`-entry bytecode-free manifest,
exact staged hashes, immutable cache/affected-row hashes, no-overwrite gates,
and normal-queue preflight. Exactly one replacement diagnostic was submitted:

```text
job_id=778079.kunanyi-ohpc
Job_Name=g_lo_pmvalue
state=Q
queue=normal
qtime=Mon Jul 27 22:51:39 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_effective_singleton_v3
```

No polling followed queued verification. No full raytrace was submitted.

## 2026-07-28 branch-semantics repair

PBS `778079.kunanyi-ohpc` finished with `Exit_status=2` after `01:54:04`.
Actual unsmoothed PRAiSE calculation completed, then the project-added
`full <= losses="none"` assertion failed. Pinned PRAiSE does not guarantee
that ordering because the `none` branch removes both adiabatic and radiative
evolution. Independent audits classify this as a diagnostic-policy defect.

The repair carries full-versus-none as descriptive evidence, adds the matched
adiabatic-only reference for the radiative gate, checkpoints all three compact
arrays, audits silent intermediate-gamma fallback, and archives evidence
before any scientific-gate failure exits nonzero. No full raytrace or
production simulation was started.

The focused local suite passed `98` tests. The fresh remote v4 stage passed
exact hashes, a `120`-entry bytecode-free manifest, wrapper syntax, runtime
imports, immutable-input checks, and no-overwrite gates. Exactly one diagnostic
was submitted:

```text
job_id=778919.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Tue Jul 28 09:35:49 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_branch_semantics_v4
```

The PBS stop rule is active. No polling or full raytrace followed.

## 2026-07-28 v4 non-finite failure and v5 evidence capture

PBS `778919.kunanyi-ohpc` finished with `Exit_status=2` after `01:27:35`.
All preflight gates passed and stderr is empty. The unchanged `4096`-row
selection was written, but no emissivity checkpoint or archive was produced.
The first failure was `PRAiSE returned non-finite endpoint emissivities`.
The v4 output does not identify the affected branch; adiabatic is a plausible
hypothesis, not an observation.

The v5 diagnostic preserves raw NaN/+Inf/-Inf cells and writes deterministic
mode/branch checkpoints, per-cell forensic records, non-finite summaries, and
replay audits. It reconciles every forensic record against the raw arrays,
suppresses finite-only comparison on any unresolved non-finite, and archives
before a deliberate scientific failure. It performs no value replacement,
clipping, flooring, or row exclusion.

The repaired implementation passed `107` focused tests, compilation, wrapper
syntax and `shellcheck`, and `git diff --check`; independent final review
returned `GO`. Remote preflight passed exact hashes, a `120`-entry
bytecode-free manifest, immutable input hashes, runtime imports, no-overwrite
gates, and queue checks. Exactly one evidence-capture job was submitted:

```text
job_id=779183.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Tue Jul 28 11:39:59 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_nonfinite_evidence_v5
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-pressure-method-value-diagnostic-nonfinite-evidence-v5
```

The PBS stop rule is active. No remote command followed running-state
verification, and no full raytrace was submitted.

## 2026-07-28 v5 completion and adiabatic numerical-recovery submission

PBS `779183.kunanyi-ohpc` completed the archive-first v5 diagnostic with a
deliberate scientific `Exit_status=3`. The retrieved evidence contains exactly
`9,103` NaNs, all and only in the adiabatic branch (`4,643` unsmoothed and
`4,460` log-Savitzky-Golay). Matched full and no-loss branches are finite.
Every affected record is replay-verified with finite dynamics inputs and a
valid shock assignment; the NaN injection gamma remains unresolved evidence
and was not replaced or excluded.

Independent diagnosis traced the failure to the pinned separate
absolute-time-power evaluation. A compact recovery diagnostic uses the
pressure-ratio/log-difference recurrence, checks it against an 80-digit
original-form reference on strictly positive relevant intervals, and preserves
the pinned failure as provenance. Independent final audit required and then
accepted a fail-closed gate proving all four selected archived
mode/frequency strata reproduce under the original path.

Local verification passed `48` focused tests, compilation, PBS syntax, and
`git diff --check`. Remote immutable-input, pinned-source, import,
no-overwrite, and queue checks passed. Exactly one compact diagnostic was
submitted and verified queued:

```text
job_id=779684.kunanyi-ohpc
Job_Name=g_lo_adrec
job_state=Q
queue=normal
qtime=Tue Jul 28 20:10:11 2026
resources=1 CPU, 32 GB, 02:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_adiabatic_recovery
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-adiabatic-recovery-diagnostic
```

The PBS stop rule is active. No polling, full comparison, raytrace, cache
mutation, history rebuild, PLUTO run, raw cleanup, commit, or push followed.

## 2026-07-28 duplicate recovery failure and guarded index-repair retry

PBS `779684.kunanyi-ohpc` and `779685.kunanyi-ohpc` both finished with
`Exit_status=2`. Their final scheduler records have the same queue/start
second and the same fixed stdout, stderr, stage, and analysis paths. Repository
records documented only `779684`, so `779685` is an unintended duplicate
submission rather than an authorized second method attempt. The duplicate
launch cause is not proven.

The shared surviving log/archive timestamps match the later `779685`
completion. That evidence is preserved under
`adiabatic_recovery_shared_stage_snapshot_after_779684_779685/` and is not
mislabelled as job-specific evidence for `779684`. The traceback shows the
first material defect:

```text
TypeError: Indexing elements must be in increasing order
```

The repair performs the HDF5 read through sorted unique cache rows, then
restores the exact requested selection order for every row-aligned field. The
wrapper also claims an atomic run lock. Local verification passed `50`
focused tests, compilation, `bash -n`, `shellcheck`, and `git diff --check`.

A new no-overwrite stage passed its `123`-entry bytecode-free manifest,
immutable hashes, pinned-source proof, runtime import, wrapper syntax, and
queue checks. Submission used a persistent atomic `qsub_once.lock`. Exactly
one corrected compact diagnostic was submitted:

```text
job_id=779693.kunanyi-ohpc
Job_Name=g_lo_adrec
job_state=R
queue=normal
qtime=Tue Jul 28 20:42:31 2026
resources=1 CPU, 32 GB, 02:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_adiabatic_recovery_index_repair_v2
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-adiabatic-recovery-index-repair-v2
```

The PBS stop rule is active. No remote command followed running-state
verification, and no full method comparison or raytrace was submitted.

## 2026-07-28 repaired adiabatic recovery completion

PBS `779693.kunanyi-ohpc` completed the repaired recovery diagnostic with
deliberate scientific `Exit_status=3`. Retrieval and archive integrity passed;
the archive SHA-256 is
`71f40e9510834acbc4475bfa59b4e22faddbba0a32dd343dcdef3b81956cf3f8`.

The stable adiabatic recovery itself passed the bounded panel: `4 / 4`
archived failure strata reproduced, all `431,744` retained stable gamma values
were finite, finite injection emissivity was reconstructed, and `98 / 98`
80-digit comparisons passed. The original composite stable-trajectory label
has been repaired locally without a remote rerun.

Goal 049 remains blocked for full-loss use. The same panel contains `22,737`
relevant non-finite `a2` intervals and `45,474` pinned gamma fallbacks. The
next justified work is a stable full-loss numerical-method gate. The
`4096`-row comparison and raytrace remain on hold.
