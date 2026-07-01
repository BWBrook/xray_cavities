# C-HI Hybrid X-ray/Cavity Topology Gate

Date: 2026-07-01

Status: `complete_synthetic_local_gate`

Decision label:
`HYBRID_TOPOLOGY_SYNTHETIC_GATE_PASSED_LOCAL_APPLICATION_PROTOCOL_NEXT`

## Scope

Goal 024 implements and tests a local hybrid tracer-seeded, X-ray-constrained
cavity topology gate. The gate is deliberately synthetic/local. It does not
apply a new topology classification to the real `C-HI` endpoint and does not
authorize a product rerun.

The method separates two concepts that must not be conflated:

- tracer-proxy side labels, which remain useful provenance labels for
  negative-z and positive-z cavity proxies; and
- X-ray topology class, which is reported separately as
  `two_separate_cavities`, `connected_envelope_single_system`, or
  `ambiguous_needs_review`.

No remote commands, HDF5/XRAiSE reruns, cavity regeneration, accepted-asset
overwrites, scientific-default changes, `agent_comms` edits, commits, or
pushes were performed for this gate.

## Helper

The helper is:

```text
scripts/science/hybrid_xray_cavity_topology.py
```

Focused tests are:

```text
tests/test_hybrid_xray_cavity_topology.py
```

The helper uses deterministic, parameterized logic:

1. build a low-X-ray cavity candidate mask from
   `xray <= median(xray) * cavity_fraction_of_background`;
2. find connected components using the configured `bridge_connectivity`;
3. discard components below `min_component_pixels`;
4. report tracer-proxy side seed labels independently; and
5. classify the X-ray topology from the significant component-to-side-label
   relation.

The synthetic gate parameters are machine-readable in:

```text
docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/method_parameters.csv
```

For this gate:

- `cavity_fraction_of_background = 0.5`
- `min_component_pixels = 4`
- `bridge_connectivity = 4`

These are not new scientific defaults for production products. They are the
local synthetic-gate parameters used to prove the classification contract.

## Synthetic Gate

Compact assets live in:

```text
docs/science/assets/c_hi_hybrid_xray_cavity_topology_gate_2026-07-01/
```

Primary assets:

- `synthetic_topology_cases.csv`
- `topology_gate_results.csv`
- `method_parameters.csv`
- `accepted_asset_application_readiness.csv`
- `next_step_recommendation.csv`
- `hybrid_topology_gate_metadata.json`

The synthetic cases prove three required branches:

| Case | Expected class | Observed class | Gate |
| --- | --- | --- | --- |
| `synthetic_two_separate_cavities` | `two_separate_cavities` | `two_separate_cavities` | `pass` |
| `synthetic_connected_envelope_single_system` | `connected_envelope_single_system` | `connected_envelope_single_system` | `pass` |
| `synthetic_one_side_only_ambiguous` | `ambiguous_needs_review` | `ambiguous_needs_review` | `fail` |

This is the desired behavior. The helper can distinguish the two decisive
topology classes while making an unsupported one-side/ambiguous case fail
instead of being forced into a false two-lobe or connected-envelope result.

The tests also confirm that tracer-proxy side labels remain present when the
X-ray topology is connected, and that callers can request fail-fast behavior
for ambiguous cases.

## Existing Asset Readiness

Goal 005 and Goal 007 compact assets are useful but not sufficient for a
proper real-endpoint application inside Goal 024.

Available locally:

- Goal 005 corrected 1 keV X-ray map.
- Goal 005 tracer max line-of-sight map.
- Goal 005 tracer-defined cavity ellipse boundary.
- Goal 007 observational-product readiness metadata.

Missing for a defensible local application:

- a deterministic side-seed derivation table or mask;
- a parseable X-ray residual/topology layer, not only a rendered figure and
  metadata; and
- a reviewed rule for whether the real endpoint mask should use corrected
  X-ray level, residual contrast, tracer-seeded regions, or a hybrid of those
  layers.

Therefore Goal 024 keeps the actual gate synthetic. The real endpoint topology
remains unresolved until a later local existing-asset application protocol
derives parseable side-seed and X-ray residual/topology-mask tables without
rerunning HDF5/XRAiSE.

## Decision

The synthetic/local gate passes.

Decision label:

```text
HYBRID_TOPOLOGY_SYNTHETIC_GATE_PASSED_LOCAL_APPLICATION_PROTOCOL_NEXT
```

This means the method contract is locally viable:

- side labels can remain provenance proxies;
- X-ray topology can be classified separately;
- connected-envelope and two-separate-cavity cases are distinguishable; and
- ambiguous cases can be made explicit and fail-fast.

It does not mean the real endpoint has been reclassified, and it does not
authorize a bounded existing-output rerun.

## Recommendation

Recommended next goal shape:

```text
local_existing_asset_application_design
```

The next goal should stay local and use existing compact Goal 005/007 assets to
derive parseable side-seed and X-ray residual/topology-mask tables. It should
apply the helper to those local tables only after the side-seed and X-ray mask
protocol is deterministic and auditable.

Only after that local application protocol is complete should X-ray Cavities
consider a bounded existing-output endpoint application or rerun under an
explicit no-overwrite policy.

## Active Caveats

- This is not a publication-ready observable product.
- The real final `C-HI` endpoint topology is not reclassified by this goal.
- Tracer side labels remain provenance proxies, not X-ray-fitted cavities.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
- No remote work, product rerun, accepted-asset overwrite, broadening, or
  scientific-default change is authorized by this package.
