# nectar-vm setup for UTAS AGN

This document records the current state of `nectar-vm` for mirroring the UTAS AGN workflow used on `deep-server`.

## Scope

This note covers:

- the machine and toolchain state relevant to UTAS AGN work
- the repo-local Python environment in `/home/ubuntu/papers/xray_cavities`
- the current UTAS AGN checkout state in `/home/ubuntu/git/utas-agn`
- the validation work completed from WSL on `2026-04-17`
- the remaining blockers to full parity with `deep-server`

It is intentionally operational rather than scientific.

## Machine summary

Observed from WSL on `2026-04-17`:

- Host alias: `nectar-vm`
- Remote host name during successful SSH sessions: `deep-vm`
- User: `ubuntu`
- Home directory: `/home/ubuntu`
- CPU cores: `64`
- RAM: about `125 GiB`

Relevant baseline tools observed before bring-up:

- `python3`
- `git`
- `tmux`
- `rsync`
- serial HDF5 wrapper `h5cc`

## Provisioned toolchain state

The following packages and tools were installed or verified during bring-up:

- `uv 0.11.7`
- `openmpi-bin`
- `libopenmpi-dev`
- `libhdf5-openmpi-dev`
- `hdf5-tools`
- `mpicc`
- `mpirun`
- `h5cc`
- `h5pcc`

Important HDF5 result:

- `h5pcc -showconfig` reports `Parallel HDF5: yes`

This means the Nectar VM now has the MPI-capable HDF5 lane required for production-style PLUTO output, not just serial HDF5 tooling.

## SSH and Git identity state

### WSL to nectar-vm

Status:

- SSH from WSL to `nectar-vm` succeeded repeatedly during provisioning.
- The VM also showed intermittent `Connection refused` episodes on port 22 during the same session.

Interpretation:

- The host was reachable and configurable.
- The residual issue looks like VM or network instability rather than an authentication issue.

### GitHub and GitLab from nectar-vm

Status during successful remote sessions:

- `ssh -T git@github.com` succeeded
- `ssh -T git@gitlab.com` succeeded

Git identity layout on the VM now includes:

- GitHub SSH config using `~/.ssh/id_ed25519_github`
- GitLab SSH config using `~/.ssh/id_ed25519_gitlab`

This gives Nectar parity with the existing split-host Git workflow:

- GitHub for `xray_cavities`
- GitLab for the UTAS AGN code repos

## UTAS AGN checkout state

The following clones were created on Nectar:

- `/home/ubuntu/git/utas-agn/pluto`
- `/home/ubuntu/git/utas-agn/jet-setup`
- `/home/ubuntu/git/utas-agn/plutokore`
- `/home/ubuntu/git/utas-agn/jet-setup.wiki`
- `/home/ubuntu/papers/xray_cavities`

Standard working directories were also created:

- `/home/ubuntu/work/pluto-onboarding`
- `/home/ubuntu/work/utas-agn-runs`

### Branch and remote layout

The three main code repos were configured to match `deep-server`:

- `pluto`
  - branch: `bwbrook/deep-server-bringup`
  - `origin = git@gitlab.com:BWBrook/pluto.git`
  - `upstream = git@gitlab.com:utas-agn/pluto.git`
- `jet-setup`
  - branch: `bwbrook/deep-server-bringup`
  - `origin = git@gitlab.com:BWBrook/jet-setup.git`
  - `upstream = git@gitlab.com:utas-agn/jet-setup.git`
- `plutokore`
  - branch: `bwbrook/deep-server-bringup`
  - `origin = git@gitlab.com:BWBrook/plutokore.git`
  - `upstream = git@gitlab.com:utas-agn/plutokore.git`
- `jet-setup.wiki`
  - branch: `master`
  - canonical remote only

`xray_cavities` was cloned from GitHub and tracks `origin/main`.

Nectar-specific PLUTO host definitions were then added in the local `pluto`
fork to make HDF5-enabled builds explicit and repeatable:

- `Config/Nectar.gcc.defs`
- `Config/Nectar.mpicc.defs`

## xray_cavities environment state

The repo-local environment at `/home/ubuntu/papers/xray_cavities` was recreated with:

```bash
cd /home/ubuntu/papers/xray_cavities
uv sync
```

Verified results:

- the environment synced successfully
- editable `plutokore` resolved from `/home/ubuntu/git/utas-agn/plutokore`
- `scipy 1.13.1`
- `sphinx 6.2.1`

So the existing compatibility pins remain valid on Nectar:

- `scipy<1.14`
- `sphinx<7`

Preferred Python invocation policy on Nectar is therefore the same as on `deep-server`:

```bash
uv run --project /home/ubuntu/papers/xray_cavities ...
```

## Smoke-test status

A remote smoke workspace was staged at:

- `/home/ubuntu/work/nectar-smoke`

### Serial PLUTO smoke

Status:

- succeeded

Case details:

- plain PLUTO Sod shock tube
- serial build with `Linux.gcc.defs`
- `.dbl` output

Confirmed behavior:

- PLUTO built successfully
- the run completed to `t = 0.2`
- `data.0001.dbl` was written

### MPI PLUTO build lane

Status:

- build succeeded
- run succeeded

Case details:

- plain PLUTO Sod shock tube
- MPI build with `Linux.mpicc.defs`
- `.dbl` output

Interpretation:

- MPI compile and runtime support are present and working on Nectar
- `data.0001.dbl` was written successfully in the MPI run workspace

### HDF5 PLUTO build lane

Status:

- succeeded after adding Nectar-specific PLUTO host definitions

Important lesson:

- the machine has MPI-capable HDF5 installed and visible through `h5pcc`
- the stock `Linux.gcc.defs` and `Linux.mpicc.defs` files in this checkout do not wire in HDF5 from the start of the build
- the reliable fix was to add explicit Nectar host definitions:
  - `Config/Nectar.gcc.defs`
  - `Config/Nectar.mpicc.defs`
- the validated production-oriented path is the parallel definition:
  - `ARCH = Nectar.mpicc.defs`
  - `CC = h5pcc`
  - `PARALLEL = TRUE`
  - `USE_HDF5 = TRUE`

Interpretation:

- Nectar is now ready for both `.dbl`-based exploratory work and HDF5-enabled production-style output
- the validated HDF5 smoke run wrote:
  - `data.0000.dbl.h5`
  - `data.0001.dbl.h5`
  - matching `.xmf` sidecar files

### jet-setup validation lane

Status:

- succeeded

Validated test path:

```bash
cd /home/ubuntu/git/utas-agn/jet-setup/test
export PLUTO_DIR=/home/ubuntu/git/utas-agn/pluto
uv run --project /home/ubuntu/papers/xray_cavities \
python3 run-tests.py environment/king/test-2d-hd-ga-sph -m Linux.gcc.defs
```

Observed result:

- `king/test-2d-hd-ga-sph` passed end-to-end
- setup, build, run, and verification all succeeded in the Nectar environment

## Workflow parity model

Nectar is intended to be the mobile-accessible companion to `deep-server`:

- `deep-server` = campus-only trusted execution node
- `nectar-vm` = mobile-accessible secondary execution node
- WSL = orchestration hub
- Git = source sync
- `rsync` = run and artifact sync

The sync policy is now documented in local helper scripts under:

- `scripts/remote_sync/`
- `scripts/pluto_onboarding/sync_to_nectar_vm.sh`

Cross-host validation status:

- WSL -> `deep-server` -> WSL mirror -> `nectar-vm` sync was tested successfully with a small synthetic run directory
- the authority model was exercised through `run_manifest.yaml`
- a small quoting bug in the initial sync helper implementation was fixed during this validation

## Known deviations and blockers

Current known differences from `deep-server` are:

- Nectar experienced intermittent `Connection refused` failures on port 22 during validation.
- Nectar reachability is good enough for provisioning and tests, but not yet stable enough to treat as fully reliable unattended infrastructure.

## Recommended next refresh on nectar-vm

Once SSH is stable again, refresh these checks in order:

1. reconnect from WSL and confirm host availability
2. recheck the mirrored run manifest directly on Nectar after a stable reconnect
3. decide whether Nectar should become a full production node now or remain the secondary overflow node for selected workloads

That will complete the remaining parity gap with `deep-server`.
