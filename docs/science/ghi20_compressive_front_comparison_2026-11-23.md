# The G-HI/20 compression front and the X-ray cavity outlines

**Simulation and observation.** The high-power jet in group atmosphere `002031` has bipolar labelled power $2\times10^{45}$ erg s⁻¹, speed $0.1c$, 15° half-opening angle and 0.75-kpc injection height. Its 960 × 960 × 1,014 Cartesian grid spans 400 × 400 × 500 kpc, with cell widths from 0.05 kpc at the centre to 1.69 kpc transversely and 2.10 kpc axially at the outer edges. The HLLC solver used CFL 0.33 and an initial step of $10^{-5}$ code units. Native single-precision fluid outputs were scheduled every 306.60139379 code units. The compared output is `Timestep_20`, code time 6131.909618, actual age **19.9996143 Myr**. The original 1-keV maps use redshift 0.05 and side-on azimuths 0°, 45° and 90° about the jet axis. [Frozen front definition](ghi20_compressive_front_contract_2026-11-23.md) · [Frozen observer comparison](compressive_front_observer_protocol_2026-11-23.md)

Patrick’s requested review covers the independent three-dimensional front definition, its projection and the interpretation of any apparent alignment. The lobe and observer metrics below use the previously exposed development maps. [Method review request](../exchange/logs/2026-11-23-ghi20-compressive-front-method-review.md)

## Do the lateral orange arcs follow the independent front?

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

On genuine lobe sightlines that the original masks missed, front-associated ambient gas brightened relative to the same cells at time zero. Its increase offsets roughly one-third to one-half of the lobe’s own lost emission. By contrast, on the orange area beyond the lobe, the front’s **net brightening** is at most 0.20% of the observed brightness when the two hemispheres are pooled. The table sums each numerator and denominator over both hemispheres with the exact pixel areas before division. [Thirty per-side component budgets](assets/compressive_front_observer_2026-11-23/emission_regions.csv)

| Side-on azimuth | Lobe decrement offset on blue-missed sightlines | Lobe decrement offset on orange-missed sightlines | Front brightening / current brightness on exterior orange area |
| --- | ---: | ---: | ---: |
| 0° | 47.43% | 32.84% | 0.00068% |
| 45° | 49.48% | 49.23% | 0.193% |
| 90° | 44.95% | 47.07% | 0.105% |

Here the numerator is current minus initial emissivity in the **current compressive-layer ambient cells**. The decrement in the first two columns is initial minus current emissivity of current `tr1 > 0.001` lobe cells, along **missed** tracer sightlines only. The older 39–84% statistic integrates **speed-selected** ambient brightening over **selected** sightlines and divides by the fitted-background-minus-current observed deficit there. Expressed against the lobe’s own decrement on those selected sightlines, that older measure was 37–44%. The changed cell sets, sky regions and denominators answer different questions. [Earlier reconciliation](turn18_review_reconciliation_2026-11-11.md)

The outer arcs also respond **indirectly** to the front through the observer’s radial background fit. At 0° the original orange inferred volume is 3.98 times the native lobe. Replacing only the front-associated ambient gas with its initial emissivity in the same cells raises that figure to 4.11 with the original background. Refitting the background to that **same altered image** gives 1.08. The area selected outside the lobe drops from 7,229 to 1,170 kpc² and purity rises from 44.7% to 84.5%, yet completeness rises only from 51.6% to 56.4%. The near-unit volume therefore still misses 43.6% of the projected lobe area. The substitution changes only the 1-keV emissivity assigned to those fixed cells in the saved snapshot. [All 60 side, method and treatment results](assets/compressive_front_observer_2026-11-23/replacement_recovery.csv)

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
