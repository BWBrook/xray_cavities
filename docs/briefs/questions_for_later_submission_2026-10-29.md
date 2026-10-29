# Questions for later submission

Status: Patrick authorized submission on 29 October 2026. Responses prepared in the existing Q-031 and Q-032 threads; GitHub synchronization pending because the SSH agent refused authentication. The sections below preserve the reviewed drafting notes.

## Q-031 addition on an alternative energy aperture

Could you also investigate a source-size-based aperture as an alternative or comparison to the approved velocity-defined spheres? One possibility is to measure the jet/cocoon extent from tracer and integrate the energy change within a surrounding region enlarged by a factor such as 1.5. This would adapt the aperture to source growth and may be less sensitive to isolated high-velocity cells.

The exact geometry, tracer definition, multiplier and method are not fixed by this suggestion. Barry and his agent should assess whether this approach is useful, modify it, or propose another defensible way to enclose the jet-driven disturbance. Define whether extent means maximum radial distance or one-sided axial length; avoid ambiguity with full bipolar length.

The aperture must include the relevant shocked ambient gas and, where important, sound waves, which may extend beyond tracer-bearing material, particularly in C-LO. Validate coverage using fluid diagnostics and assess sensitivity to reasonable aperture choices. Include all gas inside the chosen region and subtract the initial energy in the same cells, retaining the fixed initial gravitational potential. Tracer would inform aperture coverage, not limit the energy integral to jet material.

Please compare the resulting radii and component/total energy budgets with the velocity-defined apertures, and explain any material differences in terms of disturbance coverage, background drift or boundary transport. Choose and justify the method from the physics and coverage, rather than tuning it to force agreement with injection. This suggestion supplements the existing Q-031 request; the no-jet and unreached-region stability checks remain relevant.

Status: draft addition for later submission; no collaborator message or computation launched.

## Q-031 proposal for a production-grid no-jet control

Would a no-jet control on the same production grid help isolate atmospheric drift and boundary effects? The existing controls use a coarser mesh. Please assess the value and estimated computational/storage cost of matching the production atmosphere, grid, boundary conditions, gravity, solver and numerical settings, with jet injection and the initial nozzle disabled as intended. Barry and his agent can recommend the scope and practical implementation; low computational cost should not be assumed before estimating it. This is a proposal for discussion, not authorization to launch a new simulation.

Compare component and total energy changes, mass changes, and spatial/time evolution with the jet runs, including boundary transport where measurable. Patrick notes that spurious flows have been observed near boundaries in other simulations as an effect of the boundary condition, so their occurrence here is not unexpected. This provides context for the boundary-drift hypothesis; the contribution to the energy changes in these particular runs still needs to be quantified. Bounding spheres may reduce contamination from the outer region; energy transport across their surfaces still needs consideration.

Do not assume the discrepancy is mainly gravitational. At C-LO/50 Myr, the recorded whole-grid changes are approximately 12.23 E_inj thermal, 11.47 E_inj gravitational and 0.27 E_inj kinetic. Thermal and gravitational changes are comparably large, so the audit should retain all components. Assess whether a matched control supports a justified background correction rather than assuming its evolution can simply be subtracted from a jet run. Preserve the raw budgets and state the limits of any correction.

## Q-032 response scope and cavity recovery method

Collect the cavity-method questions and both visual-diagnostic requests below into the same response to Q-032. This is a consolidated discussion draft, not a posted response or approval of a particular correction.

The selected-age production path uses the strongest-deficit 1% of projected physical area inside a 120-kpc radius directly as geometry. This is an area percentile, not a 1% brightness-decrement threshold; it assigns approximately 452 kpc² before component filtering, regardless of cavity size. It may select only the deepest parts of larger cavities. The resulting volume, enthalpy and power deficits should remain provisional rather than being interpreted as intrinsic observational biases.

Please reconcile the actual staged production path with the previously validated seed-and-growth method, which uses the strongest deficits as seeds and expands into connected surrounding support. Return before/after outlines and volume comparisons. Simply increasing the selected fraction is not sufficient: it can merge unrelated structures, and changing the aperture also changes the area selected by a fixed percentile.

The present evidence raises a specific concern about cavity identification and inferred geometry. Review the X-ray methodology more broadly where warranted, but distinguish demonstrated selection problems from any separate concern about the underlying emissivity or projection calculation; a fault in that calculation has not been established.

Are there other defensible ways to recover the X-ray cavities? Please briefly compare plausible alternatives, their assumptions and failure modes rather than assuming seed-and-growth is automatically the best replacement. Assess known-geometry recovery and false detections using independent synthetic and null tests, without using tracer to choose or tune X-ray boundaries. Include background/aperture sensitivity checks and a regression test covering the actual production caller.

Preserve original products and reuse existing outputs. Following validation, refresh dependent geometry, pressure sampling, enthalpies, geometry-dependent ages, powers and manuscript claims. The observer-method issue does not invalidate the independent native tracer accounting.

## Question about the two-component topology requirement

The current quantitative gate accepts exactly two disconnected components on opposite sides of the nucleus. Connected cross-midplane, fragmented and one-sided detections are rejected; this classification depends on projection and selection method and does not establish the physical topology of the simulated cocoon.

Is requiring two disconnected components justified for every output and viewing angle? Could it reject physically valid connected or overlapping projected cavities? Please explain how alternative recovery methods would handle these morphologies and distinguish genuine non-detections from failures of the assumed geometry. This is an open question, not a request to relax the gate without validation.

## Visual validation of the shocked-ambient selection

Could we obtain a postage-stamp montage showing the shocked-ambient selection for each simulation (C-HI, C-LO, G-HI and G-LO) at every analysed output?

Each stamp should show a spatial pcolormesh slice with density or entropy as the background and the actual selected shocked-ambient mask outlined. The background and mask must refer to the same slice. Arrange the montage by simulation and output age, with clear case/time labels, axes in kpc, and labelled colour scales. Use a consistent slice convention and comparable plotting scales where practical.

The purpose is to check visually whether the energy-integration mask follows the bow-shocked ambient shell and to identify omissions, contamination or fragmentation. Include analysed outputs that fail the acceptance gates, clearly labelling their status rather than silently omitting them; any candidate mask shown for a rejected output must be distinguished from an accepted selection.

Include this shocked-ambient diagnostic in the Q-032 response as a related request, alongside the X-ray cavity-selection plots. It remains a request to discuss later, not an instruction to launch post-processing or a new simulation now.

## Validate the cavity search radius against the simulated fluid

Patrick suggests using the simulation fluid fields to check whether the fixed 120-kpc cavity-selection radius encloses the relevant source. For each simulation and analysed output, examine how far the jet/cocoon material and shocked ambient gas extend, and compare their projected extent with the 120-kpc aperture at each viewing angle. An overlay of those extents and the aperture would make any truncation apparent.

Use this as an independent validation of search-aperture coverage; retain X-ray-based determination of the cavity boundary. Report cases where jet or shocked gas extends outside the aperture, and assess whether the search radius needs revision. Where shock identification is unresolved, flag that limitation rather than treating the absent mask as evidence that the aperture contains the disturbance.

The existing implementation labels 120 kpc an edge-safe search aperture nested within a 180-kpc background region. We have not found a physical justification establishing coverage across all cases and ages; request that justification or an explicit coverage test.

Status: draft for later discussion; no analysis or collaborator message requested yet.

## Retain cavity-selection postage stamps for every method

Patrick requests visual inspection of selected X-ray cavities regardless of the recovery method used. Existing per-case selected-age montages are available under `docs/science/assets/four_case_selected_age_observables_2026-08-26/four_case_xray_complete/review_products/products/{case}/selected_age_xray_cavity.png`; these show fractional X-ray deficit, selected-mask outlines and the older projected tracer comparator.

Include updated postage stamps in the Q-032 method comparison for every analysed case, age and view, retaining rejected detections and labelling topology/acceptance status. Show the X-ray background or deficit and selected outlines, with the search aperture visible and a field of view wide enough to assess truncation. Label the tracer comparator explicitly and update it to the adopted native convention where appropriate. Preserve equivalent visual diagnostics for any alternative selection method.

## Generate morphology diagnostics on every analysis run

Both the cavity-selection and shocked-ambient-selection plots should be generated automatically on every applicable analysis-pipeline run as routine verification products, regardless of the selection method used. Produce them alongside the numerical outputs for the cases, outputs and views analysed in that run, including rejected or unresolved selections. This should make the actual masks used for geometry and energy integration visually inspectable on each execution, rather than requiring a separate diagnostic request. Retain method/settings and acceptance labels so plots can be matched to the corresponding measurements.
