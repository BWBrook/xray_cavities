# 2026-05-25 Kunanyi Restart Framework

## Summary

After jobs `692369.kunanyi-ohpc` and `692504.kunanyi-ohpc`, the operating
model has been formalized:

```text
PBS jobs are disposable segments.
Restart-capable dbl.h5 outputs are the persistent simulation state.
```

Barry will feed PBS completion/failure emails back into Codex. Codex should
inspect the remote state, classify the failure, and continue from the latest
valid `dbl.h5` checkpoint once the transport path is acceptable.

## Added Files

Restart operations guide:

```text
docs/kunanyi_restart_framework.md
```

Full-grid `C-HI` restart-state inspector:

```text
scripts/kunanyi/inspect_c_hi_fullgrid_restart_state.sh
```

Full-grid `C-HI` continuation wrapper and submit helper:

```text
scripts/kunanyi/c_hi_fullgrid_continue.pbs
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh
```

## Template Hardening

`scripts/kunanyi/jet_setup_production_template.pbs` now:

- verifies that restart catalogue entries have matching restart files before
  selecting them
- records `MPI_EXIT_CODE`
- classifies common MPI failures
- writes failure reasons into the `FAILED` marker
- clears stale `DONE` markers on failure

Classification labels currently include:

```text
ucx_ud_endpoint_timeout
mpi_signal_15_or_walltime
segmentation_fault
mpi_abort
hdf5_related_mpi_failure
```

## Route Defaults

The generic Kunanyi helpers now default to the stable home-network route:

```text
MacBook -> Tailscale deep-server/utas-ubuntu -> TPAC jumpbox -> kunanyi
```

Defaults changed:

```text
run_on_kunanyi.sh: TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep
copy_to_kunanyi.sh: TPAC_SCP_HOST=kunanyi-via-deep
fetch_from_kunanyi.sh: TPAC_SCP_HOST=kunanyi-via-deep
```

Campus direct and Nectar fallback routes still work by explicit override.

## Current Caution

Do not submit another 80-node full-grid continuation until the OpenMPI/UCX
transport issue from `692369.kunanyi-ohpc` is resolved with Stas/Patrick or
TPAC.

The continuation helper exists, but the current full-grid case only has output
`0`, and plain OB1/TCP was too slow to be useful at 80 nodes.
