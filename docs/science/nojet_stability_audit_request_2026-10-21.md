# No-jet stability audit and outer-grid motion

Status: Q-031 follow-up requested by Stas; existing compact evidence checked,
but no new raw-data read, no-jet energy audit or simulation has run here.

## Setup and scope

- Existing no-jet cluster/group controls: Stewart `002003`/`002031`, Kunanyi
  jobs `690366`/`690371`, completed 50 Myr on 2026-05-08, six double outputs.
- Control grid: `400 x 400 x 500`; production grid: stretched
  `960 x 960 x 1014`. Both domains span +/-200 kpc transversely and
  +/-250 kpc axially. These are not resolution-matched controls.
- Production C-LO/G-LO: one-sided power `1e43 erg/s`, bipolar power
  `2e43 erg/s`, active to 50 Myr, speed `0.1c`, opening angles `15 deg`,
  central spacing `0.05 kpc`, HD with `gamma=5/3` and fixed initial gravity.
- Bipolar injected energy at 50 Myr: `3.15576e58 erg`.
- The control runs completed and were used for sampled pressure/density/
  entropy threshold calibration. No integrated thermal/kinetic/gravitational
  energy-drift result was found for them in the shared repository.
- Copy the actual timestep/CFL, boundary conditions, units, gravity settings,
  jet-disable settings, build provenance and grids into the audit's setup
  block. Those details have not been independently rechecked in this note.

## Latest approved refinement: spherical jet-energy budgets

Stas requests the following refinement to Q-031:

1. **Tolerance for background velocities.** Spurious motions below 5% of
   the local sound speed are provisionally acceptable as numerical effects:

   $$|\mathbf v|/c_s<0.05,\qquad c_s=\sqrt{\gamma p/\rho}.$$

   Stas's current interpretation is that C-LO and G-LO are acceptable in
   this respect. Verify this using local three-dimensional speeds and sound
   speeds, not just axial tube averages. This velocity tolerance does not
   by itself demonstrate negligible accumulated energy drift.

2. **Restrict the primary energy comparison to a sphere enclosing the
   jet-affected gas**, rather than including the entire computational
   domain. At each snapshot, calculate two proxy radii:

   $$R_{100}=\max_{|\mathbf v_i|\ge100\,{\rm km\,s^{-1}}}r_i,\qquad
   R_{300}=\max_{|\mathbf v_i|\ge300\,{\rm km\,s^{-1}}}r_i.$$

   Use total speed, not just axial velocity. Document any minimal cell-width
   padding needed to enclose the qualifying cells.

3. **Calculate both spherical budgets independently.** Include every cell
   inside each sphere, including slow-moving cells. For thermal, kinetic
   and gravitational energy, subtract the initial state cell by cell:

   $$\Delta E_a(<R,t)=
   \sum_{r_i<R(t)}[e_{a,i}(t)-e_{a,i}(0)]V_i.$$

   Crucially, use the **same current radius and same cells for both times**,
   and retain the fixed initial gravitational potential.

4. **Report radii, component energies and their sum versus injected bipolar
   jet energy** for both thresholds. Then split each budget into cocoon and
   ambient contributions using full-cell `tr1 > 1e-3` membership and its
   complement.

5. **Validate the radius proxies.** Check that they encompass the cocoon
   and relevant disturbed ambient gas. Flag isolated boundary artefacts or
   weak waves that make a velocity threshold misleading. Interpret any
   residual with possible energy transport across the spherical boundary
   in mind; do not force agreement by adjusting the aperture.

This approved refinement supersedes the earlier whole-grid-first choice
for the primary jet-energy comparison. Preserve existing full-grid results
as diagnostic evidence, not as the requested regional measurement. The
no-jet stability audit and other regional diagnostic requests remain open.
No new spherical budgets or local-Mach checks have been calculated here.

## Existing no-jet and regional diagnostic requests

Audit the existing no-jet runs first, before proposing any new PLUTO run.
Stas accepts approximately 10--20% jet-versus-grid discrepancies as a working
tolerance, but larger low-power discrepancies require investigation. This is
not permission to hide or renormalize the raw residual, nor an automatic
energy-conservation pass for the no-jet controls.

1. For each control, report absolute initial/current thermal, kinetic and
   gravitational energies, their same-cell differences, and the total change
   between 0 and 50 Myr. Include the intermediate retained snapshots to show
   whether drift grows steadily or begins at a boundary. Sum every physical
   cell, excluding only ghost cells; no shock or tracer mask is required.
2. Use the same initial `Phi_0(r) = integral_0^r |g_0| dr` at both times.
   Keep the centre-zero convention and actual initial state. Individual forms
   can exchange energy; their total, with any measured boundary/source terms,
   is the conservation test. Verify that both initial nozzle placement and
   ongoing jet injection are disabled as intended, rather than assuming it.
3. Give energy changes in erg and relative to initial energy where meaningful.
   Also express the changes relative to `3.15576e58 erg`, explicitly labelled
   as the *comparison* low-power bipolar injection, not energy injected into
   the no-jet run. Never divide by the no-jet injected energy, which is zero.
4. At each retained age, calculate the true full-grid maximum of
   `sqrt(vx^2 + vy^2 + vz^2)` and its cell indices, `(x,y,z)`, radius and
   distance to a physical boundary. Include the velocity components, radial
   direction and local sound speed/Mach at that location. Report the maximum
   over `r > 100 kpc` separately, and provide slices/profiles locating the
   motions. Tube-averaged `vz` is not a substitute for this maximum.
5. Report whole-grid and radial mass changes alongside energy. If the total
   drifts, inspect boundary mass/energy transport, the atmosphere/gravity
   implementation and numerical settings. Keep unmeasured fluxes explicitly
   unmeasured; do not label the drift physical heating or numerical dissipation
   without evidence. The centre-zero potential convention must remain fixed
   when mass can enter or leave the domain.
6. For the jet runs C-LO and G-LO, return the same outer-region motion and
   energy diagnostics. Complete the outstanding enclosed gravitational changes
   at `R = 10, 30, 80, 100 kpc` between 0 and 50 Myr, using
   `sum_{r_i<R} [rho_i(50)-rho_i(0)] Phi_0(r_i) V_i`. Use full cell weights
   and state the aperture convention. Record tracer extent/contamination;
   absence of jet material alone does not exclude waves reaching a region.

Existing controls can establish their own drift, but must not be subtracted
cell by cell from the different production mesh. If they cannot resolve the
production discrepancy, propose a matched-grid no-jet control with identical
boundaries, gravity, units and numerical settings; do not silently commission
a new production run. Preserve the uncorrected jet-run budgets.

## Additional requirement: stability in unreached regions of jet runs

Stas explicitly requires stability checks within the jet simulations
themselves, not only in separate no-jet controls. Regions the jet has not
reached should retain the initial atmospheric equilibrium to numerical
accuracy, provided no jet-driven shock or sound wave has reached them either.
The presence of a jet elsewhere is not an explanation for unrelated outer-grid
motion or energy drift.

- Apply this check wherever an undisturbed region remains in each jet case,
  prioritizing C-LO/G-LO and the proposed `r > 100 kpc` diagnostic region.
  Establish the region's validity at each age rather than assuming that a
  fixed radius is always beyond the disturbance.
- Distinguish the extent of jet/cocoon material from that of shocks and sound
  waves. Zero tracer or absence of a supersonic shock alone does not establish
  an undisturbed atmosphere. Use time-resolved pressure, density and velocity
  profiles/slices and propagation times to justify the region selection;
  flag uncertain disturbance arrival rather than asserting isolation.
- Within the justified region, report changes from the same initial cells
  in density, pressure, mass and each energy component, plus maximum 3D speed,
  its location and boundary distance. Retain the fixed initial potential.
  Distinguish boundary-adjacent drift from any outward-propagating jet signal,
  and compare with the existing no-jet results while stating the grid mismatch.
- Unexplained motion or energy change in an otherwise unreached region is
  an atmosphere/boundary/numerics stability concern to investigate, not energy
  to attribute to jet coupling. Preserve the full-grid raw budget and report
  the regional contribution separately; do not remove it just to force closure.

This extends Q-031's post-processing request. It neither reports a completed
stability test nor authorizes a new simulation.

## Evidence already available for jet runs

The Goal 062 archive contains axial profiles averaged, without cell-volume
weighting, across a tube of radius 2 kpc. At 50 Myr, among profile positions
with `|z| > 100 kpc`, both maxima occur at the outermost axial cell centres
`z = +/-248.948074 kpc`:

| Case | Maximum absolute tube-mean vz | Direction at both ends | Density ratio to t=0 | Pressure ratio to t=0 |
| --- | ---: | --- | ---: | ---: |
| C-LO | 45.3484 km/s | inward | 1.062104 | 1.105633 |
| G-LO | 14.0946 km/s | inward | 1.036701 | 1.061911 |

The corresponding initial outer-tube velocities are zero. At representative
axial positions near 101, 150 and 200 kpc the speeds are much smaller: C-LO
is approximately `0.0003`, `0.0011`, `0.0272 km/s`; G-LO remains below
`0.001 km/s` at those sampled positions. This is evidence of outer axial
motion, concentrated near the boundary in these profiles, not a measurement
of the maximum three-dimensional speed throughout the outer grid.

The direction is inward because vz is positive at the negative-z boundary
and negative at the positive-z boundary. Boundary-associated atmospheric
drift is a plausible explanation to test, not an established root cause.

Goal 063's native-grid C-LO shell integrals give:

| Region | Delta gravitational energy (erg) | Delta gravitational energy / E_inj |
| --- | ---: | ---: |
| r < 50 kpc | -6.7014545e56 | -0.0212356 |
| r < 100 kpc | 2.4812477e57 | 0.0786260 |
| r >= 100 kpc, within the box | 3.5938383e59 | 11.3881862 |
| Whole physical grid | 3.6186507e59 | 11.4668122 |

Thus 99.314% of the net gravitational increase lies outside 100 kpc. The
outer C-LO kinetic increase is `4.3512073e57 erg` (`0.137881 E_inj`), an
independent three-dimensional integral indicating outer motions. Inside
100 kpc, the total of all three energy changes is `1.290803 E_inj`; the
small gravitational fraction alone does not demonstrate total closure.

G-LO's enclosed-100-kpc gravitational value is not present in the retrieved
compact radial products. Do not substitute its whole-grid value or infer
enclosed energy from its non-spherical axial profile. The requested 10/30/80
kpc integrals also cannot be reconstructed from 50-kpc-wide shell bins.

## Sources and validation

- `docs/exchange/logs/2026-05-08-kunanyi-stewart-environment-gates.md`
- `docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis/calibration/`
- `docs/science/assets/four_case_fluid_snapshot_census_2026-08-25/remote_logs/four_case_fluid_snapshot_census_2026-08-25.tar.gz`
- `docs/science/assets/cluster_background_and_age_validity_2026-08-26/review_products/C-LO/shell_energy_diagnostic.csv`
- `docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis/C-LO/native_energy_selected_age.csv`

Reproduce the compact-data check with
`python scripts/science/build_outer_grid_motion_check.py`.
The JSON in `docs/science/assets/nojet_stability_followup_2026-10-21/` records
source hashes, signed speeds, coordinates, initial/current density/pressure
ratios and regional energy changes. The C-LO radial sums reproduce the Q-029
whole-grid component changes within `6.21e-13 E_inj`. This checks the existing
products; it is not the requested new no-jet energy audit.
