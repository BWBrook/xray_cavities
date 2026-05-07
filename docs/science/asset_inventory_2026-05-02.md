# Science Asset Inventory

Created: `2026-05-02`
Updated: `2026-05-05`

This inventory records what is currently visible from the MacBook control
plane and the local `env/` asset drop. It supports the three-case spec in
`docs/science/three_case_spec.md`.

## UTAS AGN Source Mirrors

Local MacBook source mirrors:

- `/Users/bwbrook/git/utas-agn/pluto`
- `/Users/bwbrook/git/utas-agn/jet-setup`
- `/Users/bwbrook/git/utas-agn/plutokore`
- `/Users/bwbrook/git/utas-agn/jet-setup.wiki`

Nectar has corresponding mirrors under `/home/ubuntu/git/utas-agn`.

## 2026-05-05 Stewart Environment Assets

Patrick supplied `env/environments.zip`, and Stas clarified that science runs
must use the radially averaged tabulated environments rather than the full 3D
cubes.

Files extracted from the archive:

| Environment | Extracted file | Rows | Radius range | Notes |
| --- | --- | ---: | --- | --- |
| cluster `002_003` | `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv` | `4000` | `0` to `1.697123e24 cm` | selected for `C-HI` and `C-LO` |
| group `002_031` | `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv` | `4000` | `0` to `1.697123e24 cm` | selected for `G-LO` |

Column ranges from `scripts/science/inspect_tabulated_environment.py`:

| Environment | Density range (`g cm^-3`) | Pressure range (`dyn cm^-2`) | Temperature range (`K`) | Gravity range (`cm s^-2`) |
| --- | ---: | ---: | ---: | ---: |
| cluster `002_003` | `5.847058e-28` to `1.537677e-26` | `1.429542e-12` to `5.257199e-11` | `1.775021e7` to `2.482180e7` | `-1.476103e-08` to `-3.527603e-11` |
| group `002_031` | `8.717397e-29` to `4.151229e-27` | `4.313558e-14` to `6.012708e-12` | `3.592466e6` to `1.051568e7` | `-9.481650e-09` to `-3.471923e-11` |

The archive also contains full-grid environment assets and example
`environment.ini` files:

- `full/env.h003_bv.ini`
- `full/env.h031_bv.ini`
- full `.dbl`/`grid.out` assets, including an 8 GB `h031` cube

Those full 3D environments are reference assets only for this project stage.
They are not the selected science inputs after Stas' clarification.

## 2026-05-05 Simulation INIs

Patrick supplied `env/inis.zip`, extracted under `env/extracted/inis/`.

Useful implementation facts from the old INIs:

- PLUTO `tstop` and output intervals use code time, not Myr.
- The conversion implied by the archived runs is
  `1 Myr = 306.601393788` PLUTO code-time units.
- The 2026-05-06 supervisor meeting clarified that user-defined jet duty-cycle
  parameters such as `JET_END_TIME` and `JET_ACTIVE_TIME` remain physical Myr
  values even though PLUTO core time controls are code time.
- The common CosmoDRAGoN production grid family used stretched Cartesian
  domains with dense central coverage and larger outer cells.
- Old particle-enabled runs commonly used `Nparticles -1 16.0` and
  `particles_dbl 3.06601394 -1`, equivalent to `0.01 Myr` particle cadence.
- Full production should prefer HDF5 outputs, but sparse `dbl` outputs remain
  useful until every analysis step is HDF5-native.

## 2026-05-05 GRAiLE/XRAiSE Assets

Patrick supplied `env/graile-all.zip`, extracted under
`env/extracted/graile/graile-all/`.

Relevant files:

- `xraise.txt`: Python source for the XRAiSE loss/emissivity helper.
- `do_XRAiSE-inputlist.txt`: script for producing X-ray images.
- `emission_params(1).yml`: radio/X-ray observing and emission parameter
  presets.
- `sim_directories(1).yml`: old absolute path map for CosmoDRAGoN products.
- `EXAMPLE_XRAY.ipynb`: worked X-ray HDF5 inspection/plotting notebook.
- `Q38-v98-a25-C180-xray.hdf5`: small example X-ray output.
- `gaunt_lut_2d.npz` and `apec_corrections(1).txt`: correction tables used
  by the X-ray path.
- `Some_Xray_notes.docx`: Georgia's short notes on the XRAiSE/GRAiLE path.

The bundle is now present, so the blocker has shifted from "missing X-ray
assets" to "port Georgia's absolute-path script bundle into this repo's
control-plane and remote-execution workflow."

## 2026-05-05 Nectar Environment Gate

The selected tabulated Stewart environments were staged to resized
`nectar-vm` and run through no-jet 3D Cartesian stability gates to `300 Myr`.

| Environment | Gate file | Max central density drift | Max central pressure drift | Max Mach | Result |
| --- | --- | ---: | ---: | ---: | --- |
| cluster `002_003` | `tabulated_cosmo_002003.csv` | `0.136%` | `0.226%` | `0.0242` | pass |
| group `002_031` | `tabulated_cosmo_002031.csv` | `0.284%` | `0.473%` | `0.0330` | pass |

Detailed report and plots:

- `docs/science/stewart_environment_gate_2026-05-05.md`
- `docs/science/assets/stewart_environment_gate_2026-05-05/`

## 2026-05-02 Environment Files Found

The only environment-like files found in the current UTAS AGN mirrors are
examples or test fixtures, not confirmed science assets.

| File | Host | Interpretation |
| --- | --- | --- |
| `/Users/bwbrook/git/utas-agn/jet-setup/resources/tabulated-environments/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv` | MacBook | Present tabulated candidate; not confirmed as a Stewart science cluster or group profile |
| `/Users/bwbrook/git/utas-agn/jet-setup/test/environment/tabulated/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv` | MacBook | Test fixture copy |
| `/Users/bwbrook/git/utas-agn/jet-setup/test/environment/external/spherical-r200-n3.dbl` | MacBook | External test data fixture |
| `/home/ubuntu/git/utas-agn/jet-setup/resources/tabulated-environments/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv` | Nectar | Same tabulated candidate visible on Nectar |

Known missing file:

- `spherical-r200-n3.grid.out`

Prior setup notes already record that the external `spherical-r200-n3` test
case references this missing grid file. It must not be treated as a complete
science environment.

## Tabulated Candidate Metadata

For the tabulated candidate:

- rows: `1000`
- first radius: `2.429e+20 cm`
- final radius: `2.429e+24 cm`
- columns: radius, density, pressure, temperature, gravitational acceleration,
  gravitational acceleration again
- units: cgs, according to `jet-setup.wiki/setup/environments.md`

This file remains a candidate/test asset only. It has been superseded by the
`2026-05-05` Stewart files above.

The helper `scripts/science/inspect_tabulated_environment.py` can be used to
record the same metadata for any confirmed Stewart tabulated environment before
the Nectar stability gate, for example:

```bash
python3 scripts/science/inspect_tabulated_environment.py \
  /path/to/confirmed_stewart_cluster.csv \
  --label Stewart-cluster
```

## GRAiLE And X-ray Assets

The GRAiLE/XRAiSE bundle is now present under the ignored `env/` drop, but it
is not yet repo-native. The next X-ray task is to port Georgia's script bundle
away from absolute historical paths and into this repo's control-plane plus
remote-execution layout.

## Rehearsal Implication

The next compute action should not be a long production submission. The first
two science gates are now complete: the real Stewart tabulated assets were
identified, and the no-jet Nectar environment gates passed. The next action is:

1. generate and validate the particles-enabled `C-HI` symmetric run package
2. run a production-like `kunanyi` no-jet environment/MPI/HDF5 gate
3. ask Patrick/Stas to inspect the generated `C-HI` package before a long run
4. run early `C-HI` snapshots and diagnostics at about `1 Myr` cadence
5. port the first GRAiLE/XRAiSE X-ray map path once a usable snapshot exists
