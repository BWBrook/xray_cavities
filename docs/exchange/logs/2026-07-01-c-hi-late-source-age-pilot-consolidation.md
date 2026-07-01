# 2026-07-01 - C-HI Late Source-Age Pilot Consolidation

## Scope

Goal 020 created a local-only review product consolidating the repaired Goal
019 late-source-age pilot against the accepted endpoint/refined-viewing surface.
No remote commands, SSH/SCP, qstat, Open OnDemand, PBS submission, finalizer,
retrieval, HDF5/XRAiSE recomputation, PLUTO production, PRAiSE/radio/cavity
regeneration, source-age substitution, broad batch, commit, push, cleanup, or
scientific-default change occurred.

## Evidence Read

- `docs/exchange/current_status.md`
- Goal 019 repair note and assets, including:
  - `repair_summary.json`
  - `repackage_validation_summary.csv`
  - `repackage_validation_summary.json`
  - `product_inventory.csv`
- Goal 017 refined-viewing consolidation note and assets.
- Goal 016 refined projection metrics and summary note.
- Goal 005 endpoint `0deg` note and compact X-ray summary.
- Goal 018 source-age sampling plan and metadata.

## Output

New science note:
`docs/science/c_hi_late_source_age_pilot_consolidation_2026-07-01.md`

New asset bundle:
`docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/`

Machine-readable assets:

- `per_age_view_comparison.csv`
- `source_age_trend_readiness.csv`
- `product_provenance.csv`
- `next_step_recommendation.csv`
- `late_source_age_pilot_consolidation_metadata.json`

## Result

Decision label:
`LATE_SOURCE_AGE_PILOT_READY_FOR_BOUNDED_C_HI_AGE_AXIS_NEXT_STEP`.

The repaired late-source-age pilot is finite, support-complete, and smoothly
close to the accepted endpoint/refined-viewing surface across `0/45/90deg`.
Corrected X-ray sums for output `46` are within about `2.9%` for `0deg` and
about `1.0%` for `45/90deg` of the endpoint controls. Output `49` tightens to
about `1.1%` for `0deg` and about `0.4%` for `45/90deg`. All comparison rows
have `0/0/0` raw/corrected/correction-ratio empty projected columns.

The original Goal 019 PBS record remains a scheduler caveat:
`706130.kunanyi-ohpc` has `Exit_status=1` and `Stageout_status=1`. The clean
no-rerun repaired archive SHA-256 remains:

`ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110`

## Recommendation

Prepare the next bounded C-HI age-axis extension after review: choose/preflight
one or two additional final-production C-HI source-age targets, preserve
`0/45/90deg`, use refined projection for nonzero views, and do not broaden to
comparison cases or a source-age sweep.

## Validation

Validation performed after writing the package:

- JSON parse for the new metadata.
- CSV parse, expected-column, and nonempty checks for the new CSV assets.
- `git diff --check`.
- Targeted unresolved-marker scan over the new science note, this exchange log,
  current status, and Goal 020 log.

No helper code was added, so no project tests were needed for Goal 020.
