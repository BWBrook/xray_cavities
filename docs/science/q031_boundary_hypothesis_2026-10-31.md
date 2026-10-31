# Q-031 boundary-inflow hypothesis audit — 31 October 2026

Status: strong support for boundary-carried energy; quantitative flux closure
and the injection source remain to be measured. This diagnostic does not
replace the approved 100/300 km/s-defined spherical budgets or the requested
existing no-jet and unreached-atmosphere audits.

Claude Opus 5.5 proposed the boundary explanation in Correspondence discussion
29, message 2644, after accepting a hemisphere/whole-grid mass mismatch in the
earlier calculation. Codex (GPT-6) integrated an independent GPT-5.6 Sol
numerical and source audit. The calculations below reproduce the compact data;
no native HDF5 was reread and no simulation was run.

## Reproduction

Run from the project root:

```bash
.venv/bin/python scripts/science/audit_q031_boundary_hypothesis.py
```

Outputs are in `docs/science/assets/q031_boundary_hypothesis_2026-10-31/`:
eight face/weighting scenarios, 19 selected-age energy/mass rows, four analytic
nozzle predictions and nine HI–LO mass comparisons. `provenance.json` records
input hashes and local source commits/dirty state; `manifest.sha256` binds the
five CSV/JSON outputs. The local source is contextual evidence, not a claim
that it is the exact production binary. Rendered production overrides and
retained run evidence support use of `DENSITY_LENGTH_SCALE`.

The atmosphere profiles are the retained cluster/group Stewart tables. For
gamma=5/3, specific enthalpy is `h=2.5p/rho`. The gravitational potential uses
the same centre-zero trapezoid integral of the mean absolute tabulated gravity
components as `snapshot_energy.py`. Face averages use midpoint quadrature over
the actual box faces, x/y=±200 kpc and z=±250 kpc. Area and density weighting
are illustrative scenarios; neither is a measured mass-flux weighting.

| Environment | Face/weighting | Mean h+phi (erg/g) |
| --- | --- | ---: |
| Cluster | x/y, density | 1.4567100e16 |
| Cluster | x/y, area | 1.4661735e16 |
| Cluster | z, density | 1.4952216e16 |
| Cluster | z, area | 1.4988872e16 |
| Group | x/y, density | 5.2861440e15 |
| Group | x/y, area | 5.3044581e15 |
| Group | z, density | 5.3569963e15 |
| Group | z, area | 5.3638292e15 |

C-LO's whole-grid `(delta E - E_nominal)/delta M` is
1.48775–1.49530e16 erg/g over 10–50 Myr. Its agreement with the outer-atmosphere
specific energy is strong support for the boundary hypothesis. It does not
locate the entering gas or measure its time-integrated energy flux.

## Why closure remains provisional

The scenario calculation subtracts analytic continuum jet mass from whole-grid
mass gain, then multiplies that inferred boundary mass by each face-specific
energy. For C-LO, the resulting `(delta E - E_boundary_estimate)/E_nominal` is:

| Age (Myr) | Scenario minimum | Scenario maximum |
| ---: | ---: | ---: |
| 10 | 0.991 | 1.133 |
| 20 | 0.933 | 1.201 |
| 30 | 0.906 | 1.300 |
| 40 | 0.888 | 1.408 |
| 50 | 0.893 | 1.543 |

These are alternative weightings, not confidence limits or guaranteed physical
bounds. The late C-LO values do not support the claim that every run closes
within 20% of injection. Subtracting a boundary term much larger than the jet
energy magnifies even a small error in its representative specific energy.

Likewise, taking the HI–LO mass-gain difference as jet injection and subtracting
it from HI forces the inferred background mass gains to agree. That agreement
is algebraic, not an independent test of power-invariant boundary inflow.

For the density-length-scale source, the continuum bipolar mass flux is
`4Q/v^2 * rho(L1b)/rho(0)`, where Q is configured one-sided power. Its predicted
HI–LO mass difference per 10 Myr is 1.38970e41 g in the cluster and 1.38514e41 g
in the group. The observed cumulative paired differences are 1.549–1.629 times
that prediction in the cluster and 1.569–1.571 in the group. The discrepancy
could reflect discrete nozzle delivery or power-dependent boundary response;
the endpoint sums do not distinguish them.

The continuum kinetic-plus-enthalpy nozzle power is 1.00022, 1.00442, 1.00019
and 1.00124 times configured bipolar power for C-LO, C-HI, G-LO and G-HI,
respectively. Thus the analytic source formula alone does not explain a
5–18% energy excess. Internal-boundary overwrite and the discrete nozzle
surface require their own accounting.

## Decisive next measurements

Use the retained fluid cadence to integrate signed mass and
`rho*v_normal*(h + phi + v^2/2)` across all six box faces. In the same extraction,
measure fluxes across a closed surface outside the nozzle, outer-cell normal
velocity through time, and radial/shell mass changes. Compare their integrals
with the observed whole-grid mass and energy changes. Retain the unadjusted
budgets and report residuals.

The zero-gradient outflow boundaries in a stratified gravitational atmosphere
provide a plausible mechanism: edge pressure support is altered and ghost
cells can supply material when edge velocities point inward. Source support
is PLUTO `Src/boundary.c` (`OutflowBound`) and `jet-setup/src/jet.c`; their hashes
are recorded in provenance. A tube-mean 45 km/s is not a face-integrated
measurement and cannot rule out z-face inflow by itself.

Cell-centred snapshot reconstructions approximate the numerical face fluxes
used by PLUTO. Assess temporal quadrature and reconstruction errors before
calling the result closure. A short instrumented diagnostic run could resolve
remaining discrete-source/flux uncertainty if existing outputs prove
insufficient; no such new PLUTO run is authorized or launched here. Deferring
a new matched no-jet simulation does not cancel the existing-control audit.
