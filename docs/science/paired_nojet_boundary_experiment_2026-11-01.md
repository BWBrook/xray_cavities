# Paired coarse-grid boundary experiment

Status: target MPI/HDF5 build `872548` completed F/0 with 77/77 tests passing.
Four 28-rank smoke runs (`872581`–`872584`) are running. Full 50-Myr controls
await the runtime budget, native-output and paired-identity gates.

Barry authorised on 1 November 2026: “Go ahead with the cheap paired
reflective/outflow controls, keeping everything else identical. Hold off on
a full production-matched run.” This continues turn #5. Claude is not being
asked to implement or approve this experiment.

## Contrast and scope

Run four fresh 50-Myr simulations: cluster and group, each with reflective and
outflow boundaries. Each pair uses the same executable, initial atmosphere,
gravity, 400 × 400 × 500 uniform 1-kpc grid, box, solver, timestep policy,
28-rank decomposition (2 × 2 × 7), output settings and diagnostics. The sole
within-pair physics difference is the six boundary settings. Output directories
are isolated so relative paths can remain identical. Boundary-dependent
timesteps are allowed; comparison uses actual physical time, with the exact
50-Myr endpoint as the primary contrast.

This tests whether the boundary switch produces mass/energy drift in these
coarse configurations. It does not estimate the effect on the stretched
production grid, establish production stability, or authorise control
subtraction from production. Cluster/group are two environments, not replicates.

## Common build

Freeze Git source snapshots from PLUTO `2674fc38b152f96605cb24e2840e92b64ebd5b81`
and jet-setup `e17ac8f8640017900abfe635737bd3199d607363`. Preserve source hashes,
patch receipts, effective compiled definitions, compiler/module details and
the executable hash. Global source checkouts and frozen production inputs
remain untouched.

The staged-only patch makes inactive injection explicit before the old
zero-duty `fmod` calculation, loads the staged atmosphere selected by `environment.ini`
instead of the source's hard-coded path (`PAIRED_NOJET_TABLE` supplies a required
default), and removes the unused particle
makefile include as in the historical no-particles gate. Both treatments use
these same changes. Passive diagnostics observe numerical fluxes, gravity work
and conserved-to-primitive energy adjustments without changing solution arrays.

Physical conversion uses the exact pinned solver constants: atomic mass unit
1.66053886e-24 g, mean molecular weight 0.60364, parsec 3.0856775807e18 cm and
speed of light 2.99792458e10 cm/s. The new validator records these explicitly;
historical analysis constants are not changed. Potential is the centre-zero
trapezoidal integral of the initial tabulated gravity, with linear interpolation
between potential nodes, matching the adopted method.

## Measurements and predeclared checks

At every accepted RK2 update, retain all six faces' numerical mass,
hydrodynamic-energy and potential-energy transport, weighted by their actual
RK stages. Outward transport is positive. Positive and negative traffic are
accumulated separately. Record exact applied gravity work and any energy
adjustment in conserved-to-primitive conversion, storage components, time/dt,
step and boundary-normal velocities. Conversion adjustments include all changes
to conserved energy during conversion, not only entropy switching. Retain
cellwise signed positive/negative totals and their gross magnitude before
spatial cancellation; fail on any conversion failure/positivity flag or
nonzero conversion return. Flag counts are cell-call observations, not unique cells. Nonzero conversion
return calls use the maximum count across ranks per update; they detect any
failure but do not report global failure multiplicity. Cell-centred reconstructed fluxes and
their trapezoids are additional diagnostics, not the numerical closure test.

The independent budget equations are:

- ΔM + F_M = ε_M.
- ΔH + F_H − W_gravity − R_conversion = ε_H.
- ΔP + F_P + W_gravity = ε_P.
- Δ(H + P) + F_H + F_P − R_conversion = ε_total.

Here H is conserved hydrodynamic energy and P is fixed-potential energy.
The ledger also reports primitive thermal/kinetic energy and its difference
from conserved H. For mass and H, require absolute residual no greater than
1e-10 of initial storage plus 1e-6 of gross transport/source magnitude, both
per update and cumulatively. Reflective numerical mass/energy traffic must be
below 1e-12 of initial storage per update. Failures trigger diagnosis; the
thresholds must not be loosened merely to admit a run.

Potential/total residuals quantify the gravity discretisation and are reported
separately rather than assumed identically zero. Attributing the pair contrast
to boundary transport requires the unexplained residual and numerical
conversion adjustments to be materially smaller than that contrast.

## Execution gates

1. Local transformation, treatment-identity, native-output and manufactured
   budget tests; independent review of numerical hooks and accounting.
2. Build once on Kunanyi with the retained HDF5/OpenMPI toolchain. Run the
   staged tests and bind the executable to the frozen source manifest.
3. Smoke all four configurations on the full grid with 28 ranks through
   0.25 Myr (at least ten accepted updates), preserving t0 and endpoint HDF5.
   Check complete output histories, geometry, finite positive primitives,
   zero tracer, no initial velocity, table/profile identity, numerical budget
   closure and independent native-cell storage integrals.
4. Require bit-identical initial physical arrays and identical executable,
   table and effective definitions within each pair. Only the six boundary
   values may differ in their semantic configurations. Inspect target timing,
   memory and capacity before full runs.
5. Start all full runs fresh. Retain six double snapshots over 0–50 Myr plus
   compact every-update diagnostics. Require clean scheduler completion and
   complete, source-bound validation receipts. Scientific quietness is an
   outcome, not an acceptance gate.

The four full histories require approximately 138.4 GB uncompressed; the
eight smoke snapshots add approximately 46.1 GB. Historical uninstrumented
runs suggest about 23 allocated core-hours each, before new diagnostics and
validation; smoke measurements will determine the full allocation. Use home,
not quota-limited scratch. At the live preparation check, home directory
accounting was 13,720,842,598,712 bytes against the recorded 20-TiB allocation;
allow for the unfinished C-LO migration as well as these new outputs.

## Interpretation

A treatment contrast that agrees with measured numerical transport supports
the mechanism on this coarse grid. A contrast without closure establishes
boundary sensitivity but leaves the mechanism unresolved. A null contrast
does not exclude an interaction between boundary condition and the production
grid. Similar drift in both twins points toward common evolution or numerical
effects. No outcome automatically removes the need for a matched control when
the eventual claim concerns production-specific regional attribution or an
evolved X-ray background.

## Local implementation evidence

The four focused suites pass 76 tests locally with one expected stage-only
skip; the exported-stage suite passes all 77. A full serial compile/link passes
with the revised conversion diagnostics. The independent source audit checked
physical-face ownership, flux signs and areas, RK2 weights, gravity/repair
accounting and passive instrumentation. Its repair-cancellation finding was
addressed with cellwise signed/gross totals and strict failure counters.
Local compile evidence is retained under
`assets/paired_nojet_boundary_experiment_2026-11-01/local_checks/`.
These checks do not substitute for target MPI execution and native-cell closure.

Final target stage: `paired_nojet_boundary_2026-11-01_r1`, frozen from project
commit `493e724`, with 77/77 tests passing. Archive SHA-256:
`0aa334e3a5ec933a749867b2c708cd51ab4884982a2e3780b961672b2fd08973`
(4,786,674 bytes). Its manifests, patch receipt and test XML are retained
under `assets/paired_nojet_boundary_experiment_2026-11-01/stage_r1/`.
The frozen plan inside the archive describes the pre-launch state; this live
note records later access status without mutating that stage.
