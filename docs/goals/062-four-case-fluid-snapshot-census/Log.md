# Goal 062 log

## 2026-08-25 - opened

- Accepted Goal 061 as the final production run. The matched raw factorial now
  has `51/11/5001` float/double/particle surfaces for all four cases.
- Selected the full four-case fluid census as the first analysis tranche:
  `51` annual float snapshots for each of `C-HI`, `C-LO`, `G-HI`, and `G-LO`.
- Reused the accepted Goal 058 fluid controller without changing its
  scientific calculations.
- Added a single-node wrapper that preflights all canonical chains, runs the
  four cases concurrently, validates `204` snapshot records and the locked
  energy/shock boundaries, and creates a compact no-overwrite archive.
- Radio and projected X-ray cavity work are deliberately deferred until the
  census identifies the scientifically useful and technically valid ages.

## 2026-08-25 - remote preflight and submission

- Refreshed the TPAC jumpbox selector through the authorized Chrome route and
  returned to the repository helpers for terminal-first staging/submission.
- Staged six source/wrapper files plus the SHA-256 manifest under
  `/u/bwbrook/codex_kunanyi/goal062_four_case_fluid_snapshot_census`.
- Remote staged hashes and `bash -n` passed. The target analysis/archive
  surfaces were absent.
- Canonical float counts passed as `51/51/51/51`; G-HI uses the accepted
  scratch-then-home union.
- Cluster and group environment tables matched within their pairs and matched
  the locked SHA-256 values.
- Submitted PBS `786969.kunanyi-ohpc` / `four_fluid`, state `Q` in `normal`,
  with `select=1:ncpus=4:mpiprocs=1:mem=96gb` and `walltime=12:00:00`.
- Invoked the PBS stop rule immediately after queued proof; no polling or
  product claim followed.

Status: `submitted_waiting_pbs_completion`.

## 2026-08-25 - completion, retrieval, and first synthesis

- Barry reported PBS completion for `786969.kunanyi-ohpc` / `four_fluid` with
  `Exit_status=0` and walltime `04:18:49`.
- A single final remote review confirmed `job_state=F`, all four case exit
  statuses `0`, `four_case_validation=passed cases=4 snapshots=204`, and
  zero-byte stderr. `Stageout_status=1` remains a scheduler caveat; the stage
  archive/stdout/stderr were present and readable.
- Retrieved the `13,417,876` byte compact archive plus stdout/stderr. Archive
  SHA-256 is
  `b4dfb65a9231a53caec776f435ab819ce0b67c61fa9fd7f4aa866a5d7d83ece6`
  and its `646` members pass `tar -tzf`.
- Kept top-level review tables expanded locally while retaining per-snapshot
  axial profiles only in the immutable archive. No raw HDF5 or particle file
  was retrieved or modified.
- Added a lean four-case synthesis: `204` primary fluid rows, `408` primary
  shock-side rows, four endpoint summaries, `32` descriptive factorial
  contrasts, and one diagnostic figure.
- The synthesis exposes two material science gates: the `C-LO` normalized
  ambient budget is dominated by a large background/common-atmosphere term,
  and the late `G-HI` shock reaches the axial domain boundary.

Status: `complete_product`.
Decision:
`FOUR_CASE_FLUID_CENSUS_GREEN_C_LO_ENERGY_BASELINE_AND_G_HI_BOUNDARY_GATES_EXPOSED`.
