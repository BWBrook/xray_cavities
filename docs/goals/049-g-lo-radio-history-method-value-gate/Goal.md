# Goal 049: G-LO Radio History, Method, And Value Gate

## Objective

Use the retained accepted-lineage `G-LO` particle sequence to determine whether
the project can recover a complete, scientifically usable particle history,
run the current `plutokore` PRAiSE and particle-raytracing implementation under
an explicit common observing contract, and quantify whether loss-aware radio
products differ enough from a matched endpoint-lossless reference to justify
new `C-HI` and `C-LO` history-regeneration production runs.

This is the G-LO-first discriminator required by Goal 048. It must fail closed
before any mixed-method three-case radio claim.

## Approved Scope

Barry approved Goal 049 on 2026-07-24.

In scope:

- validate the retained G-LO `particles.0000..5000.dbl` source surface,
  including schemas, physical times, cadence, IDs, missingness, overlapping
  outputs `1000..1499`, and the `1499/1500` continuation seam;
- implement field-selective, endpoint-ID-keyed, chunked and restartable history
  recovery without allocating a dense all-field particle cube;
- exercise the actual current
  `plutokore.radio.praise.calculate_praise_emissivity_numba` and
  `plutokore.radio.raytracing.raytrace_particles_multiple_freq` functions;
- validate units, flux recovery, rotations, Doppler handling, support gaps,
  resolution, ray step, particle density, and determinism;
- calculate matched full-loss and endpoint-lossless G-LO products at observed
  `150 MHz` and `1.4 GHz`, redshift `z=0.05`, and views `0/45/90 deg`;
- compare luminosity, detected support, extent, spectral index, and overlap
  with accepted X-ray/truth controls; and
- produce a value-of-information decision on two possible new 64-node
  `C-HI`/`C-LO` history-regeneration runs.

Out of scope:

- no new PLUTO production;
- no `C-HI` or `C-LO` history-regeneration submission;
- no mixed loss-aware/lossless three-case result;
- no synchrotron-age claim from two frequencies;
- no raw particle deletion, relocation, truncation, or overwrite;
- no change to accepted simulation physics or scientific defaults; and
- no publication-facing or population-level claim.

## Source Contract

The accepted history source is the restart-lineage union of:

- initial G-LO root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles/problem/outputs`,
  expected outputs `0000..1499`; and
- guarded G-LO root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation/G-LO/particles/problem/outputs`,
  expected outputs `1000..5000`.

The guarded run is an accepted replay from the exact output-1000 particle
restart, not a byte-identical continuation of all later files in the first
root. The canonical history is therefore initial outputs `0000..0999` plus
guarded outputs `1000..5000`. Initial outputs `1001..1499` are superseded
alternate-trajectory evidence and must not be merged with the guarded
endpoint lineage.

The history gate passes only if:

1. every expected output is readable with a consistent field schema, endianity,
   precision, payload size, and strictly increasing physical time;
2. output `1000` is byte-identical across roots and binds the accepted restart
   anchor before the guarded replay is selected as canonical;
3. both the cross-root `0999/1000` interval and the guarded-root `1499/1500`
   interval are consistent with the documented cadence;
4. endpoint IDs are unique and all post-injection absences can be distinguished
   from legitimate pre-injection absence;
5. no endpoint particle has an unexplained missing post-injection record; and
6. the accepted endpoint record, canonical source hashes, restart-anchor hash,
   and superseded-overlap range are bound into the output provenance.

Any failed item blocks a full-loss product.

## Method Contract

The primary physical and observing surface is:

- `plutokore` source commit
  `e80252cf35ff5a06166240e2867d3d485aaf6956`;
- observed frequencies `150 MHz` and `1.4 GHz`;
- `z=0.05`;
- views `0`, `45`, and `90 deg`;
- common physical support and grid across loss treatments, views, and bands;
- pixel size no larger than `2 kpc`;
- circular `5 kpc FWHM` primary beam with `2.5/10 kpc` sensitivities;
- primary threshold `0.05 mJy beam^-1` with one-third and three-times
  sensitivities;
- matched `losses="full"` and `losses="none"` emissivity calls using identical
  endpoint particles and all other parameters; and
- radio topology derived from radio brightness, with tracer and accepted
  X-ray products used only as truth/overlap controls.

The electron index, equipartition parameter, Lorentz-factor limits,
last-shock component, particle-support distance, and map convergence settings
must be recorded explicitly and sensitivity-tested where they remain
provisional.

## Compute And Storage Contract

- Read source files sequentially and retain only fields required by PRAiSE and
  endpoint raytracing.
- Store histories keyed to accepted endpoint IDs in chunked datasets.
- Preserve `NaN` for valid pre-injection absence and reject missing
  post-injection records.
- Checkpoint after deterministic output ranges and emissivity ID chunks.
- Keep peak memory below the requested node memory and record measured peak
  RSS, walltime, cache size, and compact-product size.
- Archive compact manifests, metrics, maps, and logs only. Do not place raw
  particle files or dense history caches in Git.
- Do not delete the retained source history in this goal.

## Decision Gate

The value gate will report one of:

1. `G_LO_FULL_HISTORY_VALUE_GREEN_REGENERATION_REVIEW_JUSTIFIED`:
   source/method/compute gates pass and full losses materially change at least
   one thesis-relevant radio observable under a stable sensitivity surface;
2. `G_LO_FULL_HISTORY_VALUE_LOW_MATCHED_LOSSLESS_SCOPE_PREFERRED`:
   source/method/compute gates pass but loss-aware changes are not materially
   decision-relevant;
3. `G_LO_HISTORY_BLOCKED`:
   source continuity, schema, seam, or endpoint-ID completeness fails;
4. `G_LO_RADIO_METHOD_BLOCKED`:
   actual-function numerical, unit, support, or convergence checks fail; or
5. `G_LO_RADIO_COMPUTE_BLOCKED`:
   the recovery path is not practical within the declared memory, storage, or
   walltime envelope.

New multi-node `C-HI` and `C-LO` production remains a later material decision
requiring Stas/Patrick review and Barry approval.

## Completion And Stopping

- If the local method gates fail, stop with the exact failure and no PBS job.
- If remote preflight fails, stop without substituting sources or schemas.
- If one post-processing PBS job is submitted and verified queued or running,
  invoke the PBS stop rule and wait for Barry's completion email.
- Apply the 80/20 delivery rule: complete the decision-grade core and one
  focused repair pass; do not add marginal parameter sweeps that cannot change
  the production decision.

## Validation

- red-green focused tests for the particle reader, overlap/seam decisions,
  missingness classification, checkpoints, and aggregation;
- actual-function PRAiSE and raytracing fixtures, not only stand-alone formulas;
- deterministic repeat checks and resolution/ray-step/support sensitivities;
- CSV/JSON schema and duplicate-header checks;
- exact source and implementation hashes;
- compact payload guard;
- independent scientific review of the decision packet;
- `bash -n` for any PBS wrapper; and
- `git diff --check`.
