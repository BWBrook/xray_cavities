# 2026-08-31 - selected-age dual-space energetics audit

Goal 066 implements the selected-age proof of the locked dual-space energetics
design. It uses the existing native-grid fractional-tracer energy ledger and a
new independent observer path based on X-ray-only cavity geometry and a
synthetic-X-ray-deprojected ambient pressure profile.

The observer pass now retains density-squared path length and
corrected-emissivity temperature information. It excludes the X-ray cavity
mask from spherical ambient annuli, deprojects density and temperature under
an explicit lightly regularized non-negative model, and computes both
midpoint and ellipsoid-volume-averaged pressures. Tracer does not enter this
builder.

The eventual local join will report volume recovery, pressure recovery,
their exact product as lobe-enthalpy recovery, and separate ratios to native
lobe enthalpy, retained energy, and injected energy. `2.5pV` is primary and
`4pV` is retained as the literature comparator. C-LO background and unresolved
boundary terms remain labelled; no closure residual is promoted to physical
energy.

The complete selected surface is `57` case-age views: five ages for `C-HI`,
`C-LO`, and `G-LO`, four for `G-HI`, and `0/45/90 deg`. `G-HI/50` is excluded
by construction. The native 3D shock mask remains a later, decision-gated
extension after this join is reviewed.

Focused local validation passed (`24` tests), as did local/remote wrapper
syntax, staged hashes, runtime imports, canonical-source readability, and the
no-overwrite contract.

One complete PBS job was submitted:

```text
789776.kunanyi-ohpc / dual_energy
normal / Q
select=1:ncpus=2:mpiprocs=1:mem=128gb
walltime=08:00:00
```

The job runs two case processes at a time in two waves, reflecting the measured
Goal 064 memory boundary while preserving the complete scientific surface.
Only compact products and logs will be archived. No polling follows the queued
state proof.

## Completion and pressure-only repair

PBS `789776.kunanyi-ohpc` completed `F/0` in `04:02:12`. The retrieved compact
archive contains all `57` intended case-age views, has SHA-256
`1bb57358da88c328c0b34bbdd88aeb8c31f7b9a2f5899c5249bcbb0305730a9f`,
and is accompanied by empty stderr and a remote validation marker.

The first local join exposed a numerical, not physical, failure: the original
`0.03` first-difference penalty over-smoothed the high-contrast `G-HI`
temperature numerator, yielding fit residuals near `0.47` and false near-zero
pressures. Those joined tables are labelled diagnostic-invalid. The stable
`1e-6` penalty and explicit shared-support interpolation passed `27` focused
tests and the all-view sensitivity gate.

Pressure-only repair `789809.kunanyi-ohpc` / `dual_enfix` was verified queued
on `normal` with one CPU, `16gb`, and one hour. It reuses the completed X-ray
maps; it does not reread HDF5 or rerun XRAiSE. No polling follows the queued
state proof.

Status: `submitted_waiting_pressure_repair_completion`.

## Repair completion and scientific decision

PBS `789809.kunanyi-ohpc` completed `F/0` in `00:02:48`. Its compact repaired
archive has SHA-256
`1f540882174ab2a705a07fe830c450ca54e7b497f7e16ae75498c5cce640cf59`,
remote stderr is empty, and remote validation passed all `57` views with a
maximum reconstruction residual of `1.651e-4` and at most one interpolated
shell per view.

The rebuilt local audit contains `37` usable X-ray views and `20` topology
failures. In the primary method, pressure recovery is within a factor of two
for `36/37` usable views, but both volume and native lobe-enthalpy recovery are
within that band for only `5/37`. Median native-lobe recovery is `0.1076`,
`6.762`, `0.0363`, and `0.4559` for `C-HI`, `C-LO`, `G-HI`, and `G-LO`.

The selected-age proof therefore identifies X-ray geometry/topology, not
pressure inference, as the dominant lobe-enthalpy bias. Ratios to the whole
outburst remain descriptive because shock fraction, boundary flux, and the
`C-LO` no-jet correction are unresolved.

Status: `complete_selected_age_proof`. Next recommended tranche: calculate
the prespecified selected-age native 3D shock partition before deciding
whether an annual observer extension is scientifically warranted.
