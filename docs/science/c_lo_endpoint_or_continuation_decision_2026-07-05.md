# C-LO Endpoint-Or-Continuation Decision

Date: 2026-07-05

Goal 034 inspected the accepted Goal 033 C-LO checkpoint continuation surface
and found that it remains a clean checkpoint, not the 50 Myr endpoint. The
evidence supports one more bounded continuation submission before any C-LO
post-processing or endpoint product work.

## Decision

Decision label:
`C_LO_CHECKPOINT_CLEAN_NOT_ENDPOINT_CONTINUATION2_SUBMITTED`.

The Goal 033 checkpoint is clean:

- `markers/DONE` present.
- `markers/FAILED` absent.
- latest double checkpoint row:
  `4 3.270555e+03 2.680126e-01 12349`.
- latest float output row:
  `12 3.270555e+03 2.680126e-01 12349`.
- latest restart files include `data.0004.dbl.h5`, `data.0004.dbl.xmf`,
  and `particles.1068.dbl`.

The checkpoint is not endpoint-complete. The latest code time is `3270.555`,
which is `0.21334247` of the accepted endpoint target
`15330.06968940`.

## Continuation Contract

The prepared continuation uses the same conservative restart contract as Goal
033:

- case: `C-LO`;
- variant: `particles`;
- resources: `select=64:ncpus=28:mpiprocs=28`;
- walltime: `04:00:00`;
- `PLUTO_MAXTIME_HOURS=3.5`;
- stack: AGN Intel/IMPI/HDF5;
- restart policy: `auto`, which selects `-h5restart 4` from the staged
  Goal 033 double checkpoint catalogue;
- new no-overwrite run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-07-05-c-lo-bounded-continuation-2`;
- stage root:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation`.

The particle restart surface is carried by the accepted Goal 033
`particles.1068.dbl` file. This run surface does not expose a separate
`particles.dbl.out` catalogue; `restart.out` plus the ordered particle restart
files are the particle restart evidence.

## Submission Result

The final remote staging/submission gate passed and exactly one PBS job was
submitted:

- job id: `750944.kunanyi-ohpc`;
- job name: `c_lo_cont2`;
- queue/state at stop: `normal` / `R`;
- resources: `select=64:ncpus=28:mpiprocs=28`, `ncpus=1792`,
  `mpiprocs=1792`, `mem=128gb`, `walltime=04:00:00`;
- stdout:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.out`;
- stderr:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/c_lo_endpoint_or_continuation.err`;
- preflight transcript:
  `/u/bwbrook/codex_kunanyi/goal034_c_lo_endpoint_or_continuation/remote_logs/submission_preflight_2026-07-05_final.txt`.

The stop rule is active: no polling or retrieval should occur until Barry
reports the PBS completion email or X-ray Cavities explicitly authorizes a
re-check.

## Caveats

- This is a continuation decision/submission package, not C-LO endpoint
  science.
- No XRAiSE, PRAiSE, radio, cavity, source-age, endpoint-comparison, or
  observable workflows are authorized here.
- No bulky HDF5 or particle payloads were copied locally.
- The endpoint remains unresolved until the continuation-2 completion evidence
  is retrieved and reviewed after Barry reports the PBS completion email.

## Recommendation

Wait for the PBS completion email for `750944.kunanyi-ohpc`, then run a
compact completion retrieval and endpoint review. Do not start C-LO
post-processing until endpoint status is explicitly resolved.
