# Current Status

Last updated: 2026-08-20
Repository: `/Users/bwbrook/papers/xray_cavities`
Primary role: private scientific control-plane shell for the X-ray Cavities
simulation project.

## Read This First

Pull the latest repository before relying on this handoff:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

This file is intentionally short. It records the active state and decisions;
dated goal logs, exchange logs, science notes, and their assets are the
historical provenance record. Do not treat old material in those records as a
current instruction without checking its goal status.

## Project Contract

- Existing completed cases: `C-HI`, `C-LO`, and `G-LO`.
- Intended factorial set: cluster/group environments crossed with low/high jet
  power, adding planned `G-HI` as the missing fourth case.
- Preferred endpoint viewing surface: `0/45/90 deg`; nonzero views use
  `edge_overlap_uniform_cell_projection`.
- Products are compact prove-out evidence unless a science note explicitly
  promotes them; they are not publication-ready observables by implication.
- Remote jobs must be explicit, no-overwrite, provenance-preserving, and
  stopped after queued/running verification unless a completion re-check is
  authorized.
- Raw HDF5, particle, and other bulky production files stay remote while an
  active analysis depends on them. Local bundles should contain compact
  products, manifests, checksums, and review logs.

## Supervisor Priority And Execution Order

- Scientific analysis may proceed now on `G-LO`, which has the complete
  retained particle-history sequence. The PRAiSE coefficient science gate is
  green; corrected PRAiSE2 is the production method once its tested source
  change is published to the fork-backed working branch.
- TPAC has approved the storage increase. The authenticated dashboard reports
  `20 TiB` allocated and `8 TiB` occupied, approximately `12 TiB` headroom
  before the new runs.
- Full-history `C-HI` and `C-LO` completed green under Goal 059 and are banked
  as a matched pair. Each retains the exact 50 Myr endpoint, `51/11` fluid
  surfaces, `5001` particle histories, and approximately `2.9 TiB` of raw
  evidence.
- Fresh `G-HI` is the next production case needed to complete the 2 x 2
  environment-by-jet-power factorial set. Existing full-history `G-LO` remains
  accepted and should not be rerun without a demonstrated missing surface.

## Per-Snapshot Science Analysis Contract

- Apply the supervisor directive in
  `agent_comms/threads/2026-08-12-snapshot-science-analysis-contract.md` to
  every available `G-LO` snapshot now and later to the complete four-case set.
- Required surfaces include lossless/full-loss radio luminosity at
  `0.15/0.5/1.4/4.5/15 GHz`, X-ray cavity energies, cell-wise ambient/lobe
  thermal-kinetic-gravitational accounting, direct/residual cocoon energy with
  closure, shock speed and Mach number, spectral age, and two families of
  inferred jet power.
- The primary science tests are cavity-energy bias versus shock strength and
  inferred versus known bipolar jet power. Preserve `2.5pV` as the adopted
  non-relativistic interpretation and `4pV` as the literature comparator.
- Corrected PRAiSE2 governs final full-loss radio production. This does not
  block the other `G-LO` analysis components or pipeline preparation.

## Active Checkpoint

### Goal 059: cluster full-history production

- Status: `complete_matched_cluster_full_history_production`.
- Decision: `MATCHED_CLUSTER_FULL_HISTORY_PAIR_GREEN_G_HI_READY`.
- Quota gate: TPAC reports `20 TiB` allocated and `8 TiB` occupied. Goal 057's
  conservative forecast for these two raw cases is `5.638 TiB`.
- The matched contract is fresh `C-HI` and `C-LO`, Stewart cluster `002_003`,
  `50 Myr`, float HDF5 every `1 Myr`, double HDF5 every `5 Myr`, and complete
  particle histories every `0.01 Myr`.
- PBS `785822.kunanyi-ohpc` / `c_hi_hist` completed with `Exit_status=0` in
  `32:30:03`. The exact 50 Myr endpoint, all `51/11` float/double HDF5
  checkpoints, and the continuous `0..5000` particle history passed. The
  banked run occupies approximately `2.9 TiB`.
- PBS `785823.kunanyi-ohpc` / `c_lo_hist` completed with `Exit_status=0` in
  `31:49:01`. Its exact 50 Myr endpoint, all `51/11` float/double HDF5
  checkpoints, and the continuous `0..5000` particle history passed. The
  banked run also occupies approximately `2.9 TiB`.
- The paired cluster tranche is complete at approximately `5.8 TiB` combined.
  No raw payload was copied or changed. Do not compact/delete source files or
  submit `G-HI` by implication; the next production launch remains a separate
  consequential decision.
- Science note/assets:
  `docs/science/cluster_full_history_production_2026-08-17.md` and
  `docs/science/assets/cluster_full_history_production_2026-08-17/`.
- Goal/log: `docs/goals/059-cluster-full-history-production/` and
  `docs/exchange/logs/2026-08-17-cluster-full-history-production.md`.

### Goal 058: G-LO snapshot science

- Status: `complete_single_case_snapshot_science_product`.
- Decision:
  `G_LO_SINGLE_CASE_PIPELINE_GREEN_RECOVERY_BIASES_EXPOSED_NO_CROSS_CASE_CLAIM`.
- A reusable single-case analysis core now covers retained-snapshot provenance,
  fractional-primary plus binary-sensitivity tracer partitions, ambient/lobe
  thermal-kinetic-gravitational accounting, explicit unresolved boundary flux,
  two-sided shock dynamics, corrected-PRAiSE2 radio/spectral-age inference, and
  the final compact synthesis surface.
- Live Kunanyi preflight confirmed that compaction retained six G-LO float
  snapshots at `0/10/20/30/40/50 Myr`, exactly matching Goal 057. The draft
  51-snapshot assumption was corrected before submission; no missing ages were
  invented or substituted.
- PBS `785483.kunanyi-ohpc` / `g_lo_fluid` ended with `Exit_status=1`, zero CPU
  time, and `00:00:13` walltime. All locked-input and six-snapshot HDF5
  preflights passed; analysis did not begin. Kunanyi Bash rejected expansion
  of an empty optional-argument array under `set -u`. The wrapper now uses
  portable positional arguments and carries a regression guard.
- Repaired PBS `785485.kunanyi-ohpc` / `g_lo_fluid` completed green with
  `Exit_status=0`, `00:26:13` walltime, all six snapshot markers, and zero-byte
  stderr. The retrieved archive SHA-256 is
  `44312bac8f208fcf599e6d86995ccce1768acb094ec04a50fd23eef3260449ed`.
- Fluid results detect both shock sides at later ages with kinematic Mach
  numbers about `2.15-2.86`. The unmeasured-boundary closure fraction changes
  from about `-0.227` at 10 Myr to `-0.577` at 50 Myr; this residual remains
  unattributed and is not promoted to cocoon energy.
- Corrected-PRAiSE2 PBS `785488.kunanyi-ohpc` / `g_lo_radio` completed with
  `Exit_status=0`, `04:58:58` walltime, `radio_validation=passed`, and
  zero-byte stderr. The retrieved archive SHA-256 is
  `c648d22e2059b3ec3464537b6a1992896bf1f20b0b0e37e952d7614d9dc1ce8b`.
- The final radio surface has exactly `50` primary `45deg` rows and `150`
  unique age/view/loss/frequency rows. Its corrected PRAiSE2 commit and source
  hash match the staged contract, and all particle states are causal.
- The real local assembler produced `13` scientific tables and `7` diagnostic
  figures. Its direct executable entry point is now regression-tested; `35`
  focused tests pass.
- All fitted continuous-injection breaks remain above the `15 GHz` observed
  band. Spectral ages are therefore upper limits. Central empirical
  radio-power relations recover `3.09-7.12x` known power, while valid `45deg`
  spectral-cavity treatments recover `0.074-0.541x` and remain conditional
  lower bounds.
- The setup-first note preserves the negative zero-boundary closure as
  unresolved, the weak Rankine-Hugoniot corroboration, and 10/30 Myr X-ray
  topology exclusions. No cross-case claim is made.
- Science note/product:
  `docs/science/g_lo_snapshot_science_2026-08-14.md` and
  `docs/science/assets/g_lo_snapshot_science_2026-08-14/`.
- Goal/log: `docs/goals/058-g-lo-snapshot-science/` and
  `docs/exchange/logs/2026-08-14-g-lo-snapshot-science.md`.

### Goal 057: four-case pre-production readiness

- Status: `complete_preproduction_readiness_quota_hold_superseded_by_goal059`.
- Decision:
  `FOUR_CASE_CONTRACT_AND_METHOD_GATES_GREEN_QUOTA_APPROVAL_PENDING`.
- The matched production contract is `C-HI` full-history rerun, `C-LO`
  full-history rerun, then new `G-HI`; existing full-history `G-LO` is analysed
  now and rerun only if a specific missing surface is demonstrated.
- TPAC approved the requested increase on 2026-08-17. Goal 059 has submitted
  the two cluster reruns; the historical quota hold no longer applies.
- Conservative uncompressed storage is `2.819 TiB` per case and `11.277 TiB`
  for four matched cases. The validated pilot ratios project about `0.936 TiB`
  retained per case and `3.745 TiB` across four cases, but this excludes
  source/copy overlap and safety margin. Keep the quota request at least
  `16 TiB`, preferably `20 TiB`; no production submission occurs before
  approval.
- The approved PRAiSE2 equation (3) coefficient is implemented locally in the
  `plutokore` working tree. PBS `785271.kunanyi-ohpc` / `g_lo_c1cmp` completed
  green; corrected PRAiSE2 is the production method. Its 50 Myr integrated
  effect ranges from `-0.096%` at 0.15 GHz to `-2.694%` at 15 GHz, with zero
  added non-finite values.
- The corrected plutokore source and regression test are integrated into
  `master` as commit `73210e15d4c60e77ffb317b3ee2b9209c049edd4` from
  tested source commit `a190f0d96610c781a7ff71860333a0aae3cdfe92`; future
  production staging pins the canonical `master` revision.
- PBS `785272.kunanyi-ohpc` / `h5_revpil` produced bitwise-valid reversible
  float and double copies with `72.45%` and `55.58%` file-size reductions, then
  failed only because the fresh XRAiSE process lacked `HDF5_PLUGIN_PATH`.
- Future compression now discovers the plugin path and routes integers plus
  real `cell_coords`/`node_coords` arrays through gzip+shuffle. No original was
  changed or deleted and the pilot copies were not recompressed.
- Readability-only finalizer PBS `785371.kunanyi-ohpc` / `h5_readfin` completed
  green. Fresh-process ZFP reads and real XRAiSE analysis passed; reversible
  HDF5 compression is technically validated for future completed copies.
- No original may be deleted from the compression pilot. Any later source
  deletion requires an explicit lifecycle decision after validation.
- A reusable five-stage `G-LO` snapshot-analysis contract now covers source
  truth, energy/gravity/shocks, X-ray/cavity, radio/spectral age, and inferred
  jet-power synthesis at `0/10/20/30/40/50 Myr`.
- Science note/assets:
  `docs/science/four_case_preproduction_readiness_2026-08-13.md` and
  `docs/science/assets/four_case_preproduction_readiness_2026-08-13/`.
- Pilot completion notes/assets:
  `docs/science/g_lo_praise2_coefficient_correction_2026-08-14.md`,
  `docs/science/reversible_hdf5_compression_pilot_2026-08-14.md`, and their
  matching dated asset directories.
- Goal/log: `docs/goals/057-four-case-preproduction-readiness/` and
  `docs/exchange/logs/2026-08-13-four-case-preproduction-readiness.md`.

### Goal 056: G-LO last-shock PRAiSE comparison

- Status: `complete_reference_accepted_coefficient_followup_resolved_by_goal057`.
- Patrick's review supersedes the provisional Goal 055 unsmoothed-primary
  convention: corrected `plutokore.radio.praise2.praise(...)`, following the
  published equation (3), is the intended reference. The interval-aware
  validation is accepted; Goal 057 has now completed the coefficient-only
  correction and validation.
- Goal 056 compares PRAiSE1, native PRAiSE2, controlled-common-input PRAiSE2,
  and Goal 050 on the exact deterministic 4096-particle panel, using only the
  latest-shock-to-evaluation interval for scientific classification.
- First attempt PBS `784909.kunanyi-ohpc` (`g_lo_lstcmp`) is immutable failed
  provenance (`Exit_status=1`). Its inputs/imports passed, but the diagnostic
  incorrectly required every irregular source timestep to survive PRAiSE2's
  0.01 Myr resampling; evidence archiving also invoked a non-executable helper
  directly. No Goal 056 science decision was produced.
- The repair now reproduces pinned PRAiSE2's order: uniform resampling,
  backfilling, then optional native linear Savitzky-Golay smoothing. Local and
  Kunanyi-side irregular-history replay checks passed, including omitted
  source-index provenance. Archiving now invokes the helper through `bash`.
- Retry PBS `784931.kunanyi-ohpc` (`g_lo_lstcmp_r1`) is immutable failed
  provenance (`Exit_status=2`). It cleared the earlier PRAiSE2 gates and failed
  only when the contextual Goal 050 detailed comparator assumed every
  frequency had finite endpoint and injection gamma. No science decision was
  produced; its compact failure archive was retrieved successfully.
- The state-aware repair retains Goal 050 cutoffs as zero, reconstructs finite
  states, and records non-finite/subrelativistic states as unavailable. It
  leaves all PRAiSE2 gates unchanged. Local and Kunanyi-side focused tests
  passed.
- Final PBS `784939.kunanyi-ohpc` (`g_lo_lstcmp_r2`) completed the diagnostic
  and archive, then returned the intentional science-hold exit `3`. Native
  retained pressures stayed positive and no native numerical failure occurred.
- The only hold was two native/common checks of one width-one representative
  history. The detailed path bypassed the approved population singleton
  convention; all `62/62` applicable direct full-loss replays matched exactly.
  The local diagnostic contract is repaired and tested; no fourth remote run
  is warranted.
- Common-input PRAiSE2 still differs materially from PRAiSE1 for `17.96%` of
  weight at `0.15 GHz`, `27.17%` at `1.4 GHz`, and `12.79%` by spectral index.
  Native smoothing alone is material for `0.756%` of weight and `0%` by
  spectral index. The difference is therefore principally method recurrence,
  coefficients, and cutoff handling rather than smoothing.
- Patrick accepted Goal 056's interval-aware validation and selected PRAiSE2
  as the published-method reference. Its recurrence, cutoff, and smoothing
  differences from PRAiSE1/Goal 050 are retained as distinct-method behaviour.
- The pinned PRAiSE2 radiative coefficient was `0.7500000023105955` of the
  published equation (3) value. Goal 057 restored and isolated the missing
  `4/3` multiplier; the coefficient probe, particle histories, weighted
  luminosities, endpoint maps, finite-value gates, and regression tests pass.
- Corrected `pk.radio.praise2.praise(...)` is the production method. Preserve
  the uncorrected Goal 056 products as baseline provenance. The tested source
  correction is integrated into plutokore `master` as commit
  `73210e15d4c60e77ffb317b3ee2b9209c049edd4`; its original validation commit
  is `a190f0d96610c781a7ff71860333a0aae3cdfe92`.
- Goal/log:
  `docs/goals/056-g-lo-praise-last-shock-comparison/` and
  `docs/exchange/logs/2026-08-10-g-lo-praise-last-shock-comparison.md`.
- First-attempt failure note/logs:
  `docs/science/g_lo_praise_last_shock_comparison_failure_2026-08-11.md` and
  `docs/science/assets/g_lo_praise_last_shock_comparison_failure_2026-08-11/`.
- Retry failure note/logs:
  `docs/science/g_lo_praise_last_shock_comparison_retry_failure_2026-08-11.md`
  and
  `docs/science/assets/g_lo_praise_last_shock_comparison_retry_failure_2026-08-11/`.
- Completion/review note and assets:
  `docs/science/g_lo_praise_last_shock_comparison_review_2026-08-11.md` and
  `docs/science/assets/g_lo_praise_last_shock_comparison_hold_2026-08-11/`.

### Goal 055: G-LO pressure-history production-default decision

- Status: `complete_local_method_decision`.
- Decision:
  `UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE`.
- Its unsmoothed-primary/log-SG-sensitivity recommendation is retained as
  historical project evidence but is superseded operationally by Patrick's
  request to treat pinned PRAiSE2 as the intended reference.
- Published-style linear Savitzky-Golay smoothing is inadmissible for the
  current G-LO cache because it creates `216035` non-positive pressure values
  across `99108/197398` eligible histories.
- In the census-replaced population, log-SG shifts the no-loss amplitude by
  `1.80646%` and the full-loss amplitudes by `1.89273-1.94849%`; the full-loss
  spectral-index shift is only `-0.00024496`.
- This is a provisional internal convention, not a physical uncertainty
  interval or final publication-method freeze.
- Before new C-HI/C-LO history production or publication-facing radio use,
  request one focused Patrick/Stas review of this method contract.
- Science note/assets:
  `docs/science/g_lo_pressure_history_production_default_decision_2026-08-05.md`
  and
  `docs/science/assets/g_lo_pressure_history_production_default_decision_2026-08-05/`.

### Goal 054: G-LO pressure-method synthesis

- Status: `complete_local_synthesis`.
- Decision: `LOCALIZED_REGIME_SYNTHESIZED_NO_FURTHER_CENSUS`.
- The exact census preserves population mass and reduces weighted discrepancy
  by `58.4531%`; hybrid full-loss shifts are `1.8927%` at 0.15 GHz and
  `1.9485%` at 1.4 GHz.
- The target stratum is `0.1326%` of population mass but contributes
  `60.0462%` of hybrid discrepancy. No single remaining stratum clears the
  `0.50` concentration gate.
- This is a diagnostic synthesis, not a physical uncertainty estimate,
  causal attribution, or production-default change.
- Goal 055 has now interpreted this evidence. No further census is warranted.
- Science note/assets:
  `docs/science/g_lo_pressure_method_synthesis_2026-08-01.md` and
  `docs/science/assets/g_lo_pressure_method_synthesis_2026-08-01/`.

### Goal 053: G-LO critical-stratum census

- Status: `complete_no_recompute_finalization`.
- Decision: `CENSUS_SUPPORTS_LOCALIZED_REGIME`.
- PBS `780326.kunanyi-ohpc` remains immutable failed provenance
  (`Exit_status=2`, `Stageout_status=1`). The preserved census passed the
  scale-aware tolerance; `168/204` branch cells are bitwise identical and the
  remaining differences are confined to three physical IDs.
- No cache or stable-branch computation was rerun after finalization.
- Science/failure/repair records are under
  `docs/science/g_lo_critical_stratum_census*.md` and their dated assets.

### Goal 052: PRAiSE2 high-level method validation

- Status: `complete_local_fail_closed_gate`.
- Decision: `PRAISE2_HIGH_LEVEL_VALIDATION_HOLD_NO_PROMOTION`.
- The pinned high-level interface exposes emissivity but not the gamma,
  cutoff, and fallback evidence needed for method promotion; material
  coefficient differences remain.
- Do not promote PRAiSE2, read the 33 GB cache, or change production defaults
  without a new explicit method decision.

### Goal 051: G-LO stable method-value comparison

- Status: `complete_comparison_gate_fail_discrepancy_concentration`.
- Decision: `G_LO_STABLE_METHOD_VALUE_FAIL`.
- The deterministic 4096-row comparison passed infrastructure and numerical
  gates but failed the predeclared discrepancy-concentration gate: the top 1%
  of represented weight contributes `0.9511627` of total method discrepancy.
- Two immediately post-shock histories account for `0.8339063`; exclusion is
  an influence diagnostic, not an alternative estimator. Do not weaken the
  gate or submit another retry without a new scientific rationale.

## Holds and Caveats

- Goal 056 establishes PRAiSE2's post-shock numerical usability and scientific
  interpretability. Patrick has accepted the distinct-method behaviour. The
  equation (3) `4/3` coefficient is implemented locally; matched radio
  production remains held until Goal 057's coefficient-only remote comparison
  verifies its scientific effect. Radio/raytracing products remain diagnostic
  until then.
- X-ray cavity topology remains conditional rather than frozen.
- The Level 3 gravitational-energy method is now defined by Stas: construct
  the initial-atmosphere potential from `tabulated_cosmo_002003.csv` and apply
  the cellwise mass-change convention with tracer-weighted gas/lobe reporting.
  The component remains not computed, but is no longer blocked by a missing
  potential convention.
- `pV`, adopted `2.5pV`, and `4pV` conventions remain carried-forward
  conventions, not a new physical default.
- No new production run, broad source-age sweep, comparison expansion, or
  publication-facing claim is authorized by this handoff alone.

## Repository Simplification

The dated architecture review and current tranche are recorded in
`docs/science/codebase_simplification_audit_2026-08-05.md`.

- `pyproject.toml` now keeps direct runtime dependencies separate from the
  development/docs group; `uv.lock` is synchronized and the focused science
  tests remain green.
- `scripts/kunanyi/archive_file_list_payload.sh` owns the representative
  file-list archive contract used by
  `scripts/kunanyi/g_lo_endpoint_first_products.pbs`. It refuses existing
  snapshot/archive paths and validates the resulting tarball.
- `scripts/science/diagnose_g_lo_pressure_method_value.py` now isolates the
  two pressure-method calls, emissivity checkpoints, and non-finite evidence
  persistence in `_run_pressure_modes`; numerical helpers and output schemas
  are unchanged.
- The asset tree is not mass-deleted. Canonical science products are retained;
  transport copies and byte-identical generated tables are only candidates
  for later reference-checked pruning.
- Do not add a second general ledger. Use the existing data-lifecycle strategy
  for promote/prove/prune decisions.

## Resume Checklist

1. Fetch/pull the latest `origin/main` without disturbing a dirty worktree.
2. Read this file, the latest relevant `Goal.md`/`Log.md`, and the science
   note before interpreting a result.
3. Separate observed scheduler/product facts from inference and caveats.
4. Preserve accepted assets and raw-data provenance; never overwrite on rerun.
5. Run the smallest high-value validation needed for the current decision,
   then hand off rather than polishing historical records.

## Historical Pointers

- Project plan and case definitions: `docs/science/three_case_spec.md` and
  `docs/Honours_Research_Plan.md`.
- Data lifecycle: `docs/science/xray_cavities_data_lifecycle_strategy_2026-07-10.md`.
- Current goals and logs: `docs/goals/`, `docs/exchange/logs/`, and
  `agent_comms/threads/`.
- Earlier endpoint, age-axis, topology, C-LO, and G-LO evidence remains in
  the dated science notes and assets; this file deliberately does not replay
  that history.
