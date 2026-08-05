# Current Status

Last updated: 2026-08-05
Repository: `/Users/bwbrook/papers/xray_cavities`
Primary role: private scientific control-plane shell for the X-ray Cavities
three-case project.

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

- Cases: `C-HI`, `C-LO`, and `G-LO`, with endpoint-first comparison as the
  current scientific surface.
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

## Active Checkpoint

### Goal 055: G-LO pressure-history production-default decision

- Status: `complete_local_method_decision`.
- Decision:
  `UNSMOOTHED_PRIMARY_LOG_SG_REQUIRED_SENSITIVITY_NO_FINAL_FREEZE`.
- Stable unsmoothed pressure is the provisional project-analysis primary;
  positivity-preserving log-SG is required sensitivity analysis.
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

- The project pressure-method primary remains unsmoothed, with log-SG required
  as sensitivity. Supervisor review is still required before new production
  commitments or publication-facing method claims.
- PRAiSE2 is not promoted; radio/raytracing products remain diagnostic rather
  than validated observables.
- X-ray cavity topology remains conditional rather than frozen.
- Level 3 gravitational energy remains `blocked_missing_potential`.
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
