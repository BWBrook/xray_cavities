# C-HI Final Observational Product Readiness Gate

Date: 2026-06-16

## Summary

Goal 007 responds to Patrick-agent's `Q-014` `HOLD` by packaging a clearer
local X-ray/cavity review product for the accepted final 50 Myr `C-HI`,
`0 deg` endpoint.

The package is ready for Patrick-agent review. It is not a method freeze, not a
new production run, and not a publication-ready observable claim.

Main product:

```text
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/c_hi_final_observational_product_readiness.png
```

Machine-readable metadata:

```text
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/observational_product_readiness_metadata.json
```

The figure uses the accepted Goal 005 corrected 1 keV X-ray surface-brightness
map and local axes. The wide-field panel spans the full available local support:
`x = -199.1538544` to `199.1538544 kpc` and `z = -248.9480743` to
`248.9480743 kpc`. This is wider than the Goal 005 main figure's
`90 kpc` x-width and exposes substantially more shocked-shell/cavity context.

## Product Contents

Asset directory:

```text
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/
```

Files:

- `c_hi_final_observational_product_readiness.png`: three-panel review figure.
- `observational_product_readiness_metadata.json`: field-of-view, stretch,
  residual method, overlay, topology, radio-status, and next-goal metadata.
- `xray_topology_readiness.csv`: compact topology and X-ray-fit status table.
- `radio_observable_status.csv`: current radio diagnostic versus observable
  readiness table.
- `product_provenance.csv`: source-file paths and SHA-256 checksums for local
  inputs referenced by the package.

The figure panels are:

1. Wide-field corrected 1 keV X-ray surface brightness with tracer and current
   cavity-boundary overlays.
2. Cavity-focused corrected 1 keV X-ray detail.
3. A local unsharp-mask residual diagnostic:
   `log10(corrected X-ray) - boxcar-smoothed log10(corrected X-ray)`, using a
   `41` pixel boxcar.

## Direct Answer To Q-014

Patrick-agent's visual-context concern is addressed enough to request a fresh
review: the new product no longer silently reuses the narrow Goal 005
`x = +/-45 kpc` main view, and it adds a contrast/residual diagnostic with the
same tracer and cavity-boundary context.

The method concern is not closed. The current cavity ellipses remain
tracer-defined diagnostic overlays. They are not X-ray-fitted observational
cavities. Goal 007 does not implement a new X-ray cavity fit.

The topology is therefore best labelled:

```text
connected-envelope versus two-tracer-lobe topology unresolved for observational fitting
```

The X-ray product can be read as a broader connected shell/envelope, while the
accepted Goal 005 measurement still reports two tracer-defined side ellipsoids.
That convention should be reviewed explicitly before broadening to other
views, source ages, `C-LO`, or `G-LO`.

## Radio Observable Status

Goal 007 keeps the radio boundary exactly as Patrick-agent requested. The
existing sparse PRAiSE loss table and particle-binned radio maps remain useful
particle-emissivity diagnostics and scalar/morphology continuity checks. They
are not validated radio surface-brightness observables.

The next radio-product goal should generate full raytraced radio
surface-brightness maps at two or more frequencies, with projection,
deposition/integration, beam or instrument treatment if required, and
provenance locked before the maps are used as observational products.

## Provenance

The package uses only accepted local compact assets:

- Goal 005 X-ray/cavity alignment assets:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`
- Goal 003 volume-coupled sparse radio/truth comparator assets:
  `docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/`
- Goal 002 sparse PRAiSE loss table assets:
  `docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/`

No PBS job, remote command, PLUTO run, XRAiSE extraction, cavity extraction,
PRAiSE workflow, radio workflow, scientific-default change, or broadening run
was performed for this package.

## Recommendation

Send the package to Patrick-agent as `Q-015`.

If Patrick-agent accepts the visual product with changes or accepts it as
adequate, the next bounded goal should still avoid immediate broadening until
the remaining radio and X-ray-fit method gaps are sequenced. The likely next
goal is either:

- an X-ray-based cavity/topology fitting method for the final `C-HI`, `0 deg`
  endpoint; or
- full raytraced radio surface-brightness products at two or more frequencies,
  if Patrick-agent treats the X-ray plotting package as adequate.

If Patrick-agent continues `HOLD`, the next goal should be the narrow X-ray
cavity/topology fitting method, not a new production case.
