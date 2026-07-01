# C-HI Residual-Threshold Sensitivity Review

Date: 2026-07-01

Status: `complete_local_threshold_sensitivity_review`

Decision label: `CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL`

## Scope

Goal 026 reviews the threshold dependence of the Goal 025 conditional
residual-core topology application for the final `C-HI`, `0 deg` endpoint.
It uses only existing local compact assets from Goals 005, 007, and 025. It
does not rerun HDF5/XRAiSE, PLUTO, PRAiSE, radio, cavity extraction, endpoint
products, remote jobs, or accepted assets.

The question is deliberately narrow: whether the conditional connected-core
result is robust enough to support a later bounded no-overwrite endpoint
topology application package, or whether the project should hold at
tracer-proxy status and refine the residual-mask protocol first.

## Assets

Machine-readable assets live in:

```text
docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/
```

Primary files:

- `residual_threshold_sensitivity.csv`
- `residual_component_sensitivity.csv`
- `mask_seed_overlap_summary.csv`
- `figure_provenance.csv`
- `next_step_recommendation.csv`
- `residual_threshold_sensitivity_metadata.json`
- `residual_threshold_sensitivity.png`

The builder and focused tests are:

```text
scripts/science/build_residual_threshold_sensitivity_review.py
tests/test_residual_threshold_sensitivity_review.py
```

## Method

The review keeps the Goal 025 protocol:

```text
residual = log10(corrected_xray) - boxcar_smooth(log10(corrected_xray), 41 px)
side seed = tracer_max_los >= 5e-3, split by z_kpc sign
min_component_pixels = 50
connectivity = 4
```

It then evaluates residual-core masks at:

```text
0.5, 1, 2, 3, 5, 10, 20 percent
```

The helper reports unlabelled residual islands explicitly. They are not used
for the seeded topology class, but they remain visible in the tables and
figure because they matter for method review.

This review separates three concepts:

- X-ray residual mask: a thresholded low-residual structure in the corrected
  X-ray map.
- Tracer-proxy side seed labels: provenance labels derived from the tracer map
  and z sign.
- Observational cavity topology: not finalized here; only a conditional local
  seeded classification is reviewed.

## Sensitivity Result

| Residual percentile | Mask pixels | Seeded components | Unlabelled components | Observed class |
| ---: | ---: | ---: | ---: | --- |
| `0.5` | `4868` | `1` | `10` | `connected_envelope_single_system` |
| `1` | `9735` | `1` | `6` | `connected_envelope_single_system` |
| `2` | `19469` | `1` | `7` | `connected_envelope_single_system` |
| `3` | `29204` | `3` | `1` | `ambiguous_needs_review` |
| `5` | `48672` | `7` | `3` | `ambiguous_needs_review` |
| `10` | `97344` | `27` | `2` | `ambiguous_needs_review` |
| `20` | `194688` | `59` | `10` | `ambiguous_needs_review` |

The narrow residual-core regime is stable across `0.5`, `1`, and `2`
percent. In all three cases the seeded component that matters to the topology
classification spans both negative-z and positive-z tracer-proxy side labels.

At `3` percent, the mask first admits side-specific seeded components in
addition to the spanning connected core. The current helper therefore returns
`ambiguous_needs_review`. Broader `5`, `10`, and `20` percent masks are also
ambiguous because they mix the connected core, side-specific structure, and
unlabelled residual islands.

## Figure

The reviewer-facing figure is:

```text
docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.png
```

It shows the corrected X-ray context, the boxcar residual field, the
tracer-proxy side seeds, and the thresholded masks. Mask colors are:

- gray: unlabelled residual island;
- blue: residual pixels overlapping the negative-z tracer-proxy seed;
- red: residual pixels overlapping the positive-z tracer-proxy seed.

The figure is a diagnostic review aid, not a hand-drawn boundary or a final
observational topology product.

## Decision

Decision label:

```text
CONNECTED_CORE_PRESERVED_THRESHOLD_SENSITIVE_NOT_FINAL
```

The connected residual core looks real and review-worthy in the narrow
threshold regime. The result is not robust enough to freeze final endpoint
topology, because the class changes to ambiguous once the mask expands beyond
the core.

## Recommendation

Recommended next goal shape:

```text
bounded_conditional_endpoint_topology_application_package
```

This should be a bounded, no-overwrite application package that preserves the
connected core as a conditional result and keeps the threshold sensitivity
visible. It should not replace accepted Goal 005/007 products, rerun
HDF5/XRAiSE by default, or claim final observational cavity topology.

Fallback if X-ray Cavities does not want to carry the conditional result:

```text
refine_residual_mask_protocol
```

The status quo tracer-proxy ellipsoids remain valid as prove-out and
provenance proxies, but they should not be called X-ray-fitted cavities.

## Active Caveats

- This is not a publication-ready observable product.
- The conditional residual-core result is not a final observational endpoint
  topology claim.
- Tracer side labels remain provenance proxies, not X-ray-fitted cavities.
- Threshold sensitivity remains active and visible.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
