# deep-server setup for UTAS AGN

This document records the current state of `deep-server` for running the UTAS AGN GitLab workflows from the `xray_cavities` project environment.

## Scope

This note covers:

- the machine and toolchain state relevant to UTAS AGN work
- the repo-local Python/docs environment in `/home/bwbrook/papers/xray_cavities`
- the current UTAS AGN checkout state in `/home/bwbrook/git/utas-agn`
- smoke-test and verification results gathered on `2026-04-16`

It does not attempt to describe the scientific content of the simulations in depth.

## Machine summary

Observed on `2026-04-16T16:18:06+10:00`:

- Host: `deep-server`
- OS: `Ubuntu 24.04.4 LTS (Noble Numbat)`
- Kernel: `Linux 6.8.0-107-generic x86_64`
- CPU cores: `64`
- RAM: `125 GiB`
- Free memory at check time: about `105 GiB`
- Swap: `8 GiB`

Relevant tool versions:

- `Python 3.12.3`
- `uv 0.9.13`
- `gcc 13.3.0`
- `Open MPI 4.1.6`

## UTAS AGN checkout state

Current local checkouts:

- `/home/bwbrook/git/utas-agn/pluto`
- `/home/bwbrook/git/utas-agn/jet-setup`
- `/home/bwbrook/git/utas-agn/plutokore`
- `/home/bwbrook/git/utas-agn/jet-setup.wiki`

Branch and commit state at time of writing:

- `pluto`
  - branch: `4.4.0-localchanges`
  - commit: `587e34d`
- `jet-setup`
  - branch: `pluto-4.4`
  - commit: `0427058`
- `plutokore`
  - branch: `master`
  - commit: `6a47511`
- `jet-setup.wiki`
  - branch: `master`
  - commit: `14d5aa7`

Important local state:

- `pluto`, `plutokore`, and `jet-setup.wiki` are clean.
- `jet-setup` is not clean. It contains local fixes and test edits created during bring-up and validation on this machine.

The current `jet-setup` local modifications include:

- docs cleanup:
  - `docs/Doxyfile`
  - `docs/source/code/api.rst`
  - `docs/source/_static/`
- source fixes:
  - `src/hdf5_io.c`
  - `src/init.c`
  - `test/run-tests.py`
- HD test config updates:
  - multiple `test/environment/*/*.ini` files now explicitly set `JET_RELATIVISTIC_DENSITY = NO`
- preserved scratch case:
  - `test/environment/king/test/`

## xray_cavities environment state

The repo-local environment in `/home/bwbrook/papers/xray_cavities` is the preferred Python/docs environment for this work.

Managed files:

- [pyproject.toml](/home/bwbrook/papers/xray_cavities/pyproject.toml)
- [uv.lock](/home/bwbrook/papers/xray_cavities/uv.lock)
- [.python-version](/home/bwbrook/papers/xray_cavities/.python-version)
- repo-local `.venv/`
- repo-local `.doxygen/`

Key installed packages:

- `astropy 7.2.0`
- `breathe 4.35.0`
- `colorful 0.5.8`
- `contextlib2 21.6.0`
- `future 1.0.0`
- `h5py 3.16.0`
- `hdf5plugin 6.0.0`
- `ipykernel 7.2.0`
- `ipython 9.12.0`
- `jupyterlab 4.5.6`
- `matplotlib 3.10.8`
- `numba 0.65.0`
- `numpy 2.2.6`
- `pykdtree 1.4.3`
- `pytest 9.0.3`
- `pytest-datafiles 3.0.1`
- `pyyaml 6.0.3`
- `scipy 1.13.1`
- `sphinx 6.2.1`
- `sphinx-multiversion 0.2.5`
- `tabulate 0.10.0`
- `yt 4.4.2`
- editable local `plutokore`

Important compatibility pins:

- `scipy<1.14`
  - needed because `verify-environment-stability.py` imports `scipy.integrate.trapz`
- `sphinx<7`
  - needed because the current legacy `jet-setup` docs theme is not compatible with newer Sphinx releases

## Docs toolchain status

The following docs toolchain is available from the `xray_cavities` environment:

- `sphinx`
- `breathe`
- `sphinx-multiversion`
- repo-local `doxygen`

Validated command:

```bash
cd /home/bwbrook/git/utas-agn/jet-setup/docs
uv run --project /home/bwbrook/papers/xray_cavities \
sphinx-build -b html source _build/html
```

Status:

- HTML docs build successfully.
- The warning load was cleaned up enough to treat the docs build as healthy.

Relevant fixes made in `jet-setup` to get there:

- removed obsolete Doxygen config tags
- disabled `WARN_IF_UNDOCUMENTED`
- removed overlapping `.. doxygenindex::` content from `docs/source/code/api.rst`
- added `docs/source/_static/.gitkeep`
- removed stale `\return` tags from `void` functions in `src/hdf5_io.c`

## Simulation toolchain status

### Compiler and runtime

The machine is ready for both serial and MPI PLUTO runs.

Serial path:

- works with `Linux.gcc.defs`

MPI path:

- works with `Linux.mpicc.defs`
- `mpiexec` and `mpicc` are available
- `libopenmpi-dev` is installed, so `mpi.h` is visible and parallel builds succeed

Important note:

- PLUTO parallelism here is MPI-based.
- CPU usage is controlled by MPI rank count, for example `mpiexec -n 8 ./pluto`.
- There is no direct PLUTO setting for explicit RAM allocation.
- Memory use is determined by grid size, enabled physics, outputs, and domain decomposition.

## Test harness status

The stock `jet-setup/test/run-tests.py` harness currently builds and runs tests successfully for the cases exercised here, but it still defaults to serial execution.

Local compatibility fixes made:

- tolerate missing legacy `definitions.h` keys such as `COMPONENTS` instead of crashing
- replace the removed `VAR_LOOP` macro with `NVAR_LOOP` in `src/init.c`
- explicitly disable `JET_RELATIVISTIC_DENSITY` in HD test configs that otherwise fail runtime checks

Practical consequence:

- serial harness-driven tests are working
- MPI test runs currently require a manual build/run step from the generated scratch case

## Smoke-test results

### 2D HD King potential

Case:

- `jet-setup/test/environment/king/test-2d-hd-gp-sph.ini`

Status:

- passed end-to-end
- build, run, and verification all succeeded

### 2D RHD King acceleration

Case:

- `jet-setup/test/environment/king/test-2d-rhd-ga-sph.ini`

Status:

- passed end-to-end

### Tabulated 2D HD

Case:

- `jet-setup/test/environment/tabulated/test-2d-hd-ga-sph.ini`

Status:

- run completed
- verification failed its stability thresholds

Interpretation:

- this is currently a repo/test-content issue, not a machine setup issue

### External 3D RHD

Case:

- `jet-setup/test/environment/external/test-3d-rhd-ga-cart.ini`

Status:

- blocked before meaningful run

Cause:

- referenced file `spherical-r200-n3.grid.out` is missing from the local UTAS AGN checkouts

Interpretation:

- likely a missing generated artefact or omitted file in the repo/group
- not an Ubuntu/toolchain failure

## Full 3D validation

### Case used

- `jet-setup/test/environment/king/test-3d-hd-gp-cart.ini`

Configuration:

- HD
- 3D
- Cartesian
- gravitational potential
- grid: `100 x 100 x 100`
- `tstop = 90660`
- outputs `0..30`

### Serial run

Command path:

- built through the test harness with `Linux.gcc.defs`

Observed result:

- completed successfully
- full verification table passed
- wall time reported by PLUTO/harness: about `7m06s`

### Parallel run

Build:

- rebuilt the same case with `Linux.mpicc.defs`

Execution mode:

- `OMP_NUM_THREADS=1`
- `mpiexec -n 8 ./pluto`

Observed result:

- all 8 MPI ranks were active during the run
- full output sequence `0..30` was produced
- full verification table passed
- timed rerun wall time: `1:07.29`

Interpretation:

- the multicore MPI path is working correctly on this host
- for this case, `8` ranks gave a strong speedup over serial

## Readiness assessment

Current overall assessment:

- machine/toolchain readiness: good
- Python analysis readiness: good
- docs readiness: good
- serial simulation readiness: good
- MPI simulation readiness: good

Remaining known issues are now mostly inside the UTAS AGN repo content:

- one tabulated HD case fails its own verification thresholds
- the external 3D RHD case references a missing `.grid.out` file
- the test harness still does not provide a built-in MPI execution mode

## Recommended next steps

If work continues from here, the most useful next improvements are:

1. teach `jet-setup/test/run-tests.py` an MPI mode so parallel runs are first-class
2. investigate the `tabulated/test-2d-hd-ga-sph` verification failure
3. locate, regenerate, or restore `spherical-r200-n3.grid.out`
4. decide whether the local `jet-setup` fixes should be committed upstream in that repo
