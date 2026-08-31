# Current Status

Last updated: 2026-08-31
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

- Completed matched-cadence factorial: cluster/group environments crossed with
  low/high jet power (`C-HI`, `C-LO`, `G-HI`, and `G-LO`), each with the
  intended `51/11/5001` float/double/particle temporal surface.
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

- Production is complete. Goal 062 applied the common fluid, gravity, tracer,
  and shock workflow to all `204` annual snapshots; Goal 063 confirmed that
  the large `C-LO` normalized budget is background dominated; and Goal 064
  completed the selected-age X-ray/cavity and corrected-PRAiSE2 surface.
  The 2026-08-28 boundary review now drops `G-HI/50` from all science and
  replaces the single emissivity-weighted spectral-age field with primary
  mean-pressure plus emissivity-weighted sensitivity treatments. A new
  seven-method cavity-age comparison now adds sound, buoyant, refill, shock,
  true, and both spectral clocks with explicit censoring. Goal 065 has been
  regenerated under those corrected gates, Goal 066 completed the selected-
  age dual-space proof, and Goal 067 completed the native 3D shock-energy
  partition. No PLUTO, X-ray, or PRAiSE rerun is required. The next high-value
  step is local synthesis/manuscript integration, not cadence expansion.
- The PRAiSE coefficient science gate is green; corrected PRAiSE2 is the
  production radio method once its tested source change is published to the
  fork-backed working branch.
- TPAC applied the storage increase to home, not scratch. Live quotas are
  `/u/bwbrook=20 TiB` and `/scratch/bwbrook=8 TiB`; Goal 060 mistakenly wrote
  heavy output to scratch. The recovered home continuation now occupies about
  `2.2 TiB`; future production output must use home.
- Full-history `C-HI` and `C-LO` completed green under Goal 059 and are banked
  as a matched pair. Each retains the exact 50 Myr endpoint, `51/11` fluid
  surfaces, `5001` particle histories, and approximately `2.9 TiB` of raw
  evidence.
- Goal 060 G-HI is now complete. A scratch-quota stop at 15 Myr was recovered
  from the validated 10 Myr tuple into home; PBS `786326` reached the exact
  50 Myr endpoint. Its canonical raw sequence uses scratch through 10 Myr and
  home thereafter, with complete `51/11/5001` float/double/particle surfaces.
- Goal 061 `G-LO` is the canonical matched source: exact 50 Myr endpoint,
  continuous `51/11/5001` outputs, and approximately `2.9 TiB` on home
  storage. The older six-age compacted roots remain protected historical
  provenance, not the default science input.

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

### Goal 067: selected-age native 3D shock-energy partition

- Status: `complete_product_recovered_no_hdf5_rerun`.
- Decision:
  `SELECTED_AGE_NATIVE_SHOCK_PARTITION_GREEN_C_LO_LATE_FAIL_CLOSED`.
- The method is frozen before result inspection. It reports native thermal,
  kinetic, gravitational, total, and irreversible-heating terms in the
  connected shocked ambient region at the accepted selected ages.
- Energy changes use the exact same-grid production `t=0` snapshot. The fixed
  initial gravitational potential uses Stas's centre-zero convention.
- Coarser cluster/group no-jet controls calibrate dimensionless false-positive
  thresholds only; they are not called resolution-matched and are not
  subtracted cell by cell.
- The 3D mask is an ambient entropy-excess component connected to a compressed
  axial-front seed. Missing or non-supersonic fronts, unsupported components,
  boundary contact, and front-extent mismatches fail closed.
- The full prespecified surface is complete: `171` total rows and `19` primary
  bipolar case-age rows, of which `15` are quantitative. `C-LO/20--50` fail
  closed because one accepted side is non-supersonic; no values are imputed.
- PBS `789812.kunanyi-ohpc` / `shock_energy` failed immediately as `F/2` with
  zero resource use: Kunanyi's Bash `4.2.46` rejected the wrapper's single
  `declare -n` nameref before calibration or science analysis began.
- The wrapper now uses explicit portable array-count checks, covered by a
  regression test. Original failure evidence is preserved and the repair uses
  fresh `r1` stage, analysis, archive, stdout, and stderr paths.
- PBS `789813.kunanyi-ohpc` completed all four science workers but ended `F/1`
  because the final wrapper validator requested `volume_kpc3` instead of the
  actual `mask_volume_kpc3` field. The validator is repaired. Existing compact
  outputs were validated and archived without reopening HDF5 inputs; recovered
  archive SHA-256 is
  `1287c74a2a9c2891ba2feb6d641128460f9a546828e2380daed901c40b73182d`.
- Net selected shock-region energy is typically `0.58--0.87` of injected
  energy in the three fully quantitative series. Joining this result to Goal
  066 shows that X-ray cavity enthalpy is much smaller than the native shock-
  region reservoir where both are quantitative, while the lobe-recovery bias
  remains dominated by X-ray geometry/topology.
- Method note:
  `docs/science/four_case_selected_age_native_shock_partition_method_2026-08-31.md`.
- Result note:
  `docs/science/four_case_selected_age_native_shock_partition_2026-08-31.md`.
- Goal/log:
  `docs/goals/067-selected-age-native-shock-partition/` and
  `docs/exchange/logs/2026-08-31-selected-age-native-shock-partition.md`.

### Goal 066: selected-age dual-space energetics audit

- Status: `complete_selected_age_proof`.
- Decision:
  `SELECTED_AGE_DUAL_SPACE_PROOF_GREEN_VOLUME_TOPOLOGY_BIAS_DOMINATES`.
- Decision scope: prove the independent native-grid/X-ray join on all `57`
  accepted selected-age views before deciding whether annual cadence and the
  native 3D shock-energy mask materially change the paper analysis.
- Native lobe `pV`, mean pressure, retained energy, and injected energy reuse
  the accepted fractional-tracer cell ledger. No redundant HDF5 reread is
  required for those exact quantities.
- The observer route now derives density and temperature from synthetic X-ray
  projection inputs, masks cavities using X-rays alone, and retains midpoint
  and ellipsoid-volume-averaged pressure across three line-of-sight depths.
  Tracer is not loaded or used in the observer builder.
- The accepted join factorizes cavity-to-lobe enthalpy bias into volume and
  pressure terms and separately reports recovery relative to lobe, retained,
  and injected energy. Goal 067 now adds the prespecified selected-age native
  shock context without changing Goal 066 validity flags.
- Full job `789776.kunanyi-ohpc` / `dual_energy` completed `F/0` in `04:02:12`.
  Its retrieved archive contains all `57` views, has SHA-256
  `1bb57358da88c328c0b34bbdd88aeb8c31f7b9a2f5899c5249bcbb0305730a9f`,
  and has empty remote stderr.
- Scientific review rejected the first joined pressure surface: the original
  `0.03` deprojection penalty over-smoothed high-contrast `G-HI` temperature
  numerators, with residuals near `0.47` and false near-zero pressures. These
  tables are diagnostic evidence only, not a result.
- The all-view sensitivity gate supports regularization `1e-6` plus explicit
  interpolation only where numerator/emissivity support is below `1e-12` of
  its fitted maximum. Pressure-only repair `789809.kunanyi-ohpc` /
  `dual_enfix` completed `F/0`; all `57` views passed with maximum residual
  `1.651e-4` and at most one interpolated shell per view.
- Of `57` selected views, `37` pass the observer topology gate. Pressure
  recovery lies within a factor of two in `36/37`; volume and native lobe-
  enthalpy recovery do so in only `5/37`. Case-median lobe recovery is
  `0.1076`, `6.762`, `0.0363`, and `0.4559` for `C-HI`, `C-LO`, `G-HI`, and
  `G-LO`. Geometry/topology is therefore the dominant selected-age bias.
- Goal 067 materially updates the whole-outburst context: the selected shocked
  region contains far more energy than X-ray cavity enthalpy where both are
  quantitative. Boundary flux remains pending, and `C-LO` remains background
  dominated without matched no-jet subtraction. Annual observer extension is
  not justified by default.
- Science note:
  `docs/science/four_case_selected_age_dual_space_energetics_2026-08-31.md`.
- Goal/log:
  `docs/goals/066-selected-age-dual-space-energetics-audit/` and
  `docs/exchange/logs/2026-08-31-selected-age-dual-space-energetics-audit.md`.

### 2026-08-28 dual-space energetics audit decision

- Status: `selected_age_proof_complete_shock_partition_pending`.
- Every cavity/lobe and total-outburst comparison must retain two independent
  paths: native-grid truth using fractional tracer and cell-wise initial-state
  subtraction, and observer-like X-ray cavity enthalpy using X-ray-only
  geometry and pressure inference. Shock subcomponents remain native-grid
  truth unless a separately validated observable shock model is added.
- Native-grid and X-ray products are joined only after both are complete.
  Tracer may assess X-ray recovery post hoc but may not define or repair the
  observed cavity.
- The matched audit separates volume bias, pressure bias, lobe-enthalpy bias,
  and missing shock/outburst energy. It reports `H_X/H_lobe,grid`,
  `H_X/E_retained`, and `H_X/E_injected` as distinct questions.
- X-ray midpoint pressure and volume-averaged pressure over the inferred
  ellipsoid must both be retained. `2.5pV` remains primary and `4pV` remains
  the literature comparator.
- Science design:
  `docs/science/four_case_dual_space_energetics_audit_design_2026-08-28.md`.

### 2026-08-28 cavity-age and inferred-power comparison

- Status: `complete_method_surface_integrated_into_goal065`.
- The retained quantitative surface contains `37` X-ray cavity views and `74`
  side components after excluding `G-HI/50` and failing closed on non-bipolar
  X-ray topologies.
- Seven age treatments are now available: true, sound crossing, buoyant rise,
  refill, bilateral supersonic shock, mean-pressure spectral, and
  emissivity-weighted spectral age. Spectral breaks above 15 GHz remain age
  upper limits and inferred-power lower limits.
- Sound speed and gravity are evaluated in the initial static atmosphere.
  The group reconstruction agrees with its independent tabulated environment
  to maximum relative differences of `1.04e-4` in sound speed and `1.78e-3`
  in gravity.
- `t_buoy/t_cs` spans `1.20--2.36` with median `1.57`; do not replace the
  calculation with a fixed factor of two.
- With true age, median `2.5pV` power recovery is `0.0081`, `0.628`, `0.00437`,
  and `0.0731` for `C-HI`, `C-LO`, `G-HI`, and `G-LO`. The high-power deficit
  is therefore dominated by X-ray cavity-energy recovery, not only age bias.
- Science note/assets:
  `docs/science/four_case_cavity_age_method_comparison_2026-08-28.md` and
  `docs/science/assets/four_case_cavity_age_method_comparison_2026-08-28/`.

### 2026-08-28 boundary and spectral-field correction

- Status: `complete_method_correction_integrated_into_goal065`.
- Decision: `DROP_G_HI_50_FROM_ALL_SCIENCE`.
- The annual axial audit finds boundary contamination only in `G-HI`, first at
  snapshot 48 and persisting through 50. At 50 Myr its lobe/shock is only
  `1.052 kpc` from the X3 face and edge pressure is up to `315.31` times the
  initial atmosphere. `C-HI`, `C-LO`, and `G-LO` retain their 50 Myr points.
- Recalculated break frequencies are independent of magnetic-field choice.
  Spectral ages are now reported with a global fractional-tracer mean-pressure
  field as primary and the existing 1.4 GHz emissivity-weighted field as a
  sensitivity. `G-HI` science ages are `10/20/30/40 Myr` only.
- Goal 065 now filters `G-HI/50` from every downstream cavity, radio,
  spectral-age, and inferred-power product and has rebuilt all case medians
  and row counts. Existing raw/compact endpoint files remain archival evidence.
- Science note/assets:
  `docs/science/four_case_boundary_spectral_field_review_2026-08-28.md` and
  `docs/science/assets/four_case_boundary_spectral_field_review_2026-08-28/`.

### Goal 065: four-case scientific synthesis

- Status: `complete_corrected_local_scientific_synthesis`.
- Decision: `FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT`.
- The joined surface covers `C-HI`, `C-LO`, and `G-LO` at
  `10/20/30/40/50 Myr`, and `G-HI` at `10/20/30/40 Myr`, using accepted
  compact products only. `G-HI/50` is absent from every scientific output.
- The topology, pressure, background, censoring, and shock-validity gates
  remain fail-closed. There are `37` quantitative cavity views and `74` side
  components.
- Test 1: pooled within-view cavity-bias/Mach Spearman rho spans `-0.888` to
  `-0.868`, but the case/view-adjusted slope is only `-0.0402 dex/Mach`, Mach
  adds `0.0031` R-squared, and leave-one-case-out slopes change sign. This is
  a strong pooled pattern, not a case-robust independent Mach effect.
- Test 2: true-age median `2.5pV` power recovery is `0.00810`, `0.628`,
  `0.00437`, and `0.0731`. Mean-pressure spectral recovery is `0.0124` and
  `1.05` for the cluster cases, with median lower bounds `>0.00321` and
  `>0.0871` for the group cases. Age choice modulates but does not explain the
  high-power cavity-energy deficit.
- Test 3: corrected median full-loss 150 MHz power recovery is `0.937`, `7.34`,
  `0.520`, and `4.03`; the corresponding 1.4 GHz values are `5.10`, `15.85`,
  `2.36`, and `7.02`.
- Goals 066 and 067 now provide the selected-age dual-space and native-shock
  evidence needed for local synthesis and manuscript integration.
- Science note/assets:
  `docs/science/four_case_scientific_synthesis_2026-08-26.md` and
  `docs/science/assets/four_case_scientific_synthesis_2026-08-26/`.
- Goal/log: `docs/goals/065-four-case-scientific-synthesis/` and
  `docs/exchange/logs/2026-08-26-four-case-scientific-synthesis.md`.

### Goal 064: four-case selected-age observables

- Status: `complete_product`.
- Decision:
  `FOUR_CASE_SELECTED_AGE_OBSERVABLE_SURFACE_COMPLETE_SYNTHESIS_READY`.
- Produced ages: snapshots `10/20/30/40/50` for all four cases, retaining
  actual HDF5 times. The `G-HI/50` products are now archival only and must be
  excluded from all science; the other three cases retain all five ages.
- X-ray/cavity surface: `0/45/90 deg`, X-ray-only one-percent projected-area
  deficit mask, tracer post-hoc only, and quantitative cavity energy only for
  exactly two non-crossing opposite-side components.
- Radio surface: corrected PRAiSE2 lossless/full-loss luminosity at
  `0.15/0.5/1.4/4.5/15 GHz` and `0/45/90 deg`, with complete case-specific
  histories and causal particle-state matching.
- Superseding validity gate: `G-HI/50` is excluded from every observable and
  inference. Its annual boundary contamination begins at snapshot `48`; shock
  positions still stop at `47` and centred speed/Mach at `46`.
- Execution is one four-core X-ray job plus four independent 16-core radio
  jobs. This is the complete prespecified surface, split only at genuine
  restart/failure boundaries.
- The first five jobs (`787293`-`787297`) failed during launch because their
  transient analysis roots targeted the full scratch allocation. Radio logs
  directly report `Errno 122`; the X-ray common cause is inferred from its
  simultaneous launch failure and empty case outputs. No science calculation
  started. Failure evidence is preserved; no raw input was changed.
- The repair moved transient analysis/history-cache products to the enlarged
  home allocation only. Scientific defaults and the prespecified surface are
  unchanged, and regression tests now enforce the storage placement.
- The next authorized evidence found all four radio replacements (`787302`-
  `787305`) failed after completing their full history caches: the staged
  runtime omitted `plutokore.radio.praise` and `raytracing`. The complete
  caches were retained and validated; this is an execution packaging defect,
  not a particle-history or scientific-method failure.
- A separate repair stage now contains the complete reviewed radio dependency
  surface and fails fast on its imports before cache work. Resume jobs `787310`
  (`C-HI`), `787329` (`C-LO`), `787311` (`G-HI`), and `787312` (`G-LO`) were
  verified running once.
- X-ray `787301` subsequently finished with `Exit_status=1` after using
  `126641000kb` of its `128gb` request. C-HI, C-LO, and G-LO completed; only
  G-HI exited `137` after manifest preflight. This is an aggregate-memory
  concurrency failure, and the three completed products remain reusable.
- The wrapper now supports an isolated case without changing its four-case
  default. G-HI-only repair `787415` was staged separately and verified
  running once with one CPU and the full `128gb` node memory.
- C-HI radio `787310` and G-HI radio `787311` then completed with
  `Exit_status=0`. Their compact products were retrieved and passed the full
  row-count, finite-value, causal-source, corrected-PRAiSE2 provenance, and
  empty-stderr contract. Each contributes `50` primary and `150` view rows.
- G-LO radio `787312` and G-HI X-ray repair `787415` then completed with
  `Exit_status=0` and empty stderr. G-LO passed the same corrected-PRAiSE2,
  row-count, finite-value, and causal-source contract as C-HI and G-HI.
- The G-HI repair passed all `15` case-age-view projection checks. Its compact
  output was combined without recomputation with the successful C-HI, C-LO,
  and G-LO products retained from `787301`. The resulting four-case X-ray
  package covers `60` case-age views, has SHA-256
  `359b9e2fd4d6b87309177adefcab86b34c22a9645fb1c1da8f1deb192a343d3e`,
  and preserves nonquantitative zero-energy rows where no significant cavity
  component was recovered.
- C-LO radio `787329` completed with `Exit_status=0` in `05:40:55`, empty
  stderr, and the same corrected-PRAiSE2 contract. The full radio surface now
  contains `200` primary rows and `600` viewing rows across all four cases.
- Goal 064 remains a complete provenance product. Downstream analysis must
  apply the 2026-08-28 `G-HI/50` exclusion; no production recomputation is
  required.
- Science note/assets:
  `docs/science/four_case_selected_age_observables_2026-08-26.md` and
  `docs/science/assets/four_case_selected_age_observables_2026-08-26/`.
- Goal/log: `docs/goals/064-four-case-selected-age-observables/` and
  `docs/exchange/logs/2026-08-26-four-case-selected-age-observables.md`.

### Goal 063: cluster background and age validity

- Status: `complete_product`.
- Decision:
  `C_LO_LARGE_NORMALIZED_BUDGET_BACKGROUND_DOMINATED_SHOCK_WINDOWS_LOCKED`.
- Scope: use existing `C-HI` and `C-LO` HDF5 outputs at eight anchor ages to
  separate full-fluid energy changes into five radial shells, with `r >= 100
  kpc` as the early far-field control.
- Shell sums must reconstruct Goal 062 at every non-baseline age; raw HDF5
  inputs remain read-only and no PLUTO production is involved.
- Existing Goal 062 evidence locks `G-HI` front-position validity through
  snapshot `47` and centred three-snapshot shock kinematics through snapshot
  `46`. Other cases remain domain-valid through snapshot `50`.
- The paired cluster design can diagnose a common far-field term but is not an
  unforced no-jet control; causal interpretation will remain qualified.
- Remote preflight passed for both canonical chains, all selected HDF5
  contracts, both Goal 062 references, staged hashes, wrapper syntax, and
  no-overwrite targets.
- PBS `787276.kunanyi-ohpc` / `cl_bgdiag` completed with `Exit_status=0` in
  `00:30:57`. Both cases, `16` snapshots, and `80` shell rows validated;
  stderr is empty. The directly retrieved `11`-member archive SHA-256 is
  `5633df0a8be47b3142336c39ab2bb2dad8a7220ac1176a567430b828494d7a15`.
- Through `20 Myr`, absolute far-field `C-HI` and `C-LO` energy terms agree
  within `0.024%`, confirming a common atmosphere-evolution term.
- At the `C-LO` endpoint, `94.61%` of the accounted change lies beyond
  `100 kpc`, with zero tracer and no shock arrival. The uncorrected
  `23.9673`-times-injected whole-domain value is background dominated.
- The inside-`100 kpc` remainder is `1.2908` times injected energy and is an
  upper bound, not a background-corrected coupling efficiency.
- Next: lock common paper-analysis ages and run selected-age four-case
  X-ray/cavity plus corrected-PRAiSE2 products, capping `G-HI` shock-kinematic
  use at snapshot `46`.
- Science note/assets:
  `docs/science/cluster_background_and_age_validity_2026-08-26.md` and
  `docs/science/assets/cluster_background_and_age_validity_2026-08-26/`.
- Goal/log: `docs/goals/063-cluster-background-and-age-validity/` and
  `docs/exchange/logs/2026-08-26-cluster-background-and-age-validity.md`.

### Goal 062: four-case fluid snapshot census

- Status: `complete_product`.
- Decision:
  `FOUR_CASE_FLUID_CENSUS_GREEN_C_LO_ENERGY_BASELINE_AND_G_HI_BOUNDARY_GATES_EXPOSED`.
- Scope: apply the accepted energy, centre-zero gravity, tracer-partition, and
  axial-shock methods to float outputs `0..50` for all four cases. Radio and
  projected X-ray cavity work remain deliberately separate.
- PBS `786969.kunanyi-ohpc` / `four_fluid` completed with `Exit_status=0` in
  `04:18:49`. All four case processes exited `0`; the wrapper validated `51`
  snapshots, `612` energy rows, `306` shock rows, and `51` source rows per
  case. Remote stderr is empty.
- `Stageout_status=1` remains a scheduler caveat, but the stage archive and
  logs were directly retrieved. The `646`-member archive SHA-256 is
  `b4dfb65a9231a53caec776f435ab819ce0b67c61fa9fd7f4aa866a5d7d83ece6`.
- The first descriptive synthesis contains `204` primary energy rows, `408`
  primary shock-side rows, endpoint summaries, factorial contrasts, and one
  figure. It makes no replicate-based inferential claim.
- Material gate 1: `C-LO` ambient total change reaches `23.91` times injected
  energy with residual `-22.97`; its low-power energy comparison requires a
  background/common-atmosphere diagnosis before promotion.
- Material gate 2: the late `G-HI` front reaches `248.95 kpc` in a roughly
  `250 kpc` half-domain; endpoint shock kinematics are boundary-limited.
- No raw HDF5 or particle payload was copied or changed. The next tranche is a
  targeted existing-output background and valid-age diagnostic before broad
  radio/X-ray processing.
- Science note/assets:
  `docs/science/four_case_fluid_snapshot_census_2026-08-25.md` and
  `docs/science/assets/four_case_fluid_snapshot_census_2026-08-25/`.
- Goal/log: `docs/goals/062-four-case-fluid-snapshot-census/` and
  `docs/exchange/logs/2026-08-25-four-case-fluid-snapshot-census.md`.

### Goal 061: G-LO matched full-history production

- Status: `complete_matched_full_history_endpoint_green`.
- Decision:
  `G_LO_MATCHED_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_MATCHED_RAW_FACTORIAL_COMPLETE`.
- Rationale: historical `G-LO` retains particles `0..5000` but only six fluid
  ages at `0/10/20/30/40/50 Myr`; the other three treatments retain the
  matched `51` float, `11` double, and `5001` particle surfaces.
- Contract: fresh group `002_031`, one-sided jet power `1e43 erg s^-1`, speed
  `0.1c`, exact `50 Myr` target, float/double HDF5 every `1/5 Myr`, and
  particle histories every `0.01 Myr`.
- Storage gate: home use was `2,394,234,566,848` bytes against the `20 TiB`
  quota; more than the required `4 TiB` headroom remained. A disposable
  `16 MiB` write-and-fsync probe passed and was removed.
- PBS `786516.kunanyi-ohpc` / `g_lo_hist2` completed with `Exit_status=0`,
  `30:01:35` walltime, and `1792` CPUs. `Stageout_status=1` remains a
  scheduler caveat, but all required evidence was directly retrievable.
- The run has `DONE`, no `FAILED`, `RUN_KIND=fresh`, `MPI_EXIT_CODE=0`, and
  only the known nonfatal 93-byte missing-`git` warning in stderr.
- Continuous non-empty sequences passed: float HDF5 `0..50`, double HDF5
  `0..10`, and particles `0..5000`.
- Both fluid endpoints have exact code time `15330.0696894`, all six required
  fields, and shape `1014 x 960 x 960`. Particle endpoint `5000` contains
  `197,568` unique valid records at the same step and time.
- Run root:
  `/u/bwbrook/xray_cavities_runs/2026-08-23-g-lo-matched-full-history-production`.
  This home-resident run is now canonical for matched analysis. Historical
  compacted G-LO roots remain untouched as provenance.
- No post-processing, compaction, deletion, or follow-on submission occurred
  during completion review. Approximately `124 KiB` of remote evidence was
  retrieved; the complete compact local bundle is approximately `160 KiB`.
- Science note/assets:
  `docs/science/g_lo_matched_full_history_production_2026-08-23.md` and
  `docs/science/assets/g_lo_matched_full_history_production_2026-08-23/`.
- Goal/log: `docs/goals/061-g-lo-matched-full-history-production/` and
  `docs/exchange/logs/2026-08-23-g-lo-matched-full-history-production.md`.

### Goal 060: G-HI full-history production

- Status: `complete_full_history_endpoint_split_root_canonical_sequence_green`.
- Historical decision:
  `G_HI_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_RAW_FACTORIAL_COMPLETE`.
  Goal 061 supersedes only the claim that raw temporal cadence was fully
  matched; the G-HI endpoint and canonical split-root evidence remain green.
- PBS `786189.kunanyi-ohpc` / `g_hi_hist` ended `F` with `Exit_status=124`
  after `11:06:32`; stage stdout records the distinct
  `no_progress_watchdog_timeout` failure.
- Contract: fresh group `002_031`, one-sided jet power `1e45 erg s^-1`, speed
  `0.1c`, exact `50 Myr` target, float/double HDF5 every `1/5 Myr`, and
  particle histories every `0.01 Myr` (`0..5000` inclusive).
- The run completed float surfaces `0..14` and particle histories `0..1499`,
  then left an uncatalogued partial `data.0003.dbl.h5` during the `15 Myr`
  write. The partial root occupies approximately `863 GiB` and is preserved.
- The validated safe restart is double HDF5 index `2` plus particle index
  `1000` at `10 Myr`, step `10011`; HDF5 structure/time/datasets and all
  `39,764` particle records passed.
- A post-failure scratch probe failed at about `8.0 TiB`, matching the unchanged
  scratch quota. Home is the enlarged `20 TiB` destination and passed a
  disposable `16 MiB` write-and-fsync probe.
- Recovery PBS `786326.kunanyi-ohpc` / `g_hi_hist_r1` completed with
  `Exit_status=0` in `28:08:03`. The target has `DONE`, no `FAILED`, empty
  stderr, and occupies approximately `2.2 TiB` under the home run root.
- Endpoint HDF5 and particle evidence both match code time `15330.0696894`.
  The HDF5 fields have shape `1014 x 960 x 960`; particle index `5000` has
  `193,741` records.
- Canonical split-root selection is green: double HDF5 scratch `0..2` then
  home `3..10`; float HDF5 scratch `0..10` then home `11..50`; particles
  scratch `0..1000` then home `1001..5000`. Preserve both roots until the
  selected scratch segment is reduced or moved.
- Science note/assets:
  `docs/science/g_hi_full_history_production_2026-08-20.md` and
  `docs/science/assets/g_hi_full_history_production_2026-08-20/`.
- Goal/log: `docs/goals/060-g-hi-full-history-production/` and
  `docs/exchange/logs/2026-08-20-g-hi-full-history-production.md`.

### Goal 059: cluster full-history production

- Status: `complete_matched_cluster_full_history_production`.
- Decision: `MATCHED_CLUSTER_FULL_HISTORY_PAIR_GREEN_G_HI_READY`.
- Historical storage note: these two raw cases were written to the 8 TiB
  scratch filesystem. The later quota increase applies to 20 TiB home storage,
  not to scratch.
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
