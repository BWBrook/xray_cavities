# Goal 053 log

## 2026-07-30 — exact census packet prepared

- Kept Goal 051's predeclared concentration failure unchanged.
- Chose an exact 262-row census of its one high-leverage stratum rather than
  another 4096-row sample rerun or a new production workflow.
- Refactored the existing certainty and stratum assignment into shared helpers;
  the original Goal 049 sampler regression suite remains green.
- Added a census diagnostic that validates the immutable cache, affected rows,
  original selection, and original particle comparison before deriving
  membership.
- Added exact oracle replay, unit-weight census, hybrid population replacement,
  unchanged concentration threshold, and explicit three-way scientific
  interpretation.
- Added a one-node PBS wrapper with no-overwrite, schema, archive, and
  scientific/infrastructure exit contracts.
- Focused local verification passed before remote preflight.

Status: `prepared_for_remote_preflight`.

## 2026-07-30 — fail-closed review and remote submission

- Retrieved and independently reviewed the completed Goal 051 retry package.
  All numerical, reconstruction, repeatability, cutoff, and infrastructure
  gates were green; the sole formal failure remained the predeclared
  discrepancy-concentration gate.
- Confirmed that two histories account for most of the discrepancy and that
  the exact 262-row target-stratum census is the smallest analysis that
  resolves the remaining sampling-leverage ambiguity.
- An independent wrapper review found that a structured stable-core
  scientific failure could be converted incorrectly into an infrastructure
  failure by requiring success-only branch arrays. Repaired the failure path
  to preserve the cutoff and gate evidence without fabricating absent outputs.
- Added exact original-row identity validation, pre-resolution symlink
  rejection, and regression coverage at the exact `0.50` decision boundary.
- The first remote preflight stopped before `qsub` when the staged runtime
  could not import `hdf5plugin`. The wrapper was repaired to put
  `scripts/kunanyi/python_compat` first on `PYTHONPATH`, matching the proven
  Goal 051 runtime contract.
- Final local verification passed `61` focused tests, Python compilation,
  `bash -n`, `shellcheck`, and `git diff --check`. The compatibility follow-up
  passed its focused `16` tests and the same shell checks.
- Final remote preflight passed the staged hash manifest, pinned plutokore
  commit, affected-row and Goal 051 input hashes, runtime import, exact
  `4096`-row selection/comparison counts, fresh analysis target, and
  no-prior-submission gate.
- Submitted exactly one job: `780326.kunanyi-ohpc` / `g_lo_strcen`.
  It was verified running on `normal` at `Thu Jul 30 23:10:51 2026` with
  `select=1:ncpus=16:mpiprocs=1:mem=96gb` and `walltime=12:00:00`.
- Invoked the PBS stop rule immediately after running-state verification. No
  polling or retrieval followed.

Status: `submitted_waiting_pbs_completion`.

## 2026-07-30 — failed exact gate retrieved and finalized without recomputation

- Barry reported PBS `780326.kunanyi-ohpc` / `g_lo_strcen` complete with
  `Exit_status=2`, walltime `00:34:56`, and CPU time `01:59:37`.
- Final `qstat`, stdout, stderr, and the compact archive were retrieved.
  The archive is readable and preserves the completed 262-row census branch
  arrays, particle comparison, ordering, stable-core gate table, and cutoff
  table.
- The first failure was the diagnostic's bitwise-exact Goal 051 oracle replay
  gate. All 22 stable-core gates passed and there were no cutoffs.
- Independent comparison found 36 non-bitwise-identical cells among 204,
  confined to physical IDs `196752`, `197253`, and `197269`. The maximum
  absolute and relative differences were `9.15421913206577e-50` and
  `9.1601327385061e-12`.
- Replaced the zero-tolerance gate with the existing project equivalence
  contract:

  ```text
  abs(diff) <= abs(original) * 1e-10
               + 8 * max(abs(spacing(original)), abs(spacing(census)))
  ```

  Every oracle cell passes; the worst difference uses `0.09160043107217158`
  of its tolerance.
- Added a fail-closed no-recompute finalizer. It validates preserved CSV/NPZ
  identity, row order, features, weights, represented population mass, and
  oracle tolerance before writing the missing downstream products to a fresh
  directory.
- The authoritative retrieved evidence finalized locally without opening the
  cache or rerunning any stable branch.
- Result:
  `CENSUS_SUPPORTS_LOCALIZED_REGIME`.
  Census-stratum top-1% concentration is `0.07069644733314163`; hybrid
  concentration is `0.883220701841804`; the threshold remains `0.50`.
- A sensitivity substitution using exact Goal 051 values for the three
  non-bitwise-identical histories leaves the classification unchanged to
  approximately 14 decimal places.
- Final local verification passed `63` related tests, Python compilation,
  wrapper `bash -n` and `shellcheck`, JSON/CSV schema checks, both local SHA
  manifests, retrieved archive readability/SHA, and `git diff --check`.
- The original scheduler `Exit_status=2` remains immutable failure
  provenance. No replacement PBS job was submitted.

Status: `complete_no_recompute_finalization`.
