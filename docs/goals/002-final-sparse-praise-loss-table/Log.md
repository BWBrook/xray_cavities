# Log: Goal 002 Final Sparse PRAiSE Loss Table

## 2026-06-11 - X-ray Cavities goal creation

Created by the X-ray Cavities orchestrator after accepting Goal 001.

Action repo state before writing this packet:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 77fadd2
```

Goal 001 added and published the local `--loss-table` interface for
`scripts/science/sparse_particle_radio_bridge.py`. Goal 002 is the bounded
remote follow-up: generate a real final sparse selected-ID PRAiSE-compatible
loss table, run the bridge through that table, and document either a green
provisional product or a precise blocker.

No project implementation, remote staging, remote job, data workflow, or
validation run was performed by the orchestrator while creating this packet.

## 2026-06-11 - jet starting state

Started Goal 002 from the active packet.

Starting state checked before edits:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD ee5df03
```

Working tree was clean before Goal 002 edits. The launch HEAD differs from the
packet's expected `77fadd2`, but the repo is clean and even with `origin/main`,
consistent with a pre-delegation fast-forward by X-ray Cavities.

## 2026-06-11 - jet local implementation

Read the Goal 002 packet and required local context, including the Goal 001
loss-table interface note, June final sparse-window/radio bridge notes, May
PRAiSE particle-loss/radio smokes, and the existing Kunanyi PBS wrappers.

Remote read-only preflight:

```text
scripts/kunanyi/run_on_kunanyi.sh 'hostname; date -u +%Y-%m-%dT%H:%M:%SZ; ...'
initial result: MFA check failed; TPAC jumpbox SSH window needed enabling
```

Used the authorized narrow Chrome/Computer Use route to open the TPAC
`Enable Jumpbox SSH` page. The portal reported a 5-minute window ending at
`Thu Jun 11 11:57:00 2026`.

Remote preflight after enablement:

```text
host: <tpac-host>
utc: 2026-06-11T01:52:24Z
sparse_window=present
final_particles=present
runtime=present
```

Remote sparse-window files:

```text
particle_sparse_window_lifecycle.csv      3873818 bytes
particle_sparse_window_metadata.json       229654 bytes
particle_sparse_window_side_summary.csv      1612 bytes
particle_sparse_window_summary.csv           4782 bytes
particle_sparse_window_trajectory.tsv    59070780 bytes
```

Read-only inspection of `/u/bwbrook/codex_kunanyi/particle_loss_runtime/xraise.py`
showed that `praise(...)` consumes particle data arrays for `density`,
`pressure`, `tracer`, and `last_shock_time`; this means the sparse selected-ID
helper must read the original final PLUTO particle outputs for the bounded
window, not only the existing sparse trajectory TSV, because that TSV does not
carry `last_shock_time`.

Implemented:

- `scripts/science/sparse_praise_loss_table.py`
  - reads selected IDs and window indices from the final sparse-window metadata;
  - reads only those IDs over the bounded sparse-window PLUTO particle outputs;
  - shapes the minimal particle arrays needed by the staged XRAiSE/PRAiSE
    `praise(...)` call;
  - writes `sparse_praise_loss_table.csv` with `id,loss_factor`;
  - writes metadata, summary, first-1000 sample, and SHA-256 provenance.
- `tests/test_sparse_praise_loss_table.py`
  - tests selected-ID matrix shaping, missing-output coverage, and an
    end-to-end fake-XRAiSE table writer.
- `scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs`
  - supports deterministic smoke subsets, full selected-ID table generation,
    and optional Goal 001 bridge execution through `--loss-table`.

TDD checkpoint:

```text
uv run pytest tests/test_sparse_praise_loss_table.py -q
initial result after adding tests: 2 failed
failure reason: scripts/science/sparse_praise_loss_table.py did not exist yet
```

Focused post-implementation check:

```text
uv run pytest tests/test_sparse_praise_loss_table.py -q
2 passed in 0.15s
```

Local validation gate:

```text
uv run pytest tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
14 passed in 0.72s
```

PBS syntax:

```text
bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs
passed
```

## 2026-06-11 - jet remote smoke checkpoint

Staged the local helper, Goal 001 bridge script, sparse-window reader, and PBS
wrapper under:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss
```

Remote staged SHA-256 values matched the local files:

```text
1710ea53916a5c95379c88a306bcca07f9fedf6ab49a90eb02424687b3e944db  sparse_praise_loss_table.py
00dbd2acd99bbcd3ab2a2ba13be73060e5c0b53dfd6cbbfd413c7587f7bb6716  sparse_particle_radio_bridge.py
af8705e0f625b756eb37dc3ba2d738ecc5f5382e13dcb2c3a0d581a1a9afe8b3  pluto_particle_sparse_window.py
eb36aa01eb9a593580e47f6e7f983eeee85524686aca1b1819ff234836c48098  c_hi_fullgrid_final_sparse_praise_loss.pbs
```

Submitted 1-thread smoke:

```text
qsub -v RUN_LABEL=smoke_threads1,MAX_SELECTED_IDS=64,DO_BRIDGE=0,NUMBA_NUM_THREADS=1 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697866.kunanyi-ohpc
```

Result: completed successfully on node `n186.kunanyi`.

Key smoke outputs:

```text
output_dir=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/smoke_threads1
selected_id_count=64
loss_table_sha256=c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
loss_factor_finite_count=64
loss_factor_positive_count=63
loss_factor_nan_count=0
loss_factor_min=0.0
loss_factor_max=1.1715045144905087
loss_factor_mean=0.9904199134320749
```

Generated smoke files:

```text
sparse_praise_loss_metadata.json          1946 bytes
sparse_praise_loss_summary.csv             712 bytes
sparse_praise_loss_table.csv              1648 bytes
sparse_praise_loss_table_first1000.tsv    1648 bytes
```

Archive:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/smoke_threads1_sparse_praise_loss_2026-06-11.tar.gz
sha256=6665acc3e8b58e6ecb32ea8d03d9543374c7165a77d9f48c937d630f176756d8
```

The only stderr content was the existing XRAiSE/PRAiSE
`NumbaParallelSafetyWarning` from `xraise.py`.

Submitted 4-thread smoke for determinism comparison:

```text
qsub -v RUN_LABEL=smoke_threads4,MAX_SELECTED_IDS=64,DO_BRIDGE=0,NUMBA_NUM_THREADS=4 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697869.kunanyi-ohpc
```

Result: completed successfully on node `n186.kunanyi`.

Key 4-thread smoke outputs:

```text
output_dir=/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/smoke_threads4
selected_id_count=64
loss_table_sha256=c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
loss_factor_finite_count=64
loss_factor_positive_count=63
loss_factor_nan_count=0
loss_factor_min=0.0
loss_factor_max=1.1715045144905087
loss_factor_mean=0.9904199134320749
```

Smoke determinism comparison:

```text
smoke_threads1 sparse_praise_loss_table.csv sha256 = c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
smoke_threads4 sparse_praise_loss_table.csv sha256 = c70c90b3175b0febf35bd6804e1e25b96d2aeda6386f81fcb4aa281107a0d358
result: exact table match
```

Archive:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/smoke_threads4_sparse_praise_loss_2026-06-11.tar.gz
sha256=8243ecf08312b1b87e6456fe2fb038de8ca1a16f3488cc6a68fe379f00fca36b
```

The only stderr content was the same existing XRAiSE/PRAiSE
`NumbaParallelSafetyWarning` from `xraise.py`.

Submitted full selected-ID PRAiSE-compatible loss table plus Goal 001 bridge:

```text
qsub -v RUN_LABEL=full,MAX_SELECTED_IDS=0,DO_BRIDGE=1,NUMBA_NUM_THREADS=4 c_hi_fullgrid_final_sparse_praise_loss.pbs
job: 697872.kunanyi-ohpc
```

## 2026-06-11 - jet full run closeout

Full selected-ID loss table plus external-loss bridge completed successfully.

Full run:

```text
job: 697872.kunanyi-ohpc
run_label=full
max_selected_ids=0
do_bridge=1
numba_num_threads=4
finished_utc=2026-06-11T02:10:57Z
```

Remote full output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/full
```

Full loss-table summary:

```text
selected_id_count=20000
target_index=5000
loss_table_sha256=23cbcb4ea85dae35689648dc6e63489a9403a51055e4fa462f6b9b8ddec2c320
loss_factor_finite_count=20000
loss_factor_positive_count=19777
loss_factor_nan_count=0
loss_factor_min=0.0
loss_factor_max=2.5362859154522237
loss_factor_mean=0.9928540493456512
loss_factor_positive_min=0.7687704937161209
loss_factor_positive_max=2.5362859154522237
loss_factor_positive_mean=1.0040491979022614
```

Bridge metadata gate:

```text
loss_model_key=external_praise_compatible
matched_selected_ids=20000
extra_ids=0
table_rows=20000
```

Bridge scalar summary:

```text
selected_particles=20000
in_frame_particles=20000
radio_map_max_mjy_sr=1.2449378189918464e+16
radio_map_sum_mjy_sr_pixel=3.731739885133339e+16
radio_positive_pixels=11783
negative_z_lossy_luminosity_doppler=1.4100527262673754e+27 W/Hz
positive_z_lossy_luminosity_doppler=3.0549560699942794e+27 W/Hz
bipolar_total_lossy_luminosity_doppler=4.465008796261656e+27 W/Hz
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/goal002_sparse_praise_loss/full_sparse_praise_loss_2026-06-11.tar.gz
sha256=ba8b39378d351728c5424871917a1891b488e1b83ab7de8f4597208d0cbd8392
```

The only remote stderr content was the known XRAiSE/PRAiSE
`NumbaParallelSafetyWarning` from `xraise.py`.

Pulled compact local review assets into:

```text
docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/
```

Added documentation:

```text
docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
docs/exchange/logs/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss.md
```

Final local validation:

```text
uv run pytest tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
14 passed in 0.81s

bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs
passed

git diff --check
passed
```

Final git status before orchestrator wake-up:

```text
## main...origin/main
 M docs/goals/002-final-sparse-praise-loss-table/Log.md
?? docs/exchange/logs/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss.md
?? docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/
?? docs/science/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11.md
?? scripts/kunanyi/c_hi_fullgrid_final_sparse_praise_loss.pbs
?? scripts/science/sparse_praise_loss_table.py
?? tests/test_sparse_praise_loss_table.py
```

Goal status: green interface/provenance product. The next orchestrator review
step should inspect the helper/tests/PBS wrapper and the science note, then
decide the next science goal for grid/tracer volume coupling and the final
observable-comparison page.

## 2026-06-11 - jet review iteration: fail-fast test lock

X-ray Cavities requested one narrow local review iteration before accepting
Goal 002. Scope was tests-only unless a real implementation defect was exposed;
no remote work or remote product rerun was performed.

Added focused tests in `tests/test_sparse_praise_loss_table.py` for:

- `validate_loss_factors(...)` rejecting non-finite values (`nan`);
- `validate_loss_factors(...)` rejecting negative values;
- `validate_loss_factors(...)` rejecting loss-factor count mismatches;
- `build_sparse_particle_data(...)` rejecting a selected ID missing at the
  target output;
- `deterministic_subset(...)` stable bounded selection, including
  `max_selected_ids=1`.

Focused check:

```text
uv run pytest tests/test_sparse_praise_loss_table.py -q
7 passed in 0.17s
```

The existing implementation satisfied these contracts, so no helper or PBS
implementation change was needed.
