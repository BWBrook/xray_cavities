# Goal 005: C-HI Final Endpoint X-ray/Cavity Alignment Gate

## Objective

Build the first final-endpoint `C-HI` X-ray plus cavity alignment gate for the
completed 50 Myr production run, using the `0 deg` view and the accepted
Level 1/2 truth and Goal 003 radio-volume scalars as comparators.

This goal is complete when the repo contains reviewable code, provenance,
compact products, and a science note showing either:

- a green final 50 Myr `C-HI`, `0 deg` XRAiSE/GRAiLE grid X-ray plus cavity
  comparison product; or
- a sharply documented blocker proving which final X-ray, cavity, remote
  runtime, or protocol contract is missing.

## Why This Matters

Goal 004 established that the first full 50 Myr `C-HI` run is a credible
prove-out anchor but does not yet prove the final X-ray path or final cavity
measurement protocol. This goal attacks that largest remaining single-case
gap without launching a new PLUTO production run or broadening to the
mandatory comparison cases.

The intended outcome is a decision-quality gate: can the project apply the
existing 5 Myr XRAiSE/cavity mechanics to the final endpoint, compare cavity
`pV`, `4pV`, and age estimates against accepted truth/radio scalars, and make
the remaining physics/protocol caveats explicit enough for Barry, Stas, and
Patrick to review?

## Operating Mode

Local-first implementation and validation, with bounded `kunanyi`
post-processing allowed for final endpoint extraction.

Use local development for scripts, parsers, tests, product assembly, and
documentation. Use `kunanyi` only for bounded post-processing against the
existing completed 50 Myr `C-HI` output. Do not launch or prepare any new
PLUTO production run.

If SSH access to `kunanyi` requires the TPAC "Enable Jumpbox SSH" selector,
use Chrome or Computer Use for that narrow access step, then return to a
terminal-first workflow.

## Review Surface

The X-ray Cavities orchestrator will review:

- the git diff;
- new or changed tests;
- new or changed PBS wrappers or remote-run helpers;
- `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`;
- remote job IDs, stdout/stderr excerpts, status markers, resource notes, and
  checksums;
- compact local artefacts under `docs/science/` and
  `docs/science/assets/`;
- the final interpretation, caveats, and recommendation for the next goal.

## Scope

In scope:

- Use the completed final float HDF5 output:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`.
- Use timestep `Timestep_51`.
- Use the initial `0 deg` view projected along the simulation `y` axis.
- Reuse or narrowly adapt the existing XRAiSE/GRAiLE grid X-ray path proven in
  the 5 Myr smoke product.
- Reuse or narrowly adapt the existing ellipsoid plus ambient-shell cavity
  protocol proven in the 5 Myr smoke product.
- Produce final endpoint X-ray map products including raw/corrected 1 keV
  maps, correction-ratio diagnostics, tracer line-of-sight mask information,
  axes, and metadata.
- Produce final endpoint cavity products including lobe summaries, projected
  boundaries, overlay figure, `pV`, `4pV`, and clearly labelled age estimates.
- Compare final cavity quantities against:
  - accepted Level 1 injected-energy truth;
  - accepted Level 2 `tracer > 5e-3` side volumes and energies;
  - accepted Goal 003 volume-coupled sparse radio scalars.
- Preserve the current scientific contracts unless an implementation blocker
  proves they are impossible:
  - `tracer > 5e-3` for Level 2 truth and cavity lobe geometry;
  - `0 deg` view only;
  - `1 keV` X-ray map;
  - no beam or instrument model;
  - no Level 3 ambient-energy method claim beyond explicit caveats.
- Add focused tests for any new local comparison, parsing, metadata,
  validation, or report-assembly helper.
- Pull only compact review artefacts into the repo, following existing
  `docs/science/assets/` conventions.
- Write a concise dated science note and exchange log.
- Update `docs/exchange/current_status.md` if the practical project state
  materially changes and the update can be kept compact.

Out of scope:

- Do not launch, stage, or prepare a new PLUTO production run.
- Do not broaden to `C-LO`, `G-LO`, `45 deg`, `90 deg`, or source-age
  sampling.
- Do not add beam convolution, detector response, exposure modelling, or other
  instrument treatment.
- Do not define or implement the final Level 3 ambient thermal/kinetic/
  gravitational energy method.
- Do not change the Goal 001/002 external loss-table contract or rerun the
  Goal 002 loss-table generation unless a blocking integrity defect is found.
- Do not change scientific defaults such as redshift, photon energy, tracer
  threshold, PRAiSE parameters, observing frequency, sparse-window selection,
  or selected-ID population without pausing for X-ray Cavities.
- Do not edit `/Users/bwbrook/chief_of_staff`,
  `/Users/bwbrook/work/goal_composer`, sibling project repos, or local UTAS
  AGN source checkouts under `/Users/bwbrook/git/utas-agn`.
- Do not make broad project, comparison-suite, or finished-observable claims.
- Do not commit or push.

## Read First

- `AGENTS.md`
- `README.md`
- `docs/exchange/current_status.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Goal.md`
- `docs/goals/004-c-hi-final-production-prove-out-gap-audit/Log.md`
- `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- `docs/science/c_hi_xraise_grid_smoke_2026-05-10.md`
- `docs/science/c_hi_cavity_stub_2026-05-10.md`
- `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md`
- `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`
- `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
- `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- `scripts/science/xraise_grid_smoke.py`
- `scripts/science/plot_xraise_grid_smoke.py`
- `scripts/science/pluto_h5_cavity_stub_extract.c`
- `scripts/science/plot_cavity_stub.py`
- `scripts/science/build_aligned_smoke_comparison.py`
- `scripts/science/build_final_volume_coupled_comparison.py`
- `scripts/kunanyi/c_hi_xraise_grid_smoke.pbs`
- `scripts/kunanyi/c_hi_cavity_stub.pbs`
- `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs`

Read other repo-local files only as needed to find exact input paths,
product conventions, helper APIs, or provenance from accepted Goals 001-004.
Do not read other repos. The remote final HDF5 input and remote output/staging
paths named in this packet are explicitly allowed.

## Starting State Checks

Before editing, record in `Log.md`:

```bash
pwd
git status --short --branch
git rev-parse --short HEAD
```

Expected starting branch at goal launch is `main` at `da41d13`, clean against
`origin/main`, unless X-ray Cavities has fast-forwarded the repo before
delegation.

If unexpected dirty state exists before editing, stop and wake X-ray
Cavities.

## Required Work

- Determine the smallest reliable adaptation from the 5 Myr XRAiSE/cavity
  smoke path to the 50 Myr final endpoint.
- Confirm the final HDF5 path, timestep name, grid shape, required variables,
  correction-table inputs, and remote module/runtime path before any PBS
  submission.
- Produce the final 50 Myr, `0 deg`, 1 keV XRAiSE/GRAiLE grid X-ray products.
- Apply the existing ellipsoid plus ambient-shell cavity protocol to the same
  final endpoint target. If the final endpoint makes the protocol numerically
  unstable or scientifically indefensible, stop with a blocker report rather
  than inventing a new protocol.
- Generate a compact alignment package that includes, at minimum:
  - X-ray scalar summary;
  - cavity lobe summary with `pV`, `4pV`, and age estimates;
  - final Level 1 injected energy;
  - final Level 2 `tracer > 5e-3` lobe volumes and energies;
  - Goal 003 radio-volume scalar references;
  - explicit caveats for proxy age estimates, missing Level 3 ambient energy,
    missing beam/instrument treatment, and absent viewing/source-age sampling.
- Verify that every comparison is side-aware where possible: negative-z,
  positive-z, and bipolar totals should not be silently mixed.
- Keep remote products compact. If the raw final arrays are too large for repo
  storage, archive them remotely and pull only TSV/CSV/JSON summaries and
  review figures needed for local review.
- Record remote commands, job IDs, output roots, archive paths, checksums, and
  stdout/stderr summaries in `Log.md` and the exchange log.

## Validation Gates

Local gates before remote submission:

```bash
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Also run focused tests for every new or edited helper. If a new helper is
named `scripts/science/build_final_xray_cavity_alignment.py`, the focused test
should be named consistently, for example:

```bash
uv run pytest tests/test_final_xray_cavity_alignment.py -q
```

For every new or edited PBS wrapper listed by:

```bash
git diff --name-only -- 'scripts/kunanyi/*.pbs'
```

run:

```bash
bash -n <that-wrapper>
```

Remote validation ladder:

1. Read-only preflight: verify final HDF5 path, timestep name, correction-table
   inputs, staged scripts, and module/runtime environment.
2. X-ray extraction: run the final 50 Myr, `0 deg`, 1 keV grid X-ray path on a
   compute node and confirm finite nonblank raw and corrected maps plus
   finite correction-ratio diagnostics.
3. Cavity extraction: run the final ellipsoid plus ambient-shell cavity path
   and confirm finite lobe geometry, ambient pressure/density, `pV`, `4pV`,
   and labelled age estimates or produce a blocker report explaining the
   failed assumption.
4. Alignment package: compare X-ray/cavity outputs with accepted final Level
   1/2 truth and Goal 003 radio scalars from local compact artefacts.
5. Hygiene: run `git diff --check`.

If a remote PBS job remains queued or running for too long to monitor sensibly
in one session, wake X-ray Cavities with the job ID, queue state, staged paths,
and exact command needed to resume inspection.

## Deliverables

Successful path deliverables:

- Code and PBS/helper changes needed for final X-ray extraction, cavity
  measurement, and alignment-package assembly.
- Focused tests for new local helper logic plus relevant existing regression
  tests.
- Remote job records, status markers, stdout/stderr summaries, resource notes
  where available, and checksums.
- Compact local final endpoint X-ray/cavity/alignment artefacts under:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`.
- Science note:
  `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`.
- Exchange log:
  `docs/exchange/logs/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment.md`.
- Updated `docs/exchange/current_status.md`, if the practical state changes.
- Updated `docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md`.
- Final wake-up to X-ray Cavities with:
  - changed files;
  - validation results;
  - remote job IDs and product paths;
  - current git status;
  - headline alignment result;
  - residual caveats and next-goal recommendation.

Blocked path deliverables:

- A concise blocker note explaining which required final endpoint X-ray,
  cavity, remote runtime, or protocol contract failed.
- Specific commands, files, stdout/stderr excerpts, and repo areas inspected.
- Whether the blocker is implementation, remote runtime, missing input data,
  or a physics/protocol decision.
- Updated `Log.md` and final wake-up.

## Decision Authority

You may decide:

- exact helper, wrapper, and test filenames;
- whether to adapt existing smoke scripts or add final-specific scripts;
- how to structure compact CSV/TSV/JSON review artefacts;
- whether the alignment package needs one figure or several small figures;
- whether remote output should be archived as one tarball or separate compact
  archives.

Pause and ask X-ray Cavities before:

- changing scientific defaults, thresholds, source parameters, redshift,
  photon energy, viewing angle, or radio/PRAiSE parameters;
- broadening to new simulations, `C-LO`, `G-LO`, additional views, source-age
  sampling, beam/instrument treatment, or Level 3 ambient-energy methods;
- editing UTAS AGN source checkouts or any repo outside this action repo;
- treating proxy buoyancy/refill ages as final physics;
- committing or pushing.

## Stop Conditions

Stop when one of these is true:

- the final `C-HI`, 50 Myr, `0 deg` X-ray/cavity alignment gate is complete
  and ready for orchestrator review;
- a blocker prevents a credible final endpoint X-ray/cavity product;
- the next step requires a Barry/Stas/Patrick science decision before it can
  be stated responsibly.
