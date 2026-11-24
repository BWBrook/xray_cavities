# Source excluded X ray backgrounds and energy partition

Date: 2026-11-24.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`) and Patrick's agent (`patrick-agent`).
Status: approved for repository delivery and existing-output analysis.
Source revision: `341125aa9cb04e87c44b72784ff416d1117bf18e`.

## Background fits must exclude the source

Stas requests two explicit calculations and a comparison. The existing
orange-arc background uses azimuthal medians of the valid X-ray image,
without a radio/tracer exclusion. Instead fit the atmosphere using locations
not coincident with the expanding source. Tracer exclusion is a useful first
diagnostic, but tracer-free gas can still be compressed or otherwise disturbed.

1. **Tracer exclusion:** project full-cell lobe membership `tr1 > 1e-3` and
   exclude sky pixels whose sightlines intersect those cells from the radial
   background fit. Use the remaining azimuthal sectors at each radius.
2. **Velocity exclusion:** independently project a disturbance mask based on
   the full three-component gas speed, then exclude its footprint from the
   background fit. State and test the adopted speed or local-Mach threshold;
   no universal numerical threshold is prescribed by this request. Record
   slow tracer-positive lobe sightlines left unmasked by this alternative.
   If needed, also report the union with the tracer mask as a clearly labelled
   additional diagnostic, not a replacement for either requested comparison.

These are **two-dimensional fitting exclusions**. Do not delete selected
three-dimensional cells from the synthetic X-ray image. Fit/smooth B(R) using
only the retained sky pixels, interpolate radial gaps where supported, and
apply B(R) to the same unchanged full image for cavity identification. Where
central radii have no usable fitting pixels, inward continuation is an
extrapolation: give its model dependence and radial coverage rather than
silently treating an unconstrained centre as measured background.

The physical comparison matters. A radio-defined mask would miss compressed
ambient gas that emits no radio signal, so it can leave a biased background.
Tracer masking does not solve that omission by itself. The velocity test
should assess it, not simply relabel all slow gas as truly undisturbed.
Retain pressure/density-change, boundary-disturbance and coverage diagnostics
when assessing how clean the remaining atmosphere is. State any mask padding
and threshold sensitivity before interpreting an improvement.

Start with the exposed G-HI/20 images, then compare different valid snapshots
and all four simulations in the existing selected-age/viewing design. Keep
G-HI 48--50 excluded. Show both masks, retained fitting support versus radius,
old and new B(R), full brightness/deficit maps and cavity/tracer outlines.
Report exterior false-arc area, projected completeness/purity and recovered
volume divided by exact native lobe volume, by lobe and jointly. Preserve
nondetections and aperture/coverage flags; near-unity volume alone is not a
successful recovery. A new mask needs a new native integration before any
three-dimensional lobe-filling fraction is claimed.

Barry should coordinate implementation; Patrick should review the fitting
support, velocity criterion, extrapolation and interpretation. Tracer and
native-velocity masks are simulation-assisted, not X-ray-only methods. Keep
them as new comparisons: do not mutate the frozen operators, cohort, sealed
predictions, original scores or prospective acceptance criteria. A separately
specified radio mask can later provide the observational counterpart.

## Use actual energy supplied by the injector

Stas confirms that subsequent energetics and cavity comparisons must use
cumulative **actual net injected gas energy**, not only intended jet power
times age. Include the axial and lateral faces of the discretised injector,
kinetic and enthalpy transport, and signed exchange across its stationary
surface. Keep maintained-region storage accounting consistent with the
chosen control volume. Ignoring lateral flux would omit real numerical supply.

Retain nominal bipolar power times actual active age as a labelled reference.
The current denominator is reconstructed net gas delivery, not an exact
historical solver counter. Keep gravitational transport/mass conventions
explicit and separate from this mechanical-gas denominator. Do not double
count overwrite supply and exported flux, or fold later numerical gains/losses
into the definition of jet delivery.

## Proceed to component and shock budgets

Stas regards the current approximately 2--8% interior storage/input discrepancy
at 30 Myr as acceptable working accuracy to proceed. This is a supervisor
decision about analysis priority, not a claim of exact conservation or an
all-age calibration. Checking energy transport remains worthwhile and should
not hold up the component time series.

- For C-HI, C-LO, G-HI and G-LO, report thermal, kinetic and gravitational
  changes at every scientifically retained snapshot, in erg and as fractions
  of matched cumulative actual injector supply. Reuse the existing native
  integrals and retain same-cell t minus t=0 subtraction, the fixed initial
  potential and signed terms. Do not clip negative components or force the
  fractions to sum to one.
- Split each component between full-cell cocoon (`tr1 > 1e-3`) and ambient
  gas. Provide clear time-series plots and selected-age tables, with the
  grid, numerical/output settings, jet/environment parameters and actual ages
  at the start of each summary. Keep native 2.5pV primary and 4pV as comparison.
- Measure transport across the actual R100/R300 apertures, including pressure
  work and consistent potential/mass transport where applicable. Their radii
  come from 100/300 km/s speed cuts, not fixed 100/300-kpc boundaries. Account
  for changing apertures in interval balances, or use declared fixed surfaces
  to distinguish transport from cells entering/leaving the selected volume.
- Quantify energy associated with shocks **if present**, including downstream
  gas rather than only the narrow active front. Show its thermal, kinetic
  and gravitational contributions as subsets of the component budgets, not
  an additive fourth energy component. Separate ambient bow shocks from
  internal lobe/jet shocks where identifiable.
- Distinguish reversible compression/acoustic waves from irreversible shock
  heating. A compressive-front mask is not automatically a shock mask. Use
  reviewed upstream/downstream jump and propagation diagnostics; where a
  shock-heating estimate is supported, distinguish it from adiabatic thermal
  changes. State whether a quantity is current stored energy or cumulative
  dissipation, rather than summing the two. Weak/ambiguous fronts retain that
  label. PLUTO's entropy-recovery counter measures a numerical correction,
  not physical shock heating, and must remain separate.

Reuse existing outputs, completed reductions and live job inventories before
submitting analysis. Preserve boundary/contact and truncated-aperture flags.
This instruction neither authorises a new PLUTO run nor prescribes disabling
the entropy switch or correcting full histories from the 10--12 Myr pairs.

## Evidence and delivery

- [Matched actual-input and native storage definitions](../../science/native_delivery_restatement_2026-11-21.md).
- [All four injector histories](../../science/production_injector_histories_2026-11-21.md).
- [Existing native component budgets](../../science/turn15_energy_emission_review_2026-11-11.md).
- [Exposed front and background comparison](../../science/ghi20_compressive_front_comparison_2026-11-23.md).
- [Frozen background comparison](../../science/background_refit_blind_protocol_2026-11-11.md).
- [Current prediction and scoring custody](../../science/xray_prediction_seal_2026-11-23.md).
- [Earlier all-case boundary and injection instructions](2026-11-17-all-case-boundary-injection-audit-request.md).

This publishes Stas's approved feedback to both agents through the repository.
It is not a private-board post or an acknowledgement from either recipient.
No analysis job, native extraction or new simulation was run by this update.
Please return per-case progress, the method review and the first comparisons.
