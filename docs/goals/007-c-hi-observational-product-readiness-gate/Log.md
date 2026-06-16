# Log: Goal 007 C-HI Observational Product Readiness Gate

## 2026-06-16 - Orchestrator Launch Packet

X-ray Cavities created this Goal 007 packet after Barry reported that
Patrick-agent had responded to the Goal 006 method-review thread.

Patrick-agent's current `Q-014` position is `HOLD` on broadening. The
superseding nuance is that the X-ray cavities may be generated, but the current
Goal 005 review plot does not show enough shocked-shell/cavity context to
serve as a production-quality observational product. Patrick-agent also asked
for the current sparse PRAiSE/radio products to remain labelled as particle
emissivity diagnostics until full raytraced radio surface-brightness products
are validated.

### Orchestrator Starting State

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
f1dc809
```

### Evidence Read By Orchestrator

- `AGENTS.md`
- `agent_comms/AGENTS.md`
- `agent_comms/threads/README.md`
- `docs/exchange/current_status.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/requests/open_questions.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `scripts/science/build_final_xray_cavity_alignment.py`
- `tests/test_final_xray_cavity_alignment.py`
- Goal 005 local figure:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/c_hi_final_endpoint_xray_cavity_alignment.png`
- Goal 005 X-ray axes and corrected map metadata:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid/`

### Orchestrator Notes

- The action repo was fast-forwarded from `15d8d28` to `f1dc809`.
- The fast-forward added Patrick-agent's clarification and moved `Q-014` to
  recently answered.
- Local Goal 005 X-ray axes span approximately `x = +/-199.15 kpc` and
  `z = +/-248.95 kpc`, while the current Goal 005 figure defaults to
  `xlim = +/-45 kpc` and `zlim = +/-230 kpc`.
- The corrected local X-ray map is finite and nonblank, with shape
  `1014 x 960` and maximum `2874403.7146 mJy sr^-1`.
- This packet deliberately prioritizes an X-ray observational-product
  readability gate before broadening. It does not try to settle the full radio
  observables requirement in the same breath unless a proper local path already
  exists.

### Delegation Boundary

`jet` should implement and validate this goal inside
`/Users/bwbrook/papers/xray_cavities` only. No commits, pushes, PBS
submissions, new production runs, remote heavy jobs, broadening, or manuscript
work are authorized.

`jet` must wake X-ray Cavities when complete or blocked, then stop.

## 2026-06-16 - jet action-agent start state

Ran the required repository update and identity checks before editing:

```text
git fetch --prune origin
git pull --ff-only
Already up to date.

pwd
/Users/bwbrook/papers/xray_cavities

git branch --show-current
main

git rev-parse --short HEAD
fba8e54

git status --short --branch
## main...origin/main
```

Start state was clean, on `main`, and even with `origin/main`. Proceeding
within the Goal 007 local-only product-readiness boundary.

## 2026-06-16 - jet evidence read and local product build

Read the required Goal 007 packet and repo-local context:

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/README.md`
- `agent_comms/AGENTS.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/README.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Goal.md`
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`
- `docs/goals/006-c-hi-final-method-review-decision-packet/Log.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `scripts/science/build_final_xray_cavity_alignment.py`
- `tests/test_final_xray_cavity_alignment.py`

Inspected only accepted repo-local compact assets from Goals 002, 003, and 005
as permitted by the packet. The Goal 005 X-ray axes span:

```text
x_kpc: -199.1538544 to 199.1538544
z_kpc: -248.9480743 to 248.9480743
corrected X-ray map shape: 1014 x 960
```

Implemented the local product builder:

```text
scripts/science/build_final_observational_product_readiness.py
```

The builder reads the accepted local corrected 1 keV X-ray map, tracer overlay,
tracer-defined cavity boundary overlay, and compact radio/provenance assets. It
writes:

```text
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/c_hi_final_observational_product_readiness.png
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/observational_product_readiness_metadata.json
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/xray_topology_readiness.csv
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/radio_observable_status.csv
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/product_provenance.csv
```

The product includes a wide-field corrected 1 keV X-ray panel, a cavity-focused
corrected X-ray panel, and a `41` pixel boxcar unsharp-mask residual diagnostic.
Tracer contours and the current cavity ellipses are labelled as diagnostic
overlays, not X-ray-fitted observational cavities.

Added focused tests:

```text
tests/test_final_observational_product_readiness.py
```

Initial focused validation:

```text
uv run pytest tests/test_final_observational_product_readiness.py -q
3 passed in 0.94s
```

## 2026-06-16 - jet science note, agent-comms, and handoff updates

Created the Goal 007 science note:

```text
docs/science/c_hi_final_observational_product_readiness_2026-06-16.md
```

Created the dated exchange log:

```text
docs/exchange/logs/2026-06-16-c-hi-final-observational-product-readiness.md
```

Created the Patrick-agent review thread:

```text
agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md
```

Added open question `Q-015` for Patrick-agent:

```text
Is the Goal 007 wide-field X-ray/cavity observational-product readiness package
adequate for review before broadening, and what topology or radio-observable
changes remain required?
```

Updated `docs/exchange/current_status.md` with a post-Goal-007 handoff and
updated `agent_comms/threads/README.md` so the new review thread is
discoverable.

Added the new Goal 007 asset bundle to `.gitattributes`, consistent with the
existing Goal 002/003/005 review-asset rules.

## 2026-06-16 - jet validation and completion state

Focused validation passed:

```text
uv run pytest tests/test_final_observational_product_readiness.py tests/test_final_xray_cavity_alignment.py -q
........                                                                 [100%]
8 passed in 1.38s

git diff --check
<no output>
```

Lightweight asset parse checks also passed:

```text
uv run python -m json.tool docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/observational_product_readiness_metadata.json
<parsed successfully>

xray_topology_readiness.csv: 4 rows; columns=aspect,status,evidence,limitation,recommendation
radio_observable_status.csv: 3 rows; columns=item,current_status,not_yet_validated_as,next_requirement
product_provenance.csv: 10 rows; columns=role,source,path,sha256

wc -c docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/c_hi_final_observational_product_readiness.png
699992
```

Completion status:

- Goal 007 local package is complete and ready for Patrick-agent review.
- Patrick-agent review question created as `Q-015`.
- The X-ray visual-context concern is addressed for review, but not closed as
  an X-ray-fitting method.
- Topology remains explicitly unresolved between connected shocked-shell
  envelope and two tracer-defined side ellipsoids.
- Sparse PRAiSE and particle-binned radio products remain
  particle-emissivity diagnostics, not validated radio observables.
- Recommended next goal depends on Patrick-agent's `Q-015` response:
  prioritize a narrow X-ray-based cavity/topology fitting method if
  Patrick-agent continues `HOLD`; otherwise plan full raytraced radio
  surface-brightness at two or more frequencies before treating radio maps as
  observables.

No remote commands, PBS jobs, PLUTO runs, heavy XRAiSE/cavity/PRAiSE/radio
workflows, broadening runs, Level 3 work, scientific-default changes, commits,
or pushes were performed.
