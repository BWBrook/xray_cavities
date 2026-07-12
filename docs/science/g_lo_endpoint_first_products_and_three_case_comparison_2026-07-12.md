# G-LO Endpoint First Products And Three-Case Comparison

Date: 2026-07-12

Goal 039 moves directly from the validated G-LO production endpoint to its
first complete X-ray/tracer product surface and the first coherent
`C-HI`/`C-LO`/`G-LO` endpoint scalar comparison.

## Product Contract

The completed job processed only the accepted final G-LO endpoint:

```text
data.0050.flt.h5::Timestep_50
```

It requires the accepted Goal 038 `DONE` marker, absence of `FAILED`, and the
endpoint double and particle surfaces as guards. The three views are:

- `0 deg`: `direct_y_axis_sum`;
- `45 deg`: `edge_overlap_uniform_cell_projection`;
- `90 deg`: `edge_overlap_uniform_cell_projection`.

Every view must produce finite positive X-ray metrics and remain below the
configured empty-column threshold. The three-case comparison must contain
exactly nine rows: three cases by three views.

## Interpretation Boundary

This is a full endpoint first-products comparison step, not another production
prove-out rung. It should answer whether the three accepted simulation cases
produce coherent, technically comparable endpoint X-ray/tracer surfaces.

It remains pre-observational in the strict sense: no beam or instrument model,
final radio observable, frozen cavity topology, or publication-facing claim is
introduced. Existing radio, topology, and Level 3 gravity caveats remain
active.

## Completion

PBS job `756090.kunanyi-ohpc` / `g_lo_xprod` was submitted to `normal` with
one CPU, 96 GB memory, and four hours walltime. It completed with
`Exit_status=0` after `00:29:05`; stdout contains all three view-validation
markers and the nine-row comparison marker, while stderr is empty.

The retrieved archive is immutable provenance:

```text
docs/science/assets/g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12/remote_logs/g_lo_endpoint_first_products_2026-07-12.tar.gz
```

Its SHA-256 is
`149141739f6f8a631b94425230d5e824f6efc426c0ddc25dacd84aacb73e4e99`.
All 37 archive members and the internal checksum manifest validate.

Status: `complete_product`.

Decision label: `THREE_CASE_ENDPOINT_FIRST_PRODUCTS_COMPLETE`.

## Direct Observations

All nine case/view rows have finite positive X-ray metrics and zero empty
columns. The nonzero views use the refined edge-overlap accumulation.

Same-view corrected X-ray sum ratios are:

| View | C-LO / C-HI | G-LO / C-HI | C-LO / G-LO |
| --- | ---: | ---: | ---: |
| 0 deg | 1.08784 | 0.061946 | 17.5610 |
| 45 deg | 0.966527 | 0.0467666 | 20.6670 |
| 90 deg | 0.966527 | 0.0467666 | 20.6670 |

Thus the G-LO total corrected endpoint X-ray sum is substantially lower than
the cluster cases in every view. This is a result about these processed total
maps. It is not yet a result about cavity deficit, feedback strength, or
observational detectability.

The correction also has greater leverage in G-LO: corrected/raw total ratios
are approximately 2.63-2.75, versus roughly 1.33-1.35 for the cluster cases.
That difference must be understood before corrected totals receive a physical
interpretation.

## Comparison Figure

The reviewer-facing figure is:

```text
docs/science/assets/g_lo_endpoint_first_products_and_three_case_comparison_2026-07-12/g_lo_three_case_endpoint_comparison.png
```

Each panel uses independent percentile log scaling to preserve morphology.
Panel colour is therefore not an absolute brightness comparison. The title
annotations and `three_case_endpoint_comparison.csv` carry the quantitative
ratios.

## Scientific Assessment

A focused `sol_medium_scientist` review independently recomputed all nine
ratios, with maximum absolute discrepancy `4.44e-16`, and found the contrast
computationally credible but not physically identified. Its key distinction is
accepted here:

- observation: G-LO's processed total X-ray sum is much lower;
- inference requiring further work: whether the contrast is driven by the
  group atmosphere, cavity response, correction behaviour, or some
  combination.

The next goal should therefore be a full three-case, multi-view endpoint
cavity-recovery and truth-alignment analysis using existing outputs. It should
replace total-map sums as the primary estimand with common-aperture background,
fractional cavity deficit, contrast, area/volume recovery, tracer-threshold
sensitivity, and Level 1/2 truth alignment. It should proceed as post-processing
without another production run. Final method freezing or publication-facing
interpretation remains the later escalation point.

## Asset Policy

The local review bundle is approximately 234 MB. `large_file_inventory.csv`
records exactly 13 deliberate files above 5 MiB: the 42 MB immutable remote
archive and twelve 16 MB parseable G-LO endpoint arrays. No HDF5, production
`data.*`, or particle payload is present locally; every retained file is below
100 MiB. `local_asset_manifest.sha256` covers the complete bundle.
