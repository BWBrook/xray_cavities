# 2026-06-11 C-HI final production prove-out gap audit

## Context

Goal 004 was opened after acceptance of Goals 001-003 because the project
needed a prove-out audit, not another immediate data product. Goals 001-003
closed important sparse radio/truth bridge gaps, but they did not prove the
whole Honours workflow or readiness for broader production.

This was a docs/audit-only goal. No remote commands, Kunanyi staging, PBS jobs,
new data processing, observable generation, validation suites, document builds,
commits, or pushes were performed.

## Evidence Read

Read from the repo-local packet and documentation:

- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Goal.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Plan.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Runbook.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`
- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/Honours_Research_Plan.md`
- `docs/Honours_research_plan_feedback_SS_260424.txt`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/exchange/logs/2026-05-07-supervisor-meeting-2-plan-update.md`
- targeted Meeting 3 transcript sections showing Meeting 2 remains the active
  working plan and that Patrick/Stas wanted run parameters and grid choices
  surfaced before major production
- accepted Goal 001-003 logs
- final endpoint quick-look, particle endpoint, sparse-window, sparse PRAiSE
  loss-table, sparse radio bridge, and volume-coupled comparison notes
- older 5 Myr XRAiSE, cavity, particle-loss, particle-radio, and aligned
  comparison smoke notes
- the three-case science-run specification

## Headline Classifications

Proven for the first full `C-HI` endpoint:

- final endpoint integrity and readable final HDF5/particle products;
- restart/output-catalogue discipline for the completed run chain;
- final quick-look health;
- endpoint particle-state sanity;
- bounded sparse-particle window without dense all-history caches;
- Level 1 injected energy;
- Level 2 tracer-lobe truth at `tracer > 5e-3`.

Green but narrow:

- Goal 001/002 selected-ID sparse PRAiSE-compatible loss-table contract;
- Goal 003 final tracer-volume coupling into that sparse radio bridge.

Proxy-only or missing:

- final X-ray product for the 50 Myr endpoint;
- final cavity protocol at 50 Myr;
- Level 3 ambient-energy method;
- beam/instrument treatment;
- `45/90 deg` viewing-angle sampling;
- source-age sampling;
- mandatory `C-LO` and `G-LO` comparison cases.

## Products

Created:

```text
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv
```

Updated:

```text
docs/exchange/current_status.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md
```

This exchange log records the handoff:

```text
docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md
```

## Recommended Next Goal

Recommended Goal 005 shape:

```text
C-HI final endpoint X-ray/cavity alignment gate
```

Goal 005 should use the completed 50 Myr `C-HI` endpoint and initially the
`0 deg` view to produce a compact final X-ray plus cavity alignment product.
It should compare cavity `pV`, `4pV`, and age estimates against accepted
Level 1 injected energy, Level 2 tracer-lobe truth, and the Goal 003
volume-coupled radio scalars.

It should not launch a new PLUTO production run, broaden to `C-LO` or `G-LO`,
or add viewing-angle/source-age sampling until the final `C-HI` alignment gate
is reviewed.

## Questions

For Barry:

- Should Goal 005 allow bounded Kunanyi post-processing, or first freeze the
  final X-ray/cavity protocol locally?
- Should the first Goal 005 view stay strictly `0 deg`?

For Stas:

- Is the current ellipsoid plus ambient-shell cavity protocol acceptable for
  the first final endpoint pass?
- Which Level 3 ambient-energy definition should be targeted first?

For Patrick:

- Is the current XRAiSE/GRAiLE grid path sufficient for the first final
  endpoint X-ray product?
- Are any particle/radio runtime constraints needed before using the Goal 003
  radio scalars beside X-ray/cavity quantities?

## Validation

Docs/audit hygiene gates:

```text
git diff --check
passed

required marker search
no matches

stale next-action wording search
no matches
```

The exact validation commands and shell outputs are recorded in the Goal 004
log.
