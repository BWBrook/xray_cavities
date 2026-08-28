# Four-case cavity-age and inferred-power comparison

## Simulation setup

| Item | Configuration |
| --- | --- |
| Cases | `C-HI`, `C-LO`, `G-HI`, and `G-LO` |
| Environments | Stewart cluster `002003` for `C-*`; Stewart group `002031` for `G-*` |
| Grid/domain | Cartesian `960 x 960 x 1014`; X1/X2 `-200..200 kpc`, X3 `-250..250 kpc`; central `0.05 kpc` cells with stretched outer zones |
| Jet power | One-sided `1e45 erg/s` for `*-HI`, `1e43 erg/s` for `*-LO`; known bipolar powers are `2e45` and `2e43 erg/s` |
| Jet geometry | Speed `0.1c`; two `15 deg` cones; initial radius `0.1 kpc`; injection height `0.75 kpc`; centred launch |
| Particles | `Nparticles = 32` per injection event; particle cadence approximately `0.01 Myr` |
| Fluid output | Float approximately every `1 Myr`, double approximately every `5 Myr`; exact 50 Myr endpoint retained |
| X-ray surface | X-ray-only one-percent projected-area deficit mask; `0/45/90 deg`; geometric line-of-sight depth; side-specific tracer-shell pressure proxy |
| Radio surface | Corrected PRAiSE2; continuous-injection fit; `z=0.05`, `eta=0.03`; `0.15/0.5/1.4/4.5/15 GHz` |
| Science ages | `10/20/30/40/50 Myr`, except boundary-contaminated `G-HI/50`, which is excluded |

## Purpose

This comparison tests the observational age choices used to convert a cavity
energy into a jet power. It retains seven treatments separately:

1. the true simulation age, as a control;
2. sound-crossing age;
3. buoyant-rise age;
4. refill age;
5. instantaneous shock-kinematic age;
6. spectral age using the global tracer-lobe mean-pressure field; and
7. spectral age using the 1.4 GHz emissivity-weighted field.

The calculation uses the 37 retained case/age/view combinations for which the
X-ray-only recovery finds exactly two non-crossing cavities. These comprise 74
side-specific cavity components. Nonquantitative X-ray topologies are not
forced into the comparison.

## Age definitions

For each recovered cavity side, `R` is the projected distance from the source
to the X-ray component centroid, `V` is the geometric-depth ellipsoid volume,
and `S` is the projected cross-section normal to buoyant motion. The initial
static atmosphere supplies

```text
c_s(r) = sqrt[gamma p_0(r) / rho_0(r)]

g(r) = -[1 / rho_0(r)] dp_0(r)/dr.
```

The nozzle-regularised central region is excluded when reconstructing the
atmosphere; the radial profile starts at 1 kpc. Every accepted cavity centroid
is beyond 16 kpc. Against the independent group environment table, the maximum
relative differences are `1.04e-4` in sound speed and `1.78e-3` in gravity.

The standard cavity ages are

```text
t_cs = R / c_s,

v_b = sqrt[2 g V / (C_D S)],       C_D = 0.75,
t_buoy = R / v_b,

r_eff = [3V / (4 pi)]^(1/3),
t_refill = 2 sqrt(r_eff / g).
```

The shock estimate is

```text
t_shock = R_shock / v_shock.
```

It is quantitative only when both axial sides have a detected disturbance
with positive centred speed and kinematic Mach number greater than one. This
fails closed for all accepted `C-LO` cavity views; 27 of the 37 cavity views
have quantitative bilateral shock ages.

The two spectral ages retain the accepted continuous-injection break and use

```text
t_spec[Myr] = 1590 sqrt(B[uG])
              / (B[uG]^2 + B_CMB[uG]^2)
              / sqrt[(1 + z) nu_b[GHz]],

B_CMB[uG] = 3.25 (1 + z)^2.
```

A fitted break above 15 GHz is an age upper limit, not a measurement. The
corresponding cavity power is therefore a lower limit. The compact surface has
40 such upper-limit rows among its 74 spectral rows.

## Cavity-power definitions

For side-resolved sound, buoyant, refill, and shock ages, the bipolar inferred
power is calculated without averaging away side asymmetry:

```text
Q_cav(alpha) = sum_i [alpha p_i V_i / t_i],
```

where `i` denotes the two cavity sides. For the common true or spectral age,
the summed bipolar energy is divided by that age. The adopted science value is
`alpha=2.5` for non-relativistic lobe plasma; `alpha=4` is retained for direct
comparison with the relativistic-cavity literature.

## Age results

Median exact inferred-to-true age ratios over the quantitatively valid X-ray
views are:

| Case | Sound | Buoyant | Refill | Shock | Spectral, mean pressure | Spectral, emissivity weighted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `C-HI` | `1.39` | `2.68` | `3.13` | `1.32` | `0.57` | `0.40` |
| `C-LO` | `1.67` | `3.12` | `2.12` | unavailable | `0.54` | `0.50` |
| `G-HI` | `2.85` | `4.00` | `5.33` | `1.46` | all upper limits | all upper limits |
| `G-LO` | `1.59` | `2.41` | `2.66` | `2.16` | all upper limits | all upper limits |

The buoyant-to-sound age ratio ranges from `1.20` to `2.36`, with median
`1.57`. Thus `t_buoy approximately 2 t_cs` is a useful order-of-magnitude
description, but not a fixed conversion. The fitted cavity geometry and local
initial atmosphere must be used for each object.

## Inferred-power results

Using the true age isolates cavity-energy recovery from age-estimator bias.
Median inferred-to-known bipolar power ratios are:

| Case | `2.5pV / t_true` | `4pV / t_true` |
| --- | ---: | ---: |
| `C-HI` | `0.0081` | `0.0130` |
| `C-LO` | `0.628` | `1.004` |
| `G-HI` | `0.00437` | `0.00699` |
| `G-LO` | `0.0731` | `0.117` |

The standard cavity ages are generally longer than the true source age and
therefore reduce the inferred power further. For example, the median adopted
`2.5pV` recovery changes from `0.628` with the true age to `0.379`, `0.205`,
and `0.296` with the sound, buoyant, and refill ages in `C-LO`.

Exact spectral ages are shorter than the true age in the two cluster cases.
They consequently raise the adopted median power recovery to `0.0124`
(mean-pressure field) or `0.0405` (emissivity-weighted field) for `C-HI`, and
to `1.05` or `1.48` for `C-LO`. The group spectral powers are lower limits and
must not be summarized as ordinary medians.

The main result is therefore not just an age bias. Even with the known true
age, the accepted X-ray `pV` geometry and pressure recover only about 0.4--0.8
percent of the high-power jets under `2.5pV`. Changing the age prescription by
a factor of a few cannot repair that deficit. This is consistent with the
project hypothesis that cavity methods become poor representations of the
total injected/lobe energy for strongly shocked systems, but the causal claim
must still be tested against the accepted Mach and direct-energy surfaces.

## Interpretation and next use

- Do not replace the three standard cavity times with a single assumed
  `2 t_cs` age. Carry sound, buoyant, and refill estimates separately.
- Keep the shock age as a distinct dynamical comparator and fail closed where
  the bilateral disturbance is not supersonic.
- Use mean-pressure spectral age as the primary global-cocoon treatment and
  emissivity weighting as an observer-like sensitivity.
- Keep true-age powers as the control that separates energy-recovery bias from
  age bias.
- Preserve `2.5pV` for the non-relativistic science interpretation and `4pV`
  for literature comparison.
- Exclude `G-HI/50` from every table, median, and plot.
- Treat the tracer-shell pressure as a labelled proxy, not an X-ray-fitted
  pressure measurement.

These products should replace the age-method portion of the pending Goal 065
revision. They do not replace the separate cell-wise energy closure or the
cavity-bias-versus-shock-Mach test.

## Literature context

The sound, buoyancy, and refill definitions follow the standard X-ray cavity
practice in Birzan et al. (2004), Rafferty et al. (2006), and the review by
McNamara and Nulsen (2007). Dunn and Fabian (2004) provide the associated
enthalpy and cavity-power context. Spectral age remains a complementary radio
clock rather than the default age in large X-ray cavity catalogues.

- Birzan et al. (2004): <https://arxiv.org/abs/astro-ph/0402348>
- Dunn and Fabian (2004): <https://arxiv.org/abs/astro-ph/0409055>
- Rafferty et al. (2006): <https://arxiv.org/abs/astro-ph/0605323>
- McNamara and Nulsen (2007): <https://doi.org/10.1146/annurev.astro.45.051806.110625>

## Evidence and reproduction

Machine-readable tables, metadata, checksums, and figures are under
`docs/science/assets/four_case_cavity_age_method_comparison_2026-08-28/`.
The primary files are:

- `xray_cavity_age_geometry.csv`;
- `age_method_comparison.csv`;
- `cavity_power_method_comparison.csv`;
- `age_power_method_summary.csv`;
- `age_estimator_comparison.png`;
- `buoyancy_to_sound_ratio.png`; and
- `cavity_power_recovery_by_age_method.png`.

Rebuild with:

```bash
python scripts/science/build_four_case_cavity_age_method_comparison.py --force
```
