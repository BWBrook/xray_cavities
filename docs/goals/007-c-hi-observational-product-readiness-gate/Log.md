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
