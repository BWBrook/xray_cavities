# Runbook: Goal 009 C-HI Level 3 Remote Extraction Closeout

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
docs/goals/009-c-hi-level3-remote-extraction-closeout/Goal.md
docs/goals/009-c-hi-level3-remote-extraction-closeout/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
docs/goals/008-c-hi-level3-ambient-energy/Goal.md
docs/goals/008-c-hi-level3-ambient-energy/Log.md
docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_ambient_energy.csv
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_method_decisions.csv
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_metadata.json
scripts/science/pluto_h5_level3_ambient_extract.py
scripts/science/build_final_level3_ambient_energy.py
tests/test_pluto_h5_level3_ambient_extract.py
tests/test_final_level3_ambient_energy.py
```

Read other repo-local files only as needed for exact packaging or Kunanyi
environment details.

## Existing Remote Inputs

Baseline:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0
```

Final:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Known required datasets:

```text
rho, prs, tr1, vx1, vx2, vx3
```

Known preflight shape from Goal 008:

```text
1014 x 960 x 960
```

Treat this as a shape/dataset preflight only. The extractor must still execute
the coordinate-axis compatibility check on the remote pair before values are
trusted.

## Local Pre-Remote Gate

Run:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
```

If this fails, fix or stop locally before remote staging.

## Access Route

Try the smallest reliable route.

Terminal route, if available:

```bash
ssh kunanyi-via-deep hostname
ssh kunanyi-via-nectar hostname
```

Use the working route only. Do not keep retrying blindly.

If terminal SSH/SCP remains blocked, an Open OnDemand web shell or file route is
authorized for this bounded existing-output post-processing task if it can stage
commands and retrieve compact outputs reliably. Record the route and evidence
used. If the route is not reliable enough, stop as `blocked_remote_access`.

## PBS Stop Rule

If a compute-node PBS job is needed:

1. Stage the extractor and wrapper under an auditable Kunanyi path.
2. Submit the job.
3. Verify it is queued or running.
4. Wake X-ray Cavities with:
   - PBS job id;
   - queue/running evidence;
   - stage directory;
   - output root;
   - exact resume command or retrieval steps;
   - expected compact products.
5. Stop. Do not poll for completion.

Resume only after Barry reports the PBS completion email or X-ray Cavities
explicitly requests a re-check.

## Packaging Completed Output

If extractor output is available, package it locally under a Goal 009 dated
asset directory, for example:

```text
docs/science/assets/c_hi_final_level3_remote_extraction_closeout_2026-06-18/
```

Expected compact outputs include:

```text
level3_ambient_energy.csv
level3_method_decisions.csv
level3_metadata.json
remote_logs/
```

The package must state:

- baseline/final paths and timesteps;
- coordinate check status;
- thermal and kinetic values;
- thermal-plus-kinetic values;
- side and bipolar rows if produced;
- ratios to Level 1, Level 2, `pV`, `2.5pV`, and `4pV`;
- gravitational status, normally still `blocked_missing_potential`;
- checksums or compact provenance for retrieved remote outputs.

## Validation

Run focused tests:

```bash
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
```

For each changed PBS wrapper:

```bash
bash -n <wrapper>
```

Parse JSON metadata if created:

```bash
uv run python -m json.tool <metadata-json>
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
- login-node heavy extraction if a compute-node job is appropriate;
- changing scientific defaults;
- solving gravitational energy without reviewed potential/profile evidence;
- committing or pushing.

## Wake-Up Rule

When submitted, complete, or blocked, wake X-ray Cavities with:

- status;
- changed files;
- validation results;
- current `git status --short --branch`;
- access route used;
- remote job id if any;
- whether the stop rule was invoked;
- product asset paths if available;
- Level 3 result status;
- residual caveats;
- recommended next step.
