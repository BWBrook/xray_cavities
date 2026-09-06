# Four-case dual-space energetics audit design

## Simulation setup

| Item | Configuration |
| --- | --- |
| Cases | `C-HI`, `C-LO`, `G-HI`, and `G-LO` |
| Environments | Stewart cluster `002003` for `C-*`; Stewart group `002031` for `G-*` |
| Grid/domain | Cartesian `960 x 960 x 1014`; X1/X2 `-200..200 kpc`, X3 `-250..250 kpc`; central `0.05 kpc` cells with stretched outer zones |
| Jet power | One-sided `1e45 erg/s` for `*-HI`, `1e43 erg/s` for `*-LO`; bipolar powers `2e45` and `2e43 erg/s` |
| Jet geometry | Speed `0.1c`; two `15 deg` cones; initial radius `0.1 kpc`; injection height `0.75 kpc`; centred launch |
| Particles | `Nparticles = 32` per injection event; particle cadence approximately `0.01 Myr` |
| Fluid output | Float approximately every `1 Myr`, double approximately every `5 Myr`; exact 50 Myr endpoint retained |
| Primary material split | Fractional `f=clip(tr1,0,1)`; binary thresholds are sensitivities only |
| Gravity | Fixed centre-zero potential integrated from the initial static atmosphere |
| X-ray views | `0/45/90 deg`; X-ray-only cavity detection; tracer is post-hoc truth only |
| Validity | Boundary- and topology-gated; `G-HI/50` is excluded and annual snapshots 48--50 retain boundary-failure status |

## Supervisor decision

The energetics audit must calculate the cavity and outburst energetics in two
independent ways:

1. a native-grid truth calculation that accurately partitions every cell into
   lobe and ambient material; and
2. an observer-like X-ray calculation that estimates the volume of the
   detected cavities and averages the inferred pressure/enthalpy over that
   volume.

The native calculation is view independent. The X-ray calculation is
projection dependent and must never use tracer to define a cavity, repair a
topology, select a volume, or choose a pressure. Tracer may be overlaid only
after both calculations are complete.

## Native-grid ledger

For each native cell `i`, define

```text
f_i = clip(tr1_i, 0, 1)
u_i = p_i / (gamma - 1)
k_i = 0.5 rho_i |v_i|^2
g_i = rho_i Phi_0(r_i)
```

with `gamma=5/3` and

```text
Phi_0(r) = integral_0^r g_0(r') dr'.
```

`Phi_0` is evaluated once from the initial static atmosphere and is never
recomputed from a disturbed snapshot. Thermal, kinetic, and gravitational
changes are evaluated cell by cell against the same cell at `t=0`. For a
quantity density `q`, the primary partitions are

```text
Delta E_lobe,q(t)
  = sum_i {[f_i(t) q_i(t) - f_i(0) q_i(0)] V_i}

Delta E_ambient,q(t)
  = sum_i {[(1-f_i(t)) q_i(t) - q_i(0)] V_i}.
```

The design assumed `f_i(0)=0`. The Q-029 audit on 2026-09-06 found that the
retained t=0 files contain a nonzero nozzle/tracer region, so this reduction
must not be used for those files. The implementation's absolute current lobe
energy is distinct from a lobe energy change. The corrected binary allocation
and complementary current-region changes are defined in
`q029_binary_native_refresh_2026-09-06.md`; neither assumes zero initial tracer.

When matched no-jet controls are available, subtract their cell-wise evolution
from the second expression. One cluster and one group control are sufficient
because each environment is shared by its low- and high-power pair. Until
then, `C-LO` ambient energetics retain the existing background-dominated gate.

The native physical ledger is

```text
E_retained = E_lobe,thermal + E_lobe,kinetic + E_lobe,gravitational
           + Delta E_ambient,thermal
           + Delta E_ambient,kinetic
           + Delta E_ambient,gravitational.
```

Boundary flux must be calculated before promoting the closure residual:

```text
E_injected = E_retained + E_boundary + E_residual.
```

The residual is not cocoon energy. It remains unattributed unless the
background and boundary terms are quantified.

For comparison with cavity thermodynamics, also calculate the native lobe
pressure-volume conventions

```text
H_lobe,grid(alpha) = alpha sum_i [f_i p_i V_i],

alpha = 2.5  non-relativistic physical interpretation
alpha = 4.0  relativistic literature comparator.
```

Only the `2.5pV` form is the native thermodynamic enthalpy for this gas. The
`4pV` form is a convention-matched sensitivity. Neither may be added to the
native physical ledger because the `pV` contribution represents work whose
consequences are already present in the ambient energy terms.

## Shock partition

Shock-specific energy is a native-grid truth product in this audit. The
native-grid calculation must identify both an instantaneous bow-shock
front and the ambient material processed by that shock. Use a connected 3D
ambient mask based on pressure/density compression and entropy excess,
validated against the accepted axial positions and Mach numbers. The primary
entropy diagnostic is

```text
Delta ln K = ln(p_jet/p_control)
           - gamma ln(rho_jet/rho_control).
```

Within the shock-processed ambient mask, report thermal, kinetic, and
gravitational changes separately. Also report the irreversible-heating proxy

```text
E_irreversible = sum_shock {
  [p_jet - p_control (rho_jet/rho_control)^gamma]
  / (gamma - 1) * V
}.
```

Ambient gravitational uplift remains a separate mechanical component rather
than being called shock heat. Thresholds must be calibrated against no-jet
noise and carried as a sensitivity surface.

An observer-derived shock energy based on projected X-ray jumps and a fitted
hydrodynamic shock model would be a separate later sensitivity; it is not to
be silently equated with this native shock ledger.

## X-ray cavity ledger

For each case, snapshot, side, and view, use the accepted X-ray-only deficit
mask and topology gate. Fit the projected component and infer an ellipsoidal
volume `V_X`. Geometric line-of-sight depth remains primary; minor- and
major-depth assumptions remain systematic sensitivities.

The standard observer calculation uses pressure at the cavity midpoint:

```text
H_X,mid(alpha) = alpha p_X(R_mid) V_X.
```

The preferred pressure-gradient-aware calculation averages the X-ray-inferred
ambient pressure profile over the inferred three-dimensional ellipsoid:

```text
p_X,bar = (1/V_X) integral_VX p_X,ambient(r) dV

H_X,avg(alpha) = alpha p_X,bar V_X
               = alpha integral_VX p_X,ambient(r) dV,
```

with `alpha=2.5` for the non-relativistic science interpretation and `alpha=4`
for literature comparison. Both midpoint and volume-averaged results must be
retained. The current tracer-shell pressure may be used only as a labelled
prove-out proxy; the publication-facing observer path requires an X-ray-fitted
or synthetic-X-ray-deprojected pressure profile.

An optional bridge may sample native pressure inside the inferred X-ray
ellipsoid. It must be labelled `diagnostic_not_observable` and cannot replace
the observer estimate.

## Matched decomposition

Join the two ledgers only after they are independently complete, matching
case, actual snapshot time, side, and view. Retain native-grid rows even when
the X-ray topology fails; failure to recover a cavity is itself an
observational result.

Define the native tracer-weighted lobe volume and pressure by

```text
V_lobe = sum_i f_i V_i
p_lobe,bar = sum_i(f_i p_i V_i) / V_lobe.
```

For the non-relativistic comparison, the cavity-to-native enthalpy bias
factorizes exactly:

```text
H_X,avg / H_lobe,grid
  = (V_X / V_lobe) * (p_X,bar / p_lobe,bar).
```

This gives separate volume-recovery and pressure-recovery terms. The audit
must then report three distinct adequacy ratios:

```text
A_lobe  = H_X / H_lobe,grid
A_total = H_X / E_retained
A_inj   = H_X / E_injected.
```

`A_lobe` asks whether X-ray cavity enthalpy measures the lobe. `A_total` and
`A_inj` ask whether it represents the whole outburst. These questions must not
be conflated.

Also report

```text
f_shock = E_shock_region / E_injected
f_irr   = E_irreversible / E_injected.
```

The central science test is whether `A_total` or `A_inj` decreases as Mach
number and native shock-energy fraction increase, after separately exposing
volume and pressure biases.

## Required products

- `native_grid_energy_timeseries.csv`: every cell-wise lobe and ambient term,
  injected energy, boundary term, and closure status.
- `native_shock_energy_timeseries.csv`: shock-region thermal, kinetic,
  gravitational, irreversible, Mach, and threshold-sensitivity terms.
- `xray_cavity_enthalpy_timeseries.csv`: topology, view, volume assumptions,
  midpoint and volume-averaged pressures, `2.5pV`, and `4pV`.
- `matched_native_xray_energetics.csv`: volume, pressure, lobe, total-outburst,
  injected-energy, and shock-fraction comparisons.
- `energetics_audit_summary.csv`: per-case exact medians and ranges with
  topology, background, boundary, and censoring counts.

Native products should cover every annual snapshot that passes the physical
validity gates. The observer-like X-ray surface should ultimately use the same
cadence. Existing selected-age X-ray products can prove the join first, but
they are not the final all-snapshot audit.

## Required figures

- Stacked native-grid energy fractions versus time for each case.
- Native shock-region components and irreversible heating versus time.
- X-ray `2.5pV` and `4pV` against native lobe enthalpy, retained energy, and
  injected energy.
- Volume bias and pressure bias separately versus time and view.
- `A_lobe`, `A_total`, and `A_inj` versus native shock fraction and Mach.
- Selected-age waterfall diagrams from injected energy to each native
  component, with X-ray cavity estimates overplotted rather than added.

Use a factor-of-two band as a descriptive cavity-adequacy guide. Label a point
`unresolved`, rather than good or bad, whenever topology, background, boundary,
or closure gates fail.

## Literature alignment

The native internal/kinetic/potential split and separate cocoon/external-medium
accounting follow the simulation strategy of Hardcastle and Krause and later
jet-energy partition work. The pressure-gradient sensitivity is also
motivated by recent mock-X-ray cavity studies showing that midpoint and outer
pressures can materially change inferred enthalpy.

- <https://arxiv.org/abs/1301.2531>
- <https://academic.oup.com/mnras/article/498/3/3870/5900565>
- <https://academic.oup.com/mnras/article/536/1/145/7903412>
