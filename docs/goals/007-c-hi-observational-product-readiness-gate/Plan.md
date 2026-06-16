# Plan: Goal 007 C-HI Observational Product Readiness Gate

## Intended Shape

Build a local, reproducible product-quality diagnostic package rather than a
new production run:

```text
Patrick-agent Q-014 HOLD
  + Goal 005 final X-ray assets
  + Goal 003/002 radio diagnostic status
  -> wide-field X-ray context
  -> cavity-focused X-ray diagnostic
  -> contrast/residual view
  -> topology and provenance table
  -> Patrick-agent product-review request
```

The key judgment is whether the existing final endpoint X-ray product can be
made observationally legible from accepted assets, and what remains to be done
before broadening.

## Likely Files

- Create:
  `scripts/science/build_final_observational_product_readiness.py`
- Create:
  `tests/test_final_observational_product_readiness.py`
- Create:
  `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- Create:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/`
- Create:
  `docs/exchange/logs/2026-06-16-c-hi-final-observational-product-readiness.md`
- Create or update:
  `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- Modify, if useful:
  `agent_comms/requests/open_questions.md`
- Modify:
  `docs/exchange/current_status.md`
- Modify:
  `docs/goals/007-c-hi-observational-product-readiness-gate/Log.md`

If a simpler implementation can meet the acceptance criteria without a new
script, use it, but keep the product reproducible and validate the assets.

## Work Plan

1. Record starting state in `Log.md`.
2. Read Patrick-agent's `Q-014` response and the Goal 005 product assets.
3. Inspect local X-ray axes, maps, tracer mask, and cavity-boundary files.
4. Design the diagnostic figure package:
   - wide-field X-ray surface brightness;
   - cavity-focused X-ray view;
   - contrast/residual/unsharp-mask view;
   - tracer/cavity overlays clearly labelled as diagnostic overlays.
5. Add product-generation code and focused tests if needed.
6. Generate compact figures and machine-readable metadata/provenance tables.
7. Write the science note with a direct answer to Patrick-agent's concerns.
8. Create the agent-comms product-review request.
9. Update the open-question queue and current status if useful.
10. Add the exchange log and finish `Log.md`.
11. Run focused validation.
12. Wake X-ray Cavities and stop.

## Expected Recommendation

Expected default branch:

- hold broadening until Patrick-agent can inspect a clearer X-ray product;
- treat the Goal 005 cavity ellipses as tracer-defined diagnostic overlays;
- do not call them an X-ray-fitted observational cavity measurement;
- carry a connected-envelope versus two-lobe topology statement as an explicit
  uncertainty or convention;
- keep sparse particle maps labelled as emissivity diagnostics;
- make full raytraced radio surface-brightness at two or more frequencies a
  follow-up product requirement unless it can be generated properly inside this
  goal without remote production work.

If the new diagnostics show that the X-ray cavity/shell is not legible even
with wider context and contrast views, recommend a narrow X-ray-method revision
goal rather than broadening.

## Non-Goals

Do not launch a new PLUTO segment, remote XRAiSE job, PBS job, comparison case,
viewing-angle sweep, source-age sweep, Level 3 method implementation, or
manuscript-facing closeout. Do not promote sparse particle radio maps into
validated observables.
