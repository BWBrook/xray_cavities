# X-ray Cavity Recovery Method Refinement

Date: 2026-07-23

Decision label:
`XRAY_CAVITY_RECOVERY_METHOD_REFINEMENT_GREEN`

## Result

Goal 045 passed all seven predeclared gates on the existing Goal 044 map
surface. It repairs the two downstream defects exposed by Goal 044 without
rerunning XRAiSE or PLUTO and without changing the preserved Goal 044
failed-closed evidence.

The production-pipeline validation surface is green for the two synthetic
fixtures at the three unique physical views and for direct-90 versus edge-90
equivalence on the accepted real C-HI endpoint. This result resolves the
X-ray-validation hold attributable to Goal 044. It does not itself authorize
lifecycle deletion; Goal 042 retention dependencies and the separately
approved Goal 043 execution ledger still govern any deletion.

## Method

The highest-deficit one percent of projected physical area is retained as a
high-purity seed detector, not as the cavity-area estimator. Seeds are selected
independently in the known negative-z and positive-z jet hemispheres without
using tracer truth.

Production support comes from a robust degree-6 two-dimensional Chebyshev
model of log X-ray intensity on normalized coordinates, fitted by SVD with
fixed lower-outlier clipping. Connected components are grown through a frozen
outer-annulus support threshold on the fitted-background deficit. Primary
components and secondary fragments remain explicit.

Degree-5/6/7 convergence, conditioning, blocked spatial cross-validation, and
a numerical knife-edge check are required. Smooth-null and one-sided-ablation
controls use an independent radial background rather than the fitted
polynomial.

Direct-90 and edge-90 products are conservatively mapped to a third symmetric
common grid before map or recovered-geometry comparisons. Truth comparisons
use physical cell area on the nonuniform projected grids.

## Observations

All seven gates passed:

- background stability: `18/18` fits converged, maximum condition number
  `257.5965365689359`;
- synthetic recovery: `12/12` side-angle rows;
- independent negative controls: `18/18`;
- common-grid equivalence: `3/3` cases;
- geometry resolution: `24/24` expected components;
- energy convention: `42/42` finite positive rows and `14/14` exact
  `pV`/`2.5pV`/`4pV` multiplier groups; and
- provenance: `40` map inputs plus all `9/9` required code/input roles.

Across the synthetic recovery rows:

- minimum area-weighted precision was `1.0`;
- minimum area-weighted IoU was `0.7904401533674832`;
- maximum centroid error was `1.8090761378638365 kpc`;
- maximum projected-area relative error was `0.20955984663251687`;
- maximum geometric-volume relative error was `0.28644070576568764`; and
- maximum secondary-fragment fraction was `0.0`.

For the real C-HI endpoint, direct-90 and edge-90 on the common grid had
normalized L1 `1.01176563906442e-10`, mask IoU `1.0`, and zero differences in
recovered area, centroid, and geometric-volume proxy.

## Interpretation

Observation: Goal 044 already certified projection conservation, native-axis
agreement, near-90 continuity, occupancy, determinism, and provenance.
Goal 045 now demonstrates stable two-sided recovery, resolved geometry,
common-grid method equivalence, independent negative controls, and honest
energy propagation on the same map evidence.

Inference: the end-to-end X-ray cavity production path is fit for the current
fixture-informed project validation and for retaining the Goal 041 synthesis
as accepted evidence. The earlier Goal 044 recovery failures were addressed by
separating detection from geometry and by comparing projection methods on the
same physical grid, not by relaxing the frozen truth tolerances after seeing
the result.

## Limits

This is not a general observational or publication-method certification.
Both synthetic fixtures informed the method design, and the real endpoint
comparison tests numerical method equivalence rather than truth recovery.
The degree-6 background may behave differently under instrumental PSF,
counting noise, more complex backgrounds, or arbitrary cavity morphology.

The tightest accepted margin is the axisymmetric 45-degree volume-proxy error
`0.28644070576568764` against the frozen `0.30` gate. A genuinely independent
fixture or adversarial methods audit remains appropriate before a
publication-facing recovery-method freeze.

The C-HI energy rows remain simulation-assisted pressure times a geometric
proxy volume. They carry the established `pV`, adopted `2.5pV`, and `4pV`
conventions and are not direct observational calorimetry.

## Operational Evidence

PBS job `775522.kunanyi-ohpc` / `xcav_refine` ended `F` with
`Exit_status=0`, walltime `00:00:30`, CPU time `00:00:25`, and empty stderr.
`Stageout_status=1` is retained as a scheduler caveat, but the requested
archive and logs were present at the stage root and were retrieved directly.

The retrieved archive SHA-256 is:

```text
462199cc4537cf987556c04961dd807e5a0a465ede40f0af46c1c2f34a4675a1
```

All internal archive checksums passed. The immutable retrieved archive and
logs plus the extracted review surface are under:

```text
docs/science/assets/xray_cavity_recovery_method_refinement_2026-07-23/
```

The archive's self-referential `archive_manifest.tsv` row records its own
pre-write size as `0 bytes`; the completed file is present and its final
SHA-256 passes. This is a nonmaterial packaging blemish, not a data-integrity
or scientific-result defect, and does not justify a rerun.

## Recommendation

Accept Goal 045 and close `Q-021` as answered. Lift the Goal 044
X-ray-validation hold in the lifecycle dependency ledger, while preserving
all independent radio, Level 3 gravity, publication-method, and explicit
Goal 043 deletion-authorization boundaries.
