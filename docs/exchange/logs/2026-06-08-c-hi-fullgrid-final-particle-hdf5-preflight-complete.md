# C-HI full-grid final particle-HDF5 feasibility preflight complete

Date: 2026-06-08

## Summary

The bounded one-node feasibility preflight for the completed 50 Myr full-grid
`C-HI` endpoint completed successfully and returned a negative recommendation
for the current naive full-history particle-HDF5 build approach.

## PBS Result

```text
PBS Job Id: 697639.kunanyi-ohpc
Job Name:   c_hi_ph5_pf
Exit_status = 0
resources_used.walltime = 00:08:13
resources_used.cput = 00:00:08
resources_used.cpupercent = 3
resources_used.mem = 188228kb
resources_used.vmem = 895220kb
resources_used.ncpus = 1
```

Remote files:

```text
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight.out
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight.err
/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight_2026-06-07.tar.gz
```

The stderr file was empty. The compact archive was present and about `1.2K`.

## Output Files

Remote preflight output directory:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-particle-hdf5-preflight
```

Output listing:

```text
particle_hdf5_feasibility_fields.csv 949 bytes
particle_hdf5_feasibility_summary.csv 637 bytes
particle_hdf5_feasibility_summary.json 4100 bytes
```

## Feasibility Values

```text
particle_output_count=5001 outputs
total_particles_from_final_id=196732 particles
field_count=13 fields
total_field_width=15 scalar_field_equivalents
raw_float64_matrix_gib=109.9545581638813 GiB
saved_float32_matrix_gib=54.97727908194065 GiB
estimated_peak_gib=1099.545581638813 GiB
max_memory_gib=128.0 GiB
full_history_build_recommended=False boolean
recommendation=DO_NOT_BUILD_FULL_HISTORY_CACHE_WITH_CURRENT_APPROACH
```

Fields represented by the final particle output:

```text
id:1
x1:1
x2:1
x3:1
vx1:1
vx2:1
vx3:1
tinj:1
color:1
tracer:1
last_shock_time:3
density:1
pressure:1
```

## Interpretation

The preflight did what it was designed to do: it avoided a large allocation and
showed that the current dense full-history `plutokore.load_all_particles()`
cache is not a sensible next production job for the full-grid 50 Myr endpoint.

The raw float64 matrices alone would be about `110 GiB`; the saved float32
datasets would be about `55 GiB`; and the conservative peak-memory estimate is
about `1.1 TiB` once dense arrays, temporary tables, compression, and Python
overheads are allowed for.

## Follow-up

Do not submit a blind all-history particle-HDF5 cache with the current approach.
The next particle-aware science step should use endpoint-only diagnostics,
sparse time windows, or a streaming/chunked analysis design that avoids
materializing all `5001` particle outputs as dense in-memory arrays.
