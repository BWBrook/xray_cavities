# How much false cavity area lies outside the G-HI compression front?

At 20 Myr the native compression front encloses both tracer-defined lobes in all three side-on G-HI views. With the X-ray background fixed, restricting the original 5% radial-deficit outline to that boundary removed **10,577 of 10,926 kpc² of false area (96.8%)** across the three projections. It kept **all 18,594 kpc² of correctly selected lobe area**. Purity rose from 63.0% to 98.2%. The detector still covered 53.8% of the full projected lobe area. The three views show the same gas from different directions. [Protocol recorded before scoring](ghi20_front_constraint_protocol_2026-11-25.md) · [Full area scores](assets/ghi20_front_constraint_2026-11-25/area_scores.csv)

| Viewing azimuth | False area before (kpc²) | False area removed (kpc²) | Share removed | False area left (kpc²) | Real lobe area lost (kpc²) | Lobe area covered before and after |
|---|---:|---:|---:|---:|---:|---:|
| 0° | 7,229.4 | 7,184.2 | 99.4% | 45.2 | 0 | 51.6% |
| 45° | 1,993.9 | 1,826.8 | 91.6% | 167.1 | 0 | 49.8% |
| 90° | 1,702.7 | 1,566.1 | 92.0% | 136.7 | 0 | 60.4% |

![Area removed outside the tracer-defined lobes and fraction of their projected area covered by the original cavity candidates in each view](assets/ghi20_front_constraint_2026-11-25/front_clipping.png)

The two lobes gave similar results within each view. The table records physical detector areas. The removal percentage uses each lobe’s initially selected false area as its denominator. The zero loss extends to the full tracer footprint, including lobe pixels the X-ray outline missed. [Geometry and closure checks](assets/ghi20_front_constraint_2026-11-25/front_geometry.csv) · [Input, background and mask hashes](assets/ghi20_front_constraint_2026-11-25/receipt.json)

| View | Lobe | False area removed (kpc²) | Share removed | Correctly selected lobe area kept (kpc²) | Real area lost (kpc²) |
|---|---|---:|---:|---:|---:|
| 0° | Negative axis | 3,589.7 | 99.4% | 2,954.0 | 0 |
| 0° | Positive axis | 3,594.5 | 99.3% | 2,880.2 | 0 |
| 45° | Negative axis | 913.4 | 91.8% | 3,005.3 | 0 |
| 45° | Positive axis | 913.4 | 91.4% | 2,965.1 | 0 |
| 90° | Negative axis | 783.5 | 91.9% | 3,385.3 | 0 |
| 90° | Positive axis | 782.6 | 92.1% | 3,403.9 | 0 |

## Does the residual circular arc survive?

Patrick also flagged the smaller arc left after an earlier experiment replaced the front gas’s emissivity with its initial value and fitted a new background. We reproduced that outline, held its own background fixed, and applied the same cut. It removed **96.9%, 86.2% and 82.0%** of the remaining false area at 0°, 45° and 90°, respectively. That is 2,427 of 2,712 kpc² in total, again with zero real lobe area lost. The front therefore excludes most of both the broad original arc and its smaller residual in this snapshot. [Previous emissivity experiment and images](ghi20_compressive_front_comparison_2026-11-23.md) · [All comparison rows](assets/ghi20_front_constraint_2026-11-25/area_scores.csv)

The exact-edge reconstruction of the original radial image gave the same removal percentages to one decimal place. The original seed/grow rule selected only 9.56 kpc² of false area across the three views, all inside the front. In DET-06’s 100 km/s background fits these same three views had 0 kpc² of false area with a flat centre and 5.09 kpc² with the extrapolated slope. The front removed no pixels from either speed-based outline. This distinguishes the front’s benefit for the original orange arcs from the effect of changing how their background is fitted. [DET-06 background comparison](source_excluded_background_results_2026-11-25.md)

## What defines the boundary?

The magenta outline encloses the projected path of the dominant compressive layer mapped from native simulation fields. All four historical choices of layer definition gave a single bounded, hole-free sky footprint enclosing the source in every view. None touched the edge of the detector or the native box. The primary footprint enclosed 15,917, 16,395 and 15,929 kpc² at the three angles. Across the four definitions, pooled false-area removal ranged from 96.0% to 97.1%, with zero tracer pixels lost throughout. The physical areas use the exact nonuniform sky-cell edges. The comparison preserves the original candidate fragments, internal indentations and background fit. [Native front selection](ghi20_compressive_front_contract_2026-11-23.md) · [Geometry table](assets/ghi20_front_constraint_2026-11-25/front_geometry.csv)

This gives a reason to test the outer bound Patrick proposed on X-ray data. The missing half of the lobe at 45° is already inside the front. A better boundary alone cannot supply its missing cavity signal. An observer would also have to locate a reliable edge from brightness alone and recognise views with an open or ambiguous edge. The present result concerns one simulated state with a known projected compression front. Shock identification and performance of an image-only edge rule remain separate questions. [Patrick’s proposed observational test](../exchange/logs/2026-11-25-q032-front-constrained-cavity-handover.md)

## Reproduction

The public summary recomputes the bipolar and pooled results from the six hemisphere rows, verifies the two table hashes and can redraw the figure.

```sh
.venv/bin/python scripts/science/summarise_ghi20_front_constraint.py
.venv/bin/python scripts/science/summarise_ghi20_front_constraint.py \
  --figure docs/science/assets/ghi20_front_constraint_2026-11-25/front_clipping.png
```

With the archived G-HI/20 inputs, the measurement binds the two producer receipts to the same time, native files and exact sky grid. It replays the two original image-only outlines, the emissivity-replacement radial fit and the exact-image radial reference, and verifies both DET-06 candidates against their published mask digests.

```sh
.venv/bin/python scripts/science/measure_ghi20_front_constraint.py \
  --inputs "$GHI20_EMISSION" --native "$GHI20_FRONT" --out "$NEW_RESULTS"
```

A second Codex implementation traced the physical edges into a polygon, classified each row by boundary crossings and summed the widths of the occupied spans. It independently reconstructed the smaller refitted orange candidate. For the original and smaller orange candidates, all 24 clipped masks matched exactly across the three views and four fronts. All 15 area and fraction fields agreed on all 72 lobe and bipolar rows, within 1.82 × 10⁻¹² kpc² in area. The two implementations share the archived projections. The four other candidate comparisons were checked against their original inputs by the main analysis. [Independent review receipt](assets/ghi20_front_constraint_2026-11-25/independent_review.json) · [Independent implementation](../../scripts/science/review_ghi20_front_constraint.py)

```sh
uv run --no-project --python 3.12 --with scikit-image==0.26.0 python \
  scripts/science/review_ghi20_front_constraint.py \
  --maps "$GHI20_EMISSION" --front "$GHI20_FRONT" \
  --compare "$NEW_RESULTS/area_scores.csv" --output "$NEW_RESULTS/independent_review.json"
```
