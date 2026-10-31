# Native path lengths and shell emission: extraction design

Status: proposed for Claude's methodological review. No native-grid extraction
has been implemented or submitted by this note. This follows Correspondence
discussion 29, messages 2688 and 2696–2699, and the corrected Q-032 synthetic
shell experiments.

## Question and scope

Measure whether simulated shocked ambient gas fills the projected cocoon's
X-ray deficit, and separate this effect from background estimation and cavity
selection. Start with one quantitatively accepted cluster snapshot and one
accepted group snapshot at the same age, selected from the existing native
manifest before inspecting method performance. Extend only after geometry,
mask and brightness checks pass. Use retained outputs; no new PLUTO simulation.

The synthetic hot-shell ordering and overlapping mass-matched shell arms are
sensitivity results. Neither determines the correction for simulated shells.
Density and temperature averages alone cannot predict emission from a mixture:
integrate the adopted cellwise 1 keV emissivity before averaging or projection.

## Regions and validity

- Cocoon: full native cells with stored tracer promoted to float64 and
  `tr1 > 1e-3`, matching Q-029. Keep threshold-equality diagnostics.
- Ambient total: the exact complement `tr1 <= 1e-3` on valid fluid cells.
- Shocked ambient: the existing accepted, seeded entropy-excess component,
  restricted to ambient total. Reuse the calibrated thresholds, connected
  components, accepted axial fronts and Mach validity checks from Q-029.
- Unshocked ambient: ambient total minus shocked ambient only when the shock
  classification is quantitatively accepted. Missing/rejected shock regions
  remain unavailable with explicit status, never a zero-valued physical claim.

Retain the existing C-LO late-age and G-HI/50 restrictions. Cocoon and total
ambient projections can still be evaluated where shock classification fails,
provided source and fluid checks pass; this does not reinstate excluded
scientific inference. Do not tune shock thresholds to improve X-ray recovery.

## Projection and products

Reuse the retained render's exact axes, pixel edges, view transform, domain,
units and projection method. `xraise_grid_smoke.py` supplies direct-axis and
edge-overlap scalar projection primitives. For each region project its binary
indicator to a path length, and independently project its cellwise corrected
1 keV emissivity. Use the same density/temperature conversion and emissivity
convention as the accepted XRAiSE maps.

One NPZ per case/age/view should contain pixel axes/edges, path lengths in kpc,
component brightness in the retained map's units, and explicit validity flags.
Shock-dependent arrays must be absent or consistently marked unavailable when
invalid. A JSON sidecar binds source HDF5 identity and timestep, retained-map
hashes, native mask/calibration provenance, code hashes, definitions, units,
projection details and exclusions. Raw fields remain on Kunanyi.

Compact native summaries should report region volume and mass, volume-weighted
and emission-weighted density/temperature distributions, and integrated
cellwise emissivity. Keep current-state values distinct from changes relative
to initial fields. Avoid calling an initial-state comparison an evolved no-jet
counterfactual.

## Acceptance before extension

1. Reproduce accepted native region volumes and mask statuses without changing
   the Q-029 reference; verify zero cocoon/shocked-ambient overlap.
2. Check pixelwise cocoon plus total-ambient path length against the full-domain
   projection. Where shock classification is valid, check the ambient split.
3. Integrate path length times pixel area and recover native regional volume,
   allowing only a declared, measured clipping contribution and numerical error.
4. Require the sum of component brightness maps to reproduce an independently
   rendered whole-fluid brightness map; compare that to the retained map and
   explain any source or renderer difference before using it quantitatively.
5. Exercise analytic slabs and ellipsoids at 0°, 45° and 90°, grid refinement,
   threshold equality, invalid shock labels and deliberate source/axis mismatch.
6. Run the first native pilot in an allocation with measured peak memory and
   immutable output receipts; retrieve compact products for independent review
   before expanding to all selected ages.

The pilot resource request must follow a measured implementation smoke. The
earlier Q-029 run peaked near 41 GB, so the native extraction does not belong
on the 24 GB mini. Its scheduling must respect the current migration and the
already queued flux analysis. Detector adoption, topology changes and dependent
energetics remain separate decisions after these checks.
