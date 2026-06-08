# C-HI Full-grid Final Particle Sparse Window

Date: 2026-06-08

## Summary

This note records the first bounded sparse-window particle trajectory product
for the completed full-grid, particles-enabled `C-HI` endpoint.

The purpose was to move beyond endpoint-only particle summaries without
building the rejected dense all-history particle HDF5 cache. The sparse-window
tool reads selected PLUTO `particles.NNNN.dbl` files directly, chooses a
deterministic subset of tracer-bearing target particles, and emits compact
long-format trajectories plus lifecycle and side summaries.

## Job Record

- PBS job: `697644.kunanyi-ohpc`
- job name: `c_hi_psw_fin`
- result: `Exit_status = 0`
- walltime used: `00:01:04`
- CPU time: `00:00:13`
- peak memory: `92200kb`
- peak virtual memory: `684996kb`
- request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
- stdout: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_sparse_window.out`
- stderr: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_sparse_window.err`
  was empty

The staged remote source was checksum-verified before submission:

- local/remote script SHA-256:
  `af8705e0f625b756eb37dc3ba2d738ecc5f5382e13dcb2c3a0d581a1a9afe8b3`
- local/remote PBS wrapper SHA-256:
  `c14f21c20a514b1f641b421a88ad6ccbbcc46870d0a8e59ee9089ff25696c371`

## Remote Outputs

- input particle directory:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs`
- output directory:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window`
- compact archive:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.tar.gz`
- archive SHA-256:
  `9894f2dfc6cae5b76257b1c5b66b9438fdc25424d66d43ea68df1b2dbc80dc62`

Output files:

| File | Size |
| --- | ---: |
| `particle_sparse_window_lifecycle.csv` | 3873818 bytes |
| `particle_sparse_window_metadata.json` | 229654 bytes |
| `particle_sparse_window_side_summary.csv` | 1612 bytes |
| `particle_sparse_window_summary.csv` | 4782 bytes |
| `particle_sparse_window_trajectory.tsv` | 59070780 bytes |

## Window Configuration

| Parameter | Value |
| --- | ---: |
| target particle output | `5000` |
| start particle output | `4950` |
| end particle output | `5000` |
| stride | `5` |
| window outputs | `4950, 4955, ..., 5000` |
| tracer threshold | `0.005` |
| maximum selected IDs | `20000` |
| target candidates | `195558` |
| selected IDs | `20000` |
| trajectory rows | `218909` |

The window spans approximately `49.49905441915949` to
`50.00000000000777 Myr`.

## Endpoint Row

The final window row agrees with the endpoint particle summary:

- output index: `5000`
- file: `particles.5000.dbl`
- time: `50.00000000000777 Myr`
- particles: `196732`
- tracer/density/pressure-positive candidates: `195558`
- selected IDs present: `20000`
- selected IDs missing: `0`
- position envelope:
  - `x = -29.695625916316235` to `30.132441460503376 kpc`
  - `y = -32.27023110544345` to `30.062788186588232 kpc`
  - `z = -215.6060699853556` to `216.06201669846072 kpc`

At the target output, the selected sparse set splits into:

- negative-z: `9945` selected particles
- positive-z: `10055` selected particles

Across the first window output, `19801` of the `20000` selected target IDs are
already present; by the final target output all selected IDs are present.

## Interpretation

This is a green sparse-window particle gate. The workflow reads bounded
particle windows directly from PLUTO binary outputs, avoids dense all-history
materialisation, and produces trajectory/lifecycle tables large enough for the
next particle-loss/radio step but small enough to inspect, archive, and rerun.

The next science move is to connect this sparse trajectory table to the
particle-loss/radio machinery: compute loss factors for the selected IDs over
the bounded window, then bin a 150 MHz map for the final output using the
existing endpoint/tracer volume conventions.
