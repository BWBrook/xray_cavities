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
- `jet_setup_basic/`
  Script bundle used for the jet-setup familiarization and first basic jet run.
- `jet_parameter_sweep/`
  Small runtime parameter sweep on the same 2D spherical jet setup.
- `krause_jets_assignment/`
  Final onboarding capstone: fresh jet mini-suite plus pure-Python tracer/lobe
  analysis with remade figures.
- `official_jet_assignment/`
  Patrick's supplied Martin Krause jet assignment, run against PLUTO
  `Test_Problems/HD/Jet` in 2D cylindrical coordinates at 10 and 20 cells per
  beam radius.
- `jet_setup_tiny_3d_cart/`
  Smoke-sized full-3D Cartesian `jet-setup` bridge after the official 2D jet
  assignment.
- `sync_to_deep_server.sh`
  Pushes the local script bundles back to the canonical remote workspaces.
- `sync_to_nectar_vm.sh`
  Pushes the same workflow bundles to the Nectar mirror workspace.

## Important Note

The scripts in `rt_instability/`, `kh_instability/`, `jet_setup_basic/`,
`jet_parameter_sweep/`, and `krause_jets_assignment/` are written for the
remote directory layout used on the execution hosts, for example:

- `/home/bwbrook/work/pluto-onboarding/rt_instability` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/kh_instability` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/jet_setup_basic` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/krause_jets_assignment` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/official_jet_assignment` on `deep-server`
- `/home/bwbrook/work/pluto-onboarding/jet_setup_tiny_3d_cart` on `deep-server`
- `/home/ubuntu/work/pluto-onboarding/rt_instability` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/kh_instability` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/jet_setup_basic` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/jet_parameter_sweep` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/krause_jets_assignment` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/official_jet_assignment` on `nectar-vm`
- `/home/ubuntu/work/pluto-onboarding/jet_setup_tiny_3d_cart` on `nectar-vm`
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

or:

```bash
ssh deep-server 'tmux new -As pluto-jet /home/bwbrook/work/pluto-onboarding/jet_setup_basic/scripts/run_all.sh'
```

or:

```bash
ssh deep-server 'tmux new -As pluto-jet-sweep /home/bwbrook/work/pluto-onboarding/jet_parameter_sweep/scripts/run_all.sh'
```

or:

```bash
ssh deep-server 'tmux new -As pluto-krause /home/bwbrook/work/pluto-onboarding/krause_jets_assignment/scripts/run_all.sh'
```

This keeps the local repo as the versioned source of truth while preserving the
agreed workflow split:

- WSL as orchestration hub
- `deep-server` as the campus-only trusted execution node
- `nectar-vm` as the mobile-accessible secondary execution node
- `tmux` for long runs
- `rsync` for synchronization
