# Goal 044 X-ray Cavity Production Validation

Date: 2026-07-23
Status: `failed_closed`
Decision label: `XRAY_CAVITY_PRODUCTION_VALIDATION_FAILED_CLOSED_RECOVERY_METHOD_REFINEMENT_REQUIRED`

## Purpose

Goal 044 implements Patrick-agent's `Q-021` request as a fail-closed
production-pipeline validation using existing simulation evidence only. It
does not reopen PLUTO production or authorize lifecycle deletion.

The pipeline under test is:

```text
PLUTO-schema HDF5 -> XRAiSE -> projection -> corrected X-ray map ->
tracer-blind residual -> cavity mask -> area/volume/energy evidence
```

## Implementation

- Added explicit `auto`, `direct_axis`, and `edge_overlap` projection modes to
  `scripts/science/xraise_grid_smoke.py` while preserving existing defaults.
- Added independent native x-axis integration for an exact 90-degree reference.
- Added two nonuniform production-schema synthetic fixtures, axisymmetric and
  non-axisymmetric.
- Predeclared ten fail-closed acceptance gates covering schema, flux,
  native-axis agreement, near-90-degree continuity, occupancy, synthetic
  recovery, real-endpoint recovery equivalence, energy conventions,
  determinism, and provenance.
- Added a real C-HI endpoint replay with direct 0/90-degree and edge-overlap
  90-degree comparisons on shared physical and colour scales.
- Kept full maps remote; the wrapper archives compact tables, figures,
  criteria, commands, hashes, and metadata.

## Local Verification

```text
uv run pytest tests/test_xray_cavity_production_validation_wrapper.py \
  tests/test_xray_cavity_production_validation.py \
  tests/test_xraise_grid_smoke_projection.py \
  tests/test_three_case_cavity_recovery.py -q
30 passed in 0.79s

bash -n scripts/kunanyi/xray_cavity_production_validation.pbs
passed

python compilation and git diff --check
passed
```

## Remote Preflight

- Stage root:
  `/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation`.
- Analysis root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-production-validation`.
- All six staged files matched local SHA-256 values.
- Remote wrapper syntax passed.
- XRAiSE runtime and the accepted C-HI endpoint HDF5 were readable.
- Stage, analysis, and archive targets passed no-overwrite checks.
- `normal` was enabled and started with sufficient walltime.

## PBS Submission

```text
job_id=775513.kunanyi-ohpc
Job_Name=xcav_valid
job_state=Q
queue=normal
qtime=Thu Jul 23 11:00:51 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime=08:00:00
```

Expected compact archive:

```text
/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation/xray_cavity_production_validation_2026-07-23.tar.gz
```

The PBS stop rule was invoked after queued-state verification. Do not poll.
Resume only after Barry reports the completion email or explicitly requests a
re-check.

## Holds and Caveats

- No scientific pass/fail result is claimed while the job is queued.
- No new PLUTO production, source-age substitution, scientific-default
  change, lifecycle deletion, commit, or push occurred.
- Goal 042 remains a read-only lifecycle packet.
- Goal 043 remains separately reserved for approved lifecycle execution.
- Raw endpoint HDF5 and required X-ray intermediates remain protected until
  the Goal 044 result is retrieved and reviewed.

## Completion and Diagnosis

PBS job `775513.kunanyi-ohpc` ended `F` with `Exit_status=1`, walltime
`00:32:35`, and peak reported memory `1303676kb`. All requested XRAiSE CLI
products completed. The validator then reported:

```text
validation_status=fail passed_gates=7/10
```

Passed gates were fixture schema, physical flux conservation, native-axis
equivalence, near-90-degree continuity, projected occupancy, determinism, and
provenance. Failed gates were synthetic cavity recovery, real-endpoint recovery
equivalence, and energy convention.

The synthetic failure is material: the fixed one-percent physical-area tail
recovered two components in only `6/12` views, despite precision `1.0`. It can
miss the weaker lobe in an asymmetric case and fragment the coarse 45-degree
core. No post-hoc threshold relaxation was used to manufacture a pass.

The real recovery failure is partly a validation-design defect. Direct-90 and
edge-90 maps agree to normalized L1 `8.534190750687258e-11`, but the evaluator
ran recovery on different native horizontal grids, producing `4.35%` area and
`2.36%` volume differences. A valid exact-equivalence test must run both masks
on one conservative common grid.

The energy gate failed because degenerate synthetic fragments produced zero
volumes and energies. The reporting path is patched to state the true positive
count and check exact `1/2.5/4` multipliers per component.

The original wrapper stopped before archiving when validation returned
nonzero. Retrieved validation tables, figure, contracts, command manifest,
stdout, and stderr are preserved under:

```text
docs/science/assets/xray_cavity_production_validation_2026-07-23/failed_run/
```

The wrapper is patched so future failed validations preserve their compact
archive before returning the nonzero status. No XRAiSE or PLUTO rerun was
submitted. Goal 042/043 X-ray-validation holds remain active.
