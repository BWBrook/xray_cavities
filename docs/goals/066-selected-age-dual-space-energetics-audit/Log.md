# Goal 066 log

## 2026-08-31 - method implemented and full selected-age audit submitted

- Implemented the selected-age proof of the supervisor-approved dual-space
  energetics design. The native and observer ledgers remain independent until
  the final compact join.
- Reused the accepted native fractional-tracer, cell-wise initial-state ledger
  rather than rereading HDF5 for quantities already calculated exactly. Native
  lobe pressure-volume is derived from
  `sum(f p V) = (gamma - 1) E_lobe,thermal`, with `gamma=5/3`.
- Extended the existing XRAiSE projection pass with three observer inputs:
  line-of-sight mass-density-squared, corrected-emissivity temperature
  numerator, and projected emissivity-weighted temperature. Tracer remains
  present only in the historical projection product and is neither loaded nor
  used by the new pressure/cavity builder.
- Added a spherical non-negative deprojection of density-squared, corrected
  X-ray emissivity, and temperature-weighted emissivity. The X-ray-only cavity
  mask is excluded from the ambient annular profiles.
- Retained midpoint and ellipsoid-volume-averaged pressure; minor, geometric,
  and major line-of-sight depths; and `2.5pV` and `4pV` conventions.
- Added the post-retrieval join that factorizes lobe-enthalpy recovery into
  volume and pressure recovery and separately reports ratios to native lobe
  enthalpy, retained energy, and injected energy.
- Kept the native 3D shock-energy fraction outside this first proof. It is
  explicitly pending rather than inferred from the closure residual or the
  existing one-dimensional shock diagnostics.
- Selected surface: `C-HI`, `C-LO`, and `G-LO` at `10/20/30/40/50 Myr`, plus
  `G-HI` at `10/20/30/40 Myr`; three views per age, for `57` case-age views.
  `G-HI/50` is excluded by construction.

Local validation:

```text
uv run pytest tests/test_selected_age_dual_space_wrapper.py tests/test_selected_age_dual_space_energetics.py tests/test_xray_pressure_deprojection.py tests/test_xraise_grid_smoke_projection.py -q
24 passed in 0.46s

PYTHONPATH=. uv run pytest tests/test_selected_age_dual_space_wrapper.py tests/test_selected_age_dual_space_energetics.py tests/test_xray_pressure_deprojection.py tests/test_xraise_grid_smoke_projection.py tests/test_four_case_scientific_synthesis.py tests/test_four_case_boundary_spectral_field_review.py tests/test_four_case_cavity_age_method_comparison.py tests/test_snapshot_synthesis.py tests/test_snapshot_inference.py -q
42 passed in 2.88s

bash -n scripts/kunanyi/four_case_selected_age_dual_space_energetics.pbs
passed

git diff --check
passed (existing CRLF-normalization warnings only)
```

Remote staging and preflight:

- Stage root:
  `/u/bwbrook/codex_kunanyi/goal066_selected_age_dual_space_energetics`.
- Analysis root:
  `/u/bwbrook/xray_cavities_analysis/2026-08-31-selected-age-dual-space-energetics`.
- Stage archive SHA-256:
  `a5961134f2a67255e30200f1e1ccc8a5c3f86d544012b0dfabcaa835fe4f3581`.
- All six staged source/wrapper hashes matched; remote wrapper syntax and the
  Anaconda `h5py/numpy/scipy/qmc` imports passed.
- Canonical raw inputs were readable. Two concurrent case processes were
  chosen because the accepted Goal 064 isolated-case peak was about 40 GB,
  while four concurrent cases exhausted a 128 GB request.
- The complete surface is one job with two memory-safe waves, not a sequence
  of exploratory jobs.

PBS submission:

```text
job_id=789776.kunanyi-ohpc
Job_Name=dual_energy
job_state=Q
queue=normal
Resource_List.select=1:ncpus=2:mpiprocs=1:mem=128gb
Resource_List.walltime=08:00:00
qtime=Mon Aug 31 14:29:09 2026
```

Expected completion files:

- archive:
  `/u/bwbrook/codex_kunanyi/goal066_selected_age_dual_space_energetics/four_case_selected_age_dual_space_energetics_2026-08-31.tar.gz`;
- stdout/stderr under the same stage root;
- compact per-case topology, pressure-profile, and X-ray enthalpy tables in
  the archive. The transient X-ray maps remain remote and are not archived.

Status: `submitted_waiting_pbs_completion`.

The PBS stop rule is active. Resume only after Barry reports the completion
email or explicitly authorizes a re-check.

## 2026-08-31 - full projection green; pressure regularization defect isolated and repair submitted

Barry reported successful completion of `789776.kunanyi-ohpc` / `dual_energy`:

```text
Exit_status=0
resources_used.walltime=04:02:12
resources_used.cput=05:57:45
resources_used.mem=2912192kb
resources_used.ncpus=2
```

The final scheduler record is `F/0` with the usual `Stageout_status=1`
caveat. The stage archive, stdout, stderr, and archive file list were present
and retrieved. The archive SHA-256 is
`1bb57358da88c328c0b34bbdd88aeb8c31f7b9a2f5899c5249bcbb0305730a9f`;
it contains `33` compact members. Remote stderr is empty, stdout records
`selected_age_xray_pressure_validation=passed case_age_views=57`, and all four
case processes exited zero.

The first local native/X-ray join passed its algebraic and coverage gates, but
the scientific review found a material numerical defect. The nominal
deprojection regularization `0.03` produced temperature-numerator fit residuals
up to about `0.47` and erased the inferred temperature in high-contrast
`G-HI` shells while density remained finite. This created false pressure and
enthalpy ratios near zero. Those first joined tables are retained only under
`diagnostic_original_regularization/`; they are not an accepted science
product.

A sensitivity review over all `57` views identified `1e-6` as the stable
regularization regime: the maximum three-profile fit residual is below
`2e-4`, and the inferred profiles are stable against weaker penalties. The
repair also treats numerator/emissivity support below `1e-12` of each fitted
maximum as numerically unconstrained and transparently interpolates those
isolated shells. Tests now record directly constrained versus interpolated
temperature shells.

Local repair validation:

```text
uv run pytest tests/test_selected_age_dual_space_wrapper.py tests/test_selected_age_dual_space_energetics.py tests/test_xray_pressure_deprojection.py tests/test_xraise_grid_smoke_projection.py -q
27 passed in 0.61s

bash -n scripts/kunanyi/four_case_selected_age_pressure_repair.pbs
passed

git diff --check
passed (existing CRLF-normalization warnings only)
```

The pressure-only repair reuses the completed projected maps and performs no
HDF5 read or XRAiSE projection rerun. Staged hashes, remote wrapper syntax,
runtime imports, and no-overwrite checks passed. Exactly one repair job was
submitted:

```text
job_id=789809.kunanyi-ohpc
Job_Name=dual_enfix
job_state=Q
queue=normal
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=16gb
Resource_List.walltime=01:00:00
qtime=Mon Aug 31 19:34:20 2026
```

Status: `submitted_waiting_pressure_repair_completion`. The PBS stop rule is
active; do not interpret the dual-space bias surface until the repaired compact
archive is retrieved and the local join is rebuilt.

## 2026-08-31 - pressure repair green and selected-age audit complete

Barry reported completion of `789809.kunanyi-ohpc` / `dual_enfix`. The final
scheduler record is `F/0` with `Stageout_status=1`, walltime `00:02:48`, CPU
time `00:01:25`, and peak memory `174868kb`. Remote stderr is empty.

The repaired pressure archive was retrieved with SHA-256
`1f540882174ab2a705a07fe830c450ca54e7b497f7e16ae75498c5cce640cf59`.
It contains `32` compact members. Remote validation covered all `57`
case-age views, with maximum profile reconstruction residual
`1.651000166245975e-4` and at most one interpolated temperature shell per
view.

The accepted local join contains `19` native case-age rows, `57` observer
case-age-view rows, `37` primary quantitative matches, `20` topology failures,
and `464` rows over all retained method sensitivities. For the primary
geometric-depth, ellipsoid-volume-averaged, `2.5pV` method, pressure recovery
is within a factor of two for `36/37` usable views, while volume and native
lobe-enthalpy recovery are within a factor of two for only `5/37`.

The case-median lobe recoveries are `0.1076` (`C-HI`), `6.762` (`C-LO`),
`0.0363` (`G-HI`), and `0.4559` (`G-LO`). The volume term, together with the
X-ray topology failure surface, therefore dominates the selected-age lobe-
enthalpy bias; the pressure term is secondary. This conclusion is stable to
the retained depth and midpoint-versus-volume-average pressure sensitivities.

Ratios to retained and injected energy remain descriptive rather than final:
the native 3D shock fraction and boundary flux are pending, and `C-LO` remains
background dominated without its no-jet correction.

Science note:
`docs/science/four_case_selected_age_dual_space_energetics_2026-08-31.md`.

Status: `complete_selected_age_proof`. Decision:
`SELECTED_AGE_DUAL_SPACE_PROOF_GREEN_VOLUME_TOPOLOGY_BIAS_DOMINATES`.

Recommended next tranche: selected-age native 3D shock-energy partition with
no-jet controls and threshold sensitivity. Do not expand the observer cadence
unless that result exposes decision-relevant temporal structure.
