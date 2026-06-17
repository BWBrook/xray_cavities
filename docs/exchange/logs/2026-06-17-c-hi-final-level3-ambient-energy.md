# 2026-06-17 C-HI Final Level 3 Ambient Energy Method Gate

## Why This Packet Was Opened

Stas-agent answered `Q-013` that Level 3 ambient energy must be completed
before broadening to additional viewing angles, source-age sampling, `C-LO`, or
`G-LO`. Stas-agent also answered `Q-012` that `2.5pV` should be the adopted
non-relativistic interpretation while retaining `4pV` as the literature
comparison. Patrick-agent answered `Q-015` that Goal 007 is product-adequate.

Goal 008 therefore opened a bounded Level 3 ambient-energy method gate for the
accepted final 50 Myr `C-HI` endpoint.

## Evidence Read

- Goal 008 packet and log.
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

## Remote Preflight

Terminal SSH aliases to Kunanyi failed at the TPAC jumpbox with
`Permission denied (publickey,password)`. Open OnDemand was used narrowly to
enable Jumpbox SSH and then to open a web shell. The web shell allowed read-only
preflight on `kunanyi-00`.

Verified existing-output inputs:

```text
baseline:
/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0000.flt.h5
Timestep_0

final:
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
Timestep_51
```

Both contain:

```text
rho, prs, tr1, vx1, vx2, vx3
shape = 1014 x 960 x 960
```

This was a shape/dataset preflight only. A later local-only review iteration
hardened the extractor so it also compares baseline and final `X`, `Y`, and
`Z` coordinate axes before subtraction, but that coordinate check has not yet
been executed on the full remote HDF5 pair.

No PBS job was submitted, so the project stop rule was not invoked.

## Deliverables

- Science note:
  `docs/science/c_hi_final_level3_ambient_energy_2026-06-17.md`
- Asset directory:
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/`
- Component status table:
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_ambient_energy.csv`
- Method table:
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_method_decisions.csv`
- Metadata:
  `docs/science/assets/c_hi_final_level3_ambient_energy_2026-06-17/level3_metadata.json`
- Streaming extractor:
  `scripts/science/pluto_h5_level3_ambient_extract.py`
- Package builder:
  `scripts/science/build_final_level3_ambient_energy.py`
- Focused tests:
  `tests/test_pluto_h5_level3_ambient_extract.py`
  `tests/test_final_level3_ambient_energy.py`

## Headline Result

Result status:

```text
blocked_remote_postprocessing_access
```

Thermal and kinetic Level 3 formulas are defined, the baseline/final HDF5
inputs are identified, required datasets are present, and the streaming
extractor is locally tested. The extractor now fails fast if baseline/final
coordinate axes differ, but that check has not been run on the full remote pair.
The full-grid extraction was not run because terminal SSH/SCP remained blocked
after Open OnDemand enablement.

Gravitational component status:

```text
blocked_missing_potential
```

The accepted HDF5 outputs do not expose a gravitational potential, and this repo
does not yet contain a reviewed potential/profile zero-point convention.

## Validation

Validation is recorded in the Goal 008 log. Required focused gates include:

```text
uv run pytest tests/test_final_level3_ambient_energy.py tests/test_pluto_h5_level3_ambient_extract.py tests/test_final_volume_coupled_comparison.py -q
git diff --check
```

No new PLUTO run, production job, broadening job, final radio observable,
scientific-default change, commit, or push occurred.
