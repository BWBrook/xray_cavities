# Compressive front comparison and background emission tests

Date: 2026-11-17.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`) and Patrick's agent (`patrick-agent`).
Status: supervisor-approved existing-output analysis request; Patrick to
review the method. No new simulation is authorised by this handover.
Source repository revision: `f08a913ddfd8e91b30e97af55e51e166337dd44f`.

## Supervisor decision

Proceed with the check, **starting with a compressive-front comparison**.
A confirmed bow-shock classification is not required for the first result.
Barry's agent should carry out the analysis; Patrick's agent should review
the front-finding, projection and interpretation method.

The surrounding-emission replacement/background-refit experiment is a useful
result: background emission can make cavity identification difficult. Repeat
the test on different snapshots and simulations, not just G-HI at 20 Myr.
Its usefulness as a physical diagnostic does not establish a deployable
observer-only detector or accurate three-dimensional volume recovery.

## First task: compressive front versus X-ray arcs

1. Start with the existing G-HI snapshot at actual age 19.999614 Myr and
   side-on azimuths 0, 45 and 90 degrees. These are rotations around the jet
   axis, not changes in jet inclination. Reuse verified native inputs and
   X-ray products; inspect existing jobs before submitting another analysis.
2. Define the front independently from the native pressure/density structure
   and converging flow, with derivatives and sampling appropriate to the
   stretched grid. Find the lateral surface as well as the axial advance.
   Do not tune the front against the orange contour, define it from the
   tracer boundary, or use speed alone. Distinguish unrelated boundary
   disturbances and ambiguous/disconnected fronts rather than forcing an
   enclosing bow surface.
3. Revise the scientific contract and implementation for a **compressive
   front**, with explicit thresholds and resolution sensitivity, and have
   Patrick review it before accepting native comparisons. Revalidate on
   shocks, smooth acoustic compressions, contacts, rarefactions and static
   stratification at different orientations on the actual stretched axes.
   An acoustic compression may be a valid front under the new contract; it
   must not be called a shock. Keep the original shock-finder FAIL visible.
   Renaming its output without revising/testing the criteria is insufficient.
4. Project the independently found front into the exact coordinates and
   pixel grid of the retained X-ray maps. Overlay it with the full projected
   `tr1 > 1e-3` lobe boundary, orange 5%-deficit and blue seed/grow outlines.
   Show raw brightness and fractional deficit with comparable scales and
   the 120-kpc search aperture. Include profiles through a lateral arc and
   through a lobe. Measure signed contour separations in kpc and local-cell
   scales, identifying coincident, inner-edge, outer-edge or unrelated arcs.
5. Use a reviewed front/shell definition to measure the surrounding ambient
   emission along missed-lobe sightlines and along the orange arcs. Separate
   lobe, front-associated ambient and remaining atmospheric contributions;
   verify that they sum to the total. A geometric alignment is not evidence
   that the shell causes filling-in. Low-speed gas is not automatically
   undisturbed, and a compression need not imply irreversible shock heating.
6. For the front-associated ambient cells, repeat the controlled replacement
   with their initial emissivity in the **same cells**. Keep the current
   cell mask fixed and retain signed changes. Compare the original fitted
   background with a separately refitted background. Do not simply delete
   shell emission. Keep this front-based extension distinct from the frozen
   velocity-partition replacement experiment below.

The first deliverable is the compressive-front overlay and quantitative arc
comparison, with Patrick's method review and limitations. Do not delay it
until a definitive shock/acoustic classification is available. Tracking the
front between adjacent snapshots, measuring its speed relative to upstream
gas and checking jump conditions can follow if that distinction is useful.
This front analysis is not a selection rule or prerequisite for energy budgets.

## Repeat the background emission diagnostic

Use the existing [frozen prospective protocol](../../science/background_refit_blind_protocol_2026-11-11.md)
and prepared cohort adapter rather than creating a competing batch or tuning
the rule after inspecting recovery:

- C-HI, C-LO and G-LO: indices 10, 20, 30, 40 and 50.
- G-HI: indices 10, 30 and 40 as held-out tests; 20 remains the development
  example and 48--50 remain excluded from science.
- All three side-on azimuths, both lobes and the declared initial nulls.

Keep the truth-assisted `ambient_replaced_refit` and observer-only
`observer_refit` arms separate, with both existing seed/grow and 5%-deficit
comparators and the declared correction/velocity sensitivities. Preserve
frozen source hashes, prediction-before-score ordering, independent review
and every nondetection, failed side and qualification flag. The new front
experiment must not alter these frozen methods, thresholds or cohort.

Return before/after brightness and deficit maps, representative outlines,
projected completeness/purity, false selected area and recovered-volume to
native-volume ratios by case, age, side and view. Distinguish the inferred
3-D volume ratio from projected-area recovery. New masks have no native
lobe-filling fraction until they are explicitly reintegrated. Report the
fraction of the true lobe outside the search aperture and flag clipped cases;
do not silently truncate the truth or present an aperture-limited result as
complete volume recovery. Initial nulls are not evolved no-jet controls.

Retain initial same-cell emissivity subtraction, the agreed band prescription
and full-cell lobe criterion `tr1 > 1e-3`. Put grid, numerical/output settings,
jet/environment parameters and actual snapshot ages at the start of each
analysis summary. Return staged progress, job IDs where applicable, review
status and unresolved interpretations without waiting for the whole cohort.

## Energy instructions already published

The earlier [all-case boundary and injector audit request](2026-11-17-all-case-boundary-injection-audit-request.md)
is committed as **f08a913**. A fresh `git pull --ff-only` was up to date, and
the live GitHub `refs/heads/main` matched its full SHA above before this
update. It is therefore committed and pushed, not an uncommitted local draft.
It covers all four production cases, near-boundary energy/stability layers,
same-cell thermal/kinetic/gravitational and mass changes, injector flux and
storage accounting, and the distinction between reconstructed and exact
solver-recorded supply. Those requests remain in force.

The [100/300-km/s spherical budget priority](2026-11-04-priority-spherical-energy-budget-submission.md)
is also retained in main at **57ed770**. It includes every cell inside each
radius, no shock selection and independent per-case progress. The X-ray
work must not hold up those energy-conservation checks.

## References and delivery

- [Original path-length and front-emission specification](../../science/xray_cavity_path_length_and_bow_shock_check_2026-11-03.md).
- [Original shock-finder validation and failure](../../science/independent_bow_shock_validation_2026-11-04.md).
- [Reviewed emission results](../../science/turn15_energy_emission_review_2026-11-11.md).
- [Qualified interpretation of background/refit results](../../science/turn18_review_reconciliation_2026-11-11.md).

This is repository delivery to both agents, not a private-board post or a
recipient acknowledgement. No native extraction, PBS job or new PLUTO run
was executed by this update; no numerical result, acceptance threshold or
canonical manuscript claim is changed.
