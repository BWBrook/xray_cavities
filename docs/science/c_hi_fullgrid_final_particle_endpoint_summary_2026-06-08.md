# C-HI Full-grid Final Particle Endpoint Summary

Date: 2026-06-08

## Summary

This note records the first compact particle-state diagnostic for the completed
full-grid, particles-enabled `C-HI` production endpoint.

The earlier full-history particle-HDF5 preflight showed that a naive
`plutokore.load_all_particles()` cache over all `5001` particle outputs would
be too memory-expensive for the current approach. This job therefore used a
bounded endpoint-only parser against the final PLUTO particle file,
`particles.5000.dbl`, and did not attempt to materialise the full particle
history.

## Job Record

- PBS job: `697643.kunanyi-ohpc`
- job name: `c_hi_pend_sum`
- result: `Exit_status = 0`
- walltime used: `00:00:39`
- CPU time: `00:00:02`
- peak memory: `9444kb`
- peak virtual memory: `367032kb`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stdout: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_endpoint_summary.out`
- stderr: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_endpoint_summary.err`
  was empty

The staged remote source was checksum-verified before submission:

- local/remote script SHA-256:
  `64f640d3717601270d3d5d9b0bbbe169ab709522bc9248ab6181a529a60e0731`
- local/remote PBS wrapper SHA-256:
  `d96db8f82dcdc41c695d8b8ea2c7a5c8feef29e7ae71ed857cc71d9743d35762`

## Remote Outputs

- input particle file:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/particles.5000.dbl`
- output directory:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-endpoint-summary`
- compact archive:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.tar.gz`
- archive SHA-256:
  `a25a805858a438f56369fe4d3690c31bdd358efb0082f73c3d5e51b0633e35e1`

Output files:

| File | Size |
| --- | ---: |
| `particle_endpoint_metadata.json` | 1349 bytes |
| `particle_endpoint_summary.csv` | 769 bytes |
| `particle_field_summary.csv` | 2760 bytes |
| `particle_histograms.csv` | 12658 bytes |
| `particle_position_sample.tsv` | 2155540 bytes |
| `particle_side_summary.csv` | 835 bytes |

## Endpoint Metrics

| Metric | Value |
| --- | ---: |
| particle file size | `23608389` bytes |
| particles | `196732` |
| field count | `13` |
| scalar field width | `15` |
| payload offset | `549` bytes |
| endpoint code time | `15330.0696894` |
| endpoint physical time | `50.00000000000777 Myr` |
| PLUTO step | `49253` |
| `x` extent | `-29.695625916316235` to `30.132441460503376 kpc` |
| `y` extent | `-32.27023110544345` to `30.062788186588232 kpc` |
| `z` extent | `-215.6060699853556` to `216.06201669846072 kpc` |
| injection time range | `0.0` to `49.99959115169515 Myr` |
| particle age range | `0.0004088483126271399` to `50.00000000000777 Myr` |

## Lobe Split

| Side | Particles | Fraction | Median z | Median injection time | Median age |
| --- | ---: | ---: | ---: | ---: | ---: |
| negative z lobe | `97451` | `0.4953490027041864` | `-119.28566338111048 kpc` | `25.052792802105255 Myr` | `24.94720719790252 Myr` |
| positive z lobe | `99281` | `0.5046509972958136` | `123.38448628186553 kpc` | `24.583872936481832 Myr` | `25.41612706352594 Myr` |

## Field Sanity

The final particle field summary is consistent with the endpoint quick-look
and final particle header:

- particle IDs span `1` to `196732`
- median particle position is near the centre in `x`/`y`, with a broad
  symmetric `z` distribution
- tracer median is `0.2710462752584028`, with 95th percentile
  `0.8854066251683547`
- median density is `1.5996522894860235e-4`
- median pressure is `3.224600500854765e-8`
- `color` is zero throughout this endpoint file

## Interpretation

This is a green endpoint particle-state gate. It confirms that the final
particle product is compact, readable, and internally consistent, while leaving
the full-history particle-HDF5 cache off the table for the current dense
approach.

The next particle-analysis move should be a streaming or sparse-window
workflow: read particle files in bounded time windows, compute loss/radio
quantities incrementally, and avoid constructing an all-output dense
particle-time matrix in memory.
