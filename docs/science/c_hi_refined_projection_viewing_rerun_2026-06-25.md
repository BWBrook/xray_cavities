# C-HI Refined Projection Viewing Rerun

Date: 2026-06-25

## Summary

Goal 016 retrieves and packages the bounded Kunanyi rerun of final `C-HI`
`90 deg` and `45 deg` X-ray/tracer projections using the Goal 015 refined
projected-bin accumulator:

```text
projection.projected_accumulation=edge_overlap_uniform_cell_projection
```

Decision label:

```text
REFINED_PROJECTION_FIXES_EMPTY_COLUMN_FAILURE
```

The refined accumulator fixes the Goal 012 `90 deg` empty-column/striping
failure in the X-ray layers. The historical `90 deg` raw, corrected, and
correction-ratio X-ray products each had `400/960` all-zero projected columns;
the refined products have `0/960`. The `45 deg` sanity rerun improves from
`22/960` all-zero X-ray columns to `0/960`.

Raw and corrected X-ray pixel sums are conserved to roundoff relative to the
accepted historical products. The correction-ratio positive-pixel sum increases
because previously empty projected columns are now populated.

This is a projection-method repair/evidence package, not a publication-ready
observable product.

## Remote Record

PBS completion evidence:

| Job | Name | Exit | State | Walltime | CPU time | Memory |
| --- | --- | ---: | --- | ---: | ---: | ---: |
| `700044.kunanyi-ohpc` | `c_hi_xrefprj` | `0` | `F` | `00:22:01` | `00:17:40` | `1362356kb` |

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal016_refined_projection_viewing_rerun
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-25-c-hi-refined-projection-viewing-rerun
```

Input endpoint:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Fetched archive:

```text
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/remote_logs/refined_projection_viewing_rerun_2026-06-25.tar.gz
sha256=363b942f93908a342141d88220f30e5c2585bde74679e57322beb751e15dbf77
```

Remote stdout records:

- `hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960) time_code=15330.069689399999`
- `xray_90deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]`
- `xray_45deg_refined_validation=passed empty_columns=[('raw_xray', 0, 0.0), ('corrected_xray', 0, 0.0), ('correction_ratio', 0, 0.0)]`
- `finished_utc=2026-06-25T03:28:43Z`

Remote stderr is zero bytes.

## Local Review Assets

Compact local review assets are under:

```text
docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/
```

Primary files:

| File | Purpose |
| --- | --- |
| `remote_logs/refined_projection_viewing_rerun_2026-06-25.tar.gz` | fetched compact remote archive |
| `remote_logs/c_hi_refined_projection_viewing_rerun.out` | PBS stdout |
| `remote_logs/c_hi_refined_projection_viewing_rerun.err` | PBS stderr, zero bytes |
| `refined_projection_metrics.csv` | refined 90/45 projection metrics and accumulator metadata |
| `empty_column_before_after.csv` | accepted versus refined empty-column diagnostics |
| `refined_vs_accepted_xray_summary.csv` | scalar X-ray comparison against accepted historical products |
| `product_provenance.csv` | remote/local paths and checksums |
| `refined_projection_viewing_rerun_metadata.json` | status, result label, archive SHA, and compact outcomes |

The package builder is:

```text
scripts/science/build_refined_projection_viewing_rerun.py
```

It is covered by:

```text
tests/test_refined_projection_viewing_rerun.py
```

## Empty-Column Repair

The refined `90 deg` X-ray layers remove the diagnosed all-zero projected
columns:

| View | Layer | Accepted empty columns | Refined empty columns | Assessment |
| --- | --- | ---: | ---: | --- |
| `90 deg` | raw X-ray | `400/960` | `0/960` | fixed |
| `90 deg` | corrected X-ray | `400/960` | `0/960` | fixed |
| `90 deg` | correction ratio | `400/960` | `0/960` | fixed |
| `45 deg` | raw X-ray | `22/960` | `0/960` | fixed |
| `45 deg` | corrected X-ray | `22/960` | `0/960` | fixed |
| `45 deg` | correction ratio | `22/960` | `0/960` | fixed |

For both views, refined raw/corrected/correction-ratio positive masks remain
consistent with the refined raw-X-ray mask. This matches the Goal 014 diagnosis
that the historical striping was an occupancy/binning issue shared by raw,
corrected, and correction-ratio layers.

## Scalar Checks

The refined method changes local bin occupancy without changing the physical
input endpoint or correction tables.

| View | Metric | Relative change | Assessment |
| --- | --- | ---: | --- |
| `90 deg` | raw X-ray pixel sum | `6.31e-16` | conserved to roundoff |
| `90 deg` | corrected X-ray pixel sum | `5.88e-16` | conserved to roundoff |
| `90 deg` | raw X-ray max | `0.001413` | small bin-distribution change |
| `90 deg` | corrected X-ray max | `0.001067` | small bin-distribution change |
| `90 deg` | correction-ratio positive sum | `0.712242` | positive support expanded |
| `45 deg` | raw X-ray pixel sum | `0` | conserved to roundoff |
| `45 deg` | corrected X-ray pixel sum | `-1.33e-15` | conserved to roundoff |
| `45 deg` | raw X-ray max | `-0.000214` | small bin-distribution change |
| `45 deg` | corrected X-ray max | `-0.000138` | small bin-distribution change |
| `45 deg` | correction-ratio positive sum | `0.023463` | positive support expanded |

The correction-ratio positive sum is not a conserved physical scalar here. Its
increase is expected once previously all-zero columns become positive cells.

## Interpretation

The Goal 015 accumulator fixes the specific Goal 012 `90 deg` pathological
empty-bin/striping failure on the real final `C-HI` endpoint. The result is
also conservative in the X-ray pixel-sum sense for both the affected `90 deg`
view and the `45 deg` sanity rerun.

This supports replacing or superseding the historical 45/90 projection products
in a later bounded review step, while preserving the accepted Goal 011/012
assets as historical evidence. It also supports moving toward a tightly bounded
`C-HI` source-age sampling plan after X-ray Cavities decides how to present the
refined-view products.

Recommended next step: review/accept Goal 016, then write a narrow Goal 017
that either packages reviewer-facing refined 45/90 figures/trio context or
uses the refined projection method as the default for the next bounded
`C-HI` source-age sampling step. Do not open a broad batch by implication.

## Caveats

- Projection-method repair/evidence only; not publication-ready observables.
- Accepted Goal 011/012 assets are historical products and were not overwritten.
- Connected-envelope/X-ray topology caveat remains active.
- Sparse particle-binned radio remains diagnostic, not a validated radio
  observable.
- Level 3 gravitational energy remains `blocked_missing_potential`.
- Future energy summaries should continue carrying `pV`, adopted `2.5pV`, and
  `4pV`.

## Non-Claims

- No new PLUTO production, source-age sampling, `C-LO`, `G-LO`,
  comparison-case processing, PRAiSE/radio/cavity regeneration, scientific
  default changes, commits, pushes, `agent_comms` changes, or Stas/Patrick
  escalation occurred.
- No new PBS job was submitted in the retrieval/package phase.
