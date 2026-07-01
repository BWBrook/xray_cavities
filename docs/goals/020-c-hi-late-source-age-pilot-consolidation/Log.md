# Goal 020 Log - C-HI Late Source-Age Pilot Consolidation

## 2026-07-01 Start

Start state:

- `pwd`: `/Users/bwbrook/papers/xray_cavities`
- branch: `main`
- short HEAD: `63f980e`
- `git status --short --branch`: dirty with the accepted Goal 019
  failure/repair package and current-status update present.

Read repo-local `AGENTS.md` first.

Boundary:

- local-only consolidation;
- no remote commands, Open OnDemand, SSH/SCP, qstat, Kunanyi staging, PBS jobs,
  finalizers, or retrieval;
- no HDF5/XRAiSE, PLUTO, PRAiSE, radio, or cavity reruns;
- no source-age substitution, early `5/10 Myr`, `C-LO`, `G-LO`,
  comparison-case processing, broad batch, commits, pushes, cleanup,
  `agent_comms` edits, or scientific-default changes.

## Evidence Read

- `docs/exchange/current_status.md`
- `docs/science/c_hi_late_source_age_pilot_repair_2026-07-01.md`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repair_summary.json`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_validation_summary.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_validation_summary.json`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/product_inventory.csv`
- `docs/science/c_hi_refined_viewing_angle_consolidation_2026-06-25.md`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/refined_trio_context.csv`
- `docs/science/assets/c_hi_refined_viewing_angle_consolidation_2026-06-25/historical_vs_refined_viewing_products.csv`
- `docs/science/c_hi_refined_projection_viewing_rerun_2026-06-25.md`
- `docs/science/assets/c_hi_refined_projection_viewing_rerun_2026-06-25/refined_projection_metrics.csv`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid/xraise_grid_smoke_summary.csv`
- `docs/science/c_hi_source_age_sampling_plan_2026-06-25.md`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/source_age_sampling_plan_metadata.json`
- `docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/proposed_sampling_plan.csv`

No sibling repositories, remote files, or external memory were read.

## Assets Created

Created:

- `docs/science/c_hi_late_source_age_pilot_consolidation_2026-07-01.md`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/per_age_view_comparison.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/source_age_trend_readiness.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/product_provenance.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/next_step_recommendation.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01/late_source_age_pilot_consolidation_metadata.json`
- `docs/exchange/logs/2026-07-01-c-hi-late-source-age-pilot-consolidation.md`

Updated:

- `docs/exchange/current_status.md`

No figure was created. The compact scalar tables were sufficient for the local
review surface, and no science products were regenerated.

## Result

Status: `complete_local_consolidation`.

Decision label:
`LATE_SOURCE_AGE_PILOT_READY_FOR_BOUNDED_C_HI_AGE_AXIS_NEXT_STEP`.

The repaired late-source-age pilot is finite, support-complete, and smoothly
close to the accepted endpoint/refined-viewing surface across `0/45/90deg`.
All comparison rows have zero raw/corrected/correction-ratio empty projected
columns. Nonzero late-age rows use `edge_overlap_uniform_cell_projection`.

The original Goal 019 scheduler caveat remains visible:
PBS job `706130.kunanyi-ohpc` exited with `Exit_status=1` and
`Stageout_status=1`, but the clean no-rerun repaired archive validates the
already-produced six-product surface. Clean archive SHA-256:

`ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110`

Recommended next goal shape:
bounded C-HI age-axis extension after review, choosing/preflighting one or two
additional final-production source-age targets while preserving `0/45/90deg`
and refined nonzero-view projection. Do not broaden to comparison cases or a
source-age sweep by implication.

## Validation

Passed:

- JSON parse for new metadata.
- CSV parse, expected-column, and nonempty checks for new CSV assets.
- `git diff --check`.
- Targeted unresolved-marker scan over new note/log/status files.

No helper code was added, so no project tests were needed.

Commands:

```bash
python3 - <<'PY'
import csv, json
from pathlib import Path
base = Path('docs/science/assets/c_hi_late_source_age_pilot_consolidation_2026-07-01')
json_path = base / 'late_source_age_pilot_consolidation_metadata.json'
with json_path.open() as f:
    data = json.load(f)
assert data['status'] == 'complete_local_consolidation'
assert data['decision_label'] == 'LATE_SOURCE_AGE_PILOT_READY_FOR_BOUNDED_C_HI_AGE_AXIS_NEXT_STEP'
checks = {
    'per_age_view_comparison.csv': {'age_role','output','timestep','source_age_myr','view','projected_accumulation','raw_xray_sum','corrected_xray_sum','empty_column_triplet','corrected_xray_sum_ratio_to_endpoint_same_view','validation_status','source_goal','source_asset_path'},
    'source_age_trend_readiness.csv': {'view','source_age_sequence_myr','corrected_sum_46','corrected_sum_49','corrected_sum_endpoint_51','corrected_sum_46_to_endpoint_ratio','corrected_sum_49_to_endpoint_ratio','projection_support_status','readiness_assessment'},
    'product_provenance.csv': {'product_key','role','source_goal','source_asset_path','status','note'},
    'next_step_recommendation.csv': {'option','rank','recommendation_label','why','minimum_scope','do_not_do','status'},
}
for name, required in checks.items():
    path = base / name
    with path.open(newline='') as f:
        reader = csv.DictReader(f)
        missing = required - set(reader.fieldnames or [])
        assert not missing, f'{name} missing columns: {sorted(missing)}'
        rows = list(reader)
        assert rows, f'{name} has no rows'
        if name == 'per_age_view_comparison.csv':
            assert len(rows) == 9, f'{name} expected 9 rows, got {len(rows)}'
            assert all(row['empty_column_triplet'] == '0/0/0' for row in rows), name
        if name == 'source_age_trend_readiness.csv':
            assert len(rows) == 3, f'{name} expected 3 rows, got {len(rows)}'
print('structured validation passed')
PY

git diff --check

targeted unresolved-marker scan over the new science note, exchange log,
current status, and Goal 020 log
```
