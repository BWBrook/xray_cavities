# 2026-07-05 - C-LO Endpoint-Oriented Continuation

Goal 035 prepares a bolder C-LO continuation from the accepted Goal 034
checkpoint surface. The strategic shift is explicit: do not submit another
default 3.5-hour ladder rung if the queue supports a credible endpoint-oriented
job.

## Current Decision

Status: `submitted_waiting_pbs_completion`.

Decision label:
`C_LO_RESTART_GATE_CLEAN_ENDPOINT_ORIENTED_48H_CONTINUATION_SUBMITTED`.

Restart gate evidence from the accepted Goal 034 surface:

- `markers/DONE` present and `markers/FAILED` absent.
- Latest `dbl.h5.out` row:
  `6 4.930755e+03 2.678869e-01 18546`.
- Latest `flt.h5.out` row:
  `19 4.930755e+03 2.678869e-01 18546`.
- Latest restart surfaces:
  `data.0006.dbl.h5`, `data.0006.dbl.xmf`, and `particles.1611.dbl`.
- Endpoint target remains `15330.06968940`; latest catalogue time is
  `4930.755`, or `0.32163944` of endpoint.

Queue evidence and amendment:

- `normal` queue maximum walltime is `48:00:00`.
- Barry clarified that Kunanyi generally accepts jobs up to 48 hours and that
  64 nodes is the preferred restart scale unless a concrete restart-gate reason
  says otherwise.
- Goal 035 now requests `48:00:00` walltime and
  `PLUTO_MAXTIME_HOURS=47.5`.
- 64 nodes / 1792 ranks are retained to avoid the unresolved 80-node restart
  stall risk.

## Local Packet

Added:

- `scripts/kunanyi/c_lo_endpoint_oriented_continuation.pbs`;
- `tests/test_c_lo_endpoint_oriented_continuation_wrapper.py`;
- `docs/goals/035-c-lo-endpoint-oriented-continuation/Log.md`;
- `docs/science/c_lo_endpoint_oriented_continuation_2026-07-05.md`;
- `docs/science/assets/c_lo_endpoint_oriented_continuation_2026-07-05/`.

Updated:

- `docs/exchange/current_status.md`.

## Submission

Remote staging passed local/remote SHA-256 checks, remote wrapper/template
syntax, restart surface checks, no-overwrite run-root checks, source-path
checks, and AGN Intel/IMPI/HDF5 module loading.

The run root was prepared by copying compact catalogues and symlinking large
restart payloads from the accepted Goal 034 surface, so Goal 035 can append
new catalogues without mutating accepted Goal 034 evidence.

Submitted PBS job:

- job id: `750947.kunanyi-ohpc`;
- job name: `c_lo_endpt`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `walltime=48:00:00`;
- stage root:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation`;
- run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-endpoint-oriented-continuation`;
- stdout/stderr:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.out`
  and
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/c_lo_endpoint_oriented_continuation.err`;
- preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_preflight_2026-07-05_endpoint_oriented.txt`;
- submission record:
  `/u/bwbrook/codex_kunanyi/goal035_c_lo_endpoint_oriented_continuation/remote_logs/submission_record_2026-07-05_endpoint_oriented.txt`.

Remote activity stopped after qstat showed state `R`. The helper returned a
late `141` after emitting the qstat record; this is recorded as a helper
transport caveat, not as a qsub failure.

## Recommendation

Wait for Barry's PBS completion email for `750947.kunanyi-ohpc`. After
completion authorization, retrieve compact scheduler/stdout/stderr and
run-root inventory evidence only, then decide whether C-LO endpoint status has
been reached.

No C-LO post-processing, endpoint observables, `G-LO`, scientific-default
changes, commits, pushes, cleanup, Stas/Patrick contact, `agent_comms` edits,
or accepted-asset overwrites are authorized by this packet.

## Completion Retrieval - 2026-07-07

Status:
`complete_endpoint_review`.

Decision label:
`C_LO_ENDPOINT_ORIENTED_RUN_REACHED_ENDPOINT_COMPACT_EVIDENCE_GREEN`.

Barry reported PBS completion for `750947.kunanyi-ohpc` / `c_lo_endpt` with
`Exit_status=0`, `resources_used.walltime=24:47:37`,
`resources_used.cput=692:21:26`, `resources_used.ncpus=1792`,
`resources_used.mem=9891168kb`, and `resources_used.vmem=27596320kb`.

Compact retrieval and endpoint review were completed after refreshing the TPAC
selector through the authorized Chrome/Open OnDemand route. Safari was not
used. Retrieved evidence was limited to final `qstat`, stdout/stderr,
submission preflight transcript, and compact text/CSV inventories of the run
root.

Endpoint evidence:

- `qstat` final state `F`, `Exit_status=0`, `Stageout_status=1`;
- `markers/DONE` present and `markers/FAILED` absent;
- stdout contains `MPI_EXIT_CODE=0`;
- stderr contains only the known nonfatal
  `setup-problem: git: command not found` warning;
- latest `dbl.h5.out` row:
  `13 1.533007e+04 2.422549e-03 57029`;
- latest `flt.h5.out` row:
  `53 1.533007e+04 2.422549e-03 57029`;
- endpoint target: `15330.06968940`;
- latest compact catalogue time: `15330.07`;
- endpoint fraction: `1.00000002026`;
- remaining gap: `-0.000310600000375`.

Interpretation: the compact catalogues support that C-LO reached the configured
50 Myr endpoint. This is an endpoint-status review only; no C-LO science
post-processing or observables were run.

Completion package:

- science note:
  `docs/science/c_lo_endpoint_oriented_continuation_completion_2026-07-07.md`;
- asset bundle:
  `docs/science/assets/c_lo_endpoint_oriented_continuation_completion_2026-07-07/`;
- key assets:
  `qstat_final.csv`, `completion_summary.csv`, `run_output_inventory.csv`,
  `run_output_inventory_summary.csv`, `remote_log_inventory.csv`,
  `next_step_recommendation.csv`,
  `c_lo_endpoint_oriented_continuation_completion_metadata.json`, compact
  `remote_logs/`, and `local_asset_manifest.sha256`.

Recommendation: next prepare a bounded C-LO endpoint post-processing preflight
or inspection packet after X-ray Cavities accepts this endpoint-status package.
Do not start XRAiSE, PRAiSE, radio, cavity, endpoint-comparison, observable,
or `G-LO` work from this closeout alone.
