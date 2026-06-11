# Runbook: Goal 005 C-HI Final Endpoint X-ray/Cavity Alignment Gate

## Launch

Start from:

```bash
cd /Users/bwbrook/papers/xray_cavities
pwd
git status --short --branch
git rev-parse --short HEAD
```

Record the output in `Log.md` before editing.

## Read Order

Read:

```text
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Goal.md
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Plan.md
AGENTS.md
README.md
docs/exchange/current_status.md
docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md
docs/science/c_hi_xraise_grid_smoke_2026-05-10.md
docs/science/c_hi_cavity_stub_2026-05-10.md
docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md
docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
scripts/science/xraise_grid_smoke.py
scripts/science/plot_xraise_grid_smoke.py
scripts/science/pluto_h5_cavity_stub_extract.c
scripts/science/plot_cavity_stub.py
scripts/science/build_aligned_smoke_comparison.py
scripts/science/build_final_volume_coupled_comparison.py
scripts/kunanyi/c_hi_xraise_grid_smoke.pbs
scripts/kunanyi/c_hi_cavity_stub.pbs
scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
```

Read other repo-local files only as needed for exact paths or established
patterns. Do not read other repos. The remote final HDF5 input and remote
output/staging paths named in this packet are explicitly allowed.

## Inputs

Final HDF5 endpoint:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
```

Final timestep:

```text
Timestep_51
```

Accepted local truth/radio artefacts start under:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
```

Use `0 deg`, projected along simulation `y`, and preserve the existing
`tracer > 5e-3`, `1 keV`, and Goal 003 radio contracts.

## Remote Staging Discipline

Before remote submission, record the local file hashes for every staged script
or wrapper. On the remote side, verify the staged file hashes match.

Use a date-scoped remote output root such as:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment
```

Use a compact archive path such as:

```text
/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/final_endpoint_xray_cavity_alignment_2026-06-11.tar.gz
```

If SSH access requires the TPAC jumpbox selector, use Chrome or Computer Use
only to enable the narrow SSH window, then return to terminal-first commands.

## Local Validation Before Remote Work

Run the relevant existing regression tests:

```bash
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Run focused tests for new helper logic, for example:

```bash
uv run pytest tests/test_final_xray_cavity_alignment.py -q
```

For every new or edited PBS wrapper reported by:

```bash
git diff --name-only -- 'scripts/kunanyi/*.pbs'
```

run:

```bash
bash -n <that-wrapper>
```

## Remote Validation

1. Confirm the final HDF5 file exists, is readable on a compute node, and
   contains `Timestep_51`.
2. Confirm the XRAiSE correction-table inputs and runtime modules are
   available before running the extraction.
3. Run the final endpoint X-ray/cavity post-processing.
4. Confirm X-ray outputs are finite and nonblank.
5. Confirm cavity outputs have finite lobe geometry, pressure, density, `pV`,
   `4pV`, and labelled age estimates, or record the exact failed assumption.
6. Write compact products and a remote archive.
7. Pull only compact products needed for review.
8. Record job ID, stdout/stderr summary, output root, archive path, archive
   SHA-256, and resource notes where available.

## Alignment Package

The alignment package should include:

- `final_xray_summary.csv` or an equivalent X-ray scalar table;
- `final_cavity_summary.csv` or an equivalent cavity lobe table;
- an alignment comparison table joining cavity values with accepted Level 1/2
  truth and Goal 003 radio scalars;
- metadata recording input paths, timestep, view, thresholds, photon energy,
  remote job ID, script hashes, and caveats;
- at least one review figure showing the final X-ray map, tracer contour or
  mask, and projected cavity boundaries if the data support it.

## Documentation

Create:

```text
docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md
docs/exchange/logs/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment.md
```

Update:

```text
docs/goals/005-c-hi-final-endpoint-xray-cavity-alignment/Log.md
```

Update `docs/exchange/current_status.md` if the practical state changes.

## Final Validation

Run:

```bash
git diff --check
```

Run all focused and relevant regression tests recorded in `Goal.md`.

Repeat `bash -n` for every new or edited PBS wrapper.

## Hard Stops

Stop immediately before:

- launching or preparing a new PLUTO production run;
- broadening to `C-LO`, `G-LO`, `45 deg`, `90 deg`, source-age sampling, beam
  modelling, detector response, or Level 3 ambient energy;
- changing science defaults or product contracts;
- editing any repo outside `/Users/bwbrook/papers/xray_cavities`;
- treating proxy age estimates as final physics;
- committing or pushing.

## Wake-Up Rule

When complete or blocked, send a short wake-up to X-ray Cavities with:

- status;
- changed files;
- validation results;
- remote job IDs and product paths;
- current `git status --short --branch`;
- headline alignment result;
- caveats and next-goal recommendation.
