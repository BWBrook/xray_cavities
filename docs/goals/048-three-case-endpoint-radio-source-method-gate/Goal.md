# Goal 048: Three-Case Endpoint Radio Source And Method Gate

## Objective

Determine whether the accepted `C-HI`, `C-LO`, and `G-LO` endpoint lineages can
support one scientifically comparable, loss-aware, ray-traced radio-observable
analysis. Freeze the common observing and numerical contract, validate its
local numerical foundations, and either prepare the common analysis or fail
closed with an explicit production decision.

This goal implements the remaining core radio lane in Aim 4 of the Honours
Research Plan. It must not make a three-case comparison by mixing different
loss-history methods.

## Approved Scope

Barry approved Goal 048 on 2026-07-24.

In scope:

- exact local and read-only Kunanyi source-history inventory;
- audit of the supplied XRAiSE/PRAiSE runtime and the current `plutokore`
  emissivity/raytracing implementation;
- a frozen common radio-observing protocol;
- deterministic local numerical fixtures for line-of-sight integration,
  normalized beam convolution, and rotation/view invariance;
- a machine-readable source/method gate;
- a decision packet for any new production commitment required to restore
  complete histories; and
- lifecycle guidance for the existing radio-held particle payloads.

Out of scope:

- no new PLUTO production without the recorded production decision;
- no mixed loss-aware/lossless three-case analysis;
- no endpoint-only loss factor presented as a full-history result;
- no new PBS science-product submission after a failed source gate;
- no raw-data deletion, move, truncation, or overwrite;
- no synchrotron age unless a spectral break is identifiable from at least
  three common-beam bands with uncertainty; and
- no causal or population-level inference from the three endpoint cases.

## Common Full-History Contract

A case passes the loss-aware source gate only if:

1. the accepted endpoint lineage is exact and hash/provenance bound;
2. every selected endpoint particle has an ID-keyed history from injection or
   last acceleration through the endpoint;
3. time, pressure, density, tracer, shock history, position, and velocity are
   available at a documented common cadence;
4. missing pre-injection records are distinguishable from missing
   post-injection history;
5. the same emissivity implementation and parameters are used for all cases;
6. the same raytracing, grid, support, beam, frequency, view, and threshold
   rules are used for all cases; and
7. no case substitutes a sparse late window, reduced-grid cache, or
   instantaneous endpoint factor for a complete accepted-lineage history.

Any failed case blocks the common loss-aware product.

## Provisional Common Radio Protocol

The observing-frame protocol to test at the next method gate is:

- accepted matched endpoints near `50 Myr`;
- observed frequencies `150 MHz` and `1.4 GHz` at `z=0.05`;
- optional `9 GHz` only for a separately gated curvature/age analysis;
- views `0`, `45`, and `90 deg`;
- `plutokore.radio.praise.calculate_praise_emissivity_numba` as a candidate
  full-loss implementation;
- `plutokore.radio.raytracing.raytrace_particles_multiple_freq` as a candidate
  multi-frequency raytracer, with explicit units and Doppler/view handling;
- one physical grid and full support shared by cases, views, and frequencies;
- a circular `5 kpc FWHM` primary beam, pixel size no larger than `2 kpc`,
  and beam sensitivities at `2.5` and `10 kpc`;
- a primary absolute detection threshold of `0.05 mJy beam^-1`, with
  sensitivities at one-third and three times that value; and
- integrated luminosity, detected topology, extent, centroid, sidedness,
  spectral index where both bands are detected, and overlap with accepted
  X-ray/truth products.

The exact production implementation must pass analytic line-of-sight,
integrated-flux, rotation, convergence, determinism, unit, support, and
provenance gates before its maps are accepted.

The emission contract is not yet frozen. The next gate must predeclare and
justify the electron index, equipartition/magnetic-field prescription,
`gamma_min`, `gamma_max`, shock/acceleration rule, loss modes, smoothing, and
particle-support treatment. The beam and threshold values above are
provisional observing choices until the production path and estimand are
validated.

## Permitted Decisions

1. `LOSS_AWARE_READY`: all three cases have comparable complete histories and
   the production implementation may be prepared.
2. `PRODUCTION_DECISION_REQUIRED`: one or more accepted lineages lack complete
   histories. Prepare, but do not launch, the production remedy.
3. `G_LO_METHOD_VALUE_GATE_REQUIRED`: filename coverage is present for G-LO,
   but usable ID/time/schema continuity, computational feasibility, the
   production implementation, and the scientific effect of losses are not yet
   established.
4. `MATCHED_LOSSLESS_REFERENCE`: explicitly narrow the radio claim to a
   common endpoint-only, lossless, ray-traced reference. This is not a
   substitute for full PRAiSE ageing or synchrotron age.
5. `BLOCKED_METHOD`: runtime semantics or numerical validation prevents even a
   matched reference.

## Production Escalation

New `C-HI` or `C-LO` PLUTO production is a material multi-node commitment and
requires Stas/Patrick review plus Barry approval. Before that escalation, a
G-LO recovery/method/value-of-information gate must establish that the retained
sequence is a usable complete history, validate the candidate production
implementation, demonstrate a feasible chunked/restartable compute plan, and
quantify how much full losses change the headline products relative to a
matched endpoint-lossless reference.

## Completion States

- `complete_source_method_gate_g_lo_method_value_gate_required`: source
  evidence establishes the cross-case blocker and local acceptance references
  pass, but production escalation is deferred until the G-LO
  recovery/method/value gate resolves usefulness and feasibility.
- `complete_loss_aware_ready`: all sources and methods pass, and a later
  execution goal can be specified.
- `blocked_method`: the implementation cannot support a defensible common
  radio surface.

## Validation

- focused automated tests for aggregation, method consistency, deterministic
  asset generation, and numerical fixtures;
- CSV/JSON schema and duplicate-header checks;
- explicit observation/inference/decision fields;
- exact source/runtime hashes where available;
- independent scientific review of the decision and claims;
- `git diff --check`; and
- no raw HDF5 or particle payload in the local evidence bundle.
