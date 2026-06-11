# Runbook: Goal 006 C-HI Final Method Review Decision Packet

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
docs/goals/006-c-hi-final-method-review-decision-packet/Goal.md
docs/goals/006-c-hi-final-method-review-decision-packet/Plan.md
agent_comms/README.md
agent_comms/AGENTS.md
agent_comms/requests/open_questions.md
agent_comms/threads/README.md
docs/exchange/current_status.md
docs/Honours_Research_Plan.md
docs/codex_utas_phys_hons_meeting_2_action_plan.md
agent_comms/threads/2026-05-11-c-hi-science-interpretation.md
agent_comms/threads/2026-05-11-production-scale-allocation.md
agent_comms/threads/2026-05-13-c-hi-grid-config-review.md
agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md
docs/goals/003-final-volume-coupled-comparison/Log.md
docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md
```

Read other repo-local files only as needed for exact evidence paths or
agent-comms formatting. Do not read outside this repo.

## Decision Matrix

Create:

```text
docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv
```

Use these columns:

```text
component,current_evidence,risk_or_caveat,decision_needed,recommended_branch,reviewer
```

Include at least these components:

```text
enthalpy_convention_pV_2p5pV_4pV
cavity_age_estimates
ambient_shell_pressure
ellipsoid_geometry_and_depth
level1_injected_energy_comparison
level2_tracer_lobe_comparison
level3_ambient_energy
goal003_radio_comparator
viewing_angle_sampling
source_age_sampling
comparison_case_broadening
large_pbs_job_stop_rule
```

## Science Decision Note

Create:

```text
docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md
```

Required sections:

- `Summary`
- `Evidence Base`
- `Current Method Choices`
- `Decision Matrix`
- `Recommended Branch`
- `Questions For Stas-Agent`
- `Questions For Patrick-Agent`
- `Operational Rule For Large PBS Jobs`
- `Non-Goals`

Keep the note decision-oriented. Do not re-summarize every past goal.

## Agent-Comms Thread

Create:

```text
agent_comms/threads/2026-06-11-c-hi-final-method-review.md
```

Use the agent-comms thread template. The thread should:

- name Stas-agent and Patrick-agent as primary reviewers;
- link to the decision note, matrix, Goal 005 science note, Goal 004 audit,
  and current status;
- ask for a response in this shape:

```text
Decision: ACCEPT CURRENT METHOD | ACCEPT WITH CHANGES | HOLD
Required changes before broadening:
- ...
Can proceed before Level 3? yes/no/conditional
Notes for Barry/X-ray Cavities:
- ...
```

Ask Stas-agent specifically about:

- `2.5pV` versus `4pV` interpretation for non-relativistic plasma;
- ambient-shell pressure and cavity age assumptions;
- whether Level 3 ambient energy is required before broadening.

Ask Patrick-agent specifically about:

- whether the XRAiSE/GRAiLE and particle/radio runtime contracts are adequate
  for controlled replication;
- whether any runtime/provenance constraints should be locked before views or
  comparison cases.

## Open Questions

If updating:

```text
agent_comms/requests/open_questions.md
```

add new rows after current open rows. Use the next available question IDs and
mark them `open`.

## Exchange Log

Create:

```text
docs/exchange/logs/2026-06-11-c-hi-final-method-review-decision-packet.md
```

Capture:

- why the packet was opened;
- evidence read;
- headline recommendation;
- agent-comms thread path;
- validation commands.

## Validation

Run:

```bash
git diff --check
rg -n "TB''D|TO''DO|place''holder|TBD|TODO|placeholder" \
  docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md \
  docs/exchange/logs/2026-06-11-c-hi-final-method-review-decision-packet.md \
  agent_comms/threads/2026-06-11-c-hi-final-method-review.md \
  docs/exchange/current_status.md \
  agent_comms/requests/open_questions.md
```

If the matrix is created, run:

```bash
uv run python - <<'PY'
import csv
from pathlib import Path
path = Path("docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv")
rows = list(csv.DictReader(path.open()))
required = {"component", "current_evidence", "risk_or_caveat", "decision_needed", "recommended_branch", "reviewer"}
missing = required - set(rows[0])
if missing:
    raise SystemExit(f"missing columns: {sorted(missing)}")
if len(rows) < 8:
    raise SystemExit(f"too few rows: {len(rows)}")
print(f"method_decision_matrix_rows={len(rows)}")
PY
```

Do not run project tests for this docs-only goal.

## Hard Stops

Stop immediately before:

- running remote commands;
- submitting PBS jobs;
- changing scripts, wrappers, thresholds, defaults, or data products;
- promoting an unresolved review request into a durable decision;
- recommending immediate comparison-case production without the requested
  method review.

## Wake-Up Rule

When complete or blocked, send a short wake-up to X-ray Cavities with:

- status;
- changed files;
- validation results;
- current `git status --short --branch`;
- agent-comms thread path;
- headline recommendation;
- open questions for Stas-agent and Patrick-agent.
