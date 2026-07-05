# Goal 033 Log - C-LO Checkpoint Continuation

Date: 2026-07-04

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `870dbbb`.
- Git status at start: `## main...origin/main`.
- Fast-forward check: `git pull --ff-only` reported already up to date.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 033 authorizes checkpoint inspection and, if clean, exactly one bounded
`C-LO` continuation PBS submission. It does not authorize `G-LO`, multiple
jobs, retries, polling after queued/running verification, bulky output
retrieval, finalizers, post-processing, XRAiSE, PRAiSE, radio or cavity
extraction, observables, endpoint comparison products, scientific-default
changes, commits, pushes, cleanup, Stas/Patrick contact, or `agent_comms`
edits.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 032 completion science note, Goal log, exchange log, and compact
  assets, especially `completion_summary.csv`, `run_output_inventory.csv`,
  `remote_log_inventory.csv`, and `next_step_recommendation.csv`.
- Goal 032 wrapper and tests:
  `scripts/kunanyi/c_lo_bounded_execution.pbs` and
  `tests/test_c_lo_bounded_execution_wrapper.py`.
- Production/restart patterns:
  `scripts/kunanyi/jet_setup_production_template.pbs`,
  `scripts/kunanyi/c_hi_fullgrid_agn_impi_bounded_restart.pbs`,
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_bounded_restart.sh`,
  `scripts/kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs`, and
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_restart_ladder.sh`.
- C-HI restart evidence showing `64` nodes / `1792` ranks as the clean restart
  scale and `80` nodes / `2240` ranks as a reproducible HDF5 restart-stall
  boundary.

## Checkpoint Inspection

The TPAC SSH selector had expired during the first remote attempt. The
authorized Chrome/Open OnDemand route was used, and the portal reported a live
window closing at `Sat Jul 4 22:41:44 2026` Hobart time. Safari was not used.

Read-only checkpoint inspection of:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles
```

found:

- `markers/DONE` present and `markers/FAILED` absent.
- Latest `dbl.h5.out` record:
  `2 1.533095e+03 2.702729e-01 5920`.
- Latest `flt.h5.out` record:
  `6 1.533095e+03 2.702729e-01 5920`.
- Restart file present:
  `data.0002.dbl.h5`, size `67318639276` bytes.
- Matching XMF present:
  `data.0002.dbl.xmf`.
- Latest particle restart surface present:
  `particles.0501.dbl`, size `2808546` bytes.
- `restart.out`, `dbl.h5.out`, and `flt.h5.out` present.
- The proposed continuation workdir did not exist.
- Required PLUTO, `jet-setup`, and AGN modulefile paths exist.

`h5dump` was not available on the login path, so a header-only probe was
skipped rather than substituting a heavier read.

## Local Work

- Added `scripts/kunanyi/c_lo_checkpoint_continuation.pbs`.
- Added focused wrapper tests in
  `tests/test_c_lo_checkpoint_continuation_wrapper.py`.
- Rendered an asset-backed `C-LO` config into ignored build path
  `build/science/c_lo_checkpoint_continuation_2026-07-04/rendered_c_lo_config`
  using `--require-assets --check-local-assets`.
- Confirmed the restored Stewart CSV and the build-copy of it are ignored by
  Git.
- Added compact local Goal 033 note/assets under:
  `docs/science/c_lo_checkpoint_continuation_decision_2026-07-04.md` and
  `docs/science/assets/c_lo_checkpoint_continuation_2026-07-04/`.

## Local Validation Before Submission

Passed:

```bash
uv run pytest tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q
```

Result: `8 passed`.

Passed:

```bash
bash -n scripts/kunanyi/c_lo_checkpoint_continuation.pbs
bash -n scripts/kunanyi/jet_setup_production_template.pbs
```

Passed JSON parse checks for the rendered config:

```bash
uv run python -m json.tool build/science/c_lo_checkpoint_continuation_2026-07-04/rendered_c_lo_config/C-LO/particles/render_validation.json
uv run python -m json.tool build/science/c_lo_checkpoint_continuation_2026-07-04/rendered_c_lo_config/C-LO/particles/case_manifest.json
```

## Remote Staging And Submission

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal033_c_lo_checkpoint_continuation
```

Continuation run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation
```

Staged files:

- `c_lo_checkpoint_continuation.pbs`
- `jet_setup_production_template_latest.pbs`
- `rendered_c_lo_config/`

Remote preflight passed:

- SHA-256 verification for staged wrapper, template, config files, and Stewart
  `tabulated_cosmo_002003.csv`.
- Remote `bash -n` for wrapper and template.
- Source checkpoint marker/catalogue/restart/particle checks.
- Isolated continuation workdir preparation without overwriting Goal 032.
- AGN Intel/IMPI/HDF5 module stack load.

Prepared continuation workdir:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO/particles
```

The workdir contains copied compact config/catalogue files and symlinks to the
accepted Goal 032 `data.0002.dbl.h5`, `data.0002.dbl.xmf`, and
`particles.0501.dbl` restart surfaces.

Exactly one PBS job was submitted:

- Job id: `750931.kunanyi-ohpc`.
- Job name: `c_lo_cont`.
- PBS state at stop: `Q`.
- Queue: `normal`.
- Resources: `select=64:ncpus=28:mpiprocs=28`, walltime `04:00:00`.
- Stage stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal033_c_lo_checkpoint_continuation/c_lo_checkpoint_continuation.out`
  and
  `/u/bwbrook/codex_kunanyi/goal033_c_lo_checkpoint_continuation/c_lo_checkpoint_continuation.err`.
- Submission transcript:
  `/u/bwbrook/codex_kunanyi/goal033_c_lo_checkpoint_continuation/remote_logs/submission_preflight_2026-07-04.txt`.

## Final Status

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_CHECKPOINT_SURFACE_CLEAN_CONTINUATION_SUBMITTED`.

Stop rule is active. Do not poll or retrieve until Barry reports the PBS
completion email for `750931.kunanyi-ohpc`, or X-ray Cavities explicitly
authorizes a re-check.

Boundary confirmation: no post-queue polling, retrieval, bulky output copying,
finalizer, science post-processing, endpoint products, `G-LO`, scientific
default change, commit, push, cleanup, Stas/Patrick contact, `agent_comms`
edit, or accepted-asset overwrite occurred.

## Continuation Completion Retrieval - 2026-07-05

Barry reported the PBS completion email for `750931.kunanyi-ohpc`:

```text
Job Name:   c_lo_cont
Exit_status=0
resources_used.cpupercent=2820
resources_used.cput=98:54:40
resources_used.mem=9870960kb
resources_used.ncpus=1792
resources_used.vmem=27588972kb
resources_used.walltime=03:33:08
```

The continuation closeout stayed in retrieval/checkpoint-review mode only.
No new PBS job, retry, continuation, polling loop, science post-processing,
bulky HDF5/particle retrieval, `G-LO` work, scientific-default change, commit,
push, cleanup, or `agent_comms` edit occurred.

Compact evidence retrieved or reconstructed from the already-authorized Goal
033 stage/run paths:

- `qstat -x -f 750931.kunanyi-ohpc`, saved as
  `docs/science/assets/c_lo_checkpoint_continuation_completion_2026-07-05/remote_logs/qstat_final_2026-07-05.txt`.
- Stage stdout:
  `remote_logs/c_lo_checkpoint_continuation.out`.
- Stage stderr:
  `remote_logs/c_lo_checkpoint_continuation.err`; remote size was `0` bytes
  and local SHA-256 is the empty-file hash.
- Submission preflight transcript:
  `remote_logs/submission_preflight_2026-07-04.txt`.
- Compact run inventory and completion tables under
  `docs/science/assets/c_lo_checkpoint_continuation_completion_2026-07-05/`.

Completion review evidence:

- `qstat` final state: `F`.
- `qstat` `Exit_status=0`.
- `qstat` `Stageout_status=1`; retained as a scheduler caveat.
- `markers/DONE` present and `markers/FAILED` absent.
- wrapper stdout reports `MPI_EXIT_CODE=0`.
- stderr is empty.
- latest `dbl.h5.out` row:
  `4 3.270555e+03 2.680126e-01 12349`, with latest remote double checkpoint
  `data.0004.dbl.h5`.
- latest `flt.h5.out` row:
  `12 3.270555e+03 2.680126e-01 12349`, with latest remote float output
  `data.0012.flt.h5`.
- latest remote particle restart inventory row:
  `particles.1068.dbl`.
- remote inventory count:
  `8` HDF5 files and `567` particle restart files, inventoried only by path,
  role, and size; none were copied locally.

Status:
`complete_checkpoint_review`.

Decision label:
`C_LO_CONTINUATION_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

Interpretation:
the continuation surface is clean and advanced from the Goal 032 checkpoint
near `1.533095e+03` to `3.270555e+03` code-time units. It is not the 50 Myr
C-LO endpoint.

Recommended next goal:
a bounded `C-LO` endpoint-or-next-continuation decision from compact checkpoint
catalogues. Do not begin C-LO post-processing until endpoint status is
explicitly resolved.
