# G-LO Endpoint-Oriented Production Submission

Date: 2026-07-07

## Decision

Status:
`submitted_waiting_pbs_completion`.

Decision label:
`G_LO_ENDPOINT_ORIENTED_PRODUCTION_SUBMITTED_WAITING_PBS_COMPLETION`.

Goal 037 restored the Stewart group `002_031` environment asset, rendered and
audited an asset-backed `G-LO` particles config, passed local and remote
preflight, and submitted exactly one endpoint-oriented Kunanyi production job.

This is a production submission handoff, not a completion or science-product
claim.

## Restored Group Asset

The required ignored local asset was restored to:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002031.csv
```

Trusted source:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/group_002031/tabulated_cosmo_002031.csv
```

SHA-256:

```text
1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a
```

Validation:

- `4000` rows;
- `6` whitespace columns;
- strictly increasing radius;
- radius range `0` to `1.697122669820251998e+24` cm;
- raw asset remains ignored under `env/` and is not committed.

## Config And Production Contract

Rendered G-LO config:

```text
build/science/g_lo_endpoint_oriented_production_2026-07-07/rendered_g_lo_config/G-LO/particles/
```

Key audited constants:

- case: `G-LO`;
- environment: Stewart group `002_031`;
- role: environment-dependence case;
- `JET_PWR=1e43 erg/s`;
- `JET_SPD=0.1 c`;
- target duration: `50 Myr`;
- PLUTO `tstop=15330.06968940`;
- grid: `stewart_stretched_250`;
- particles enabled.

Production wrapper:

```text
scripts/kunanyi/g_lo_endpoint_oriented_production.pbs
```

Resource choice:

- queue: `normal`;
- `select=64:ncpus=28:mpiprocs=28`;
- total ranks: `1792`;
- walltime: `48:00:00`;
- `PLUTO_MAXTIME_HOURS=47.5`;
- restart policy: `force-fresh`.

This follows the accepted C-LO endpoint-oriented production pattern while
using the G-LO group asset and a fresh no-overwrite G-LO run root.

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

- staged wrapper/template/config/table hashes matched local values;
- remote wrapper and template `bash -n` passed;
- remote config sanity asserted `G-LO`, group environment, `JET_PWR=1e+43`,
  `JET_SPD=0.1`, and `tstop=15330.06968940`;
- remote tabulated group asset passed row/column/radius checks;
- PLUTO, `jet-setup`, `setup-problem`, and AGN modulefile paths existed;
- `module purge` plus `intel/18.0.1.163`, `impi/2018.1.163`,
  `hdf5/1.12.1p`, and `zfp/0.5.5` loaded successfully;
- `mpicc` and `mpirun` were available;
- the no-overwrite workdir was absent;
- queue `normal` was enabled/started and allowed `48:00:00` walltime.

Remote preflight transcript:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/remote_logs/submission_preflight_2026-07-07_g_lo.txt
```

## Submitted Job

PBS job:

```text
751105.kunanyi-ohpc
```

Job name:

```text
g_lo_endpt
```

State at stop:

```text
Q
```

Expected stdout/stderr:

```text
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.out
/u/bwbrook/codex_kunanyi/goal037_g_lo_endpoint_oriented_production/g_lo_endpoint_oriented_production.err
```

Expected workdir:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles
```

The terminal helper reported status `141` after `qsub` and `qstat` had already
printed the queued-state proof. This is retained as an operational helper
caveat; the PBS submission proof itself showed job `751105.kunanyi-ohpc` in
state `Q`.

## Review Assets

Machine-readable assets:

```text
docs/science/assets/g_lo_endpoint_oriented_production_2026-07-07/
```

Key files:

- `asset_source_search.csv`;
- `restored_asset_manifest.csv`;
- `asset_validation.csv`;
- `g_lo_config_audit.csv`;
- `wrapper_contract_audit.csv`;
- `remote_preflight_status.csv`;
- `staged_file_hashes.csv`;
- `submission_summary.csv`;
- `g_lo_endpoint_oriented_production_metadata.json`.

## Boundary And Next Step

No polling, retrieval, checkpoint review, post-processing, XRAiSE/PRAiSE/radio
/cavity/source-age work, C-HI/C-LO rerun, G-LO product generation,
scientific-default change, commit, push, cleanup, Stas/Patrick contact, or
`agent_comms` edit occurred.

Next step: wait for Barry's PBS completion email. Then run a bounded retrieval
and checkpoint/endpoint review goal for job `751105.kunanyi-ohpc`, retrieving
compact scheduler/stdout/stderr/catalogue evidence only and no bulky HDF5,
`data.*`, or particle payloads.

## Completion Review - 2026-07-10

Job `751105.kunanyi-ohpc` ended with `Exit_status=271` after
`resources_used.walltime=48:01:33` against a `48:00:00` request. `markers/DONE`
is absent and `markers/FAILED` is present. The run did not reach the 50 Myr
endpoint.

Critical restart guardrail:

- `data.0003.dbl.h5` is the latest inventoried double filename, but it is only
  `44,741,404,952` bytes and has neither a matching XMF nor a `dbl.h5.out` row.
  It is an incomplete termination artifact and is not restartable.
- The latest validated fluid restart checkpoint is `data.0002.dbl.h5`,
  catalogue index `2`, at code time `3065.935`; it is `67,318,639,276` bytes and
  has matching `data.0002.dbl.xmf` metadata.
- `particles.1000.dbl` is the candidate paired particle file because its remote
  mtime is 44 seconds after the safe HDF5 file. This is an mtime-only pairing
  and requires explicit content and restart-pair validation before submission.
- The latest complete float output is `data.0014.flt.h5` at code time
  `4292.332`. It records about `13.99971 Myr` of progress but does not replace
  the double-HDF5 restart surface.

Restarting from index `2` preserves about `9.99974 Myr` / `19.99949%` of the
endpoint. Relative to the latest complete float output, it rolls back
`1226.397` code-time units, about `3.99997 Myr` or `7.99994` endpoint percentage
points.

The mtime evidence is more important than the nominal 30-minute shutdown
buffer: `data.0003.dbl.h5` stopped changing about `10:22:34` after job start and
about `37:38:48` before wrapper termination. This is consistent with a stall in
the regular 15 Myr collective double-HDF5 write. A modestly shorter
`-maxtime` would not have recovered this run because PLUTO could not return to
its wall-clock check while blocked in output.

The boldest defensible continuation is one isolated 64-node / 1792-rank /
48-hour restart from index `2`, after the particle pairing passes explicit
preflight, with an output-stall watchdog that terminates a non-progressing
collective write early. Retain the established 5 Myr double-output cadence and
the `47.5` hour PLUTO guard for this next run; changing cadence or shaving the
end buffer does not address the observed 37-hour I/O stall.
