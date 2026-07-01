# C-HI Existing-Asset Topology Application Design

Date: 2026-07-01

Status: `complete_conditional_local_application_design`

Decision label: `CONDITIONAL_LOCAL_APPLICATION_CONNECTED_CORE_NOT_FINAL`

## Scope

Goal 025 tests whether the accepted local Goal 005/007 compact assets are
enough to design a deterministic application of the Goal 024 hybrid
X-ray/cavity topology helper to the real final `C-HI`, `0 deg` endpoint.

This goal uses only existing local compact assets:

- Goal 005 corrected 1 keV X-ray map.
- Goal 005 tracer max line-of-sight map.
- Goal 005 `x_kpc` and `z_kpc` axes.
- Goal 005 tracer-defined cavity ellipse boundary and lobe/scalar tables as
  provenance.
- Goal 007 observational-readiness metadata and topology-readiness table.

No remote commands, HDF5/XRAiSE reruns, PLUTO, PRAiSE, radio, cavity
regeneration, endpoint rerun, accepted-asset overwrites, scientific-default
changes, `agent_comms` edits, commits, or pushes were performed.

## Assets

Machine-readable assets live in:

```text
docs/science/assets/c_hi_existing_asset_topology_application_design_2026-07-01/
```

Primary files:

- `input_asset_contract.csv`
- `side_seed_protocol.csv`
- `xray_mask_protocol.csv`
- `application_readiness_decision.csv`
- `topology_application_result.csv`
- `topology_component_summary.csv`
- `next_step_recommendation.csv`
- `existing_asset_topology_application_metadata.json`

The builder is:

```text
scripts/science/build_existing_asset_topology_application_design.py
```

It uses the Goal 024 helper:

```text
scripts/science/hybrid_xray_cavity_topology.py
```

## Input Contract

The local input contract is compatible:

- corrected X-ray map: `1014 x 960`;
- tracer max line-of-sight map: `1014 x 960`;
- `z_kpc` axis: `1014` rows;
- `x_kpc` axis: `960` columns.

The cavity ellipse boundary and lobe scalar tables are kept as provenance only.
They are not selected as X-ray topology masks because that would circularly
reuse the existing tracer-defined proxy overlay as the method under test.

## Side-Seed Protocol

Selected side-seed protocol:

```text
tracer_max_los >= 5e-3
negative_z if z_kpc < 0
positive_z if z_kpc > 0
```

This yields:

| Label | Pixels |
| --- | ---: |
| negative-z seed | `230967` |
| positive-z seed | `230250` |
| unlabelled | `512223` |

This is deterministic and auditable from existing compact assets. It preserves
the tracer-proxy side labels, but it is not an X-ray-fitted cavity boundary.

## X-ray Mask Protocol

Selected conditional X-ray mask protocol:

```text
residual = log10(corrected_xray) - boxcar_smooth(log10(corrected_xray), 41 px)
mask = residual <= 1st percentile
min_component_pixels = 50
connectivity = 4
ignore_unlabelled_components = true
```

This follows the Goal 007 residual-display method and makes it parseable from
the existing corrected X-ray map. The selected 1st-percentile residual-core
threshold is:

```text
-0.04586436454772977
```

It selects `9735` candidate pixels.

## Application Result

The selected residual-core application classifies the seeded X-ray topology as:

```text
connected_envelope_single_system
```

The selected mask has one significant seeded component that spans both
negative-z and positive-z tracer-proxy seed labels:

```text
spans_negative_and_positive
```

This is a conditional local application, not a final observational endpoint
topology claim.

The threshold sensitivity is the reason for the caveat:

| Residual percentile | Observed class | Gate |
| ---: | --- | --- |
| `1` | `connected_envelope_single_system` | `pass` |
| `2` | `connected_envelope_single_system` | `pass` |
| `5` | `ambiguous_needs_review` | `fail` |
| `10` | `ambiguous_needs_review` | `fail` |
| `20` | `ambiguous_needs_review` | `fail` |

The narrow residual core is connected, while broader residual masks include
multiple side-specific and spanning structures. That is useful evidence, but
not strong enough to freeze the real endpoint as a final connected-envelope
observational cavity topology.

## Decision

Decision:

```text
conditional_local_application_made_not_final_topology
```

Decision label:

```text
CONDITIONAL_LOCAL_APPLICATION_CONNECTED_CORE_NOT_FINAL
```

This means:

- a deterministic side-seed protocol can be derived locally;
- a parseable residual-core X-ray mask can be derived locally;
- the Goal 024 helper can be applied to the real endpoint as a conditional
  residual-core probe; and
- the result must remain conditional because the broader residual-mask
  sensitivity becomes mixed/ambiguous.

## Recommendation

Recommended next goal shape:

```text
local_residual_threshold_sensitivity_review_package
```

The next goal should stay local and create a compact reviewer-facing residual
threshold/morphology sensitivity package from the existing Goal 005/007 arrays.
It should include a figure or small matrix of residual-mask choices, seeded
component summaries, and a clear recommendation on whether the 1-2% connected
core is enough to support a bounded no-overwrite endpoint topology application.

Do not proceed directly to remote work, HDF5/XRAiSE rerun, accepted-product
replacement, or final topology language from this design pass.

## Active Caveats

- This is not a publication-ready observable product.
- The conditional residual-core result is not a final observational endpoint
  topology claim.
- Tracer side labels remain provenance proxies, not X-ray-fitted cavities.
- Threshold sensitivity must be reviewed locally before any bounded
  application/rerun.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
