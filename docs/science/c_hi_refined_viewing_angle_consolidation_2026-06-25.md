# C-HI Refined Viewing-Angle Consolidation

Date: 2026-06-25

## Summary

Goal 017 consolidates the accepted Goal 016 refined viewing-angle evidence into
a local review surface for the next project decision.

Decision label:

```text
REFINED_VIEWING_ANGLE_EVIDENCE_READY_FOR_NEXT_STEP_PLANNING
```

The refined projection method supersedes the historical `45 deg` and `90 deg`
projection products for future viewing-angle evidence. Goal 011 and Goal 012
remain preserved historical diagnostic artifacts; they should not be
overwritten or treated as the preferred future 45/90-degree evidence.

The accepted `0 deg` Goal 005 product remains the unchanged control baseline.
The accepted Goal 016 refined `45 deg` and `90 deg` products use:

```text
projection.projected_accumulation=edge_overlap_uniform_cell_projection
```

This consolidation is local-only. It does not run source-age sampling, open a
new science broadening step, or claim publication/manuscript readiness.

## Assets

Compact assets are under:

```text
docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/
```

Files:

| File | Purpose |
| --- | --- |
| `historical_vs_refined_viewing_products.csv` | accepted historical versus refined 45/90 products |
| `refined_trio_context.csv` | current 0/45/90-degree control surface using accepted 0 deg plus refined 45/90 deg |
| `product_provenance.csv` | source-goal and source-asset mapping for each product row |
| `next_step_readiness.csv` | next-step options and recommendation ranking |
| `refined_viewing_angle_consolidation_metadata.json` | compact status, supersession, and recommendation metadata |

The asset builder is:

```text
scripts/science/build_refined_viewing_angle_consolidation.py
```

It is covered by:

```text
tests/test_refined_viewing_angle_consolidation.py
```

## Historical Versus Refined Products

Goal 016 fixed the historical projected-column occupancy failure while
preserving raw/corrected X-ray pixel sums to roundoff.

| View | Historical goal | Future evidence | Raw empty columns | Corrected empty columns | Ratio empty columns | Raw sum delta | Corrected sum delta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| `45 deg` | Goal 011 | Goal 016 refined | `22 -> 0` | `22 -> 0` | `22 -> 0` | `0` | `-1.33e-15` |
| `90 deg` | Goal 012 | Goal 016 refined | `400 -> 0` | `400 -> 0` | `400 -> 0` | `6.31e-16` | `5.88e-16` |

Small max-value shifts are interpreted as bin-distribution effects of the
refined projected-bin remap:

| View | Raw max relative delta | Corrected max relative delta |
| --- | ---: | ---: |
| `45 deg` | `-0.000214` | `-0.000138` |
| `90 deg` | `0.001413` | `0.001067` |

The correction-ratio positive-pixel sum increases because previously empty
projected columns become populated. It is not treated as a conserved physical
scalar.

## Current Trio Context

The current preferred 0/45/90-degree control surface is:

| View | Product status | Source | Accumulator | Corrected X-ray max / 0 deg | Corrected X-ray sum / 0 deg |
| --- | --- | --- | --- | ---: | ---: |
| `0 deg` | accepted unchanged baseline | Goal 005 | direct y-axis sum baseline | `1` | `1` |
| `45 deg` | refined projection product | Goal 016 | edge overlap | `0.114734` | `0.446362` |
| `90 deg` | refined projection product | Goal 016 | edge overlap | `0.160718` | `0.631251` |

The refined products should be used for future viewing-angle evidence. The
historical Goal 011/012 products remain useful as diagnostics showing why the
projection-bin repair was required.

## Readiness Decision

Recommended next step:

```text
Prepare a tightly bounded C-HI source-age sampling plan after Kunanyi maintenance.
```

This should be a plan/control-surface goal, not an immediate source-age run.
The maintenance window starts on Friday 2026-06-26 at 09:00, so the next goal
should not stage or submit remote work unless X-ray Cavities explicitly
authorizes it after the outage clears.

Next-step ranking:

| Rank | Option | Readiness | Recommendation |
| ---: | --- | --- | --- |
| `1` | tightly bounded `C-HI` source-age sampling after maintenance | recommended next planning goal | write a local plan/packet for a small post-maintenance run |
| `2` | X-ray/cavity topology refinement | important but not next blocker | keep near-term if source-age planning exposes topology sensitivity |
| `3` | radio observable/raytracing method work | hold for method lane | defer until after the next C-HI sampling control surface is chosen |
| `4` | gravitational Level 3 convention work | blocked missing potential | keep as a separate convention goal |
| `5` | comparison-case preparation for `C-LO`/`G-LO` | hold | defer comparison-case preparation |

Rationale: the projection-bin artifact that blocked clean use of the
viewing-angle trio is now repaired. The remaining X-ray/cavity topology caveat
is important, but it does not by itself require another local method-refinement
goal before planning a tightly bounded within-`C-HI` source-age probe.

## Caveats Preserved

- Projection products remain review/control-surface evidence, not
  publication-ready observables.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse particle-binned radio remains diagnostic, not a validated radio
  observable.
- Level 3 gravitational energy remains `blocked_missing_potential`.
- The `pV`, adopted `2.5pV`, and `4pV` cavity-energy convention remains active.
- `C-LO`, `G-LO`, comparison-case processing, and broad batches remain on hold.

## Non-Claims

- No remote commands, Open OnDemand, SSH/SCP, Kunanyi staging, `qstat`, PBS
  submission, finalizer, retrieval, or job polling occurred.
- No PLUTO production, source-age sampling, `C-LO`, `G-LO`, comparison-case
  processing, PRAiSE/radio/cavity regeneration, heavy XRAiSE rerun, or
  scientific-default change occurred.
- No commits, pushes, staging, cleanup, `agent_comms` changes, or Stas/Patrick
  escalation occurred.
- Accepted Goal 005/011/012/016 assets were not overwritten.
