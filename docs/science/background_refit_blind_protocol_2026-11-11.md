# Frozen prospective background-refit diagnostic

Prepared 11 November 2026 in response to board message 3244. This protocol
freezes two existing operators before any new held-out refit result is
inspected. The machine-readable specification is
`configs/background_refit_blind_2026-11-11.json`; its SHA-256 binds the runner
and exact observer source files. Commit the specification, runner and this
protocol before acquiring held-out emission products or beginning new native
accounting that reads their native fields. Existing native accounting results
must not select or refine the observer rule.

## What is being tested

The favorable G-HI/20 result was **not an observer-only background rule**.
`build_q032_source_emission.finish_views` constructs

```text
C = current tr1 > 1e-3
A_v = current non-C cells with full three-component speed >= v
D_A = line-of-sight integral of [initial emissivity - current emissivity]
      in those same current A_v cells
replacement image = current whole image + D_A
ambient_replaced_refit = original_observers(replacement image)
```

The tracer partition, three-dimensional speed and initial same-cell emissivity
are unavailable to an X-ray observer. This arm is a frozen **truth-assisted
diagnostic**, even when the subsequent two-dimensional fit is tracer-blind.
Its held-out performance tests whether ambient replacement and refitting
generalize; passing cannot validate a real-world detector.

The separate **observer_refit** arm calls `original_observers` on the current
whole image alone. It is the existing `exact_projection_refit` comparator,
not a newly invented replacement for the favorable diagnostic. Its mask API
accepts only a two-dimensional brightness image and axes. It does not access
the tracer mask or native component paths. No new observer-available estimate
of D_A is specified or accepted by this protocol.

Both arms retain both existing comparators: degree-6 polynomial-background
hemisphere seed/grow and 5%-deficit selection against the radial background.
The exact source hashes freeze all fit, clipping, seed, support, aperture and
component choices. There is no threshold adjustment, fallback, tracer repair
or selection of whichever comparator does better after scoring.

## Frozen cohort and exposure limits

- Development exclusion: G-HI/20, all three side-on azimuths.
- Science: C-HI/C-LO/G-LO at indices 10, 20, 30, 40 and 50; G-HI at 10, 30
  and 40. G-HI 48--50 stay excluded by the existing boundary decision.
- All three side-on azimuths 0/45/90 degrees and both z hemispheres are
  reported separately: 54 science views, 108 science sides per arm/method.
  These views are not independent realisations.
- Null: each case's initial image, at every declared azimuth, with no evolved
  cavity target. The null target is an explicitly empty mask, not an inference
  that the initial simulation's nozzle cells have zero tracer. Initial
  replacement has D_A = 0. Nulls test whether the operators invent cavities
  on the initial atmosphere; they are not evolved no-jet controls.
- Primary: retained-linear emissivity, 100-km/s partition in the diagnostic.
  Observer-only selection has no velocity cut. The clamped correction and
  30/300-km/s partitions are declared sensitivities, not opportunities to
  choose a better primary result.

Earlier published legacy-method selected-age summaries already exist, and
some were visible during source/doc search. This is a prospective test of
the newly frozen refit diagnostic, not a claim that every prior measurement
or simulation is globally unseen. No new held-out refit maps, tables, mask
metrics or native truth have been inspected during this freeze. Subsequent
native mass/energy accounting may read the same native fields, but it may
not feed the segmentation, alter the cohort, thresholds or declared criteria.

## Outcomes and failure criteria

Use full projected `path_C > 0` truth for science, separately on each side,
with exact pixel areas. Do not crop truth to the detector's 120-kpc aperture
or report medians only over detected sides. Nondetections remain rows with
zero completeness, undefined purity and zero recovered volume. Report the
fraction of truth inside the candidate aperture, aperture contact, false
selected area, completeness, purity and exact-edge revolution volume.
No native filling fraction is inferred for newly selected masks.

The prespecified strict diagnostic-generalization screen requires every
primary science side to have completeness >= 0.75, purity >= 0.95 and no
aperture contact. Every initial null side must have zero detections. These
are new prospective reporting criteria motivated by the development result,
not established physical acceptance thresholds or automatic detector-adoption
criteria. Report every failing side; one failure rejects the universal
generalization statement for that arm/method. A high aggregate score cannot
erase a failed case, age, side or null. A partial result is a partial result.

Nonfinite data, missing units, mismatched grids, mutated hashes or missing
native provenance stop scoring; they are data-integrity failures, not zero
measurements. Native boundary contact, sky coverage and other producer
qualification flags must accompany the results. They cannot silently remove
an unfavorable unit after truth is opened. Projection/volume conventions
remain the same as the development diagnostic.

## Execution and sealing

The existing native producer is explicitly hard-coded to G-HI/20. It cannot
produce this cohort by changing a label or bypassing inherited-lineage gates.
A separately reviewed generalization/staging adapter must preserve the
per-case native-input contracts, exact projection axes, source and emissivity
identities, correction policies and all qualification flags. This protocol
and runner do not weaken or replace that upstream provenance audit.

Prepare a source-bound input manifest containing `units`, each with `unit_id`,
`case`, `snapshot_index`, `view_deg`, `kind` (`science` or `initial_null`) and
`maps` (`path`, absolute, and `sha256`). Every frozen unit must occur exactly
once. Each unit also binds `provenance.native_input_receipt` and
`provenance.producer_receipt` (absolute path and SHA-256), and preserves the
producer's exact `qualification_holds` list. Native/producer case and index,
the producer-to-native receipt hash, and its map output hash must agree.
The NPZ map schema is the existing producer schema: the four exact axes,
current whole brightness under both correction conventions and D_A maps at
30/100/300 km/s. Do not display maps or metrics while generating predictions.

```bash
.venv/bin/python scripts/science/run_background_refit_blind.py predict \
  --config configs/background_refit_blind_2026-11-11.json \
  --manifest <audited input manifest> --output-dir <new sealed predictions>
```

Prediction accesses only the named brightness/component and axis arrays;
it never reads `path_C_kpc`. Component inputs in the diagnostic remain
truth-assisted by construction. Seal all prediction files and
`prediction_receipt.json` by recording their hashes in the private archive
before releasing the scoring manifest to the evaluator. Have an independent
reviewer check this ordering and the input/native provenance chain. A local
Boolean saying truth was not read is not evidence of independent custody.

Only then provide the separate truth manifest: same complete unit metadata,
native/producer provenance and qualification holds, with `truth` absolute
path and SHA-256. Truth NPZs contain the exact matching
axes and projected `path_C_kpc`; initial-null targets are explicitly zero.

```bash
.venv/bin/python scripts/science/run_background_refit_blind.py score \
  --config configs/background_refit_blind_2026-11-11.json \
  --predictions <sealed predictions> --truth-manifest <audited truth manifest> \
  --output-dir <new evaluation directory>
```

Scoring verifies the frozen runner/source/config, full cohort, exact complete
mode/method/correction/cut label and mask inventories before opening any truth,
prediction hashes, truth hashes, provenance/hold preservation and exact grids.
It requires a nonzero exact primary side count for every arm/method and produces all side rows and an
arm/method verdict. No plot or score is generated during prediction. Preserve
all failures, receipts and exceptions. Any amendment after held-out inspection
ends this test; a later revised rule needs a new protocol and new hold-out.

## Verification and remaining decision

Focused synthetic tests check source mutation, cohort omissions/duplicates,
development exclusion, full-truth denominators, retained nondetections, null
false selections, prediction/truth separation and post-freeze tampering.
They verify the evaluator; they are not scientific results on the cohort.

No held-out evaluation or native job is run by preparing this protocol.
The remaining scientific choice, if the collaboration wants a deployable
detector, is how to estimate surrounding-gas contamination from observer data
alone. That is a new proposal requiring reconciliation before implementation;
the native-truth replacement cannot silently serve as that estimate.
