# Goal 035 Log - C-LO Endpoint-Oriented Continuation

Date: 2026-07-05

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `af8c5f3`.
- Git status at start: `## main...origin/main`.
- Fast-forward state: local checkout already matched `origin/main` at
  `af8c5f3`.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 035 authorizes one endpoint-oriented C-LO continuation submission if the
Goal 034 restart gate and queue/resource gate are clean. It does not authorize
`G-LO`, C-LO post-processing, endpoint observables, XRAiSE/PRAiSE, radio or
cavity workflows, source-age products, broad continuation ladders,
scientific-default changes, commits, pushes, cleanup, or `agent_comms` edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 034 log, exchange log, completion science note, and compact completion
  assets, especially `completion_summary.csv`,
  `run_output_inventory_summary.csv`, `qstat_final.csv`,
  `next_step_recommendation.csv`, and
  `c_lo_endpoint_or_continuation_completion_metadata.json`.
- Goal 034 wrapper and focused test:
  `scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` and
  `tests/test_c_lo_endpoint_or_continuation_wrapper.py`.
- Production template:
  `scripts/kunanyi/jet_setup_production_template.pbs`.
- Restored C-LO config bundle from Goal 031, only enough to confirm the
  endpoint target and Stewart asset contract.

## Restart And Queue Gate

The first live helper attempt found the TPAC selector expired. The authorized
Chrome/Open OnDemand route was used only for the selector, and the portal
reported a live window closing at `Sun Jul 5 22:19:11 2026`. Safari was not
used.

Live read-only Kunanyi evidence from the Goal 034 run root:

- run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2/C-LO/particles`;
- `markers/DONE` present;
- `markers/FAILED` absent;
- latest `dbl.h5.out` row:
  `6 4.930755e+03 2.678869e-01 18546 single_file little rho vx1 vx2 vx3 prs tr1`;
- latest `flt.h5.out` row:
  `19 4.930755e+03 2.678869e-01 18546 single_file little rho vx1 vx2 vx3 prs tr1`;
- required restart surfaces present:
  `data.0006.dbl.h5`, `data.0006.dbl.xmf`, and `particles.1611.dbl`;
- required catalogues/logs present:
  `dbl.h5.out`, `flt.h5.out`, `restart.out`, and `grid.out`;
- endpoint target remains `15330.06968940` code-time units;
- latest compact catalogue time is `4930.755`, or `0.32163944` of endpoint.

Queue/resource evidence:

- `qstat -Qf normal` reports `resources_max.walltime = 48:00:00`.
- The `normal` queue was enabled and started.
- The previous 64-node Goal 034 rung advanced by about `1660.2` code-time
  units over a `3.5` hour PLUTO maxtime window. The remaining code-time span
  to endpoint is about `10399.31468940`, implying about `21.92` PLUTO hours at
  the recent restart rate.

Initial decision before the amendment was a single endpoint-oriented
`24:00:00` walltime job with `PLUTO_MAXTIME_HOURS=23.5`, while retaining the
accepted 64-node restart scale because the 80-node restart-stall caveat remains
unresolved.

Barry/X-ray Cavities then amended Goal 035 before `qsub`: Kunanyi generally
accepts jobs up to 48 hours, 64 nodes is the preferred restart scale, and the
new default ambition is one 64-node endpoint-oriented continuation up to the
queue ceiling if scheduler preflight is clean. The wrapper and decision assets
were updated accordingly to `walltime=48:00:00` and
`PLUTO_MAXTIME_HOURS=47.5`.

## Local Work

- Added `scripts/kunanyi/c_lo_endpoint_oriented_continuation.pbs`.
- Added focused wrapper tests in
  `tests/test_c_lo_endpoint_oriented_continuation_wrapper.py`.
- Added compact Goal 035 science note/assets under:
  `docs/science/c_lo_endpoint_oriented_continuation_2026-07-05.md` and
  `docs/science/assets/c_lo_endpoint_oriented_continuation_2026-07-05/`.

## Validation

- Local focused wrapper tests:
  `uv run pytest tests/test_c_lo_endpoint_oriented_continuation_wrapper.py tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed: `16 passed in 0.02s`.
- Local wrapper/template syntax:
  `bash -n scripts/kunanyi/c_lo_endpoint_oriented_continuation.pbs` and
  `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for
  `docs/science/assets/c_lo_endpoint_oriented_continuation_2026-07-05/c_lo_endpoint_oriented_continuation_metadata.json`.
- CSV parse/expected-column checks passed for the Goal 035 asset tables.
- `git diff --check` passed before remote staging.

## Remote Staging And Submission

Remote stage root:

```text
/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation
```

Remote endpoint-oriented run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation
```

Staged surfaces:

- `scripts/kunanyi/c_lo_endpoint_oriented_continuation.pbs`;
- `scripts/kunanyi/jet_setup_production_template.pbs` as
  `jet_setup_production_template_latest.pbs`;
- rendered C-LO config bundle under
  `rendered_c_lo_config/C-LO/particles`;
- verified Stewart CSV
  `tabulated_cosmo_002003.csv`.

Remote SHA-256 gates passed:

- wrapper:
  `44d7b49d62ec1d1e8fb3933db078cd2794bc68d55d97e3eeb66ff1a04e9f71ff`;
- production template:
  `9085e64fe1ca58010909790f3b6fa01abed7962c752d7d106f260bd3403356fc`;
- `case_manifest.json`:
  `019cb4eda5b9d1009d4a73e57a7b1ac5ca6f15b24eaf583a4b480b5d6a593c3b`;
- `pluto.ini`:
  `3c6b127b716f3c8d112a5cccd37f42d13aee10962e869a6d1ac0e8b5e3485341`;
- `environment.ini`:
  `3b49690db1185c70742400925fb19f3f51abead2967f0e46a732b9734c86630b`;
- `definitions_overrides.json`:
  `a65fbd272dd4d4f49d02efc7b54b8cf26f2356e6dd5bcfcaf402cf00cc48660c`;
- Stewart CSV:
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`.

Remote wrapper/template `bash -n` passed. The remote wrapper contract checked
`walltime=48:00:00` and `PLUTO_MAXTIME_HOURS=47.5`. `qstat -Qf normal`
confirmed the queue walltime ceiling `48:00:00`.

The prepared Goal 035 run root copied compact catalogues/logs and symlinked
large restart payloads from the accepted Goal 034 surface:

- copied: `dbl.h5.out`, `flt.h5.out`, `restart.out`, `grid.out`,
  `data.0006.dbl.xmf`;
- symlinked: `data.0006.dbl.h5`, `particles.1611.dbl`.

This avoids mutating the accepted Goal 034 output catalogues while still
providing the restart payloads needed by the production template.

The final remote gate submitted exactly one PBS job:

- job id: `750947.kunanyi-ohpc`;
- job name: `c_lo_endpt`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `walltime=48:00:00`;
- stdout:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.out`;
- stderr:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.err`;
- preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_preflight_2026-07-05_endpoint_oriented.txt`;
- submission record:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_record_2026-07-05_endpoint_oriented.txt`.

The remote helper returned `141` after emitting the qstat record, consistent
with a late pipe/terminal condition rather than a qsub failure. The qstat
record in the same command showed job state `R`, so the PBS stop rule was
invoked immediately. No further remote polling or retrieval was performed.

## Final Status

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_RESTART_GATE_CLEAN_ENDPOINT_ORIENTED_48H_CONTINUATION_SUBMITTED`.

No post-submission polling, retrieval, post-processing, endpoint products,
`G-LO`, scientific-default changes, commits, pushes, cleanup, `agent_comms`
edits, or accepted-asset overwrites occurred.

## Completion Retrieval - 2026-07-07

Barry reported the PBS completion email for `750947.kunanyi-ohpc`:
`Exit_status=0`, `resources_used.walltime=24:47:37`,
`resources_used.cput=692:21:26`, `resources_used.ncpus=1792`,
`resources_used.mem=9891168kb`, and `resources_used.vmem=27596320kb`.

Repo-local `AGENTS.md`, this Goal log, the exchange log, current status, the
Goal 035 wrapper, and focused wrapper test were re-read before retrieval. The
local checkout remained on `main` at `af8c5f3` with the expected dirty Goal 035
submission packet.

The first helper access was refreshed through the authorized Chrome/Open
OnDemand route only. The selector page reported a live SSH window closing at
`Tue Jul 7 11:16:23 2026`; Safari was not used.

Retrieved compact evidence only:

- final scheduler record:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/qstat_final_2026-07-07.txt`;
- stdout:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.out`;
- stderr:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.err`;
- submission preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_preflight_2026-07-05_endpoint_oriented.txt`;
- compact run-root inventories and summaries generated under:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/`.

No HDF5, `data.*`, or particle payload files were copied locally.

## Completion Evidence

`qstat -x -f 750947.kunanyi-ohpc` shows:

- job name: `c_lo_endpt`;
- final state: `F`;
- `Exit_status=0`;
- `Stageout_status=1`;
- resources used: `walltime=24:47:37`, `cput=692:21:26`,
  `ncpus=1792`, `mem=9891168kb`, `vmem=27596320kb`;
- requested resources: `select=64:ncpus=28:mpiprocs=28`,
  `walltime=48:00:00`.

Compact endpoint evidence from the run root:

- `markers/DONE` present;
- `markers/FAILED` absent;
- stdout contains `MPI_EXIT_CODE=0`;
- stderr is non-empty only because
  `/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem` reported
  `git: command not found`;
- latest `dbl.h5.out` row:
  `13 1.533007e+04 2.422549e-03 57029 single_file little rho vx1 vx2 vx3 prs tr1`;
- latest `flt.h5.out` row:
  `53 1.533007e+04 2.422549e-03 57029 single_file little rho vx1 vx2 vx3 prs tr1`;
- latest inventoried double checkpoint: `data.0013.dbl.h5`;
- latest inventoried float output: `data.0053.flt.h5`;
- latest inventoried particle restart: `particles.5003.dbl`;
- remote output inventory: `41` HDF5 files, `3392` particle restart files,
  and remote output directory size `1.9T`.

The configured endpoint target remains `15330.06968940` code-time units. The
latest compact catalogue time is `15330.07`, giving endpoint fraction
`1.00000002026` and remaining gap `-0.000310600000375`. Within compact
catalogue precision, the endpoint target is reached.

## Completion Package

Added completion science note:

```text
docs/science/c_lo_endpoint_oriented_continuation_completion_2026-07-07.md
```

Added completion asset bundle:

```text
docs/science/assets/c_lo_endpoint_oriented_continuation_completion_2026-07-07/
```

Key assets:

- `qstat_final.csv`;
- `completion_summary.csv`;
- `run_output_inventory.csv`;
- `run_output_inventory_summary.csv`;
- `remote_log_inventory.csv`;
- `next_step_recommendation.csv`;
- `c_lo_endpoint_oriented_continuation_completion_metadata.json`;
- `local_asset_manifest.sha256`;
- compact `remote_logs/`.

## Completion Status

Status: `complete_endpoint_review`.

Decision label:
`C_LO_ENDPOINT_ORIENTED_RUN_REACHED_ENDPOINT_COMPACT_EVIDENCE_GREEN`.

The next recommended goal is a bounded C-LO endpoint post-processing preflight
or inspection packet after X-ray Cavities accepts this endpoint-status package.
No C-LO post-processing, XRAiSE, PRAiSE, radio, cavity, source-age,
endpoint-comparison, observable workflow, new PBS submission, retry,
continuation, polling loop, bulky local retrieval, `G-LO`, scientific-default
change, commit, push, cleanup, Stas/Patrick contact, `agent_comms` edit, or
accepted-asset overwrite occurred.
