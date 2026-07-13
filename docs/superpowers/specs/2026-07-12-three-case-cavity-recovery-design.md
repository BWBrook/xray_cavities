# Three-case endpoint cavity recovery and truth-alignment design

## Objective

Recover projected X-ray cavity candidates for the accepted 50 Myr C-HI,
C-LO, and G-LO endpoints at 0, 45, and 90 degrees, then compare those
observer-side candidates with independently extracted Level 1 injected-energy
and Level 2 tracer-lobe truth. This is a prove-out analysis surface, not a
final observable or publication claim.

## Evidence separation

The analysis has three explicit layers:

1. **Observer-side recovery:** corrected X-ray maps and physical coordinate
   axes only. Tracer arrays do not influence smoothing, thresholding,
   component selection, or topology classification.
2. **Simulation-truth validation:** projected tracer masks at thresholds
   `1e-3`, `5e-3`, and `1e-2`, plus full-grid Level 2 volumes and energies.
   These are used only after the X-ray candidates are fixed.
3. **Hybrid energetics context:** tracer-shell ambient pressure from the
   existing cavity extractor is combined with X-ray-derived volume
   sensitivities. These values are labelled hybrid proxies, not
   observer-only measurements.

## Observer-side protocol

- Use a common 180 kpc circular background field and a nested 120 kpc circular
  candidate aperture. The outer field supplies ambient-halo information; the
  inner aperture prevents map or field boundaries from becoming cavity
  candidates.
- Estimate the smooth X-ray background from the tracer-blind azimuthal median
  profile in 5 kpc radial bins, smoothed along radius with a 10 kpc Gaussian.
  Retain 4/8 kpc bins and 8/15 kpc smoothing as sensitivity checks. This
  removes the dominant radial halo gradient without imposing a lobe shape.
- Define fractional deficit as `(background - corrected) / background` where
  the background is finite and positive.
- Define the base candidate mask as the most X-ray-deficient 1 percent of
  projected physical area inside the common region. Retain 0.5, 2, 3, and 5
  percent as threshold sensitivity checks. Physical-area weighting is required
  because projected pixel areas differ across views.
- Use 8-connected components and reject components below 25 kpc2. This gate is
  converted to pixels using each map's physical cell area.
- Do not force a two-lobe split. Report the number of retained X-ray
  components and whether any component crosses projected `z=0`.

## Validation metrics

For each case and view, report candidate area, component count, integrated and
mean fractional deficit, and topology class. Against each projected tracer
threshold, report intersection-over-union, Dice coefficient, X-ray-mask
precision, and tracer-mask recall. These metrics are validation diagnostics;
they do not retroactively alter the X-ray mask.

## Volume and energy sensitivities

For each retained X-ray component, use physical-area-weighted second moments
to estimate projected semiaxes `a >= b`. Report three line-of-sight depth
assumptions:

- `minor_depth`: `c=b`
- `geometric_depth`: `c=sqrt(a*b)`
- `major_depth`: `c=a`

The corresponding ellipsoid volumes bracket projection uncertainty. The
geometric-depth value is the labelled central proxy, not an identified true
volume. Case-level ambient pressure is the volume-weighted mean of the two
tracer-shell pressure estimates from the existing cavity extractor. Report
`pV`, adopted `2.5pV`, and `4pV` for every depth assumption and compare the
central proxy with Level 1 and Level 2 energy and volume truth.

## Remote extraction

One serial Kunanyi post-processing job will run the existing
`pluto_h5_truth_extract.c` and `pluto_h5_cavity_stub_extract.c` helpers against
the accepted C-HI, C-LO, and G-LO endpoint HDF5 files. It will create compact
CSV/text products and a stable file-list archive. It will not run PLUTO,
XRAiSE, PRAiSE, radio synthesis, or a new production simulation.

The wrapper must preflight all endpoint paths, timestep groups, required
datasets, and staged hashes before extraction. After submission and queued or
running verification, the PBS stop rule applies.

## Acceptance criteria

- Synthetic tests demonstrate physical radial-bin invariance across different
  pixel spacings, recovery of an injected bipolar deficit, exclusion of a
  field-edge artefact, and tracer blindness of the X-ray mask.
- All nine accepted maps produce finite metrics without empty-support failure.
- Threshold and smoothing sensitivities are retained in machine-readable
  outputs.
- Remote Level 1/2 and ambient-pressure products validate for all three cases.
- The package distinguishes observation, inference, assumptions, and active
  caveats; no final topology or observable claim is made.
