# Paired boundary controls: interior-energy check

Status: requested for execution by Barry's agent. The post-processing script
passes local tests, but no native interior-energy measurement is available yet.
This is an analysis of existing outputs, not a request for new PLUTO runs.

## Decision clarification, 4 November, before full measurements

Report boundary localization and absolute background stability separately.
The localization width is the smallest tested cut for which every energy
component's cellwise absolute paired contrast is at most `0.01 S(t)`.
A candidate adopted coarse-control width must additionally satisfy that same
bound for each twin's cellwise absolute change from its initial state, for
every energy component. Common drift cannot certify an unaffected interior.
Mass times initial specific enthalpy plus fixed potential is contextual only.

The immutable r1 compute stage measures all required signed and absolute
quantities but its adoption label uses only paired contrast. Preserve those
raw results; supersede that label with a separately hash-bound decision
summary applying the combined criterion above. This does not change any
measured quantity. Production-grid certification remains a separate question.

## Setup

- Cases: cluster `002003` and group `002031`, each with reflective and outflow
  conditions on all six faces; initial physical fields must be identical within
  each pair.
- Grid: `400 x 400 x 500`, uniform `1 kpc`; x/y span `-200..200 kpc`,
  z spans `-250..250 kpc`.
- Physics: HD, gamma `5/3`, fixed initial tabulated gravity, no active jet,
  no particles, no cooling.
- First comparison: `t = 0` and `t = 0.25 Myr`, smoke output indices `0,1`.
  The smokes used CFL `0.33`, first timestep approximately `0.01 Myr`, and
  14 accepted updates. Use actual HDF5 ages, not assumed output spacing.
- Follow-up: the corresponding paired `50 Myr` controls once their completion
  and saved-output receipts have been validated.

## Requested test

Check whether the outflow/reflective energy difference is confined to the
boundary's acoustic influence region. At `0.25 Myr`, remove the outermost
`1 kpc` from every box face and compare the remaining energy content. Also
report exclusions of `0, 2, 4 kpc` to expose numerical spreading and convergence.
Corners and edges belong to the excluded union only once.

For each component X, measure the same-cell contrast

\[
D_i^X = [E_{i,\mathrm{out}}^X(t)-E_{i,\mathrm{out}}^X(0)]
       -[E_{i,\mathrm{ref}}^X(t)-E_{i,\mathrm{ref}}^X(0)].
\]

Use thermal `p V / (gamma - 1)`, kinetic `rho |v|^2 V / 2`, and gravitational
`rho Phi_0 V`, with the same fixed centre-zero initial potential in every run.
Also measure mass. Initial arrays are checked cellwise for exact agreement;
then the direct outflow-minus-reflective difference avoids subtracting two large
background sums. Only complete physical cells inside the inset box are kept.

Report for every exclusion:

- Cell count and retained volume.
- Each run's signed change from its own initial state.
- Signed paired differences in all three energies and their sum.
- The sum of absolute cellwise paired differences, separately for each
  component and total, so cancellation cannot masquerade as agreement.
- Residual total difference relative to the whole-grid paired difference and
  to the labelled low-power bipolar comparison `2e43 erg/s * t`.
  There is no actual jet injection in these controls.
- Whether the difference is negligible on those scientifically relevant
  scales. Do not assess this solely against the enormous initial atmosphere
  energy or force a pass by adjusting the exclusion.

## Sound-crossing scale

The retained initial tables have the same SHA-256 hashes as the paired-run
receipts. Using `c_s = sqrt((5/3) p_0/rho_0)` across physical face radii
`200..377.49 kpc` gives:

| Atmosphere | Initial face sound speed (km/s) | c_s * 0.25 Myr (kpc) | c_s * 50 Myr (kpc) |
| --- | ---: | ---: | ---: |
| Cluster | 659.90-695.89 | 0.1687-0.1779 | 33.74-35.58 |
| Group | 311.05-355.07 | 0.0795-0.0908 | 15.91-18.16 |

Sources: `assets/q032_synthetic_harness_2026-10-31/inputs/tabulated_cosmo_002003.csv`
and `tabulated_cosmo_002031.csv`. These are profile-based estimates, not the
requested interior-energy measurements. A spatially varying acoustic travel
time integrates `ds/c_s` along a path; a single local `c_s*t` is an estimate.
Numerical stencils can also spread small differences beyond the continuum
sound horizon. The exclusions must therefore be tested rather than assumed.

## Conditional 40-kpc choice

The requested conservative choice at `50 Myr` is a `40 kpc` exclusion from
every face, conditional on the paired-control check confirming that the
remaining region is sufficiently unaffected. On the production box this keeps
complete cells inside `|x|, |y| < 160 kpc`, `|z| < 210 kpc`.

Compare `0, 20, 30, 40, 50 kpc` on the completed paired 50-Myr controls.
Use the same retained cell set at t and t=0. Do not yet silently replace
published production budgets with this cut. The production grid is stretched,
so coarse-control success alone does not establish its discrete boundary error.

For jet-run application, retain the approved jet-affected spherical apertures
and explicitly check whether they lie inside the boundary-safe region. Flag
any excluded jet-affected gas; clipping it is not evidence of missing jet
injection. Report energy transport across any adopted interior control surface
before treating its storage change as a closed-system conservation result.
The existing G-HI late-time boundary-contact exclusion remains in force.

## Required spherical budgets on the jet simulations

The 100/300-km/s speed-threshold checks are required on **all four full,
with-jet production simulations: C-HI, C-LO, G-HI and G-LO**. The no-jet
reflective/outflow comparison above diagnoses boundary contamination; it does
not replace these production energy budgets.

For each available scientifically valid snapshot, calculate two radii from
the full three-component speed, not just the axial velocity:

\[
R_{100}(t) = \max_{|\boldsymbol v_i|\geq100\,\mathrm{km\,s^{-1}}} r_i,
\qquad
R_{300}(t) = \max_{|\boldsymbol v_i|\geq300\,\mathrm{km\,s^{-1}}} r_i.
\]

Document the cell-membership rule and any minimal padding to enclose the
selected cells. If no cell reaches a threshold, mark that radius unavailable;
do not invent an aperture or report a zero-energy measurement.

For each radius:

- Include **all gas inside the sphere**, including slow cells. Speed defines
  only the outer aperture, not which interior cells contribute energy.
- Subtract the actual t=0 state cell by cell, using exactly the same current
  sphere and fixed initial potential for both times.
- Report thermal, kinetic and gravitational changes, their total, and the
  ratio to the case's bipolar injected energy at that age.
- Then partition the same budget into full-cell cocoon/jet `tr1 > 1e-3` and
  complementary ambient gas. Do not require a shock detection for inclusion.
- Check cocoon and disturbed-gas coverage, weak sound waves, isolated fast
  outliers and boundary-associated flows. Preserve raw threshold radii and
  disclose any selection issue rather than tuning radii for better closure.
- Check the sphere against the proposed boundary-safe region. If it overlaps
  the 40-kpc excluded layer at 50 Myr, flag the conflict. Any separately
  reported clipped budget must identify lost jet-affected gas and must not be
  presented as the complete spherical or injected-energy budget.

Return radius and component-energy time series for both thresholds, including
the total/injected-energy ratios and the difference between threshold choices.
Retain existing snapshot-validity exclusions, particularly late G-HI outputs.
Boundary/spherical energy transport remains relevant to interpreting closure.

The script supplied below is specifically for **no-jet paired controls** and
rejects nonzero tracer. It must not be applied unchanged to the jet runs; the
production spherical-budget extraction is a separate required task.

## Ready-to-run post-processing

Implementation: `scripts/science/audit_paired_boundary_interior.py`.
It opens native HDF5 read-only, streams z planes, checks paired initial fields,
grid agreement, ages and existing source receipts, and refuses to overwrite its
output. Snapshot hashes are reused from validated receipts; live metadata is
checked before and after reading, with the existing device-transition rule.

Run on an allocated compute node, not a login node. Set `PAIRED_RUN_ROOT` to
the existing experiment's `smoke` directory and `RESULTS` to a fresh results
directory. Preserve the frozen experiment sources and original outputs.

```bash
python -m pytest -q tests/test_paired_boundary_interior.py tests/test_paired_nojet_outputs.py
for case_id in cluster_002003 group_002031; do
  python scripts/science/audit_paired_boundary_interior.py \
    --reflective-run "$PAIRED_RUN_ROOT/${case_id}_reflective" \
    --outflow-run "$PAIRED_RUN_ROOT/${case_id}_outflow" \
    --environment "$PAIRED_RUN_ROOT/${case_id}_reflective/tabulated_cosmo_${case_id#*_}.csv" \
    --snapshot-index 1 --buffers-kpc 0 1 2 4 \
    --output "$RESULTS/${case_id}_0p25_interior.json"
done
```

For 50 Myr, use the full-run directories, the validated endpoint index (expected
`5`), and `--buffers-kpc 0 20 30 40 50`. Preserve separate output files.

Local verification: **56 tests passed**, including the existing paired-output
validator suite. Synthetic cases cover boundary-only perturbations, second-layer
penetration, cancellation, full-cell geometry, same-cell subtraction, invalid
states, mismatched initial fields, real HDF5 inputs and receipt mutation checks.
This validates the analysis code, not the physical hypothesis.

## Return to the supervisor

Please return the two-atmosphere energy tables versus exclusion width, a plot
of signed and absolute residual differences versus width, and a clear answer
to whether the 1-kpc hypothesis holds at 0.25 Myr. Separately report the 40-kpc
test at 50 Myr when available. Preserve failures and explain material residuals.
