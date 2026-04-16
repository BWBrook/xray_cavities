# PLUTO Onboarding Workflow Scripts

This directory keeps versioned local copies of the remote workflow bundles used
for the PLUTO onboarding studies on `deep-server`.

These files are intended to be the source-controlled record of what was run on
`deep-server`, not a separate local execution environment.

## Layout

- `rt_instability/`
  Exact script bundle used for the Rayleigh-Taylor study.
- `kh_instability/`
  Exact script bundle used for the Kelvin-Helmholtz study.
- `sync_to_deep_server.sh`
  Pushes the local script bundles back to the canonical remote workspaces.

## Important Note

The scripts in `rt_instability/` and `kh_instability/` are written for the
existing remote directory layout on `deep-server`, for example:

- `/home/bwbrook/work/pluto-onboarding/rt_instability`
- `/home/bwbrook/work/pluto-onboarding/kh_instability`
- `/home/bwbrook/git/utas-agn/pluto`
- `/home/bwbrook/papers/xray_cavities`

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

- WSL as control plane
- `deep-server` as execution machine
- `tmux` for long runs
- `rsync` for synchronization
