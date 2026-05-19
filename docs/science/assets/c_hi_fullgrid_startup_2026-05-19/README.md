# C-HI Full-Grid Startup Config Snapshot

This folder records the launch configuration prepared on `2026-05-19` for the
first full-grid `C-HI` startup/checkpoint gate on `kunanyi`.

The runnable bundle is generated under ignored `build/` space:

```bash
uv run python scripts/science/render_three_case_configs.py \
  --variant particles \
  --case C-HI \
  --grid stewart_stretched_250 \
  --duration-myr 50 \
  --snapshot-interval-myr 1 \
  --dbl-h5-interval-myr 5 \
  --particle-interval-myr 0.01 \
  --particles-per-injection 32 \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --check-local-assets \
  --output build/science/c_hi_fullgrid_startup_2026-05-19 \
  --force
```

Tracked files under `config/` exclude the tabulated environment CSV, which
remains under ignored `env/` and is copied into the runnable `build/` bundle.

Key launch choices:

- grid preset: `stewart_stretched_250`
- case: `C-HI`
- variant: particles enabled
- particle injection count: `32`
- particle cadence: `0.01 Myr`
- `flt.h5` cadence: `1 Myr`
- `dbl.h5` cadence: `5 Myr`
- first launch script: `scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs`
- stage/submit helper: `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh`

The first launch is intentionally a bounded startup/checkpoint gate:

- `select=80:ncpus=28:mpiprocs=28`
- `walltime=04:00:00`
- `PLUTO_MAXTIME_HOURS=3.5`
- `RESTART_POLICY=force-fresh`

It was prepared on `2026-05-19` but not submitted because off-campus direct
MacBook SSH to `<tpac-host>:22` timed out and the Nectar bastion route
was temporarily unavailable. The direct launch command for campus/`eduroam` is:

```bash
cd /Users/bwbrook/papers/xray_cavities
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh
```
