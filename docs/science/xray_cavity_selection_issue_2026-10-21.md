# X-ray cavity selection: check and action requested

Status: Q-032 open for Barry-codex to resolve with Patrick-agent. Patrick's
29 October review is endorsed by Stas on 30 October; implementation and
validated results remain outstanding.

## Supervisor endorsement on 30 October

Stas agrees that Patrick's approach is correct and that the cavity recovery
issue needs to be resolved. Barry should prioritise the corrective work with
Patrick, following the method comparison, production-path validation,
aperture-coverage and topology review requested on 29 October. This includes
automatic cavity and shocked-ambient mask overlays on every applicable
analysis run, with rejected detections and the search aperture visible.

Return before/after outlines and volumes, then refresh affected geometry,
pressure sampling, enthalpies, geometry-dependent ages, powers and manuscript
claims after validation. Choosing seed-and-growth or another method still
requires evidence; the endorsement is not an automatic pass for a specific
algorithm. Keep observer conclusions provisional, preserve native accounting
and old products, and reuse existing outputs. Q-031 remains requested; no
new PLUTO simulation or data deletion is authorised here.

## Setup and scope

- Four production cases: C-HI/C-LO in cluster 002003, G-HI/G-LO in group
  002031; one-sided jet powers 1e45/1e43 erg/s for HI/LO, twice these for
  bipolar power; HD with gamma=5/3, speed 0.1c and 15-degree opening angles.
- Production grid: 960 x 960 x 1014, x/y +/-200 kpc and z +/-250 kpc,
  central spacing 0.05 kpc. This is a downstream X-ray recovery review,
  not a new simulation or timestep/configuration audit.
- Q-029 comparisons use 19 case-ages: 10/20/30/40/50 Myr, except G-HI/50
  is excluded. There are 57 age-view combinations at 0/45/90 degrees,
  37 accepted observer measurements and 20 topology failures.
- Native reference: full cell volumes for strict tr1 > 1e-3. The displayed
  older contour figures instead use projected tracer >=5e-3; label that
  distinction and refresh the comparison outline when regenerating figures.

## Findings from code and retained products

Stas agrees that the displayed X-ray outlines do not adequately recover
the cocoon extent and asks Patrick-agent to check/action this issue, with
Barry-codex also informed.

The selected-age builder calls
`build_three_case_cavity_recovery.analyse_loaded_map`. That routine computes
`D = (S_background - S_X) / S_background` and keeps the highest-deficit
1 percent of projected physical area within a 120-kpc-radius circle.
The background is an azimuthal median within 180 kpc, with 5-kpc radial bins
and 10-kpc smoothing. Components below 25 kpc^2 are removed. The retained
seed-sized mask is used directly for geometry; it is not grown afterwards.

This is an area-percentile criterion, NOT a fixed 1-percent brightness
decrement. Before filtering and discretization/ties it assigns approximately
`0.01*pi*120^2 = 452.39 kpc^2` to the candidate, regardless of source size.
It is therefore a likely major contributor to the nearly fixed recovered
volumes. The 120-kpc search aperture is a separate possible truncation of
larger sources; changing the percentile alone does not address that.

For C-HI at 20 Myr and 0 degrees, with the same 5/10-kpc background settings,
the existing sensitivity table gives:

| Selected area fraction | Deficit threshold | Geometric volume (kpc^3) | Topology |
| --- | ---: | ---: | --- |
| 1% | 0.17959484 | 6410.8494 | two separate components |
| 2% | 0.13964172 | 16175.7905 | two separate components |
| 3% | 0.10217887 | 27907.2232 | two separate components |
| 5% | 0.03645391 | 54477.7784 | connected across midplane; not quantitative |

Thus relaxation increases the selected extent but can also merge background
structures. The final row is an invalid geometry proxy, not an accepted
cavity volume. These are retained sensitivity results, not new calculations.

## Discrepancy with the validated method

Goal 045's July 23 report explicitly uses the one-percent tail only as
hemisphere-specific seeds, followed by connected growth against a robust
degree-6 Chebyshev log-intensity background. Its validator calls
`hemisphere_seed_grow_recovery.recover_hemisphere_seed_grow`; the recorded
support threshold is `max(0, median + 3*1.4826*MAD)` in the outer-annulus
fractional deficit. The current selected-age caller instead uses the older
direct one-percent mask described above. Q-029 reused those observer
measurements when changing the native reference.

Patrick should independently reconcile the actual staged source/provenance
with this code-path finding. July's fixture-informed pass does not establish
that the different selected-age method passed the same geometry tests.
The existing volume deficits must remain provisional pipeline results,
not evidence of an intrinsic observational loss of most cocoon volume.

## Requested actions

1. Patrick-agent: check the actual selection/background/geometry path and
   confirm whether the validated seed-and-growth routine was omitted from
   selected-age production. State the impact and coordinate corrective action
   with Barry-codex. Verify the existing refinement before integrating it;
   do not simply substitute another fixed area fraction without validation.
2. Check search-aperture coverage and background-model stability. Retain
   tracer-blind X-ray selection; use the adopted tr1 > 1e-3 reference only
   for post-hoc evaluation, not tuning boundaries to force agreement.
3. Validate the chosen method with independent synthetic and null controls,
   known-volume recovery, threshold/aperture sensitivities, and actual-source
   contour overlays. Keep rejected/connected/fragmented detections explicit.
   Add a regression test covering the actual selected-age production caller,
   not just a separate validation routine.
4. Barry-codex: mark affected Q-029/Q-030 X-ray recovery conclusions as
   provisional pending Q-032. Preserve original products and source hashes.
   After validation, refresh affected volumes, pressure sampling, pV/2.5pV/
   4pV, geometry-dependent age inputs, inferred powers, figures and manuscript
   statements. The native tracer definition and independent native ledgers
   are not invalidated by this observer-mask finding.
5. Return a concise diagnosis, chosen correction, validation evidence and
   before/after outlines and volume ratios. Reuse retained maps where possible;
   this notification does not authorize a new PLUTO campaign or data deletion.

## Evidence

- `scripts/science/build_selected_age_xray_cavity.py`, call to `analyse_loaded_map`.
- `scripts/science/build_three_case_cavity_recovery.py`, `_observer_mask` and `analyse_loaded_map`.
- `scripts/science/three_case_cavity_recovery.py`, physical-area selection and constants.
- `scripts/science/validate_xray_cavity_recovery_refinement.py`, seed/growth validation.
- `docs/science/xray_cavity_recovery_method_refinement_2026-07-23.md`.
- `docs/science/assets/four_case_selected_age_observables_2026-08-26/four_case_xray_complete/review_products/products/C-HI/xray_method_sensitivity.csv`.
- `docs/science/assets/four_case_selected_age_observables_2026-08-26/four_case_xray_complete/review_products/products/` for saved outlines and selection parameters.
- `docs/science/q029_binary_native_refresh_2026-09-06.md` for observer reuse and current native reference.
