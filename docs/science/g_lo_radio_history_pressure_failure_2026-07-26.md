# G-LO radio-history pressure failure

## Status

Status: `complete_adiabatic_recovery_full_loss_method_blocked`.

The complete retained history cache has passed lifecycle, pressure-topology,
and source-lineage gates. Subsequent diagnostics blocked linear pressure
smoothing and isolated the remaining PRAiSE non-finite result to exactly `48`
one-record endpoint histories. PBS `777213.kunanyi-ohpc` completed that
forensic replay with `Exit_status=0`.

The optimized PRAiSE path leaves injection gamma unassigned when the backward
history loop has zero intervals. A narrowly gated instantaneous recent-shock
convention is now implemented and locally tested. PBS
`778078.kunanyi-ohpc` exposed one provenance bug before PRAiSE: `46`
untrimmed singleton histories plus `2` histories that become singleton only
after the approved trim had been represented as mutually exclusive classes.
That overlap and the later branch-semantics diagnostic policy are repaired.
PBS `778919.kunanyi-ohpc` then exposed a non-finite actual-PRAiSE result.
Archive-first PBS `779183.kunanyi-ohpc` identified exactly `9,103` NaNs, all
and only in the adiabatic branch, while full and no-loss branches remained
finite. A compact numerical-recovery diagnostic is now queued as PBS
`779684.kunanyi-ohpc`. No full `4096`-row comparison or raytrace is authorized
until that diagnostic is reviewed.

## Preserved evidence

The stage stdout, empty stderr, per-job analysis log, and readable compact
archive are retained under:

```text
docs/science/assets/g_lo_radio_history_method_value_gate_failure_2026-07-26/remote_logs/attempt3_777006/
```

The archive contains the completed cache and source manifests, method-gate
tables, both preceding attempt logs, and the explicit blocked decision. It
contains no emissivity product. The final cache now exists remotely as
`g_lo_history.h5`, with shape `197568 x 5001`, `next_output=5001`, no pending
batch marker, and size `33191119360` bytes.

## Mechanism and uncertainty

The checked particle-injection source initializes new PRAiSE particles with
zero pressure, density, and tracer before later fluid interpolation. Output can
occur between injection and the next update. The corresponding files in the
Kunanyi source tree have the same SHA-256 values as the local reviewed files.

That observation makes an exact-zero leading initialization record the leading
explanation. It does not yet prove that every offending cache value has that
origin, nor does the source-file match alone prove the compiled executable
lineage. Negative pressure, a zero after the first positive record, or a
non-positive endpoint remains method-blocking.

## Diagnostic result

The cache-wide scan classified `502,174,540` present records:

| Class | Records |
| --- | ---: |
| finite positive | `502,164,508` |
| exact zero | `10,032` |
| negative | `0` |
| non-finite | `0` |

The zeros have a sharply constrained topology:

- `10,030` histories contain exactly one leading zero before a continuous
  positive-pressure suffix;
- no history contains a non-positive value after its first positive value;
- two endpoint-injected histories contain one zero record and no positive
  record;
- the lifecycle validator reports no violations; and
- all `32/32` bounded representative source checks match the canonical raw
  particle record exactly.

These are observations. The interpretation that the `10,030` leading joint
pressure-density-tracer zeros are initialization samples is an inference,
supported by their position and the reviewed injection source. The two
no-positive histories have no defensible PRAiSE pressure history.

## Repair and sensitivity contract

The primary treatment preserves each particle's original injection time,
turns only the single joint-zero initialization sample into pre-history, and
uses the later positive suffix. The two no-positive histories are excluded
from emissivity and raytracing. No pressure floor or interpolation is used.

A conservative comparator excludes all `10,032` affected histories. The
primary and conservative treatments are compared at both frequencies and all
three views for:

- full-loss and lossless luminosity and spectral index;
- normalized map difference and peak change;
- support area, extent, overlap, and connected-component topology; and
- final decision-label stability.

If the scientific decision changes under the conservative treatment, the
method remains blocked.

The resumed wrapper independently reruns the diagnostic before PRAiSE,
requires the exact count topology above, and requires the two exceptional
histories to match their canonical raw source rows as exact joint zeros. That
source-lineage check was not available in the original `777007` export and is
therefore a runtime gate, not an already claimed result.

## Launch-manifest failure and repair

PBS `777008.kunanyi-ohpc` (`g_lo_radhist`) finished with `Exit_status=1` and
zero recorded CPU, memory, and walltime usage. The wrapper stopped at its first
stage-integrity check:

```text
scripts/kunanyi/python_compat/__pycache__/hdf5plugin.cpython-311.pyc: FAILED
sha256sum: WARNING: 1 computed checksum did NOT match
```

The v4 staged manifest included a generated `.pyc` file. Remote preflight then
ran `py_compile`, which legitimately rewrote that bytecode before the queued
job checked the manifest. This is an immutable-stage construction error, not a
pressure-treatment or PRAiSE result. The diagnostic, source-lineage gate,
emissivity calculation, and raytracing did not run.

The wrapper now fails closed if its manifest binds `__pycache__`, `.pyc`, or
`.pyo` entries. A clean v5 stage excludes generated bytecode. Its remote
preflight compiled the staged Python and then rechecked all `83` manifest
entries successfully, with zero bytecode entries.

PBS `777009.kunanyi-ohpc` (`g_lo_radhist`) was submitted from that clean stage
and verified queued:

```text
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v5
state=Q
queue=normal
qtime=Sun Jul 26 23:18:27 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
```

The completed history cache is reused; it is not regenerated or mutated.
The PBS stop rule is active.

## Endpoint no-positive classification failure and repair

PBS `777009.kunanyi-ohpc` passed the stage manifest and repeated pressure
diagnostic, then finished with `Exit_status=2` after `00:07:52`. Its archive,
zero-byte stderr, and decision record preserve the first failure:

```text
PressureTreatmentError: pressure-treatment trim reaches beyond the endpoint
```

Both exceptional rows observed by the diagnostic have exactly one present
record at output `5000`, with joint-zero pressure, density, and tracer and no
positive record. In the treatment planner, that topology satisfied both the
old single-leading-zero trim expression and the no-positive expression:
`positive_count == present_count - 1` is true when both sides are zero. The
planner therefore attempted to advance the trim from column `5000` to
nonexistent column `5001`.

The categories are now mutually exclusive. A row is trim-eligible only when it
also has at least one positive record; a history with no positive pressure is
excluded. An exact regression fixture models a sole endpoint presence with
joint-zero fields. It failed with the remote error before the change and
passed afterward. The full focused suite now reports `55 passed`.

Independent review returned GO: the new requirement does not weaken the
joint-zero, internal-zero, multiple-zero, lifecycle, or aggregate-count gates.
A fresh v6 stage passed its `83`-entry post-compilation manifest, zero-bytecode,
exact-hash, completed-cache, and no-overwrite checks.

PBS `777011.kunanyi-ohpc` (`g_lo_radhist`) was then verified running:

```text
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_radio_history_method_value_gate_resume_pressure_v6
state=R
queue=normal
qtime=Sun Jul 26 23:37:44 2026
resources=1 node, 16 CPUs, 128 GB, 48:00:00
runner_sha256=fe86c6ff44fa0e137eaeaa70f7f4664e3177f3e84ae8f0977823c820eecc2b2c
```

No polling followed running-state verification. The completed history cache
is reused and remains unchanged.

## Linear smoothing failure and diagnostic

PBS `777011.kunanyi-ohpc` passed its `83`-entry bytecode-free immutable
manifest, runtime imports, complete-cache pressure diagnostic, and repaired
pressure-treatment plan. It finished with `Exit_status=2` after `00:08:14`,
with `00:06:56` CPU time, `776964kb` memory, and empty stderr. Its stdout
records the first new failure:

```text
status=diagnostic_complete
affected_rows=10032 affected_outputs=5001
pressure_diagnostic_validation=passed
ValueError: smoothed pressure history must be positive after injection
```

The compact archive is readable and has SHA-256
`0049f76ebf915bdf5fc2f99c62b827a73b7e358326c746bc50bae56fff2012f2`.
It records `197566` active rows, `10030` trimmed leading-initialization rows,
and two excluded no-positive histories. No PRAiSE emissivity chunk or
raytracing product completed.

The positive treated histories passed validation immediately before the
current five-point linear Savitzky-Golay operation. The observed failure is
therefore linear-filter overshoot, not another raw-history or treatment
classification defect. Because pressure history affects adiabatic evolution
and radiative losses, clipping or flooring the result would change the
physical method and is not an acceptable mechanical repair.

The provisional method recommendation is:

- primary: unsmoothed treated pressure, matching the pinned upstream
  `smooth_pressure=False` default;
- required sensitivity: Savitzky-Golay smoothing in log-pressure space;
- diagnostic comparator only: a positive-kernel triangular smoother; and
- forbidden: clipping, flooring, excluding overshoot rows, or retrying the
  unchanged linear smoother.

Before implementing that recommendation in a science retry, the immutable
completed cache will be scanned read-only for invalid counts, exact affected
particle IDs and local stencils, pressure and endpoint changes, and bounded
adiabatic-rate summaries under all four treatments.

PBS `777065.kunanyi-ohpc` (`g_lo_psdiag`) was submitted for that diagnostic
and verified queued:

```text
state=Q
queue=normal
qtime=Mon Jul 27 14:18:49 2026
resources=1 CPU, 64 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_smoothing_diagnostic_777011
manifest_entries=83
manifest_bytecode_entries=0
cache_shape=197568x5001
cache_next_output=5001
```

The diagnostic does not call PRAiSE, mutate the cache, or authorize a science
retry. No polling followed queued verification.

## Smoothing diagnostic completion

PBS `777065.kunanyi-ohpc` finished with `Exit_status=1` after `00:13:51`.
That scheduler status records a packaging defect, not a failed diagnostic.
Stdout contains:

```text
status=diagnostic_complete
active_rows=197566 smoothed_rows=197398
affected_rows=99108
smoothing_diagnostic_validation=passed
```

The first and only stderr line was:

```text
tar: 2026-07-27-g-lo-pressure-smoothing-diagnostic-777011: file changed as we read it
```

The wrapper had archived the entire live analysis directory. The two completed
diagnostic products were retrieved directly and their local SHA-256 values
match the remote values:

```text
pressure_smoothing_diagnostic.json
  aca07047bb5b91338bb7a69e2eb687bacd69ab5fbde6eaef64f70b3f5c89aafc
pressure_smoothing_affected_rows.csv
  85caef2184edd7786e4d791fd52e77e422269bb6a156a48047d3c7901e4d79f2
```

The diagnostic makes the linear-domain decision unambiguous:

- `99,108 / 197,398` smoothed histories (`50.21%`) contain at least one
  non-positive linear-Savitzky-Golay output;
- those histories contain `216,035` invalid transformed records, only about
  `0.043%` of the positive treated records but distributed widely across
  particles;
- the minimum linear result is `-1.1641e-7`, and the minimum transformed/raw
  ratio is `-41,779.7`;
- log-pressure Savitzky-Golay and the triangular comparator produce no
  non-positive or non-finite values; and
- positivity alone is not a science acceptance gate: log smoothing changes
  endpoint pressure by as much as `-83.42%` and `+25.40%`.

These are numerical observations. The local stencils are consistent with
negative-lobe overshoot across sharp positive pressure changes, but the
diagnostic does not establish whether each change is a physical shock,
contact transition, or numerical fluctuation.

Linear-domain Savitzky-Golay is therefore blocked. Clipping, flooring, or
discarding the affected histories remains forbidden. Unsmoothed treated
pressure and log-pressure Savitzky-Golay are both implementable, but the
diagnostic does not yet establish that they give materially equivalent PRAiSE
emissivities. Its bounded adiabatic-rate sample is also front-loaded by chunk
order and is not a population-representative substitute for the actual
function.

Before a full science retry, the next gate is an actual
`calculate_praise_emissivity_numba` comparison under explicit `unsmoothed` and
`log_savgol` modes on a deterministic stratified cache sample. It must compare
full and lossless emissivities at both frequencies, weighted aggregate
luminosities, spectral index, decision direction, and discrepancy
concentration. The predeclared materiality limits are `0.10 dex` in aggregate
emissivity and `0.10` in two-point spectral index.

The diagnostic wrapper is repaired for future use: it copies only the two
validated outputs into a stable payload and archives an explicit file list.
No diagnostic rerun is required, and no full Goal 049 science retry has been
authorized from this result alone.

## Actual-PRAiSE pressure-method sensitivity

The required actual-function gate is now implemented. It calls the pinned
`calculate_praise_emissivity_numba` path under explicit `unsmoothed` and
`log_savgol` modes on a deterministic `4096`-history
certainty-plus-stratified sample. Full-loss and lossless emissivities are
computed at `150 MHz` and `1.4 GHz`.

The sample design includes all short histories, full-cache global log-SG
endpoint and minimum-ratio extremes, linear-failure affected/unaffected
strata, trim status, history length, injection age, pressure range, and shock
state. Its calibrated weights estimate represented-population aggregates, but
the result remains deterministic weighted-sample evidence rather than a
full-population equivalence proof.

The discrepancy concentration gate ranks unweighted per-particle absolute
method differences, then accumulates exactly `1%` of represented population
mass with fractional inclusion of the boundary row. The compact result
records its numerator, denominator, total and target represented weights, and
boundary semantics. The archive also includes `staged_inputs.sha256`.

After focused local verification and independent method review returned
`GO`, the fresh remote stage passed its `120`-entry bytecode-free manifest,
runtime imports, cache metadata, and no-overwrite gates. PBS
`777074.kunanyi-ohpc` (`g_lo_pmvalue`) was submitted and verified queued:

```text
queue=normal
qtime=Mon Jul 27 15:06:53 2026
resources=1 node, 16 CPUs, 96 GB, 12:00:00
stage=/u/bwbrook/codex_kunanyi/goal049_g_lo_pressure_method_value_diagnostic
analysis=/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-pressure-method-value-diagnostic
```

No full Goal 049 science retry or raytrace is authorized until this diagnostic
returns and its predeclared materiality gates are reviewed. The PBS stop rule
is active.

## Non-finite endpoint forensic gate

PBS `777074.kunanyi-ohpc` finished with `Exit_status=2` after `01:01:06`.
The staged manifest and runtime imports passed, stderr is empty, and stdout
ends with:

```text
ValueError: PRAiSE returned non-finite endpoint emissivities
```

This is an actual-PRAiSE result failure, not an archive or input-preflight
failure. The current exception is non-identifying because finiteness is
checked only after all full/lossless injection groups for the current pressure
mode have returned, and no output is written before both pressure modes
complete.

The upstream method explicitly marks some cooled/no-emission states with NaN
injection Lorentz factors. Observation of NaN alone is insufficient evidence
for zero emission: injection gamma begins as NaN, an endpoint-valued shock
index is not visited by the backward loop, and non-finite adiabatic/radiative
coefficients or gamma arithmetic can propagate into emissivity.

The forensic continuation therefore replays the exact pinned upstream
functions and records mode, loss branch, injection group, physical ID,
frequency, output class, shock index, no-emission index, pressures, tracer,
and current/injection Lorentz factors. It classifies a full-loss NaN as
`proven_full_loss_cutoff` only when replay, finite-dynamics, visited-shock,
explicit-no-emission, and matched-finite-lossless gates all pass. It does not
replace any value.

PBS `777213.kunanyi-ohpc` / `g_lo_pnf` was submitted and verified queued on
`normal` at `Mon Jul 27 17:11:21 2026`, requesting one node, `16` CPUs,
`96 GB`, and `12:00:00`. The fresh stage and analysis roots are:

```text
/u/bwbrook/codex_kunanyi/goal049_g_lo_praise_nonfinite_forensic
/scratch/bwbrook/xray_cavities_analysis/2026-07-27-g-lo-praise-nonfinite-forensic
```

The acceptable diagnostic decisions are cutoff-policy eligibility, unresolved
PRAiSE numerical block, or failure to reproduce a non-finite result. No full
science retry is implied by any of them.

## Forensic completion and singleton boundary diagnosis

PBS `777213.kunanyi-ohpc` finished with `Exit_status=0` after `03:34:28`.
The immutable inputs, deterministic selection, both pressure-mode checkpoints,
forensic replay, and archive validation passed. Stderr is empty. The final
scheduler record retains `Stageout_status=1`, but the stage-root archive and
logs were present and retrieved directly.

The retrieved archive is readable and has SHA-256:

```text
03f94d5df0c70ddb7f0d1070186ca0f3df9946e00cf9df40debfc0bdf81564be
```

The observed failure pattern is exact:

- `384 / 32768` forensic cells are non-finite;
- the same `48` physical IDs account for every non-finite cell;
- every affected history has effective length `1` and starts at endpoint
  output `5000`;
- unsmoothed and log-Savitzky-Golay pressure each contain `192` non-finite
  cells;
- full-loss and lossless branches fail equally, so none is a proven
  full-loss cooling cutoff;
- all affected inputs and replay dynamics are finite; and
- pinned replay reproduces the result, but injection gamma remains unassigned
  because the optimized backward interval loop has zero iterations.

The first six bullets are observations. The conclusion that this is an
optimized PRAiSE singleton-boundary inconsistency is an inference supported by
the reviewed implementation: the older non-optimized path naturally uses the
endpoint gamma as injection gamma for a one-record endpoint history, whereas
the optimized path initializes injection gamma to NaN and assigns it only
inside the empty backward loop.

The primary repair is therefore an explicit, narrowly gated
`instantaneous_recent_shock` convention:

- only an effective one-record history may enter the convention;
- pressure, density, tracer, shock state, and current Lorentz factor must be
  finite and physically valid;
- injection, last-shock, and endpoint times must be consistently ordered;
- the shock age must not exceed the final output interval;
- the real cache must contain exactly the expected `48` singleton rows;
- injection pressure is the endpoint pressure;
- injection gamma is the current endpoint gamma; and
- with no elapsed history interval, full-loss and lossless emissivities must
  be identical.

The adapter defaults to fail-closed unless that policy is selected explicitly.
The singleton mask, count, IDs, and provenance remain distinct from the
leading-zero pressure-treatment mask. Excluding the `48` rows is retained only
as a conservative comparator. The rows are `48 / 197568` of the endpoint
population; a design-weighted instantaneous-emissivity screen estimates about
`3.14e-6` of total emissivity, but this is not a substitute for the required
map-level comparison.

## Repaired actual-PRAiSE gate submitted

The singleton convention and provenance plumbing passed the focused local
suite:

```text
75 tests passed
four PBS wrappers passed bash -n
git diff --check passed
```

A fresh no-overwrite remote stage reused the immutable completed history cache
and affected-row evidence. Its changed-file hashes, wrapper syntax, cache hash,
affected-row hash, and staged-input manifest passed. Exactly one repaired
method-value diagnostic was submitted and verified running:

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

This is the repaired pressure-method value gate, not the full Goal 049
raytrace. No further remote command followed running-state verification. Wait
for Barry's completion email before retrieval or any full science continuation.

## Effective-singleton overlap repair

PBS `778078.kunanyi-ohpc` finished with `Exit_status=2` after `00:04:25`.
Its immutable manifest, cache hash, affected-row hash, runtime imports, and
input gates passed; stderr is empty. The first failure occurred in the
pressure-treatment planner before PRAiSE:

```text
trim=10030 expected=10030
no_positive=2 expected=2
single_record=46 expected=48
```

The forensic cache evidence resolves the discrepancy exactly. There are `46`
untrimmed one-record histories and two more histories, physical IDs `197519`
and `197520`, whose leading joint-zero record is removed by the approved trim,
leaving one effective positive record. Thus singleton status is an orthogonal
post-treatment property, not a mutually exclusive raw-pressure category.

The version-3 contract now:

- preserves exclusive base categories for unchanged, trim, and no-positive
  histories;
- computes effective singleton status after the approved trim;
- fails closed on `10030 / 2 / 48 / 2` trim, no-positive, effective-singleton,
  and trim-singleton-overlap counts;
- hashes the effective singleton mask and effective history lengths;
- propagates singleton provenance independently from trim provenance;
- checks that PRAiSE returns exactly the planned singleton IDs; and
- excludes the union of trim and singleton histories from the conservative
  comparator.

Independent scientific and code audits both supported this repair. The focused
suite passed `76` tests, all four related PBS wrappers passed `bash -n`, and
`git diff --check` passed. A fresh `120`-entry bytecode-free stage passed
remote hashes, wrapper syntax, immutable cache and affected-row hashes,
no-overwrite gates, and queue preflight. Exactly one replacement diagnostic
was submitted:

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

The PBS stop rule is active. No remote command followed queued verification.

## Branch-semantics correction after PBS 778079

PBS `778079.kunanyi-ohpc` completed the expensive unsmoothed actual-PRAiSE
calculation, then failed the project assertion that full-loss emissivity must
never exceed matched `losses="none"` emissivity. The run exited `2` after
`01:54:04`; stderr is empty.

That assertion is not supported by the pinned implementation. The
`losses="none"` branch zeroes both the pressure-work coefficient and the
radiative coefficient. The full branch retains both. Consequently,
full-versus-none combines adiabatic evolution and radiative losses, and
adiabatic compression can legitimately reverse the assumed ordering. The
observation from `778079` is only that at least one selected unsmoothed cell
had full emissivity above the no-evolution branch; the magnitude and
concentration were not persisted by the old gate.

The corrected method uses three matched branches:

- `full`: pressure work plus radiative evolution;
- `adiabatic`: the same pressure work with radiative evolution disabled; and
- `none`: neither pressure-work nor radiative evolution.

Full-versus-none is now descriptive. Full-versus-adiabatic is the
radiative-suppression discriminator. A reference-relative plus per-cell ULP
tolerance prevents bright cells from hiding relative discrepancies in faint
cells. The compact full/adiabatic/none arrays are checkpointed before
comparison, and a replay audit counts the pinned state machine's silent
intermediate-gamma fallbacks. Any fallback or full-above-adiabatic result
blocks scientific acceptance. The wrapper still archives the evidence before
returning nonzero on a failed scientific gate.

The corrected implementation passed `98` focused Goal 049 tests, Python
compilation, four related wrapper syntax checks, method-wrapper `shellcheck`,
and `git diff --check`. A fresh `120`-entry bytecode-free remote stage passed
exact hashes, immutable cache/evidence checks, runtime imports, and
no-overwrite gates. PBS `778919.kunanyi-ohpc` was submitted once and verified
running on `normal` at `Tue Jul 28 09:35:49 2026`, requesting one node,
`16` CPUs, `96 GB`, and `12:00:00`. No full raytrace was submitted.

## Branch-aware non-finite evidence continuation

PBS `778919.kunanyi-ohpc` finished with `Exit_status=2` after `01:27:35`.
Its stage manifest, immutable-input checks, and runtime imports passed;
stderr is empty. The deterministic `4096`-row selection was written and is
byte-identical to the selection used by the completed forensic run. Stdout
ends with:

```text
ValueError: PRAiSE returned non-finite endpoint emissivities
```

The failure occurred during the unsmoothed actual-PRAiSE calculation before
the first emissivity checkpoint. The v4 post-return finiteness guard did not
record which mode, branch, frequency, particle, or non-finite class failed.
Because the matched adiabatic branch was newly introduced, it is the leading
hypothesis, but this is an inference and is not treated as a result.

The v5 evidence path is deliberately fail-closed. It:

- invokes the pinned diagnostic return path for full, adiabatic, and none
  branches;
- preserves raw NaN, positive-infinity, and negative-infinity cells without
  replacement or exclusion;
- checkpoints each mode/branch result before any scientific comparison;
- records mode, branch, physical ID, frequency, raw non-finite class, and
  replay classification for every affected cell;
- reconciles the forensic records against the raw checkpoint arrays;
- captures gamma/dynamics audit exceptions as explicit audit failures; and
- archives all compact evidence before returning a deliberate nonzero status
  when any non-finite, audit, or reconciliation failure remains.

Finite-only method comparisons are suppressed whenever that fail-closed
surface is active. This diagnostic cannot silently turn a numerical failure
or unresolved PRAiSE state into zero emission.

Local verification passed `107` focused tests in `6.11s`, Python compilation,
wrapper syntax, wrapper `shellcheck`, and `git diff --check`. A final
independent scientific/code review returned `GO` for one remote evidence
capture. The fresh stage passed a `120`-entry bytecode-free manifest, exact
changed-file and immutable-input hashes, runtime imports, no-overwrite gates,
and the normal-queue check. Exactly one job was submitted:

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

The PBS stop rule is active. No remote command followed running-state
verification, and no full raytrace was submitted.

## Adiabatic non-finite diagnosis

PBS `779183.kunanyi-ohpc` completed the archive-first v5 evidence path with a
deliberate scientific `Exit_status=3`. The retrieved record contains `9,103`
NaN cells, all in the adiabatic branch: `4,643` under unsmoothed pressure and
`4,460` under log-Savitzky-Golay pressure. The matched full and no-loss
branches are finite.

Observed replay evidence shows finite dynamics inputs, valid shock assignment,
and pinned no-emission state with NaN injection gamma for every affected cell.
No non-finite value was replaced, excluded, clipped, or interpreted as zero.

The numerical diagnosis is that pinned PRAiSE evaluates separate
absolute-time powers in the adiabatic recurrence. On strictly positive-time
intervals, the pressure-ratio/log-difference recurrence is algebraically
equivalent but avoids that unstable operation. The compact recovery gate:

- reproduces one exact archived failure in each unsmoothed/log-Savitzky-Golay
  by `0.15/1.4 GHz` stratum under the pinned original path;
- compares the stable recurrence with an 80-digit original-form reference;
- treats endpoint-to-shock intervals as the decision gate;
- retains pre-shock anomalies as evidence; and
- reconstructs injection gamma and emissivity without changing pinned
  physical defaults.

This is a numerical-method recovery test, not authorization for the full
`4096`-row method comparison or raytrace.

## Duplicate recovery launch and index-order repair

PBS `779684.kunanyi-ohpc` and `779685.kunanyi-ohpc` were submitted at the same
second with the same job name, resources, and fixed output paths. The local
handoff recorded only `779684`; the later remote job-id file contained
`779685`. Their shared output paths make the first job's individual log
unrecoverable. The surviving shared evidence has timestamps matching the later
`779685` completion and is therefore packaged as a shared-stage snapshot, not
as two independent scientific results.

The surviving failure occurred before any recovery summary was produced:

```text
TypeError: Indexing elements must be in increasing order
```

The trace selector intentionally orders rows by evidence class rather than
cache-row number. The inherited reader passed those non-monotonic indices
directly to `h5py`. The repaired adapter reads sorted unique cache rows and
then restores the exact requested ordering for physical IDs, pressure
treatment, positions, velocities, and other row-aligned fields. The scientific
selection and gate definitions are unchanged.

Regression tests reproduce the remote failure and verify alignment after the
repair. The wrapper now uses an atomic run lock, and the replacement
submission uses a persistent submit-once guard. The repaired compact
diagnostic is PBS `779693.kunanyi-ohpc`, verified running on `normal` at
`Tue Jul 28 20:42:31 2026`. No full comparison or raytrace was submitted.

## Repaired recovery completion and closeout

PBS `779693.kunanyi-ohpc` completed with deliberate scientific
`Exit_status=3`. The HDF5 order repair passed, all four archived failure
strata reproduced, every retained stable gamma value was finite, stable
injection emissivity was finite, and all `98` high-precision comparisons
passed.

The remote summary's stable-trajectory label was composite: it also included
full-loss fallback and pinned-upstream comparison state. The corrected local
reporting separates the conditional adiabatic-recovery PASS from the overall
full-loss method decision.

The full-loss method remains blocked by `22,737` relevant non-finite `a2`
intervals and `45,474` pinned gamma fallbacks. No `4096`-row comparison or
raytrace is authorized. The next method goal should derive and independently
validate a stable full-loss `a2` and gamma recurrence on the existing bounded
panel.
