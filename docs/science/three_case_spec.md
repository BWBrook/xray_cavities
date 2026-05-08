# Three-Case Science Run Specification

Spec version: `three-case-v0.3`
Frozen date: `2026-05-02`
Updated: `2026-05-08`
Status: frozen for the first production-like `C-HI` preparation after Patrick
and Stas' configuration review. This version supersedes the earlier
hydro-first, 300 Myr-first scaffold and the 2026-05-07 pre-review C-HI packet.

## Purpose

This document records the first science-facing comparison suite for the Honours
X-ray cavity project. The suite remains deliberately small: it is designed to
bring up the observable and truth-analysis pipeline quickly, then support a
minimal comparison of jet power and environment.

The current execution model is:

- MacBook: control plane, documentation, config generation, static checks, and
  light local inspection.
- `nectar-vm`: resizeable rehearsal host, normally parked at `c3.xsmall` and
  resized to `c3.3xlarge` only when useful.
- `kunanyi`: production-like validation and full 3D production jobs.

Patrick supplied the environment archive on `2026-05-05`; Stas confirmed that
science runs should use the radially averaged tabulated environments, not the
full 3D grid environments, because the full-grid profiles have too much
spurious motion for reliable energetics.

The 2026-05-06 supervisor meeting made the next gate more specific:

- use a centered, symmetric high-power cluster control first
- enable particles from the first nominal science run
- target about `50 Myr` initially, not `300 Myr`
- treat `JET_END_TIME` and `JET_ACTIVE_TIME` as Myr physical parameters

Patrick and Stas' 2026-05-08 review then locked the first-pass injection,
particle, restart, and grid corrections:

- extend the jet-axis grid to `X3 = +/-250 kpc`
- preserve the old resolution at about `200 kpc` when extending X3
- set `JET_INITIAL_RADIUS = 0.1 kpc`
- set `JET_INJECTION_HEIGHT = 0.75 kpc`
- set `JET_CHI = 1.0` for a pressure-matched non-relativistic jet
- output particles every `0.01 Myr` and inject at least `16` particles at that
  cadence
- use static-grid `dbl.h5` files every `5 Myr` for restart support
- leave Chombo `Checkpoint_interval` disabled
- run PLUTO with `-maxtime`, e.g. `47.5` hours for a `48` hour PBS job

## Case Table

All three cases use the same launch geometry, solver defaults, and
observable/truth workflow unless Stas or Patrick override them.

| Case ID | Environment | Jet power | Jet speed | Role | Launch order |
| --- | --- | ---: | ---: | --- | ---: |
| `C-HI` | Stewart cluster `002_003` | `1e45 erg/s` (`10^38 W`) | `0.1 c` | first high-visibility validation/control case | 1 |
| `C-LO` | Stewart cluster `002_003` | `1e43 erg/s` (`10^36 W`) | `0.1 c` | baseline science anchor | 2 |
| `G-LO` | Stewart group `002_031` | `1e43 erg/s` (`10^36 W`) | `0.1 c` | environment-dependence case | 3 |

The high-power cluster case is first because it should produce the most visible
lobes and cavities. The low-power cluster remains the baseline science anchor;
the low-power group tests environment dependence without changing jet power.

## Shared Simulation Defaults

These defaults are locked for the first production-like package:

| Setting | Value |
| --- | --- |
| Launch point | centered on the tabulated environment centre |
| Physics | hydrodynamic (`HD`) |
| Geometry | 3D Cartesian |
| Jet model | two-sided internal boundary condition |
| Density calculation | non-relativistic jet-density equation |
| `JET_RELATIVISTIC_DENSITY` | `NO` |
| `JET_PWR` convention | one-sided jet power, applied to both jets |
| `JET_OA_PRIMARY` | `15.0 deg` |
| `JET_OA_SECONDARY` | `15.0 deg` |
| `JET_INITIAL_RADIUS` | `0.1 kpc` |
| `JET_INJECTION_HEIGHT` | `0.75 kpc` |
| `JET_CHI` | `1.0` |
| physical jet start | `0.0 Myr` |
| first target physical jet end | `50.0 Myr` |
| first target physical active time | `50.0 Myr` |
| particles | enabled for nominal `C-HI`; disabled only for no-jet gates or narrow debugging |
| particle output cadence | `0.01 Myr` (`3.06601394` PLUTO code-time units for `particles_dbl`) |
| particle injection cadence | `0.01 Myr` via `PART_INJECT_FREQUENCY` |
| particles per injection | `16.0` initially, with `32` or `64` available if supervisors request denser sampling |
| Tracer threshold, default | `5e-3` |
| Tracer threshold, sensitivity | `1e-3`, `1e-2` |

## Unit Convention

The meeting clarified a critical unit split:

| Parameter family | Units |
| --- | --- |
| PLUTO core controls such as `tstop` | PLUTO code time |
| static-grid output intervals such as `dbl`, `flt`, `dbl.h5`, `flt.h5` | PLUTO code time |
| Chombo `Checkpoint_interval` and `Plot_interval` | disabled for static-grid PLUTO |
| `JET_END_TIME`, `JET_ACTIVE_TIME`, `JET_START_TIME` | Myr |
| `PART_INJECT_FREQUENCY` | Myr |
| jet injection dimensions and environment offsets | kpc |
| density inputs | `g cm^-3` |
| `JET_PWR` | one-sided `erg/s` |

The archived Stewart/CosmoDRAGoN INIs remain useful for converting PLUTO core
times:

```text
1 Myr = 306.601393788 PLUTO code-time units
```

Therefore the first `50 Myr` target should render as:

```text
tstop = 15330.06968940
JET_END_TIME = 50.0
JET_ACTIVE_TIME = 50.0
1 Myr flt.h5 cadence = 306.60139379
5 Myr dbl.h5 restart-output cadence = 1533.00696894
0.01 Myr particles_dbl cadence = 3.06601394
Checkpoint_interval = -1.0
```

No current source-of-truth document should describe `JET_END_TIME` or
`JET_ACTIVE_TIME` as code-time values.

## Output And Sampling Protocol

The immediate `C-HI` diagnostic cadence is:

- early science snapshots about every `1 Myr`
- first diagnostic decision after the first `3-5` snapshots
- target run length for the first production-like pass: about `50 Myr`

The first quick-look products are:

- mid-plane density, pressure, and tracer maps
- jet-axis profiles of density, pressure, tracer, and `v_z`

Viewing angles are post-processing choices, not simulation variants:

- `0 deg`: jet in the plane of the sky; default first view
- `45 deg`: intermediate inclination
- `90 deg`: jet directed along the line of sight

The older `100`, `200`, `300 Myr` analysis grid is no longer a first-run
requirement. Longer-duration science sampling should be refrozen after the
first production-like `C-HI` run establishes runtime, stability, and output
volume.

Production output should be sparse and auditable:

- `flt.h5` science snapshots every `1 Myr`
- `dbl.h5` restart-capable outputs every `5 Myr`
- particle outputs every `0.01 Myr` as high-time-resolution tracer proxies
- PLUTO `-maxtime` set below the PBS walltime so the code writes a final
  `*.{flt,dbl}.h5` output before scheduler termination
- full output catalogue mapping output number to physical time and file role
- cluster-side analysis by PBS job or interactive compute session

Parallel HDF5 itself has already been smoke-tested on `kunanyi`; the next gate
is confirming HDF5 output inside the production-like PLUTO/jet-setup workflow.

## Environment Asset Gate

The real Stewart cluster and group environment files are present locally under
the ignored `env/` asset drop.

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

## Environment Validation Gates

Status on `2026-05-05`: both selected tabulated environments passed smoke-scale
no-jet gates on resized `nectar-vm`. The detailed report is
`docs/science/stewart_environment_gate_2026-05-05.md`.

Those gates remain useful smoke evidence, but the meeting requested a
production-relevant repeat on `kunanyi`:

- at least `1 cell/kpc`, preferably `2 cells/kpc` where feasible
- no jet
- MPI through PBS
- HDF5 output enabled
- available `kunanyi` modules first; do not compile a private MPI/HDF5 stack
  unless the module path fails

Pass criteria:

- the tabulated environment imports through the current `jet-setup` path
- PLUTO/jet-setup compiles on a `kunanyi` compute node
- MPI launch uses rank count from `PBS_NODEFILE`
- HDF5 output is written and readable
- no obvious hydrostatic drift or timestep collapse
- `grid.out`, output metadata, and data products load through the analysis
  environment

No environment gate should be run on the parked `c3.xsmall` Nectar instance.

## `C-HI` First-Run Sequence

The first nominal science sequence is:

1. Generate a concise `C_high_symmetric` run definition.
2. Render `pluto.ini`, `environment.ini`, `definitions_overrides.json`, and
   `case_manifest.json`.
3. Validate rendered values against the run definition.
4. Confirm the rendered package contains Patrick/Stas' 2026-05-08 corrections.
5. Run a production-like, particles-enabled `C-HI` control on `kunanyi`.
6. Inspect the first `3-5` snapshots at about `1 Myr` cadence.
7. Continue toward about `50 Myr` only if early morphology, outputs, and
   restart behaviour are healthy.

Hydro-only `C-HI` remains allowed as a narrow debugging fallback, not as the
nominal science gate.

The rehearsal grid is derived from the verified Stewart environment, the old
0.1c/0.3c CosmoDRAGoN-style INIs, and Stas' 2026-05-08 X3 resolution
constraint:

- `X1/X2`: keep the old `-200` to `+200 kpc` stretched grid:
  `330 s, 100 s, 100 u, 100 s, 330 s`
- `X3`: extend to `-250` to `+250 kpc`
- `X3` outer stretched patches: use `357` cells on each side, not `330`
- rationale: the PLUTO stretched-grid recurrence gives `dx ~ 1.6923 kpc` at
  `200 kpc` in the old `10-200 kpc` outer patch, and `357` cells in the
  `10-250 kpc` patch gives `dx ~ 1.6930 kpc` in the cell spanning `200 kpc`
- stretched grid preserving central/injection-region resolution

If the jet or bow shock reaches the domain boundary, the run cannot be patched
later; the case must be restarted with a larger grid. Err on safe domain size
while keeping the central resolution physically adequate.

## Truth Definitions

Level 1 truth is injected jet energy.

- `JET_PWR` is confirmed as one-sided jet power.
- One-sided injected energy is `JET_PWR * active_time`.
- Total bipolar injected energy is `2 * JET_PWR * active_time`.
- Use the one-sided convention for the headline simulation parameter and record
  the bipolar total where it clarifies energy accounting.

Level 2 truth is tracer-defined lobe material and its energy.

- Default lobe mask: tracer > `5e-3`.
- Sensitivity masks: tracer > `1e-3` and tracer > `1e-2`.
- Report volume, thermal energy, kinetic energy, and total lobe energy where
  `plutokore` supports the calculation reliably.
- Initial energy comparisons should use the same snapshot and view as the
  first X-ray/radio smoke products.

Gas-coupled or shock-deposited energy remains a later truth level until Level 1
and Level 2 are green.

## Observable Protocol

The first observable/truth comparison is for `C-HI` at one declared early
snapshot and view. The meeting made `0 deg` the natural first view because it
places the jet in the plane of the sky.

Required first products:

- one X-ray map from GRAiLE/XRAiSE or the predecessor-project pipeline
- one ellipsoidal cavity boundary
- local ambient pressure near the cavity
- `pV` and `4pV`
- sound, buoyancy, and refill age estimates
- one radio lobe boundary
- one radio luminosity smoke product
- Level 1 and Level 2 truth values for the same snapshot

The X-ray workflow must use GRAiLE/XRAiSE or the predecessor project pipeline.
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
mpirun -np "$NRANKS" ./pluto -i pluto.ini -e environment.ini -maxtime 47.5
```

Required production-safety features:

- `DONE` and `FAILED` markers
- fresh-start vs restart detection
- PLUTO source revision logging
- `jet-setup` source revision logging
- run definition and case manifest logging
- PBS nodefile logging
- output-volume estimate before submission
- output catalogue mapping file number to physical time and file role
- walltime-safe PLUTO stop before PBS termination
- double-precision HDF5 restart output at walltime stop
- static-grid `.dbl.h5` restart via `-h5restart n`
- email notifications to `barry.brook@utas.edu.au`

One intermediate `C-HI` `kunanyi` rehearsal must pass before any multi-day
production chain is submitted.

## Acceptance Gate For The Three-Case Suite

Move from single-case validation to the full three-case suite only after
`C-HI` has:

- a generated config package reviewed by Patrick/Stas
- a production-like, particles-enabled run with healthy first `3-5` snapshots
- a confirmed restart path
- `DONE`/`FAILED` marker behavior
- HDF5 and restart output confirmed
- at least one aligned X-ray/radio/truth comparison at a declared snapshot and
  view
- a practical runtime/output-volume estimate for longer runs

After that, production launch order is:

1. `C-HI`
2. `C-LO`
3. `G-LO`

## Later Extension: Offset Tabulated Environments

The offset-environment idea is not the first run. The order is:

1. centered, symmetric `C-HI` control
2. implement or verify offset support for tabulated environments
3. run the offset tabulated environment without a jet
4. inject the same jet into the offset environment

For tabulated environments, the radius lookup should be computed relative to
the requested offset centre rather than unconditionally relative to `(0,0,0)`:

```text
r = sqrt((x - x_offset)^2 + (y - y_offset)^2 + (z - z_offset)^2)
```

The first scientifically useful offset may be large, around `50 kpc`, to
produce visibly different bubbles on the two sides.

## Unresolved Supervisor Confirmations

The following items remain open and should be resolved before serious
production:

- production grid extents and stretched-grid patch structure
- science inlet radius and injection height
- exact first diagnostic snapshot for the X-ray/radio/truth comparison
- whether longer science sampling should use `50`, `100`, `200`, `300 Myr`, or
  a shorter sequence after the first runtime estimate
- repo-local GRAiLE/XRAiSE porting details and dependency environment
- production queue, walltime limit, and storage retention plan on `kunanyi`
- whether tabulated-environment offset support should be implemented before or
  after the three centered cases
