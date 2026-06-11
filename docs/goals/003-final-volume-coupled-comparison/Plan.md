# Plan: Goal 003 Final Volume-Coupled Comparison Page

## Intended Shape

Build the narrowest bridge from final grid/tracer truth to the existing sparse
PRAiSE radio product.

```text
final HDF5 truth extraction
  -> tracer > 5e-3 negative/positive lobe volumes
  -> Goal 002 loss table + Goal 001 bridge declared side volumes
  -> compact final comparison page
```

This goal should make the final endpoint scientifically more interpretable by
removing the `1.0 kpc^3` per selected particle scale from the sparse radio
summary. It should not expand into full beam-convolved radio, final X-ray, or
cavity `pV` science.

## Likely Files

- Reuse or modify `scripts/science/pluto_h5_truth_extract.c` only if final
  extraction exposes a concrete defect.
- Create or modify one PBS wrapper under `scripts/kunanyi/`, likely with a
  final-endpoint name, if the existing truth wrapper is too generic for clean
  provenance.
- Create one focused comparison builder under `scripts/science/`, likely
  `scripts/science/build_final_volume_coupled_comparison.py`.
- Create focused tests under `tests/`, likely
  `tests/test_final_volume_coupled_comparison.py`.
- Add a dated science note under `docs/science/`.
- Add compact generated review assets under `docs/science/assets/`.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/exchange/current_status.md` if the practical handoff state
  changes.
- Update `docs/goals/003-final-volume-coupled-comparison/Log.md`.

Avoid broad refactors. The established `--loss-table` interface is a project
asset now; preserve it unless a genuine bug is found.

## Work Plan

1. Record starting state in `Log.md`.
2. Re-read the Goal 003 packet, Goal 002 science note, final quick-look note,
   final sparse-window note, and bridge code.
3. Inspect the final HDF5 truth extractor and decide whether it can be reused
   unchanged for `data.0051.flt.h5` / `Timestep_51`.
4. Add tests for the comparison builder before implementing it:
   - parse Level 2 truth rows;
   - select the `5e-3` negative-z and positive-z volumes;
   - reject missing threshold/side rows;
   - reject non-finite or non-positive selected volumes;
   - compare declared bridge volumes against truth volumes;
   - compute old-vs-new lobe scale factors.
5. Implement the smallest local comparison builder needed to assemble compact
   machine-readable outputs and a figure or Markdown tables.
6. Add or adapt a PBS wrapper that stages and runs final truth extraction and,
   if appropriate, the volume-coupled bridge rerun.
7. Run focused local tests and the existing sparse bridge/loss-table tests.
8. Run `bash -n` for every new or edited PBS wrapper.
9. Stage only the required scripts and goal-specific wrapper to Kunanyi.
10. Run read-only remote preflight for:
    - final HDF5 path;
    - `Timestep_51`;
    - Goal 002 full loss table or archive;
    - required module/compiler/runtime commands;
    - goal-specific output directories.
11. Run final truth extraction on a compute node. Record job ID, node, walltime,
    memory if available, stdout/stderr, and output checksums.
12. Inspect `level2_tracer_lobe_truth.csv`. Use the `5e-3` negative-z and
    positive-z `volume_kpc3` values as bridge inputs only after the validation
    checks pass.
13. Rerun the sparse particle radio bridge with the Goal 002 full loss table
    and declared side volumes.
14. Validate bridge metadata and lobe-summary side volumes.
15. Archive compact products remotely and pull only reviewable artefacts into
    the repo.
16. Build the comparison package from machine-readable truth and bridge
    outputs.
17. Write the science note and exchange log.
18. Update `Log.md` with commands, job IDs, outcomes, checksums, caveats, and
    recommendation.
19. Wake X-ray Cavities when complete, blocked, or queued/running past a
    sensible monitoring window.

## Expected Design Decisions

Prefer:

- measured final tracer volumes over particle-count proxy volumes;
- parser functions with tests over ad hoc report scraping;
- explicit side labels over positional row assumptions;
- generated comparison tables over hand-copied values;
- dated artefact directories with checksums;
- direct caveats over optimistic naming.

The comparison page should be useful to a physicist reading quickly. It should
answer: what final truth volume was used, what changed relative to Goal 002,
what luminosities follow from that scale, and what pieces remain absent.

## Non-Goals

Do not build dense particle history. Do not alter the sparse selected-ID loss
table. Do not change physical defaults. Do not turn this into a final
publication figure package. Do not hide missing full X-ray/cavity/beam products
behind polished language.
