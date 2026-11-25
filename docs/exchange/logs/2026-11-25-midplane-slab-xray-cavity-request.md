# Midplane slab test of projected X-ray cavity filling

Date: 2026-11-25.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`); Patrick's agent (`patrick-agent`) for context.
Status: supervisor-approved request for existing-output post-processing.
Source revision: `6c5838eee1f3c06b3a6d24849befec0f6a2632f0`.

## Question and requested calculation

Could bright gas in front of and behind the tracer-defined lobes be filling
the X-ray depression in projection? Recalculate the cavity area on the sky
after limiting the emitting cells to slabs around the x-z midplane, y = 0.
Compare three line-of-sight integrations of the same simulation snapshot:

1. Full available y extent: the existing full-depth reference.
2. Only cells, or portions of cells, within -30 <= y <= 30 kpc.
3. Only cells, or portions of cells, within -10 <= y <= 10 kpc.

For the primary comparison, look along y so the image plane is x-z and the
jet axis is z. These are physical y-coordinate cuts, not a rotation about
the jet axis, a sky-plane aperture cut or a selection by velocity.

Integrate the same X-ray emissivity prescription at the same photon energy
used in the current comparison:

```text
I_h(x,z,t) = integral from -h to +h of epsilon_X(x,y,z,t) dy
h = 10 kpc or 30 kpc
```

Use native cell widths and the intersection of a cell with the slab at each
slab face. Do not replace the integration by a single midplane slice, an
average emissivity, or an unweighted count of grid cells. Keep all emitting
gas inside each slab, including lobe gas and compressed/moving ambient gas.
Only the foreground/background outside the slab is removed.

## Matched detection and reference definitions

- Keep the image grid, sky aperture, component-size rule and 5% fractional
  depression cut fixed across the three depths. Use the same declared
  background-fitting prescription for each image; recompute its background
  consistently for that integration depth rather than subtracting the
  full-depth background from a truncated image. Report background profiles
  and unsupported fitting/extrapolation regions, since a refit can itself
  change the detected area. Produce matched time-zero slab images as a
  physical brightness/depression reference.
- The true lobe remains the binary full-cell set `tr1 > 1e-3`, with no tracer
  fraction weighting. Shocked or sound-wave gas outside this set must not
  enter the true lobe volume or projected lobe area.
- Retain the full-depth projected tracer lobe as the common recovery
  reference. Also show the slab-restricted tracer footprint and the fraction
  of full lobe area/volume retained in each slab. If a slab cuts through the
  lobe, provide separately labelled slab-matched completeness/purity as
  well, rather than silently changing the denominator or calling removed
  lobe material a detection failure. Projected area is the physical area of
  the union of tracer-intersecting sightlines, counted once per sky pixel.
- This request deliberately changes the three-dimensional emitting domain.
  It is a separate simulation-assisted diagnostic from the earlier request
  to exclude source sightlines only when fitting the background to an
  otherwise unchanged full-depth image. Preserve those results and the
  frozen detector/cohort scores; do not overwrite them with slab scores.

## Requested output and sequence

Start with the exposed G-HI/20 example, then apply the comparison to the
existing valid selected-age snapshots across C-HI, C-LO, G-HI and G-LO.
Reuse existing native outputs; retain the exclusion of G-HI 48--50 Myr and
flag cases where the search aperture or simulation boundary clips the lobe.

For each matched case and age, provide:

- Full-depth / +/-30 / +/-10 kpc brightness and deficit maps on a common
  x-z grid, with tracer and detected-cavity contours. State intensity scales
  and show matched initial-reference depressions where useful.
- A compact table of X-ray-selected area, tracer-overlap area, missed lobe
  area and false exterior area in kpc^2; completeness and purity; and slab
  lobe retention. Give both lobes separately and the bipolar physical sums.
- A short interpretation: does removing distant foreground/background
  emission restore the missing cavity area? Distinguish that effect from
  bright gas remaining within the slab, lost lobe material, background-fit
  changes and finite search-aperture limitations. Do not assume in advance
  that the masking will improve recovery or that all remaining fill is a
  shock.

Include the usual simulation setup and actual snapshot age with the results.
No new PLUTO simulation is requested. Barry should implement and return the
first matched maps/table before drawing a general conclusion.

## Delivery

This note records Stas's instruction for repository delivery to Barry's agent.
It reports no new measurement or submitted job and is not a private-board
post or an acknowledgement from either recipient.

Related instructions and results:

- [Source-excluded fits and energy partition](2026-11-24-source-excluded-backgrounds-and-energy-partition.md).
- [Current source-excluded comparison](../../science/source_excluded_background_results_2026-11-25.md).
- [Held-out area and volume definitions](../../science/heldout_xray_results_2026-11-24.md).
