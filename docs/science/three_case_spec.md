# Three-Case Science Run Specification

Spec version: `three-case-v0.1`
Frozen date: `2026-05-02`
Updated: `2026-05-05`
Status: frozen for scaffolding and environment-gate preparation. The Stewart
tabulated environments are now identified; production remains blocked until the
Nectar stability gates and the first `C-HI` rehearsals are green.

## Purpose

This document freezes the first science-facing comparison suite for the
Honours X-ray cavity project. The suite is deliberately small: it is designed
to bring up the observable and truth-analysis pipeline quickly, then support a
minimal publishable comparison of jet power and environment.

The current execution model is:

- MacBook: control plane, documentation, static checks, config generation,
  light local inspection only.
- `nectar-vm`: resized rehearsal host, normally parked at `c3.xsmall`, resized
  to `c3.3xlarge` for serious rehearsal work.
- `kunanyi`: intermediate and full production jobs after the Nectar gates are
  green.

Patrick supplied the environment archive on `2026-05-05`; Stas confirmed that
science runs should use the radially averaged tabulated environments, not the
full 3D grid environments, because the full-grid profiles have too much
spurious motion for reliable energetics.

## Case Table

All three cases use the same launch geometry, solver defaults, snapshot
protocol, and observable/truth workflow unless Stas or Patrick override them.

| Case ID | Environment | Jet power | Jet speed | Role | Launch order |
| --- | --- | ---: | ---: | --- | ---: |
| `C-HI` | Stewart cluster | `1e45 erg/s` (`10^38 W`) | `0.1 c` | First validation case with clearer cavities | 1 |
| `C-LO` | Stewart cluster | `1e43 erg/s` (`10^36 W`) | `0.1 c` | Baseline science anchor | 2 |
| `G-LO` | Stewart group | `1e43 erg/s` (`10^36 W`) | `0.1 c` | Environment-dependence case | 3 |

The high-power cluster case is first because it should produce the most visible
lobes and cavities. The low-power cluster remains the baseline science anchor;
the low-power group then tests the environment dependence without changing jet
power.

## Shared Simulation Defaults

These defaults are locked for the first pass:

| Setting | Value |
| --- | --- |
| Launch point | centered on the environment centre |
| Physics | hydrodynamic (`HD`) |
| Geometry | 3D Cartesian for science runs |
| Density calculation | non-relativistic jet-density equation |
| `JET_RELATIVISTIC_DENSITY` | `NO` |
| `JET_OA_PRIMARY` | `15.0 deg` |
| `JET_OA_SECONDARY` | `15.0 deg` |
| `JET_START_TIME` | `0.0 Myr` |
| `JET_END_TIME` | `300.0 Myr` |
| `JET_ACTIVE_TIME` | `300.0 Myr` |
| Particle staging | particles off first, particles on second |
| Tracer threshold, default | `5e-3` |
| Tracer threshold, sensitivity | `1e-3`, `1e-2` |

The current `jet-setup` example uses `JET_INITIAL_RADIUS = 0.1`, while recent
smoke tests used `JET_INITIAL_RADIUS = 1.0`. That inlet radius is not yet
frozen for science. It must be confirmed with Stas/Patrick or derived from the
chosen Stewart grid before production.

## Output And Sampling Protocol

Analysis snapshots are fixed at:

- `100 Myr`
- `200 Myr`
- `300 Myr`

Viewing angles are fixed at:

- `0 deg`
- `45 deg`
- `90 deg`

Production output is hybrid sparse:

- `dbl` outputs at the three analysis snapshots for known `plutokore`
  compatibility until the analysis path is HDF5-native.
- `dbl.h5` is the preferred production output family for full simulations, per
  Patrick's guidance, once read/analysis compatibility has been smoke-tested.
- PLUTO restart/checkpoint files kept in scratch during long runs.
- Particle outputs only in the particle-enabled stage, with cadence no denser
  than the three analysis snapshots unless radio testing requires more.
- parallel HDF5 itself is already smoke-tested on `kunanyi`.

Important unit convention: `JET_END_TIME` and `JET_ACTIVE_TIME` are set in Myr,
but PLUTO `tstop`, `dbl`, `dbl.h5`, and checkpoint intervals are in PLUTO code
time. The archived CosmoDRAGoN INIs use:

```text
1 Myr = 306.601393788 PLUTO code-time units
```

Therefore the frozen `300 Myr` science duration corresponds to:

```text
tstop = 91980.41813640
100 Myr snapshot cadence = 30660.13937880
25 Myr checkpoint cadence = 7665.03484470
```

## Environment Asset Gate

The real Stewart cluster and group environment files are now present locally
under the ignored `env/` asset drop.

Use the radially averaged tabulated files for science runs:

| Environment | File | Rows | Radius range | Status |
| --- | --- | ---: | --- | --- |
| Stewart cluster `002_003` | `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv` | `4000` | `0` to `1.697123e24 cm` | selected for `C-HI` and `C-LO` |
| Stewart group `002_031` | `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv` | `4000` | `0` to `1.697123e24 cm` | selected for `G-LO` |

The original full environments are also in `env/environments.zip`, but they
are not the production science inputs after Stas' clarification. They can be
kept as reference assets only.

The tabulated environment format expected by `jet-setup` is six
space-separated cgs columns:

1. radius
2. density
3. pressure
4. temperature
5. gravitational acceleration
6. gravitational acceleration again

The old full 3D environment format, not selected for science energetics, is a
`.dbl` plus matching `grid.out` pair containing:

1. `rho`
2. `prs`
3. `gx`
4. `gy`
5. `gz`
6. `vx`
7. `vy`
8. `vz`

These full 3D files must not be substituted back into the science run without a
supervisor override.

## Nectar Environment Gates

Before a full science run, resize `nectar-vm` to `c3.3xlarge` and run
standalone no-jet stability checks for the chosen cluster and group
environments.

Pass criteria:

- The tabulated environment imports through the current `jet-setup` path without missing
  files or unit errors.
- A no-jet run remains hydrostatically stable over the chosen rehearsal window.
- `grid.out`, `dbl.out`, and final `data.*.dbl` products are present and load
  through the current Python analysis environment.
- Density and pressure stability plots are produced and stored with the
  rehearsal report.

No environment gate should be run on the parked `c3.xsmall` instance.

## `C-HI` Rehearsal Sequence

The first rehearsal sequence is:

1. Build `C-HI` with particles off.
2. Run a modest 3D Cartesian grid on resized Nectar.
3. Confirm stable completion to `300 Myr`.
4. Produce quick-look density, pressure, tracer, and log diagnostics.
5. Repeat the same case with particles enabled.
6. Confirm particle files load and one radio smoke product can be produced.

The rehearsal grid must be derived from the verified Stewart environment
extent. A micro grid can be generated for syntax/dry-run tests, but it is not a
science rehearsal by itself.

## Truth Definitions

Level 1 truth is injected jet energy.

- `JET_PWR` in `jet-setup` is treated as one-sided unless supervisor guidance
  says otherwise.
- One-sided injected energy is `JET_PWR * active_time`.
- Bipolar injected energy is `2 * JET_PWR * active_time`.
- Both conventions must be recorded in any comparison table until the
  supervisor-preferred convention is frozen.

Level 2 truth is tracer-defined lobe material and its energy.

- Default lobe mask: tracer > `5e-3`.
- Sensitivity masks: tracer > `1e-3` and tracer > `1e-2`.
- Report volume, thermal energy, kinetic energy, and total lobe energy where
  `plutokore` supports the calculation reliably.
- Initial energy comparisons should use the same snapshot and viewing angle as
  the first X-ray/radio smoke products.

Gas-coupled or shock-deposited energy remains a later truth level until Level 1
and Level 2 are green.

## Observable Protocol

The first aligned observable/truth comparison is for `C-HI` at one declared
snapshot/view. The default target is:

- snapshot: `100 Myr`
- view: `45 deg`

Required first products:

- one X-ray map from GRAiLE or the predecessor-project pipeline
- one ellipsoidal cavity boundary
- local ambient pressure near the cavity
- `pV` and `4pV`
- sound, buoyancy, and refill age estimates
- one radio lobe boundary
- one radio luminosity smoke product
- Level 1 and Level 2 truth values for the same snapshot

The X-ray workflow must use GRAiLE or the predecessor project pipeline.
Patrick supplied the current GRAiLE/XRAiSE bundle as `env/graile-all.zip`; it
has been extracted under `env/extracted/graile/` for inspection. The next X-ray
gate is to port those scripts from Georgia's absolute paths into a repo-local
or Nectar/kunanyi-friendly workflow.

## `kunanyi` Production Template Requirements

Production jobs should use the validated full-node pattern:

```pbs
#PBS -l select=N:ncpus=28:mpiprocs=28
#PBS -M barry.brook@utas.edu.au
#PBS -m ae
```

The run script must derive rank count from `PBS_NODEFILE`:

```bash
NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini -e environment.ini
```

Required production-safety features:

- `DONE` and `FAILED` markers.
- Fresh-start vs restart detection.
- Restart/checkpoint cadence recorded in the generated `pluto.ini`.
- PLUTO and `jet-setup` source revision logging.
- Case manifest logging.
- PBS nodefile logging.
- Output-volume estimate before submission.
- Email notifications to `barry.brook@utas.edu.au`.

One intermediate `C-HI` `kunanyi` rehearsal must pass before any 48-hour
multi-node job is submitted.

## Acceptance Gate For The Three-Case Suite

Move from single-case validation to the full three-case suite only after
`C-HI` has:

- a stable particle-enabled run to `300 Myr`
- a confirmed restart path
- `DONE` marker behavior
- artifact retrieval
- at least one aligned X-ray/radio/truth comparison at a declared snapshot and
  view

After that, production launch order is:

1. `C-HI`
2. `C-LO`
3. `G-LO`

## Unresolved Supervisor Confirmations

The following items remain open and should be resolved before production:

- whether Stas/Patrick want any smoothing or trimming of the confirmed
  tabulated Stewart profiles before production
- environment grid extents and production-domain size
- science inlet radius and whether it should be tied to environment/domain
  scale
- one-sided vs bipolar convention for the headline injected-energy comparison
- repo-local GRAiLE/XRAiSE porting details and dependency environment
- production queue, walltime limit, and storage retention plan on `kunanyi`
