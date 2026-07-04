# 2026-07-03 - Bounded C-LO Execution Submission

Goal 032 prepared, staged, and submitted the first bounded `C-LO` execution
job after the Goal 031 Stewart asset restore and clean config/preflight gate.

## Result

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_BOUNDED_EXECUTION_SUBMITTED_WAITING_PBS_COMPLETION`.

Exactly one PBS job was submitted:

```text
Job id: 750065.kunanyi-ohpc
Job name: c_lo_bound
State at stop: Q
Queue: normal
Resources: select=80:ncpus=28:mpiprocs=28, walltime=04:00:00
```

The PBS stop rule is now active: do not poll or retrieve until Barry reports
the PBS completion email, or X-ray Cavities explicitly authorizes a re-check.

## Completion Retrieval - 2026-07-04

Barry reported the PBS completion email for `750065.kunanyi-ohpc`, and Goal
032 retrieved compact completion evidence only.

Completion status:
`complete_execution_checkpoint_surface_green`.

Completion decision label:
`C_LO_BOUNDED_EXECUTION_CHECKPOINT_SURFACE_GREEN`.

Final scheduler/resource evidence:

```text
Job id: 750065.kunanyi-ohpc
Job name: c_lo_bound
Final state: F
Exit_status: 0
resources_used.walltime: 03:34:35
resources_used.cput: 99:36:16
resources_used.ncpus: 2240
resources_used.mem: 7188268kb
resources_used.vmem: 26357460kb
```

Compact retrieved evidence:

- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/c_lo_bounded_execution.out`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/c_lo_bounded_execution.err`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/submission_preflight_2026-07-03.txt`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/job_logs/artifact_manifest.750065.kunanyi-ohpc.txt`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/job_logs/source_revisions.txt`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/job_logs/pbs_nodefile.750065.kunanyi-ohpc.txt`
- `docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/remote_logs/job_logs/intelmpi_machinefile.750065.kunanyi-ohpc.txt`

Key outcome:

- `c_lo_bounded_execution.out` reports `MPI_EXIT_CODE=0`,
  `RUN_KIND=fresh`, `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 3.5`,
  and `JOB_END=2026-07-03T08:11:42Z`.
- `markers/DONE` exists remotely.
- Remote output volume is `482G`.
- HDF5 output inventory reports `10` HDF5 files: `7` `flt.h5` and `3`
  `dbl.h5`.
- The latest HDF5 output time recorded in `dbl.h5.out` and `flt.h5.out` is
  `1.533095e+03` code-time units at step `5920`.
- Particle text outputs are present through `particles.0501.dbl`.

Important caveats:

- This is a successful bounded execution/checkpoint surface, not a final
  50 Myr endpoint product.
- qstat reports `Stageout_status=1`, but requested stdout/stderr and the
  submission transcript were present and retrieved.
- stderr contains one `setup-problem` warning that `git` was not found, so
  source Git metadata is unavailable in `source_revisions.txt`.
- No bulky HDF5 or particle payload files were copied locally.

New science note:
`docs/science/c_lo_bounded_execution_completion_2026-07-04.md`.

New compact asset bundle:
`docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/`.

Recommended next goal:
`bounded_c_lo_checkpoint_inspection_and_continuation_decision`.

## Local Packet

Added:

- `scripts/kunanyi/c_lo_bounded_execution.pbs`
- `tests/test_c_lo_bounded_execution_wrapper.py`
- `docs/goals/032-c-lo-bounded-execution/Log.md`

Updated:

- `docs/exchange/current_status.md`

The wrapper targets only `C-LO`/`particles`, uses the Goal 031 restored Stewart
cluster `002_003` asset through an asset-backed rendered config, preserves the
AGN Intel/IMPI module stack, and delegates to the existing production-template
contract. The raw Stewart CSV remains ignored under `env/` and was not added to
Git.

## Remote Staging

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution
```

Run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution
```

Staged:

- `rendered_c_lo_config/`
- `c_lo_bounded_execution.pbs`
- `jet_setup_production_template_latest.pbs`

Remote pre-submission checks passed: SHA-256 verification, remote `bash -n`,
config and Stewart asset validation, run-root no-overwrite check, PLUTO and
`jet-setup` source path checks, setup-problem/modulefile checks, and module
loading after `module purge`.

The staged Stewart asset SHA-256 remained:

```text
30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa
```

## Expected Completion Evidence

After Barry reports the completion email, inspect only the Goal 032 paths
first:

- `qstat -x -f 750065.kunanyi-ohpc`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.out`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/c_lo_bounded_execution.err`
- `/u/bwbrook/codex_kunanyi/goal032_c_lo_bounded_execution/remote_logs/submission_preflight_2026-07-03.txt`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/problem/outputs/`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/markers/`
- `/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles/job_logs/`

This submission uses the production-template run-root/log/marker contract. It
does not create a Goal 032 science-product archive by itself.

## Validation

Validation passed:

- `bash -n scripts/kunanyi/c_lo_bounded_execution.pbs`
- `bash -n scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs`
- `uv run pytest tests/test_c_lo_bounded_execution_wrapper.py tests/test_c_lo_config_asset_preflight_contract.py -q`
  (`7 passed`).
- Asset-backed rendered config JSON check for `C-LO`, `JET_PWR = 1e+43`,
  `JET_SPD = 0.1`, and `tstop = 15330.06968940`.
- SHA-256 validation for
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`.
- `git diff --check`.
- Targeted unresolved-marker scan over the Goal 032 log, this exchange log,
  and current status.

## Boundary

No `G-LO`, retries, follow-on jobs, post-queue polling, retrieval, finalizer,
post-processing, XRAiSE/PRAiSE/radio/cavity extraction, source-age products,
endpoint comparison products, observables, scientific-default changes,
environment substitutions, source-age substitutions, commits, pushes, cleanup,
Stas/Patrick contact, `agent_comms` edits, or accepted-asset overwrites
occurred.
