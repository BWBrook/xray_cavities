# C-HI Conditional Endpoint Topology Application

Date: 2026-07-01

Status: `complete_conditional_endpoint_topology_application_package`

Decision label: `CONDITIONAL_CONNECTED_CORE_APPLICATION_NO_FINAL_FREEZE`

## Scope

Goal 027 packages a bounded, local-only conditional endpoint topology
application for the final `C-HI`, `0 deg` endpoint. It sits beside the
accepted Goal 005/007 endpoint products and does not overwrite, replace, or
rerun them.

The package preserves the connected residual core from Goals 025/026 as a
conditional review/application result. It does not freeze final observational
cavity topology, does not define a new final cavity boundary, and does not
claim that tracer-proxy seeds are X-ray-fitted cavities.

No remote commands, HDF5/XRAiSE reruns, PLUTO, PRAiSE, radio, cavity
regeneration, endpoint rerun, accepted-asset overwrites, scientific-default
changes, `agent_comms` edits, commits, or pushes were performed.

## Assets

Machine-readable assets live in:

```text
docs/science/assets/c_hi_conditional_endpoint_topology_application_2026-07-01/
```

Primary files:

- `conditional_topology_application_summary.csv`
- `selected_threshold_component_summary.csv`
- `threshold_sensitivity_carried_forward.csv`
- `accepted_product_relationship.csv`
- `caveat_register.csv`
- `next_step_recommendation.csv`
- `conditional_endpoint_topology_application_metadata.json`

The builder and focused tests are:

```text
scripts/science/build_conditional_endpoint_topology_application.py
tests/test_conditional_endpoint_topology_application.py
```

Goal 027 does not duplicate the Goal 026 PNG. It records a direct provenance
pointer instead:

```text
docs/science/assets/c_hi_residual_threshold_sensitivity_review_2026-07-01/residual_threshold_sensitivity.png
```

## Selected Application

Selected threshold:

```text
1 percent residual-core mask
```

Selected residual threshold:

```text
-0.04586436454772977
```

Selection rationale:

- `1` percent was the Goal 025 representative residual-core threshold.
- It sits inside the Goal 026 narrow-threshold connected regime.
- `0.5` and `2` percent support robustness of the narrow connected core.
- `3`, `5`, `10`, and `20` percent remain ambiguity bounds.

Application result:

| Field | Value |
| --- | --- |
| observed topology class | `connected_envelope_single_system` |
| gate status | `pass` |
| mask pixels | `9735` |
| seeded component count | `1` |
| unlabelled component count | `6` |
| selected seeded component | `spans_negative_and_positive` |
| negative-z seed overlap pixels | `724` |
| positive-z seed overlap pixels | `719` |
| final observational topology frozen | `false` |

The selected mask has one seeded component that spans both tracer-proxy side
labels. It also has six significant unlabelled residual islands; those are
retained as caveats rather than silently discarded.

## Threshold Sensitivity Carried Forward

Goal 026 threshold sensitivity is first-class evidence in this package:

| Residual percentile | Application role | Observed class |
| ---: | --- | --- |
| `0.5` | supporting narrow-threshold robustness | `connected_envelope_single_system` |
| `1` | selected representative conditional application | `connected_envelope_single_system` |
| `2` | supporting narrow-threshold robustness | `connected_envelope_single_system` |
| `3` | ambiguity bound | `ambiguous_needs_review` |
| `5` | ambiguity bound | `ambiguous_needs_review` |
| `10` | ambiguity bound | `ambiguous_needs_review` |
| `20` | ambiguity bound | `ambiguous_needs_review` |

This is the key interpretation boundary: the connected core is stable in the
narrow residual-core regime, but the classification becomes ambiguous when the
mask expands enough to include additional side-specific seeded structures and
unlabelled residual islands.

## Relationship To Accepted Products

Accepted Goal 005/007 endpoint products remain the baseline evidence and are
not overwritten or replaced.

- Goal 005 still supplies the accepted corrected X-ray map, tracer map,
  tracer-defined cavity ellipses, lobe volumes, and energy convention context.
- Goal 007 still supplies the observational-product readiness context and the
  residual-display method.
- Goal 027 adds a no-overwrite conditional application package that makes the
  connected residual-core interpretation durable and auditable.

The Goal 005 tracer-defined ellipses remain valid prove-out/provenance proxies.
Goal 027 does not turn them into X-ray-fitted cavity boundaries.

## Decision

Decision label:

```text
CONDITIONAL_CONNECTED_CORE_APPLICATION_NO_FINAL_FREEZE
```

This means the project can carry the `1` percent connected residual core as a
conditional endpoint topology control surface, provided the Goal 026 threshold
sensitivity is carried beside it. It does not authorize final topology
language, accepted-product replacement, or publication-ready observational
claims.

## Recommendation

Recommended next goal shape:

```text
conditional_topology_application_acceptance_review
```

The next decision should be whether X-ray Cavities accepts this package as the
conditional endpoint topology control surface. The review should stay
docs/evidence only unless X-ray Cavities explicitly authorizes a new bounded
method or product step.

Fallbacks:

- `refine_residual_mask_protocol` if the conditional 1 percent threshold is
  not acceptable.
- `hold_at_tracer_proxy_status` if X-ray Cavities prefers not to carry a
  conditional topology application yet.

## Active Caveats

- This is not a publication-ready observable product.
- Final observational endpoint topology is not frozen.
- Tracer side labels remain provenance proxies, not X-ray-fitted cavities.
- Threshold sensitivity remains active and visible.
- Unlabelled residual islands are reported explicitly.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
