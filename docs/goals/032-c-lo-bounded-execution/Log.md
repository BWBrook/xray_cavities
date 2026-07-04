# Goal 032 Log - Bounded C-LO Execution Submission

Date: 2026-07-03

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `703f4bd`.
- Git status at start: `## main...origin/main`.
- Fast-forward check: `git pull --ff-only` reported already up to date.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 032 is an execution submission packet only. It may stage and submit at
most one bounded `C-LO` PBS job, then must stop once PBS reports the job as
queued or running. It does not authorize `G-LO`, follow-on jobs, output
retrieval, finalizers, post-processing, XRAiSE, PRAiSE, radio or cavity
extraction, source-age products, endpoint comparison products, observables,
scientific-default changes, commits, pushes, cleanup, Stas/Patrick contact, or
`agent_comms` edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 031 science note, Goal log, and compact assets, especially
  `restored_asset_manifest.csv`, `asset_backed_c_lo_config_audit.csv`,
  `remote_preflight_status.csv`, and `next_step_recommendation.csv`.
- Goal 030 preflight wrapper contract and focused tests:
  `scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs` and
  `tests/test_c_lo_config_asset_preflight_contract.py`.
- `scripts/science/render_three_case_configs.py` as needed to regenerate the
  asset-backed `C-LO` config.
- C-HI production/staging patterns only enough to preserve the established
  startup/checkpoint contract:
  `scripts/kunanyi/jet_setup_production_template.pbs`,
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh`,
  `scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs`, and the later
  C-HI full-grid startup/restart/continue wrappers.

## Local Work Performed

- Reconfirmed the ignored restored Stewart cluster asset exists at
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`.
- Reconfirmed its SHA-256 as
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa` and
  row count as `4000`.
- Reconfirmed Git ignores the raw restored asset through `.gitignore:14:env/`.
- Regenerated an asset-backed `C-LO` particles config into the ignored build
  path
  `build/science/c_lo_bounded_execution_2026-07-03/rendered_c_lo_config`
  using `--require-assets --check-local-assets`.
- Added `scripts/kunanyi/c_lo_bounded_execution.pbs`, a bounded wrapper that
  targets only `C-LO`/`particles`, uses the staged asset-backed config, sets
  the run root to
  `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution`,
  preserves the AGN Intel/IMPI stack, and delegates to the established
  `jet_setup_production_template` contract.
- Used the accepted C-HI startup/checkpoint pattern for resources:
  `select=80:ncpus=28:mpiprocs=28`, walltime `04:00:00`, and
  `PLUTO_MAXTIME_HOURS=3.5`. This is a bounded startup/checkpoint submission,
  not a 48-hour continuation or broad production campaign.
- Added focused wrapper tests in
  `tests/test_c_lo_bounded_execution_wrapper.py`.

## Local Validation

Local validation passed:

- `bash -n scripts/kunanyi/c_lo_bounded_execution.pbs`
- `bash -n scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs`
- `uv run pytest tests/test_c_lo_bounded_execution_wrapper.py tests/test_c_lo_config_asset_preflight_contract.py -q`
  (`7 passed`).
- `jq -e` validation of the ignored render validation JSON for `C-LO`,
  `JET_PWR = 1e+43`, `JET_SPD = 0.1`, and
  `tstop = 15330.06968940`.
- SHA-256 validation for the ignored restored Stewart CSV.

## Remote Staging And Submission

Authorized stage root:
`/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution`.

Authorized run root:
`/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution`.

The authorized Chrome/Open OnDemand route was used to refresh the TPAC SSH
selector. The portal reported a live 5-minute window closing at
`Fri Jul 3 14:41:28 2026` Hobart time. Safari was not used.

Staged files:

- `rendered_c_lo_config/`
- `c_lo_bounded_execution.pbs`
- `jet_setup_production_template_latest.pbs`

Remote pre-submission checks passed:

- Staged local/remote SHA-256 verification for wrapper, production template,
  compact config files, and the restored Stewart CSV.
- Remote `bash -n` for the wrapper and production template.
- Remote config validation for `C-LO`, `JET_PWR = 1e+43`,
  `JET_SPD = 0.1`, `tstop = 15330.06968940`, Stewart asset SHA-256
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`,
  and `4000` asset rows.
- Run-root no-overwrite check for
  `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles`.
- Remote PLUTO, `jet-setup`, setup-problem, and AGN modulefile path checks.
- Runtime module loading after `module purge`: `intel/18.0.1.163`,
  `impi/2018.1.163`, `hdf5/1.12.1p`, and `zfp/0.5.5`.

Exactly one PBS job was submitted:

- Job id: `750065.kunanyi-ohpc`.
- Job name: `c_lo_bound`.
- PBS state at stop: `Q`.
- Queue: `normal`.
- Resources: `select=80:ncpus=28:mpiprocs=28`, `ncpus=2240`,
  `mpiprocs=2240`, `mem=128gb`, walltime `04:00:00`.
- Stdout:
  `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.out`.
- Stderr:
  `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.err`.
- Submission/preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/remote_logs/submission_preflight_2026-07-03.txt`.

The remote command reported `SUBMITTED_WAITING_PBS_COMPLETION=pass`.

## Retrieval Instructions

Do not poll or retrieve until Barry reports the PBS completion email, or X-ray
Cavities explicitly authorizes a re-check.

After completion authorization, the next agent should inspect only the Goal
032 paths first:

- `qstat -x -f 750065.kunanyi-ohpc`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.out`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.err`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/remote_logs/submission_preflight_2026-07-03.txt`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/problem/outputs/`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/markers/`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/job_logs/`

This production-template submission is run-root/log/marker based; no compact
science product or review archive is expected from Goal 032 itself.

## Decision

Status:
`submitted_waiting_pbs_completion`.

Decision label:
`C_LO_BOUNDED_EXECUTION_SUBMITTED_WAITING_PBS_COMPLETION`.

## Final Validation

Final local closeout validation is recorded in the exchange log and included:
wrapper syntax checks, focused wrapper tests, config/asset validation,
`git diff --check`, and targeted unresolved-marker scans.

## Boundary Confirmation

No `G-LO` job, retry, follow-on PBS job, polling after queued verification,
retrieval, finalizer, post-processing, XRAiSE/PRAiSE/radio/cavity extraction,
source-age product, endpoint comparison product, observable generation,
scientific-default change, environment substitution, source-age substitution,
commit, push, cleanup, Stas/Patrick contact, `agent_comms` edit, or
accepted-asset overwrite occurred.

## Completion Retrieval - 2026-07-04

Barry reported the PBS completion email for `750065.kunanyi-ohpc` with
`Exit_status=0`, `resources_used.walltime=03:34:35`,
`resources_used.cput=99:36:16`, `resources_used.ncpus=2240`,
`resources_used.mem=7188268kb`, and `resources_used.vmem=26357460kb`.

This authorized compact completion retrieval and inspection only. No new PBS
job, retry, continuation, polling loop, PLUTO rerun, finalizer,
post-processing, XRAiSE, PRAiSE, radio, cavity extraction, source-age product,
endpoint comparison product, observable generation, bulky HDF5 retrieval,
scientific-default change, commit, push, cleanup, or `agent_comms` edit was
authorized or performed.

### Completion Evidence Read And Retrieved

Remote read-only checks used the repo-local Kunanyi helpers. The existing
TPAC SSH route was live; no Safari route was used.

Retrieved compact text evidence into
`docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/`:

- `c_lo_bounded_execution.out`
- `c_lo_bounded_execution.err`
- `submission_preflight_2026-07-03.txt`
- `job_logs/artifact_manifest.750065.kunanyi-ohpc.txt`
- `job_logs/source_revisions.txt`
- `job_logs/pbs_nodefile.750065.kunanyi-ohpc.txt`
- `job_logs/intelmpi_machinefile.750065.kunanyi-ohpc.txt`

No HDF5 files, particle payloads, or bulky output directories were retrieved.
The retrieved text bundle totals `494973` bytes.

### Remote Completion Summary

- Final scheduler state: `F`.
- Final scheduler exit: `Exit_status = 0`.
- qstat caveat: `Stageout_status = 1`, while requested stdout/stderr and the
  submission transcript were nevertheless present at staged paths and
  retrieved.
- Stdout markers: `RUN_KIND=fresh`, `RUN_ARGS=-i pluto.ini -e environment.ini
  -maxtime 3.5`, `MPI_EXIT_CODE=0`, and
  `JOB_END=2026-07-03T08:11:42Z`.
- Stderr: one line from `setup-problem` reporting `git: command not found`.
  This leaves source Git metadata unavailable in `source_revisions.txt`; staged
  config hashes and execution logs remain available.
- Remote run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles`.
- Remote output volume: `482G`.
- Marker: `markers/DONE` present.
- HDF5 outputs: `10` total, including `7` `flt.h5` and `3` `dbl.h5`.
- Latest HDF5 files: `data.0006.flt.h5` and `data.0002.dbl.h5`.
- Latest reported HDF5 output time: `1.533095e+03` code-time units at step
  `5920`.
- Particle text outputs: `502`, through `particles.0501.dbl`.

### Completion Package

Added science note:
`docs/science/c_lo_bounded_execution_completion_2026-07-04.md`.

Added asset bundle:
`docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/`.

Machine-readable assets:

- `qstat_final.csv`
- `remote_log_inventory.csv`
- `run_output_inventory.csv`
- `completion_summary.csv`
- `next_step_recommendation.csv`
- `c_lo_bounded_execution_completion_metadata.json`
- `remote_logs/`

### Completion Decision

Status:
`complete_execution_checkpoint_surface_green`.

Decision label:
`C_LO_BOUNDED_EXECUTION_CHECKPOINT_SURFACE_GREEN`.

This is green as a bounded execution/checkpoint surface, not as a final 50 Myr
endpoint product. The next recommended goal is
`bounded_c_lo_checkpoint_inspection_and_continuation_decision`.
