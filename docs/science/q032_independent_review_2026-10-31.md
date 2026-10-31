# Q-032 synthetic harness: independent scientific review

Date: 2026-10-31
Reviewer: Codex (GPT-6)
Reviewed repository state: `fa175dbb`

## Decision

The harness is sufficient to reject the legacy one-percent-area selector as a
cavity detector and to justify running the retained-map ladder as a diagnostic
comparison. It is not sufficient to select or validate a production
replacement. The retained-map run should therefore return masks, topology,
aperture coverage and tracer comparisons without changing production volumes,
enthalpies or manuscript claims.

The main blockers to method adoption are an incorrect description of the rim
thermodynamics, the lack of an evolved counterfactual background for the
oracle rung, and unresolved compatibility between recovered masks and the
production topology gate. The committed result manifest also does not verify
after Git checkout, although a clean regeneration establishes that the
numerical tables themselves are reproducible.

Independent regeneration and parent-verified comparison receipts are retained
under `docs/science/assets/q032_independent_review_2026-10-31/`.

## Evidence and reproduced results

The input atmosphere checksum manifest verifies both vendored tables. A clean
stride-2 regeneration in temporary storage produced 1,024 per-side rows from
64 scenarios. All five regenerated result-manifest entries verified. The two
regenerated CSVs were record-for-record identical to the committed CSVs, and
both figures were byte-identical. The regenerated metadata differed in the
expected `git_commit` field because the review ran at `fa175dbb` rather than
the recorded build commit `134e31b`.

The focused test command

```text
.venv/bin/pytest -q \
  tests/test_xray_cavity_synthetic.py \
  tests/test_xray_cavity_method_ladder.py \
  tests/test_xray_cavity_production_caller.py \
  tests/test_q032_selected_age_method_ladder.py
```

returned `19 passed, 1 xfailed`. The strict expected failure is the production
caller's inability to recover a large synthetic cavity within 30%; the caller
tests also establish that production still invokes the legacy selector and
returns less than 5% of the large-cavity truth
(`tests/test_xray_cavity_production_caller.py:148-165`).

The central null result is supported directly:

| Rung | Null detections |
| --- | ---: |
| Legacy, observer background | 8/8 sides |
| Legacy, matched oracle background | 8/8 sides |
| Seed-and-grow, either background | 0/8 sides |
| Every tested deficit-threshold rung | 0/8 sides |

Thus the legacy algorithm is a forced area selector rather than a detector.
Its production-equivalent implementation retains the highest-deficit one per
cent of aperture area (`xray_cavity_method_ladder.py:103-132`), and its exact
mask equivalence to the production observer path is tested
(`tests/test_xray_cavity_method_ladder.py:44-56`).

Most reported evacuated-cavity medians reproduce. For the observer radial
null-calibrated threshold, however, the declared median over two atmospheres
and two views is not consistently the statistic printed in the note:

| Along-jet semiaxis (kpc) | Median revolution ratio, all 8 sides | Note value |
| ---: | ---: | ---: |
| 10 | 0.198 | 0.27 |
| 20 | 0.696 | 0.74 |
| 40 | 0.865 | 0.88 |
| 60 | 0.892 | 0.90 |
| 90 | 0.629 | 0.61 |

At 10 kpc, 0.27 is the median conditional on detection (six of eight sides),
not the stated unconditional median. The summary should specify one aggregation
rule and report detection frequency separately. This does not change the broad
ranking, but it precludes treating the printed table as a calibrated performance
estimate.

## Rim thermodynamics and mass assumption

The note and metadata describe the density-times-two rim as isothermal. The
code does something different. `Atmosphere.emissivity` divides temperature by
every supplied density factor (`xray_cavity_synthetic.py:45-55`), and the rim
passes `rim_density_factor=2` through that same function
(`xray_cavity_synthetic.py:185-199`). The implemented rim is therefore
pressure-matched with half the ambient temperature, not isothermal.

At 1 keV, the implemented rim-to-ambient emissivity ratio is approximately
3.29--3.54 across the sampled cluster radii but only 0.75--1.88 across the
group. An actually isothermal density-times-two rim would have ratio 4 in both
atmospheres under this emissivity law. Much of the reported cluster--group rim
contrast can therefore arise from the unstated temperature prescription. The
claim that realistic bright shocked shells impose the quantified recovery
loss is not established by this scenario. Real shocked gas is neither this
isobaric cool shell nor necessarily an isothermal shell.

The geometry is also not explicitly mass-conserving. Under a local
uniform-density approximation, aspect ratio 0.6 and equal axis growth of
`0.15a` give a shell volume of `0.796875` cavity volumes. At twice ambient
density its excess mass is therefore `0.796875 rho_amb V`, compared with
`0.99 rho_amb V` removed by the density-0.01 cavity: about 80.5% is rehoused.
This is a geometric local approximation, not an integration through the
stratified atmosphere. The defensible interpretation is a controlled contrast
sensitivity, not a physical shocked-shell model.

## Background, topology and viewing scope

The synthetic oracle is the exact cavity-free map of the same static initial
atmosphere. A real time-zero render is not the equivalent counterfactual for a
10--50 Myr evolved jet run: hydrostatic drift, boundary transport, weak waves,
shocks and secular atmosphere changes would all enter the difference. The
oracle results show that the selection and volume estimator can recover the
idealised projected spheroid; they do not validate time-zero subtraction on
retained simulations.

The retained-map runner currently applies legacy, observer seed-and-grow, and
fixed observer thresholds 0.05, 0.10 and 0.20
(`build_q032_selected_age_method_ladder.py:64-72`). It has neither an oracle
background nor a real-map null calibration. The synthetic null threshold is
itself calibrated on noiseless initial profiles and measures background-model
error only (`build_q032_synthetic_harness.py:71-76`); it is not a false-positive
calibration under projection structure, Poisson noise or evolved dynamics.

Topology is still a production blocker. Ideal oracle seed-and-grow commonly
recovers the touching bipolar pair nearly exactly but labels the union
`connected_cross_midplane_component`. The current production energy path is
quantitative only for `two_separate_components`
(`build_selected_age_xray_cavity.py:119-129`). Splitting the recovered union at
`z=0` produces useful diagnostic per-side volumes, but it does not by itself
justify bypassing that gate.

The 0 and 45 degree synthetic views are sufficient for the spherical
atmosphere and axisymmetric spheroids because 90 degrees is identical to zero.
They test azimuth-dependent chord length through the square box, not
inclination, realistic cocoon asymmetry or azimuthal robustness. All retained
0/45/90 degree views remain necessary.

## Manifest defect

The committed `results/manifest.sha256` fails on exactly these files:

| File | Recorded SHA-256 | Checkout SHA-256 |
| --- | --- | --- |
| `null_calibrated_thresholds.csv` | `1c47040f199efab0e66b1d8c2eb322363f8f0bc0c7397bb8604484a2ae68218a` | `8a5e31c9e8e6166985956116de50fbd79a04bd1980c2242bbcf815dc97f30731` |
| `synthetic_recovery.csv` | `31b623ec313e3265457ee8b2550f727537245ce4a78d91cc21f102b223cd089f` | `a160c68322218213dffde5c904a7ae7543d262d2f157ad2528995a1d46297878` |

The builder writes CSV with CRLF and hashes those bytes before commit
(`build_q032_synthetic_harness.py:133-159`). Git stores/checks out the text as
LF. Converting the checkout LF bytes back to CRLF reproduces both recorded
hashes exactly, and a clean regeneration reproduces every CSV record. This is
a provenance-format defect, not evidence of numerical mutation. The durable
remedy is to write canonical LF before hashing or declare an explicit Git
attribute, then regenerate the manifest.

## Recommendation

Run the retained-map ladder as a blinded diagnostic and preserve every method,
view, rejected topology and aperture-coverage result. Do not promote a method
or refresh dependent energetics until:

1. the rim prescription is labelled correctly and tested against at least a
   physically plausible temperature/mass-conserving alternative;
2. observer thresholds are calibrated on relevant evolved null or negative
   controls, and any time-zero background is labelled as a baseline rather
   than an oracle;
3. the topology rule for midplane-connected but bilaterally recoverable masks
   is decided and validated; and
4. the result aggregation and checksum manifest are corrected.

Further independent scientific review would materially affect method adoption,
but it is not needed before the diagnostic retained-map ladder run.
