# Log: Goal 008 C-HI Level 3 Ambient Energy Method Gate

## 2026-06-17 - Orchestrator Launch Packet

X-ray Cavities created this Goal 008 packet after fast-forwarding the action
repo and reading the new Stas-agent and Patrick-agent responses.

Patrick-agent answered `Q-015`: Goal 007 is product-adequate. The wide-field,
cavity-focused, residual X-ray figure fixes the visual-context concern. The
X-ray topology reads as a connected envelope or single connected lobe in the
current plot, but X-ray-based cavity-fit confirmation is still required before
freezing the fitted observational-cavity method. Sparse PRAiSE/radio products
remain particle-emissivity diagnostics until full raytraced radio
surface-brightness is validated.

Stas-agent answered `Q-012`: future method-facing summaries should carry `pV`,
`2.5pV`, and `4pV`, with `2.5pV` as the adopted non-relativistic physical
interpretation and `4pV` as the literature comparison.

Stas-agent answered `Q-013`: Level 3 ambient-energy calculation is required
before broadening to `45/90 deg`, source-age sampling, `C-LO`, or `G-LO`.

### Orchestrator Starting State

```text
pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
b33d5e3
```

### Evidence Read By Orchestrator

- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/three_case_spec.md`
- `scripts/science/pluto_h5_truth_extract.c`
- `scripts/science/build_final_volume_coupled_comparison.py`
- `tests/test_final_volume_coupled_comparison.py`
- `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs`
- `docs/goals/003-final-volume-coupled-comparison/Goal.md`

### Orchestrator Notes

- The action repo was fast-forwarded to `b33d5e3` before this packet was
  created.
- This goal is intentionally post-processing-first. Patrick and Stas have given
  decision autonomy for post-processing work, but new `48 h` Kunanyi production
  simulation commitments remain supervisor/orchestrator gated.
- The existing Level 2 truth extractor computes lobe thermal and kinetic
  energy from full-grid HDF5 fields; Goal 008 should extend or complement that
  pattern for ambient-medium energy relative to a baseline/reference state.
- The most likely hard part is gravitational energy: if no potential/profile or
  convention is available, `jet` should produce a precise blocked component,
  not invent a gravitational-energy claim.

### Delegation Boundary

`jet` should implement and validate this goal inside
`/Users/bwbrook/papers/xray_cavities` only. No commits, pushes, new production
runs, broadening, or multi-day Kunanyi simulation jobs are authorized.

`jet` must wake X-ray Cavities when complete or blocked, then stop.

## 2026-06-17 - jet action-agent start state

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
b16048c

git status --short --branch
## main...origin/main
```

Start state was clean, on `main`, and even with `origin/main`. Proceeding
within the Goal 008 Level 3 post-processing boundary.

## 2026-06-17 - jet evidence read and remote preflight

Read the required Goal 008 packet and repo-local context:

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `agent_comms/requests/open_questions.md`
- `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- `scripts/science/pluto_h5_truth_extract.c`
- `scripts/science/build_final_volume_coupled_comparison.py`
- `tests/test_final_volume_coupled_comparison.py`
- relevant existing Kunanyi PBS wrappers under `scripts/kunanyi/`

The accepted comparator scalars are:

```text
Level 1 bipolar injected energy: 3.1557599999999995e60 erg
Level 2 tracer > 5e-3 bipolar lobe energy: 1.3881436397447783e60 erg
Goal 005 bipolar pV: 6.87805393912703e59 erg
adopted non-relativistic 2.5pV: 1.7195134847817576e60 erg
literature-comparison 4pV: 2.751221575650812e60 erg
```

Terminal SSH probes failed after the Open OnDemand jumpbox enablement:

```text
ssh kunanyi-via-deep hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).

ssh kunanyi-via-nectar hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).

ssh tpac-jumpbox-via-deep hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).

ssh tpac-jumpbox-via-nectar hostname
bwbrook@<tpac-host>: Permission denied (publickey,password).
```

Used the already-open Kunanyi Open OnDemand dashboard narrowly to enable
Jumpbox SSH. The portal reported a `5.0 min` SSH window, but terminal SSH/SCP
still failed. Opened `kunanyi Shell Access` through the portal and used the web
shell for read-only preflight only.

Remote preflight found:

```text
baseline:
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0

final:
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

HDF5 vars for both baseline and final:

```text
prs Dataset {1014, 960, 960}
rho Dataset {1014, 960, 960}
tr1 Dataset {1014, 960, 960}
vx1 Dataset {1014, 960, 960}
vx2 Dataset {1014, 960, 960}
vx3 Dataset {1014, 960, 960}
```

No PBS job was submitted, so the stop rule was not invoked.

## 2026-06-17 - jet implementation and package

Added a streaming HDF5 extractor:

```text
scripts/science/pluto_h5_level3_ambient_extract.py
```

The extractor computes thermal and kinetic ambient-medium energy changes from
baseline and final HDF5 files using:

```text
ambient mask: final tr1 <= 5e-3
thermal: sum((prs_final - prs_baseline) * dV / (gamma - 1)) * unit_energy
kinetic: sum(0.5 * (rho_final*v_final^2 - rho_baseline*v_baseline^2) * dV) * unit_energy
side split: z < 0, z >= 0, and bipolar_total
```

Added a package builder:

```text
scripts/science/build_final_level3_ambient_energy.py
```

Generated the local blocked Level 3 package:

```text
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_ambient_energy.csv
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_method_decisions.csv
docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_metadata.json
```

Package result status:

```text
blocked_remote_postprocessing_access
```

The thermal and kinetic components are method-defined and extractor-ready, but
the full remote post-processing run was not completed because terminal SSH/SCP
access to Kunanyi remained blocked. The gravitational component is recorded as:

```text
blocked_missing_potential
```

because the accepted HDF5 vars do not include gravitational potential and this
repo does not contain a reviewed potential/profile zero-point convention.

Created the science note and exchange log:

```text
docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md
docs/exchange/logs/2026-06-17-c-hi-final-level3-ambient-energy.md
```

Updated `docs/exchange/current_status.md` with a compact post-Goal-008
handoff and added the Goal 008 asset bundle to `.gitattributes`.

## 2026-06-17 - jet validation and completion state

Focused validation passed:

```text
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
.............                                                            [100%]
13 passed in 0.15s

git diff --name-only -- 'scripts/kunanyi/*.pbs'
<no output>

git diff --check
<no output>

uv run python -m json.tool docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_metadata.json
<parsed successfully>
```

Final status:

- Level 3 result status is `blocked_remote_postprocessing_access`.
- Thermal and kinetic Level 3 are method-defined and extractor-ready, but the
  full remote extraction was not run because terminal SSH/SCP through the TPAC
  jumpbox remained blocked after Open OnDemand enablement.
- Gravitational Level 3 remains `blocked_missing_potential`.
- No PBS job was submitted and the PBS stop rule was not invoked.
- No PLUTO production run, broadening run, source-age/view/comparison-case
  work, final radio observable generation, scientific-default change, commit,
  or push occurred.

Recommended next goal:

```text
C-HI Level 3 bounded remote extraction closeout
```

That goal should repair terminal SSH/SCP or approve a reliable Open OnDemand
staging/retrieval route, then run the tested streaming extractor against the
existing baseline/final HDF5 pair. Keep gravitational energy blocked unless
Stas/Patrick provide a reviewed potential/profile convention.

## 2026-06-17 - jet local review iteration: coordinate compatibility

Orchestrator review identified a real method-contract gap: equal HDF5 dataset
shapes are not sufficient for cell-wise baseline/final Level 3 subtraction.
The extractor now validates baseline and final coordinate axes before reading
field slabs.

Implementation update:

```text
scripts/science/pluto_h5_level3_ambient_extract.py
```

- reads baseline and final `X`, `Y`, and `Z` coordinate axes using the existing
  PLUTO HDF5 `/cell_coords/{X,Y,Z}` convention;
- verifies each axis length against the grid shape;
- compares baseline/final axes with `rtol = 0` and `atol = 1e-10 kpc`;
- fails fast with `coordinate mismatch for <axis>` before any subtraction.

Focused tests updated:

```text
tests/test_pluto_h5_level3_ambient_extract.py
tests/test_final_level3_ambient_energy.py
```

Red/green evidence:

```text
uv run pytest tests/test_pluto_h5_level3_ambient_extract.py -q
..F
FAILED test_extract_level3_rejects_coordinate_mismatch
Failed: DID NOT RAISE <class 'ValueError'>

uv run pytest tests/test_pluto_h5_level3_ambient_extract.py -q
...                                                                      [100%]
3 passed in 0.07s

uv run pytest tests/test_final_level3_ambient_energy.py -q
...F
FAILED ... missing coordinate_compatibility method-decision row

uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py -q
.......                                                                  [100%]
7 passed in 0.07s
```

Regenerated the local Level 3 asset bundle so
`level3_method_decisions.csv` now includes:

```text
coordinate_compatibility,enforced_by_extractor_not_remote_preflight,
compare baseline/final X, Y, and Z coordinate axes with rtol=0 and atol=1e-10 kpc
```

Important boundary: this was local-only hardening. No remote command, Open
OnDemand action, SSH/SCP probe, PBS job, data extraction, heavy product,
broadening work, commit, or push occurred in this review iteration. The remote
preflight remains shape/dataset-only; the new coordinate check has not yet run
on the full remote baseline/final pair.
