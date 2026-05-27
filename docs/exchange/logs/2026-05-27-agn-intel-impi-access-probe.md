# 2026-05-27 AGN Intel/IMPI Access Probe

## Session Context

- Machine used: Mac Mini `dev-box-ts`
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- `xray_cavities` commit at start: `30c460d`
- Target checked: `kunanyi` via `tpac-jumpbox-via-deep`

## What Was Done

- Fast-forwarded `xray_cavities` to latest `origin/main`.
- Read Patrick-agent's new proposal to test the AGN group Intel/IMPI/HDF5/ZFP
  stack instead of further OpenMPI/UCX tuning.
- Used Safari/Open OnDemand to refresh the `Enable Jumpbox SSH` window.
- Probed `/ds/projects/agn`, module visibility, and public Intel/HDF5 module
  fallbacks from the `kunanyi` login node.
- Added a repeatable exact-stack probe and a guarded tiny-smoke staging helper.

## Files / Workspaces Touched

- `scripts/kunanyi/probe_agn_intel_impi_stack.sh`
- `scripts/kunanyi/stage_and_submit_agn_intel_impi_tiny_smoke.sh`
- `scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs`
- remote staged wrapper:
  `/u/bwbrook/codex_kunanyi/jet_setup_tiny_3d_cart_agn_intel_impi_smoke.pbs`

## Validation

- Local syntax checks passed:
  `bash -n scripts/kunanyi/probe_agn_intel_impi_stack.sh scripts/kunanyi/stage_and_submit_agn_intel_impi_tiny_smoke.sh scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs`
- Exact-stack probe reached `<tpac-host>`.
- Account state:
  `uid=145812(bwbrook) gid=1003(hpcusers) groups=1003(hpcusers)`.
- `/ds/projects/agn` state:
  `drwxrwxr-- 10 pmyates agn ... /ds/projects/agn`.
- `bwbrook` currently has no execute/traverse access to `/ds/projects/agn`,
  so `/ds/projects/agn/modulefiles` and `/ds/projects/agn/libraries` report
  permission denied.
- The stage/submit helper copied the PBS wrapper but stopped before `qsub`
  with exit code `10`. No PBS job was submitted.

## Current State

Patrick's proposed stack is plausible and probably the right next test, but it
is currently blocked by access to the AGN group directory rather than by the
local scripts.

Public modules do expose a partial Intel path:

```text
intel/18.0.1.163
impi/2018.1.163
hdf5/1.10.4
```

That fallback is not equivalent to Patrick's requested
`/ds/projects/agn` stack and does not expose `zfp/0.5.5`.

## Next Recommended Step

1. Ask Patrick/TPAC to add `bwbrook` to group `agn`, or grant equivalent
   execute/traverse ACL/permission on `/ds/projects/agn`.
2. Rerun:

   ```bash
   scripts/kunanyi/probe_agn_intel_impi_stack.sh
   scripts/kunanyi/stage_and_submit_agn_intel_impi_tiny_smoke.sh
   ```

3. Only after the tiny Intel/IMPI smoke is green should the production
   continuation wrapper be updated for a larger run.

## Sync Notes

- `xray_cavities` has local uncommitted script and handover-doc changes at
  this checkpoint.
- No Nectar or `deep-server` checkout update is required yet.

## Blockers / Risks

- Do not submit the 80-node `C-HI` continuation yet.
- Do not treat the public `intel/impi/hdf5/1.10.4` path as a substitute for
  Patrick's requested AGN stack without explicit approval.
