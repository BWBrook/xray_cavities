# Fitting the X-ray background outside the simulated source

**Question.** Does the radial 5%-deficit outline recover more of the lobe when sightlines through the source are excluded from the brightness fit? The outcome for the original image-only rule is already known. Stas requested a retrospective comparison using native tracer and velocity information. This specification was written before inspecting the new fits. [Supervisor request](../exchange/logs/2026-11-24-source-excluded-backgrounds-and-energy-partition.md) · [Published DET-05 reference](heldout_xray_results_2026-11-24.md)

## Images and comparisons

Start with the three exposed G-HI/20 projections (19.999614 Myr). Carry the same settings to the 54 DET-05 science views from 18 case-ages and the 12 initial controls. The four runs cross cluster/group atmospheres with labelled powers of 2 × 10⁴⁵ and 2 × 10⁴³ erg/s. Each production mesh contains 960 × 960 × 1,014 cells. Use the existing noiseless 1-keV, redshift 0.05, retained-linear whole-brightness image at each side-on azimuth (0°, 45°, 90°) and the native cell and sky edges bound to that image. G-HI/20 is reported separately. The boundary exclusion of G-HI at 48–50 Myr stands. [Case register, grid and native times](assets/xray_prediction_seal_2026-11-23/native_inputs.csv)

The reference is the **image-only radial 5%** rule in DET-05. For G-HI/20 its counterpart is the exact-projection refit in the exposed comparison. First reproduce the original outline on each image pixel for pixel. Then change only which pixels contribute to the radial fit.

| Fit | Exclude these lines of sight |
| --- | --- |
| Original | None |
| Tracer | Any positive projected path through current cells with stored tracer, promoted to double precision, strictly above 0.001 |
| Speed | Any positive projected path through a current cell with three-component speed ≥100 km/s, irrespective of tracer |
| Speed sensitivity | Repeat the independent speed mask at 30 and 300 km/s |

Use the established side-on projection and positive physical overlap. Apply zero padding to every mask. Keep tracer and speed exclusions independent. A slow lobe sightline left in the speed fit is counted explicitly. Fit exclusion never changes the pixel brightness supplied to the detector. The earlier ambient-emissivity replacement and the seed/grow rule answer different questions. The target for an initial control is empty by the DET-05 definition; a physical nozzle footprint at time zero still participates in the fitting exclusion.

## Radial support and continuation

Use the original 180-kpc circular fitting region, 5-kpc annuli, unweighted median of finite positive pixel-centre brightnesses, and Gaussian radial smoothing with 10-kpc sigma. Retain the original radial bin grid after exclusion. Record counts, physical areas and occupied angular sectors before and after masking. Divide each annulus into twelve 30° sectors. Accept its retained median with at least eight pixels and three occupied sectors, each minimum capped at the original available count. This preserves the original rule when nothing is excluded. Retained-sector counts describe angular sampling; they do not establish that the gas is in equilibrium.

Interpolate unsupported interior bins linearly in brightness between measured bins. For an unsupported centre use the nearest measured median as primary. Repeat with a log-brightness slope anchored at the first measured bin and fitted to the innermost three supported medians (two when only two exist). Hold the outer profile at the last supported median. Distinguish measured bins, bracketed interpolation, central extrapolation and outer extrapolation in the outputs. Report insufficient support or an undefined continuation explicitly. Count such cases separately from a defined fit whose outline is empty.

## Scoring and interpretation

Apply each completed background to the same full image using the original fractional deficit strictly above 5%, a 120-kpc search aperture, 8-connected components of at least 25 kpc² and separate positive and negative jet sides. Report physical areas of the target, selection, overlap and false exterior, completeness, purity, aperture clipping, nondetections and the exact-edge axisymmetric volume divided by native lobe volume. Sum side areas and volumes before forming a bipolar ratio. Keep every eligible side. The DET-05 cut of 75% completeness, 95% purity and no aperture contact is a descriptive comparator for these fits. The frozen scores and their status are preserved.

Compare each new outline with its own original view, including truth beyond the aperture. Record the exterior selection relative to the initial brightness image, the retained area whose sightlines intersect pressure or density changes of at least 1% relative to time zero where the native reduction permits, and boundary and projection coverage flags. These last indicators diagnose possible contamination of the fitted atmosphere. Either a boundary disturbance or internal flow can change pressure or density. No shock identification or three-dimensional filling measurement follows from these images.

The review bundle should show the full image, the two fitting exclusions, annular support and original and new profiles, deficits and outlines for the same sky coordinates. Individual target rasters, held-out truth contours and review correspondence stay in the private archive. Patrick’s review concerns the retained support, the speed definition, inward continuation, and how far the geometry supports the physical interpretation.
