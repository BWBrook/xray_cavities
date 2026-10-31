# Native path lengths and shell emission: extraction design

Status: accepted by Claude in message 2718; pre-pilot table check adds a parallel
clamp sensitivity. No native-grid extraction
has been implemented or submitted by this note. This follows Correspondence
discussion 29, messages 2688 and 2696–2699, and the corrected Q-032 synthetic
shell experiments.

## Question and scope

Measure whether simulated shocked ambient gas fills the projected cocoon's
X-ray deficit, and separate this effect from background estimation and cavity
selection. Start with C-HI and G-HI at 40 Myr, the latest common high-power age
accepted as quantitative bilateral in the retained Q-029 closeout. This choice
was fixed on 31 October before inspecting the new 60-view detector results.
Bind the exact case-specific source manifest rows in staging. Extend only after geometry,
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

## Initial-state decomposition and declared metrics

Project both current emissivity and case-specific initial emissivity through
each current region mask. Retained output zero is already nozzle-initialized;
do not reuse one atmosphere's baseline across HI/LO unless the relevant fields
are proved identical. Cache each required baseline once. The resulting
partition is Eulerian: it compares the same cells, not the histories of the
same gas parcels. For valid complete regional partitions, require per pixel

`B_t - B_0 = delta_B_cocoon + delta_B_shocked + delta_B_unshocked`.

The summed initial regional maps provide a matched-axis `t0_baseline`, not an
evolved no-jet control. No sign is imposed on any regional change. Tracer-selected
gas can brighten, and shocked ambient can dim in the chosen band. The unshocked
term includes uplift, waves, rarefaction and sub-threshold shocks as well as
boundary/numerical evolution; it supplies no upper or lower bound on a no-jet
counterfactual.

Before examining detector results, declare these budgets for each side/view,
on (a) the projected cocoon footprint and (b) that footprint intersected with
the 120 kpc candidate aperture. Report the full aperture separately to expose
off-footprint rims. Integrals include pixel area. Preserve signed net change
and positive/negative parts of every regional map. Define cocoon loss
`D_coc = integral max(-delta_B_cocoon, 0) dA`, cocoon brightening analogously,
and shell brightening `E_sh = integral max(delta_B_shocked, 0) dA`.
Report `E_sh / D_coc` and `integral delta_B_shocked dA / D_coc` only when
`D_coc > 0`; otherwise mark undefined. These aggregate filling diagnostics
can exceed one and do not assert pixel-by-pixel cancellation. Also retain the
spatial change maps and unshocked-region budget on the same support.

Report initial/current mass differences through these same masks, including
positive, negative and net terms, with whole-domain partition closure. They
are signed regional mass changes, not proof that cocoon-displaced material
entered the shell. Preserve regional per-pixel emission-weighted temperature;
mark undefined when the emissivity denominator is non-positive and retain
negative/nonfinite-emissivity diagnostics.

## Emissivity-table coverage

Direct inspection of the retained runtime tables on 31 October verified:

| Table coordinate | Minimum | Maximum |
| --- | ---: | ---: |
| APEC temperature (keV) | 0.01 | 10 |
| APEC redshift | 0.01 | 10 |
| Gaunt temperature (K) | 1e5 | 1e13 |
| Gaunt frequency (Hz) | 1e16 | 1e19 |

The exact table hashes and inspection evidence are in
`docs/exchange/logs/2026-10-31-tpac-access-and-native-design-review.md`.
The accepted renderer linearly extrapolates outside these ranges and preserves
finite negative corrected emissivity. Preserve that convention for reproduction.
For initial and current fields separately, report per-region out-of-range cell
counts, volume fractions, signed brightness contributions and fractions of
absolute brightness, plus negative and nonfinite values before sanitization.
Check all interpolation coordinates, not only temperature. The pre-pilot check
in `q031_emissivity_extrapolation_2026-10-31.md` finds a positive rising factor
through 20 keV, a turnover near 89 keV, and negative extrapolation above
544.71 keV. Include a separately labelled clamp-to-edge sensitivity in the same
pilot, applying each table's own coordinate bounds to both current and initial
fields. Keep masks and projection identical. It must not replace the retained
convention or be treated as a physical uncertainty bound.

## Acceptance before extension

1. Reproduce accepted native region volumes and mask statuses without changing
   the Q-029 reference; verify zero cocoon/shocked-ambient overlap.
2. Check pixelwise cocoon plus total-ambient path length against the full-domain
   projection. Where shock classification is valid, check the ambient split.
   Reproject the native tracer maximum alongside path length; compare strict
   support with the retained TSV mask, recording mismatch count/area and maxima
   near the cutoff. Unexplained mismatches stop quantitative use; threshold
   serialization differences must be separately demonstrated and bounded.
3. Integrate path length times pixel area and recover native regional volume,
   allowing only a declared, measured clipping contribution and numerical error.
   Independently compare the three ellipse depths and both half-plane revolution
   estimates on the native footprint. Each half uses `2*pi*integral |u| dA`;
   their mean is the symmetrized full-footprint estimate `pi*integral |u| dA`.
   Use exact pixel-edge moments, especially across u=0, and show sensitivity to
   partial-pixel support/bin refinement. These are shape estimators, not assumed
   true volumes for asymmetric cocoons.
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
