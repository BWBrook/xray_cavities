# Science Asset Inventory: 2026-05-02

This inventory records what is currently visible from the MacBook control
plane and a light Nectar probe. It supports the three-case spec in
`docs/science/three_case_spec.md`.

## UTAS AGN Source Mirrors

Local MacBook source mirrors:

- `/Users/bwbrook/git/utas-agn/pluto`
- `/Users/bwbrook/git/utas-agn/jet-setup`
- `/Users/bwbrook/git/utas-agn/plutokore`
- `/Users/bwbrook/git/utas-agn/jet-setup.wiki`

Nectar has corresponding mirrors under `/home/ubuntu/git/utas-agn`.

## Environment Files Found

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

This file remains a candidate/test asset only. Production must wait for
confirmation of the real Stewart cluster and group assets.

The helper `scripts/science/inspect_tabulated_environment.py` can be used to
record the same metadata for any confirmed Stewart tabulated environment before
the Nectar stability gate, for example:

```bash
python3 scripts/science/inspect_tabulated_environment.py \
  /path/to/confirmed_stewart_cluster.csv \
  --label Stewart-cluster
```

## GRAiLE And X-ray Assets

The project documents reference GRAiLE and Alain's predecessor X-ray cavity
pipeline, but the current local UTAS AGN mirrors do not expose a complete
runnable X-ray pipeline. The radio-facing `plutokore` path is visible, but the
X-ray map path is still an asset gate.

Required next input from Stas/Patrick:

- GRAiLE repository or predecessor pipeline location
- any environment, emissivity, response, or configuration files needed to
  reproduce the synthetic X-ray maps
- preferred first snapshot/view for the `C-HI` smoke comparison if not
  `100 Myr` and `45 deg`

## Rehearsal Implication

The next compute action should not be a production submission. It should be:

1. obtain the real Stewart cluster and group environment assets
2. resize `nectar-vm` to `c3.3xlarge`
3. run no-jet environment stability gates
4. run the `C-HI` no-particle rehearsal
5. repeat `C-HI` with particles
