# Plan: Goal 002 Final Sparse PRAiSE Loss Table

## Intended Shape

Build the narrowest remote pathway from the final sparse selected-ID history to
a PRAiSE-compatible loss table, then reuse the Goal 001 bridge rather than
building a separate radio-map lane.

```text
final sparse window -> selected-ID PRAiSE loss table -> Goal 001 bridge --loss-table -> compact review artefacts
```

The goal is not to make the final observable page. It is to prove whether the
sparse selected-ID PRAiSE loss contract is now real enough to carry forward.

## Likely Files

- Create or modify one focused script under `scripts/science/` for the sparse
  selected-ID loss-table path.
- Create or modify one or more focused tests under `tests/`.
- Create or modify one PBS wrapper and, if useful, one stage/submit helper
  under `scripts/kunanyi/`.
- Add a dated science note under `docs/science/`.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/goals/002-final-sparse-praise-loss-table/Log.md`.

Avoid broad refactors. Do not duplicate the full radio bridge if the Goal 001
`--loss-table` path already does the job.

## Work Plan

1. Record starting state in `Log.md`.
2. Re-read the Goal 002 packet and the Goal 001 interface note.
3. Inspect the final sparse-window product contract and the May PRAiSE smoke
   contract.
4. Decide the implementation route:
   - preferred: sparse selected-ID history is shaped into the minimum structure
     PRAiSE needs;
   - fallback: document the exact missing contract if PRAiSE cannot consume
     sparse selected-ID history safely.
5. Add focused local tests for any new parser/shaper/table writer.
6. Implement the smallest helper script needed to write
   `id,loss_factor` for selected IDs.
7. Add a PBS wrapper or stage helper that supports:
   - remote preflight;
   - deterministic smoke subset;
   - full selected-ID table;
   - bridge run with `--loss-table`.
8. Run local tests and PBS syntax checks.
9. Stage to Kunanyi with checksums.
10. Run read-only remote preflight.
11. Run the smoke gate and inspect finite/non-negative selected-ID output.
12. Run the reproducibility gate or record why a different bounded check is the
    right substitute.
13. Run the full selected-ID loss-table job only after the smoke gate is green.
14. Run the sparse bridge with the generated loss table.
15. Archive compact products and pull only reviewable artefacts into the repo.
16. Write the science note and exchange log.
17. Update `Log.md` with commands, job IDs, outcomes, checksums, caveats, and
    recommendation.
18. Wake X-ray Cavities when complete, blocked, or queued/running past a
    sensible monitoring window.

## Expected Design Decisions

Prefer:

- selected-ID keyed tables over row-order assumptions;
- deterministic subsets over ad hoc sampling;
- finite/non-negative fail-fast checks over silent clipping;
- explicit `science_status` metadata over optimistic labels;
- remote artefacts with checksums and compact local summaries;
- one remote production path that can be rerun, rather than manual one-offs.

## Non-Goals

Do not solve final tracer-volume coupling here. Do not beam-convolve maps. Do
not build the aligned observable comparison page. Do not modify scientific
defaults. Do not spend a large allocation just to discover whether the sparse
loss table can be generated.
