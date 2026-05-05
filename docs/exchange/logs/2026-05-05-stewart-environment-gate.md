# 2026-05-05 Stewart Environment Gate

## Context

Patrick supplied the Stewart environment archive plus historical INIs and the
GRAiLE/XRAiSE bundle under the ignored `env/` asset drop. Stas clarified that
science runs should use the radially averaged tabulated environments rather
than the full 3D grid profiles.

## Assets Selected

- cluster environment for `C-HI` and `C-LO`:
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`
- group environment for `G-LO`:
  `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv`

The full 3D environment cubes remain reference assets only.

## Nectar Gate

`nectar-vm` was resized to `c3.3xlarge`, and the two selected tabulated
environments were staged from the MacBook to:

- `/home/ubuntu/papers/xray_cavities/env/extracted/environments/tabulated/`

Generated no-jet gate directories were copied into the Nectar `jet-setup`
test tree:

- `/home/ubuntu/git/utas-agn/jet-setup/test/environment/stewart_cluster_002003`
- `/home/ubuntu/git/utas-agn/jet-setup/test/environment/stewart_group_002031`

The gate renderer now emits:

- a copied `makefile`
- a hydro-only `definitions.h` with `PARTICLES = NO`
- a `local_make` that keeps UTAS user objects while excluding
  `include Particles/makefile`

This was needed because the current `jet-setup` source template otherwise
keeps `PARTICLES_LP` enabled, even for a no-particle hydro gate.

## Results

Both gates ran to `300 Myr` and passed the existing
`verify-environment-stability.py` checks.

| Environment | Runtime | Max central density drift | Max central pressure drift | Max Mach | Result |
| --- | ---: | ---: | ---: | ---: | --- |
| cluster `002_003` | `39 s` | `0.136%` | `0.226%` | `0.0242` | pass |
| group `002_031` | `30 s` | `0.284%` | `0.473%` | `0.0330` | pass |

Report and plots:

- `docs/science/stewart_environment_gate_2026-05-05.md`
- `docs/science/assets/stewart_environment_gate_2026-05-05/`

## Important Unit Fix

The old Stewart INIs confirm that `JET_END_TIME` and `JET_ACTIVE_TIME` are
PLUTO code-time values, like `tstop` and output intervals. The three-case
renderer was updated so the physical `300 Myr` science duration renders as:

```text
JET_END_TIME = 91980.41813640
JET_ACTIVE_TIME = 91980.41813640
tstop = 91980.41813640
```

The no-jet gates were unaffected because the jet active/end times were zero.

## Nectar SSH Fix

During the gate, Nectar SSH briefly reverted to intermittent
`Connection refused` failures. The VM was `ACTIVE` in OpenStack and the console
looked healthy, so the fix was to disable socket activation and enable the
persistent SSH service:

```bash
sudo systemctl disable --now ssh.socket || true
sudo systemctl enable --now ssh.service
sudo systemctl restart ssh.service
```

Repeated SSH logins succeeded after that.

## Next Step

Run the `C-HI` particle-free high-power cluster rehearsal on resized Nectar.
Only after that is green should the particle-enabled `C-HI` repeat start.
