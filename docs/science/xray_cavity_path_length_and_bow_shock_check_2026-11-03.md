# X-ray recovery: path length and bow-shock emission

Date: 2026-11-03.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`) and Patrick's agent (`patrick-agent`).
Status: requested existing-output diagnostic and methodological review.
No new native analysis, bow-shock alignment, or causal result is claimed here.

## The two distinct questions

Stas agrees that two effects must be investigated separately:

1. **"Is the background contrast enough?"** The path length through the
   cocoon, relative to the foreground/background emitting column, controls
   whether a tracer-bearing sightline produces a detectable X-ray deficit.
   Near projected rims and tips, a short cavity chord may produce little
   missing emission even though the sightline intersects genuine cocoon.
2. **"Is tracer cell seen as an X-ray cavity cell?"** Emission from shocked
   ambient gas may fill in the projected deficit of the cocoon. Also measure
   emission from the tracer-tagged material itself rather than assuming that
   every tagged cell is X-ray dark.

The specific additional check requested by Stas is: **do the orange X-ray
arcs line up with the bow shock?** They may trace a jet-driven shock structure
or its effect on the background estimate, even though they lie outside the
tracer-defined cocoon. Do not assume they are unrelated background features
before doing this comparison.

Orange is the outline of the **5% fractional-deficit selection**, not a contour
of bright shocked emission. Distinguish coincidence with a shock front, its
inner/outer edge, and an adjacent apparent deficit. Alignment is a useful
test, but by itself does not establish which emission component causes the
selection failure.

## Setup and motivating evidence

Start with the retained **G-HI 20-Myr** snapshot and its **0/90-degree** maps;
include 45 degrees as a cross-check. Report the actual HDF5 age and the
source-bound grid, timestep/output settings, jet parameters and environment
at the start of the returned analysis. Use the existing manifests rather
than inferring a timestep from the nominal snapshot spacing.

- G-HI is the high-power group case, environment `002031`.
- These projections rotate the line of sight about the jet's z-axis, from
  y towards x. All three keep the jet in the sky plane; they do not test
  inclination or foreshortening. The projected tracer shapes are similar.
- Both lobes of this snapshot are fully inside the 120-kpc search aperture.
  Aperture clipping therefore cannot explain the examples below.
- The reference is the existing full-cell `tr1 > 1e-3` cocoon definition.
  The projected mask uses the maximum grid tracer along the sightline, not
  particle counts and not an emissivity-weighted tracer. Fewer radio tracer
  particles cannot directly cause this map-selection failure.
- The retained comparisons use corrected 1-keV brightness maps and estimated
  observer backgrounds; they have not used a t=0 background in this ladder.

These values were recomputed from the retained per-side CSV rows and native
binary-tracer volumes. Volumes sum both lobes before division; projected
completeness and purity use summed intersection/reference/selected areas.
They are not medians across ages or sides.

| View | Method / colour | Recovered / native volume | Tracer area recovered | Selected area inside tracer |
| --- | --- | ---: | ---: | ---: |
| 0 deg | Seed-and-grow / blue | 67.8% | 67.8% | approximately 100% |
| 0 deg | Deficit 5% / orange | 398.1% | 51.6% | 44.7% |
| 90 deg | Seed-and-grow / blue | 62.2% | 64.4% | approximately 100% |
| 90 deg | Deficit 5% / orange | 108.9% | 60.4% | 80.0% |

The blue outline is relatively faithful but misses about a third of the
volume at 0 degrees. The orange outline includes large lateral arcs at
0 degrees; revolving off-axis selected areas gives them a large volume
weight. The near-correct total orange volume at 90 degrees is not proof of
correct geometry. The impression of better recovery near the jet/lobe
interior than at the rims is a hypothesis to quantify, not a measured
monotonic radial trend or a local 3D-volume result.

## Requested checks

1. **Independent shock geometry.** Identify the bow shock from the native
   hydrodynamics, with pressure/density jumps and compression checks. State
   the detector and limitations; do not define the shock using the orange
   mask, the tracer boundary, or speed alone. Project the shock surface and
   shocked-shell emission into the exact same coordinates and pixel grid as
   the retained maps. An axial shock position alone cannot locate the lateral
   arcs. This shock diagnostic does not reintroduce shock selection into the
   total-grid or spherical energy budgets.
2. **Matched overlays and profiles.** For each view show raw X-ray brightness,
   fractional deficit, the full projected tracer boundary, the independent
   shock outline, and the blue/orange recovered masks. Include transverse
   profiles through an arc and through a lobe, showing pressure/density
   diagnostics or projected shocked emission where appropriate. Measure
   contour separation/overlap; do not rely only on visual resemblance. Keep
   scales comparable across views and show the 120-kpc aperture explicitly.
3. **Path length versus selection.** Map the summed physical path length of
   cells with `tr1 > 1e-3`, not just the maximum tracer. Compare detected and
   missed tracer sightlines by cocoon chord length, position, initial
   brightness and fractional deficit. Distinguish distance from the jet
   axis/cocoon boundary from distance from the galaxy centre. This addresses
   the first question without assuming a loss of tracer-particle sampling.
4. **Emission accounting.** Use the same 1-keV emissivity prescription,
   projection weights and pixel grid for disjoint cocoon, shocked-ambient and
   unshocked-ambient contributions. Verify that their sum reproduces the
   total brightness. Quantify shell emission along both missed cocoon
   sightlines and the lateral orange arcs. Do not assume heating always
   increases the emission in this particular band; retain the measured sign.
5. **Controlled same-cell initial-emissivity test.** Replace the emissivity
   of the current shocked-ambient cells by their t=0 emissivity at the same
   grid locations. Leave all other cells and projection weights unchanged.
   Hold the observer background fixed first, then separately refit it and
   repeat the detection to distinguish direct filling-in from background-fit
   bias. Do not delete all shocked emission: that would also delete the
   emission of the gas that was present initially and create an artificial
   cavity. Label the replacement a diagnostic, not a new physical simulation.

For clarity, for each sightline/pixel p, with j the band-specific volume
emissivity and w the existing path-length/projection weight:

\[
S_t(p) = S_{\rm cocoon}(p) + S_{\rm shocked\ ambient}(p)
       + S_{\rm unshocked\ ambient}(p),
\]

\[
\Delta S_{\rm shock}(p)
 = \sum_{i\in{\cal S}(t)} w_{pi}\,[j_i(t)-j_i(0)],
\qquad
S_{\rm test}(p) = S_t(p)-\Delta S_{\rm shock}(p).
\]

Here the current shocked-ambient mask is fixed for the t/t=0 comparison;
`j_i(0)` is evaluated from the initial primitives in the identical cell.
Retain signed differences rather than clipping negative changes. This
isolates the emissivity-change contribution of those cells, not exclusively
irreversible shock heating or a complete no-jet counterfactual. Compare with
the separately projected t=0 atmosphere as a labelled reference, with the
known atmosphere-stability caveat retained.

## Requested response and scope

- **Barry's agent:** coordinate the existing-output extraction and return
  the matched maps, component accounting, path-length comparison, and
  before/after recovery metrics. State whether the arcs follow the shock,
  whether shell emission hides real cocoon, and whether background fitting
  generates or enlarges the apparent deficits. Report unresolved alternatives.
- **Patrick's agent:** review/action the cavity-selection and background-model
  issues, the independent shock comparison and the interpretation of any
  alignment. Advise how to separate a true shell/cavity boundary from an
  artefact of background fitting without using tracer truth to tune the
  observer detector.
- Report both per-lobe and bipolar volume accuracy, tracer completeness and
  purity. Keep direct projected-area recovery distinct from 3D volume
  inference. Preserve the `tr1 > 1e-3` convention and show the selection rule.
- For age extensions, exclude snapshots where the existing aperture truncates
  the cocoon, or use and explicitly validate a larger aperture. C-HI and
  G-HI at 10/20 Myr are fully contained in the retained three-view set; their
  later selected ages are not. Existing G-HI late-time physical-validity
  exclusions remain in force regardless of aperture changes.
- This requests post-processing of existing outputs, not new PLUTO runs,
  duplicate jobs, or immediate adoption of a new recovery method. Preserve
  existing compute/ownership/dependency gates. The published Q-031 native
  pilot targets C-HI/G-HI at 40 Myr and currently has no published scientific
  results; it is relevant infrastructure, not completion of this 20-Myr test.

## Evidence and implementation references

- [Retained interpretation](q032_retained_method_ladder_interpretation_2026-11-01.md).
- [Per-side recovery rows](assets/q032_retained_method_ladder_2026-10-31/results/method_ladder_rows.csv).
- [Native G-HI volumes](assets/q029_binary_native_refresh_2026-09-06/remote_analysis/G-HI/native_energy_selected_age.csv).
- [G-HI 20 Myr, 0 degrees](assets/q032_retained_method_ladder_2026-10-31/results/stamps/G-HI_age20_0deg.png).
- [G-HI 20 Myr, 90 degrees](assets/q032_retained_method_ladder_2026-10-31/results/stamps/G-HI_age20_90deg.png).
- `scripts/science/build_q032_selected_age_method_ladder.py` and
  `scripts/science/xray_cavity_method_ladder.py`: selection and evaluation.
- `scripts/science/build_q031_native_emission.py`: existing native path-length
  and emission-component pilot; currently fixed to snapshot 40.

Delivery: repository handover addressed to both agents. This note does not
claim a separate private-board post or acknowledgement from either agent.
