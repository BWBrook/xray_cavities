# C-LO Bounded Execution Completion

Date: 2026-07-04

Goal 032 completed the bounded `C-LO` execution/checkpoint submission that was
authorized after the Goal 031 Stewart asset restore and C-LO preflight. The
PBS job was `750065.kunanyi-ohpc` (`c_lo_bound`).

## Result

Decision label:
`C_LO_BOUNDED_EXECUTION_CHECKPOINT_SURFACE_GREEN`.

The scheduler record, stdout, markers, and remote output inventory support
accepting this as a successful bounded execution/checkpoint surface:

- `Exit_status = 0`.
- `resources_used.walltime = 03:34:35`.
- `MPI_EXIT_CODE=0`.
- `markers/DONE` exists.
- Remote output volume is `482G`.
- HDF5 outputs are present: `7` `flt.h5` files and `3` `dbl.h5` files.
- Particle text outputs are present through `particles.0501.dbl`.

This is not a final 50 Myr endpoint product. The wrapper deliberately used
`-maxtime 3.5`, and the compact logs show the latest recorded HDF5 output time
as `1.533095e+03` code-time units, corresponding to the first major checkpoint
surface under the 50 Myr configuration.

## Caveats

The final `qstat` record includes `Stageout_status = 1`; however, the requested
stdout/stderr and submission transcript were present at the staged paths and
were retrieved. This is retained as a scheduler caveat rather than treated as a
run failure.

Stderr contains one line:

```text
/scratch/bwbrook/git/utas-agn/jet-setup/tools/setup-problem: line 11: git: command not found
```

The consequence is that `source_revisions.txt` reports source Git metadata as
unavailable. The staged config hashes, case identity, module stack, run
arguments, scheduler record, and output inventory are still recorded.

No HDF5 headers, science arrays, XRAiSE/PRAiSE outputs, radio products, cavity
products, endpoint comparison products, or observables were generated or
retrieved in this closeout.

## Local Bundle

Compact assets live under:

```text
docs/science/assets/c_lo_bounded_execution_completion_2026-07-04/
```

Machine-readable assets:

- `qstat_final.csv`
- `remote_log_inventory.csv`
- `run_output_inventory.csv`
- `completion_summary.csv`
- `next_step_recommendation.csv`
- `c_lo_bounded_execution_completion_metadata.json`

Retrieved text logs/manifests are under `remote_logs/`. The local bundle
contains only compact text evidence and no HDF5 or particle payload files.

## Recommendation

Recommended next goal:
`bounded_c_lo_checkpoint_inspection_and_continuation_decision`.

The next step should review this clean C-LO checkpoint surface and prepare the
smallest Barry-authorized continuation packet toward the C-LO endpoint while
preserving no-overwrite provenance and the PBS stop rule. C-LO science
post-processing should wait until the project has a suitable endpoint or a
deliberately selected later checkpoint surface.
