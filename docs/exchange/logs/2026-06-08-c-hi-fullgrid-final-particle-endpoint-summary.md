# 2026-06-08 C-HI full-grid final particle endpoint summary

## Context

The full-grid final particle-HDF5 feasibility preflight completed green but
recommended against a naive full-history `plutokore.load_all_particles()` cache:
the raw float64 matrix was estimated at about `109.95 GiB`, with a conservative
peak-memory estimate near `1099.55 GiB`.

The next bounded step was therefore an endpoint-only particle summary from the
final PLUTO particle file.

## Submission

Remote control was via the authenticated Chrome Kunanyi shell tab because plain
SSH control-socket auth was unavailable in this session.

Long source pastes through hterm corrupted data unless staged in small
clipboard batches and verified. The final staged files matched local SHA-256:

- `pes.py`:
  `64f640d3717601270d3d5d9b0bbbe169ab709522bc9248ab6181a529a60e0731`
- `pend.pbs`:
  `d96db8f82dcdc41c695d8b8ea2c7a5c8feef29e7ae71ed857cc71d9743d35762`

Submitted:

```text
qsub pend.pbs
697643.kunanyi-ohpc
```

## Result

- PBS job: `697643.kunanyi-ohpc`
- job name: `c_hi_pend_sum`
- result: `Exit_status = 0`
- walltime used: `00:00:39`
- CPU time: `00:00:02`
- peak memory: `9444kb`
- peak virtual memory: `367032kb`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stderr size: `0` bytes

Remote output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-endpoint-summary
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.tar.gz
```

Archive SHA-256:

```text
a25a805858a438f56369fe4d3690c31bdd358efb0082f73c3d5e51b0633e35e1
```

## Headline Metrics

- particles: `196732`
- endpoint physical time: `50.00000000000777 Myr`
- PLUTO step: `49253`
- position envelope:
  - `x = -29.695625916316235` to `30.132441460503376 kpc`
  - `y = -32.27023110544345` to `30.062788186588232 kpc`
  - `z = -215.6060699853556` to `216.06201669846072 kpc`
- negative-z lobe: `97451` particles, fraction `0.4953490027041864`
- positive-z lobe: `99281` particles, fraction `0.5046509972958136`

## Decision

Endpoint particle diagnostics are green. Continue toward sparse-window or
streaming particle analysis; do not submit a dense all-history particle-HDF5
cache with the current approach.
