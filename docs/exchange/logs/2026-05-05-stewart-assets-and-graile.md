# 2026-05-05 Stewart Assets And GRAiLE Bundle

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

The config renderer has been updated so `300 Myr` now renders as:

```text
tstop = 91980.41813640
dbl/dbl.h5 snapshot interval = 30660.13937880
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

1. Ensure `nectar-vm` is resized to `c3.3xlarge`.
2. Sync `xray_cavities`, the two tabulated files, and the generated gate tests
   to Nectar.
3. Run the cluster and group no-jet stability gates using the existing
   `jet-setup/test/run-tests.py` pattern.
4. If both environments pass, generate the `C-HI` hydro case from the same
   tabulated cluster file.
