# Runbook: Goal 004 C-HI Final Production Prove-out Gap Audit

## Launch

Start from:

```bash
cd /Users/bwbrook/papers/xray_cavities
pwd
git status --short --branch
git rev-parse --short HEAD
```

Record the output in `Log.md` before editing.

## Read Order

Read:

```text
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Goal.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
docs/Honours_Research_Plan.md
docs/Honours_research_plan_feedback_SS_260424.txt
docs/codex_utas_phys_hons_meeting_2_action_plan.md
docs/exchange/logs/2026-05-07-supervisor-meeting-2-plan-update.md
docs/codex_utas_phys_hons_meeting_3_transcript.md
docs/goals/001-sparse-praise-loss-interface/Log.md
docs/goals/002-final-sparse-praise-loss-table/Log.md
docs/goals/003-final-volume-coupled-comparison/Log.md
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md
docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md
docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
```

Read other repo-local science notes only as needed to classify a matrix row.
Do not read outside this repo.

## Evidence Matrix

Create:

```text
docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv
```

Use these columns:

```text
component,status,evidence,next_action,notes
```

Use stable status values:

```text
proven
green_narrow
proxy_only
missing
needs_decision
```

Include at least these components:

```text
meeting_2_alignment
final_endpoint_integrity
restart_and_output_catalogue
early_diagnostic_coverage
final_quicklook_health
level1_injected_energy
level2_tracer_lobe_truth
level3_ambient_energy
final_xray_observable
final_cavity_protocol
radio_sparse_praise_loss_table
radio_volume_coupling
beam_or_instrument_model
viewing_angle_sampling
source_age_sampling
comparison_suite_readiness
next_major_run_readiness
```

## Audit Note

Create:

```text
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
```

Required sections:

- `Summary`
- `What Goals 001-003 Proved`
- `What The First Full C-HI Run Proves`
- `What Remains Provisional Or Missing`
- `Matrix`
- `Recommended Goal 005`
- `Questions Or Decisions`

The audit should be direct and useful. It is acceptable for many rows to be
`missing` or `proxy_only`; that is the point of this goal.

## Current Status Update

Update the top of `docs/exchange/current_status.md` so the latest section
points to the new prove-out audit and no longer frames the next action as
manuscript-facing.

Keep the update compact. Do not rewrite older history.

## Exchange Log

Create:

```text
docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md
```

Capture:

- why the audit was opened;
- what evidence was read;
- headline classifications;
- recommended next goal;
- validation commands.

## Validation

Run:

```bash
git diff --check
for marker in TB''D TO''DO place''holder; do
  rg -n "$marker" \
    docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md \
    docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
    docs/exchange/current_status.md
done
rg -n "manuscript-facing|publication-ready" \
  docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
  docs/exchange/current_status.md
```

The final `rg` command should either return no matches or only matches that
are quoted deliberately as stale wording being corrected. If there are
deliberate matches, explain them in `Log.md`.

## Hard Stops

Stop immediately before:

- running remote commands;
- launching jobs;
- running data-processing scripts;
- editing files outside this repo;
- editing UTAS AGN source checkouts;
- making manuscript-readiness claims;
- recommending a new major production run without a clear intervening
  prove-out gate;
- committing or pushing.

## Wake-Up Rule

When complete or blocked, send a short wake-up to the X-ray Cavities
orchestrator thread. Include:

- status;
- changed files;
- validation result;
- current `git status --short --branch`;
- headline audit conclusion;
- recommended Goal 005 shape;
- questions for Barry/Stas/Patrick.
