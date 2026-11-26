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

Keep the two fixed-radius estimates and the moving-endpoint trapezoid to show sensitivity to the annual sampling. The same motion identity and flux accounting apply to mass. The sweep is a stock change relative to the initial atmosphere, so it excludes the undisturbed atmosphere acquired by expanding the aperture. Rates are in cgs and use the actual elapsed time of each pair.

## Injector normalization and balance

Use the signed gas energy delivered across the complete discretised injector surface, \(D_{\rm gas}\), from the [archived injector history](production_injector_histories_2026-11-21.md). The primary reconstruction uses the stored linear states and solver flags, with trapezoidal integration. The axial, lateral and stationary sectors all contribute. Report the balance as \(\Delta S-M+T-D_{\rm gas}-D_{\Phi}-\Delta E_{\rm maintained}\). The last two terms account for injector potential-energy transport and changing storage in its maintained cells. Keep the mechanical denominator \(D_{\rm gas}\) and nominal labelled input separately visible. For cumulative ratios, sum signed energies first and divide by cumulative delivery.

These snapshot estimates have one sample per Myr. Rapid wave or jet passages can fall between outputs, and a reconstructed primitive-state flux can differ from the solver's time-integrated flux. Separate both limitations from the exact discrete membership correction and the archived stock changes. A balance residual by itself does not identify dissipation, a shock or an entropy-switch contribution. The [component partition](four_case_energy_partition_2026-11-26.md) gives the complementary cocoon and ambient measurements.
