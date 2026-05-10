# 2026-05-10 C-HI Two-node Continuation To 5 Myr

## Context

This note records the follow-up after the two-node `C-HI` restart rehearsal.
The goal was to continue the particles-enabled high-power Stewart-cluster run
far enough to collect the agreed early diagnostic snapshots before beginning the
truth/observable smoke work.

## `kunanyi` Run

PBS job:

- job id: `690560.kunanyi-ohpc`
- job name: `c_hi_2node_to5`
- case: `C-HI`
- variant: `particles`
- resources: `select=2:ncpus=28:mpiprocs=28`
- nodes: `n194` and `n029`
- MPI ranks: `56`
- restart mode: `RUN_KIND=h5_restart_3`
- PLUTO arguments: `-i pluto.ini -e environment.ini -maxtime 4.5 -h5restart 3`
- result: `Exit_status = 0`
- walltime: `04:52:47`
- CPU time: `127:07:58`
- peak memory: `18625004kb`

The job wrote a `DONE` marker and no `FAILED` marker.

## Output State

The run now has regular science-cadence `flt.h5` outputs at approximately:

- `1 Myr`: `data.0002.flt.h5`
- `2 Myr`: `data.0004.flt.h5`
- `3 Myr`: `data.0006.flt.h5`
- `4 Myr`: `data.0007.flt.h5`
- `5 Myr`: `data.0008.flt.h5`

It also has restart-capable `dbl.h5` outputs through:

- `data.0004.dbl.h5` at about `5 Myr`
- `data.0005.dbl.h5` at about `5.455 Myr`, written by the walltime-safe
  `-maxtime` stop

Particle outputs extend through `particles.0549.dbl`.

## Quick-look

A compute-node quick-look extraction job inspected the nominal 5 Myr float
snapshot:

- quick-look job id: `690583.kunanyi-ohpc`
- inspected file: `data.0008.flt.h5`
- timestep: `Timestep_8`
- physical time: `4.9994 Myr`
- result: `Exit_status = 0`

At the default tracer threshold `tracer > 5e-3`, the tracer-defined region spans
approximately:

- `x`: `-9.46` to `+9.46 kpc`
- `y`: `-9.46` to `+9.46 kpc`
- `z`: `-33.0` to `+33.0 kpc`

This remains comfortably inside the `X3 = +/-250 kpc` domain.

## Truth Smoke

A compute-node truth extraction job was also run against the same 5 Myr
snapshot:

- truth job id: `690585.kunanyi-ohpc`
- inspected file: `data.0008.flt.h5`
- timestep: `Timestep_8`
- result: `Exit_status = 0`
- walltime: `00:00:27`
- peak memory: `3467276kb`

Level 1 at `4.9994 Myr`:

- one-sided injected energy elapsed: `1.5777e59 erg`
- bipolar injected energy elapsed: `3.1554e59 erg`
- configured 50 Myr bipolar active-time energy: `3.1558e60 erg`

Level 2 default tracer mask, `tracer > 5e-3`:

- bipolar tracer-mask volume: `10791.8 kpc^3`
- bipolar thermal energy: `9.6642e58 erg`
- bipolar kinetic energy: `8.7948e58 erg`
- bipolar total energy: `1.8459e59 erg`

The two sides are balanced to the precision needed for this smoke check, which
is a useful confirmation of the symmetric-control setup. These are
tracer-mask energetics, not cavity `pV` measurements.

## Local Artifacts

Report:

- `docs/science/c_hi_to5_quicklook_2026-05-10.md`
- `docs/science/c_hi_to5_quicklook_2026-05-10.pdf`

Figures and catalogue:

- `docs/science/assets/c_hi_to5_quicklook_2026-05-10/`

Compact evidence bundle:

- `build/science/kunanyi_stage_2026-05-08/c_hi_to5_690560_quicklook_690583_compact_2026-05-10.tar.gz`
- SHA-256:
  `56a4190ba1727070809f52233648b9e2097df9ab29859b85bf7b12460a9ebbc5`

Truth compact evidence bundle:

- `build/science/kunanyi_stage_2026-05-08/c_hi_truth_690585_compact_2026-05-10.tar.gz`
- SHA-256:
  `b6b3a32517084e9f4d458e9740ecdefb5ec740d8be5d42532137f8911dd81b5c`

## Next Step

The early diagnostic run gate is green, and the Level 1/Level 2 truth half of
the first smoke package now exists. The next science gate should be the first
aligned observable smoke package, starting from the 5 Myr regular snapshot and
the `0 deg` view unless there is a deliberate choice to wait for a later,
larger cavity:

1. First GRAiLE/XRAiSE X-ray map path using the supplied assets.
2. First particle/radio smoke product through `plutokore`.
3. First cavity-protocol stub: ellipsoidal boundary, local pressure, `pV`, and
   `4pV` from the same snapshot.
