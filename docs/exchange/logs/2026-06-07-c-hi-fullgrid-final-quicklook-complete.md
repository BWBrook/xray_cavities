# C-HI full-grid final quick-look extraction complete

Date: 2026-06-07

## Summary

The compact quick-look extraction submitted as `697386.kunanyi-ohpc` completed
successfully and the products were fetched, plotted, and written up locally.

## PBS Result

```text
PBS Job Id: 697386.kunanyi-ohpc
Job Name:   c_hi_final_ql
Exit_status = 0
job_state = F
resources_used.walltime = 00:04:34
resources_used.cput = 00:00:20
resources_used.mem = 3771068kb
resources_used.cpupercent = 11
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=32gb
Resource_List.walltime = 01:00:00
```

The job ran on `n004` and wrote no stderr output.

## Extracted Product Summary

Input:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
```

Timestep:

```text
Timestep_51
```

Remote compact output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-quicklook
```

The completed remote output listing was:

```text
axis_profile_z.tsv        96102 bytes
metadata.txt              231 bytes
pluto_h5_quicklook_extract 4252808 bytes
slice_xz_prs.tsv          14493067 bytes
slice_xz_rho.tsv          13742799 bytes
slice_xz_tr1.tsv          8677231 bytes
slice_xz_vx3.tsv          14479067 bytes
summary_metrics.csv       966 bytes
x_centres.tsv             18354 bytes
y_centres.tsv             18354 bytes
z_centres.tsv             19409 bytes
```

Compact archive fetched locally:

```text
build/science/kunanyi_stage_2026-06-07/c_hi_fullgrid_final_quicklook_697386_compact_2026-06-07.tar.gz
```

SHA-256:

```text
26f8ab57e4f8e3913bc629abb391f699c75b45296d474fe2c411736a0b71098c
```

## Final Metrics

```text
time_code=15330.069689399999
physical_time=50.0000 Myr
shape_nz_ny_nx=1014,960,960
tracer_min=0
tracer_max=1
tracer_mean=0.038685525102403313
```

Tracer extent:

| Threshold | Cells | x range (kpc) | y range (kpc) | z range (kpc) |
| --- | ---: | --- | --- | --- |
| `1e-3` | 194674862 | -30.832 to 31.400 | -32.861 to 31.115 | -217.440 to 217.440 |
| `5e-3` | 185000464 | -29.998 to 30.832 | -32.269 to 30.551 | -217.440 to 217.440 |
| `1e-2` | 177856594 | -29.724 to 29.724 | -31.977 to 30.273 | -215.607 to 215.607 |

## Local Report And Assets

Report:

```text
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md
docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.pdf
```

Assets:

```text
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/c_hi_quicklook_midplane_maps.png
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/c_hi_quicklook_midplane_maps_central_zoom.png
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/c_hi_quicklook_axis_profiles.png
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/c_hi_quicklook_summary.md
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/metadata.txt
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/summary_metrics.csv
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/quicklook_pbs_stdout.txt
docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/quicklook_pbs_stderr.txt
```

The PDF rendered successfully with Pandoc/XeLaTeX and has `5` pages.

## Interpretation

The completed `prod64` endpoint has now passed the first compact science-facing
readiness gate. The final products are readable, the final float HDF5 can be
extracted on a one-node compute job, and the resulting quick-look figures are
nonblank and show the expected bilateral jet/cocoon structure.

The next step is the downstream aligned truth, X-ray, radio, and cavity-analysis
workflow for the 50 Myr endpoint.
