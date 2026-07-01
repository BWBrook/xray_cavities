# C-HI Late Source-Age Pilot Consolidation

Date: 2026-07-01
Status: `complete_local_consolidation`
Decision label: `LATE_SOURCE_AGE_PILOT_READY_FOR_BOUNDED_C_HI_AGE_AXIS_NEXT_STEP`

## Scope

This note consolidates the repaired Goal 019 late-source-age pilot against the
accepted endpoint/refined-viewing surface. It is a local review product only.
No remote commands, PBS work, retrieval, HDF5/XRAiSE recomputation, source-age
substitution, endpoint rerun, radio/cavity regeneration, or scientific-default
change was performed for Goal 020.

The repaired pilot surface is:

- output `46`, `Timestep_46`, source age `44.9992713373 Myr`;
- output `49`, `Timestep_49`, source age `47.9991267252 Myr`;
- views `0deg`, `45deg`, and `90deg`.

The endpoint/reference surface is:

- output `51`, `Timestep_51`, source age `50.000000000008 Myr`;
- `0deg` from accepted Goal 005;
- refined `45deg` and `90deg` from accepted Goal 016 and consolidated by
  Goal 017.

## Evidence Used

Machine-readable assets for this consolidation are under:

`docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/`

Key inputs were the Goal 019 repaired no-rerun validation tables and clean
archive, the Goal 017 refined-viewing consolidation, the Goal 016 refined
projection metrics, the Goal 005 endpoint `0deg` baseline, and the Goal 018
source-age sampling contract.

The Goal 019 scheduler caveat remains visible: PBS job
`706130.kunanyi-ohpc` exited with `Exit_status=1` and `Stageout_status=1`.
The accepted repair isolates that failure to
`wrapper_archive_race_live_directory_changed_during_tar`; the clean no-rerun
archive validates the six already-produced products. The clean archive SHA-256
is:

`ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110`

## Consolidated Result

All six late-source-age pilot products remain finite, positive, and
support-complete in the compact repaired archive. All raw, corrected, and
correction-ratio empty projected-column counts are zero. The nonzero views
declare `edge_overlap_uniform_cell_projection`, matching the refined
projection contract.

Corrected X-ray sums relative to the same-view endpoint control:

| View | Output 46 / endpoint | Output 49 / endpoint | Support status |
| --- | ---: | ---: | --- |
| `0deg` | `1.02921391765` | `1.01140612976` | `0/0/0` empty columns |
| `45deg` | `1.00966638372` | `1.00394731058` | `0/0/0` empty columns |
| `90deg` | `1.00966638372` | `1.00394731058` | `0/0/0` empty columns |

Raw X-ray sums show the same late-age convergence pattern. From output `46` to
output `49` to the endpoint, the compact X-ray scalars move smoothly toward
the accepted endpoint/refined-viewing surface. This supports treating the
repaired Goal 019 product as a useful pilot review surface despite the original
PBS scheduler caveat.

## Interpretation

The late-source-age pilot is strong enough to justify a next bounded C-HI
age-axis step after X-ray Cavities review. That next step should remain narrow:
choose and preflight one or two additional final-production C-HI source-age
targets, keep the `0/45/90deg` compact X-ray/tracer product surface, use the
refined accumulator for nonzero views, and reuse the accepted endpoint control
rather than rerunning it by default.

This consolidation does not authorize a broad source-age sweep, early `5/10
Myr` branch, `C-LO`, `G-LO`, comparison-case processing, or publication-ready
observable claims.

## Active Caveats

- This is a late-source-age pilot review, not publication-ready observables.
- Original PBS job `706130.kunanyi-ohpc` remains nonzero; acceptance rests on
  the clean no-rerun repaired archive and validation evidence.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse radio remains diagnostic only.
- Level 3 gravity remains `blocked_missing_potential`.
- The `pV` / adopted `2.5pV` / `4pV` convention remains active.
- Refined projection is the preferred method for future nonzero-view X-ray
  products.

## Recommendation

Recommended next goal shape:
`bounded C-HI age-axis extension after review`.

The next goal should be submission/preflight-oriented only if authorized after
review. It should not broaden to comparison cases or broad production work by
implication from this pilot.

No figure was created for Goal 020. The existing compact scalar tables are
sufficient for this consolidation, and no science product was regenerated.
