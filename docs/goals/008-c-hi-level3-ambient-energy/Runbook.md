# Runbook: Goal 008 C-HI Level 3 Ambient Energy Method Gate

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
docs/goals/008-c-hi-level3-ambient-energy/Goal.md
docs/goals/008-c-hi-level3-ambient-energy/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
agent_comms/requests/open_questions.md
agent_comms/threads/2026-06-11-c-hi-final-method-review.md
agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md
docs/Honours_Research_Plan.md
docs/codex_utas_phys_hons_meeting_2_action_plan.md
docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md
docs/science/c_hi_final_observational_product_readiness_2026-06-16.md
scripts/science/pluto_h5_truth_extract.c
scripts/science/build_final_volume_coupled_comparison.py
tests/test_final_volume_coupled_comparison.py
```

Read other repo-local files only as needed for exact paths, HDF5 contracts, or
unit conventions.

## Candidate Existing Inputs

Final endpoint:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Known relevant production-chain paths from current status include:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/
```

Do not assume a valid baseline exists. Verify it.

Accepted local truth and comparison assets:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth/
docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/
docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/
```

## Method Requirements

The Level 3 method must state:

- final input path and timestep;
- baseline/reference input path and timestep;
- whether grids match exactly or how compatibility was validated;
- tracer exclusion threshold;
- spatial mask;
- thermal energy formula;
- kinetic energy formula;
- gravitational energy formula, or exact blocker;
- unit conversion;
- side/bipolar convention;
- ratios against Level 1, Level 2, `pV`, `2.5pV`, and `4pV`.

If a component is blocked, write it as data, not prose only. Use status fields
such as:

```text
computed
blocked_missing_baseline
blocked_missing_dataset
blocked_missing_potential
blocked_missing_convention
```

## Remote Post-Processing Rules

Remote work is allowed only for existing-output post-processing. Before remote
work:

1. Run local tests for new helper logic.
2. Verify remote input paths with read-only commands.
3. Use a compute-node PBS job only if the login node is inappropriate.
4. Keep walltime and resource request bounded to the post-processing task.
5. If the job is submitted and verified queued/running, wake X-ray Cavities and
   stop until Barry reports the PBS completion email or requests a re-check.

Hard stop before any new PLUTO production simulation, `48 h` run, new case, or
view/source-age broadening.

## Validation

Run focused tests:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py -q
```

Run existing comparison tests if shared helpers or ratio logic are reused:

```bash
uv run pytest tests/test_final_volume_coupled_comparison.py -q
```

If a PBS wrapper is created or edited:

```bash
bash -n scripts/kunanyi/c_hi_final_level3_ambient_energy.pbs
```

Final hygiene:

```bash
git diff --check
```

## Hard Stops

Stop immediately before:

- new PLUTO production simulation;
- broadening to `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`;
- a multi-day Kunanyi production run;
- editing external UTAS AGN source checkouts;
- changing scientific defaults without X-ray Cavities approval;
- presenting tracer-derived or incomplete Level 3 results as final method
  truth.

## Wake-Up Rule

When complete or blocked, send a short wake-up to X-ray Cavities with:

- status;
- changed files;
- validation results;
- current `git status --short --branch`;
- Level 3 result status;
- product asset paths;
- remote job id if any;
- whether the stop rule was invoked;
- residual caveats;
- recommended next goal.
