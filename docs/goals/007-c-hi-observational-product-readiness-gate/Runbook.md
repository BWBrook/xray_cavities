# Runbook: Goal 007 C-HI Observational Product Readiness Gate

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
docs/goals/007-c-hi-observational-product-readiness-gate/Goal.md
docs/goals/007-c-hi-observational-product-readiness-gate/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
agent_comms/README.md
agent_comms/AGENTS.md
agent_comms/requests/open_questions.md
agent_comms/threads/README.md
agent_comms/threads/2026-06-11-c-hi-final-method-review.md
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Goal.md
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md
docs/goals/006-c-hi-final-method-review-decision-packet/Log.md
docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md
docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md
docs/Honours_Research_Plan.md
docs/codex_utas_phys_hons_meeting_2_action_plan.md
scripts/science/build_final_xray_cavity_alignment.py
tests/test_final_xray_cavity_alignment.py
```

Read other repo-local files only as needed for exact paths or existing
contracts. Do not read outside this repo.

## Accepted Local Inputs

Use accepted local compact assets:

```text
docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/
```

Core X-ray files:

```text
xraise_grid/x_kpc.tsv
xraise_grid/z_kpc.tsv
xraise_grid/xray_1kev_xraise_corrected_mjy_sr.tsv
xraise_grid/tracer_max_los.tsv
xraise_grid/xraise_grid_smoke_metadata.json
xraise_grid/xraise_grid_smoke_summary.csv
cavity_stub/cavity_ellipse_boundary_0deg.tsv
cavity_stub/cavity_stub_summary.csv
final_xray_cavity_alignment_metadata.json
final_xray_cavity_alignment_metrics.csv
```

Do not require raw X-ray or correction-ratio products unless they are already
available locally or can be derived from accepted local inputs without a remote
job. If a raw/corrected comparison is essential and missing, report that as a
blocked input rather than substituting an unsupported claim.

## Figure And Metadata Requirements

The product should create:

- one wide-field X-ray context figure using the available `x_kpc` and `z_kpc`
  axes or a clearly justified wide field of view;
- one cavity-focused X-ray figure or panel;
- one contrast/residual/unsharp-mask diagnostic;
- overlays for tracer and current cavity boundaries, labelled as overlays;
- metadata recording:
  - input files;
  - x/z field of view;
  - image stretch and color scale;
  - contrast/residual method and parameter values;
  - tracer threshold;
  - projection angle;
  - current cavity-boundary source;
  - radio-diagnostic limitation.

Use stable machine-readable metadata, such as JSON plus compact CSV tables.

## Topology And Cavity-Fit Statement

The science note must explicitly answer:

- Does the X-ray product read as two separate lobes, one connected shocked-shell
  envelope, or unresolved with current diagnostics?
- Are current ellipses derived from X-ray data or from tracer/hydro extents?
- If an observational X-ray cavity fit is not yet implemented, what exact
  input or method is missing?

Do not present tracer-derived fits as X-ray-fitted observational cavity
measurements.

## Agent-Comms Request

Create or update a Patrick-agent review thread. A new thread is appropriate if
the product package is clearer as a distinct follow-up to `Q-014`.

Use this response shape:

```text
Decision: PRODUCT ADEQUATE | ADEQUATE WITH CHANGES | HOLD
Required changes before broadening:
- ...
X-ray topology interpretation:
- two lobes | connected envelope | unresolved
Radio-observable status:
- ...
Notes for Barry/X-ray Cavities:
- ...
```

If updating `agent_comms/requests/open_questions.md`, add the next available
question ID and mark it `open`.

## Validation

Run:

```bash
uv run pytest tests/test_final_observational_product_readiness.py tests/test_final_xray_cavity_alignment.py -q
git diff --check
```

If no new pytest target exists, run narrow parse/asset checks that prove:

- generated images exist and are non-empty;
- metadata JSON parses;
- CSV tables parse and have required columns;
- the wide-field product records a wider x-field than the Goal 005 main figure.

Do not run the full suite unless the implementation changes shared scripts.
Do not submit PBS jobs.

## Hard Stops

Stop immediately before:

- submitting a PBS job;
- running a long remote command;
- changing scientific defaults;
- changing PLUTO/XRAiSE/PRAiSE runtime contracts;
- broadening to new views, source ages, or comparison cases;
- claiming final radio-observable validation from sparse particle maps.

If a large PBS job is proposed, wake X-ray Cavities with the exact reason. If a
future authorized large PBS job is submitted and verified queued/running, wake
X-ray Cavities and stop until Barry reports the PBS completion email or gives
an explicit re-check instruction.

## Wake-Up Rule

When complete or blocked, send a short wake-up to X-ray Cavities with:

- status;
- changed files;
- validation results;
- current `git status --short --branch`;
- product asset paths;
- agent-comms thread path;
- Patrick-agent review question ID, if created;
- whether the product is ready for Patrick-agent review;
- recommended next goal.
