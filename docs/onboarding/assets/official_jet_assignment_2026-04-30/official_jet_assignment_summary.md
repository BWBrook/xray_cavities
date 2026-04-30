# Official PLUTO HD/Jet Assignment Summary

This smoke report follows Patrick's supplied Martin Krause jet assignment using
PLUTO `Test_Problems/HD/Jet` in 2D cylindrical coordinates.

Run setup:

- Ambient-to-jet density ratio: `10`
- External Mach number: `20`
- Pressure matched jet and uniform environment.
- Two resolutions: `10` and `20` cells per beam radius.
- Domain: `0 <= r <= 8`, `0 <= z <= 32`, beam radius `1`.

Artifacts:

- `official_jet_density_r10.png`
- `official_jet_density_r20.png`
- `official_jet_diagnostics_timeseries.png`
- `official_jet_metrics.csv`

Diagnostic notes:

- The bow-shock position is estimated from the furthest on-axis pressure
  enhancement above `1.10` times ambient pressure.
- The KH growth-rate estimate uses the incompressible sheet formula with
  characteristic wavelength `2 R_beam`; it is a scale check, not a full
  compressible stability analysis.
- Rankine-Hugoniot checking is summarized by the measured bow-shell density
  compression relative to the strong-shock ideal-gas limit of `4`.

## 10 cells per beam radius

- Final bow position: `19.550`
- Mean bow speed from origin: `1.303`
- Strong-shock density-ratio limit: `4.000`
- Measured bow-shell density ratio: `3.432`
- Most negative backflow speed: `-4.003`
- Characteristic shear velocity estimate: `9.503`
- KH growth-rate scale for lambda=2R: `8.582`

## 20 cells per beam radius

- Final bow position: `19.475`
- Mean bow speed from origin: `1.298`
- Strong-shock density-ratio limit: `4.000`
- Measured bow-shell density ratio: `4.613`
- Most negative backflow speed: `-4.141`
- Characteristic shear velocity estimate: `10.069`
- KH growth-rate scale for lambda=2R: `9.093`

