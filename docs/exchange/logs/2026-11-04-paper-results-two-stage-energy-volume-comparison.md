# Paper results: separate physical energetics from X-ray volume recovery

Date: 2026-11-04.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`).
Status: supervisor instruction for the paper structure and analysis sequence.
Source repository revision: `6dfaf0853749a958d64cfec4d2817c8bc4aaca79`.

## Requested logical flow

Stas requests two separate comparisons in the Results, in this order:

1. **Energetics using the true volume inflated by the lobes.** Compare the
   actual native energy components and jet input with `2.5pV` and `4pV` on
   that true volume. Any failure of enthalpy to represent the supplied energy,
   including omission of shock-associated energy, must already be visible
   here. It must not be attributed to an X-ray volume-finding error.
2. **Energetics using the synthetic-X-ray recovered volume.** Only after the
   first comparison introduce the recovered volume and the additional errors
   caused by detection, projection and geometry. This stage should establish
   which combinations of jet power and environment make X-ray recovery more
   or less feasible.

Conversion of energy to power using uncertain ages remains a later, separate
layer. Use the true simulation age for injected-energy normalization in the
first two stages.

## Stage 1: physical-proxy performance at native truth

Use the established full-cell `tr1 > 1e-3` lobe/jet definition for the native
volume. Calculate native enthalpy with the resolved pressure field:

\[
V_{\rm lobe}=\sum_{\mathrm{tr1}_i>10^{-3}}V_i,
\qquad
H_{\rm native,\alpha}
 =\alpha\sum_{\mathrm{tr1}_i>10^{-3}}p_i(t)V_i,
\qquad \alpha=2.5,\ 4.
\]

Keep `2.5pV` primary for the adopted non-relativistic analysis and `4pV` as
the literature comparator. This instruction does not change those conventions.

Show alongside these proxies:

- Injected bipolar energy at the actual simulation age.
- Thermal, kinetic and fixed-initial-potential gravitational changes, using
  same-cell subtraction from the actual initial state and the approved
  aperture/coverage reporting.
- The full-cell cocoon/ambient split, so energy retained outside the lobe is
  visible. Shocked/compressed gas, acoustic disturbances and bulk motions
  belong in the ambient accounting whether or not a shock finder accepts them.
- The corresponding retained-energy/input comparison, with boundary
  contamination and aperture transport limitations explicit.

The intended question is: **even with perfect knowledge of lobe volume,
how well does classical cavity enthalpy capture the actual energetics?**
This is where the energy associated with shocks or other ambient disturbances
must be exposed. Do not infer that every enthalpy shortfall is shock energy
without the component accounting. Enthalpy is a proxy including internal
energy plus displacement work, not another additive term to sum with the
complete thermal/kinetic/gravitational ledger; avoid double counting.

## Stage 2: the additional observational-volume error

For matched case, age, lobe side and viewing angle, show:

- Recovered X-ray volume relative to native true lobe volume.
- X-ray-inferred `2.5pV` and `4pV` relative to both the corresponding native
  proxy and the actual energy/input benchmarks used in stage 1.
- A volume-only comparison holding the pressure convention fixed, followed
  by the full observer estimate with its inferred pressure. Report pressure
  bias separately so the volume-recovery contribution remains identifiable.
- How these results vary across C-HI, C-LO, G-HI and G-LO, with representative
  good/bad maps, completeness/purity, aperture clipping and nondetections.

The question is now: **how much further error is introduced by recovering
the cavity from an X-ray image, and for which jet/environment combinations
does that measurement work?** Do not combine this additional error with the
physical-proxy limitation into one unexplained recovery factor.

Use scientifically valid snapshots and existing boundary-contact exclusions.
Do not let the 120-kpc search aperture silently truncate the comparison.
The current 0/45/90-degree maps are azimuthal, all side-on; label them as such
and do not interpret their differences as inclination foreshortening.
Keep tracer-based validation independent of observer detection, and preserve
the existing holds on failed or withdrawn cavity-recovery results.

## Relation to the emission-decomposition clarification

The accompanying
[source/external emission diagnostic](2026-11-04-q032-source-external-emission-clarification.md)
helps explain stage 2: separate emission from lobe material plus moving
shocked/sound-wave ambient gas from approximately static external gas.
That broader source-associated emission component **does not redefine**
the native tracer-defined lobe volume or merge ambient energy into the
cocoon in stage 1.

## Requested action and delivery

Barry's agent: incorporate this explicit two-stage comparison into the Results
plan, figure design and analysis interpretation. The existing broad native ->
observer -> clock order in
[the canonical manuscript](../../../manuscript/text/main.md) is consistent
with this request, but the true-volume baseline and the distinct sources of
error must be explicit. Revise scientific claims only when the required
measurements are available; do not reinstate invalid observer numbers.

This handover does not change the priority of submitting the independent
100/300-km/s energy budgets. It records the supervisor's requested structure,
not a completed manuscript rewrite, new result, separate private-board post
or recipient acknowledgement.
