# C-LO Endpoint First Products

Date: 2026-07-07

Goal 036 produced the first compact C-LO endpoint X-ray/tracer product suite
and a first-pass C-HI/C-LO endpoint scalar comparison. This is a prove-out and
review package, not a publication-ready observable product.

## Decision

Status:
`complete_product`.

Decision label:
`C_LO_ENDPOINT_FIRST_PRODUCTS_COMPLETE_COMPACT_COMPARISON_READY`.

PBS completion:

```text
Job id: 751098.kunanyi-ohpc
Job name: c_lo_xprod
Final state: F
Exit_status: 0
resources_used.walltime: 00:27:19
resources_used.cput: 00:17:39
resources_used.mem: 1144972kb
resources_used.ncpus: 1
resources_used.vmem: 1709232kb
```

The qstat record also reports `Stageout_status=1`. The required stage-root
stdout, stderr, final qstat transcript, remote logs, and product archive were
present and retrieved, so this is carried as a scheduler-stageout caveat rather
than a product failure.

## Endpoint Gate

The C-LO endpoint input surface is the accepted Goal 035 run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation/C-LO/particles
```

The product archive records a clean endpoint preflight:

- `markers/DONE` present.
- `markers/FAILED` absent.
- endpoint file `data.0053.flt.h5` contains `Timestep_53`.
- required datasets `rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3` share shape
  `(1014, 960, 960)`.
- endpoint HDF5 time is `15330.069689399999`, matching the configured target
  `15330.06968940`.

## Product Suite

The retrieved archive SHA-256 is:

```text
041eed367d0b74e5bbfbfd3d2ca1e9b51c0eb24b90c7fdd32c36a8bec95646c1
```

Local schema-clean review product root:

```text
docs/science/assets/c_lo_endpoint_first_products_2026-07-07/review_products/
```

The original retrieved remote archive is retained byte-for-byte under
`remote_logs/` as provenance. The local review copy repairs one packaging
schema issue from the archive: the original
`c_lo_endpoint_projection_metrics.csv` header repeated `time_myr`. The local
`review_products/c_lo_endpoint_projection_metrics.csv` keeps the first
`time_myr` column, drops the duplicate copy, and leaves the scalar values
unchanged. The wrapper now fails fast if future projection-metrics columns are
not unique.

Validated C-LO endpoint products:

| View | Accumulation | Corrected X-ray sum | Corrected X-ray max | Empty columns |
| --- | --- | ---: | ---: | ---: |
| `0deg` | `direct_y_axis_sum` | `3494804623.455285` | `8676.140755686643` | `0` |
| `45deg` | `edge_overlap_uniform_cell_projection` | `1385987160.135606` | `7861.240459759196` | `0` |
| `90deg` | `edge_overlap_uniform_cell_projection` | `1960081839.138744` | `7734.063489218517` | `0` |

All raw, corrected, and correction-ratio layers have `0/960` empty projected
columns for all three views. The `45deg` and `90deg` products use the accepted
refined nonzero-view projection method.

## C-HI/C-LO Comparison

The first-pass scalar comparison is compact and deliberately conservative:

| View | C-LO/C-HI raw sum | C-LO/C-HI corrected sum | C-LO/C-HI corrected max |
| --- | ---: | ---: | ---: |
| `0deg` | `1.101367748136191` | `1.087839647658863` | `0.003018414118929397` |
| `45deg` | `0.9732792952759747` | `0.9665266425113752` | `0.02383693282436476` |
| `90deg` | `0.9732792952759742` | `0.9665266425113748` | `0.01674149034101392` |

The sum ratios are useful first-pass endpoint control-surface scalars. The max
ratios are carried as diagnostic scalar evidence only; they should not be read
as a final morphology or observability claim.

## Assets

Key machine-readable assets:

- `c_lo_endpoint_preflight.csv`
- `c_lo_endpoint_projection_metrics.csv`
- `c_hi_c_lo_endpoint_comparison.csv`
- `c_lo_product_provenance.csv`
- `c_lo_endpoint_first_products_caveats.csv`
- `completion_summary.csv`
- `retrieved_archive_manifest.csv`
- `product_validation_summary.csv`
- `headline_c_hi_c_lo_comparison.csv`
- `large_file_inventory.csv`
- `schema_repair_manifest.csv`
- `c_lo_endpoint_first_products_metadata.json`

Retrieved remote evidence:

- `remote_logs/c_lo_endpoint_first_products_2026-07-07.tar.gz`
- `remote_logs/c_lo_endpoint_first_products.out`
- `remote_logs/c_lo_endpoint_first_products.err`
- `remote_logs/remote_logs/qstat_final_2026-07-07.txt`
- `remote_logs/remote_logs/submission_preflight_2026-07-07.txt`

## Package Size Policy

The local asset bundle is intentionally not tiny: it is about `229 MB` because
it keeps the retrieved `39.419 MiB` archive and twelve `15.782 MiB` TSV review
arrays. The TSV arrays are 2-D endpoint-review products:
`tracer_max_los.tsv`, `xray_1kev_raw_mjy_sr.tsv`,
`xray_1kev_xraise_corrected_mjy_sr.tsv`, and
`xray_1kev_correction_ratio.tsv` for each of `0deg`, `45deg`, and `90deg`.

These files are retained because they are the first parseable C-LO endpoint
review maps needed to inspect the compact product surface without returning to
Kunanyi. They are not PLUTO HDF5 payloads, not `data.*` files, and not particle
restart/output payloads. Every retained file is below `100 MiB`; the full list
of files above `5 MiB` is in `large_file_inventory.csv`.

No C-LO `.h5`, `data.*`, or particle payload files were copied into the local
Goal 036 asset bundle.

## Caveats

- This is the first compact C-LO endpoint prove-out product package, not a
  publication-ready observable product.
- No C-LO cavity, PRAiSE/radio, Level 3, or topology product was generated.
- The C-HI/C-LO comparison is scalar-first and inherits existing C-HI caveats:
  sparse radio remains diagnostic only, Level 3 gravity remains
  `blocked_missing_potential`, and the C-HI topology control surface remains
  conditional rather than a final topology freeze.
- G-LO work is still not authorized by this package.

## Recommendation

Accept Goal 036 as the first compact C-LO endpoint product surface if the
validation gate remains green. The next useful goal should be a bounded
C-LO/C-HI endpoint product interpretation and comparison-readiness packet, or a
G-LO readiness/execution decision if X-ray Cavities wants to complete the
three-case comparison ladder next.
