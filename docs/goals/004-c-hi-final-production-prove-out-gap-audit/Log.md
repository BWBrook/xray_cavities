# Log: Goal 004 C-HI Final Production Prove-out Gap Audit

## 2026-06-11 - X-ray Cavities goal creation

Created by the X-ray Cavities orchestrator after Barry corrected the proposed
post-Goal-003 direction.

Action repo state before writing this packet:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 6a35952
```

Goal 003 accepted a final-endpoint volume-coupled sparse PRAiSE comparison
product. Barry then clarified that the broader project remains in prove-out of
the first full production run, with major synthetic-observable, truth,
sampling, and comparison-suite work still ahead. Goal 004 is therefore a
bounded audit goal: classify what the first full `C-HI` run and Goals 001-003
have actually proven, identify gaps, and recommend the next prove-out goal.

No project implementation, remote staging, remote job, data workflow, or
validation run was performed by the orchestrator while creating this packet.

## 2026-06-11 - jet start state

Ran the required fast-forward check first:

```text
/Users/bwbrook/papers/xray_cavities
Already up to date.
```

Starting state before audit edits:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 1884ec6
```

This differs from the packet's expected `6a35952` because the checkout had
already fast-forwarded to a newer clean published state before Goal 004
execution. The worktree was clean and even with `origin/main`.

## 2026-06-11 - jet evidence read and audit synthesis

Read the Goal 004 packet first:

```text
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Goal.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Plan.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Runbook.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md
```

Then read the required repo-local evidence surface:

```text
AGENTS.md
README.md
docs/exchange/current_status.md
docs/Honours_Research_Plan.md
docs/Honours_research_plan_feedback_SS_260424.txt
docs/codex_utas_phys_hons_meeting_2_action_plan.md
docs/exchange/logs/2026-05-07-supervisor-meeting-2-plan-update.md
docs/codex_utas_phys_hons_meeting_3_transcript.md (targeted sections only)
docs/goals/001-sparse-praise-loss-interface/Log.md
docs/goals/002-final-sparse-praise-loss-table/Log.md
docs/goals/003-final-volume-coupled-comparison/Log.md
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md
docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md
docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md
docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md
docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
docs/science/c_hi_xraise_grid_smoke_2026-05-10.md
docs/science/c_hi_cavity_stub_2026-05-10.md
docs/science/c_hi_observable_smoke_2026-05-10.md
docs/science/c_hi_particle_loss_smoke_2026-05-10.md
docs/science/c_hi_particle_radio_smoke_2026-05-10.md
docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md
docs/science/c_hi_run_configuration_audit_2026-05-13.md
docs/science/c_hi_8node_mini_production_2026-05-13.md
docs/science/three_case_spec.md
```

Meeting 3 targeted read confirmed that Barry and Patrick treated the Meeting 2
action plan as the active working plan, with no major new science plan needed
until the current plan was worked through. It also reinforced Patrick/Stas'
request to surface simulation parameters, modules, grid choices, and output
sizes before major production decisions.

Classification synthesis:

- `proven`: final endpoint integrity, restart/output catalogue, early
  diagnostics, final quick-look health, endpoint particle state, bounded sparse
  particle window, Level 1 injected energy, and Level 2 tracer-lobe truth.
- `green_narrow`: accepted selected-ID sparse PRAiSE-compatible loss-table
  contract and final tracer-volume coupling into that sparse bridge.
- `proxy_only`: final cavity protocol, because only 5 Myr smoke/stub products
  currently exist and age estimates remain provisional.
- `missing`: final 50 Myr X-ray product, beam/instrument treatment,
  viewing-angle sampling, source-age sampling, and the `C-LO`/`G-LO`
  comparison-suite cases.
- `needs_decision`: Level 3 ambient energy method and readiness for any next
  major production run.

Created the machine-readable matrix:

```text
docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv
```

Created the audit note:

```text
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
```

Created the exchange log:

```text
docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md
```

Updated `docs/exchange/current_status.md` so the latest next action is a
prove-out-aligned Goal 005 recommendation, not a broader interpretation or
new-production step.

Recommended Goal 005 shape:

```text
C-HI final endpoint X-ray/cavity alignment gate
```

The recommended Goal 005 should use the completed 50 Myr `C-HI` endpoint and
initially the `0 deg` view to produce a compact final X-ray plus cavity
alignment product, comparing cavity `pV`, `4pV`, and age estimates against
accepted Level 1 injected energy, Level 2 tracer-lobe truth, and the Goal 003
volume-coupled radio scalars. It should not launch a new PLUTO production run.

## 2026-06-11 - jet docs/audit validation

Validation run:

```text
git diff --check
passed
```

Marker search:

```text
for marker in TB''D TO''DO place''holder; do
  rg -n "$marker" \
    docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md \
    docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
    docs/exchange/current_status.md
done

marker=TBD
marker=TODO
marker=placeholder
```

No marker matches were returned.

Stale next-action wording search:

```text
rg -n "manuscript-facing|publication-ready" \
  docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
  docs/exchange/current_status.md
```

No matches were returned. The first attempt at the marker search had a shell
quoting error and was rerun with the packet's intended shell syntax; no files
were changed by that failed command.

## 2026-06-11 - X-ray Cavities review and acceptance

The X-ray Cavities orchestrator reviewed the Goal 004 audit note, proof/gap
matrix, exchange log, current-status update, and goal log.

Fresh orchestrator validation:

```text
git diff --check
passed

for marker in TB''D TO''DO place''holder; do
  printf 'marker=%s\n' "$marker"
  rg -n "$marker" \
    docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md \
    docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
    docs/exchange/current_status.md
done

marker=TBD
marker=TODO
marker=placeholder
no matches

rg -n "manuscript-facing|publication-ready|final-observable" \
  docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md \
  docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md \
  docs/exchange/current_status.md
no matches
```

Decision: accepted as a green docs/audit-only prove-out gap audit. The audit
correctly treats the first full 50 Myr `C-HI` run as a credible prove-out
anchor, not as completion of the X-ray/cavity, Level 3, beam/instrument,
viewing-angle, source-age, or comparison-case workflow.

Recommended next direction: Goal 005 should be a narrow final `C-HI` endpoint
X-ray/cavity alignment gate at `50 Myr`, initially `0 deg`, with no new PLUTO
production run and no broadening to `C-LO`/`G-LO` before that gate is reviewed.
