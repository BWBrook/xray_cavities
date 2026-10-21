# X-ray Cavities successor handoff

Last reviewed: 2026-10-21 (repository and supervisor direction; remote state
was last reported on 2026-09-06).

Verified shared base before this tranche: `aec8117` on `main` and `origin/main`

Operating state: `Q-029 native accounting accepted; Q-032 X-ray recovery review/action open; Q-031 spherical energy and stability audit requested; Q-030 revision pending`

Stas requests Patrick-agent check/action Q-032, with Barry-codex notified:
the selected-age X-ray path uses the 1%-area seed mask directly as geometry,
unlike Goal 045's seed-and-growth method. Verify the staged source, fixed
120-kpc aperture and background; coordinate a validated correction and
before/after overlays and volume comparisons. Affected observer/enthalpy/
power manuscript conclusions are provisional, not established intrinsic
observational biases. Native tracer accounting remains intact. Details:
`docs/science/xray_cavity_selection_issue_2026-10-21.md`. No science code
or threshold was changed and no new simulation was authorized here.

Latest approved Q-031 direction: make the primary jet-energy comparison
inside two spheres defined by the furthest cells with total speed >=100 and
>=300 km/s. Include every enclosed cell, using the same current aperture at
both t and t=0 and fixed initial gravity, then split with `tr1 > 1e-3`.
Validate disturbance/cocoon coverage and consider energy transport across
the spheres; report both radii and budgets, not a closure-tuned aperture.
Spurious speeds below 5% of local sound speed are provisionally acceptable.
Stas regards C-LO/G-LO as acceptable on that basis, pending local 3D speed
and sound-speed checks; this is not an energy-drift validation. The no-jet
audit remains requested. Read the latest approved refinement in
`docs/science/nojet_stability_audit_request_2026-10-21.md`.

The following earlier whole-grid comparison remains diagnostic evidence;
its primary-aperture instruction is superseded above. It audits full-grid
thermal/kinetic/gravitational `E(t)-E(0)` against injection, then the
complementary binary tracer split.
Neither calculation depends on shock detection. Retain late C-LO, where Stas
expects sound waves; no explicit viscosity means smooth-wave damping is
numerical. Clarify that numerical partition agreement is not physical closure.
Read `docs/science/whole_grid_energy_closure_and_partition_2026-10-21.md` and
the latest message in the snapshot-science thread. Q-031 is open to Barry;
reuse existing native ledgers and update the next Q-030 manuscript iteration.
A compact-table comparison of the 19 accepted ages now accompanies the
direction: grid changes exceed nominal injection by 14--28% (C-HI), about
8% (G-HI), 23--58% (G-LO), and a factor of 6--24 (C-LO). Absolute sums,
cell-wise differences and partitions agree numerically. See the new note and
its figures; physical discrepancy diagnosis remains open. No raw HDF5 reread
or remote job check was made.

The latest Q-031 follow-up now requests an energy and maximum-velocity audit
of the existing 50 Myr no-jet controls, followed by full-3D outer motions and
10/30/80/100-kpc gravity integrals for C-LO/G-LO. See
`docs/science/nojet_stability_audit_request_2026-10-21.md`. Saved profiles show
inward boundary-tube means of 45.35/14.09 km/s; C-LO central-100 gravity is
only 7.8626% of injection, with 99.314% of the net gravity increase outside
100 kpc. This localizes the excess, not its cause. No no-jet integrated-energy
result was found and no new remote job has run. Stas's working jet-closure
tolerance is 10--20%; larger low-power differences need investigation.

Stas also explicitly requires atmospheric stability in unreached regions of
the jet simulations themselves. Check density, pressure, velocity and energy
changes there, distinguishing jet/cocoon extent from shock and sound-wave
arrival. No tracer does not necessarily mean no jet-driven disturbance.
Investigate unexplained outer drift; do not count it as jet coupling or hide
it by changing the raw energy budget. This is part of Q-031, not a new run.

PBS `790871.kunanyi-ohpc` completed `F/0` in 02:40:26. Its compact output has
been retrieved and revalidated locally: 228 native rows, 19 precision rows,
171 shock rows and 15/19 quantitative primary shock ages. Threshold precision
is negligible. The C-LO median X-ray/native enthalpy ratio is now 0.494,
replacing fractional-mask over-recovery; the main geometry-driven conclusion
survives. Read `docs/science/q029_binary_native_refresh_2026-09-06.md` for the
accepted accounting, limits and products. No remote job is awaiting a check.
The source changes and manuscript iteration are included in the published
Q-029/Q-030 tranche, following Barry's 2026-09-06 commit/push instruction.
Review the tracked PDF
`docs/science/assets/q029_binary_native_refresh_2026-09-06/xray_cavities_q030_first_iteration.pdf`
and the three figures
in `manuscript/figures/`. The power tables now use accepted X-ray pressures;
old Goal 065 power summaries are not the current manuscript evidence.

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
   this note. Q-029 is analytically accepted and the first Q-030 iteration
   is ready; Q-029 is answered and Q-030 is in review in the request registry.

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

## Accepted analysis tranche: Q-029

The strict binary native cocoon definition and combined native/shock refresh
pass numerical acceptance. The requirements below record the completed scope;
use the September 6 accepted products for the manuscript iteration.

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
