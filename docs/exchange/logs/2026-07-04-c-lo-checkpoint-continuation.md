# 2026-07-04 - C-LO Checkpoint Continuation

Goal 033 inspected the accepted Goal 032 `C-LO` checkpoint surface and submitted
one bounded continuation job after the restart gate passed.

## Result

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_CHECKPOINT_SURFACE_CLEAN_CONTINUATION_SUBMITTED`.

Submitted PBS job:

```text
Job id: 750931.kunanyi-ohpc
Job name: c_lo_cont
State at stop: Q
Queue: normal
Resources: select=64:ncpus=28:mpiprocs=28, walltime=04:00:00
```

Stop rule:
Do not poll or retrieve until Barry reports the PBS completion email, or X-ray
Cavities explicitly authorizes a re-check.

## Checkpoint Inspection

Source checkpoint:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-03-c-lo-bounded-execution/C-LO/particles
```

The restart surface was clean:

- `markers/DONE` present.
- `markers/FAILED` absent.
- Latest `dbl.h5.out` restart record:
  `2 1.533095e+03 2.702729e-01 5920`.
- Latest `flt.h5.out` record:
  `6 1.533095e+03 2.702729e-01 5920`.
- Restart HDF5 `data.0002.dbl.h5` present, size `67318639276` bytes.
- Particle restart file `particles.0501.dbl` present, size `2808546` bytes.
- New continuation workdir was absent before staging.

## Local Packet

Added:

- `scripts/kunanyi/c_lo_checkpoint_continuation.pbs`
- `tests/test_c_lo_checkpoint_continuation_wrapper.py`
- `docs/science/c_lo_checkpoint_continuation_decision_2026-07-04.md`
- `docs/science/assets/c_lo_checkpoint_continuation_2026-07-04/`
- `docs/goals/033-c-lo-checkpoint-continuation/Log.md`

Updated:

- `docs/exchange/current_status.md`

## Staging And Submission

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal033_c_lo_checkpoint_continuation
```

Continuation run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation
```

Staged:

- `rendered_c_lo_config/`
- `c_lo_checkpoint_continuation.pbs`
- `jet_setup_production_template_latest.pbs`

Remote validation passed:

- staged SHA-256 verification;
- remote wrapper/template `bash -n`;
- source checkpoint marker/catalogue/restart/particle checks;
- no-overwrite continuation workdir preparation;
- module stack load under the AGN Intel/IMPI/HDF5 path.

The continuation workdir was prepared with copied compact config/catalogue
surfaces and symlinks to the accepted Goal 032 restart HDF5/XMF and particle
restart surfaces.

## Recommendation

Wait for Barry's PBS completion email for `750931.kunanyi-ohpc`. The next goal
should retrieve compact completion evidence only and decide whether the
continuation surface is clean and how far it advanced toward the C-LO endpoint.

No retrieval, polling loop, finalizer, post-processing, XRAiSE/PRAiSE,
radio/cavity extraction, endpoint product, `G-LO`, scientific-default change,
commit, push, cleanup, Stas/Patrick contact, `agent_comms` edit, or
accepted-asset overwrite occurred.

## Completion Retrieval - 2026-07-05

Barry reported the completion email for `750931.kunanyi-ohpc` with
`Exit_status=0`, `resources_used.walltime=03:33:08`,
`resources_used.cput=98:54:40`, `resources_used.ncpus=1792`, and
`resources_used.mem=9870960kb`.

Goal 033 retrieved compact completion evidence only:

- final qstat record for `750931.kunanyi-ohpc`;
- stage stdout/stderr;
- submission preflight transcript;
- compact marker/log/output inventory for
  `/scratch/bwbrook/xray_cavities_runs/2026-07-04-c-lo-bounded-continuation/C-LO/particles`.

New local completion note and assets:

- `docs/science/c_lo_checkpoint_continuation_completion_2026-07-05.md`
- `docs/science/assets/c_lo_checkpoint_continuation_completion_2026-07-05/`

Completion evidence:

- `qstat` final state `F`, `Exit_status=0`.
- `Stageout_status=1`; retained as a scheduler caveat.
- `markers/DONE` present and `markers/FAILED` absent.
- stdout reports `MPI_EXIT_CODE=0`; stderr is empty.
- latest `dbl.h5.out` row:
  `4 3.270555e+03 2.680126e-01 12349`.
- latest `flt.h5.out` row:
  `12 3.270555e+03 2.680126e-01 12349`.
- latest remote restart surfaces:
  `data.0004.dbl.h5`, `data.0012.flt.h5`, and `particles.1068.dbl`.
- remote output inventory:
  `8` HDF5 files and `567` particle restart files, inventoried by path/size
  only and not copied locally.

Status:
`complete_checkpoint_review`.

Decision label:
`C_LO_CONTINUATION_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

This is a green continuation checkpoint surface, not the C-LO 50 Myr endpoint.
The next goal should decide whether another bounded continuation is required
before any C-LO post-processing. No new PBS job, retry, continuation, polling
loop, bulky retrieval, XRAiSE/PRAiSE, radio/cavity work, endpoint product,
`G-LO`, scientific-default change, commit, push, cleanup, Stas/Patrick contact,
`agent_comms` edit, or accepted-asset overwrite occurred.
