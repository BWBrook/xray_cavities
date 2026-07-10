# G-LO HDF5-Stall Guarded Continuation

Date: 2026-07-10

Goal 038 recovered the valid Goal 037 G-LO restart surface, hardened the
restart and progress-watchdog contracts, executed Barry-approved scratch
compaction, and submitted one endpoint-oriented 64-node continuation.

## Decision

Status: `submitted_waiting_pbs_completion`.

Decision label:
`G_LO_GUARDED_CONTINUATION_SUBMITTED_WAITING_PBS_COMPLETION`.

PBS job `751292.kunanyi-ohpc` (`g_lo_guard`) was verified queued on the
`normal` queue at `2026-07-10 15:04:00` Hobart time. The request is
`select=64:ncpus=28:mpiprocs=28`, 1,792 MPI ranks, 128 GB, and
`walltime=48:00:00`; PLUTO receives a 47.5-hour maximum runtime. The PBS stop
rule is active: there will be no polling or retrieval until Barry reports the
completion email or explicitly asks for a re-check.

## Restart Surface

The selected restart is no longer an mtime inference. The PLUTO binary
`restart.out` contains exactly three 128-byte records. Record 2 binds:

- double-HDF5 runtime slot 2 to `data.0002.dbl.h5`;
- float-HDF5 runtime slot 3 to index 10;
- particle runtime slot 8 to `particles.1000.dbl`;
- fluid step 10578 and code time 3065.934704693023.

The particle header independently reports step 10578 and time
3065.934704693, with an absolute time delta of
2.2737367544323206e-11. Its 5,044,387-byte file contains a 547-byte header
and 42,032 records of 15 little-endian doubles. A complete scan found finite
values and 42,032 unique integral IDs.

The hardened validator also checks the exact 67,318,639,276-byte fluid HDF5,
required `rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3` datasets at
`Timestep_2`, common shape `1014 x 960 x 960`, HDF5 time, restart scalar
samples, and the unique `dbl.h5.out` index/time/step row. The submitted job
hashes the trusted Goal 037 source HDF5 on the compute node and requires the
isolated staged HDF5 to match it before `mpirun`; it also SHA-binds the
catalogue, `restart.out`, and particle input.

The incomplete `data.0003.dbl.h5` is excluded and was removed during the
approved compaction.

## Watchdog

The shared production template retains its unchanged default path unless the
watchdog is explicitly enabled. Goal 038 fixes the watchdog at:

- no-output-progress timeout: 5,400 seconds;
- poll interval: 60 seconds;
- TERM grace: 120 seconds;
- Intel MPI signal propagation enabled.

Progress is based on HDF5 metadata, latest particle output, `dbl.h5.out`,
`flt.h5.out`, and `restart.out`; PLUTO log chatter does not reset the timer.
On timeout the helper writes an atomic trigger, sends TERM to the dedicated
launcher process group, escalates KILL to the whole group if required, and
returns 124. The template records the distinct failure reason
`no_progress_watchdog_timeout`.

## Review And Hardening

Independent reviews initially found that validation was not enforced by the
wrapper, the HDF5 and catalogue were not fully bound to the restart proof,
particle and fluid steps were not directly compared, the float slot and record
count were not fixed, and KILL escalation targeted only the launcher PID.
Later review found an awk built-in-name collision and wrapper override paths
that could separate the validated and launched targets.

All findings were reproduced red-first and fixed. The wrapper now pins case,
variant, run root, restart policy, restart index, resources, and module stack;
the validator binds all four restart surfaces; catalogue tests exercise valid,
duplicate, and malformed rows; and the watchdog terminates the full process
group. A final independent review reported no correctness or launch-safety
findings.

## Approved Scratch Compaction

The first remote staging attempt exposed an apparent scratch quota boundary:
a 929,856-byte executable copy failed with `Disk quota exceeded`. Barry then
approved the documented retention-aware compaction.

The one-off fail-closed utility
`scripts/kunanyi/compact_xray_cavities_scratch_goal038.py`:

- wrote pre/post inventories and hashes to the remote stage root;
- promoted C-LO float-HDF5/XMF age surfaces into the accepted endpoint root;
- retained C-HI and C-LO accepted endpoints, production float-HDF5 age
  surfaces, selected restart tuples, catalogues, configuration, and compact
  provenance;
- removed superseded C-HI scale ladders and May prove-outs;
- removed redundant C-HI/C-LO double checkpoints and particle restarts; and
- removed only the known-invalid G-LO double HDF5 plus the zero-byte partial
  Goal 038 root.

The orchestrator-observed initial summary reported 2,344,938,776,583 bytes
freed and the idempotent corrective summary reported 465,358,011,179 bytes,
for a manifest-based total of 2,810,296,787,762 bytes (2.810 TB). A subsequent
16 MiB scratch write probe passed. The corrective-pass manifests remain in the
remote stage root and were not copied locally before the PBS stop rule. The
initial-pass manifest/summary may have been overwritten by the idempotent
second run, so the summed exact-byte claim is retained as
orchestrator-observed derivative evidence and may not be independently
reconstructable. A later recursive `du` value was internally implausible and
is not used as a capacity claim.

The compaction script is deliberately Goal-038-specific. It is not a generic
cleanup command. Future cleanup must use the dependency and lifecycle rules in
`docs/science/xray_cavities_data_lifecycle_strategy_2026-07-10.md`.

That policy is prospective. Retrospectively, Goal 038's capacity evidence is
`RED` or unquantified once its 20 percent forecast safety factor and
particle/log growth are included. The already-submitted job is an explicit
pre-policy exception, not the capacity precedent for later production.

## Final Staging And Submission

Stage root:

```text
/u/bwbrook/codex_kunanyi/goal038_g_lo_hdf5_stall_guarded_continuation
```

Source root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-07-g-lo-endpoint-oriented-production/G-LO/particles
```

Isolated run root:

```text
/scratch/bwbrook/xray_cavities_runs/2026-07-10-g-lo-hdf5-stall-guarded-continuation
```

The isolated root contains the exact Goal 037 executable/configuration and
only the selected restart surfaces: `data.0002.dbl.h5`, its XMF,
`restart.out`, `particles.1000.dbl`, `grid.out`, and truncated catalogues
through double index 2 and float index 10. No later HDF5 or particle payload,
stale marker, or partial index 3 is present.

The submission session observed passing staged SHA-256 checks, shell syntax,
exact inventory, catalogue structure, full particle scan, HDF5
structure/time/shape/datasets, module stack, and queue limits. The raw
post-compaction preflight and qstat transcripts remain remote-only pending the
completion wake-up; `provenance_gap_register.csv` makes that local evidence gap
explicit. Source-to-isolated HDF5 SHA equality is also a fail-closed
compute-node pre-launch check inside job `751292`.

## Validation

The final integrated local suite passed 89 tests across the compaction tool,
restart validator, guarded wrapper, shared production template, watchdog, and
inherited C-LO/G-LO production contracts. All Goal 038 shell surfaces pass
`bash -n`; JSON/CSV parsing and `git diff --check` also pass.

## Boundary

Exactly one PBS job was submitted and verified queued. No post-submission
polling, retrieval, follow-on job, post-processing, XRAiSE, PRAiSE, radio,
cavity, source-age, C-HI/C-LO rerun, science-product workflow, commit, or push
occurred. The accepted Goal 037 source root was read for staging and validation
but not mutated.
