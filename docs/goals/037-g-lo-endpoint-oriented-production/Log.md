# Goal 037 Log - G-LO Endpoint-Oriented Production

Date: 2026-07-07

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `cc8dbea`.
- Initial git status: `## main...origin/main`.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 037 authorizes restoring/verifying the Stewart group `002_031` asset,
rendering an asset-backed `G-LO` particles config, preflighting Kunanyi, and
submitting exactly one endpoint-oriented `G-LO` production PBS job if all gates
are clean.

The goal does not authorize polling after queued/running proof, retrieval,
checkpoint review, post-processing, XRAiSE/PRAiSE/radio/cavity/source-age work,
C-HI/C-LO reruns, G-LO science products, scientific-default changes, commits,
pushes, cleanup, Stas/Patrick contact, or `agent_comms` edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- `docs/science/three_case_spec.md`.
- Goal 029 comparison readiness note/assets/log.
- Goal 031 Stewart asset restore/preflight note/assets/log.
- Goal 032/035 C-LO production wrappers and logs.
- Goal 036 C-LO endpoint first-products note/log sufficient to inherit the
  endpoint/control-surface contract.
- `scripts/science/render_three_case_configs.py`.
- `scripts/kunanyi/jet_setup_production_template.pbs`.

## Asset Restore

The local ignored asset was absent at:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002031.csv
```

The authorized Chrome/Open OnDemand route was used to open the TPAC SSH
selector. The page reported a 5-minute window closing at
`Tue Jul 7 13:48:26 2026` for the asset search and restore.

Bounded remote search under the trusted May 8 staging root found one exact
candidate:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/group_002031/tabulated_cosmo_002031.csv
```

Remote validation:

- SHA-256:
  `1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a`;
- size: `608000` bytes;
- rows: `4000`;
- columns: `6`;
- radius monotonicity: strictly increasing;
- radius range: `0.000000000000000000e+00` to
  `1.697122669820251998e+24` cm.

The file was fetched exactly into the ignored local `env/` path. Local
validation reproduced the same SHA, size, row count, column count, and radius
range. `git check-ignore` confirmed the raw asset is ignored by `.gitignore`.

## Local Implementation

Added focused wrapper contract tests:

```text
tests/test_g_lo_endpoint_oriented_production_wrapper.py
```

Added the endpoint-oriented G-LO production wrapper:

```text
scripts/kunanyi/g_lo_endpoint_oriented_production.pbs
```

The wrapper:

- targets `G-LO` / `particles`;
- uses the Goal 037 rendered config stage path;
- uses a fresh no-overwrite run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production`;
- requests `select=64:ncpus=28:mpiprocs=28`, `walltime=48:00:00`;
- sets `PLUTO_MAXTIME_HOURS=47.5`;
- uses `RESTART_POLICY=force-fresh`;
- preserves the accepted `agn_intel_impi` module stack and Intel MPI contract;
- delegates to `jet_setup_production_template_latest.pbs`;
- does not submit follow-on jobs or run post-processing.

The test was run red first and failed because the wrapper did not exist. After
adding the wrapper, the focused G-LO tests plus the C-LO endpoint-oriented
regression tests passed.

## Config Render

Rendered the G-LO particles config with the restored group asset:

```bash
uv run python scripts/science/render_three_case_configs.py \
  --case G-LO \
  --variant particles \
  --grid stewart_stretched_250 \
  --duration-myr 50 \
  --snapshot-interval-myr 1 \
  --dbl-h5-interval-myr 5 \
  --particle-interval-myr 0.01 \
  --particles-per-injection 32 \
  --group-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002031.csv \
  --require-assets \
  --check-local-assets \
  --output build/science/g_lo_endpoint_oriented_production_2026-07-07/rendered_g_lo_config \
  --force
```

Rendered config audit passed:

- case: `G-LO`;
- environment: `group`;
- Stewart group: `002_031`;
- `JET_PWR=1e43 erg/s`;
- `JET_SPD=0.1 c`;
- `tstop=15330.06968940`;
- `tabulated_cosmo_002031.csv` SHA matched the restored asset.

## Remote Staging And Preflight

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production
```

Run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production
```

The TPAC selector expired once before remote preflight. The authorized Chrome
route was used again; the page reported a live window closing at
`Tue Jul 7 13:54:10 2026`. Safari was not used.

Staged files:

- `g_lo_endpoint_oriented_production.pbs`;
- `jet_setup_production_template_latest.pbs`;
- rendered `G-LO/particles` config bundle, including
  `tabulated_cosmo_002031.csv`.

Remote preflight passed:

- staged SHA-256 values matched local values;
- remote `bash -n` passed for wrapper and production template;
- remote config sanity asserted `G-LO`, `group`, `tabulated_cosmo_002031.csv`,
  `JET_PWR=1e+43`, `JET_SPD=0.1`, and `tstop=15330.06968940`;
- remote group table reported `asset_rows=4000`, `asset_bad_col_rows=0`, and
  `asset_radius_monotonic=1`;
- PLUTO, `jet-setup`, `setup-problem`, and `/ds/projects/agn/modulefiles`
  paths existed;
- module purge/use/load succeeded for `intel/18.0.1.163`,
  `impi/2018.1.163`, `hdf5/1.12.1p`, and `zfp/0.5.5`;
- `mpicc` and `mpirun` were available;
- no-overwrite workdir was absent at
  `/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles`;
- queue `normal` was enabled and started, with
  `resources_max.walltime=48:00:00`.

Preflight transcript path:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/remote_logs/submission_preflight_2026-07-07_g_lo.txt
```

## Submission

Submitted exactly one PBS job:

```text
751105.kunanyi-ohpc
```

Scheduler proof at stop:

- job name: `g_lo_endpt`;
- queue: `normal`;
- state: `Q`;
- `Resource_List.select=64:ncpus=28:mpiprocs=28`;
- `Resource_List.ncpus=1792`;
- `Resource_List.mpiprocs=1792`;
- `Resource_List.nodect=64`;
- `Resource_List.walltime=48:00:00`;
- output path:
  `/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.out`;
- error path:
  `/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.err`.

The repo-local helper returned `__CODEX_STATUS__=141` after qsub and qstat
printed the queued-state proof. This is recorded as a helper/session
pipe-status caveat, not as a submission failure. No further remote commands
were run after the `Q` proof.

Status:

```text
submitted_waiting_pbs_completion
```

Decision label:

```text
G_LO_ENDPOINT_ORIENTED_PRODUCTION_SUBMITTED_WAITING_PBS_COMPLETION
```

## Local Validation

Focused tests and syntax checks:

```bash
uv run pytest tests/test_g_lo_endpoint_oriented_production_wrapper.py tests/test_c_lo_endpoint_oriented_continuation_wrapper.py -q
bash -n scripts/kunanyi/g_lo_endpoint_oriented_production.pbs
bash -n scripts/kunanyi/jet_setup_production_template.pbs
```

Result:

```text
8 passed
```

Additional validation:

- G-LO config rendered with `--require-assets --check-local-assets`;
- local/restored asset shape and SHA checks passed;
- remote staged hashes and remote syntax checks passed;
- structured asset JSON/CSV parse checks passed;
- `git diff --check` passed;
- targeted unresolved/stale-label scan passed.

## Next Step

Stop now under the PBS stop rule. Wait for Barry's PBS completion email before
any qstat, retrieval, or checkpoint review. The next goal should retrieve only
compact stdout/stderr/qstat/catalogue evidence and classify the G-LO run as an
endpoint, checkpoint, or failure surface. Do not retrieve bulky HDF5, `data.*`,
or particle payloads locally.

## Completion Failure Diagnosis And Checkpoint Correction - 2026-07-10

Status: `complete_failure_diagnosis_checkpoint_preserved`.

Decision label:
`G_LO_HDF5_WRITE_STALL_SAFE_FLUID_CHECKPOINT_PRESERVED_RESTART_PREFLIGHT_REQUIRED`.

The completion turn used Chrome/Open OnDemand for access, remote read-only
final qstat and inventory generation, and compact evidence retrieval for job
`751105.kunanyi-ohpc`. It submitted no new PBS job and retrieved no bulky
payloads.

The compact evidence shows:

- final scheduler state `F`, `Exit_status=271`, and
  `resources_used.walltime=48:01:33` against `48:00:00` requested;
- stderr says PBS killed the job because walltime `172883` exceeded limit
  `172800`;
- stdout records `RUN_KIND=fresh`,
  `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5`, and
  `JOB_SIGNAL=TERM`;
- `markers/DONE` absent and `markers/FAILED` present but zero bytes because
  termination interrupted marker writing;
- latest completed `dbl.h5.out` row
  `2 3.065935e+03 3.213700e-01 10578`;
- latest completed `flt.h5.out` row
  `14 4.292332e+03 3.164317e-01 14424`;
- full `data.0000.dbl.h5`, `data.0001.dbl.h5`, and `data.0002.dbl.h5` files,
  each `67,318,639,276` bytes;
- partial `data.0003.dbl.h5` at `44,741,404,952` bytes, with no matching XMF
  and no index-3 `dbl.h5.out` row.

`data.0003.dbl.h5` is therefore only the latest inventoried double filename. It
is an incomplete termination artifact and must never be selected as a restart.
The validated fluid checkpoint preserved is `data.0002.dbl.h5`, catalogue
index `2`, at code time `3065.935`, with matching XMF.

The nearest particle file by remote mtime is `particles.1000.dbl`, size
`5,044,387` bytes, written 44 seconds after the safe HDF5 file. It is the
candidate paired particle surface only. Its contents and restart pairing have
not been validated and require an explicit preflight before any submission.
The full fluid/particle restart is conditional on that preflight and a
fail-closed no-progress watchdog.

The latest complete float output is `data.0014.flt.h5` at code time `4292.332`.
The safe restart preserves about `9.99974 Myr` / `19.99949%` of the endpoint,
whereas the latest float records about `13.99971 Myr` / `27.99943%`. The
restart rollback is `1226.397` code-time units, about `3.99997 Myr` or
`7.99994` endpoint percentage points.

The configured endpoint remains `15330.06968940`, leaving
`11037.73768940` code-time units after the latest float row. Remote inventory
records `863G`, `19` HDF5 files (`4` double and `15` float), and `1500`
particle restart files. The 10 Myr fluid checkpoint is validated and
preserved, but the whole restart surface is not unconditionally restartable.
This is not an endpoint and not a science product.

The partial double file stopped changing about `10:22:34` after job start and
about `37:38:48` before wrapper termination. This rules out the simple theory
that a 30-minute PLUTO/PBS buffer was merely too short for a final dump. The
strongest supported root cause is a stalled regular 15 Myr parallel
collective-HDF5 write, with scheduler walltime as the terminal symptom. The
stall began about 10.4 hours after launch, so `PLUTO_MAXTIME_HOURS=47.5` is not
the cause. No physics failure is demonstrated.

Recommended next contract, only after Barry explicitly authorizes another
run: one isolated 64-node / 1792-rank / 48-hour continuation with explicit
`-h5restart 2`, after validating the candidate particle pairing, and with a
fail-closed no-progress watchdog. Do not stage `data.0003.dbl.h5`. Retain the
5 Myr double-output cadence and the `47.5` hour PLUTO guard for this next run;
neither a denser double cadence nor a modestly shorter maxtime addresses the
observed stall.

Completion package:

- `docs/science/g_lo_endpoint_oriented_production_completion_2026-07-10.md`;
- `docs/science/assets/g_lo_endpoint_oriented_production_completion_2026-07-10/`.

Provenance caveats:

- raw `remote_logs/safe_restart_surface_2026-07-10.txt` contains literal
  backslash-`n` sequences and is preserved unchanged; local reviewed summaries
  normalize its fields;
- the original remote SHA manifest predates that file and the empty PLUTO
  diagnostic extracts; `local_asset_manifest.sha256` covers the complete final
  bundle.

No new PBS submission, bulky retrieval, staging, cleanup, commit, push,
post-processing, endpoint product, or science-product work occurred.
