# 2026-06-11 C-HI full-grid final volume-coupled comparison

## Context

Goal 001 made the sparse radio bridge consume an external `id,loss_factor`
table. Goal 002 generated the first final sparse selected-ID
PRAiSE-compatible loss table and ran it through that bridge. Goal 003 coupled
that existing sparse bridge to final grid/tracer lobe volumes from the
completed 50 Myr `C-HI` endpoint.

No dense all-history particle HDF5 cache was built, no new PLUTO segment was
run, and no scientific defaults were changed.

## Local Tooling

Added:

- `scripts/science/build_final_volume_coupled_comparison.py`
- `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs`
- `tests/test_final_volume_coupled_comparison.py`

Pre-remote local validation:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.92s

bash -n scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
passed
```

## Remote Staging

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison
```

Remote output root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison
```

Remote preflight:

```text
host: <kunanyi-login-host>
utc: 2026-06-11T02:50:00Z
final HDF5: present/readable, 42G
Goal 002 full loss table: present/readable, 503K
final sparse-window trajectory: present/readable, 57M
bash -n c_hi_fullgrid_final_volume_coupled_comparison.pbs: passed
```

Staged file SHA-256 values matched local values:

```text
d01d9be561440937a60ca5872112fe6fe149d6e6c4b81acb29e9f0eef43923a3  pluto_h5_truth_extract.c
00dbd2acd99bbcd3ab2a2ba13be73060e5c0b53dfd6cbbfd413c7587f7bb6716  sparse_particle_radio_bridge.py
8e8d49106daf7c135c01deb461fd33eb3abf0efb129c2625655112f1260a28ca  build_final_volume_coupled_comparison.py
716eb96bc316a441ecc97496a58ca1d6c33ee03f5cfaa1b864f6b826a43c2726  c_hi_fullgrid_final_volume_coupled_comparison.pbs
87774ec9c3b16f21e266f965be4fc8620ab631647af27d9240077fee77baa9f1  goal003_volume_coupled_stage.tar.gz
```

## Submission And Results

Submitted bounded one-node final truth extraction plus volume-coupled bridge:

```text
qsub c_hi_fullgrid_final_volume_coupled_comparison.pbs
job: 697875.kunanyi-ohpc
result: completed
bridge_validation=passed
finished_utc=2026-06-11T02:55:35Z
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison/final_volume_coupled_comparison_2026-06-11.tar.gz
sha256=0fe05b959843748aec1fdbdd0e08a871e03dccfb3017b78351b31f9c569a0083
```

Final `tracer > 5e-3` declared volumes:

- negative z: `367123.31815126061 kpc^3`
- positive z: `373343.26830024854 kpc^3`
- bipolar total: `740466.58644933475 kpc^3`

Bridge metadata confirmed:

```text
loss_model_key = external_praise_compatible
volume_assignment = declared side volumes divided evenly across selected particles
matched_selected_ids = 20000
extra_ids = 0
table_rows = 20000
```

Volume-coupled bridge headline metrics:

- selected particles: `20000`
- positive radio pixels: `11783`
- max external-loss map value: `4.622467967906506e17 mJy sr^-1`
- external-loss map sum: `1.3830684314552033e18 mJy sr^-1 pixels`
- negative-z external-loss luminosity: `5.20526129346918e28 W Hz^-1`
- positive-z external-loss luminosity: `1.1343085864598182e29 W Hz^-1`
- bipolar external-loss luminosity: `1.6548347158067362e29 W Hz^-1`

Compared with the Goal 002 sparse PRAiSE bridge, the new volume coupling
scales the old `1.0 kpc^3` per selected particle lobe volumes by:

- negative z: `36.9154`
- positive z: `37.1301`
- bipolar total: `37.0233`

## Local Review Assets

Pulled compact products into:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
```

Generated local comparison package:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/comparison/declared_volume_truth.csv
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/comparison/lobe_volume_coupling_comparison.csv
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/comparison/comparison_metadata.json
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/comparison/comparison_summary.md
```

Science note:

```text
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
```

## Decision

Goal 003 is green as a bounded final-volume coupling comparison product. Treat
the product as a provenance and scalar-comparison package only, not as a final
publication-ready observable. The next review should inspect the helper,
wrapper, science note, product artefacts, and validation gates, then decide
whether to proceed to a final observable-comparison or manuscript-facing review
goal.
