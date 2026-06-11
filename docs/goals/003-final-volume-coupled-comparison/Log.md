# Log: Goal 003 Final Volume-Coupled Comparison Page

## 2026-06-11 - X-ray Cavities goal creation

Created by the X-ray Cavities orchestrator after accepting Goal 002.

Action repo state before writing this packet:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD e715c79
```

Goal 002 generated and validated the first final sparse selected-ID
PRAiSE-compatible loss table and ran the Goal 001 bridge through
`--loss-table`. The remaining high-value gap is the bridge luminosity scale:
Goal 002 still used `1.0 kpc^3` per selected particle, while final grid/tracer
truth can provide side volumes for the negative-z and positive-z lobes.

Goal 003 is the bounded follow-up: extract final Level 1/2 truth from the
completed endpoint, feed the `tracer > 5e-3` side volumes into the existing
bridge, and package a compact comparison product that is honest about what is
and is not final.

No project implementation, remote staging, remote job, data workflow, or
validation run was performed by the orchestrator while creating this packet.
