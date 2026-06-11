# C-HI Full-grid Final Volume-coupled Sparse PRAiSE Comparison

Date: 2026-06-11

## Summary

This note records the bounded Goal 003 product: final grid/tracer lobe truth
for the completed 50 Myr `C-HI` endpoint, followed by a sparse
PRAiSE-compatible radio bridge run that uses the final `tracer > 5e-3`
negative-z and positive-z grid volumes as declared side volumes.

The result preserves the Goal 001/002 external loss-table contract. It changes
only the bridge volume assignment from the previous `1.0 kpc^3` per selected
particle convention to declared side volumes divided evenly across selected
particles in each lobe.

This is a final-endpoint volume-coupling comparison product. It is not a final
publication-ready observable: the map is not beam-convolved, the selected IDs
and loss factors still come from the sparse final window, and no final
observable-comparison page is claimed here.

## Job Record

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison
```

Remote output root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison
```

Remote inputs:

```text
final HDF5: /scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
timestep: Timestep_51
sparse window: /scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window
loss table: /scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/full/sparse_praise_loss_table.csv
```

PBS job:

| Job | Name | Request | Result |
| --- | --- | --- | --- |
| `697875.kunanyi-ohpc` | `c_hi_vc_cmp` | `select=1:ncpus=1:mpiprocs=1:mem=96gb`, `walltime=02:00:00` | completed |

The wrapper compiled `scripts/science/pluto_h5_truth_extract.c`, extracted
final Level 1/Level 2 truth, selected the `5e-3` side volumes, reran
`sparse_particle_radio_bridge.py --loss-table` with declared side volumes, and
validated bridge metadata/lobe volumes before archiving the compact product.

Remote archive:

```text
/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison/final_volume_coupled_comparison_2026-06-11.tar.gz
sha256=0fe05b959843748aec1fdbdd0e08a871e03dccfb3017b78351b31f9c569a0083
```

## Local Review Assets

The compact product directory was pulled locally into:

```text
docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/
```

Primary files:

| File | Size |
| --- | ---: |
| `final_truth/level1_injected_energy.csv` | 457 bytes |
| `final_truth/level2_tracer_lobe_truth.csv` | 3624 bytes |
| `final_truth/truth_metadata.txt` | 481 bytes |
| `bridge_external_loss_volume_coupled/sparse_particle_radio_lobe_summary.csv` | 1057 bytes |
| `bridge_external_loss_volume_coupled/sparse_particle_radio_metadata.json` | 273966 bytes |
| `bridge_external_loss_volume_coupled/sparse_particle_radio_summary.csv` | 539 bytes |
| `bridge_external_loss_volume_coupled/radio_150mhz_sparse_external_praise_loss_mjy_sr.tsv` | 662400 bytes |
| `bridge_external_loss_volume_coupled/radio_150mhz_sparse_lossless_mjy_sr.tsv` | 662400 bytes |
| `bridge_external_loss_volume_coupled/radio_sparse_mean_external_praise_loss.tsv` | 662400 bytes |
| `bridge_external_loss_volume_coupled/radio_sparse_particle_count_map.tsv` | 662400 bytes |
| `comparison/declared_volume_truth.csv` | 410 bytes |
| `comparison/lobe_volume_coupling_comparison.csv` | 585 bytes |
| `comparison/comparison_metadata.json` | 2530 bytes |
| `comparison/comparison_summary.md` | 997 bytes |

Selected local SHA-256 values:

```text
3914dba8595c5c7c7b4b9f6bff9d35e9df86b3f4ba9847d5123f18f00f1ac09c  final_truth/level1_injected_energy.csv
5bd5e617860d9afa63e4daf6c884ac7c2c8b65be0f5f9b0ec81b957d56fb6f24  final_truth/level2_tracer_lobe_truth.csv
4c058e230e694e018daa18973be5e0a9f14e55f4ae462aad33e464ffb76c4764  bridge_external_loss_volume_coupled/sparse_particle_radio_lobe_summary.csv
4c13eac3d81e7ac93773e6673ed35f57ec77db6c7829494083da02920644f23a  bridge_external_loss_volume_coupled/sparse_particle_radio_summary.csv
9bf703114457ac656cb5e98ea8e63faf9ad05f6aa8a2533f26ef12158de7b307  comparison/comparison_metadata.json
```

## Method

The final truth extractor reads the completed 50 Myr PLUTO HDF5 endpoint and
writes:

- `level1_injected_energy.csv` with elapsed and configured one-sided/bipolar
  jet energy checks;
- `level2_tracer_lobe_truth.csv` with lobe truth at tracer thresholds `1e-3`,
  `5e-3`, and `1e-2` for negative z, positive z, and bipolar total;
- `truth_metadata.txt` with the input path, timestep, grid shape, and unit
  conversions used for the extraction.

The volume-coupled bridge then uses the existing Goal 002 loss table and the
declared side volumes:

```text
--loss-table /scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-sparse-praise-loss/full/sparse_praise_loss_table.csv
--negative-volume-kpc3 367123.31815126061
--positive-volume-kpc3 373343.26830024854
```

No dense all-history particle cache was built, no new PLUTO simulation segment
was run, and no scientific defaults were changed.

## Final Truth Metrics

Level 1 energy:

| Metric | Value |
| --- | ---: |
| time | `50.000000000007773 Myr` |
| one-sided jet power | `9.9999999999999993e44 erg s^-1` |
| elapsed one-sided injected energy | `1.57787999999999974e60 erg` |
| elapsed bipolar injected energy | `3.15575999999999949e60 erg` |

Level 2 `tracer > 5e-3` lobe truth:

| Side | Cell count | Volume (`kpc^3`) | Total energy (`erg`) | Z range (`kpc`) |
| --- | ---: | ---: | ---: | ---: |
| negative z | `92882767` | `367123.31815126061` | `6.9236422439341875e59` | `-217.440` to `-0.025` |
| positive z | `92117697` | `373343.26830024854` | `6.9577941535160785e59` | `0.025` to `217.440` |
| bipolar total | `185000464` | `740466.58644933475` | `1.3881436397447783e60` | `-217.440` to `217.440` |

## Volume-coupled Bridge Metrics

Bridge metadata confirmed:

```text
loss_model_key = external_praise_compatible
volume_assignment = declared side volumes divided evenly across selected particles
matched_selected_ids = 20000
extra_ids = 0
table_rows = 20000
```

Radio summary:

| Metric | Value |
| --- | ---: |
| selected particles | `20000` |
| particles in frame | `20000` |
| positive radio pixels | `11783` |
| max external-loss map value | `4.622467967906506e17 mJy sr^-1` |
| external-loss map sum | `1.3830684314552033e18 mJy sr^-1 pixels` |
| negative-z external-loss luminosity | `5.20526129346918e28 W Hz^-1` |
| positive-z external-loss luminosity | `1.1343085864598182e29 W Hz^-1` |
| bipolar external-loss luminosity | `1.6548347158067362e29 W Hz^-1` |

Lobe summary:

| Side | Particles | Declared volume (`kpc^3`) | External-loss luminosity (`W Hz^-1`) | Mean loss factor |
| --- | ---: | ---: | ---: | ---: |
| negative z | `9945` | `367123.3181512607` | `5.2053e28` | `0.9933` |
| positive z | `10055` | `373343.2683002487` | `1.1343e29` | `0.9924` |
| bipolar total | `20000` | `740466.5864515094` | `1.6548e29` | `0.9929` |

## Comparison To Goal 002 Sparse PRAiSE Bridge

Goal 002 used the same selected IDs and external PRAiSE-compatible loss table,
but kept the old `1.0 kpc^3` per selected particle volume convention. The new
run scales the bridge by final grid/tracer lobe volume:

| Side | Old volume | New volume | Volume scale | Old luminosity | New luminosity | Luminosity scale |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| negative z | `9945` | `367123.3181512607` | `36.9154` | `1.4101e27` | `5.2053e28` | `36.9154` |
| positive z | `10055` | `373343.2683002487` | `37.1301` | `3.0550e27` | `1.1343e29` | `37.1301` |
| bipolar total | `20000` | `740466.5864515094` | `37.0233` | `4.4650e27` | `1.6548e29` | `37.0623` |

The slight difference between bipolar volume scale and bipolar luminosity
scale follows from the two lobes having different old luminosity weights.

## Validation

Local validation before remote staging:

```text
uv run pytest tests/test_final_volume_coupled_comparison.py tests/test_sparse_praise_loss_table.py tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
26 passed in 0.92s

bash -n scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs
passed
```

Remote wrapper validation printed:

```text
bridge_validation=passed
finished_utc=2026-06-11T02:55:35Z
```

The local comparison builder also revalidated the fetched product and wrote
`comparison/declared_volume_truth.csv`,
`comparison/lobe_volume_coupling_comparison.csv`,
`comparison/comparison_metadata.json`, and
`comparison/comparison_summary.md`.

## Caveats

- This is not a final publication-ready observable product.
- The map is sparse-particle binned and not beam-convolved.
- The selected-ID population, sparse window, loss table, PRAiSE parameters,
  observing frequency, redshift, and tracer threshold were preserved.
- The product couples final grid/tracer lobe volume to sparse selected
  particles; it does not replace the sparse bridge with a full grid radiation
  transfer model.
- The bridge lobe volumes agree with extracted truth within floating-point
  tolerance; small last-decimal differences come from CSV round-tripping and
  per-side volume division.

## Interpretation

Goal 003 closes the first final-volume coupling gap after Goal 002: the sparse
external PRAiSE-compatible bridge now has a compact comparison product using
the final `tracer > 5e-3` grid/tracer side volumes. The next review should
inspect the helper, wrapper, provenance, and scalar comparison before deciding
whether to proceed to a final observable-comparison or manuscript-facing
review goal.
