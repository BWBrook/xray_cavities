# 2026-08-26 - cluster background and age validity

Goal 063 addresses the two decision gates from Goal 062 without broadening the
analysis. It measures cluster-atmosphere energy changes in radial shells for
the matched `C-HI`/`C-LO` pair and locks the domain-valid shock windows from
the existing four-case census.

The background calculation uses eight anchor ages, five shells, the accepted
centre-zero potential, and full-fluid energy accounting. `r >= 100 kpc` is the
early far-field control; both cluster fronts remain inside that radius through
`20 Myr`. The paired simulations are not a no-jet control, so causal attribution
to unforced atmosphere drift will remain appropriately qualified.

The existing shock surface supports `G-HI` front positions through snapshot
`47`, but centred three-snapshot speeds only through snapshot `46`: the speed
at `47` borrows boundary-limited snapshot `48`. Other cases retain the required
domain margin through the endpoint.

Remote preflight passed for the canonical chains, selected HDF5 contracts,
Goal 062 references, staged hashes, wrapper syntax, and no-overwrite targets.
PBS `787276.kunanyi-ohpc` / `cl_bgdiag` was submitted with `2` CPUs, `96 GB`,
and `04:00:00`; it was verified `Q` in `normal` at
`Wed Aug 26 08:29:15 2026`.

Barry reported successful completion. Final qstat confirmed `job_state=F`,
`Exit_status=0`, walltime `00:30:57`, and `Stageout_status=1`. The latter is
retained as a scheduler caveat; the stage-root archive and logs were present
and retrieved directly. Both cases, all `16` anchor snapshots, and all `80`
shell rows validated; remote stderr is empty.

The clean early far field agrees between `C-HI` and `C-LO` in absolute energy
to within `0.024%` across all four terms. At the `C-LO` endpoint, `94.61%` of
the whole-domain accounted change lies beyond `100 kpc`, with zero tracer and
no shock arrival. The previously alarming `23.97`-times-injected budget is
therefore background dominated. The inside-`100 kpc` remainder is `1.2908`
times injected energy but remains an upper bound, not a corrected efficiency.

Status: `complete_product`.
Decision:
`C_LO_LARGE_NORMALIZED_BUDGET_BACKGROUND_DOMINATED_SHOCK_WINDOWS_LOCKED`.

Recommended next tranche: lock common paper-analysis ages, then run the
selected-age four-case X-ray/cavity and corrected-PRAiSE2 workflow. Cap `G-HI`
shock-kinematic comparisons at snapshot `46`.
