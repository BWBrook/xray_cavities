# Goal 063 log

## 2026-08-26 - opened

- Accepted Goal 062 as the common four-case fluid census and carried forward
  its energy, gravity, tracer, and shock contracts unchanged.
- Prespecified a paired cluster diagnostic for `C-HI` and `C-LO` at eight
  anchor ages and five spherical shells. The primary far-field control is
  `r >= 100 kpc` through `20 Myr`, before either cluster front enters it.
- Required shell sums to reconstruct the accepted Goal 062 accounted-energy
  surface. Baseline cancellation is recorded as an absolute difference rather
  than an undefined relative error around zero.
- Locked the shock-domain rule from existing Goal 062 evidence. `G-HI` is
  position-valid through snapshot `47` and three-snapshot-kinematics-valid
  through snapshot `46`; the other three cases remain domain-valid through
  snapshot `50`.
- Added a streaming HDF5 diagnostic and a paired one-node PBS wrapper. Raw
  simulation outputs remain read-only and no production simulation is run.

## 2026-08-26 - remote preflight and submission

- Refreshed the authorized Chrome/Open OnDemand SSH window and returned to the
  repository helpers for terminal-first remote work.
- Confirmed `51/51` canonical float files, matching cluster-environment hashes,
  all `16` selected HDF5 files with required variables and shape
  `(1014,960,960)`, and `51/51` Goal 062 reference rows.
- Staged five source/wrapper files plus their SHA-256 manifest under
  `/u/bwbrook/codex_kunanyi/goal063_cluster_background_age_validity`; remote
  hashes and `bash -n` passed.
- Submitted PBS `787276.kunanyi-ohpc` / `cl_bgdiag`, verified `Q` in `normal`,
  with `2` CPUs, `96 GB`, and `04:00:00` walltime.
- Invoked the PBS stop rule after queued proof; no polling or product claim
  followed.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-26 - completion and synthesis

- Barry reported `Exit_status=0` for PBS `787276.kunanyi-ohpc`; final qstat
  confirmed state `F`, walltime `00:30:57`, and two CPUs.
- The remote wrapper validated both cases, `16` anchor snapshots, and `80`
  shell rows. Stderr is empty. `Stageout_status=1` remains a scheduler caveat,
  but the stage-root archive and logs were present and directly retrieved.
- Retrieved the `11`-member archive with SHA-256
  `5633df0a8be47b3142336c39ab2bb2dad8a7220ac1176a567430b828494d7a15`.
  No HDF5 or particle payload was copied or modified.
- In the clean early far field, absolute `C-HI` and `C-LO` energy terms match
  within `0.024%`, establishing a common atmosphere-evolution term.
- At the `C-LO` endpoint, `94.61%` of the accounted change lies beyond
  `100 kpc`, with zero tracer and no shock arrival. Removing that far-field
  term leaves `1.2908` times injected energy inside `100 kpc`, retained only as
  an upper bound because inner background evolution is uncorrected.
- Confirmed the Goal 063 shock windows: `G-HI` positions through snapshot `47`
  and three-snapshot speed/Mach through snapshot `46`; other cases remain
  domain-valid through `50`.

Status: `complete_product`.
Decision:
`C_LO_LARGE_NORMALIZED_BUDGET_BACKGROUND_DOMINATED_SHOCK_WINDOWS_LOCKED`.
