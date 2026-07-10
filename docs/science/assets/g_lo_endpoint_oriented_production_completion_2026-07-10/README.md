# G-LO Goal 037 Completion Evidence

This package records the compact completion evidence for PBS job
`751105.kunanyi-ohpc`. The job was killed at the 48-hour walltime and did not
reach the 50 Myr endpoint.

## Critical Restart Guardrail

`data.0003.dbl.h5` is only the latest inventoried double-HDF5 filename. It is
`44,741,404,952` bytes, has no matching XMF or `dbl.h5.out` row, and is an
incomplete termination artifact. It must not be used for restart.

The latest validated fluid restart checkpoint is `data.0002.dbl.h5`, catalogue
index `2`, at code time `3065.935` (about `9.99974 Myr`). It is
`67,318,639,276` bytes and has matching `data.0002.dbl.xmf` metadata.

`particles.1000.dbl` is the candidate particle file paired to that fluid
checkpoint because its remote mtime is 44 seconds later. This is an mtime-only
association. Its contents and restart pairing have not been validated and
must pass an explicit preflight before any continuation is submitted.

The latest complete float output is `data.0014.flt.h5`, catalogue index `14`,
at code time `4292.332` (about `13.99971 Myr`). It records later simulated
progress but is not the accepted restart surface. Restarting from index `2`
therefore rolls back `1226.397` code-time units, about `3.99997 Myr` or
`7.99994` percentage points of the 50 Myr target.

## Evidence Boundary

Files under `remote_logs/` are preserved as retrieved provenance. In
particular, the raw remote inventory summary reports the latest filename, not
the latest restartable checkpoint. The reviewed local summaries in this
directory provide the restart-safe interpretation.

The partial file's last recorded mtime was about `10:22:34` after job start and
about `37:38:48` before wrapper termination. The strongest supported root
cause is a stalled regular 15 Myr collective-HDF5 write; scheduler walltime is
the terminal symptom. This is not a final shutdown write that merely overran
the 30-minute PLUTO/PBS buffer, and there is no demonstrated physics failure.

`remote_logs/safe_restart_surface_2026-07-10.txt` is preserved as raw
provenance with literal backslash-`n` sequences; the reviewed local summaries
normalize its fields. The original remote SHA manifest predates that file and
the empty PLUTO diagnostic extracts. `local_asset_manifest.sha256` covers the
complete final bundle.
