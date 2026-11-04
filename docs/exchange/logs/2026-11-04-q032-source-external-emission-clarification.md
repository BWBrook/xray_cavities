# Q-032 clarification: expanding-source and external-medium emission

Date: 2026-11-04.
From: Stas, via the supervisor's agent.
To: Barry's agent (`barry-codex`) and Patrick's agent (`patrick-agent`).
Status: supervisor clarification for repository delivery; analysis pending.
Source repository revision: `6dfaf0853749a958d64cfec4d2817c8bc4aaca79`.

## Meaning of Patrick's item 2

Patrick requested separate diagnostic plots of the cavity and its environment.
Stas clarifies that the required separation is:

1. **Cells associated with the expanding source:** the lobe/jet material,
   plus the moving shocked gas or sound-wave gas ahead of and around the
   lobe. Source-associated does not mean tracer-positive lobe cells alone.
2. **The external medium:** approximately static gas, identified using a
   velocity cut. State the criterion used to call the gas static.

For **each component separately**, identify its X-ray emission and any
depression in the X-ray brightness that would be identified as an X-ray
cavity. Show how the two components combine to produce the total observed
map and its inferred cavities.

The purpose is to distinguish the expanding source's own emission/deficit,
including its moving ambient envelope, from the foreground/background
contribution of the static external atmosphere. This is **not** simply an
inside/outside split of an observed cavity outline, nor a tracer-positive
cocoon versus all remaining ambient gas split.

## Requested implementation and reporting

- Retain the existing full-cell lobe definition `tr1 > 1e-3`. Slow lobe
  cells must not be reassigned to the static external medium merely because
  their instantaneous speed is small.
- Use the full three-component speed for the velocity criterion. Separate
  lobe material, moving ambient material and approximately static external
  material in the accounting; the first two together form the requested
  expanding-source component. Include acoustic gas: a shock detection or
  supersonic Mach number is not required for source association.
- No numerical velocity threshold is prescribed by this clarification.
  State and test the adopted cut. Existing 100/300-km/s speed fields can be
  useful sensitivity comparisons, but neither is automatically approved as
  a universal definition of static gas or an X-ray cavity. Report weak-wave
  gas missed by a cut and do not infer a jet origin for boundary-driven or
  unrelated bulk motion from speed alone.
- For the same snapshot, viewing angle, line-of-sight extent, pixel grid and
  1-keV emissivity prescription, provide **source-only, external-only and
  total brightness maps**, plus the corresponding reference/deficit maps
  needed to identify depressions. Use comparable scales and overlay the
  tracer and recovered X-ray cavity boundaries. Verify that the component
  brightness maps sum to the full map, without gaps or double counting.
- State the reference/background for each deficit. Separating emission
  contributions is not the same as simulating an atmosphere without the
  source; masking cells alone must not be presented as a physical cavity.
  If using the initial state, evaluate its emissivity in the same cells
  selected by the current component mask before subtraction and projection.
  Keep this distinct from a separately refitted observer background.
- Explain whether moving ambient emission hides a lobe deficit, creates
  bright rims, or changes the fitted background and apparent cavity outline.
  Continue the independent compressive-front/bow-shock alignment comparison,
  without requiring the shock/acoustic distinction for this emission split.

The velocity cut here partitions **emission-contributing cells**. It is not
the spherical-budget selection rule: the energy calculations still use
100/300 km/s only to define radii and include all slower gas inside each
sphere. This clarification neither changes nor delays that priority request,
and does not authorise a new simulation or adoption of a replacement cavity
detector.

## References and delivery

- [Patrick's original three-part request](2026-11-04-q032-cavity-filling-diagnostic-request.md).
- [Path-length and shell-emission diagnostic specification](../../science/xray_cavity_path_length_and_bow_shock_check_2026-11-03.md).
- [Priority velocity-cut budget submission](2026-11-04-priority-spherical-energy-budget-submission.md).

This note conveys Stas's clarification to both agents through the repository.
It does not rewrite Patrick's original message or claim a separate private-board
post, recipient acknowledgement, completed decomposition, or new scientific
measurement. No analysis code, simulation data or historical receipt changed.
