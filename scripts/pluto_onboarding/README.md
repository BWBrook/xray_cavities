# PLUTO Onboarding Workflow Scripts

This directory keeps versioned local copies of the remote workflow bundles used
for the PLUTO onboarding studies on `deep-server`.

These files are intended to be the source-controlled record of what was run on
our remote execution hosts, not a separate local execution environment.

## Layout

- `rt_instability/`
  Exact script bundle used for the Rayleigh-Taylor study.
- `kh_instability/`
  Exact script bundle used for the Kelvin-Helmholtz study.
- `sync_to_deep_server.sh`
  Pushes the local script bundles back to the canonical remote workspaces.
- `sync_to_nectar_vm.sh`
  Pushes the same workflow bundles to the Nectar mirror workspace.

## Important Note

The scripts in `rt_instability/` and `kh_instability/` are written for the
remote directory layout used on the execution hosts, for example:

- `/home/bwbrook/work/pluto-onboarding/rt_instability` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/kh_instability` on `deep-server`
- `/home/ubuntu/work/pluto-onboarding/rt_instability` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/kh_instability` on `nectar-vm`
- `/home/<user>/git/utas-agn/pluto`
- `/home/<user>/papers/xray_cavities`

So they should be treated as remote workflow artifacts and edited with that
context in mind.

## Typical Use

From WSL, after making a change to one of these scripts:

```bash
cd /home/bwbrook/papers/xray_cavities
./scripts/pluto_onboarding/sync_to_deep_server.sh
```

Then launch remotely, typically inside `tmux`, for example:

```bash
ssh deep-server 'tmux new -As pluto-rt /home/bwbrook/work/pluto-onboarding/rt_instability/scripts/run_all.sh'
```

or:

```bash
ssh deep-server 'tmux new -As pluto-kh /home/bwbrook/work/pluto-onboarding/kh_instability/scripts/run_all.sh'
```

This keeps the local repo as the versioned source of truth while preserving the
agreed workflow split:

- WSL as orchestration hub
- `deep-server` as the campus-only trusted execution node
- `nectar-vm` as the mobile-accessible secondary execution node
- `tmux` for long runs
- `rsync` for synchronization
