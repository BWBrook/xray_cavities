# Goal 049 Log

## 2026-07-24: Goal opened

Barry approved Goal 049 following the Goal 048 decision
`THREE_CASE_LOSS_AWARE_RADIO_BLOCKED_G_LO_METHOD_VALUE_GATE_REQUIRED`.

The goal is framed as a G-LO-first discriminator. It will validate the retained
history and actual `plutokore` PRAiSE/raytracing path, then quantify the value
of full losses before the project asks for two new `C-HI`/`C-LO` multi-node
history-regeneration runs.

No remote command, PBS submission, production run, raw-data mutation, commit,
or push occurred while opening the goal.

## 2026-07-24: source-lineage amendment

Read-only Kunanyi preflight found exactly `1500` initial and `4001` guarded
particle outputs. Output `1000` is byte-identical across roots, matching Goal
038's documented restart record, but sampled later overlap outputs `1250` and
`1499` differ by SHA-256. This is consistent with the guarded run being a
replay from the accepted output-1000 restart rather than a byte-identical copy
of the later initial trajectory.

Goal 049 therefore selects initial `0000..0999` plus guarded `1000..5000` as
the canonical accepted endpoint lineage. Initial `1001..1499` remains
superseded alternate-trajectory provenance and will not be merged. The remote
job must fail closed unless the exact output-1000 anchor, the `0999/1000`
switch cadence, and the guarded `1499/1500` cadence all pass.

## 2026-07-24: submitted and waiting for PBS completion

Status: `submitted_waiting_pbs_completion`.

Implemented a field-selective, endpoint-ID-keyed, chunked history reader; an
actual-function `plutokore` PRAiSE/raytracing adapter; a restartable
history/emissivity/raytrace/value-gate runner; and one compact, no-overwrite
Kunanyi wrapper.

The local gate passed:

```text
uv run pytest \
  tests/test_g_lo_particle_history.py \
  tests/test_g_lo_radio_method_value.py \
  tests/test_run_g_lo_radio_history_value.py \
  tests/test_g_lo_radio_history_method_value_wrapper.py -q
29 passed in 5.45s
```

Python compilation, wrapper `bash -n`, the actual pinned-function method gate,
and `git diff --check` also passed. The local actual-function gate recorded
finite full/lossless PRAiSE output, exact one-worker/two-worker determinism,
and stable integrated ray sums at `0.05/0.1/0.2 kpc`.

An independent methodological audit returned `GO WITH TRACKED RESIDUALS`.
Particle-density/downsampling sensitivity, support-partition sensitivity, and
accepted X-ray/truth overlap are required before a green result can support a
request for new `C-HI`/`C-LO` production. They do not block this G-LO
value-of-information run.

The first remote preflight stopped before submission because Kunanyi's login
shell did not expose `git`. No analysis root or PBS job existed at that point.
The focused repair binds a locally verified
`e80252cf35ff5a06166240e2867d3d485aaf6956` commit proof and every staged
source file into the SHA-256 manifest; live Git is an additional cross-check
when available, not a required runtime dependency. The failed immutable stage
was preserved at:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_preflight_failed_git_20260724
```

The repaired preflight passed:

```text
initial_count=1500
guarded_count=4001
output1000_sha256=a078189072443623d47a2153b72625448855f9cb20465f12ea5d4048c8764968
free_scratch_kib=3138479165440
staged_manifest_sha256=b2d076ac975c2fb6264dca7c5cf657e6c13d68f3e6c7a6ba6567d26c93576771
plutokore_commit=e80252cf35ff5a06166240e2867d3d485aaf6956
runtime_import_preflight=passed
```

Exactly one PBS post-processing job was submitted:

```text
job_id=776779.kunanyi-ohpc
Job_Name = g_lo_radhist
job_state = Q
queue = normal
qtime = Fri Jul 24 20:05:26 2026
Resource_List.select = 1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime = 48:00:00
```

Remote paths:

```text
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-24-g-lo-radio-history-method-value-gate
archive=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value_2026-07-24.tar.gz
stdout=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value.out
stderr=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/g_lo_radio_history_method_value.err
```

The PBS stop rule is active. No polling, retrieval, C-HI/C-LO regeneration,
PLUTO production, raw deletion, commit, or push occurred after queued-state
verification.

## 2026-07-26: walltime checkpoint repaired and resumed

Status remains `submitted_waiting_pbs_completion`.

PBS `776779.kunanyi-ohpc` finished at the queue walltime with
`Exit_status=271` after `48:01:49`. This was a scheduler walltime termination,
not an accepted science result. The partial cache reopened cleanly at
`next_output=1875` of `5001`; processed output indices were exactly
`0..1874`, times were strictly increasing, and no pending-batch marker was
present.

The remaining work would be inefficient with the original per-output HDF5
column writer because later particle files are larger. The cache helper now
retains sequential source parsing but commits contiguous output batches to
HDF5. Its two-phase checkpoint order is:

```text
pending-batch marker flush
data slice flush
next_output flush
pending-batch marker removal
```

The exact legacy-cache migration path, interrupted unaligned batches, and a
post-commit stale marker are covered by tests. Cache provenance records two
writer segments:

```text
outputs 0..1874:
  serial_column_v1
  helper_sha256=70a865778fbb279ad3f96a34c4f53810256824626fc21f7def1b0657bb76e654
outputs 1875..5000:
  sequential_chunk_batched_v2
  helper_sha256=19500d97e998aab0c40479cee3cffb3a09b5a60f927e821eb01611a203728ba6
```

One independent review found and blocked a resume-time log-provenance defect:
the wrapper would have truncated the original analysis log. The focused repair
uses a unique PBS-job analysis log and fails closed on collision. The complete
focused gate then passed:

```text
34 tests passed in 6.65s
Python compilation passed
PBS wrapper bash -n passed
trailing-whitespace scan passed
```

Attempt-1 scheduler/stdout/stderr/run-log evidence is preserved with a
checksum manifest at:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate/remote_logs/attempt1_776779
```

A new immutable resume stage was built rather than mutating the original:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2
```

Its 82-entry staged-input manifest, wrapper syntax, runtime compilation,
source ownership/path gates, first-attempt evidence checksums, writer hashes,
archive/output no-overwrite gates, queue state, scratch capacity, and live
cache checkpoint all passed. Exactly one resume job was submitted:

```text
job_id=777005.kunanyi-ohpc
Job_Name = g_lo_radhist
job_state = R
queue = normal
qtime = Sun Jul 26 20:40:38 2026
Resource_List.select = 1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime = 48:00:00
```

Resume stdout/stderr are unique:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2/g_lo_radio_history_method_value.resume1.out
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2/g_lo_radio_history_method_value.resume1.err
```

The PBS stop rule is active. No polling followed the running-state proof.
Wait for Barry's completion email before any completion check or retrieval.

## 2026-07-26: completed cache, lifecycle repair, and second resume

Status remains `submitted_waiting_pbs_completion`.

Barry reported that PBS `777005.kunanyi-ohpc` finished with `Exit_status=1`
after `00:23:15`. The final scheduler record also reports
`Stageout_status=1`, `cput=00:06:41`, `mem=523860kb`, and `ncpus=16`.
The stage-root stdout, stderr, per-job analysis log, cache diagnostic, and
reservation inventory were preserved with a passing checksum manifest at:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_batched_v2/remote_logs/attempt2_777005
```

The attempt supplied material new evidence rather than repeating the walltime
failure:

- the batched writer completed all `5001/5001` source outputs;
- the in-progress cache is intact at shape `197568 x 5001`, with
  `next_output=5001` and no pending-batch marker;
- the first workflow failure was
  `missing post-injection particle record: output=4152,
  particle_id=164943`; and
- packaging separately failed because Kunanyi's `tar` does not support
  `--sort=name`.

The particle record is an injection-time representation boundary, not lost
history. Its stored injection time is `12729.8486328125`; output `4152` is
absent at time `12729.84866867`; output `4153` is the first present record at
`12733.03595652`; and the particle then remains continuously present through
the endpoint. The output-4152 offset is `3.58575e-05`, below half a float32
ULP at the stored injection time (`4.8828125e-04`).

The shared lifecycle validator now requires one leading absence prefix followed
by one uninterrupted presence suffix. It accepts a preceding absence only
when the injection timestamp is bracketed within a representation-scale
tolerance that is also capped against output cadence. It still rejects early
presence, any internal presence gap, and material post-injection absence. Both
cache construction and downstream cache acceptance use this validator.

The archive wrapper now relies on the already sorted explicit file list and
omits the unsupported `tar --sort=name` flag. Deterministic file ordering,
content checksums, temporary-archive validation, atomic hard-link publication,
and overwrite refusal remain active. The existing per-PBS-job analysis-log
protection also remains active.

Focused local validation passed:

```text
33 tests passed in 6.74s
Python compilation passed
PBS wrapper bash -n passed
git diff --check passed
```

An independent post-repair review returned `GO`. It verified the shared
lifecycle contract, the exact particle-164943 boundary, rejection of material
absence/internal gaps/early presence, bounded-memory validation, and the
portable deterministic archive path. No broader methods audit was justified.

A third immutable stage was created without modifying either earlier stage:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3
```

Remote preflight passed the 82-file staged manifest, exact local/remote hashes,
wrapper syntax, Python compilation, cache shape/checkpoint and boundary smoke,
analysis ownership/non-symlink gates, attempt-2 evidence checksums,
archive/output collision gates, live Kunanyi tar smoke, scratch reserve, and
`normal` queue availability. The repaired runtime hashes are:

```text
g_lo_particle_history.py=755c3c61d1809c3a97abe361af822efd4bd9e66f12f29c0d34ef184cd93c2b89
run_g_lo_radio_history_value.py=ffb43270e9cb9587c8f6a7f93e208d7d8d63120023c4c6c801d3e915751c4a24
g_lo_radio_history_method_value.pbs=d6e6c235ff6a8e6d74296b907da5890af52480fa750903de72bf9090a958ff7d
```

Exactly one materially changed resume was submitted:

```text
job_id=777006.kunanyi-ohpc
Job_Name = g_lo_radhist
job_state = Q
queue = normal
qtime = Sun Jul 26 21:57:38 2026
Resource_List.select = 1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime = 48:00:00
```

Expected products:

```text
archive=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3/g_lo_radio_history_method_value_2026-07-24.tar.gz
stdout=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3/g_lo_radio_history_method_value.resume2.out
stderr=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_lifecycle_v3/g_lo_radio_history_method_value.resume2.err
```

The PBS stop rule is active. No polling followed queued verification. Wait for
Barry's completion email before any completion check or retrieval.

## 2026-07-26: raw-pressure failure and diagnostic submission

Status: `submitted_waiting_pressure_diagnostic`.

Barry reported PBS `777006.kunanyi-ohpc` / `g_lo_radhist` finished with
`Exit_status=2` after `00:08:16`. Final scheduler evidence also records
`Stageout_status=1`, `cput=00:04:33`, `mem=343588kb`, and `ncpus=16`.
The stage stdout, empty stderr, per-job run log, and readable compact archive
were retrieved and checksum-preserved locally.

The lifecycle repair remained green. The final cache was atomically promoted
to `g_lo_history.h5`, has shape `197568 x 5001`, `next_output=5001`, no
pending batch marker, and size `33191119360` bytes. The new first failure was
inside the first emissivity chunk:

```text
ValueError: pressure history must be positive after injection
```

The adapter checks raw converted pressure before smoothing. Source inspection
found that new PRAiSE particles are initialized with zero pressure, density,
and tracer before later fluid interpolation, while output can occur before the
next integration update. The five relevant Kunanyi source-tree file hashes
matched their reviewed local counterparts exactly. This supports an
injection-initialization hypothesis but does not by itself establish the
cache-wide pattern or authorize a pressure floor.

A read-only, chunk-vectorized diagnostic was implemented and validated. It
distinguishes leading-zero-only prefixes, internal non-positive values,
no-positive histories, and non-positive endpoints; reports per-output counts;
and cross-checks a bounded representative sample against initial `0000..0999`
and guarded `1000..5000` raw files using the accepted canonical rule.

Validation passed:

```text
38 focused tests passed
Python compilation passed
PBS wrapper bash -n passed
git diff --check passed
remote staged SHA-256 and cache/schema preflight passed
```

Exactly one small diagnostic PBS job was submitted:

```text
job_id=777007.kunanyi-ohpc
Job_Name=g_lo_prdiag
state=R
queue=normal
qtime=Sun Jul 26 22:32:27 2026
resources=1 CPU, 32 GB, 02:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_history_diagnostic_777006
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-26-g-lo-pressure-history-diagnostic-777006
```

No science retry, pressure repair, cache mutation, raw deletion, commit, or
push occurred. The PBS stop rule is active; wait for Barry's completion email.

## 2026-07-26: pressure diagnostic green and repaired science resume

Status: `submitted_waiting_pressure_repaired_science_completion`.

Barry reported that diagnostic PBS `777007.kunanyi-ohpc` / `g_lo_prdiag`
finished with `Exit_status=0` after `00:01:35`. Final evidence records one CPU,
`cput=00:01:22`, `mem=772672kb`, and zero-byte stderr. The retrieved diagnostic
scanned the complete `197568 x 5001` cache and found:

```text
total_present_records=502174540
finite_positive_records=502164508
exact_zero_records=10032
negative_records=0
nonfinite_records=0
leading_zero_only_rows=10030
internal_nonpositive_rows=0
no_positive_rows=2
nonpositive_endpoint_rows=2
lifecycle_violation_rows=0
representative_source_matches=32/32
```

Observation and inference remain separated. The observed non-positive surface
is entirely exact zero. The `10,030` eligible histories each have one leading
joint pressure-density-tracer zero followed by positive pressure. This pattern
is consistent with the reviewed injection initialization, but that mechanism
is an inference. The two endpoint-injected histories have one joint-zero
record and no positive state, so they cannot support a PRAiSE estimate.

The approved primary treatment removes only the initialization sample from the
`10,030` eligible histories, preserves their original injection timestamps,
and excludes the two no-positive histories. A conservative comparator excludes
all `10,032` affected histories. No pressure floor or interpolation is used.
Both treatments are compared for luminosity, spectral index, normalized maps,
support, topology, and decision-label stability at `150 MHz` and `1.4 GHz`
across `0/45/90 deg`. Decision instability keeps the method blocked.

The resumed science wrapper now reruns the diagnostic before PRAiSE and fails
closed unless:

- the exact cache-wide count and lifecycle topology above is reproduced;
- exactly two exceptional histories remain;
- both are exact joint zeros at output `5000`;
- both match their canonical raw source records for pressure, density, and
  tracer; and
- neither has an injection time after first presence.

Focused local validation passed:

```text
54 tests passed in 6.36s
Python compilation passed
both PBS wrappers passed bash -n
git diff --check passed
```

A fourth immutable stage was created:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v4
```

Remote preflight passed its `112`-entry staged manifest, exact local/remote
hashes, wrapper syntax, Python compilation, completed-cache shape/checkpoint,
owner/method-gate evidence, and archive/reservation no-overwrite gates. The
key hashes are:

```text
g_lo_radio_history_method_value.pbs=5a23ca65c103f3675f4fe578b25b003dc7fa3a4964de00bb5bd7b11147854b69
g_lo_particle_history.py=755c3c61d1809c3a97abe361af822efd4bd9e66f12f29c0d34ef184cd93c2b89
g_lo_radio_method_value.py=4d572ab404cc41d555b18d9891c47ce705a22a320d4f4e8f64c54eb5aaad81c8
run_g_lo_radio_history_value.py=cbf5c25d0e3b8edfb1499ef0c6770ff37c8a5fc78dc91189a2343f914650bbfe
diagnose_g_lo_pressure_history.py=8e7bedf0d58aaaf7705029def8b3ac48cf745d2b699eee617ff39186f436ebf8
```

Exactly one materially changed science resume was submitted:

```text
job_id=777008.kunanyi-ohpc
Job_Name=g_lo_radhist
job_state=Q
queue=normal
qtime=Sun Jul 26 23:07:46 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime=48:00:00
```

Expected completion products:

```text
archive=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v4/g_lo_radio_history_method_value_2026-07-24.tar.gz
stdout=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v4/g_lo_radio_history_method_value.pressure3.out
stderr=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v4/g_lo_radio_history_method_value.pressure3.err
```

No history rebuild, cache mutation, raw deletion, new PLUTO production,
C-HI/C-LO regeneration, commit, or push occurred. The PBS stop rule is active;
wait for Barry's completion email before any status check or retrieval.

## 2026-07-26: attempt-4 launch-manifest failure and hardened resume

Status:
`submitted_waiting_manifest_hardened_pressure_repaired_science_completion`.

Barry reported PBS `777008.kunanyi-ohpc` / `g_lo_radhist` finished with
`Exit_status=1`, `cput=00:00:00`, `mem=0kb`, and `walltime=00:00:00`.
Retrieved stdout, stderr, and the staged manifest identified the first and only
failure:

```text
scripts/kunanyi/python_compat/__pycache__/hdf5plugin.cpython-311.pyc: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

The v4 stage manifest had accidentally included generated Python bytecode.
Remote preflight created the manifest and then ran `py_compile`, legitimately
changing that `.pyc` before the queued job's initial checksum check. The
wrapper stopped before the embedded pressure diagnostic, raw-source checks,
PRAiSE, raytracing, history mutation, or science-output generation.

The wrapper was hardened to reject any staged manifest containing
`/__pycache__/`, `.pyc`, or `.pyo`. A clean v5 stage was copied without
generated bytecode, the patched wrapper was overlaid, and the remote preflight
order was verified explicitly:

```text
manifest_entries=83
manifest_bytecode_entries=0
Python compilation passed
post_compile_manifest_check=passed
completed_cache_shape=197568x5001
completed_cache_next_output=5001
```

Focused local validation passed:

```text
54 tests passed in 7.20s
Python compilation passed
both PBS wrappers passed bash -n
shellcheck passed
git diff --check passed
```

Exactly one manifest-hardened replacement was submitted:

```text
job_id=777009.kunanyi-ohpc
Job_Name=g_lo_radhist
job_state=Q
queue=normal
qtime=Sun Jul 26 23:18:27 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime=48:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v5
```

The wrapper SHA-256 is
`c3f9fd998e87a0d7c9b097908f2f8a89488226815f49b0c2a5d3feac22c64bd9`.
No polling followed queued verification. Wait for Barry's completion email for
`777009.kunanyi-ohpc`.

## 2026-07-26: attempt-5 endpoint-category failure and repaired resume

Status: `submitted_waiting_endpoint_no_positive_repaired_science_completion`.

Barry reported PBS `777009.kunanyi-ohpc` / `g_lo_radhist` finished with
`Exit_status=2` after `00:07:52`, `cput=00:06:14`, and `mem=725600kb`.
The bytecode-free manifest passed, the embedded cache-wide pressure diagnostic
reproduced its approved counts, and stderr was empty. The first treatment
planner failure was:

```text
PressureTreatmentError: pressure-treatment trim reaches beyond the endpoint
```

The compact archive and exact exceptional-row export show that both
endpoint-injected exceptions have one present record at output `5000`, joint
zero pressure/density/tracer, and no positive pressure record. The old trim
predicate overlapped the no-positive predicate for a one-record zero history
because `0 == 1 - 1`; it then attempted to advance past the final cache column.
No PRAiSE or raytracing ran.

An exact regression fixture was added first. It reproduced the remote failure,
then passed after trim eligibility was constrained to histories with at least
one later positive record. Treatment categories are also checked to sum to
exactly one of trim, no-positive, or unchanged. The no-positive histories
remain excluded; no floor or interpolation was introduced.

Verification:

```text
red regression: failed with "pressure-treatment trim reaches beyond the endpoint"
green regression: 1 passed
focused suite: 55 passed in 6.56s
remote runner SHA-256 matched local:
fe86c6ff44fa0e137eaeaa70f7f4664e3177f3e84ae8f0977823c820eecc2b2c
v6 manifest entries=83
v6 manifest bytecode entries=0
post-compile manifest check=passed
completed cache shape=197568x5001; next_output=5001
```

Independent review returned GO. It confirmed the predicates are mutually
exclusive and that internal/multiple zeros, non-joint zeros, lifecycle
violations, and aggregate mismatches remain fail-closed.

Exactly one replacement was submitted:

```text
job_id=777011.kunanyi-ohpc
Job_Name=g_lo_radhist
job_state=R
queue=normal
qtime=Sun Jul 26 23:37:44 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=128gb
Resource_List.walltime=48:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v6
```

No polling followed running-state verification. Wait for Barry's completion
email for `777011.kunanyi-ohpc`.

## 2026-07-27: attempt-6 linear smoothing failure and diagnostic submission

Status: `submitted_waiting_pressure_smoothing_diagnostic_completion`.

Barry reported PBS `777011.kunanyi-ohpc` / `g_lo_radhist` finished with
`Exit_status=2`, `walltime=00:08:14`, `cput=00:06:56`, and `mem=776964kb`.
The immutable manifest, runtime import, cache-wide pressure diagnostic, and
repaired pressure-treatment plan all passed. Stderr was empty. The first new
failure was:

```text
ValueError: smoothed pressure history must be positive after injection
```

The readable compact archive records `197566` active rows, `10030` trimmed
leading-initialization rows, and two excluded no-positive histories. The raw
treated pressure was positive before the current five-point linear
Savitzky-Golay operation. No PRAiSE emissivity chunk or raytrace completed.

The diagnostic conclusion is an observed linear-filter overshoot. The
provisional scientific recommendation is unsmoothed pressure as primary,
matching the pinned upstream default, with log-pressure Savitzky-Golay as the
required sensitivity. Clipping, flooring, excluding overshoot rows, and an
unchanged linear-smoothing retry are rejected.

A local read-only smoothing diagnostic was implemented with bounded row
chunks. It compares unsmoothed, linear Savitzky-Golay, log-pressure
Savitzky-Golay, and triangular positive-kernel treatments. Its outputs contain
invalid counts, exact affected rows and stencils, pressure ratios and endpoint
changes, and bounded `a_p = log(p[t+1]/p[t]) / dt` summaries.

Validation and remote preflight:

```text
focused tests=41 passed
Python compilation=passed
wrapper bash -n and shellcheck=passed
git diff --check=passed
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
job_state=Q
queue=normal
qtime=Mon Jul 27 14:18:49 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=64gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_smoothing_diagnostic_777011
```

No science retry, cache mutation, history rebuild, PRAiSE call, raytrace,
PLUTO production, raw deletion, commit, or push occurred. The PBS stop rule is
active; wait for Barry's completion email for `777065.kunanyi-ohpc`.

## 2026-07-27: smoothing diagnostic complete; archive-only failure

Status: `actual_praise_pressure_method_sensitivity_required`.

Barry reported PBS `777065.kunanyi-ohpc` / `g_lo_psdiag` finished with
`Exit_status=1`, `walltime=00:13:51`, `cput=00:11:43`, and `mem=2149400kb`.
The immutable manifest, runtime imports, full-cache calculation, and diagnostic
validation all passed. The job produced `99,108` affected-row records and
reported:

```text
status=diagnostic_complete
active_rows=197566 smoothed_rows=197398
affected_rows=99108
smoothing_diagnostic_validation=passed
```

The nonzero scheduler exit came after those outputs, when `tar` archived the
live analysis directory:

```text
tar: 2026-07-27-g-lo-pressure-smoothing-diagnostic-777011: file changed as we read it
```

The completed JSON and CSV were retrieved directly. Their local hashes match
the remote SHA-256 values. Linear Savitzky-Golay creates `216,035`
non-positive transformed records across `99,108 / 197,398` smoothed histories.
Log Savitzky-Golay and a triangular comparator preserve positivity, but log
smoothing changes endpoint pressure by `-83.42%` to `+25.40%`; numerical
admissibility is not scientific equivalence.

Decision:

- block linear-domain Savitzky-Golay permanently for this workflow;
- retain no-floor/no-clipping/no-censoring rules;
- implement explicit `unsmoothed` and `log_savgol` modes;
- run a deterministic stratified actual-PRAiSE comparison before another full
  Goal 049 science retry; and
- require aggregate method differences no larger than `0.10 dex`, spectral
  index difference no larger than `0.10`, stable full/lossless decision
  direction, and no extreme-subset dominance.

The diagnostic wrapper now archives a stable two-file payload through an
explicit file list; focused wrapper validation reports `4 passed`, `bash -n`,
`shellcheck`, and `git diff --check` green. No diagnostic rerun, cache mutation,
PRAiSE execution, raytrace, PLUTO run, raw deletion, commit, or push occurred.

## 2026-07-27: actual-PRAiSE pressure-method diagnostic submitted

Status: `submitted_waiting_actual_praise_pressure_method_value_completion`.

The next method gate was implemented without reopening the full Goal 049
science workflow. The actual upstream PRAiSE function is evaluated under two
explicit pressure modes only:

- primary candidate: `unsmoothed`, the upstream default; and
- sensitivity comparator: five-point, third-order Savitzky-Golay in natural
  log-pressure space.

Linear-domain smoothing is unavailable. Clipping, flooring, and censoring
remain forbidden.

The deterministic sample contains `4096` active histories and combines all
short histories, mandatory log-SG extrema selected across the full active
cache, and stratified rows. Analysis weights calibrate represented population
counts. The top-`1%` dominance metric ranks per-particle absolute method
discrepancy and integrates exactly `1%` of represented population mass,
including a fractional boundary row.

Local verification:

```text
focused root suite=59 passed
targeted independent repair review=GO; 12 passed
Python compilation=passed
wrapper bash -n and shellcheck=passed
git diff --check=passed
diagnostic_sha256=36bb3cf248b194f402ebb9373564cfa89e8d9bb916cbd3f72a1aca795bb4ed40
wrapper_sha256=bfa1da85eee1b0fc2fbdd46606567352cbaf22fef13f036c256f9aa15aa4e464
```

The remote stage reused the pinned `plutokore` and Python compatibility
runtime from the clean v6 stage, copied the immutable affected-row evidence
from the completed smoothing diagnostic, and removed generated bytecode
before manifest construction. Remote preflight passed:

```text
manifest_entries=120
manifest_bytecode_entries=0
runtime_import_preflight=passed
cache_metadata_preflight=passed shape=197568x5001 next_output=5001
normal queue enabled=True started=True max_walltime=48:00:00
analysis/archive/payload no-overwrite gates=passed
```

Exactly one compact actual-PRAiSE diagnostic was submitted:

```text
job_id=777074.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=Q
queue=normal
qtime=Mon Jul 27 15:06:53 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-pressure-method-value-diagnostic
```

The stable archive payload includes the four compact diagnostic outputs and
`staged_inputs.sha256`. No full science retry, raytrace, cache mutation,
history rebuild, PLUTO run, raw deletion, commit, or push occurred. The PBS
stop rule is active; wait for Barry's completion email for
`777074.kunanyi-ohpc`.

## 2026-07-27: non-finite PRAiSE result and forensic replay submitted

Status: `submitted_waiting_praise_nonfinite_forensic_completion`.

Barry reported PBS `777074.kunanyi-ohpc` / `g_lo_pmvalue` finished with
`Exit_status=2` after `01:01:06`. The final scheduler record reports
`Stageout_status=1`, `cput=22:21:14`, `mem=2957540kb`, and `ncpus=16`.
The immutable manifest and runtime import gate passed; stderr is empty. The
first and only failure is:

```text
ValueError: PRAiSE returned non-finite endpoint emissivities
```

No diagnostic result table was written. The old adapter checked finiteness
only after all injection groups for the current pressure mode had returned,
so the failed pressure mode, loss branch, frequency, cache row, and particle
ID cannot be recovered from that attempt.

Pinned upstream PRAiSE explicitly uses a NaN injection Lorentz factor for its
`no_emission` branch, and its example notebook broadly maps non-finite
emissivity to zero. That broad conversion is not adopted here: an unassigned
shock state and genuine `a_p`, `a_2`, Lorentz-factor, or fractional-power
failures can also be non-finite.

The focused repair adds an opt-in diagnostic replay of the exact pinned
PRAiSE internal functions. It leaves every emissivity unchanged and classifies
an endpoint only as `proven_full_loss_cutoff` when the output is NaN, the
matched lossless cell is finite, the replay exactly matches returned
diagnostics, inputs and dynamics are finite, the shock index is visited by the
backward loop, and the explicit no-emission mask is true. Lossless
non-finites, infinities, unassigned shocks, replay mismatches, and other
non-finites remain blocked.

Local verification passed:

```text
32 focused tests passed
Python compilation passed
PBS wrapper bash -n passed
git diff --check passed
```

A fresh stage passed a `121`-entry bytecode-free manifest, exact changed-file
hashes, wrapper syntax, runtime imports, immutable cache and affected-row
hashes, and no-overwrite gates. Exactly one forensic job was submitted:

```text
job_id=777213.kunanyi-ohpc
Job_Name=g_lo_pnf
job_state=Q
queue=normal
qtime=Mon Jul 27 17:11:21 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_praise_nonfinite_forensic
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-praise-nonfinite-forensic
```

The job writes the deterministic selection before PRAiSE, checkpoints each
pressure mode separately, and accepts a completed blocked diagnosis as valid
evidence. It does not zero, clip, censor, drop, or substitute emissivity.
No full Goal 049 science retry or raytrace is authorized. The PBS stop rule is
active; wait for Barry's completion email for `777213.kunanyi-ohpc`.

## 2026-07-27: forensic completion, singleton repair, and method gate resume

Status: `submitted_waiting_singleton_repair_method_value_completion`.

PBS `777213.kunanyi-ohpc` / `g_lo_pnf` completed with `Exit_status=0`,
`walltime=03:34:28`, `cput=88:45:02`, `mem=3469436kb`, and empty stderr. The
stage-root archive was retrieved despite the scheduler's retained
`Stageout_status=1` caveat. Its SHA-256 is
`03f94d5df0c70ddb7f0d1070186ca0f3df9946e00cf9df40debfc0bdf81564be`.

The forensic result is deterministic: `384 / 32768` cells are non-finite, all
from the same `48` physical IDs. Every affected history has effective length
one and begins at output `5000`. Both pressure modes and both loss branches
show the same pattern. Inputs and replay dynamics are finite, replay is exact,
and the optimized zero-interval path leaves injection gamma unassigned.

The repaired adapter defaults to fail-closed and exposes an explicit
`instantaneous_recent_shock` policy only for exact, finite, valid singleton
histories. It uses endpoint pressure and current gamma as the injection state,
requires full-loss and lossless equality, persists a distinct singleton mask
and provenance, and requires exactly `48` real-cache singleton rows.
Singleton exclusion remains a conservative comparator rather than the primary
method.

Focused local verification passed `75` tests, four PBS syntax checks, and
`git diff --check`. The fresh remote stage passed exact changed-file hashes,
cache and affected-row hashes, wrapper syntax, and immutable manifest checks.
Exactly one repaired method-value diagnostic was submitted and verified
running:

```text
job_id=778078.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Mon Jul 27 22:06:40 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_singleton_v2
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-pressure-method-value-diagnostic-singleton-v2
```

The PBS stop rule is active. No full raytrace, history rebuild, cache mutation,
PLUTO run, commit, push, or cleanup occurred.

## 2026-07-27: effective-singleton overlap repair and diagnostic resubmission

Status: `submitted_waiting_effective_singleton_method_value_completion`.

Barry reported PBS `778078.kunanyi-ohpc` / `g_lo_pmvalue` finished with
`Exit_status=2`, `walltime=00:04:25`, `cput=00:03:57`, `mem=411424kb`, and
empty stderr. The first failure was the planner aggregate
`single_record=46 expected=48`; PRAiSE did not run.

The forensic evidence gives an exact cross-tab: `46` untrimmed singleton
histories plus two trim-affected histories that become singleton after the
approved leading-zero trim. The planner incorrectly used an exclusive enum as
the source of singleton provenance.

The repaired version-3 treatment contract makes effective singleton status
orthogonal to trim status. It fails closed on `10030` trim rows, `2`
no-positive rows, `48` effective singleton rows, and a `2`-row overlap. The
mask and effective record counts are hashed; per-row provenance carries both
labels; PRAiSE singleton IDs must exactly match the plan; and the conservative
support excludes the union of trim and singleton histories.

Two independent audits supported the method and implementation. Local
validation passed `76` focused tests, four wrapper syntax checks, and
`git diff --check`. Remote preflight passed:

```text
manifest_entries=120
manifest_bytecode_entries=0
cache_sha256=passed
affected_rows_sha256=passed
wrapper_syntax=passed
analysis/archive/payload no-overwrite gates=passed
```

Exactly one replacement diagnostic was submitted:

```text
job_id=778079.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=Q
queue=normal
qtime=Mon Jul 27 22:51:39 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_effective_singleton_v3
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-pressure-method-value-diagnostic-effective-singleton-v3
```

The PBS stop rule is active. No full raytrace, cache rebuild, PLUTO run,
commit, push, or cleanup occurred.

## 2026-07-28: branch-semantics failure and diagnostic repair

Barry reported PBS `778079.kunanyi-ohpc` / `g_lo_pmvalue` finished with
`Exit_status=2` after `01:54:04`. The immutable input manifest and runtime
preflight passed, stderr is empty, and the actual unsmoothed PRAiSE computation
reached the project-added comparison gate. The first failure was:

```text
PressureMethodDiagnosticError: unsmoothed full-loss emissivity exceeds matched lossless emissivity
```

Independent code and method audits found that this assertion is not a pinned
PRAiSE invariant. `losses="none"` disables both pressure-work and radiative
evolution, whereas `losses="full"` includes both. Adiabatic compression can
therefore make full-evolution emissivity exceed the no-evolution branch. The
failure is a diagnostic-policy defect, not evidence by itself of corrupt
alignment or invalid physics.

The repaired diagnostic:

- retains full-versus-none ordering as descriptive evidence;
- computes a matched `losses="adiabatic"` branch and uses full-versus-adiabatic
  as the radiative-suppression gate;
- uses reference-relative plus per-cell ULP ordering tolerances;
- checkpoints full/adiabatic/none arrays immediately after each expensive
  pressure-mode calculation;
- replays and counts pinned PRAiSE's silent intermediate-gamma fallback and
  fails closed if any selected non-singleton cell uses it; and
- archives all compact evidence before returning nonzero on a failed
  scientific gate.

The `778079` compact stdout/stderr and failure summary are preserved under
`pressure_method_effective_singleton_v3_778079/`. No full raytrace, history
rebuild, cache mutation, PLUTO run, commit, push, or raw cleanup occurred.

Local verification passed:

```text
Goal 049 focused suite: 98 passed in 5.95s
Python compilation: passed
four PBS wrapper syntax checks: passed
method wrapper shellcheck: passed
git diff --check: passed
```

The fresh remote stage passed exact local/remote hashes, a `120`-entry
bytecode-free manifest, remote wrapper syntax, immutable cache and affected-row
hashes, runtime imports, no-overwrite gates, and the enabled `normal` queue.
Exactly one replacement diagnostic was submitted:

```text
job_id=778919.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Tue Jul 28 09:35:49 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_branch_semantics_v4
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-pressure-method-value-diagnostic-branch-semantics-v4
```

The PBS stop rule is active. No remote command followed the running-state
proof. Wait for Barry's completion email before retrieval or any full
raytrace.

## 2026-07-28: v4 non-finite failure and archive-first evidence submission

Status: `submitted_waiting_nonfinite_branch_evidence_completion`.

Barry reported PBS `778919.kunanyi-ohpc` / `g_lo_pmvalue` finished with
`Exit_status=2`, `walltime=01:27:35`, `cput=33:43:30`,
`mem=3286924kb`, and empty stderr. Final `qstat -x` confirmed
`job_state=F` and retained `Stageout_status=1`.

The stage and immutable-input gates passed. The deterministic selection has
`4096` rows and SHA-256
`35072ea875621015da4454de8ce01d2e5ac957f3ab1984cc6243ad8d954707df`,
identical to the preceding forensic selection. No emissivity checkpoint or
archive was written. The first failure was:

```text
ValueError: PRAiSE returned non-finite endpoint emissivities
```

The v4 guard did not identify the affected pressure mode, loss branch,
frequency, particle, or non-finite class. A newly added adiabatic branch is
the leading hypothesis, but remains explicitly inference-only.

The repaired v5 path checkpoints full/adiabatic/none results, preserves
NaN/+Inf/-Inf exactly, writes per-cell branch-aware forensic records, and
reconciles them against the raw checkpoints. Gamma/dynamics replay exceptions
become archived audit failures. Any non-finite, audit error, or
record/checkpoint mismatch suppresses finite-only comparison and returns a
deliberate scientific failure only after evidence packaging.

Independent final review returned `GO`. Local verification passed:

```text
107 focused tests passed in 6.11s
Python compilation passed
wrapper bash -n passed
wrapper shellcheck passed
git diff --check passed
```

The final local/remote changed-file hashes are:

```text
diagnostic=3ecdf589d9bc4a18d24219788c6b4a4e4002618ba1b2b2ec30dc76bee216d1dc
adapter=b029fb0fb5ec1024d8948b60dc9209bd03c5b86976725a17b8c99dea0e04ba4c
wrapper=967d0e280ba84824f7b5424f4ac2c62eb730c4f85192776046fb7272998a9d97
```

Remote preflight also passed the `120`-entry bytecode-free manifest, immutable
cache and affected-row hashes, runtime imports, wrapper syntax, no-overwrite
gates, and normal-queue gate. Exactly one diagnostic was submitted:

```text
job_id=779183.kunanyi-ohpc
Job_Name=g_lo_pmvalue
job_state=R
queue=normal
qtime=Tue Jul 28 11:39:59 2026
Resource_List.select=1:ncpus=16:mpiprocs=1:mem=96gb
Resource_List.walltime=12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic_nonfinite_evidence_v5
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-pressure-method-value-diagnostic-nonfinite-evidence-v5
```

The PBS stop rule was invoked immediately after running-state verification.
No polling, full raytrace, cache mutation, history rebuild, PLUTO run, raw
cleanup, commit, or push followed.

## 2026-07-28: v5 adiabatic failure diagnosis and recovery gate

Status: `submitted_waiting_adiabatic_recovery_completion`.

Barry reported PBS `779183.kunanyi-ohpc` / `g_lo_pmvalue` finished with
`Exit_status=3` after `05:14:34`. Final scheduler evidence retained
`job_state=F` and `Stageout_status=1`; the requested archive, stdout, and
stderr were present and retrieved. The archive SHA-256 is
`c7c9d0a2001d3c23749483e42894593c28396e70b7ad5b29a224cdc0556e83f8`.

This is a deliberate archived scientific failure, not an infrastructure
failure. The v5 product records `9,103` non-finite cells, all NaN and all in
the adiabatic branch: `4,643` under unsmoothed pressure and `4,460` under
log-Savitzky-Golay pressure. Full and no-loss branches are finite. All
non-finite records are replay-verified, have finite dynamics inputs and valid
shock assignment, and retain the pinned no-emission state with NaN injection
gamma. No NaN was converted to zero or excluded.

Independent diagnosis found that pinned PRAiSE evaluates separate
absolute-time powers in the adiabatic recurrence. The numerically stable
pressure-ratio/log-difference form is algebraically equivalent on
strictly-positive-time intervals. A compact recovery gate now compares that
form against an 80-digit original time-ratio reference over relevant
endpoint-to-shock intervals, preserves pre-shock anomalies as evidence, and
reconstructs injection gamma and emissivity without changing pinned defaults.

A Sol Max audit required one final fail-closed repair: every selected archived
unsmoothed/log-Savitzky-Golay by `0.15/1.4 GHz` failure stratum must reproduce
as non-finite under the pinned original adiabatic branch before the stable
recovery can pass. That gate is implemented. Local verification passed:

```text
48 focused tests passed in 6.00s
Python compilation passed
PBS wrapper bash -n passed
git diff --check passed
```

Remote staging passed exact script, wrapper, cache, `4096`-row selection,
`9,103`-record evidence, pinned source commit, bytecode-free manifest, runtime
import, syntax, no-overwrite, and queue gates. Exactly one compact diagnostic
was submitted:

```text
job_id=779684.kunanyi-ohpc
Job_Name=g_lo_adrec
job_state=Q
queue=normal
qtime=Tue Jul 28 20:10:11 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=32gb
Resource_List.walltime=02:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_adiabatic_recovery
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-adiabatic-recovery-diagnostic
```

The PBS stop rule is active. No remote command followed queued verification,
and no full `4096` comparison, raytrace, history rebuild, cache mutation,
PLUTO run, raw cleanup, commit, or push occurred.

## 2026-07-28: duplicate recovery completion, index repair, and guarded retry

Status: `submitted_waiting_adiabatic_recovery_index_repair_v2_completion`.

Barry reported two completed jobs:

```text
779684.kunanyi-ohpc  g_lo_adrec  Exit_status=2  walltime=00:02:38
779685.kunanyi-ohpc  g_lo_adrec  Exit_status=2  walltime=00:07:27
```

Final scheduler JSON proves both jobs had the same queue and start time
(`Tue Jul 28 20:10:11 2026`), stage-root stdout/stderr paths, job name, queue,
and resource request. Local submission records documented only `779684`, while
the shared remote `qsub_jobid.txt` contained `779685`. This is classified as a
duplicate concurrent submission with unresolved launch cause, not as two
independent scientific attempts.

The shared fixed paths prevent clean job-by-job attribution. The surviving
stdout, stderr, and archive all have the later `779685` completion timestamp.
They are preserved under:

```text
docs/science/assets/g_lo_radio_history_method_value_gate_failure_2026-07-26/
  adiabatic_recovery_shared_stage_snapshot_after_779684_779685/
```

The surviving traceback is an infrastructure defect before the recovery gate:

```text
TypeError: Indexing elements must be in increasing order
```

The deterministic trace selection is intentionally not sorted by cache row.
The inherited HDF5 sample reader therefore passed non-monotonic indices to
`h5py`. The repair reads sorted unique cache rows and restores the exact
requested order for every row-aligned field. It changes neither selected rows
nor scientific defaults. Regression coverage includes unsorted and repeated
requested indices, while the scientific selection contract continues to reject
duplicate selected cache rows.

The PBS wrapper now claims an atomic stage-run lock. The new submission path
also uses a persistent atomic `qsub_once.lock`, so repeating the submission
command cannot launch a second job. Local verification passed:

```text
50 focused tests passed in 6.52s
Python compilation passed
PBS wrapper bash -n passed
PBS wrapper shellcheck passed
git diff --check passed
```

The fresh remote stage passed exact script, wrapper, cache, selection,
non-finite-record, and pinned-source hashes; a `123`-entry bytecode-free
manifest; runtime import; wrapper syntax; and no-overwrite checks. Exactly one
replacement diagnostic was submitted:

```text
job_id=779693.kunanyi-ohpc
Job_Name=g_lo_adrec
job_state=R
queue=normal
qtime=Tue Jul 28 20:42:31 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=32gb
Resource_List.walltime=02:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_adiabatic_recovery_index_repair_v2
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-28-g-lo-adiabatic-recovery-index-repair-v2
```

The PBS stop rule is active. No remote command followed running-state
verification. No full comparison, raytrace, history rebuild, cache mutation,
PLUTO run, raw cleanup, commit, or push occurred.

## 2026-07-28: repaired recovery completion and full-loss method block

Status: `complete_adiabatic_recovery_full_loss_method_blocked`.

PBS `779693.kunanyi-ohpc` finished with deliberate scientific
`Exit_status=3`, `walltime=00:41:46`, and `cput=03:57:33`. The requested
archive, stdout, stderr, and compact summary were present and retrieved. The
archive SHA-256 is
`71f40e9510834acbc4475bfa59b4e22faddbba0a32dd343dcdef3b81956cf3f8`.

The index repair and recovery core passed:

- all `4 / 4` archived pressure-mode/frequency failure strata reproduced;
- all `431,744` retained stable gamma values were finite and positive;
- all `98` grouped comparisons with the 80-digit reference passed, with
  maximum relative difference `9.994967978657982e-12`; and
- stable reconstructed injection emissivity was finite.

The remote summary's `stable_endpoint_trajectory=false` field was a reporting
defect. Its implementation combined stable-trajectory validity with
full-loss fallback and upstream-comparison state. The local code now reports
the adiabatic recovery verdict separately, records the `32` marginal
pressure/time-form discrepancies as a diagnostic, and renames the old
"well-conditioned" upstream check to the finite-overlap check it actually
performed. Focused verification passes `17` tests plus Python compilation,
wrapper syntax, and `git diff --check`. No remote rerun was made for this
bookkeeping correction.

The overall full-loss method remains blocked. On the same retained panel,
full-loss `a2` is non-finite in `22,737 / 215,872` relevant intervals. Pinned
PRAiSE consequently makes `45,474` NaN gamma updates and silently retains the
previous gamma. These are genuine full-loss integration failures, not
adiabatic-recovery failures.

Decision label:
`ADIABATIC_RECOVERY_SUPPORTED_FULL_LOSS_METHOD_BLOCKED_A2`.

The immutable archive retains the large trace and forensic tables. Their
redundant extracted local copies were removed after the compact closeout
tables were created, reducing the retained local package from about `114 MB`
to about `16 MB`.

No full `4096`-row comparison, raytrace, history rebuild, cache mutation,
PLUTO run, raw cleanup, commit, push, or external reviewer escalation
occurred. The recommended next goal is a stable full-loss `a2` and gamma
recurrence design plus independent high-precision gate on the existing
bounded panel.
