# Handover Note: 2026-04-30 Nectar official jet assignment and tiny 3D smoke

## Session Context

- Machine used: MacBook Neo as control plane; resized `nectar-vm` as execution host
- Operator path: `/Users/bwbrook/papers/xray_cavities`
- `xray_cavities` commit: `4aca750` plus local working-tree edits
- Relevant UTAS AGN repo commits on the MacBook mirrors:
  - `pluto`: `2674fc3`
  - `jet-setup`: `e17ac8f`
  - `plutokore`: `e80252c`

## What Was Done

- Resized `nectar-vm` from `c3.xsmall` to `c3.3xlarge`.
- Ran Patrick's official Martin Krause PLUTO jet assignment using
  `Test_Problems/HD/Jet`:
  - 2D cylindrical HD
  - external Mach `20`
  - pressure-matched jet and uniform environment
  - two resolutions, `10` and `20` cells per beam radius
  - final time `15`
- Added a versioned workflow bundle:
  - `scripts/pluto_onboarding/official_jet_assignment/`
- Generated assignment-facing artifacts:
  - `docs/onboarding/reports/2026-04-30-official-jet-assignment.qmd`
  - `docs/onboarding/assets/official_jet_assignment_2026-04-30/`
- Ran a tiny full-3D Cartesian `jet-setup` smoke:
  - HD
  - 3D Cartesian
  - particles off
  - King environment
  - grid `48 x 48 x 72`
  - final time `300`
- Added a versioned workflow bundle:
  - `scripts/pluto_onboarding/jet_setup_tiny_3d_cart/`
- Generated smoke artifacts:
  - `docs/onboarding/reports/2026-04-30-jet-setup-tiny-3d-cart.qmd`
  - `docs/onboarding/assets/jet_setup_tiny_3d_cart_2026-04-30/`

## Validation

- Official 2D assignment:
  - both PLUTO runs completed on Nectar
  - four nonzero density snapshots were generated for each resolution
  - final bow positions were similar across resolutions:
    - `10` cells/R: `19.550`
    - `20` cells/R: `19.475`
  - measured mean bow speeds were similar:
    - `10` cells/R: `1.303`
    - `20` cells/R: `1.298`
- Tiny 3D Cartesian `jet-setup` smoke:
  - scaffold, compile, run, and analysis completed on Nectar
  - final output was readable by the `plutokore` analysis lane
  - final grid shape was `48 x 48 x 72`
  - maximum absolute axial velocity was `1.050e-01`
  - `10680` cells had `|vx3| > 1e-3`

## Current State

- The official 2D assignment is now reproducible and documented.
- The tiny 3D Cartesian `jet-setup` build/run/output/analyze path is now green
  on resized `nectar-vm`.
- The tiny 3D smoke is not science resolution and does not yet exercise
  particles, radio products, or HDF5 output.
- After the runs, `nectar-vm` was resized back down to `c3.xsmall`; SSH works
  and `/data` remains mounted.

## Next Recommended Step

1. Add the next Nectar smoke rung: particle-enabled and/or HDF5-enabled output
   at similarly tiny scale.
2. Keep the next 3D science cases off Nectar unless they are deliberately tiny;
   production-scale 3D belongs on `kunanyi`.
3. Begin `kunanyi` setup after the remaining Nectar smoke hooks are green:
   SSH/jumpbox, modules, PLUTO build, PBS short job, and artifact retrieval.

## Sync Notes

- `xray_cavities` was not committed or pushed during this run.
- `nectar-vm` contains the remote workspaces:
  - `/home/ubuntu/work/pluto-onboarding/official_jet_assignment`
  - `/home/ubuntu/work/pluto-onboarding/jet_setup_tiny_3d_cart`
- After committing, `nectar-vm` should pull the updated repo if it needs local
  report sources.

## Blockers / Risks

- The 3D smoke did not validate particle/radio/HDF5 products.
- The 3D smoke used a coarse HD setup only; it is an infrastructure and
  geometry test, not a physical result.
