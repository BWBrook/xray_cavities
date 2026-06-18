# Runbook: Goal 010 C-HI Level 3 Broadening Decision Packet

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
docs/goals/010-c-hi-level3-broadening-decision-packet/Goal.md
docs/goals/010-c-hi-level3-broadening-decision-packet/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
agent_comms/README.md
agent_comms/AGENTS.md
agent_comms/requests/open_questions.md
agent_comms/threads/README.md
agent_comms/threads/2026-06-11-c-hi-final-method-review.md
agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md
docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md
docs/science/c_hi_final_observational_product_readiness_2026-06-16.md
docs/science/c_hi_final_level3_remote_extraction_closeout_2026-06-18.md
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_ambient_energy.csv
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_method_decisions.csv
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/level3_metadata.json
docs/Honours_Research_Plan.md
docs/codex_utas_phys_hons_meeting_2_action_plan.md
```

Read other repo-local files only as needed.

## Evidence To Preserve

Key accepted facts:

- Stas-agent `Q-012`: carry `pV`, `2.5pV`, and `4pV`; use `2.5pV` as the
  default non-relativistic interpretation.
- Stas-agent `Q-013`: Level 3 ambient energy must be completed before
  broadening.
- Patrick-agent `Q-015`: Goal 007 observational-product package is adequate
  before broadening; topology is visually connected/single-envelope pending
  X-ray-based cavity-fit confirmation; sparse radio products remain particle
  emissivity diagnostics.
- Goal 009:
  - thermal/kinetic status `green_level3_thermal_kinetic_closeout`;
  - overall status `partial_green_with_gravitational_blocker`;
  - bipolar thermal+kinetic `2.8016637452181852e60 erg`;
  - ratio to Level 1 injected energy `0.887793667838551`;
  - ratio to Level 2 tracer-lobe energy `2.018280864459599`;
  - ratio to adopted `2.5pV` `1.6293351404416438`;
  - ratio to `4pV` `1.0183344627760273`;
  - gravitational status `blocked_missing_potential`.

## Agent-Comms Thread Shape

Use a new thread unless an existing thread clearly fits better:

```text
agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md
```

Include:

- `Status: open`;
- canonical artefact links;
- context;
- current ask;
- requested response shape;
- a timestamped message from `jet` to `stas-agent`, `patrick-agent`, and `all`;
- separate Stas and Patrick questions.

Suggested response shape:

```text
Decision: PROCEED TO CONTROLLED BROADENING | PROCEED WITH CHANGES | HOLD
Required changes before broadening:
- State required changes, or `none`.
Gravity convention required first? yes/no/conditional
Recommended first broadening target:
- State the first narrow target, or `hold`.
Notes for Barry/X-ray Cavities:
- State any caveats or review priorities.
```

## Open Questions

Use new IDs after `Q-015`, likely:

- `Q-016` to `stas-agent`: does Goal 009 thermal+kinetic Level 3 satisfy the
  pre-broadening requirement while gravity remains blocked?
- `Q-017` to `patrick-agent`: are Goal 007 plus Goal 009 sufficient to open the
  first controlled broadening from the observational/runtime side?

Keep questions short in `open_questions.md`; put detail in the thread.

## Validation

Run:

```bash
git diff --check
rg -n 'TB''D|TO''DO|FIX''ME|place''holder' \
  docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md \
  docs/exchange/logs/2026-06-18-c-hi-level3-broadening-decision-packet.md \
  agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md \
  docs/exchange/current_status.md \
  agent_comms/requests/open_questions.md
```

For CSVs:

```bash
uv run python - <<'PY'
import csv
from pathlib import Path
for name in ["broadening_decision_matrix.csv"]:
    path = Path("docs/science/assets/c_hi_level3_broadening_decision_packet_2026-06-18") / name
    rows = list(csv.DictReader(path.open()))
    if not rows:
        raise SystemExit(f"{name}: no rows")
    print(f"{name}_rows={len(rows)}")
PY
```

Do not run project tests.

## Wake-Up Rule

When complete or blocked, wake X-ray Cavities with:

- status;
- changed files;
- validation results;
- current `git status --short --branch`;
- agent-comms thread path;
- new open-question IDs;
- headline recommendation;
- residual caveats;
- recommended next goal shape.
