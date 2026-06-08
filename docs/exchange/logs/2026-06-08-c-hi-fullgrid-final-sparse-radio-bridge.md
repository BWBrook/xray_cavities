# 2026-06-08 C-HI full-grid final sparse radio bridge

## Context

The final particle endpoint summary and sparse-window trajectory extraction
were green. The next bounded science step was to connect the sparse trajectory
product to the existing 150 MHz particle radio smoke conventions without
building a dense all-history particle HDF5 cache.

## Local Tooling

Added:

- `scripts/science/sparse_particle_radio_bridge.py`
- `scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs`
- `tests/test_sparse_particle_radio_bridge.py`

The bridge computes lossless synchrotron emissivity from final sparse-window
particle rows, applies a bounded pressure-history attenuation proxy, and bins
the result into final-endpoint `x-z` radio maps and lobe summaries.

Local TDD/verification commands:

```text
uv run pytest tests/test_sparse_particle_radio_bridge.py -q
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs
```

## Remote Staging

Remote control used the authenticated Chrome Kunanyi shell because plain SSH
control-socket auth was unavailable. The reliable route was to open a fresh
Open OnDemand shell tab and type through the terminal iframe textarea; earlier
long clipboard batches through hterm could concatenate before Return landed.

Staged files matched local SHA-256:

- `spr.py`:
  `29d827cff6a8587e00f0c7b909c32ed9bd6f0c3ec3ad208052ddedc684d124dd`
- `spr.pbs`:
  `dbf2315ba4df7557c2c10571216cceab40357a135df39cc36dc1669f50c2f1a5`

## Submission

```text
qsub spr.pbs
697646.kunanyi-ohpc
```

## Result

- PBS job: `697646.kunanyi-ohpc`
- job name: `c_hi_spr_fin`
- result: `Exit_status = 0`
- walltime used: `00:00:05`
- CPU time: `00:00:04`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stderr size: `0` bytes

Remote output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.tar.gz
```

Archive SHA-256:

```text
2be0b61dcc7330727192123f9afd9c9a7138d26ea4f552ba62753cd72e24effe
```

The compact archive was downloaded through the Open OnDemand Files app and
unpacked locally under:

```text
docs/science/assets/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08/
```

## Headline Metrics

- target index: `5000`
- sparse trajectory rows consumed: `218909`
- selected target particles: `20000`
- particles in frame: `20000`
- map shape: `460 x 90`
- map pixel size: `1 kpc`
- positive radio pixels: `11829`
- pressure-history loss proxy mean: `0.8957169833296894`
- proxy map max: `1.2449378088138194e16 mJy sr^-1`
- bipolar proxy luminosity: `4.4514434941743747e27 W Hz^-1`
- negative-z proxy luminosity: `1.3997874068653554e27 W Hz^-1`
- positive-z proxy luminosity: `3.05165608730902e27 W Hz^-1`

## Decision

The first final-endpoint sparse radio bridge is green. Treat the map and lobe
summary as a morphology and continuity product only: the loss term is a
pressure-history proxy across outputs `4950..5000`, and the luminosity scale
uses `1.0 kpc^3` per selected particle.

The next technical move is to replace the pressure-history proxy with a true
sparse PRAiSE-compatible loss interface for the selected particle IDs, then
couple the resulting map to the final grid/tracer volume convention and the
observable comparison page.
