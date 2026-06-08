# 2026-06-08 C-HI full-grid final particle sparse window

## Context

The endpoint particle summary completed cleanly, but the full-history
particle-HDF5 feasibility preflight ruled out a naive dense cache over all
`5001` particle outputs. The next bounded science step was a sparse trajectory
window around the final endpoint.

## Local Tooling

Added:

- `scripts/science/pluto_particle_sparse_window.py`
- `scripts/kunanyi/c_hi_fullgrid_final_particle_sparse_window.pbs`
- `tests/test_pluto_particle_sparse_window.py`

The tests use synthetic PLUTO particle files to cover:

- target-output tracer/density/pressure selection
- deterministic selected-ID capping
- long-format selected trajectories
- per-ID lifecycle coverage
- per-output side summaries

Local TDD/verification commands:

```text
uv run pytest tests/test_pluto_particle_sparse_window.py -q
python3 -m py_compile scripts/science/pluto_particle_sparse_window.py
bash -n scripts/kunanyi/c_hi_fullgrid_final_particle_sparse_window.pbs
```

## Remote Staging

Remote control used the authenticated Chrome Kunanyi shell because plain SSH
control-socket auth was unavailable.

Staged files matched local SHA-256:

- `psw.py`:
  `af8705e0f625b756eb37dc3ba2d738ecc5f5382e13dcb2c3a0d581a1a9afe8b3`
- `psw.pbs`:
  `c14f21c20a514b1f641b421a88ad6ccbbcc46870d0a8e59ee9089ff25696c371`

The login-node `python3` is too old for `from __future__ import annotations`,
but the submitted PBS job loads `Anaconda3/2024.02-1` and ran successfully.

## Submission

```text
qsub psw.pbs
697644.kunanyi-ohpc
```

Window configuration:

- target index: `5000`
- start index: `4950`
- end index: `5000`
- stride: `5`
- tracer threshold: `0.005`
- max selected IDs: `20000`

## Result

- PBS job: `697644.kunanyi-ohpc`
- job name: `c_hi_psw_fin`
- result: `Exit_status = 0`
- walltime used: `00:01:04`
- CPU time: `00:00:13`
- peak memory: `92200kb`
- peak virtual memory: `684996kb`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stderr size: `0` bytes

Remote output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.tar.gz
```

Archive SHA-256:

```text
9894f2dfc6cae5b76257b1c5b66b9438fdc25424d66d43ea68df1b2dbc80dc62
```

Output sizes:

- `particle_sparse_window_lifecycle.csv`: `3873818` bytes
- `particle_sparse_window_metadata.json`: `229654` bytes
- `particle_sparse_window_side_summary.csv`: `1612` bytes
- `particle_sparse_window_summary.csv`: `4782` bytes
- `particle_sparse_window_trajectory.tsv`: `59070780` bytes

## Headline Metrics

- target candidates: `195558`
- selected IDs: `20000`
- trajectory rows: `218909`
- window indices:
  `[4950, 4955, 4960, 4965, 4970, 4975, 4980, 4985, 4990, 4995, 5000]`
- final-output selected split:
  - negative-z: `9945`
  - positive-z: `10055`

## Decision

Sparse-window particle extraction is green. The next step is to connect this
bounded trajectory product to particle-loss/radio calculations rather than
returning to dense all-history particle-HDF5 preprocessing.
