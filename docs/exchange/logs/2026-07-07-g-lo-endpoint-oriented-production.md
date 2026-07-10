# 2026-07-07 - G-LO Endpoint-Oriented Production

Goal 037 moved the comparison-case ladder from accepted C-HI and C-LO endpoint
surfaces to a submitted endpoint-oriented G-LO production job.

## Status

Status:
`submitted_waiting_pbs_completion`.

Decision label:
`G_LO_ENDPOINT_ORIENTED_PRODUCTION_SUBMITTED_WAITING_PBS_COMPLETION`.

## Asset Restore

Restored ignored Stewart group asset:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002031.csv
```

Trusted remote source:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/group_002031/tabulated_cosmo_002031.csv
```

SHA-256:

```text
1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a
```

The asset validates as `4000` rows, `6` columns, strictly increasing radius,
and remains ignored by Git.

## Local Gate

Generated and audited an asset-backed `G-LO` / `particles` config with:

- Stewart group `002_031`;
- `JET_PWR=1e43 erg/s`;
- `JET_SPD=0.1 c`;
- `tstop=15330.06968940`;
- grid `stewart_stretched_250`;
- particles enabled.

Added wrapper:

```text
scripts/kunanyi/g_lo_endpoint_oriented_production.pbs
```

Added focused wrapper tests:

```text
tests/test_g_lo_endpoint_oriented_production_wrapper.py
```

Local tests and syntax checks passed:

```text
uv run pytest tests/test_g_lo_endpoint_oriented_production_wrapper.py tests/test_c_lo_endpoint_oriented_continuation_wrapper.py -q
8 passed
```

## Remote Preflight

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production
```

Run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production
```

Remote preflight passed:

- staged hashes matched local wrapper/template/config/table hashes;
- remote wrapper/template `bash -n` passed;
- config sanity passed for `G-LO`, group asset, `JET_PWR=1e+43`,
  `JET_SPD=0.1`, and `tstop=15330.06968940`;
- tabulated group asset passed row/column/radius checks;
- PLUTO and `jet-setup` source paths existed;
- AGN Intel/IMPI/HDF5/ZFP module stack loaded;
- `mpicc`/`mpirun` were present;
- no-overwrite workdir was absent;
- queue `normal` was enabled/started and allowed `48:00:00` walltime.

Remote preflight transcript:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/remote_logs/submission_preflight_2026-07-07_g_lo.txt
```

## PBS Submission

Submitted exactly one job:

```text
751105.kunanyi-ohpc
```

Job name:

```text
g_lo_endpt
```

Queue/state at stop:

```text
normal / Q
```

Requested resources:

```text
select=64:ncpus=28:mpiprocs=28
ncpus=1792
mpiprocs=1792
nodect=64
walltime=48:00:00
```

Expected stdout/stderr:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.out
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.err
```

The helper returned status `141` after the queued-state proof was printed.
This is treated as a helper/session pipe-status caveat, not as a failed qsub.
No further remote commands were run after the `Q` proof.

## Next Step

Wait for Barry's PBS completion email. The next goal should retrieve compact
qstat/stdout/stderr/catalogue evidence only for `751105.kunanyi-ohpc`, classify
the G-LO surface as endpoint/checkpoint/failure, and keep bulky HDF5,
`data.*`, and particle payloads remote.

## Boundary

No polling after queued proof, retrieval, checkpoint review, post-processing,
XRAiSE/PRAiSE/radio/cavity/source-age work, C-HI/C-LO rerun, G-LO product
generation, scientific-default change, commit, push, cleanup, Stas/Patrick
contact, or `agent_comms` edit occurred.

## Completion Failure Diagnosis - 2026-07-10

Status: `complete_failure_diagnosis_checkpoint_preserved`.

Decision label:
`G_LO_HDF5_WRITE_STALL_SAFE_FLUID_CHECKPOINT_PRESERVED_RESTART_PREFLIGHT_REQUIRED`.

The completion turn used Chrome/Open OnDemand for access, remote read-only
final qstat and inventory generation, and compact evidence retrieval. It did
not submit a new PBS job or retrieve bulky payloads.

The final scheduler record for `751105.kunanyi-ohpc` is
`Exit_status=271`, `resources_used.walltime=48:01:33`, against requested
`48:00:00`. Stderr says PBS killed the job because walltime `172883` exceeded
limit `172800`; stdout records `RUN_KIND=fresh`,
`RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5`, and
`JOB_SIGNAL=TERM`. `markers/DONE` is absent, while `markers/FAILED` exists but
is zero bytes because termination interrupted marker writing. Scheduler
walltime is the terminal symptom, not the strongest root-cause classification.

Restart boundary:

- latest inventoried double filename: `data.0003.dbl.h5`, but only
  `44,741,404,952` bytes, with no XMF and no catalogue row; incomplete and not
  restartable;
- validated fluid checkpoint preserved: `data.0002.dbl.h5`,
  `67,318,639,276` bytes,
  matching XMF, catalogue index `2`, code time `3065.935`;
- candidate paired particle file: `particles.1000.dbl`, `5,044,387` bytes,
  remote mtime 44 seconds after the fluid checkpoint; mtime-only association,
  requiring explicit content/pairing preflight;
- latest complete float output: `data.0014.flt.h5`, catalogue index `14`, code
  time `4292.332`.

The safe restart is about `9.99974 Myr` / `19.99949%` of endpoint; the latest
float is about `13.99971 Myr` / `27.99943%`. Restarting rolls back about
`3.99997 Myr`, or `7.99994` endpoint percentage points.

The endpoint remains `15330.06968940`, with `11037.73768940` code-time units
remaining after the latest float row. Remote inventory records `863G`, `19`
HDF5 files (`4` double and `15` float), and `1500` particle restart files.
The 10 Myr fluid checkpoint is validated and preserved, but the full
fluid/particle restart is conditional on explicit preflight and a fail-closed
no-progress watchdog. This is not endpoint and not science product.

`data.0003.dbl.h5` stopped changing about `10:22:34` into the job and remained
stale for about `37:38:48` before termination. The strongest supported root
cause is a stalled regular 15 Myr parallel collective-HDF5 write, not an
undersized 30-minute final-output buffer. `PLUTO_MAXTIME_HOURS=47.5` is not the
cause because the stall began about 10.4 hours after launch. No physics failure
is demonstrated.

Next contract, only after Barry explicitly authorizes another run: after
particle-pair preflight, run one isolated 64-node, 1792-rank, 48-hour
`-h5restart 2` continuation with a fail-closed no-progress watchdog. Keep the 5 Myr
double cadence and the `47.5` hour PLUTO guard for this run. Do not stage or
restart from `data.0003.dbl.h5`.

Completion package:

- `docs/science/g_lo_endpoint_oriented_production_completion_2026-07-10.md`;
- `docs/science/assets/g_lo_endpoint_oriented_production_completion_2026-07-10/`.

Raw `remote_logs/safe_restart_surface_2026-07-10.txt` contains literal
backslash-`n` sequences and is preserved unchanged; local summaries normalize
its fields. The original remote SHA manifest predates that file and the empty
PLUTO diagnostic extracts; `local_asset_manifest.sha256` covers the complete
final bundle.

No new PBS submission, bulky retrieval, staging, cleanup, commit, push,
post-processing, endpoint product, or science-product work occurred.
