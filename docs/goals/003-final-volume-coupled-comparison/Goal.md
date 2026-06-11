# Goal 003: Final Volume-Coupled Comparison Page

## Objective

Extract final grid/tracer lobe volumes for the completed 50 Myr `C-HI`
endpoint, rerun the Goal 001/002 sparse PRAiSE radio bridge with those side
volumes, and package a compact final endpoint comparison page.

This goal is complete when the repo contains reviewable code, provenance, and
science notes showing either:

- a green volume-coupled final comparison product using the final
  `tracer > 5e-3` negative-z and positive-z lobe volumes; or
- a sharply documented blocker proving which grid/tracer, bridge, or remote
  runtime contract is missing.

## Why This Matters

Goal 001 built the external loss-table bridge. Goal 002 generated the first
real final sparse selected-ID PRAiSE-compatible loss table and ran it through
that bridge, but the radio luminosities still used the temporary
`1.0 kpc^3` per selected particle continuity scale.

Goal 003 should remove that particular provisional scale by tying the sparse
particle radio product to final grid/tracer side volumes. It should also create
the first honest final endpoint comparison page: useful for review and next
scientific decisions, but not pretending to be a publication-ready observable
product.

## Operating Mode

Remote-assisted implementation and validation with local tests first.

Use local development for parsers, report assembly, figure assembly, and tests.
Use `kunanyi` only for bounded final HDF5 truth extraction and any bridge run
that needs remote products. If SSH access requires the TPAC "Enable Jumpbox
SSH" selector, use Chrome or Computer Use for that narrow access step, then
return to terminal-first workflow.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- new or changed tests;
- PBS wrappers or remote-run helpers;
- `docs/goals/003-final-volume-coupled-comparison/Log.md`;
- remote stdout/stderr excerpts, job IDs, checksums, and status markers;
- compact local artefacts under `docs/science/` and
  `docs/science/assets/`;
- the final interpretation, caveats, and recommendation for Goal 004.

## Scope

In scope:

- Reuse or narrowly adapt `scripts/science/pluto_h5_truth_extract.c` to produce
  final endpoint Level 1 injected-energy and Level 2 tracer-lobe truth tables.
- Add a final-specific PBS wrapper or staging helper if the existing truth
  wrapper is not sufficiently explicit for this endpoint.
- Use the completed final float HDF5 output:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`.
- Use timestep `Timestep_51`.
- Use the existing default Level 2 truth threshold `tracer > 5e-3` for the
  volume-coupling bridge inputs.
- Extract the negative-z and positive-z `volume_kpc3` values from
  `level2_tracer_lobe_truth.csv`, not the temporary selected-particle counts.
- Rerun `scripts/science/sparse_particle_radio_bridge.py` with:
  - the Goal 002 full `sparse_praise_loss_table.csv`;
  - `--negative-volume-kpc3` set from final Level 2 truth;
  - `--positive-volume-kpc3` set from final Level 2 truth.
- Verify the bridge metadata reports the declared-volume assignment and the
  external PRAiSE-compatible loss-table contract.
- Build a compact comparison package that includes, at minimum:
  - final quick-look context from the June 7 endpoint report;
  - final Level 1 injected-energy accounting;
  - final Level 2 tracer-lobe side volumes and energies;
  - Goal 002 loss-table provenance and metrics;
  - volume-coupled sparse radio lobe summaries;
  - comparison against the Goal 002 `1.0 kpc^3` continuity-scale radio summary;
  - explicit caveats for missing beam convolution, dense all-history particle
    loss history, and full final XRAiSE/cavity products.
- Add focused local tests for any new CSV/JSON parsing, volume selection,
  comparison metrics, metadata checks, or report assembly logic.
- Pull only compact review artefacts into the repo, following existing
  `docs/science/assets/` conventions.
- Write a concise dated science note and exchange log.
- Update `docs/exchange/current_status.md` if the practical project state
  materially changes and the update can be kept compact.

Out of scope:

- Do not build a dense all-history `plutokore.load_all_particles()` HDF5 cache.
- Do not rerun the Goal 002 loss-table generation unless an input-integrity
  defect is found.
- Do not change the established Goal 001/002 `--loss-table` external-table
  contract.
- Do not change scientific defaults such as `eta`, `s`, `gmin`, `gmax`,
  frequency, redshift, tracer threshold, sparse-window start/end/stride, or
  selected-ID population without pausing for X-ray Cavities.
- Do not run a new full PLUTO simulation segment.
- Do not beam-convolve the radio map.
- Do not claim a final publication-ready observable comparison.
- Do not require a full final XRAiSE corrected 1 keV map or final cavity `pV`
  measurement unless a bounded existing product is already available and the
  route is clearly documented.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, or sibling project repos.
- Do not edit local UTAS AGN source checkouts under
  `/Users/bwbrook/git/utas-agn` unless X-ray Cavities explicitly authorizes it.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/goals/002-final-sparse-praise-loss-table/Goal.md`
- `docs/goals/002-final-sparse-praise-loss-table/Log.md`
- `docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md`
- `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md`
- `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`
- `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
- `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
- `scripts/science/sparse_particle_radio_bridge.py`
- `scripts/science/sparse_praise_loss_table.py`
- `scripts/science/pluto_h5_truth_extract.c`
- `scripts/science/build_aligned_smoke_comparison.py`
- relevant existing PBS wrappers under `scripts/kunanyi/`, starting with
  `scripts/kunanyi/c_hi_truth_extract.pbs` and
  `scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs`

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `e715c79`, clean against
`origin/main`, unless X-ray Cavities has fast-forwarded the repo before
delegation.

If unexpected dirty state exists before editing, stop and wake X-ray Cavities.

## Required Work

- Determine the smallest reliable way to run final grid/tracer truth
  extraction on `data.0051.flt.h5` without duplicating the full output locally.
- Confirm or adapt the remote memory envelope for reading the required HDF5
  variables. The June quick-look extractor succeeded in a `32gb` envelope but
  the truth extractor reads more full fields, so use a conservative bounded
  request and record actual memory use if PBS reports it.
- Produce `level1_injected_energy.csv`, `level2_tracer_lobe_truth.csv`, and
  metadata for the final endpoint.
- Select the `threshold = 5e-3` negative-z and positive-z `volume_kpc3` values
  as the declared side volumes for the radio bridge.
- Rerun the sparse particle radio bridge with the Goal 002 full loss table and
  declared side volumes.
- Verify the bridge output side volumes agree with the declared truth volumes
  within CSV roundoff.
- Build a comparison page that makes the scale change visible:
  - old Goal 002 proxy-volume side volumes and luminosities;
  - new grid/tracer-volume side volumes and luminosities;
  - final tracer truth energies and extents;
  - a clear interpretation of what improved and what remains provisional.
- Keep all caveats explicit and prominent enough for Stas, Patrick, or Barry
  to review the scientific status without reverse-engineering the tooling.

## Validation Gates

Local gates before remote submission:

```bash
uv run pytest tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Also run focused tests for any new helper scripts or modules. For every new or
edited PBS wrapper listed by `git diff --name-only -- 'scripts/kunanyi/*.pbs'`,
run `bash -n` on that exact file and record the path and result in `Log.md`.

Remote validation ladder:

1. Read-only remote preflight: verify the final HDF5 path, timestep name,
   Goal 002 full loss table or archive, staged scripts, and module/compiler
   environment.
2. Truth extraction: run the final Level 1/2 extraction on a compute node.
   Confirm row coverage for thresholds `1e-3`, `5e-3`, and `1e-2`, with
   negative-z, positive-z, and bipolar rows for each threshold.
3. Volume selection: verify the selected `5e-3` negative-z and positive-z
   volumes are finite, positive, and sum to the corresponding bipolar row
   within a small numerical tolerance.
4. Bridge gate: run `sparse_particle_radio_bridge.py --loss-table` with the
   selected side volumes and confirm metadata reports:
   - `loss_model_key = external_praise_compatible`;
   - no missing selected IDs;
   - no extra loss-table IDs;
   - declared side-volume assignment.
5. Comparison package: build local compact tables, figures if useful, and a
   dated science note from machine-readable artefacts.
6. Diff hygiene: run `git diff --check`.

If a remote PBS job remains queued/running for too long to monitor sensibly in
one session, wake X-ray Cavities with the job ID, queue state, staged paths,
and exact command needed to resume inspection.

## Deliverables

Successful path deliverables:

- Code and PBS/helper changes needed for final truth extraction, volume
  selection, volume-coupled bridge execution, and comparison packaging.
- Updated tests.
- Remote job records, status markers, stdout/stderr summaries, resource usage
  where available, and checksums.
- Final Level 1 and Level 2 truth CSVs or compact local copies.
- Volume-coupled external-loss sparse radio bridge products.
- A compact comparison package under
  `docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/`
  unless the work spans a later date.
- A science note under
  `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
  unless the work spans a later date.
- An exchange log under `docs/exchange/logs/`.
- Updated `docs/goals/003-final-volume-coupled-comparison/Log.md`.
- Final wake-up to X-ray Cavities with git status, validation, artefacts,
  residual risks, and recommended next goal.

Blocked path deliverables:

- Minimal failing command or PBS job record.
- Error trace or stdout/stderr excerpt sufficient to diagnose the failed
  contract.
- Evidence that dense all-history cache construction was not attempted.
- A concise decision note explaining whether the next step is a code refactor,
  a physics/science decision for Stas or Patrick, or a remote-runtime issue.
- Updated `Log.md` and final wake-up.

## Decision Authority

You may decide:

- whether to reuse the generic truth extractor or add a final-specific wrapper;
- exact compact artefact names, provided they follow existing repo
  conventions;
- whether the comparison page is Markdown-only or includes a generated figure;
- how to structure comparison tables and metadata, provided they are generated
  from machine-readable outputs rather than copied by hand;
- whether a small helper refactor is worthwhile to make tests clean.

Pause and ask X-ray Cavities before:

- changing physical constants, PRAiSE parameters, tracer thresholds, redshift,
  observing frequency, or sparse-window selection;
- building any dense all-history cache;
- launching multi-node or long-walltime jobs beyond the bounded final truth
  extraction and bridge rerun;
- editing UTAS AGN source repos;
- treating the result as a final science radio/X-ray/cavity product;
- committing or pushing.

## Stop Conditions

Stop when one of these is true:

- all validation gates pass and the deliverables are ready for orchestrator
  review;
- final truth extraction or volume coupling fails for a clear contract reason
  that requires a scientific or upstream-code decision;
- remote access is blocked after using the authorized jumpbox-enablement route;
- the required job is still queued/running beyond a sensible monitoring window.
