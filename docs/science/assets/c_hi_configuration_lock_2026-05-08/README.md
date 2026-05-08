# C-HI Configuration Lock Assets - 2026-05-08

This directory contains the tracked, lightweight artifacts generated after
Patrick and Stas reviewed the first `C-HI` configuration packet.

## Contents

- `config/`: rendered `C-HI` particles-enabled package for Stewart cluster
  `002_003`

The large Stewart/GRAiLE source archives remain untracked under `env/`. The
no-jet `kunanyi` gate inputs are generated into ignored `build/` space and
included in the transfer tarball rather than tracked in git.

## Render Commands

```bash
python3 scripts/science/render_three_case_configs.py \
  --force \
  --case C-HI \
  --variant particles \
  --grid stewart_stretched_250 \
  --duration-myr 50 \
  --snapshot-interval-myr 1 \
  --dbl-h5-interval-myr 5 \
  --particle-interval-myr 0.01 \
  --particles-per-injection 16 \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --check-local-assets \
  --output build/science/c_hi_configuration_lock_2026-05-08
```

```bash
python3 scripts/science/render_stewart_environment_gate_tests.py \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --group-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002031.csv \
  --output build/science/stewart_environment_gate_tests_kunanyi_2026-05-08 \
  --duration-myr 50 \
  --x-half-width-kpc 200 \
  --y-half-width-kpc 200 \
  --z-half-width-kpc 250 \
  --cells-per-kpc 1 \
  --output-interval-myr 10 \
  --hdf5-interval-myr 10 \
  --force
```

The generated gate directory is intentionally not tracked. The current
transfer bundle is:

```text
build/science/kunanyi_stage_2026-05-08/c_hi_and_environment_gate_2026-05-08.tar.gz
```

That ignored tarball contains a self-contained staged `C-HI` case directory
under `xray_cavities_cases/C-HI/particles/`, with the cluster tabulated
environment copied beside `environment.ini` and `TabulatedData` rewritten to
`./tabulated_cosmo_002003.csv` for remote execution.

## Static Validation

`config/render_validation.json` reports `ok = true` and checks the supervisor-
set values, including:

- `X3 = +/-250 kpc` via the `stewart_stretched_250` grid preset
- `Checkpoint_interval = -1.0`
- `dbl.h5 = 1533.00696894` code-time units (`5 Myr`)
- `flt.h5 = 306.60139379` code-time units (`1 Myr`)
- `particles_dbl = 3.06601394` code-time units (`0.01 Myr`)
- `Nparticles -1 16.0`
- `PART_INJECT_FREQUENCY = 0.01`
- `JET_CHI = 1.0`
- `JET_INITIAL_RADIUS = 0.1`
- `JET_INJECTION_HEIGHT = 0.75`
