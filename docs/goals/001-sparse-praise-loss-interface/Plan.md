# Plan: Goal 001 Sparse PRAiSE-Compatible Loss Interface

## Intended Shape

Add the smallest useful local interface between sparse particle trajectories and
radio-map construction:

```text
sparse window rows -> selected particles -> loss model -> radio maps/metadata
```

The current pressure-history proxy should become one loss model. An external
PRAiSE-compatible loss table should become another. The external path should be
usable in local tests without requiring the real Kunanyi PRAiSE run.

## Likely Files

- Modify `scripts/science/sparse_particle_radio_bridge.py`.
- Modify `tests/test_sparse_particle_radio_bridge.py`.
- Add one short note under `docs/science/`.
- Update `docs/goals/001-sparse-praise-loss-interface/Log.md`.

Only create a new helper module if it keeps the bridge script easier to review.
Avoid broad refactors.

## Work Plan

1. Record starting state in `Log.md`.
2. Re-read the goal and the required context files.
3. Write or extend tests for an external loss-factor table:
   - selected particle IDs are matched by ID, not row order;
   - missing IDs fail clearly or are reported clearly;
   - duplicate IDs fail clearly;
   - non-finite or negative values are rejected or handled explicitly;
   - metadata identifies the loss model.
4. Implement the smallest interface needed to satisfy those tests.
5. Preserve existing pressure-history proxy outputs and tests.
6. Update output metadata and, if needed, filenames so proxy and external-loss
   products are not confused.
7. Add the short `docs/science/` interface note.
8. Run the validation gate.
9. Update `Log.md` with validation evidence and residual risks.
10. Send X-ray Cavities a wake-up when complete or blocked.

## Expected Design Decisions

The implementation should prefer:

- explicit failure over silent row-order assumptions;
- stable CSV/TSV inputs over opaque binary inputs for the local interface;
- metadata that names the loss source and loss-column semantics;
- preserving current bridge behavior unless the external loss path is selected.

## Non-Goals

Do not make the external loss table appear magically. The goal is to build and
test the interface that a later true PRAiSE run can feed.

Do not run remote jobs or use the TPAC jumpbox path.
