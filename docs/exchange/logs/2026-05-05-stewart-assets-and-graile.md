# 2026-05-05 Stewart Assets And GRAiLE Bundle

Post-meeting correction, `2026-05-07`: the environment assets and GRAiLE notes
remain current, but the follow-on plan below was superseded by the 2026-05-06
supervisor meeting. The nominal first science package is now particles-enabled
`C-HI` to about `50 Myr`, with `JET_END_TIME` and `JET_ACTIVE_TIME` rendered as
Myr values.

## Summary

Patrick supplied the missing environment and X-ray assets under ignored
`env/`. Stas clarified the key science decision: use the radially averaged
tabulated environments for science runs, not the full 3D environment cubes.

This resolves the previous "which Stewart environments?" blocker and replaces
it with a concrete Nectar stability gate.

## Environment Assets

The large archive is:

```text
env/environments.zip
```

It is about `7.5 GiB` locally and contains:

- full 3D environment files
- tabulated radially averaged environments
- example `environment.ini` files for the full environments

Only the tabulated files were extracted:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002003.csv
env/extracted/environments/tabulated/tabulated_cosmo_002031.csv
```

Use these mappings:

| Case | Environment file |
| --- | --- |
| `C-HI` | `tabulated_cosmo_002003.csv` |
| `C-LO` | `tabulated_cosmo_002003.csv` |
| `G-LO` | `tabulated_cosmo_002031.csv` |

The full 3D environments are not selected for science energetics because Stas
warned that spurious grid motion makes them unreliable for this purpose.

## Asset Metadata

Both selected tabulated environments have:

- `4000` rows
- six cgs columns: radius, density, pressure, temperature, gravity, gravity
- strictly increasing radius
- radius range `0` to `1.697123e24 cm`

The cluster central density is `1.537677e-26 g cm^-3`; the group central
density is `4.151229e-27 g cm^-3`.

## Simulation INIs

Patrick supplied:

```text
env/inis.zip
```

Important detail from these old INIs:

```text
1 Myr = 306.601393788 PLUTO code-time units
```

The corrected config renderer now keeps this conversion for PLUTO core
controls and outputs. For the first `50 Myr` target, this renders as:

```text
tstop = 15330.06968940
dbl/dbl.h5 snapshot interval = 306.60139379
JET_END_TIME = 50.0
JET_ACTIVE_TIME = 50.0
```

## GRAiLE/XRAiSE

Patrick supplied:

```text
env/graile-all.zip
```

It includes the XRAiSE helper source, X-ray image-generation script, observing
parameter YAML, old simulation-directory YAML, correction tables, an example
X-ray HDF5 product, and Georgia's notes.

The next X-ray task is not asset acquisition anymore. It is porting the
absolute paths and old `analysis` conda assumptions into the current
MacBook/Nectar/kunanyi workflow.

## New Helper

Added:

```text
scripts/science/render_stewart_environment_gate_tests.py
```

It creates `jet-setup/test/run-tests.py` compatible no-jet stability tests for
the selected tabulated cluster and group environments.

Example:

```bash
python3 scripts/science/render_stewart_environment_gate_tests.py \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --group-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002031.csv \
  --output build/science/stewart_environment_gate_tests \
  --force
```

## Next Gate

1. Generate and validate the particles-enabled `C-HI` symmetric package.
2. Run a production-like no-jet Stewart tabulated environment/MPI/HDF5 gate on
   `kunanyi`.
3. Send the generated `C-HI` package to Patrick/Stas for sanity checking.
4. Run early, restartable `C-HI` snapshots only after those gates are green.
