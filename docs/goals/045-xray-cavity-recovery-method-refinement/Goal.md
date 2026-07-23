# Goal 045 - X-ray Cavity Recovery Method Refinement

## Objective

Repair the downstream recovery gates exposed by Goal 044 without rerunning
XRAiSE or PLUTO. Use the existing Goal 044 synthetic and real C-HI maps to
distinguish X-ray deficit-core detection from projected cavity geometry and
hybrid energy inference.

## Required Method

- Preserve Goal 044 as an immutable failed-closed result.
- Retain the highest-deficit one-percent physical-area tail as a
  high-purity seed detector, not as a cavity-area estimator.
- Select seeds independently in the known negative-z and positive-z jet
  hemispheres without using tracer truth.
- Fit a robust degree-6 two-dimensional Chebyshev model to log X-ray
  intensity on normalized coordinates using SVD least squares and fixed
  lower-outlier clipping. This is a
  `fixture_informed_pipeline_validation_background`, not a general
  observational background model.
- Demonstrate that the background is not a numerical knife-edge with
  predeclared degree-5/6/7 convergence, conditioning, blocked spatial
  cross-validation, and stability checks.
- Grow each seed through connected fractional-deficit support defined by a
  robust outer-annulus threshold on the polynomial-background deficit.
- Keep primary side components and secondary fragments explicit.
- Use area-weighted tracer comparisons on the nonuniform projected grids.
- Mark unresolved geometry and energy as not estimable rather than numeric
  zero.
- Recompute direct-90 and edge-90 recovery on a third symmetric common grid
  over their shared physical support.

## Predeclared Validation Gates

### Synthetic recovery

Evaluate two fixtures at the three physically distinct angles 0, 45, and
90 degrees. Direct/edge and 89.9/90 pairs are numerical equivalence checks,
not independent replicates.

For every fixture and angle:

- detect both independently tested jet sides;
- recover no midplane-crossing primary component;
- area-weighted precision at tracer `>=5e-3` at least `0.90`;
- area-weighted mask intersection-over-union at least `0.50`;
- primary centroid error at most `10 kpc`;
- projected-area relative error at most `0.25`;
- geometric-depth proxy volume relative error at most `0.30` against the
  same estimator applied to projected tracer truth; and
- secondary-fragment area at most ten percent of the primary side component.

A smooth-background control must detect zero sides. A one-sided ablation
control must detect exactly the retained side. Both controls must use an
independent radial background rather than the fitted degree-6 background.

### Common-grid equivalence

- corrected-map normalized L1 residual at most `1e-8`;
- identical side and topology class;
- area-weighted mask IoU at least `0.99`;
- total recovered-area relative difference at most `0.01`;
- primary centroid difference at most `1 kpc`; and
- total geometric-proxy volume relative difference at most `0.05`.

### Geometry and energy

Geometry is resolved only when a component spans at least three distinct
horizontal and vertical centres, has full-rank covariance, and has a minor
semiaxis larger than one local cell width. Resolved components must produce
finite positive `pV` and exact `2.5pV` and `4pV` multipliers at relative
tolerance `1e-12`.

## Boundaries

- Existing Goal 044 maps only; no XRAiSE or PLUTO rerun.
- No threshold or tolerance search after the Goal 045 evaluation begins.
- No lifecycle deletion, movement, truncation, or overwrite.
- No claim of general observational validity under noise, PSF convolution,
  background misspecification, or arbitrary morphology.
- Both synthetic fixtures informed this pipeline-validation design. A later
  independent fixture or adversarial methods audit is required before any
  publication-facing method freeze.
- A submitted evaluation-only PBS job triggers the normal wake-and-stop rule
  after queued or running verification.
