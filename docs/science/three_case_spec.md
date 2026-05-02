# Three-Case Science Run Specification

Spec version: `three-case-v0.1`
Frozen date: `2026-05-02`
Status: frozen for scaffolding; blocked from production until the real Stewart
cluster and group environment assets are identified and verified.

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
  compatibility.
- PLUTO restart/checkpoint files kept in scratch during long runs.
- Particle outputs only in the particle-enabled stage, with cadence no denser
  than the three analysis snapshots unless radio testing requires more.
- HDF5 plot output remains off by default until a specific analysis need is
  identified; parallel HDF5 itself is already smoke-tested on `kunanyi`.

## Environment Asset Gate

The real Stewart cluster and group environment files are required before any
science production run.

Do not treat the sample `spherical-r200-n3` external-test file as the science
environment unless Stas or Patrick explicitly confirm it. In the current local
and Nectar mirrors, that external sample is incomplete because the expected
`spherical-r200-n3.grid.out` file is not available.

Known local candidates as of `2026-05-02`:

| Asset | Location | Status |
| --- | --- | --- |
| Tabulated example | `/Users/bwbrook/git/utas-agn/jet-setup/resources/tabulated-environments/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv` | Present, not confirmed as the science Stewart cluster/group asset |
| Tabulated test copy | `/Users/bwbrook/git/utas-agn/jet-setup/test/environment/tabulated/PLUTO_data_best_fGas=0.010_Mh=4.00E+13_500m_ccc+gal_Mgal=1.00E+12galPot=true_pR=1.45E-17.csv` | Present, test fixture |
| External sample data | `/Users/bwbrook/git/utas-agn/jet-setup/test/environment/external/spherical-r200-n3.dbl` | Present, test fixture |
| External sample grid | `spherical-r200-n3.grid.out` | Missing locally; documented as missing in prior setup notes |

The tabulated environment format expected by `jet-setup` is six
space-separated cgs columns:

1. radius
2. density
3. pressure
4. temperature
5. gravitational acceleration
6. gravitational acceleration again

The current tabulated example has `1000` rows. Its first radius is
`2.429e+20 cm`; its final row reaches `2.429e+24 cm`. These numbers document
the candidate file only and are not yet a production environment lock.

If the real Stewart environments are external binary PLUTO fields instead of
tabulated radial profiles, the expected variables are, in order:

1. `rho`
2. `prs`
3. `gx`
4. `gy`
5. `gz`
6. `vx`
7. `vy`
8. `vz`

They must be in cgs units and paired with a matching `grid.out`.

## Nectar Environment Gates

Before a full science run, resize `nectar-vm` to `c3.3xlarge` and run
standalone no-jet stability checks for the chosen cluster and group
environments.

Pass criteria:

- The environment imports through the current `jet-setup` path without missing
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

The X-ray workflow must use GRAiLE or the predecessor project pipeline. If the
code or assets are missing, stop and request them from Stas/Patrick rather than
inventing a substitute.

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

- exact Stewart cluster environment filename and location
- exact Stewart group environment filename and location
- whether each environment is tabulated radial or external binary PLUTO data
- environment grid extents and production-domain size
- unit conventions for all supplied environment files
- science inlet radius and whether it should be tied to environment/domain
  scale
- one-sided vs bipolar convention for the headline injected-energy comparison
- GRAiLE/predecessor X-ray pipeline location and required assets
- production queue, walltime limit, and storage retention plan on `kunanyi`
