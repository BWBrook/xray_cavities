# X-ray Cavities successor handoff

Last verified: 2026-09-05  
Verified shared base before this note: `8d8740c` on `main` and `origin/main`  
Operating state: `supervisor direction received; native energetics refresh next`

This is the cold-start note for a new project agent. It records the current
scientific position and the shortest route forward. It is deliberately not a
history of all numbered goals. Use Git and the dated notes for provenance;
do not replay old goal logs as active instructions.

## Bootstrap in ten minutes

1. Run `git status --short --branch`, `git fetch --prune origin`, and, if the
   worktree is clean, `git pull --ff-only`.
2. Read `AGENTS.md`, this file, and the top of
   `docs/exchange/current_status.md`.
3. Read the two live supervisor requests:
   - `agent_comms/threads/2026-08-12-snapshot-science-analysis-contract.md`
     from the 2026-09-04 binary-mask correction onward;
   - `agent_comms/threads/2026-09-05-paper-plan-review.md`.
4. Read only these recent science notes before opening older material:
   - `docs/science/four_case_scientific_synthesis_2026-08-26.md`;
   - `docs/science/four_case_selected_age_dual_space_energetics_2026-08-31.md`;
   - `docs/science/four_case_selected_age_native_shock_partition_2026-08-31.md`.
5. Inspect `agent_comms/requests/open_questions.md` for feedback newer than
   this note. At this snapshot, `Q-029` and `Q-030` are open.

Do not read every historical goal or exchange log to orient yourself. Consult
one only when a current claim or implementation path points to it.

## Project in one paragraph

The project asks how well synthetic X-ray cavities recover the energetics and
power of simulated AGN jets. The experiment is a deterministic four-case
factorial: cluster (`C`) versus group (`G`) atmosphere crossed with high (`HI`)
versus low (`LO`) jet power. Matched 50 Myr histories exist for `C-HI`, `C-LO`,
`G-HI`, and `G-LO`, with the intended `51/11/5001` float/double/particle
temporal surfaces. The analysis separates native simulation truth from
observer-like X-ray and radio inference. This repository owns the analysis,
compact evidence, and PASA manuscript; it is not the PLUTO source tree and
must not absorb the multi-terabyte raw simulations.

## Current scientific contract

- Known bipolar jet powers are `2e45 erg/s` for the high-power cases and
  `2e43 erg/s` for the low-power cases.
- The accepted science ages are 10, 20, 30, 40, and 50 Myr, except `G-HI/50`,
  which is excluded because the source contacts the simulation boundary.
- Preferred viewing angles are `0/45/90 deg`. Nonzero views use
  `edge_overlap_uniform_cell_projection`.
- Native and observer routes are independent. Tracer may evaluate X-ray
  recovery after the fact but must not define or repair an observed cavity.
- `2.5pV` is the primary non-relativistic cavity-enthalpy convention; `4pV`
  is the literature comparator. Enthalpy is not added to the thermal,
  kinetic, and gravitational energy ledger because that would double count
  displacement work.
- Corrected PRAiSE2 is the accepted production radio method. Spectral limits
  remain censored, not converted into ordinary point estimates.
- No further PLUTO production run is indicated by current evidence.

## What the completed analyses showed

These are observations from Goals 065-067 followed by the current inference.
Numbers involving the native cocoon or shocked-ambient partition are
provisional until `Q-029` is complete.

### Four-case synthesis, Goal 065

**Observed:** cavity-energy recovery and shock Mach show a strong pooled
negative association, but the effect becomes small after case and view are
controlled and changes sign in leave-one-case-out checks. Changing the cavity
age estimator moves inferred power by factors of a few but does not explain
the severe high-power deficit. Empirical radio-power recovery varies
materially with environment, jet power, and frequency.

**Inference:** the pooled Mach trend is descriptive rather than an identified
independent effect; clock choice modulates rather than explains the cavity
energy deficit; radio scalings are not a common unbiased estimator across this
four-case surface.

### Native versus X-ray lobe energetics, Goal 066

**Observed:** 37 of 57 selected case-age-view products pass the X-ray topology
gate. Among usable views, inferred pressure is within a factor of two of the
then-primary native pressure for 36/37 rows, whereas inferred volume and lobe
enthalpy are within a factor of two for only 5/37. The observer calculation is
X-ray-only and its repaired deprojection has maximum residual about
`1.651e-4`.

**Inference:** cavity geometry and topology, rather than ambient-pressure
recovery, dominate observer-side lobe-enthalpy bias on the selected-age
surface. This qualitative result is likely durable, but all ratios whose
denominator used fractional tracer weighting must be recalculated under
`Q-029` before publication.

### Native shocked-ambient energy, Goal 067

**Observed:** the prespecified selected-age shock mask produced 171 rows and
15 quantitative primary bipolar case-age rows. In the three well-resolved
series, net shock-region energy was roughly `0.58-0.87` of injected energy and
irreversible heating roughly `0.17-0.33`. Late `C-LO` rows failed closed rather
than being imputed. Where both routes were quantitative, X-ray cavity
enthalpy was a small fraction of the native shocked-region energy.

**Inference:** cavity enthalpy alone misses much of the energetic disturbance,
while Goal 066 separately shows that geometry/topology dominates recovery of
the lobe itself. The old shock numbers are now a sensitivity surface because
their ambient mask allowed `tr1 <= 1e-2`; `Q-029` requires the exact
complementary `tr1 <= 1e-3` mask.

## Active next tranche: Q-029

Stas has changed the primary native cocoon definition. This is the next
scientific task and must precede updated quantitative manuscript claims.

1. Define a cocoon cell by strict `tr1 > 1e-3` and count its full cell volume,
   pressure, mass, thermal, kinetic, and gravitational terms.
2. Define ambient material by the exact complement, `tr1 <= 1e-3`.
3. Keep fractional tracer weighting and binary `5e-3`/`1e-2` masks as
   sensitivities, not as the primary result.
4. First report the existing Goal 062 `binary_threshold_1e-3` 10 Myr bipolar
   volume and `2.5pV` for all four cases. Check whether exact equality at
   `1e-3` makes the current implemented `>=` materially different from the
   required strict `>`.
5. Refresh the selected-age native/X-ray join using the binary primary. Report
   changes in volume, pressure, `2.5pV`, native energy components, and recovery
   ratios. Leave the X-ray-only measurement path unchanged.
6. Tighten the native shocked-ambient mask to `tr1 <= 1e-3`, recompute the
   selected-age shock comparison, and keep the old Goal 067 surface only as
   superseded sensitivity evidence.
7. Verify that the complementary masks preserve total retained energy and
   closure to numerical tolerance.

This is post-processing of retained outputs, not a PLUTO rerun. Use the
smallest remote computation that produces the revised native tables and
shock results. Do not expand to annual X-ray cadence unless the refreshed
result changes the scientific decision or reveals meaningful time structure.

Likely implementation touchpoints are:

- `scripts/science/snapshot_energy.py` and
  `scripts/science/build_snapshot_science.py` for the current fractional
  primary and `>=` binary partitions;
- `scripts/science/build_selected_age_dual_space_energetics.py` for the
  fractional-native join;
- `scripts/science/build_selected_age_native_shock.py` for the current ambient
  ceiling;
- the matching focused tests and Kunanyi wrappers under `tests/` and
  `scripts/kunanyi/`.

Do not edit code merely because it mentions an older tracer threshold. Trace
the active Q-029 data path and change only what feeds the revised products.

## Manuscript route: Q-030

The target journal is PASA. Stas has approved the overall plan and prefers the
working title **How well do X-ray cavities measure jet energetics?** Results
must proceed in this order:

1. Test the physical proxy with native quantities: native `2.5pV` and `4pV`
   versus injected energy and actual cocoon/ambient thermal, kinetic, and
   gravitational changes, including shocks.
2. Hold true age fixed and test observer recovery of X-ray cavity volume,
   pressure, geometry/topology, and enthalpy.
3. Then introduce sound-crossing, buoyant-rise, refill, shock, and spectral
   ages and quantify the additional bias in inferred power.

Use the factorization

```text
Q_cav / Q_true
  = (H_native / E_inj)
  * (H_X / H_native)
  * (t_true / t_est)
```

with a consistent bipolar region and enthalpy convention. The factors separate
physical-proxy, measurement, and clock bias, but are not assumed statistically
independent.

After `Q-029`, update the Results prose and figure sequence in
`manuscript/text/main.md` and `manuscript/text/figures.md`. If the recalculation
does not materially alter the conclusions, proceed directly to the first
coherent manuscript iteration rather than opening another analysis ladder.

## Residual limits that must remain visible

- `G-HI/50` is excluded, not repaired.
- Twenty of 57 selected X-ray views are topology-censored.
- Late `C-LO` shocked-ambient estimates currently fail the bilateral gate.
- The `C-LO` whole-domain ambient budget is background dominated; no
  native-resolution no-jet cellwise subtraction exists.
- Boundary flux and radial advection are absent, so there is no closed
  whole-domain conservation proof.
- The native shock mask is a truth diagnostic, not an observable X-ray shock
  model.
- The four simulations are factorial cells, not population replicates. Do not
  claim population-level p-values or independence across ages and views.
- Current products support an internal paper argument, not final publication
  claims before the supervisor review cycle.

## Data and code map

- Canonical compact science evidence is under `docs/science/assets/` beside
  its dated note. Prefer summary tables and figures over raw transport copies.
- Multi-terabyte HDF5 and particle histories remain on Kunanyi under the
  documented `/u/bwbrook` production roots. Use committed manifests and
  checksums to locate them; do not copy them into Git.
- Data lifecycle policy:
  `docs/science/xray_cavities_data_lifecycle_strategy_2026-07-10.md`.
- Manuscript sources: `manuscript/`; bibliography: `references/`; build
  configuration: `settings/build.yaml`.
- External manuscript engine: `/Users/bwbrook/work/makedoc`.
- Simulation/tool source checkouts are separate:
  `/Users/bwbrook/git/utas-agn/{pluto,jet-setup,plutokore}` on this Mac and
  `/home/bwbrook/git/utas-agn/...` on Linux. Their `origin` remotes are Barry's
  forks. Do not push to canonical upstream repositories without explicit
  authorization.

## How to work on this project

Use the `twilight-laboratory` skill for the scientific programme. Treat
`Q-029` plus the first manuscript iteration as one coherent reporting horizon:
prespecify consequential checks, distinguish observation from inference, make
routine reversible decisions autonomously, and return when the refreshed
result and manuscript argument are reviewable or when a material scientific
choice genuinely needs Barry, Stas, or Patrick.

Use the `kill-your-darlings` skill whenever adding or revising machinery. This
repo has already undergone extensive simplification. Keep one active path per
result, reuse existing components, delete obsolete compatibility paths when
safe, and avoid ceremonial goal logs, duplicate ledgers, transport archives,
or tests that do not protect a distinct scientific failure mode. Git preserves
history; production code should not.

The standing collaboration rule is: **rigour at the scientific decision
boundary; proportional engineering everywhere else.** Complete the smallest
coherent analysis that can change the decision, perform one focused review and
repair pass, state residual uncertainty, and stop. "Could be more polished" is
not a reason to continue.

## Execution and verification

- Use the repo-pinned `uv` environment for Python.
- Run focused tests for changed behavior. The last full repository gate at
  commit `4bdda2c` was `751 passed, 1 skipped`; do not repeat it unless a broad
  change or release boundary warrants it.
- Build the manuscript through the repo targets:

  ```bash
  make manuscript-validate
  make manuscript-draft
  make manuscript-submission
  make manuscript-check
  ```

- Authorship injection remains disabled until author list and order are
  agreed. Start from `manuscript/authors.template.yaml` only after that
  decision.
- For Kunanyi work, consult the Nectar control-plane guidance, use the
  repo-local helper scripts, and use Chrome/Open OnDemand only to refresh the
  TPAC jumpbox selector when needed. Stop after a PBS job is verified queued or
  running and wait for Barry's completion email unless he explicitly requests
  a re-check.
- Remote jobs must be no-overwrite and provenance preserving. Keep raw data
  remote and retrieve compact products, manifests, checksums, and logs.
- Commit and push only when Barry has authorized publication of the tranche or
  explicitly asks for it.

## Stop conditions

Return to Barry before proceeding only if the refreshed binary-mask result
materially changes the paper's central interpretation, requires a new
scientific convention, calls for substantial new production compute, exposes
data-integrity loss, or creates a publication/ownership decision. Otherwise,
carry the approved method through Q-029 and into the first Q-030 manuscript
iteration without approval ping-pong.

