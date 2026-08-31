# Four-case selected-age native shock-energy partition method

## Status

Method decision:
`NATIVE_3D_CONNECTED_SHOCK_PARTITION_READY_FOR_FULL_SELECTED_AGE_EXECUTION`.

This is the prespecified Goal 067 method contract. It closes the native shock
term left pending by Goal 066 without extending the observer cadence or
reinterpreting a closure residual as shock energy.

## Scientific question

Across the accepted selected ages, how much of the known bipolar injected
energy is found in the native three-dimensional shocked ambient medium, and
how is that energy divided among thermal, kinetic, gravitational, and
irreversible-heating terms?

The calculation is native-grid truth. It does not use an X-ray cavity mask,
and it does not use the tracer to define an observed cavity.

## Frozen analysis surface

- `C-HI`, `C-LO`, and `G-LO`: `10/20/30/40/50 Myr`.
- `G-HI`: `10/20/30/40 Myr`; `G-HI/50` remains excluded.
- Three threshold factors: `0.5`, `1`, and `2`; factor `1` is primary.
- Negative and positive jet sides are calculated separately. A bipolar value
  is reported only when both sides pass independently.

## Reference states and controls

Every energy term is a same-cell change from the exact `t=0` production
snapshot on the same `1014 x 960 x 960` grid. The fixed gravitational
potential follows Stas's convention:

```text
Phi_0(r) = integral_0^r |g_0(r')| dr'.
```

The tabulated initial atmosphere supplies `g_0`, and the centre is the zero of
potential. Gravitational change is therefore
`[m_ambient(t) - m(t=0)] Phi_0` cell by cell.

The existing no-jet cluster and group controls are coarser
(`500 x 400 x 400`) than the production grids. They are consequently used
only to calibrate dimensionless false-positive thresholds. They are not
described as resolution-matched controls and are never subtracted cell by
cell. For pressure, density, and entropy excess, the adopted primary cut is
the greater of a physical floor and five times the `0.9999` no-jet quantile.
The joint primary false-positive rate must not exceed `1e-6`.

## Three-dimensional shock mask

The instantaneous shock front must satisfy all of:

1. ambient gas, `tr1 <= 0.01`;
2. pressure compression relative to the same initial cell;
3. density compression relative to the same initial cell;
4. positive entropy excess
   `ln(p/p0) - gamma ln(rho/rho0)`;
5. intersection with an axial seed around the accepted one-dimensional front;
6. accepted kinematic Mach number greater than one.

The energy region is the 26-connected ambient entropy-excess component that
contains that compressed front seed. Thus the front locates the disturbance,
while the connected entropy footprint includes gas already processed by it.
The method fails closed for a missing or non-supersonic accepted front, no
seeded component, fewer than `100` selected cells, physical-boundary contact,
or a selected axial extent more than `10 kpc` from the accepted front.

These unresolved outcomes are scientific censoring, not substituted values.
In particular, later `C-LO` ages are expected to test the bilateral Mach gate
rather than being forced into a quantitative shock fraction.

## Energy ledger

Within each valid side mask, the code reports:

- ambient thermal-energy change;
- ambient kinetic-energy change;
- ambient gravitational-energy change in `Phi_0`;
- their total;
- irreversible-heating diagnostic
  `p - p0 (rho/rho0)^gamma`;
- selected volume, mass change, and cell count;
- total and irreversible fractions of the known injected energy.

The ambient share of a current cell is `1 - clip(tr1, 0, 1)`. This is a native
mixture accounting weight, not an observer mask. Values are retained per side;
the bipolar total is the sum of two independently valid sides.

## Decision gate

Goal 067 is successful if the full prespecified table is produced with valid
control calibration and explicit quantitative or unresolved status for every
case-age-side-threshold row. It does not require every row to be quantitative.

The result will be decision-relevant if it determines whether adding the
native shock term materially changes the Goal 066 comparison between X-ray
cavity enthalpy, retained energy, and injected energy. Annual-cadence shock
analysis is not opened unless the selected-age result exposes temporal
structure that could change that interpretation.

## Execution design

One complete Kunanyi job uses two cores and `128 GB`, runs two cases at a time
in two memory-safe waves, and requests up to `48 h`. Intermediate ratio,
potential, label, and mask arrays remain remote and are deleted case by case.
Only compact CSV/JSON/manifests and logs are archived. No PLUTO, XRAiSE,
PRAiSE, cavity, or radio product is rerun.

## Limitations

- The processed mask uses Eulerian same-cell entropy excess. Radial advection
  in the stratified atmosphere can contribute to that diagnostic; the no-jet
  calibration and connected front seed reduce but do not eliminate this
  interpretation risk.
- The no-jet controls calibrate numerical/background excursions but do not
  provide native-resolution cellwise subtraction.
- Boundary flux remains outside this goal, so this is an energy partition of
  the selected shocked region, not a closed whole-domain conservation proof.
- `G-HI/50` remains scientifically excluded under the accepted boundary gate.
