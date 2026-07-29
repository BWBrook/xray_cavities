# Three-Case Endpoint Radio Source And Method Gate

Date: 2026-07-24

Status: `complete_source_method_gate_g_lo_method_value_gate_required`

Decision label:
`THREE_CASE_LOSS_AWARE_RADIO_BLOCKED_G_LO_METHOD_VALUE_GATE_REQUIRED`

## Executive Decision

The project is ready to define and validate a common radio-observable method,
but it cannot yet calculate a scientifically comparable loss-aware endpoint
product for `C-HI`, `C-LO`, and `G-LO`.

The blocker is source history, not post-processing cost:

- the accepted G-LO chain retains continuous filename coverage
  `particles.0000..5000` across its initial and guarded-continuation roots,
  but its cross-root seam and usable ID/time/schema history have not yet been
  validated;
- the accepted C-HI chain retains only endpoint/restart particle files
  `4277` and `5000`;
- the accepted C-LO chain retains only particle files `1611` and `5003`; and
- the existing C-HI dense caches are early or reduced-grid products, not the
  accepted final full-grid endpoint lineage.

The sparse C-HI late window remains useful interface evidence, but it cannot
recover radiative losses accumulated over the full source lifetime. A
three-case result that used full histories for G-LO and endpoint-only or sparse
histories for C-HI/C-LO would confound the physical comparison with a method
change. This gate rejects that mixture.

No radio PBS job was submitted.

## Project-Plan Alignment

Aim 4 of the Honours Research Plan makes particle-based radio products a core
observable stream, including radio boundaries, integrated luminosity, and
synchrotron age where supported. The same plan explicitly treats radio
workflow effort as a schedule risk and qualifies spectral ageing by
feasibility.
The minimum three-case experiment also requires one radio-observable workflow
and an observable-versus-truth comparison surface.

The correct response to the failed source gate is therefore an explicit scope
decision:

1. first test whether the retained G-LO history and candidate production
   method can recover the intended estimand at acceptable cost;
2. if losses materially affect the headline observables and the method is
   viable, escalate new C-HI/C-LO history production; or
3. narrow the radio deliverable to a matched lossless endpoint reference and
   state that full ageing and synchrotron age remain unsupported.

The intended case contrasts are conditional, not population estimands:

- `C-HI - C-LO` estimates the jet-power contrast within the selected Stewart
  cluster setup at nominal `50 Myr`;
- `G-LO - C-LO` estimates the environment contrast at low jet power and
  nominal `50 Myr`; and
- `0/45/90 deg` are deterministic projections of one simulation realization,
  not independent replicates.

Loss-aware and endpoint-lossless products answer different questions and must
not share one headline estimand.

## Observed Source Inventory

| Case | Accepted endpoint lineage | Retained raw particle sequence | Dense cache evidence | Full-loss readiness |
| --- | --- | --- | --- | --- |
| `C-HI` | final full-grid cluster/high-power chain | `4277` and `5000` only, split across fresh/final roots | approximately `5` and `10 Myr` caches plus a `33.374 Myr` reduced-grid rehearsal cache | fail |
| `C-LO` | endpoint-oriented cluster/low-power chain | `1611` and `5003` only | none found | fail |
| `G-LO` | initial plus guarded group/low-power chain | `0000..1499` plus `1000..5000`, jointly continuous by filename | no dense cache found | candidate: seam, ID, time, and schema continuity unverified |

The Goal 046/047 lifecycle evidence retained `5,501` radio-held rows totalling
about `63.3 GB`, corresponding to the two G-LO history roots. This proves
filename availability, not that every endpoint particle has a complete,
correctly timed history through the `1499/1500` cross-root seam. Protected
C-HI/C-LO endpoint particle files remain available, but they are not histories.

The live inventory was restricted to accepted production and analysis roots.
It did not broadly scan unrelated user scratch.

## Why Existing C-HI Products Cannot Fill The Gap

The final sparse PRAiSE table used outputs `4950, 4955, ..., 5000` and was
explicitly documented as a bounded interface/provenance product. It omitted
most of the source lifetime and its compact trajectory does not retain the full
shock-history surface needed to regenerate arbitrary frequencies.

The longest dense C-HI cache reaches `33.374 Myr`, but its source is the
`404 x 404 x 452` reduced-grid `kunanyi_single_node_250` rehearsal. The
accepted final endpoint uses the full production grid and a separate lineage.
Splicing those products would mix dynamics, resolution, and provenance.
Its recorded provenance path is
`/scratch/bwbrook/xray_cavities_analysis/2026-05-13-c-hi-to33-particles-hdf5/C-HI.to33.particles.hdf5`.

## Runtime And Method Audit

### Legacy staged XRAiSE/PRAiSE runtime

The staged `xraise.py` has SHA-256:

```text
4bf17cb8e63e2d87a06615c170c7dd307788554a0cee83409762223123ec8da5
```

Its low-level `praise_aio` returns the quantity calculated by
`get_loss_term`, while the `praise` wrapper attaches
`W Hz^-1 m^-3 sr^-1` units. Existing project callers variously interpret the
same `emis` field as an emissivity and as a multiplicative loss factor.

Observation: that API contract is internally ambiguous.

Decision: do not use it as the production Goal 048 observable surface.

### Current `plutokore`

The local `plutokore` checkout is clean at:

```text
e80252cf35ff5a06166240e2867d3d485aaf6956
```

Relevant source hashes:

```text
praise.py:
ce4b17cf40ecefabbbd4ef4330b75fb63c39d40c2ef1a05a6e5ac87131145bf4

raytracing.py:
597bf9241fee0eabc1f57a9715a338ee588157787dd2ad1edd939e7c17426f38
```

`calculate_praise_emissivity_numba` consumes complete particle histories and
returns explicit multi-frequency emissivity in
`W Hz^-1 m^-3 sr^-1`. `raytrace_particles_multiple_freq` provides
multi-frequency, rotated, Doppler-aware particle ray integration within a
Delaunay support volume.

Inference: this is a source-reviewed candidate for the eventual production
observable. It has not yet passed end-to-end numerical validation, and its
Delaunay-support and nearest-particle choices require explicit disconnected-
lobe and ambient-gap tests.

## Provisional Common Observing Protocol

When the history gate is green, use:

- endpoints at nominal `50 Myr`;
- observed `150 MHz` and `1.4 GHz` at `z=0.05`;
- `9 GHz` only for a separately justified spectral-curvature gate;
- `0/45/90 deg` views;
- one physical map support and pixel grid across all cases and bands;
- primary circular beam `5 kpc FWHM`, with `2.5/10 kpc` sensitivities;
- pixel size no larger than `2 kpc`;
- primary mask threshold `0.05 mJy beam^-1`, with one-third and three-times
  sensitivities;
- radio topology derived from the radio map, with tracer used only for
  post-hoc truth overlap; and
- luminosity, boundary, area, extent, centroid, sidedness, spectral index where
  both bands are detected, and radio/X-ray/truth overlap.

Synchrotron age remains `NOT_ESTIMABLE` unless at least three common-beam bands
bracket a spectral break and the fit carries uncertainty under explicit
magnetic-field and loss assumptions.

Before production, the method gate must freeze and justify the electron index,
equipartition/magnetic-field prescription, `gamma_min`, `gamma_max`,
shock/acceleration rule, loss modes, smoothing, and particle-support
treatment. The beam and threshold values above are provisional observing
choices. `150 MHz` and `1.4 GHz` support monochromatic luminosities and a
two-point spectral index, not a band-integrated luminosity or spectral age.

## Local Numerical Gate

The Goal 048 helper supplies deterministic local fixtures for:

- a uniform-emissivity analytic line-of-sight integral;
- flux conservation under normalized Gaussian convolution; and
- rotation/view invariance of a symmetric source.

These fixtures are mathematical acceptance references. They do not certify
the complete production `plutokore` path, which must later pass the same tests
plus convergence, support, units, determinism, and provenance checks with the
actual implementation.

Machine-readable evidence:

- `source_ledger_extract.csv`;
- `source_inventory.csv`;
- `runtime_semantics_audit.csv`;
- `method_acceptance_gate.csv`;
- `decision_matrix.csv`; and
- `radio_source_method_gate_metadata.json`.

## Decision Alternatives

### A. G-LO Recovery, Method, And Value-Of-Information Gate

Recommendation: `NEXT`.

Use the retained G-LO sequence to:

- validate monotonic physical times, cadence, schemas, endpoint-ID recovery,
  missing-record classification, and the `1499/1500` seam;
- run analytic and synthetic recovery tests through the actual current
  `plutokore` PRAiSE and raytracing functions, including disconnected lobes,
  units, flux recovery, rotation, Doppler handling, resolution, ray step,
  particle density, and determinism;
- implement a field-selective, particle-ID-chunked, checkpointed path before
  loading the full source;
- compare full-loss and matched endpoint-lossless G-LO products at the
  headline frequencies and views; and
- quantify changes in luminosity, detected boundary, extent, spectral index,
  and X-ray/truth overlap.

This gate is post-processing and method validation, not a new PLUTO run. It
provides the missing evidence needed to decide whether two production reruns
are proportionate.

### B. Reproduce C-HI And C-LO Particle Histories

Recommendation: `CONDITIONAL_IF_G_LO_GATE_SHOWS_MATERIAL_VALUE`.

Run one endpoint-oriented particle-history production per missing case:

- unchanged accepted case physics, grid, environment, injection, and particle
  cadence;
- preferred `64 x 28 = 1792` MPI ranks;
- up to `48 h` per job, with the established PBS stop rule;
- particle output every `0.01 Myr`;
- restart-safe but deliberately sparse fluid output, because the accepted
  fluid science products already exist;
- immutable history/cache provenance and immediate post-processing followed by
  a new lifecycle decision.

G-LO does not need to be rerun if its retained filename sequence passes the
history parser, seam, and completeness gates.

Benefits:

- preserves the project-plan radio aim;
- enables a genuinely comparable full-loss analysis;
- supports multi-frequency luminosity, morphology, spectral index, and a
  defensible attempt at synchrotron-age identifiability.

Costs and risks:

- two multi-node production commitments;
- substantial temporary scratch use and rerun time;
- exact dynamical trajectories may not be byte-identical to the accepted
  historical runs. The design must either prove numerical identity under a
  matched source/configuration/decomposition/random-stream contract, recompute
  radio, X-ray, and truth products from the regenerated endpoints, or predefine
  quantitative equivalence tolerances before inspecting the new results;
- output minimization must not weaken restart or provenance safety.

### C. Matched Lossless Endpoint Reference

Recommendation: `ACCEPTABLE_ACCELERATED_SCOPE_FALLBACK`.

Use each accepted endpoint particle file to calculate the same instantaneous
lossless emissivity and raytrace it through the provisional common protocol.

Benefits:

- low post-processing cost;
- comparable method across all three cases;
- useful endpoint morphology, boundary, projection, and reference-luminosity
  surface.

Limitations:

- not a loss-aware PRAiSE observable;
- no synchrotron age;
- luminosity and high-frequency morphology omit source-history ageing;
- cannot satisfy the stronger wording of Aim 4 without an explicit thesis
  scope amendment.

### D. Stop The Radio Lane

Recommendation: `NOT_RECOMMENDED`.

This would leave a central required project-plan deliverable unfulfilled after
the three simulations and X-ray/truth surface are already complete.

## Recommendation

Proceed next with Alternative A, the G-LO recovery/method/value gate. Do not
yet ask Stas and Patrick to approve two production reruns: that would
presuppose both method viability and material scientific value.

If the G-LO gate shows that ageing materially changes the thesis-relevant
observables and the chunked workflow is feasible, escalate Alternative B to
Stas and Patrick as the material production decision. Otherwise adopt
Alternative C explicitly rather than quietly mixing methods.

The G-LO endpoint contains about `197,568` particles over `5,001` output
indices. One dense float64 particle-by-time field is about `7.9 GB` before
overheads; a naive multi-field path can plausibly exceed `100 GB`. The next
gate must therefore prove field selection, particle-ID chunking, deterministic
aggregation, checkpoint/restart recovery, and bounded intermediate storage.

## Data-Lifecycle Consequence

Do not compact the current radio-held surface further yet.

- Preserve the continuous G-LO histories.
- Preserve protected C-HI/C-LO endpoint particle files for the lossless
  fallback and provenance.
- If the later full-loss pathway succeeds, promote compact complete-history
  caches and final radio products before proposing deletion of superseded raw
  particle files.
- Any later deletion requires a new exact ledger and Barry approval.

## Scope Boundary

Goal 048 produced no radio maps, luminosities, age estimates, new PLUTO run, or
PBS submission. It did not mutate or delete remote data. Its scientific
conclusion is a fail-closed cross-case source gate plus a G-LO
recovery/method/value decision, not a negative result about radio physics.
