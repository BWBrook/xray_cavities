# 2026-08-25 - four-case fluid snapshot census

Goal 062 opens the analysis phase on the completed matched factorial. It uses
the accepted per-snapshot energy, gravity, tracer, and shock methods across all
`51` annual float outputs in each of `C-HI`, `C-LO`, `G-HI`, and `G-LO`.

The execution is one four-process, single-node Kunanyi job. It reads the four
canonical raw surfaces without modifying them and writes to a new no-overwrite
analysis root. Radio histories and projected X-ray cavity products remain out
of scope until this common fluid census establishes the valid comparison
surface.

Remote preflight confirmed all four `0..50` float chains, matched atmosphere
hashes within each environment pair, staged source hashes, remote wrapper
syntax, and no-overwrite targets. PBS `786969.kunanyi-ohpc` / `four_fluid` was
submitted with `4` CPUs, `96 GB`, and `12:00:00`; it was verified `Q` in
`normal` at `Tue Aug 25 15:50:47 2026`.

Barry reported successful completion. Final qstat confirmed
`job_state=F`, `Exit_status=0`, walltime `04:18:49`, CPU time `15:25:30`, and
`Stageout_status=1`. The latter is retained as a scheduler caveat; the required
archive and logs were present and directly retrieved.

All four case processes exited `0`. The final validation surface contains
`51` snapshots, `612` energy rows, `306` shock rows, and `51` source rows per
case. Remote stderr is empty. The compact archive has `646` members, size
`13,417,876` bytes, and SHA-256
`b4dfb65a9231a53caec776f435ab819ce0b67c61fa9fd7f4aa866a5d7d83ece6`.

The first descriptive factorial synthesis is complete. It preserves the
unmeasured-boundary caveat and makes no replicate-based inference. Its main
science result is not simply four green trajectories: `C-LO` has a normalized
ambient energy change and closure residual far larger than its low injected
energy, requiring a background-evolution diagnosis, while the `G-HI` shock
reaches within about `1.05 kpc` of the axial domain edge by the endpoint.

Status: `complete_product`.
Decision:
`FOUR_CASE_FLUID_CENSUS_GREEN_C_LO_ENERGY_BASELINE_AND_G_HI_BOUNDARY_GATES_EXPOSED`.

Recommended next tranche: a targeted existing-output background and valid-age
diagnostic, followed by radio/X-ray age selection only after those gates are
resolved. No new PLUTO production run is indicated.
