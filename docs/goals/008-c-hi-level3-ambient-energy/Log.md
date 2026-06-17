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
