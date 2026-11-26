# Energy transport through the velocity-defined spheres

The four production runs have 201 retained native snapshots and 197 adjacent time intervals. R100 and R300 are the outermost cell-centre radii at which the three-dimensional speed reaches 100 and 300 km/s. The measured volume contains every cell centre within that radius. The [registration](assets/aperture_transport_2026-11-26/registration.json) fixes the native and initial file identities, grid, atmosphere, radii, enclosed cell counts, volumes and energy changes before the transport extraction. G-HI ends at 47 Myr. The grid has 960 × 960 × 1,014 cells. Time zero already encloses the 14,328 maintained injector cells in every case.

## Surface and sign

Count every Cartesian face between an enclosed cell and an excluded neighbour once. Also count the portion of the computational box enclosing selected cells. Retain the two contributions separately. A sphere extending beyond a box face measures the intersection with the computational domain. Its missing exterior has no observed flux. The cell-centre convention, including the limiting floating-point tie, must reproduce each registered count and volume at both ends of every interval.

Positive flux leaves the selected volume. The primary estimate interpolates both neighbouring primitive states to the face centre on the stretched mesh. The sensitivity estimate uses the upstream cell as determined by the face-normal velocity. A domain face uses the adjacent active cell. Sum mass flux, advected internal energy, pressure work, kinetic energy and potential energy over the actual face areas. Evaluate the fixed initial potential at each face, with zero at the centre. The advected internal energy and pressure-work terms together constitute enthalpy flux. Under a shift of potential zero by a constant, potential-energy transport shifts by that constant times mass transport.

## Motion of the aperture

Let \(S_i(R)\) be the stored energy change relative to time zero **in the same cells** of aperture \(R\), and \(F_i(R)\) its instantaneous outward energy flux. For an interval with initial and final radii \(a,b\), the energy change contributed by the change of membership is

\[
M=\tfrac12\{[S_0(b)-S_0(a)]+[S_1(b)-S_1(a)]\}.
\]

Here the subscripts denote interval endpoints. The change of stored energy minus \(M\) is exactly the mean of the two stock changes evaluated at **fixed** radii. Compute the outward transport on those same two fixed surfaces by endpoint trapezoids,

\[
T=\tfrac{\Delta t}{4}[F_0(a)+F_1(a)+F_0(b)+F_1(b)].
\]

Keep the two fixed-radius estimates and the moving-endpoint trapezoid to show sensitivity to the annual sampling. The same motion identity and flux accounting apply to mass. For the mass check, subtract the signed net mass supplied across the injector and the measured change in maintained-cell mass. The native injector stencils show identical density values in those 14,328 cells at all 201 snapshots. The maintained-cell mass term is therefore zero in all 197 intervals. Report the mass residual in grams and in units of labelled jet mass. Signed net mass delivery can pass through zero when ambient gas enters the stationary part of the injector. [Maintained mass and stencil identities](assets/aperture_transport_2026-11-26/maintained_masses.csv) The sweep is a stock change relative to the initial atmosphere, so it excludes the undisturbed atmosphere acquired by expanding the aperture. Rates are in cgs and use the actual elapsed time of each pair.

## Injector normalization and balance

Use the signed gas energy delivered across the complete discretised injector surface, \(D_{\rm gas}\), from the [archived injector history](production_injector_histories_2026-11-21.md). The primary reconstruction uses the stored linear states and solver flags, with trapezoidal integration. The axial, lateral and stationary sectors all contribute. Report the balance as \(\Delta S-M+T-D_{\rm gas}-D_{\Phi}-\Delta E_{\rm maintained}\). The last two terms account for injector potential-energy transport and changing storage in its maintained cells. Keep the mechanical denominator \(D_{\rm gas}\) and nominal labelled input separately visible. For cumulative ratios, sum signed energies first and divide by cumulative delivery.

These snapshot estimates have one sample per Myr. Rapid wave or jet passages can fall between outputs, and a reconstructed primitive-state flux can differ from the solver's time-integrated flux. Separate both limitations from the exact discrete membership correction and the archived stock changes. A balance residual by itself does not identify dissipation, a shock or an entropy-switch contribution. The [component partition](four_case_energy_partition_2026-11-26.md) gives the complementary cocoon and ambient measurements.

## Checks added after the 30-Myr pilot

At time zero both apertures coincide with the maintained injector. At each end of the first interval, compare the reconstructed gas and total-energy rates through this fixed, 4,296-face surface with the saved-flag injector reconstruction on the same faces. Replacing only those two of the four samples gives a signed first-interval correction. Report it separately from the registered estimate. The same correction applies to both apertures.

A separate native C-LO/30 extraction scans the rows and columns of each plane to find the first and last enclosed cells. Compare its independently interpolated rates, face counts, areas, volumes and cell counts at both radii. It shares the source snapshot, coordinates, radii, units and potential with the primary extraction. The native file is also rehashed in full.

The 30-Myr pilot showed the largest difference between instantaneous R100 and R300 fluxes in C-LO. To test the annual time rule, use its retained 10–11 Myr production-control restart, with output every 0.1 Myr. The 10-Myr initial state and the 11-Myr control have an existing comparison with production. Hold each of the two production endpoint radii fixed for the whole Myr, for both speed cuts. Compare ten short trapezoids with one long trapezoid on each surface and their mean. Verify the endpoint fluxes against the annual measurement before interpreting the difference. This checks one case and window. The fine-cadence measurements were unseen when the window was chosen. The test also leaves any variation faster than 0.1 Myr unresolved.
