# All simulation boundary and jet injection energy audits

Date: 2026-11-17.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`).
Status: supervisor-approved request for repository delivery and existing-output
analysis; new simulations require a separate costed proposal and approval.
Source repository revision: `77e1eabc6e40b158720a076bde1ca48a9f7a7b9a`.

## Scope

Apply both audits to **C-HI, C-LO, G-HI and G-LO**, not just the cluster cases.
Use every available scientifically retained snapshot, actual HDF5 times and
accepted native identity chains. Preserve G-HI's science exclusion at indices
48--50; any boundary-contact diagnosis using those states must be separate.

Reuse completed fixed-box, spherical and flux reductions, including C-LO's
full history. Review existing jobs before submitting anything; do not duplicate
queued/running work. Report progress and blockers per case rather than waiting
for all four. This request does not change existing scientific acceptance gates.

## Near boundary energy and hydrostatic stability

Test the hypothesis that production's coarser outer stretched cells worsen
discrete hydrostatic balance and boundary inflow. Outflow can admit unwanted
mass/energy while satisfying an open-volume energy balance: separate that
atmospheric-stability problem from unaccounted numerical energy creation.

1. Partition the grid into **0--10, 10--20, 20--30, 30--40 and 40--50 kpc**
   from the nearest box face, plus the interior at least 50 kpc from every
   face. Use nested full-cell inset boxes and their differences; report the
   actual native faces. Count edges/corners only once and verify that the
   regions reconstruct the whole grid. This is not a spherical-radius cut.
2. For each region, measure initial/current/change in **thermal, kinetic and
   gravitational energy and mass**, subtracting t=0 cell by cell in the same
   cells. Use the fixed initial potential; retain signed and cellwise absolute
   changes. Do not assume the initialized nozzle has zero initial energy.
   Report absolute values and fractions of labelled bipolar input, with mass
   and potential-zero conventions explicit.
3. Check the initial pressure-gradient/gravity balance on the native grid and
   its subsequent evolution, density/pressure drift, face-normal inflow and
   outflow, maximum velocities and local Mach numbers. Show the actual cell
   widths normal to each face and relate departures to the discrete numerical
   treatment where possible, not only a continuum hydrostatic profile.
4. Distinguish apparently undisturbed outer gas from genuine jet/lobe/wave
   effects. Neither low speed nor absence of tracer establishes undisturbed
   gas. Flag late high-power contact; do not remove real jet-affected energy
   to improve agreement. Small Mach numbers can coexist with substantial
   advected energy in a massive atmosphere.
5. Include mass/energy transport where measurable. Retain reconstruction and
   temporal-quadrature sensitivity, without presenting it as a formal error
   interval. Do not call storage alone a conservation test or subtract the
   coarse-control result as an exact stretched-grid correction.
6. Return clear component-energy plots versus boundary distance and time, and
   a compact whole-grid/interior comparison for every case. Put grid,
   numerical settings, jet and atmosphere parameters at the start. If exact
   production-grid no-jet reflective/outflow controls are needed, first return
   their matched setup and compute/storage cost for approval; do not launch
   new simulations solely on this handover.

## Jet supplied energy versus labelled input

Measure the energy supplied by the injector, not just the assumed power times
time. Momentum flux is a cross-check, not energy flux. On a fixed control
surface A enclosing the injector, use native areas and all velocity components:

\[
Q_{\rm kin}=\oint_A\tfrac12\rho|\boldsymbol v|^2v_n\,dA,
\qquad Q_{\rm enth}=\oint_A\frac{\gamma}{\gamma-1}p v_n\,dA,
\qquad \gamma=5/3.
\]

Normals point out of the injector control region into the surrounding gas.
Report per-jet and bipolar powers, signed outward/return/net contributions,
and mass/momentum fluxes including the pressure term in momentum. Opposite
jet directions must not cancel the diagnostic thrust comparison. Keep kinetic
and total mechanical power separate against the labelled kinetic reference.

For the full ledger, separately include potential transport
`Q_phi = integral_A rho * Phi_0 * v_n dA`, with the same fixed initial
potential and mass convention. This is not part of the labelled kinetic power.

The source is an **internal nozzle overwrite**, not an external domain inlet.
Therefore outgoing energy flux alone is not injected energy. Reconcile it
with storage inside the enclosing control region:

\[
\widehat E_{\rm net\ source}(t_i)=\Delta E_A(t_i)
 +\int_0^{t_i}(Q_{\rm kin}+Q_{\rm enth}+Q_\Phi)\,dt.
\]

Delta E_A includes kinetic, thermal and potential changes relative to the
actual initialized t=0 cells. This reconstructed **net source/balance residual**
can include gravity-update, floor and repair effects; it is not automatically
pure jet delivery. Keep the initial nozzle energy separate from post-t=0
supply. Do not add overwrite supply and exported flux as independent inputs.

At each saved age, provide instantaneous powers, cumulative kinetic/enthalpy
transport, inferred net source and ratios to labelled per-jet/bipolar power
times actual active age. HI bipolar power is `2e45 erg/s`, LO is `2e43 erg/s`;
input normalization at t=0 is undefined. Test surface padding, reconstruction
and time quadrature, especially the first 0--1 Myr interval.

For an exact audit, check for retained solver-integrated face fluxes and
injector energy-update counters. Use actual timestep/stage weights if present.
If absent, snapshots cannot recover the exact historical supply. Propose
instrumentation recording net conservative energy actually added/removed by
the injector, with separate gravity/floor/repair accounting and cumulative
counters saved at each snapshot. Do not count temporary predictor or ghost
resets as repeated physical injection. Return a validation/compute proposal
before any new run; evaluating the imposed inlet profile or integrating annual
snapshots must not be described as exact solver delivery.

## Pending matched midplane plots

Return **density and signed z-velocity** x-z slices at the central y-coordinate
for **C-LO near 50 Myr** and full-history **C-HI near 1, 30 and 50 Myr**.
State actual time, y-coordinate, run/input identity and physical units. Use
logarithmic density and show both the full velocity range and a rendering
sensitive to 100--300 km/s motions. Include full-domain/lobe-scale views and
R100/R300 intersections from total 3-D speed, with truncation/contact flags.
Optional tracer outlines use full-cell `tr1 > 1e-3` membership.

Publish small plots and provenance, with accessible slice arrays/coordinates
where practical; broad access to private simulation directories or copying
complete HDF5 files is unnecessary. The available May reduced-grid 1-Myr and
June 50-Myr C-HI plots are illustrations, not matched images for the August
energy budgets. Existing outputs suffice for these new slices.

## References and delivery

- [Current production energy and emission review](../../science/turn15_energy_emission_review_2026-11-11.md).
- [Qualified source interpretation](../../science/turn18_review_reconciliation_2026-11-11.md).
- [C-LO full fixed and flux history](../../science/turn18_clo_history_review_2026-11-16.md).
- [Existing boundary and nozzle flux definitions](../../science/q031_retained_flux_measurements_2026-10-31.md).
- [Uniform-grid paired boundary results](../../science/paired_boundary_results_2026-11-04.md).

This is the approved repository handover to Barry's agent, not a separate
private-board post or recipient acknowledgement. No analysis job or new PLUTO
run was submitted by this update, and no numerical result changed. Please
return per-case execution status, existing/new PBS job IDs where applicable,
the first results and any remaining blockers.
