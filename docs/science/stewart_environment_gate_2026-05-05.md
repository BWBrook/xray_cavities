---
title: "Stewart Tabulated Environment Gate"
subtitle: "No-jet Nectar stability check, 2026-05-05"
date: "2026-05-05"
format:
  pdf:
    colorlinks: true
    geometry:
      - margin=22mm
---

# Stewart Tabulated Environment Gate, 2026-05-05

Post-meeting correction, `2026-05-07`: the environment-gate results remain
valid, but the "next gate" and jet-duty-cycle unit interpretation below were
superseded by the 2026-05-06 supervisor meeting. `JET_END_TIME` and
`JET_ACTIVE_TIME` are physical Myr values in the user parameter block; PLUTO
core controls such as `tstop` and output intervals are the values that use
PLUTO code time.

## Summary

The confirmed Stewart radially averaged environments passed the first no-jet
Nectar stability gate on `2026-05-05`.

Stas' clarification is now treated as binding for science runs: use the
tabulated radius profiles, not the full 3D grid environments, because the full
3D profiles have too much spurious motion for reliable energetics.

## Inputs

The tested files were extracted from the ignored `env/environments.zip` archive
and staged to `nectar-vm`:

| Science role | Stewart environment | Extracted asset |
| --- | --- | --- |
| `C-HI`, `C-LO` | cluster `002_003` | `tabulated_cosmo_002003.csv` |
| `G-LO` | group `002_031` | `tabulated_cosmo_002031.csv` |

The local MacBook remained the control plane. The simulations ran on
`nectar-vm` after resizing to `c3.3xlarge`.

## Gate Setup

The tests were rendered with
`scripts/science/render_stewart_environment_gate_tests.py`, using the extracted
cluster and group CSVs, the current `jet-setup` environment verifier, and the
current `jet-setup` makefile and `definitions.h` templates.

Each rendered gate uses:

- HD, 3D Cartesian, vector body force
- no jet: `JET_END_TIME = 0`, `JET_ACTIVE_TIME = 0`
- no particles: rendered `definitions.h` sets `PARTICLES = NO`
- grid: `50 x 50 x 50`, uniform `[-100, 100] kpc` in each dimension
- run duration: `300 Myr`
- PLUTO code-time conversion: `1 Myr = 306.601393788`
- outputs near `0`, `100`, `200`, and `300 Myr`

## Results

| Environment | Max central density drift | Max central pressure drift | Max Mach | Max velocity | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| cluster `002_003` | `0.136%` | `0.226%` | `0.0242` | `10.6 km/s` | pass |
| group `002_031` | `0.284%` | `0.473%` | `0.0330` | `8.07 km/s` | pass |

The `jet-setup` verifier passed all outputs for both environments. These are
smoke-scale stability gates, not final production-resolution validation.

![Stewart environment gate time series](assets/stewart_environment_gate_2026-05-05/stewart_environment_gate_timeseries.png)

![Stewart environment gate profiles](assets/stewart_environment_gate_2026-05-05/stewart_environment_gate_profiles.png)

The plotted metrics are stored as `stewart_environment_gate_metrics.csv` in the
matching asset directory.

## Implementation Notes

Two small operational fixes came out of the gate:

- `scripts/science/render_stewart_environment_gate_tests.py` now renders a
  hydro-only `definitions.h` and a particle-free `local_make`, because the
  current `jet-setup` source template otherwise keeps `PARTICLES_LP` enabled.
- `scripts/science/render_three_case_configs.py` was later corrected after the
  supervisor meeting so `JET_END_TIME` and `JET_ACTIVE_TIME` remain physical
  Myr values; only `tstop`, output intervals, and checkpoint intervals are
  converted to PLUTO code time.

During the run, `nectar-vm` SSH was switched from fragile socket activation to
persistent `ssh.service`; this is recorded in `docs/nectar_vm_setup.md`.

## Next Gate

The environment asset blocker is now cleared. After the supervisor meeting, the
next science gate is the production-like `C-HI` high-power cluster package
using:

- cluster tabulated environment `002_003`
- `JET_PWR = 1e45 erg/s`
- `JET_SPD = 0.1`
- `JET_OA_PRIMARY = JET_OA_SECONDARY = 15 deg`
- particles enabled for the nominal science run
- first target duration about `50 Myr`
- early outputs at about `1 Myr` cadence
- double restart checkpoints every `2-5 Myr` and at walltime stop
- HDF5/MPI validation on `kunanyi`

Hydro-only `C-HI` is now a narrow debugging fallback, not the planned first
science gate.
