# 2026-08-31 selected-age native shock-energy partition

Goal 067 implements the selected-age native three-dimensional shock term left
open by Goal 066.

The frozen method uses same-cell production `t=0` subtraction, Stas's fixed
centre-zero initial potential, and a 26-connected ambient entropy-excess
region anchored to the accepted compressed axial shock front. No-jet cluster
and group controls calibrate dimensionless pressure, density, and entropy
thresholds; their coarser resolution precludes cellwise matched subtraction.

The full accepted surface is `C-HI`, `C-LO`, and `G-LO` at
`10/20/30/40/50 Myr`, plus `G-HI` at `10/20/30/40 Myr`, with primary and
half/double threshold treatments. Unresolved side or bilateral masks are
retained explicitly rather than substituted.

Local implementation and wrapper tests are green. Live Kunanyi preflight found
both complete six-snapshot no-jet control series, verified all selected
production HDF5 inputs, staged exact-hash inputs, and passed the remote runtime
and wrapper checks.

The first selected-age job was submitted as:

```text
789812.kunanyi-ohpc / shock_energy
state=Q queue=normal
select=1:ncpus=2:mpiprocs=1:mem=128gb
walltime=48:00:00
```

Status: `submitted_waiting_pbs_completion`. No polling occurred after queued
verification.

Barry then reported an immediate failure. Authorized retrieval showed
`789812` ended `F/2` with zero resource use because Kunanyi's Bash `4.2.46`
does not support the wrapper's single `declare -n` nameref. No scientific
analysis ran.

That non-portable construct was replaced with explicit array-count checks and
covered by a regression test. The failed surfaces remain untouched; the
repair uses fresh `r1` stage, analysis, archive, stdout, and stderr paths.
Local tests passed (`9 passed`), remote hashes and wrapper syntax passed, and
exactly one repaired job was submitted:

```text
789813.kunanyi-ohpc / shock_energy
state=Q queue=normal
select=1:ncpus=2:mpiprocs=1:mem=128gb
walltime=48:00:00
```

Current status: `repair_submitted_waiting_pbs_completion`. The PBS stop rule
is active for `789813`.

Method note:
`docs/science/four_case_selected_age_native_shock_partition_method_2026-08-31.md`.

## Completion and recovery

Barry reported repaired PBS job `789813.kunanyi-ohpc` as `F/1` after
`01:46:45`. The failure was confined to the wrapper's final schema check:
`volume_kpc3` was requested where the frozen product schema uses
`mask_volume_kpc3`. All four case workers had exited `0`, all control and case
metadata were complete, and all `171` required result rows existed.

The validator and regression test were corrected. A no-rerun finalizer then
validated and archived the existing compact output tree using an explicit
file list. The recovered 39-member archive has SHA-256
`1287c74a2a9c2891ba2feb6d641128460f9a546828e2380daed901c40b73182d`.
No production HDF5 input was reopened.

The accepted primary surface contains `19` case-age rows: `15` quantitative
and four late `C-LO` rows that fail closed at the bilateral supersonic-front
gate. The three otherwise well-resolved case series place roughly
`0.58--0.87` of injected energy in the selected shocked-region energy change,
while irreversible heating is roughly `0.17--0.33` of injected energy.
Threshold sensitivity is negligible for `G-HI`, moderate for `C-HI`, and
material for `G-LO` and the single quantitative `C-LO` age.

Joining the shock surface to Goal 066 preserves its observer validity gates.
For jointly quantitative primary rows, median X-ray cavity enthalpy is about
`1.61%`, `0.45%`, and `10.15%` of native shock-region energy for `C-HI`,
`G-HI`, and `G-LO`, respectively. This materially changes the whole-outburst
context but does not overturn Goal 066's conclusion that X-ray recovery of
native lobe enthalpy is primarily geometry/topology limited.

Decision:
`SELECTED_AGE_NATIVE_SHOCK_PARTITION_GREEN_C_LO_LATE_FAIL_CLOSED`.

Status: `complete_product_recovered_no_hdf5_rerun`.

Science note:
`docs/science/four_case_selected_age_native_shock_partition_2026-08-31.md`.
