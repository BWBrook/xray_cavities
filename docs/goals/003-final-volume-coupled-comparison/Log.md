# Log: Goal 003 Final Volume-Coupled Comparison Page

## 2026-06-11 - X-ray Cavities goal creation

Created by the X-ray Cavities orchestrator after accepting Goal 002.

Action repo state before writing this packet:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD e715c79
```

Goal 002 generated and validated the first final sparse selected-ID
PRAiSE-compatible loss table and ran the Goal 001 bridge through
`--loss-table`. The remaining high-value gap is the bridge luminosity scale:
Goal 002 still used `1.0 kpc^3` per selected particle, while final grid/tracer
truth can provide side volumes for the negative-z and positive-z lobes.

Goal 003 is the bounded follow-up: extract final Level 1/2 truth from the
completed endpoint, feed the `tracer > 5e-3` side volumes into the existing
bridge, and package a compact comparison product that is honest about what is
and is not final.

No project implementation, remote staging, remote job, data workflow, or
validation run was performed by the orchestrator while creating this packet.

## 2026-06-11 - jet starting state

Started Goal 003 from the active packet after the required fast-forward pull.

Fast-forward command:

```text
cd /Users/bwbrook/papers/xray_cavities
git pull --ff-only
Already up to date.
```

Starting state checked before edits:

```text
/Users/bwbrook/papers/xray_cavities
## main...origin/main
HEAD 4ad7f58
```

Working tree was clean before Goal 003 edits. The launch HEAD differs from the
packet's expected `e715c79`, but the repo is clean and even with `origin/main`,
consistent with a pre-delegation fast-forward by X-ray Cavities.

Read the Goal 003 packet and required local context, including Goal 002 loss
table/bridge notes, the final endpoint quick-look, final particle endpoint and
sparse-window notes, `sparse_particle_radio_bridge.py`,
`sparse_praise_loss_table.py`, `pluto_h5_truth_extract.c`, the aligned smoke
comparison builder, and the existing Kunanyi truth/sparse-PRAiSE PBS wrappers.

Initial implementation decision:

- reuse `pluto_h5_truth_extract.c` unchanged unless remote final extraction
  exposes a concrete defect;
- reuse the established Goal 001/002 `--loss-table` bridge contract;
- add a local comparison builder with tests for Level 2 volume selection,
  bridge-volume validation, and old-vs-new lobe scaling;
- add a final-specific PBS wrapper for clear Goal 003 provenance around truth
  extraction and the declared-volume bridge rerun.

## 2026-06-11 - jet local TDD and wrapper checkpoint

Added failing tests first for the new comparison builder:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py -q
initial result: 7 failed
failure reason: scripts/science/build_final_volume_coupled_comparison.py did not exist yet
```

Implemented:

- `scripts/science/build_final_volume_coupled_comparison.py`
  - reads Level 1/2 truth CSVs and bridge summaries;
  - selects the `threshold = 5e-03` negative-z, positive-z, and bipolar rows;
  - validates finite positive declared side volumes and side-volume closure;
  - validates the volume-coupled bridge metadata and lobe-summary volumes;
  - writes machine-readable comparison CSV/JSON and a compact Markdown summary.
- `tests/test_final_volume_coupled_comparison.py`
  - tests truth-volume selection, missing-row rejection, non-positive volume
    rejection, bridge metadata/lobe volume validation, and lobe scale factors.
- `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs`
  - compiles/runs `pluto_h5_truth_extract.c` on the final HDF5 endpoint;
  - selects the final `tracer > 5e-3` side volumes;
  - reruns `sparse_particle_radio_bridge.py --loss-table` with declared side
    volumes;
  - validates bridge metadata and lobe-summary volume agreement;
  - archives compact Goal 003 products.

Focused check:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py -q
7 passed in 0.04s
```

Pre-remote local validation:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.92s

bash -n scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
passed
```

## 2026-06-11 - jet remote staging and submission

Initial remote helper call hit the expected TPAC jumpbox MFA gate. Used the
authorized narrow Chrome route to open the `Enable Jumpbox SSH` selector. The
portal reported a 5-minute SSH window ending at `Thu Jun 11 12:54:18 2026`.

Staged only Goal 003-required files to:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison
```

Local staged SHA-256 values:

```text
d01d9be561440937a60ca5872112fe6fe149d6e6c4b81acb29e9f0eef43923a3  scripts/science/pluto_h5_truth_extract.c
00dbd2acd99bbcd3ab2a2ba13be73060e5c0b53dfd6cbbfd413c7587f7bb6716  scripts/science/sparse_particle_radio_bridge.py
8e8d49106daf7c135c01deb461fd33eb3abf0efb129c2625655112f1260a28ca  scripts/science/build_final_volume_coupled_comparison.py
716eb96bc316a441ecc97496a58ca1d6c33ee03f5cfaa1b864f6b826a43c2726  scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
87774ec9c3b16f21e266f965be4fc8620ab631647af27d9240077fee77baa9f1  /tmp/goal003_volume_coupled_stage.tar.gz
```

Remote staged SHA-256 values matched after extraction:

```text
d01d9be561440937a60ca5872112fe6fe149d6e6c4b81acb29e9f0eef43923a3  pluto_h5_truth_extract.c
00dbd2acd99bbcd3ab2a2ba13be73060e5c0b53dfd6cbbfd413c7587f7bb6716  sparse_particle_radio_bridge.py
8e8d49106daf7c135c01deb461fd33eb3abf0efb129c2625655112f1260a28ca  build_final_volume_coupled_comparison.py
716eb96bc316a441ecc97496a58ca1d6c33ee03f5cfaa1b864f6b826a43c2726  c_hi_fullgrid_final_volume_coupled_comparison.pbs
87774ec9c3b16f21e266f965be4fc8620ab631647af27d9240077fee77baa9f1  goal003_volume_coupled_stage.tar.gz
```

Remote preflight:

```text
host: <tpac-host>
utc: 2026-06-11T02:50:00Z
final HDF5: present/readable, 42G
Goal 002 full loss table: present/readable, 503K
final sparse-window trajectory: present/readable, 57M
bash -n c_hi_fullgrid_final_volume_coupled_comparison.pbs: passed
```

Submitted bounded one-node final truth extraction plus volume-coupled bridge:

```text
qsub c_hi_fullgrid_final_volume_coupled_comparison.pbs
job: 697875.kunanyi-ohpc
```

## 2026-06-11 - jet remote completion and local product fetch

Remote monitor showed PBS job `697875.kunanyi-ohpc` running on `n149/4`.
During execution, observed resource use reached approximately:

```text
resources_used.walltime=00:04:09
resources_used.cput=00:00:29
resources_used.mem=38897368kb
resources_used.vmem=43863804kb
```

The job then completed successfully. Remote stdout ended with:

```text
bridge_validation=passed
finished_utc=2026-06-11T02:55:35Z
```

Remote stderr was empty. The compact remote analysis product contained:

```text
final_truth/level1_injected_energy.csv
final_truth/level2_tracer_lobe_truth.csv
final_truth/truth_metadata.txt
final_truth/pluto_h5_truth_extract
bridge_external_loss_volume_coupled/radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv
bridge_external_loss_volume_coupled/radio_150mhz_sparse_lossless_mjy_sr.tsv
bridge_external_loss_volume_coupled/radio_sparse_mean_external_praise_loss.tsv
bridge_external_loss_volume_coupled/radio_sparse_particle_count_map.tsv
bridge_external_loss_volume_coupled/sparse_particle_radio_lobe_summary.csv
bridge_external_loss_volume_coupled/sparse_particle_radio_metadata.json
bridge_external_loss_volume_coupled/sparse_particle_radio_positions_0deg.tsv
bridge_external_loss_volume_coupled/sparse_particle_radio_summary.csv
bridge_external_loss_volume_coupled/x_kpc.tsv
bridge_external_loss_volume_coupled/z_kpc.tsv
```

Remote archive:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison/final_volume_coupled_comparison_2026-06-11.tar.gz
sha256=0fe05b959843748aec1fdbdd0e08a871e03dccfb3017b78351b31f9c569a0083
```

The first local fetch attempt hit the expected TPAC jumpbox MFA gate. Used the
authorized narrow Chrome/Open OnDemand selector to refresh the 5-minute SSH
window, then fetched the compact remote product with the repo helper:

```text
scripts/kunanyi/fetch_from_kunanyi.sh \
  /scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison \
  docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11
```

Local fetched products are under:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
```

Selected fetched SHA-256 values:

```text
3914dba8595c5c7c7b4b9f6bff9d35e9df86b3f4ba9847d5123f18f00f1ac09c  final_truth/level1_injected_energy.csv
5bd5e617860d9afa63e4daf6c884ac7c2c8b65be0f5f9b0ec81b957d56fb6f24  final_truth/level2_tracer_lobe_truth.csv
748ed4632197ef3b872faa4ecf6ba752484e50f44f6014efea81d547e92f67ca  final_truth/truth_metadata.txt
4c058e230e694e018daa18973be5e0a9f14e55f4ae462aad33e464ffb76c4764  bridge_external_loss_volume_coupled/sparse_particle_radio_lobe_summary.csv
4c13eac3d81e7ac93773e6673ed35f57ec77db6c7829494083da02920644f23a  bridge_external_loss_volume_coupled/sparse_particle_radio_summary.csv
```

## 2026-06-11 - jet local comparison package and docs

Ran the local comparison builder against the fetched final truth, the Goal 002
external-loss bridge, and the new volume-coupled bridge:

```text
uv run python scripts/science/build_final_volume_coupled_comparison.py \
  --truth-dir docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/final_truth \
  --old-bridge-dir docs/science/assets/c_hi_fullgrid_final_sparse_praise_loss_2026-06-11/bridge_external_loss \
  --volume-coupled-bridge-dir docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/bridge_external_loss_volume_coupled \
  --output-dir docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/comparison
```

Builder validation confirmed:

```text
loss_model_key = external_praise_compatible
volume_assignment = declared side volumes divided evenly across selected particles
matched_selected_ids = 20000
extra_ids = 0
table_rows = 20000
```

Final `tracer > 5e-3` declared volumes:

```text
negative_z: 367123.31815126061 kpc^3
positive_z: 373343.26830024854 kpc^3
bipolar_total: 740466.58644933475 kpc^3
```

Volume-coupled bridge headline outputs:

```text
negative_z lossy luminosity: 5.20526129346918e28 W Hz^-1
positive_z lossy luminosity: 1.1343085864598182e29 W Hz^-1
bipolar_total lossy luminosity: 1.6548347158067362e29 W Hz^-1
radio_map_max_mjy_sr: 4.622467967906506e17
radio_map_sum_mjy_sr_pixel: 1.3830684314552033e18
```

Compared with the Goal 002 sparse PRAiSE bridge, the new declared-volume bridge
scales the lobe volumes by:

```text
negative_z: 36.915366329940746
positive_z: 37.13011121832409
bipolar_total: 37.02332932257547
```

Added review docs:

```text
docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
docs/exchange/logs/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison.md
```

Updated `docs/exchange/current_status.md` with the Goal 003 product at the top
of the handoff note.

## 2026-06-11 - jet final validation

Final validation:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.85s

bash -n scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
passed

git diff --check
passed
```

Current git status at closeout:

```text
## main...origin/main
 M docs/exchange/current_status.md
 M docs/goals/003-final-volume-coupled-comparison/Log.md
?? docs/exchange/logs/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison.md
?? docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
?? docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md
?? scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
?? scripts/science/build_final_volume_coupled_comparison.py
?? tests/test_final_volume_coupled_comparison.py
```

No commits or pushes were made.

## 2026-06-11 - X-ray Cavities review and acceptance

The X-ray Cavities orchestrator reviewed the Goal 003 diff, science note,
exchange log, current-status update, local product bundle, comparison tables,
metadata, PBS wrapper, and tests.

Fresh orchestrator validation:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.86s

bash -n scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
passed

git diff --check
passed
```

Supplemental local artefact check confirmed:

```text
loss_model_key = external_praise_compatible
volume_assignment = declared side volumes divided evenly across selected particles
matched_selected_ids = 20000
extra_ids = 0
negative_z truth/bridge relative volume difference = 3.17e-16
positive_z truth/bridge relative volume difference = 4.68e-16
bipolar_total truth/bridge relative volume difference = 2.94e-12
```

Publishing hygiene: the fetched Linux executable
`final_truth/pluto_h5_truth_extract` was removed from the local review asset
bundle before staging because the source extractor and truth products are the
reviewable artefacts. A narrow `.gitattributes` rule was added for the Goal
003 asset directory to preserve fetched CSV/TSV/JSON products byte-for-byte
when Git stores them.

Decision: accepted as a green final-endpoint volume-coupling comparison
product. This acceptance does not make a publication-ready observable claim;
beam convolution, final X-ray/cavity comparison, and manuscript-facing
interpretation remain future work.
