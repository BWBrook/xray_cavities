# C-HI Full-grid Final Sparse Radio Bridge

Date: 2026-06-08

## Summary

This note records the first 150 MHz radio-map bridge from the completed
50 Myr `C-HI` full-grid sparse particle window.

The purpose was to connect the green sparse-window particle trajectory product
to the existing particle radio smoke conventions without building a dense
all-history particle HDF5 cache. The bridge computes the same lossless
synchrotron emissivity expression used in the earlier XRAiSE/PRAiSE radio
smoke, then multiplies it by a bounded sparse-window pressure-history
attenuation proxy.

This is not the final sparse PRAiSE loss kernel. It is a controlled proxy
product for morphology, lobe balance, and pipeline continuity at the final
production endpoint.

## Job Record

- PBS job: `697646.kunanyi-ohpc`
- job name: `c_hi_spr_fin`
- result: `Exit_status = 0`
- walltime used: `00:00:05`
- CPU time: `00:00:04`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stdout:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.out`
- stderr:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.err`
  was empty

The staged remote source was checksum-verified before submission:

- local/remote script SHA-256:
  `29d827cff6a8587e00f0c7b909c32ed9bd6f0c3ec3ad208052ddedc684d124dd`
- local/remote PBS wrapper SHA-256:
  `dbf2315ba4df7557c2c10571216cceab40357a135df39cc36dc1669f50c2f1a5`

## Remote Inputs And Outputs

- input sparse window:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window`
- output directory:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge`
- compact archive:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.tar.gz`
- archive SHA-256:
  `2be0b61dcc7330727192123f9afd9c9a7138d26ea4f552ba62753cd72e24effe`

The compact products were pulled locally into:

- `docs/science/assets/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08/`

Output files:

| File | Size |
| --- | ---: |
| `radio_150mhz_sparse_lossless_mjy_sr.tsv` | 662400 bytes |
| `radio_150mhz_sparse_loss_proxy_mjy_sr.tsv` | 662400 bytes |
| `radio_sparse_mean_loss_proxy.tsv` | 662400 bytes |
| `radio_sparse_particle_count_map.tsv` | 662400 bytes |
| `sparse_particle_radio_lobe_summary.csv` | 1040 bytes |
| `sparse_particle_radio_metadata.json` | 273177 bytes |
| `sparse_particle_radio_positions_0deg.tsv` | 4860928 bytes |
| `sparse_particle_radio_summary.csv` | 539 bytes |
| `x_kpc.tsv` | 475 bytes |
| `z_kpc.tsv` | 2770 bytes |

## Method

The bridge uses:

- sparse particle trajectory rows from outputs `4950, 4955, ..., 5000`
- target particle output `5000`
- tracer threshold `5e-3`
- 150 MHz observed frequency
- redshift `0.05`
- `0 deg` projection along simulation `y` onto the `x-z` plane
- map limits `x = +/-45 kpc`, `z = +/-230 kpc`
- map pixel size `1 kpc`

For each selected target particle, the loss proxy is:

```text
clip(final pressure / maximum positive pressure across sparse window, 0, 1)
```

Particle volumes are assigned as `1.0 kpc^3` per selected particle. This keeps
the map and lobe summaries on a consistent proxy scale while avoiding a false
claim that the final tracer-mask side volumes have already been coupled to the
sparse particle map.

## Scalar Metrics

| Metric | Value |
| --- | ---: |
| target particle output | `5000` |
| sparse trajectory rows | `218909` |
| selected target particles | `20000` |
| particles in frame | `20000` |
| map shape | `460 x 90` |
| positive radio pixels | `11829` |
| max proxy map value | `1.2449e16 mJy sr^-1` |
| proxy map sum | `3.7204e16 mJy sr^-1 pixels` |
| mean pressure-history loss proxy | `0.8957` |
| minimum positive loss proxy | `2.6775e-05` |
| bipolar proxy luminosity | `4.4514e27 W Hz^-1` |
| negative-z proxy luminosity | `1.3998e27 W Hz^-1` |
| positive-z proxy luminosity | `3.0517e27 W Hz^-1` |

## Lobe Summary

| Side | Particles | Proxy volume (`kpc^3`) | Proxy luminosity (`W Hz^-1`) | Loss proxy mean | Z range (`kpc`) |
| --- | ---: | ---: | ---: | ---: | ---: |
| negative-z | `9945` | `9945` | `1.3998e27` | `0.8950` | `-215.035` to `-0.011` |
| positive-z | `10055` | `10055` | `3.0517e27` | `0.8964` | `0.041` to `216.062` |
| bipolar total | `20000` | `20000` | `4.4514e27` | `0.8957` | `-215.035` to `216.062` |

## Caveats

- The loss term is a pressure-history proxy across the sparse window, not the
  full PRAiSE synchrotron plus inverse-Compton particle loss kernel.
- The proxy currently uses `1.0 kpc^3` per selected particle. The luminosity
  values are therefore continuity-scale products, not final science
  luminosities.
- The map is particle-binned and not beam-convolved.
- The sparse window starts at output `4950`, so the proxy captures late-time
  pressure history near the final endpoint rather than the full particle life.

## Interpretation

This closes the first final-endpoint sparse radio bridge. The full 50 Myr
particle product can now produce a compact radio morphology and lobe-balance
summary without dense all-history particle materialisation.

The next technical move is to replace the pressure-history proxy with a true
sparse PRAiSE-compatible loss interface for the selected particle IDs, then
couple the resulting map to the final grid/tracer volume convention and the
observable comparison page.
