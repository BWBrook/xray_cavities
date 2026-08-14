# G-LO snapshot science

## Simulation setup

| Item | Locked value |
| --- | --- |
| Case | `G-LO` |
| Environment | Stewart group `002_031`; radially averaged tabulated static atmosphere |
| Physics and grid | 3-D Cartesian HD; `stewart_stretched_250`; `960 x 960 x 1014`; transverse domain approximately `-200..200 kpc`, jet-axis domain `-250..250 kpc` |
| Retained fluid snapshots | output indices `0/10/20/30/40/50`; actual times `0`, `9.9997416`, `19.9997844`, `29.9996436`, `39.9999862`, and `50.0000000 Myr` |
| Fluid output provenance | Canonical no-overwrite chain from the original and guarded G-LO production segments; later promoted segment wins only where overlap identity passed |
| Jet power | `1e43 erg s^-1` one-sided `JET_PWR`; `2e43 erg s^-1` bipolar truth |
| Jet timing | start `0 Myr`; active for `50 Myr`; analysed source remains active through the endpoint |
| Jet geometry | speed `0.1c`; primary/secondary opening angles `15/15 deg`; initial radius `0.1 kpc`; injection height `0.75 kpc`; centred two-sided internal boundary |
| Particles | `32` per injection; `0.01 Myr` injection/output cadence; retained history outputs `0..5000` |
| Tracer convention | primary fractional `clip(tr1,0,1)` operational partition; binary `1e-3`, `5e-3`, and `1e-2` sensitivities |
| Gravity | fixed centre-zero potential from the mean of the two matched Stewart gravity columns |
| Shock method | `2 kpc` axial tube; velocity cut above baseline noise; `5%` pressure/density disturbance; three-detected-snapshot local speed fit; threshold factors `0.5/1/2` |
| Radio | corrected PRAiSE2 commit `73210e15d4c60e77ffb317b3ee2b9209c049edd4`; `0.15/0.5/1.4/4.5/15 GHz`; lossless and full-loss; `z=0.05`, `eta=0.03`, `s=2.2`, `gmin=500`, `gmax=1e5`; views `0/45/90 deg`, with `45 deg` primary |
| X-ray | accepted XRAiSE `1 keV` corrected surface-brightness pathway with supplied APEC/Gaunt tables; inherited frozen Goal 041 response convention; projections `0/45/90 deg`, using edge-overlap accumulation for nonzero views |
| Cavity convention | X-ray-derived geometry with tracer truth kept separate; geometric line-of-sight depth; `pV`, adopted non-relativistic `2.5pV`, and literature-comparison `4pV` |

## Scope and current state

This is a complete single-case analysis. It must not be read as a comparison
among the four factorial cases. PBS `785488.kunanyi-ohpc` completed with
`Exit_status=0`; the retrieved corrected-PRAiSE2 archive has SHA-256
`c648d22e2059b3ec3464537b6a1992896bf1f20b0b0e37e952d7614d9dc1ce8b`,
contains all `50` primary and `150` viewing-angle radio rows, and has zero-byte
stderr. The fluid, gravitational, shock, X-ray/cavity, radio, spectral-age,
and inferred-power surfaces are therefore complete for G-LO.

## Fluid energy accounting

### Observation

The primary fractional tracer partition gives the following evolution relative
to cumulative bipolar injected energy:

| Actual age | Ambient total change / injected | Direct lobe total / injected | Zero-boundary closure residual / injected |
| ---: | ---: | ---: | ---: |
| `9.999742 Myr` | `1.038` | `0.189` | `-0.227` |
| `19.999784 Myr` | `1.147` | `0.173` | `-0.320` |
| `29.999644 Myr` | `1.261` | `0.156` | `-0.417` |
| `39.999986 Myr` | `1.358` | `0.143` | `-0.501` |
| `50.000000 Myr` | `1.449` | `0.128` | `-0.577` |

The ambient gravitational change grows from `0.066` to `0.334` of injected
energy across the same interval. Direct tracer-lobe gravitational energy is
small (`0.00007-0.00024` of injected energy), while its thermal and kinetic
components dominate the direct lobe total.

### Interpretation

The increasingly negative closure residual is not a cocoon-energy estimate.
The retained snapshots do not measure energy flux through the domain boundary,
and the operational tracer split also partitions mixed cells. The data support
reporting direct lobe and ambient components separately; they do not support
renaming the unclosed residual as missing lobe energy.

## Shock dynamics

### Observation

Both sides are detected from 10 through 50 Myr under the predeclared primary
threshold. Shock distances grow from about `34.7` to `80-81 kpc`. Local
three-snapshot speeds decline from about `1295 km s^-1` to `924-993 km s^-1`;
the corresponding kinematic Mach numbers span `2.15-2.86`.

The primary-threshold two-cell pressure and density ratios do not yield valid
Rankine-Hugoniot Mach numbers. At the `0.5` threshold sensitivity, available
pressure-jump estimates instead span about `1.15-1.85`; density-jump estimates
are almost entirely unavailable. The independent jump check therefore does
not corroborate the kinematic Mach surface cleanly.

### Interpretation

The kinematic surface is suitable for the prespecified cavity-recovery trend,
but its absolute Mach calibration remains method-sensitive. The disagreement
is reported as evidence about the velocity-front definition, not repaired
post hoc by choosing the threshold that gives the preferred Mach number.

## X-ray cavity recovery

### Observation

For the primary `45 deg` view, the accepted X-ray topology gate permits
quantitative cavity energetics at 20, 40, and 50 Myr. The 10 Myr map is a
connected cross-midplane component and the 30 Myr map has multiple or one-sided
components, so both remain nonquantitative.

| Age | `2.5pV / E_inj` | `4pV / E_inj` | `2.5pV / E_lobe,direct` | Topology status |
| ---: | ---: | ---: | ---: | --- |
| `20 Myr` | `0.238` | `0.381` | `1.379` | quantitative, two components |
| `40 Myr` | `0.073` | `0.117` | `0.512` | quantitative, two components |
| `50 Myr` | `0.050` | `0.080` | `0.388` | quantitative, two components |

The associated sound, buoyancy, and refill ages are retained as contextual
observational benchmarks. At 50 Myr they are approximately `79.4`, `43.3`, and
`119.1 Myr`, respectively; none replaces the requested spectral-age analysis.

### Interpretation

At 20 Myr, adopted `2.5pV` slightly over-recovers the direct tracer-lobe energy
while recovering only about one quarter of injected energy. By 50 Myr it
under-recovers both. This is qualitatively consistent with an increasing share
of the source energy residing outside the X-ray-defined cavity, but the sparse
quantitative topology surface and Mach-method sensitivity preclude a strong
functional claim within G-LO alone.

## Corrected-PRAiSE2 radio evolution

### Observation

The exact matched particle states are causal: no radio row uses particle
information later than its fluid snapshot. Active particle counts rise from
`42030` at 10 Myr to `197566` at 50 Myr. In the primary `45 deg` view, full-loss
`1.4 GHz` luminosity rises from `1.529e24 W Hz^-1` at 10 Myr to a broad plateau
near `2.6e24 W Hz^-1` at 30-50 Myr. The full-loss/lossless ratios at 1.4 GHz are
`1.047`, `1.058`, `1.001`, `0.942`, and `0.894` from 10 to 50 Myr; at 15 GHz
they are `1.035`, `1.030`, `0.959`, `0.877`, and `0.804`. The corresponding
full-loss effective magnetic field declines from `4.106` to `2.277 microG`.

Viewing-angle sensitivity is modest for these integrated scalar products. The
largest `max/min` luminosity ratio across `0/45/90 deg`, all five ages, both
loss treatments, and all five frequencies is `1.061`.

### Interpretation

The late-time, high-frequency deficit is the clearest radio signature of
radiative ageing in this surface. The small early full-loss excess is retained
as model output rather than forced to zero. It shows that the two population
branches are not acting as a simple multiplicative attenuation at early ages;
without a particle-resolved attribution it should not be interpreted as net
energy gain. The integrated orientation effect is much smaller than the
late-time high-frequency loss effect for G-LO.

## Spectral-age recovery

### Observation

Continuous-injection fits are numerically tight, but every fitted break lies
above the observed `15 GHz` ceiling: the fitted break decreases from about
`682 GHz` at 10 Myr to `20.0 GHz` at 50 Myr. The reported break is therefore
censored at `15 GHz`, and every derived spectral age is an upper limit rather
than a point estimate.

At the quantitatively valid `45 deg` cavity ages of 20, 40, and 50 Myr, the
matched-PRAiSE effective-field upper-limit ages are `32.01`, `33.46`, and
`33.54 Myr`, or `1.60`, `0.837`, and `0.671` times the true source age. The
observer-equipartition treatment gives `14.09`, `13.24`, and `13.29 Myr`, or
`0.704`, `0.331`, and `0.266` times the true age. The maximum-age magnetic
field treatment remains close to `33.66 Myr` across those snapshots.

### Interpretation

The fitted break moves in the expected ageing direction, but the available
frequency band does not locate it. Spectral ages therefore cannot yet be
treated as unbiased clocks. The growing late-time underestimate under the
observer-equipartition field and the field-treatment spread are substantive
method uncertainty, not plotting variation.

## Inferred jet-power recovery

### Observation

Against the known bipolar power `2e43 erg s^-1`, the full-loss approximate
Kokotanekov 150 MHz relation returns central ratios of `3.09-4.07`, with its
adopted `0.85 dex` intrinsic-scatter interval still containing the known power.
The Cavagnolo 1.4 GHz relation returns central ratios of `4.91-7.12`; its
`0.7 dex` lower bound is approximately equal to the known power at 10 Myr and
above it at later ages.

For valid `45 deg` cavities, `2.5pV/t_spec` using the matched-PRAiSE effective
field recovers `0.149`, `0.087`, and `0.074` of known power at 20, 40, and
50 Myr; `4pV/t_spec` gives `0.238`, `0.140`, and `0.119`. Under the
observer-equipartition field those ratios are higher but still below unity:
`0.338/0.221/0.187` for `2.5pV` and `0.541/0.353/0.299` for `4pV`.

### Interpretation

The two observer-style families bracket the truth in opposite directions:
central radio-luminosity scaling relations overestimate the known power,
whereas cavity energy divided by the censored spectral-age upper limit
underestimates it. Because `t_spec` is an upper limit here, the latter powers
are lower bounds conditional on the selected cavity and magnetic-field
treatment. G-LO alone demonstrates a method-dependent recovery bias; it does
not establish an environmental or jet-power trend.

## Reusable four-case pipeline

The fluid controller is case-parameterised, and the final assembler now locks
the four intended cases (`C-HI`, `C-LO`, `G-LO`, `G-HI`) to the correct
cluster/group atmosphere and `1e43/1e45 erg s^-1` one-sided powers. It validates
source truth against the energy surface, exact radio-view coverage, causal
particle matching, accepted X-ray topology gates, and the case-specific known
bipolar power. This establishes a common analysis method; it does not itself
constitute a four-case comparison.

The complete compact synthesis is at
`docs/science/assets/g_lo_snapshot_science_2026-08-14/synthesis/`. It contains
the locked setup and source truth, primary fluid and shock tables, the full
radio/view surface, X-ray/cavity recovery, spectral fits, inferred-power
tables, seven diagnostic figures, input hashes, and machine-readable product
validation. The decision label is
`G_LO_SINGLE_CASE_PIPELINE_GREEN_RECOVERY_BIASES_EXPOSED_NO_CROSS_CASE_CLAIM`.
