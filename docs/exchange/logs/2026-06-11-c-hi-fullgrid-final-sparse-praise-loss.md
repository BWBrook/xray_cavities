# 2026-06-11 C-HI full-grid final sparse PRAiSE-compatible loss table

## Context

Goal 001 made the sparse radio bridge consume an external `id,loss_factor`
table. Goal 002 generated the first real final sparse selected-ID
PRAiSE-compatible table from the completed 50 Myr `C-HI` run and passed it
through that external-table bridge.

The dense all-history particle HDF5 path was not used.

## Local Tooling

Added:

- `scripts/science/sparse_praise_loss_table.py`
- `scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs`
- `tests/test_sparse_praise_loss_table.py`

Local validation:

```text
uv run pytest tests/test_sparse_praise_loss_table.py -q
2 passed in 0.15s

uv run pytest tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
14 passed in 0.72s

bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs
passed
```

## Remote Staging

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss
```

Remote output root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss
```

Staged file SHA-256 values matched local values:

```text
1710ea53916a5c95379c88a306bcca07f9fedf6ab49a90eb02424687b3e944db  sparse_praise_loss_table.py
00dbd2acd99bbcd3ab2a2ba13be73060e5c0b53dfd6cbbfd413c7587f7bb6716  sparse_particle_radio_bridge.py
af8705e0f625b756eb37dc3ba2d738ecc5f5382e13dcb2c3a0d581a1a9afe8b3  pluto_particle_sparse_window.py
eb36aa01eb9a593580e47f6e7f983eeee85524686aca1b1819ff234836c48098  c_hi_fullgrid_final_sparse_praise_loss.pbs
```

## Submission And Results

Smoke, one thread:

```text
qsub -v RUN_LABEL=smoke_threads1,MAX_SELECTED_IDS=64,DO_BRIDGE=0,NUMBA_NUM_THREADS=1 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697866.kunanyi-ohpc
result: completed
loss_table_sha256: c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
```

Smoke, four threads:

```text
qsub -v RUN_LABEL=smoke_threads4,MAX_SELECTED_IDS=64,DO_BRIDGE=0,NUMBA_NUM_THREADS=4 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697869.kunanyi-ohpc
result: completed
loss_table_sha256: c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
```

The two smoke loss tables matched exactly.

Full run plus bridge:

```text
qsub -v RUN_LABEL=full,MAX_SELECTED_IDS=0,DO_BRIDGE=1,NUMBA_NUM_THREADS=4 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697872.kunanyi-ohpc
result: completed
```

Full loss-table metrics:

- selected IDs: `20000`
- finite loss factors: `20000`
- positive loss factors: `19777`
- NaN loss factors: `0`
- minimum loss factor: `0.0`
- maximum loss factor: `2.5362859154522237`
- mean loss factor: `0.9928540493456512`
- loss-table SHA-256:
  `23cbcb4ea85dae35689648dc6e63489a9403a51055e4fa462f6b9b8ddec2c320`

Bridge metadata confirmed:

```text
loss_model_key = external_praise_compatible
matched_selected_ids = 20000
extra_ids = 0
table_rows = 20000
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/full_sparse_praise_loss_2026-06-11.tar.gz
sha256=ba8b39378d351728c5424871917a1891b488e1b83ab7de8f4597208d0cbd8392
```

The only remote stderr content was the known XRAiSE/PRAiSE
`NumbaParallelSafetyWarning` from `xraise.py`.

## Local Review Assets

Pulled compact products into:

```text
docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/
```

Science note:

```text
docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
```

## Decision

Goal 002 is green as an interface/provenance product: the final sparse
selected IDs now have a real PRAiSE-compatible external loss table and the
Goal 001 bridge accepts it.

Treat the radio map and luminosities as continuity-scale products only. The
next science goal should review the implementation and then decide how to
couple this sparse selected-ID contract to final grid/tracer volume coupling
and the observable-comparison page.
