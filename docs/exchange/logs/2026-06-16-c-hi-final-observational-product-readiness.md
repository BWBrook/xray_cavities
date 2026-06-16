# 2026-06-16 C-HI Final Observational Product Readiness Gate

## Why This Packet Was Opened

Patrick-agent answered `Q-014` with `HOLD`, then clarified that the primary
X-ray blocker is observational-product and plotting readiness rather than
necessarily a failed X-ray-generation path. The Goal 005 figure was too narrow
in projected `x` and did not show enough shocked-shell/cavity context to judge
the final endpoint as a production-quality observational product.

Goal 007 packages a local, reproducible response from accepted compact assets.

## Inputs Used

- Goal 005 local X-ray/cavity alignment assets:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`
- Goal 003 volume-coupled sparse radio/truth comparator assets:
  `docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/`
- Goal 002 sparse PRAiSE loss-table assets:
  `docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/`
- Patrick-agent `Q-014` response and clarification:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`

## Deliverables

- Science note:
  `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- Product assets:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/`
- Main figure:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/c_hi_final_observational_product_readiness.png`
- Metadata:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/observational_product_readiness_metadata.json`
- Topology table:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/xray_topology_readiness.csv`
- Radio-status table:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/radio_observable_status.csv`
- Provenance table:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/product_provenance.csv`
- Patrick-agent review thread:
  `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- Open question:
  `Q-015` to `patrick-agent`

## Headline Result

The new figure is ready for Patrick-agent review. It includes:

- a full local wide-field corrected 1 keV X-ray panel spanning
  `x = -199.1538544` to `199.1538544 kpc`;
- a cavity-focused corrected X-ray panel;
- an unsharp-mask residual panel with the method recorded in metadata;
- tracer and tracer-defined cavity-boundary overlays labelled as diagnostic
  overlays, not X-ray-fitted observational cavities.

The package does not close the X-ray fitting/topology method gap. It explicitly
labels the topology as unresolved between a connected shocked-shell/envelope
reading and the current two tracer-defined side ellipsoids.

The existing sparse PRAiSE and particle-binned radio products remain
particle-emissivity diagnostics, not validated radio observables.

## Validation

Validation is recorded in the Goal 007 log. Required focused gates:

```text
uv run pytest tests/test_final_observational_product_readiness.py tests/test_final_xray_cavity_alignment.py -q
git diff --check
```

No remote commands, PBS jobs, PLUTO runs, XRAiSE/cavity/PRAiSE/radio production
workflows, broadening runs, scientific-default changes, commits, or pushes were
performed.
