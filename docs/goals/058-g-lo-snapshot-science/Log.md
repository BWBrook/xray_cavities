# Goal 058 log

## 2026-08-14 - reusable fluid core complete; G-LO job running

- Implemented a reusable single-case snapshot-science core split into energy,
  shock, and orchestration modules rather than a case-specific monolith.
- Locked the primary tracer partition to fractional `clip(tr1, 0, 1)`, with
  binary threshold sensitivities at `1e-3`, `5e-3`, and `1e-2`.
- Implemented ambient/lobe thermal, kinetic, and centre-zero gravitational
  accounting from the Stewart group `002_031` atmosphere table. Boundary flux
  is explicitly unmeasured from retained snapshots, so the closure residual is
  not promoted to cocoon energy.
- Implemented fixed-tube, two-sided shock positions and local three-snapshot
  speed/Mach estimates with pressure and density Rankine-Hugoniot checks.
- A live Kunanyi inventory corrected the draft execution assumption: the
  retained G-LO fluid surface is six snapshots at `0/10/20/30/40/50 Myr`, not
  51 annual outputs. This exactly matches the accepted Goal 057 manifest.
- Local validation passed: `31` focused tests, PBS syntax, Python compilation,
  environment-table validation, and `git diff --check`.
- Staged a SHA-locked packet under
  `/u/bwbrook/codex_kunanyi/goal058_g_lo_snapshot_science`; remote hashes,
  wrapper syntax, Python imports, atmosphere-table hash, and no-overwrite gate
  passed.
- Submitted PBS `785483.kunanyi-ohpc` / `g_lo_fluid`; verified state `R` in
  `normal`, one CPU, `64gb`, walltime `48:00:00`.
- Invoked the PBS stop rule immediately after running-state verification. No
  polling, product retrieval, radio execution, X-ray rerun, or cross-case
  comparison occurred.

Status: `submitted_waiting_fluid_analysis_completion`.

## 2026-08-14 - first launch failed before analysis; repair prepared

- Barry reported PBS `785483.kunanyi-ohpc` / `g_lo_fluid` with
  `Exit_status=1`, zero CPU time, and `00:00:13` walltime.
- Compact scheduler/stdout/stderr inspection showed that the locked input
  hashes, six-snapshot HDF5 preflight, grid/timestep checks, and Stewart
  atmosphere validation all passed.
- The first failing line was the expansion of an empty Bash array under
  `set -u`: `resume_args[@]: unbound variable`. No snapshot analysis began and
  no science method or input failed.
- Replaced the optional empty array with portable positional arguments and
  added a regression guard excluding the failed pattern. The failed scheduler
  record remains immutable provenance.

Status: `repair_in_progress_no_science_compute_from_first_attempt`.

## 2026-08-14 - repaired retry submitted

- Local repair validation passed: `17` focused tests, wrapper syntax, Python
  compilation, and `git diff --check`.
- Preserved the failed scheduler/stdout/stderr record under
  `docs/science/assets/g_lo_fluid_snapshot_science_failure_2026-08-14/`.
- Restaged only the repaired wrapper and updated SHA-256 manifest. Remote hash,
  syntax, no-overwrite, and archive-surface checks passed.
- Submitted PBS `785485.kunanyi-ohpc` / `g_lo_fluid`; verified `Q` in `normal`
  with one CPU, `64gb`, and `48:00:00` walltime.
- Invoked the PBS stop rule immediately after queued verification.

Status: `submitted_waiting_repaired_fluid_analysis_completion`.

## 2026-08-14 - fluid surface green; radio analysis submitted

- Barry reported repaired PBS `785485.kunanyi-ohpc` / `g_lo_fluid` with
  `Exit_status=0`, `00:26:13` walltime, `6234620kb` memory, and one CPU.
- Final scheduler inspection showed state `F`, `Exit_status=0`, and the known
  `Stageout_status=1` caveat. Direct stage-root retrieval remained available.
- Remote stdout contains all six per-snapshot completion markers plus
  `fluid_validation=passed`; stderr is zero bytes.
- Retrieved and extracted the compact fluid archive under
  `docs/science/assets/g_lo_snapshot_science_2026-08-14/`. Archive SHA-256:
  `44312bac8f208fcf599e6d86995ccce1768acb094ec04a50fd23eef3260449ed`.
- The fractional-primary bipolar energy table preserves the scientifically
  material non-closure: the unattributed residual fraction changes from about
  `-0.227` at 10 Myr to `-0.577` at 50 Myr. Boundary flux remains unmeasured,
  so this residual is not called cocoon energy.
- Later snapshots detect both shock sides with kinematic Mach numbers spanning
  about `2.15-2.86`.
- Completed the local final-product builder and its decision-boundary tests.
  `15` assembler/inference tests and `16` fluid/radio workflow tests passed;
  `git diff --check` passed.
- Staged the exact corrected-PRAiSE2 source at commit
  `73210e15d4c60e77ffb317b3ee2b9209c049edd4`, its small supporting
  `plutokore` source package, the complete radio helpers, and compatibility
  shims. All `38` staged hashes and the wrapper syntax passed.
- Remote preflight validated the canonical fluid manifest, complete
  `197568 x 5001` retained history cache, continuous output-index chain,
  causal particle roots, and corrected-PRAiSE2 import/provenance lock.
- Submitted PBS `785488.kunanyi-ohpc` / `g_lo_radio`; verified state `R` in
  `normal`, 16 CPUs, `96gb`, and walltime `48:00:00`.
- Invoked the PBS stop rule immediately after running-state verification. No
  polling, retrieval, synthesis, or cross-case comparison followed.

Status: `submitted_waiting_radio_snapshot_analysis_completion`.

## 2026-08-14 - final synthesis path audited while radio runs

- Exercised the final assembler end to end with the retrieved real fluid
  tables and accepted X-ray/cavity surface. A disposable synthetic radio
  surface was used only to test the pending radio schema and joins; it was not
  written into the repository or treated as science evidence.
- Tightened the radio viewing-angle gate from a row-count check to an exact
  `age x view x loss model x frequency` contract. The declared primary radio
  surface must now agree numerically with the `45deg` rows.
- Removed a test-order dependency by importing the synthesis module through
  its production package path.
- Replaced the G-LO-specific final builder with
  `scripts/science/build_snapshot_science.py`. It locks all four factorial
  case identities, environment families, and low/high jet powers, derives the
  known bipolar power from that contract, and rejects source/energy
  normalisation drift.
- Final local validation passed: `34` focused tests, including a synthetic
  high-power `C-HI` contract test, the real-input G-LO synthesis
  rehearsal, exact `150/150` unique radio-view keys, and `git diff --check`.
- The PBS stop rule remains active for `785488.kunanyi-ohpc`; no scheduler
  query or product claim occurred.
- Added the setup-first provisional science note at
  `docs/science/g_lo_snapshot_science_2026-08-14.md`. It separates observation
  from interpretation, records the non-closure and non-corroborating
  Rankine-Hugoniot checks, and carries X-ray topology exclusions without
  waiting to begin the real fluid/cavity review.

Status: `submitted_waiting_radio_snapshot_analysis_completion`.

## 2026-08-14 - radio return green; single-case synthesis complete

- Barry reported PBS `785488.kunanyi-ohpc` / `g_lo_radio` with
  `Exit_status=0`, `04:58:58` walltime, 16 CPUs, and `761396kb` memory.
- Final read-only scheduler evidence showed state `F`, `Exit_status=0`, the
  known `Stageout_status=1` caveat, `radio_validation=passed`, and zero-byte
  stderr.
- Retrieved the compact radio archive, stdout, and stderr. Archive SHA-256 is
  `c648d22e2059b3ec3464537b6a1992896bf1f20b0b0e37e952d7614d9dc1ce8b`;
  the four archive members are readable and contain `50` primary plus `150`
  viewing-angle radio rows.
- Verified corrected PRAiSE2 commit
  `73210e15d4c60e77ffb317b3ee2b9209c049edd4`, exact source SHA-256, causal
  particle matching, positive finite luminosities/fields, and complete
  age/frequency/loss/view keys.
- Repaired one material executable-path defect in the generic final builder:
  direct script invocation now finds the repository package. Added a direct
  CLI regression test.
- Built the real G-LO synthesis once from the retrieved fluid/radio tables and
  accepted X-ray/cavity surface. The product contains `13` scientific tables,
  `7` generated figures, an accepted X-ray context reference, input hashes,
  and validation metadata.
- Focused tests pass (`35`), all generated figures were visually reviewed, the
  archive and metadata parse, and no cross-case result was created.
- Scientific result: empirical radio-power relations centrally over-recover
  known power (`3.09-7.12x`), while valid `45deg` spectral-cavity treatments
  under-recover it (`0.074-0.541x`). All fitted CI breaks remain above
  `15 GHz`, so spectral ages are upper limits and spectral-cavity powers are
  conditional lower bounds.
- Preserved the unresolved boundary-flux closure, X-ray topology exclusions,
  and weak Rankine-Hugoniot corroboration rather than tuning them away.

Decision:
`G_LO_SINGLE_CASE_PIPELINE_GREEN_RECOVERY_BIASES_EXPOSED_NO_CROSS_CASE_CLAIM`.

Status: `complete_single_case_snapshot_science_product`.
