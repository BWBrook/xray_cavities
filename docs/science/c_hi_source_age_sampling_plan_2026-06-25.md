# C-HI Source-Age Sampling Plan

Date: 2026-06-25

## Summary

Goal 018 creates a local-only planning/control packet for a future tightly
bounded `C-HI` source-age sampling run after the Kunanyi maintenance outage.
It does not authorize execution.

Decision label:

```text
SOURCE_AGE_SAMPLING_PLAN_READY_FOR_POST_MAINTENANCE_AUTHORIZATION
```

Recommended first-pass design:

1. After Kunanyi maintenance and explicit X-ray Cavities/Barry authorization,
   preflight the final-production `prod64` outputs `data.0046.flt.h5`,
   `data.0049.flt.h5`, and the accepted endpoint `data.0051.flt.h5`.
2. If preflight passes, post-process two new late-source-age samples:
   `Timestep_46` at about `44.999274 Myr` and `Timestep_49` at about
   `47.999129 Myr`.
3. Run the same compact product surface for each new source age at
   `0 deg`, `45 deg`, and `90 deg`; nonzero views must use the Goal 015/016
   refined projection accumulator:

```text
projection.projected_accumulation=edge_overlap_uniform_cell_projection
```

4. Reuse the accepted `50 Myr` endpoint control surface rather than rerunning
   it by default:
   `0 deg` from Goal 005, and refined `45 deg`/`90 deg` from Goal 016.

This is a late-source-age pilot, not a broad sweep. It is deliberately smaller
than jumping immediately to early-time or comparison-case sampling.

## Assets

Compact planning assets are under:

```text
docs/science/assets/c_hi_source_age_sampling_plan_2026-06-25/
```

Files:

| File | Purpose |
| --- | --- |
| `source_age_candidate_snapshots.csv` | locally evidenced candidate snapshots and what remains unknown |
| `proposed_sampling_plan.csv` | recommended first-pass sampling design and held alternatives |
| `post_maintenance_run_contract.csv` | future execution contract, stop rules, validation gates, and no-overwrite policy |
| `runtime_resource_estimate.csv` | timing and resource estimate from Goals 011/012/016 |
| `risk_and_caveat_register.csv` | active caveats and how the next goal should preserve them |
| `source_age_sampling_plan_metadata.json` | compact machine-readable recommendation |

The asset builder is:

```text
scripts/science/build_source_age_sampling_plan.py
```

It is covered by:

```text
tests/test_source_age_sampling_plan.py
```

## Evidence Surface

Evidence read for this packet includes:

| Evidence | Use |
| --- | --- |
| Goal 017 consolidation note/assets/log | current preferred viewing-angle control surface |
| Goal 016 refined projection note/assets/log | accumulator, empty-column fix, and runtime anchor |
| Goal 015 and Goal 014 notes/assets | reason refined projection is required for nonzero views |
| Goal 005 note/assets | accepted unchanged `0 deg`, `50 Myr` endpoint baseline |
| Goal 011/012 notes/assets | preserved historical 45/90-degree diagnostics, not future preferred evidence |
| Goal 009/010 notes/assets | Level 3 gravity blocker and `pV`/`2.5pV`/`4pV` convention |
| `docs/Honours_Research_Plan.md` | source age and viewing angle as declared secondary sampling axes |
| `docs/codex_utas_phys_hons_meeting_2_action_plan.md` | first C-HI science target and early snapshot diagnostic history |
| `docs/exchange/current_status.md` and dated exchange logs | final full-grid catalogue and maintenance-window context |

No remote files were listed or probed in this goal.

## Candidate Snapshot Interpretation

The local evidence separates three categories:

| Category | Status | Planning consequence |
| --- | --- | --- |
| Early `1-10 Myr` segment diagnostics | locally processed and science-useful, but from the May segment diagnostic lane | hold for a second wave unless a future authorized preflight verifies equivalent final-production inputs |
| `33.374180 Myr` mini-production endpoint | useful context, but not the default final-production control surface | do not make it the first post-maintenance target without a separate decision |
| Final-production late outputs `46-51` | locally catalogued in the completed `prod64` integrity evidence | best first-pass execution surface because it stays inside the accepted full-grid production tree |

The recommended first-pass therefore uses `data.0046.flt.h5` and
`data.0049.flt.h5` as the two new samples, with the accepted `data.0051.flt.h5`
endpoint as the control. This tests source-age sensitivity near the already
accepted endpoint without opening a broad source-age sweep.

The locally documented early anchors remain visible:

| Candidate | Time | Status |
| --- | ---: | --- |
| `data.0008.flt.h5::Timestep_8` | `4.999436 Myr` | held pending full-grid-equivalent preflight |
| `data.0014.flt.h5::Timestep_14` | `9.999876 Myr` | held pending full-grid-equivalent preflight |

These should not be substituted into the first final-production source-age run
without explicit review.

## Future Run Contract

The later execution goal should be explicit about these gates:

| Gate | Required outcome |
| --- | --- |
| Authorization | a new post-maintenance goal must authorize staging/submission |
| Input preflight | target HDF5 files exist, expose the requested timestep, and contain `rho`, `prs`, `tr1`, `vx1`, `vx2`, `vx3` |
| Product surface | compact X-ray/tracer projection products, projection metrics, metadata JSON, provenance CSV, stdout/stderr, and remote archive |
| Projection method | `45 deg` and `90 deg` products declare `edge_overlap_uniform_cell_projection` |
| Validation | finite positive metrics, expected view/timestep labels, parseable CSV/JSON, archive SHA, and no catastrophic empty-column recurrence |
| PBS stop rule | submit one bounded job, verify queued/running, wake X-ray Cavities, and stop until Barry reports completion email or asks for a re-check |
| No-overwrite policy | write a new dated asset bundle; do not overwrite Goals 005/011/012/016/017 assets |

If any target is absent or unreadable, the future execution agent should wake
X-ray Cavities before substituting a different source age.

## Runtime Estimate

Goal 016 processed the final `45 deg` and `90 deg` refined projections together
in `00:22:01` walltime on one CPU, with about `1.36 GB` reported memory. Goal
011 and Goal 012 historical single-view runs were each about `16-17 minutes`.

For planning, one new source age with `0/45/90 deg` compact products is
estimated at `35-60 minutes` walltime. The recommended two-new-age first pass
is estimated at roughly `75-120 minutes`, plus queue time and preflight
overhead. This is bounded post-processing, not a `48 h` or production-scale
simulation commitment.

The future goal should still choose a modest walltime with conservative memory
headroom, and it should not submit if maintenance timing or queue risk makes
the job no longer credibly bounded.

## Caveats Preserved

- Projection products remain review/control-surface evidence, not
  publication-ready observables.
- Connected-envelope/X-ray topology remains unresolved.
- Sparse particle-binned radio remains diagnostic, not a validated radio
  observable.
- Level 3 gravitational energy remains `blocked_missing_potential`.
- Energy summaries should continue carrying `pV`, adopted `2.5pV`, and `4pV`
  if energetics are included.
- `C-LO`, `G-LO`, comparison-case processing, and broad batches remain on hold.

## Non-Claims

- No remote commands, Open OnDemand, SSH/SCP, Kunanyi staging, `qstat`, PBS
  submission, finalizer, retrieval, or job polling occurred.
- No PLUTO production, source-age sampling execution, `C-LO`, `G-LO`,
  comparison-case processing, PRAiSE/radio/cavity regeneration, heavy XRAiSE
  rerun, or scientific-default change occurred.
- No commits, pushes, staging, cleanup, `agent_comms` changes, or Stas/Patrick
  escalation occurred.
- Accepted Goal 005/011/012/016/017 assets were not overwritten.
