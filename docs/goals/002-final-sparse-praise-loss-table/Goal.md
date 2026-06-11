# Goal 002: Final Sparse PRAiSE Loss Table

## Objective

Generate and validate a bounded remote PRAiSE-compatible per-particle loss table
for the final `C-HI` sparse selected IDs, then feed that table through the
Goal 001 sparse radio bridge via `--loss-table`.

This goal is complete when the repo contains reviewable code, logs, and compact
science notes showing either:

- a green final sparse selected-ID loss table plus external-loss radio bridge
  product; or
- a sharply documented blocker proving which PRAiSE/sparse-history contract is
  missing and what decision is needed next.

## Why This Matters

Goal 001 built the local interface between sparse particle radio products and
an externally supplied loss table. The project now needs the first real
selected-ID loss table from the completed 50 Myr `C-HI` run, without falling
back to the rejected dense all-history particle HDF5 approach.

The output should advance the science from a pressure-history morphology proxy
toward a true PRAiSE-compatible loss product, while preserving caveats about
the sparse time window, provisional luminosity scaling, and missing final
observable-comparison page.

## Operating Mode

Remote implementation and validation with a smoke-first gate.

Use local tests and syntax checks before staging. Use `kunanyi` for the remote
PRAiSE runtime and final sparse data because the relevant products already live
there. If SSH access requires the TPAC "Enable Jumpbox SSH" selector, use
Chrome or Computer Use for that narrow access step.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- new or changed tests;
- PBS wrappers or remote-run helpers;
- `docs/goals/002-final-sparse-praise-loss-table/Log.md`;
- remote stdout/stderr excerpts, job IDs, checksums, and status markers;
- compact local artefacts under `docs/science/` and, if generated,
  `docs/science/assets/`;
- the final recommendation for the next scientific decision.

## Scope

In scope:

- Add or modify narrowly scoped repo-local scripts needed to build a sparse
  selected-ID PRAiSE-compatible loss table.
- Add local tests for any new parsing, selected-ID matching, sparse-history
  shaping, or loss-table validation logic.
- Add or modify PBS wrappers and staging helpers needed for the remote smoke
  and final selected-ID run.
- Stage code to `kunanyi` under a goal-specific path such as
  `/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/`.
- Use the final sparse-window input:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window`.
- Use the completed final production outputs:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs`.
- Reuse the existing remote PRAiSE runtime where appropriate:
  `/u/bwbrook/codex_kunanyi/particle_loss_runtime`.
- Run a small remote smoke/preflight before the full selected-ID loss-table run.
- Run the Goal 001 bridge with `--loss-table` after a valid loss table exists.
- Pull compact products into the repo when they are small enough to review
  directly, following existing `docs/science/assets/` conventions.
- Write a concise science note and exchange log explaining method, provenance,
  result, caveats, and next step.

Out of scope:

- Do not build a dense all-history `plutokore.load_all_particles()` HDF5 cache
  across all 5001 particle outputs.
- Do not run a new full PLUTO simulation segment.
- Do not change scientific defaults such as `eta`, `s`, `gmin`, `gmax`,
  frequency, redshift, tracer threshold, sparse-window start/end/stride, or
  volume assignment without pausing for X-ray Cavities.
- Do not produce or claim a final publication-ready observable comparison page.
- Do not solve final grid/tracer volume coupling in this goal.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, or sibling project repos.
- Do not edit local UTAS AGN source checkouts under
  `/Users/bwbrook/git/utas-agn` unless X-ray Cavities explicitly authorizes it.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/goals/001-sparse-praise-loss-interface/Goal.md`
- `docs/goals/001-sparse-praise-loss-interface/Log.md`
- `docs/science/sparse_praise_loss_interface_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md`
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge.md`
- `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
- `docs/science/c_hi_particle_loss_smoke_2026-05-10.md`
- `docs/science/c_hi_particle_radio_smoke_2026-05-10.md`
- `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md`
- `scripts/science/sparse_particle_radio_bridge.py`
- `scripts/science/xraise_particle_loss_smoke.py`
- `scripts/science/xraise_particle_radio_smoke.py`
- `scripts/science/pluto_particle_sparse_window.py`
- relevant existing PBS wrappers under `scripts/kunanyi/`

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `77fadd2`, clean against
`origin/main`, unless X-ray Cavities has fast-forwarded the repo before
delegation.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Required Work

- Determine the smallest reliable way to apply the existing PRAiSE/XRAiSE loss
  machinery to the final sparse selected-ID history without materialising a
  dense all-history cache.
- Produce a selected-ID external loss table with at least:

  ```text
  id,loss_factor
  ```

  The `id` values must be selected PLUTO particle IDs from the final sparse
  window. `loss_factor` values must be finite and non-negative.
- Prove that the table covers every selected ID expected by the bridge.
- Run the sparse radio bridge with `--loss-table` and produce the external
  PRAiSE-compatible map, lobe summary, metadata, and compact archive.
- Preserve and compare the pressure-history proxy path as the reference
  baseline, at least through metadata and lobe-summary comparison.
- Record whether the new loss-factor distribution is qualitatively plausible
  relative to the May 5 Myr PRAiSE smoke and the June pressure-history proxy.
- Keep caveats explicit: sparse-window history, no final grid/tracer volume
  coupling, no beam convolution, no final observable-comparison page.

## Validation Gates

Local gates before remote submission:

```bash
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Also run focused tests for any new helper scripts or modules. For every new or
edited PBS wrapper listed by `git diff --name-only -- 'scripts/kunanyi/*.pbs'`,
run `bash -n` on that exact file and record the path and result in `Log.md`.

Remote validation ladder:

1. Read-only remote preflight: verify the final sparse-window input, final
   production output directory, PRAiSE runtime, Python environment, and required
   staged files.
2. Smoke gate: run the new sparse PRAiSE path on a small deterministic subset
   of selected IDs or an otherwise bounded equivalent. Confirm finite,
   non-negative loss factors, selected-ID coverage, and stable metadata.
3. Reproducibility gate: if the new path enters the Numba PRAiSE code, compare
   `NUMBA_NUM_THREADS=1` and `4` on the same smoke subset. If it does not,
   rerun the same smoke command twice. Exact bitwise equality is ideal; small
   numerical differences are acceptable only if quantified and justified.
4. Full selected-ID run: generate the loss table for the final selected IDs.
5. Bridge gate: run `sparse_particle_radio_bridge.py --loss-table` against the
   full selected-ID table and verify the output metadata reports
   `loss_model_key = external_praise_compatible`.

If a remote PBS job remains queued/running for too long to monitor sensibly in
one session, wake X-ray Cavities with the job ID, queue state, staged paths, and
the exact command needed to resume inspection.

## Deliverables

Successful path deliverables:

- Code and PBS/helper changes needed for the sparse PRAiSE selected-ID table.
- Updated tests.
- Remote job records, status markers, stdout/stderr summaries, and checksums.
- A compact selected-ID loss table or compact sample plus a remote pointer if
  the full table should remain remote.
- External-loss sparse bridge products or compact archive.
- A science note under `docs/science/`, dated 2026-06-11 unless the work spans
  later.
- An exchange log under `docs/exchange/logs/`.
- Updated `docs/goals/002-final-sparse-praise-loss-table/Log.md`.
- Final wake-up to X-ray Cavities with git status, validation, artefacts,
  residual risks, and recommended next goal.

Blocked path deliverables:

- Minimal failing command or PBS job record.
- Error trace or stdout/stderr excerpt sufficient to diagnose the interface
  contract.
- Evidence that dense all-history cache construction was not attempted.
- A concise decision note explaining whether the next step is a code refactor,
  a physics/science decision for Stas or Patrick, or a remote-runtime issue.
- Updated `Log.md` and final wake-up.

## Decision Authority

You may decide:

- whether to implement a new helper script or adapt an existing smoke script;
- exact compact artefact names, provided they follow existing repo conventions;
- the smoke subset size, provided it is deterministic and small;
- whether a numerical reproducibility result is acceptable when it is bounded,
  quantified, and scientifically harmless for this interface gate.

Pause and ask X-ray Cavities before:

- changing physical constants, PRAiSE parameters, tracer thresholds, redshift,
  observing frequency, or sparse-window selection;
- building any dense all-history cache;
- launching multi-node or long-walltime jobs beyond the narrow smoke/full-table
  need;
- editing UTAS AGN source repos;
- treating the result as a final science radio product;
- committing or pushing.

## Stop Conditions

Stop when one of these is true:

- all validation gates pass and the deliverables are ready for orchestrator
  review;
- the sparse PRAiSE path fails for a clear contract reason that requires a
  scientific or upstream-code decision;
- remote access is blocked after using the authorized jumpbox-enablement route;
- unexpected dirty state exists before editing;
- the same blocker repeats and no meaningful progress is possible.

## Final Response Requirements

Report:

- status: complete, blocked, or queued/running;
- changed files;
- remote jobs submitted and their outcomes;
- validation commands and exact results;
- current `git status --short --branch`;
- where the selected-ID loss table and bridge products live;
- what remains scientifically provisional;
- recommendation for the next orchestrator decision.
