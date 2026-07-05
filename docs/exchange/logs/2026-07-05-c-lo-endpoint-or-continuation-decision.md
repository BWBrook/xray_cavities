# 2026-07-05 - C-LO Endpoint-Or-Continuation Decision

Goal 034 decides whether the accepted Goal 033 C-LO continuation surface is an
endpoint or a clean checkpoint requiring one more bounded continuation.

## Current Decision

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_CHECKPOINT_CLEAN_NOT_ENDPOINT_CONTINUATION2_SUBMITTED`.

Live checkpoint evidence from the Goal 033 run root shows:

- `markers/DONE` present and `markers/FAILED` absent.
- Latest `dbl.h5.out` row:
  `4 3.270555e+03 2.680126e-01 12349`.
- Latest `flt.h5.out` row:
  `12 3.270555e+03 2.680126e-01 12349`.
- Latest restart surfaces:
  `data.0004.dbl.h5`, `data.0004.dbl.xmf`, `data.0012.flt.h5`,
  `data.0012.flt.xmf`, and `particles.1068.dbl`.
- Endpoint target remains `15330.06968940` code-time units; latest time is
  only `0.21334247` of that target.
- New continuation-2 root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2`
  was absent before staging.

The conclusion is that the Goal 033 surface is a green checkpoint, not the
50 Myr endpoint.

## Local Packet

Added:

- `scripts/kunanyi/c_lo_endpoint_or_continuation.pbs`
- `tests/test_c_lo_endpoint_or_continuation_wrapper.py`
- `docs/goals/034-c-lo-endpoint-or-continuation-decision/Log.md`
- `docs/science/c_lo_endpoint_or_continuation_decision_2026-07-05.md`
- `docs/science/assets/c_lo_endpoint_or_continuation_decision_2026-07-05/`

Updated:

- `docs/exchange/current_status.md`

## Submission

The final remote gate passed staged SHA-256 checks, remote wrapper/template
syntax, restart-surface checks, no-overwrite run-root checks, source-path
checks, and AGN Intel/IMPI/HDF5 module loading.

Submitted PBS job:

- job id: `750944.kunanyi-ohpc`;
- job name: `c_lo_cont2`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `mem=128gb`, `walltime=04:00:00`;
- stage root:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation`;
- run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.out`
  and
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.err`;
- final preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/remote_logs/submission_preflight_2026-07-05_final.txt`;
- submission record:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/remote_logs/submission_record_2026-07-05.txt`.

Remote activity stopped immediately after `qstat -f` verified state `R`.

## Validation

- Focused wrapper tests:
  `uv run pytest tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed with `12 passed in 0.01s`.
- Wrapper/template syntax:
  `bash -n scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` and
  `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for the Goal 034 metadata.
- CSV parse/expected-column checks passed for all Goal 034 asset CSVs.
- `git diff --check` passed.
- Targeted unresolved-marker scans passed for new Goal 034 files and the new
  top `current_status.md` section; older `current_status.md` history contains
  unrelated historical handoff-state terms.
- No bulky HDF5, `data.*`, or particle payload files are present in the local
  Goal 034 asset bundle.

## Recommendation

Wait for Barry's PBS completion email for `750944.kunanyi-ohpc`. After
completion authorization, retrieve compact scheduler/stdout/stderr and run-root
inventory evidence only, then decide whether C-LO endpoint status has been
reached.

No C-LO post-processing, endpoint observables, `G-LO`, scientific-default
changes, commits, pushes, cleanup, Stas/Patrick contact, `agent_comms` edits,
or accepted-asset overwrites are authorized by this decision packet.

## Completion Retrieval And Review

Barry reported the PBS completion email for `750944.kunanyi-ohpc`
(`c_lo_cont2`) with `Exit_status=0`, `resources_used.walltime=03:32:55`,
`resources_used.cput=98:38:39`, `resources_used.ncpus=1792`,
`resources_used.mem=9868484kb`, and `resources_used.vmem=27590612kb`.

Status after compact retrieval/review:
`complete_checkpoint_review`.

Decision label:
`C_LO_CONTINUATION2_CHECKPOINT_SURFACE_GREEN_NOT_ENDPOINT`.

Retrieved compact assets:

- `docs/science/c_lo_endpoint_or_continuation_completion_2026-07-05.md`;
- `docs/science/assets/c_lo_endpoint_or_continuation_completion_2026-07-05/`;
- `remote_logs/qstat_final_2026-07-05.txt`;
- `remote_logs/c_lo_endpoint_or_continuation.out`;
- `remote_logs/c_lo_endpoint_or_continuation.err`;
- `remote_logs/submission_preflight_2026-07-05_final.txt`;
- compact completion and output-inventory tables.

Evidence summary:

- final scheduler state `F`, `Exit_status=0`, `Stageout_status=1`;
- `markers/DONE` present and `markers/FAILED` absent;
- wrapper stdout reports `MPI_EXIT_CODE=0`;
- stderr contains only a nonfatal `setup-problem` warning:
  `git: command not found`;
- latest `dbl.h5.out` row:
  `6 4.930755e+03 2.678869e-01 18546`;
- latest `flt.h5.out` row:
  `19 4.930755e+03 2.678869e-01 18546`;
- latest remote restart/product surfaces:
  `data.0006.dbl.h5`, `data.0019.flt.h5`, and `particles.1611.dbl`;
- compact inventory counts: `9` HDF5 files and `543` particle restart files,
  remote-only; output directory size `422G`.

Endpoint interpretation:

- configured endpoint target: `15330.06968940` code-time units;
- latest compact catalogue time: `4930.755`;
- endpoint fraction: `0.32163944`;
- conclusion: green checkpoint/continuation surface, not endpoint-complete.

Recommendation: the next packet should be another bounded `C-LO`
endpoint-or-next-continuation decision. Do not start C-LO post-processing,
XRAiSE/PRAiSE, radio, cavity, endpoint-comparison, or observable workflows
until endpoint status is explicitly resolved.

Completion-review validation:

- Focused wrapper tests:
  `uv run pytest tests/test_c_lo_endpoint_or_continuation_wrapper.py tests/test_c_lo_checkpoint_continuation_wrapper.py tests/test_c_lo_bounded_execution_wrapper.py -q`
  passed with `12 passed in 0.01s`.
- Wrapper/template syntax:
  `bash -n scripts/kunanyi/c_lo_endpoint_or_continuation.pbs` and
  `bash -n scripts/kunanyi/jet_setup_production_template.pbs` passed.
- JSON parse passed for the completion metadata.
- CSV parse/expected-column checks passed for all completion asset CSVs.
- `git diff --check` passed.
- Targeted unresolved-marker scan passed.
- No-bulky guard passed for the completion bundle: no `.h5`, `data.*`,
  `particles.*`, or files larger than `5 MB` are present locally.

Boundary confirmation: no new PBS job, retry, continuation, polling loop,
XRAiSE/PRAiSE, radio, cavity, source-age, endpoint-comparison, observable
workflow, `G-LO`, scientific-default change, bulky payload retrieval, commit,
push, cleanup, Stas/Patrick contact, `agent_comms` edit, or accepted-asset
overwrite occurred in the completion-review pass.
