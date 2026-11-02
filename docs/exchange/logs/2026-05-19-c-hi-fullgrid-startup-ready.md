# 2026-05-19 C-HI Full-Grid Startup Packet Ready

## Summary

The first full-grid `C-HI` startup/checkpoint packet is prepared locally but
has not been submitted to `kunanyi`.

Submission was deferred until Barry is on campus/direct `eduroam` on
`2026-05-20`. The off-campus direct MacBook route to
`<tpac-jumpbox>:22` timed out, and the previously validated Nectar
bastion route was unavailable because Nectar was down for maintenance.

## Supervisor-Agent Review State

Patrick-agent and Stas-agent both reviewed the next gate. The decision is
`GO WITH CHANGES`.

The required change has been made:

- `Nparticles          -1    32.0`
- render command uses `--particles-per-injection 32`

Stas-agent's requested diagnostics can proceed in parallel:

- x-z midplane slices
- `2.5pV` energetics
- tracer-energy/injected-energy and `2.5pV`/injected-energy ratios
- setup blocks in summaries
- density along the jet axis

Stas-agent also asked Patrick-agent to confirm whether `dbl.h5` cadence five
times less frequent than `flt.h5` is acceptable. Patrick-agent had already
said no HDF5 restart policy change was requested, so this is recorded as a
non-blocking follow-up for the startup/checkpoint gate.

## Prepared Local Artifacts

Tracked config snapshot:

```text
docs/science/assets/c_hi_fullgrid_startup_2026-05-19/
```

Ignored runnable bundle:

```text
build/science/c_hi_fullgrid_startup_2026-05-19/
```

PBS wrapper:

```text
scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs
```

Stage/submit helper:

```text
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
```

## Launch Shape

The first full-grid launch is a bounded startup/checkpoint gate, not the full
48-hour science segment.

```text
select=80:ncpus=28:mpiprocs=28
walltime=04:00:00
PLUTO_MAXTIME_HOURS=3.5
RESTART_POLICY=force-fresh
ALLOW_DONE_RERUN=1
RUN_ROOT=/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup
```

## Validation

Local validation completed before this note:

```text
bash -n scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh \
  scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs \
  scripts/kunanyi/jet_setup_production_template.pbs
```

Rendered config checks:

```text
render_validation.json ok = true
Nparticles_second_field expected/rendered = 32.0
particles_dbl expected/rendered = 3.06601394
flt.h5 expected/rendered = 306.60139379
dbl.h5 expected/rendered = 1533.00696894
JET_PWR expected/rendered = 1e+45
manifest case/grid/variant/particle count = ok
```

## Tomorrow's Launch Command

Direct campus path:

```bash
cd /Users/bwbrook/papers/xray_cavities
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
```

If direct campus SSH still fails and Nectar is restored:

```bash
cd /Users/bwbrook/papers/xray_cavities
TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-nectar \
TPAC_SCP_HOST=kunanyi-via-nectar \
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
```

The script stages the prepared bundle, verifies remote `Nparticles = 32` and
`render_validation.json`, submits the PBS wrapper, and prints
`SUBMITTED_JOB_ID=...`.
