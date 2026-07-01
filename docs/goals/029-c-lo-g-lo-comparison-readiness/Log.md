# Goal 029 Log - C-LO/G-LO Comparison Readiness

Date: 2026-07-01

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `c812901`.
- Git status at start: `## main...origin/main`.
- Fast-forward check: `git pull --ff-only` reported already up to date.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

This goal is local-only. No remote commands, Open OnDemand, SSH/SCP, `qstat`,
Kunanyi staging, PBS jobs, finalizers, retrieval, polling, remote file reads,
HDF5/XRAiSE reruns, PLUTO, PRAiSE, radio, cavity regeneration, endpoint rerun,
source-age substitution, `C-LO`/`G-LO` processing, comparison-case compute,
early-age branch, broad source-age sweep, publication-facing claims,
scientific-default changes, commits, pushes, cleanup, or `agent_comms` edits
are authorized.

## Evidence Read

- `docs/exchange/current_status.md`.
- Goal 028 science note, log, metadata, `next_branch_decision_matrix.csv`,
  `expert_escalation_thresholds.csv`, control-surface register, and caveat
  register.
- `docs/science/three_case_spec.md`.
- `docs/Honours_Research_Plan.md` and
  `docs/codex_utas_phys_hons_meeting_2_action_plan.md` only enough to align
  comparison-case scope.
- Goal 005, Goal 016, Goal 017, Goal 021, Goal 022, and Goal 027 compact
  notes/assets as accepted `C-HI` contracts to inherit.
- Repo-local `scripts/science/render_three_case_configs.py` and
  `scripts/kunanyi/jet_setup_production_template.pbs` to identify existing
  comparison-case scaffolding without running it.
- Repo-local environment gate notes and asset inventory for Stewart
  `cluster_002003` and `group_002031`.

## Local Findings

- `C-LO` and `G-LO` are defined in the frozen three-case specification:
  `C-LO` is the low-power cluster baseline science anchor and `G-LO` is the
  low-power group environment-dependence case.
- `scripts/science/render_three_case_configs.py` contains case specs for all
  three cases and can render dry-run bundles when supplied valid environment
  assets. It was inspected only; it was not run.
- `scripts/kunanyi/jet_setup_production_template.pbs` is a generic
  production-oriented template, but there is no Goal-ready `C-LO` or `G-LO`
  wrapper in this repo yet.
- The local ignored Stewart tabulated CSVs are not visible in this checkout at
  the documented paths:
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv` and
  `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv`.
  Prior docs record that these assets existed and passed Nectar/Kunanyi
  environment gates, so this is an operational preflight requirement rather
  than a science-default change.

## Decision

Decision label:
`C_LO_G_LO_READINESS_LOCAL_DOCS_SUFFICIENT_C_LO_PREFLIGHT_NEXT`.

The local docs/config evidence is sufficient for a readiness decision. The
selected next branch is a Barry-authorized bounded `C-LO` config and asset
preflight packet. `G-LO` should remain queued behind `C-LO` unless Barry
explicitly chooses a different launch order.

## Validation

- No helper code was added, so no project tests were needed for Goal 029.
- `uv run python -m json.tool docs/science/assets/c_lo_g_lo_comparison_readiness_2026-07-01/comparison_readiness_metadata.json`
  passed.
- CSV parse, expected-column, and nonempty checks passed for:
  - `comparison_case_readiness_matrix.csv`
  - `inherited_c_hi_contracts.csv`
  - `local_blocker_register.csv`
  - `future_preflight_requirements.csv`
  - `authorization_thresholds.csv`
  - `next_step_recommendation.csv`
- `git diff --check` passed.
- Targeted unresolved-marker scan passed after validation text was updated.
