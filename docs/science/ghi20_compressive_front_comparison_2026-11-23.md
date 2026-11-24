# The G-HI/20 compression front and the X-ray cavity outlines

**Simulation and observation.** The high-power jet in group atmosphere `002031` has bipolar labelled power $2\times10^{45}$ erg s⁻¹, speed $0.1c$, 15° half-opening angle and 0.75-kpc injection height. Its 960 × 960 × 1,014 Cartesian grid spans 400 × 400 × 500 kpc, with cell widths from 0.05 kpc at the centre to 1.69 kpc transversely and 2.10 kpc axially at the outer edges. The HLLC solver used CFL 0.33 and an initial step of $10^{-5}$ code units. Native single-precision fluid outputs were scheduled every 306.60139379 code units. The compared output is `Timestep_20`, code time 6131.909618, actual age **19.9996143 Myr**. The original 1-keV maps use redshift 0.05 and side-on azimuths 0°, 45° and 90° about the jet axis. [Frozen front definition](ghi20_compressive_front_contract_2026-11-23.md) · [Frozen observer comparison](compressive_front_observer_protocol_2026-11-23.md)

Claude reproduced the contour distances and emission budgets from the published tables. Patrick’s review of the three-dimensional front definition and its interpretation remains open. All measurements here use the previously exposed development snapshot. [Independent review](../correspondence/thread-0029.md#message-3731--claudemini-claude-fable-52--evidence) · [Method review request](../exchange/logs/2026-11-23-ghi20-compressive-front-method-review.md)

## Do the lateral orange arcs follow the independent front?

**The radial background fit creates the broad apparent deficits.** Beyond the projected lobe, the original orange arcs select sightlines whose pooled 1-keV brightness has barely changed since time zero. The fitted background sits 5.7–8.5% above the initial brightness there. A direct comparison of each pixel with its own initial brightness finds a decline exceeding 5% on just 0.56% of the exterior arc area at 45° and on none at 0° or 90°. This check uses whole-sightline brightness and is independent of how the compressing gas is identified. It measures projected change and leaves the distribution of gas along each sightline unresolved. [Complete exterior arc measurements by hemisphere and view](assets/compressive_front_observer_2026-11-23/exterior_arc_background_check.csv)

| Side-on azimuth | Exterior arc brightness change since time zero | Original fitted background above time-zero brightness | Exterior area that dimmed by more than 5% |
| --- | ---: | ---: | ---: |
| 0° | +0.017% | 5.67% | 0% |
| 45° | +0.015% | 8.02% | 0.56% |
| 90° | +0.109% | 8.49% | 0% |

Each brightness percentage compares sums over both hemispheres weighted by physical pixel area. The last column compares individual pixels, then sums the area of those that dimmed.

The most conspicuous arcs, at 0°, sit **25–26 kpc outside** the edge of the dominant compressive layer at the median contour position in either hemisphere. Their median separations span 25.2–26.2 kpc across the four native definitions. The projected compression occupies only **0.60–0.65%** of the lateral orange area in that view. Across all six sides and views, **91.4–99.4%** of that area has no sightline intersecting either the dominant or other qualifying compression components. The selected layer reaches roughly 45 kpc from the jet axis and 105 kpc along it. All three independent sky projections recover its native volume of 103,965 kpc³. No qualifying component touches the boundary at the primary settings. [Area overlaps](assets/compressive_front_observer_2026-11-23/front_sightline_overlap.csv) · [Native definition, controls and limitations](assets/ghi20_compressive_front_native_2026-11-23/README.md)

| Side-on azimuth | Hemisphere | Signed median arc–front distance (kpc) | Median absolute distance (kpc) | Arc length within one native cell | Lateral orange area intersecting the front |
| --- | --- | ---: | ---: | ---: | ---: |
| 0° | Negative z | +26.12 | 26.12 | 11.69% | 0.60% |
| 0° | Positive z | +25.47 | 25.47 | 12.51% | 0.65% |
| 45° | Negative z | −0.45 | 4.43 | 0.57% | 8.18% |
| 45° | Positive z | −0.53 | 4.76 | 0.56% | 8.58% |
| 90° | Negative z | +0.83 | 2.50 | 2.04% | 8.14% |
| 90° | Positive z | +0.83 | 2.50 | 1.50% | 7.92% |

A small signed median at 45° or 90° conceals lengths on both sides of the front. In the 45° map more than half the arc perimeter lies over one native cell inward and about 46% lies over one cell outward. Within one projected sky pixel the apparent agreement rises to 30–31% there, reflecting the 0.59-kpc sky binning. All midpoints within one native resolution element are near the exterior-facing projected edge. None meets this criterion at a hole in the footprint. The broad orange arcs do not delineate this compressive surface in any of the three maps. Some edges meet locally; the overlap of the shell with a sightline through the lobe poses a separate emission question. [Complete signed contour distributions and sensitivities](assets/compressive_front_observer_2026-11-23/front_contour_separations.csv) · [Geometry comparison receipt](assets/compressive_front_observer_2026-11-23/geometry_comparison_receipt.json)

![The 0-degree raw brightness, radial fractional deficit and independent compression components. Orange traces the 5% deficit outline, blue seed/grow, green the full lobe and magenta the dominant front.](assets/compressive_front_observer_2026-11-23/00deg_front_overlay.png)

The overlays use the same brightness and deficit scales; the colour bars indicate values beyond their displayed limits. The dashed circle marks the 120-kpc search aperture. Distances use the complete rectangular pixel edges. The qualifying native width is the local effective cell length along the three-dimensional gradient of log pressure relative to the initial gas, averaged along the ray through the selected layer. An independent brute-force segment calculation reproduced all six signed medians. [45° overlay](assets/compressive_front_observer_2026-11-23/45deg_front_overlay.png) · [90° overlay](assets/compressive_front_observer_2026-11-23/90deg_front_overlay.png)

## What the compressed gas changes in the X-ray image

On lobe sightlines missed by the original outlines, **ambient gas brightens by 1.68–2.56 times the lobe's own loss of X-ray emission**. The dominant compressive layer supplies 18–20% of that ambient gain. Gas outside the layer adds 1.35–2.09 times the lobe decrement, integrated along the same sightlines. The lobe plus all intervening gas is therefore 12–24% brighter at 20 Myr than at time zero on these missed sightlines. Over the *full* projected lobe, including sightlines the outlines detected, ambient brightening offsets 72–78% of the lobe decrement. The component sums do not locate the gas outside the layer along the line of sight. [Pooled component and whole-sightline budgets](assets/compressive_front_review_2026-11-24/pooled_emission_budget.csv) · [Per-side integrals](assets/compressive_front_observer_2026-11-23/emission_regions.csv)

| Side-on azimuth | Lobe decrement offset on blue-missed sightlines | Lobe decrement offset on orange-missed sightlines | Front brightening / current brightness on exterior orange area |
| --- | ---: | ---: | ---: |
| 0° | 47.43% | 32.84% | 0.00068% |
| 45° | 49.48% | 49.23% | 0.193% |
| 90° | 44.95% | 47.07% | 0.105% |

Here the numerator is current minus initial emission from the **current compressive-layer ambient cells**. The first two columns divide by the intrinsic loss from current `tr1 > 0.001` lobe cells on **missed** tracer sightlines, pooling the two hemispheres before division. The layer's volume-weighted effective native cell size along the pressure gradient is 0.320 kpc. The physical thickness of the layer can span several cells. The earlier 39–84% statistic divides **speed-selected** ambient brightening on **selected** sightlines by the fitted-background-minus-current observed deficit there. Expressed against the lobe’s own decrement on those selected sightlines, that earlier measure was 37–44%. [Native cell-size measurement](assets/ghi20_compressive_front_native_2026-11-23/native_projection_totals.csv) · [Earlier reconciliation](turn18_review_reconciliation_2026-11-11.md)

The 0° arc lies close to the 5% selection threshold. The difference between the area-integrated original radial background and current brightness is **5.35%** of that background. Restoring the front-associated ambient cells to their initial emissivity lowers the integrated arc brightness by only **0.00068%**. Refitting the background to the altered image lowers the integrated background over that same arc by **0.585%**. All the original exterior arc area remains selected with the fixed background. With the refit, only **15.8%** remains above threshold and selected. The corresponding fractions after refitting are 33.8% at 45° and 46.7% at 90°. These figures cover the complete arcs. On the four previously selected 0° profile rows, pixels outside both the lobe and front have a maximum original deficit of 5.58% and a median background drop of 0.64%. [Full-area threshold and selection check](assets/compressive_front_observer_2026-11-23/exterior_arc_background_check.csv) · [Profile-row thresholds](assets/compressive_front_review_2026-11-24/exterior_arc_threshold_margin.csv)

The threshold crossing accounts for the change in inferred volume. On the same altered 0° image, the original radial background gives **4.11** times the native lobe volume and the refitted background gives **1.08**. The refit still misses 43.6% of the projected lobe area. Comparing the refitted outlines before and after emissivity replacement, selected area outside the lobe falls from 7,229 to 1,170 kpc², purity rises from 44.7% to 84.5%, and completeness rises from 51.6% to 56.4%. The other two views give ratios of 0.65 and 0.85 after the same treatment. [All 60 side, method and treatment results](assets/compressive_front_observer_2026-11-23/replacement_recovery.csv)

| Azimuth | Outline | Exact image, original background | Replacement, original background | Exact image, refitted | Replacement, refitted | Refitted completeness, before → after |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 0° | Orange | 3.984 | 4.108 | 3.981 | 1.082 | 51.6% → 56.4% |
| 45° | Orange | 1.020 | 1.111 | 1.018 | 0.647 | 49.8% → 53.4% |
| 90° | Orange | 1.091 | 1.191 | 1.089 | 0.847 | 60.4% → 63.5% |
| 0° | Blue | 0.678 | 0.729 | 0.678 | 0.734 | 67.8% → 71.8% |
| 45° | Blue | 0.493 | 0.574 | 0.493 | 0.535 | 55.1% → 57.8% |
| 90° | Blue | 0.622 | 0.681 | 0.622 | 0.653 | 64.4% → 67.2% |

The four middle columns give summed symmetrised revolution volume divided by the summed native lobe volume. All baseline and replacement estimates use a common exact-edge projection. The original backgrounds were fitted to the historical images. The separate refitted arms each derive a fresh background from their exact-edge image. Replacing the front and refitting improves orange completeness in every view here, yet moves the 45° and 90° inferred volumes below their native values. The procedure uses the native front and its initial gas fields. A general claim about observer performance requires a different test. [0° replacement maps](assets/compressive_front_observer_2026-11-23/00deg_front_replacement.png) · [45° maps](assets/compressive_front_observer_2026-11-23/45deg_front_replacement.png) · [90° maps](assets/compressive_front_observer_2026-11-23/90deg_front_replacement.png)

The profiles plot raw brightness, the original radial background and same-cell replacement along twelve predetermined rows. They also give lobe and front path lengths and the front’s current-minus-initial brightness. Summing all three independently measured emission components reproduces every original sky pixel in both epochs to $1.49\times10^{-14}$ of the sum of the absolute terms. A separate integration reproduced 192 regional component totals. The final and geometry-only runs generated identical contour tables and overlay files. [0° profiles](assets/compressive_front_observer_2026-11-23/00deg_transverse_profiles.png) · [45° profiles](assets/compressive_front_observer_2026-11-23/45deg_transverse_profiles.png) · [90° profiles](assets/compressive_front_observer_2026-11-23/90deg_transverse_profiles.png) · [All 7,496 profile samples](assets/compressive_front_observer_2026-11-23/transverse_profiles.csv.gz) · [Final receipt and hashes](assets/compressive_front_observer_2026-11-23/comparison_receipt.json)

## How far the X-ray arcs extend beyond the lobes

The development image has a 5% brightness-deficit outline (orange) and a seed/grow outline (blue). The orange arcs include pixels outside the full projected lobe. At 0° the extralobe orange selection covers 3,611 and 3,618 kpc² in the negative and positive jet hemispheres. The blue selection includes 0.00 and 0.42 kpc² outside the lobe. The table measures exact distances from the exterior orange arc faces to the full projected lobe boundary, weighted by physical contour length. A positive sign means the face lies outside the lobe. [Per-side geometry](assets/compressive_front_observer_2026-11-23/original_geometry.csv) · [Signed distance distributions](assets/compressive_front_observer_2026-11-23/original_contour_to_lobe.csv)

| Side-on azimuth | Negative-z arc median (kpc) | Positive-z arc median (kpc) | Negative-z lateral profile (kpc) | Positive-z lateral profile (kpc) |
| --- | ---: | ---: | ---: | ---: |
| 0° | +36.56 | +34.74 | −71.52 | +71.52 |
| 45° | +14.37 | +14.44 | −1.88 | +0.03 |
| 90° | +13.95 | +14.52 | −2.28 | +0.03 |

The lateral profiles use the maximum total extralobe orange width at fixed z. The strongest cross-section under this rule is near the equatorial plane in the rotated views. The maximum integrated lobe-path profiles fall at −68.47 and +67.88 kpc in all three views. These cross-sections were selected using the exposed observer and tracer products before the new native front was available. [Profile locations](assets/compressive_front_observer_2026-11-23/profile_positions.csv)

## Source and control checks

The observer inputs match the three original binary map hashes and the retained native producer receipt. Across the three views the six original outlines, twelve current-image masks with fixed or refitted backgrounds, and twelve masks after replacement of the original speed-selected ambient gas all reproduced exactly. The earlier speed-selected calculation supplies a positive control for the replacement code. On this control the largest pixelwise discrepancy in the current brightness partition, divided by the sum of the absolute terms, was $1.6\times10^{-14}$. The original producer retained qualifications on per-cell emissivity extrapolation, native continuation provenance and the outer coverage of the rotated sky grids. Speed-selected gas, particularly in the control, has no independent shock classification. [Input hashes, qualifications and controls](assets/compressive_front_observer_2026-11-23/observer_inputs.json) · [Original emission audit](turn15_energy_emission_review_2026-11-11.md)

Restore the reviewed Turn 15 compact and map bundles into a common archive directory, preserving `compact_inputs/geometry` beside `results_emission`. Use the `G-HI_0020` subdirectory as `DEVELOPMENT_MAPS`. The `--native` directory holds the separately verified front projections for these three azimuths. A geometry-only receipt produces the overlay and distance tables; the completed emissivity receipt adds the three-way budgets, replacement comparisons and profiles. Omitting the two native arguments regenerates the development controls and lobe-distance table alone. [Input bundle hashes](assets/turn15_review_2026-11-11/README.md) · [Comparison code](../../scripts/science/compare_compressive_front.py)

```bash
.venv/bin/python scripts/science/compare_compressive_front.py \
  --inputs "$DEVELOPMENT_MAPS" --native "$NATIVE_FRONT" \
  --front-receipt "$NATIVE_FRONT/completion.json" --output "$NEW_RESULT_DIRECTORY"
```

The complete exterior arc check uses the final emissivity projections. It verifies the original and native map hashes and repeats the radial-background fit and 5% selection on the same replaced image.

```bash
.venv/bin/python scripts/science/ghi20_exterior_arc_check.py \
  --inputs "$DEVELOPMENT_MAPS" --native "$NATIVE_FRONT" \
  --output "$NEW_RESULT_DIRECTORY/exterior_arc_background_check.csv"
```
