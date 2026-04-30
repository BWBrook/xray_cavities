# Handover Note: 2026-04-30 kunanyi first PBS smoke

## Session Context

- Machine used: MacBook Neo as control plane
- Remote access: TPAC jumpbox window opened via Open OnDemand
- Local repo path: `/Users/bwbrook/papers/xray_cavities`

## What Was Done

- Used the private TPAC env file at
  `/Users/bwbrook/.config/tpac/kunanyi.env`.
- Confirmed password-backed SSH to `<tpac-host>`.
- Confirmed the hop from jumpbox to `kunanyi`.
- Added local SSH aliases for:
  - `tpac-jumpbox`
  - `kunanyi`
- Added a reusable PBS smoke script:
  - `scripts/kunanyi/smoke_job.pbs`
- Copied the smoke script to the jumpbox/home side with `scp`.
- Submitted it from the `kunanyi` login node with `qsub`.

## Validation

- Jumpbox login landed on `jumpbox-2`.
- `ssh kunanyi` landed on `<tpac-host>`.
- Login-node tools:
  - `qsub`: `/opt/pbs/bin/qsub`
  - `qstat`: `/opt/pbs/bin/qstat`
  - Lmod: `Modules based on Lua: Version 8.1.18`
- PBS server `kunanyi-ohpc` was active.
- Clean PBS smoke submission:

```text
SUBMITTED=688913.kunanyi-ohpc
```

- PBS job ran on compute node:

```text
HOST=n001.kunanyi
PBS_JOBID=688913.kunanyi-ohpc
PBS_QUEUE=test
NODEFILE_CONTENTS=n001.kunanyi
NCPUS=28
```

## Files / Workspaces Touched

- Local:
  - `~/.ssh/config`
  - `scripts/kunanyi/smoke_job.pbs`
  - `docs/kunanyi_setup.md`
  - `docs/exchange/logs/2026-04-30-kunanyi-first-pbs-smoke.md`
- Remote:
  - `~/codex_smoke.pbs`
  - `/scratch/bwbrook/codex_smoke/`

## Current State

- `kunanyi` access, login-node inventory, and basic PBS submission are green.
- The next HPC work should use PBS; do not compile or run simulations on the
  login node.
- Broad `module avail` can hang or be slow; use targeted module queries next.
- Follow-up helper scripts were added for the next jumpbox window:
  - `scripts/kunanyi/run_on_kunanyi.sh`
  - `scripts/kunanyi/module_inventory.sh`

## Next Recommended Step

1. Query targeted modules for compiler/MPI/HDF5/Python/Git availability.
2. Request a small interactive PBS job for the first PLUTO build smoke.
3. Build and run a tiny PLUTO case under PBS.
4. Test artifact retrieval back to the MacBook via jumpbox.

## Blockers / Risks

- SSH requires opening the 5-minute jumpbox window through Open OnDemand.
- Locale warnings appear (`C.UTF-8` not available) but did not block PBS jobs.
