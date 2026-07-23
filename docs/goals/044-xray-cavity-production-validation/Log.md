# Goal 044 Log - X-ray Cavity Production Validation

## 2026-07-23 Local implementation

Status: `local_validation_ready_remote_replay_pending`.

Patrick-agent's `Q-021` request is implemented as a production-CLI validation,
not a replacement scientific analysis. The projector now supports explicit
`auto`, `direct_axis`, and `edge_overlap` modes. `auto` preserves the accepted
legacy contract: direct y-axis integration at zero degrees and edge-overlap
projection otherwise. `direct_axis` adds the independent x-axis integration
at exactly 90 degrees.

The validation helper creates two small PLUTO-schema fixtures with nonuniform
x/y/z axes and predeclares ten fail-closed acceptance gates before XRAiSE is
run. The PBS wrapper runs all requested synthetic angles twice, replays the
accepted real C-HI endpoint, repeats the real edge-overlap 90-degree product,
and archives compact validation evidence only.

Focused local validation:

```text
uv run pytest tests/test_xray_cavity_production_validation_wrapper.py \
  tests/test_xray_cavity_production_validation.py \
  tests/test_xraise_grid_smoke_projection.py \
  tests/test_three_case_cavity_recovery.py -q
30 passed in 0.79s

bash -n scripts/kunanyi/xray_cavity_production_validation.pbs
passed
```

No remote staging, PBS submission, product claim, lifecycle action, PLUTO run,
commit, or push had occurred at that checkpoint.

## 2026-07-23 Remote preflight and submission

Status: `submitted_waiting_pbs_completion`.

The six-file remote stage was created at:

```text
/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation
```

Remote SHA-256 verification matched the local files:

```text
9759dd270077ea04843c250024f87469b9d634300faa0ef4d53083a5102835c2  build_three_case_cavity_recovery.py
7db67dbf7efcf6a8ad5ac7a1ebc04a89776b89e7b8d3d3b4adafc488854bd1f3  three_case_cavity_recovery.py
6082368d589b3772769c1d84ec768f772034d3f187cddd01139460443fbc0dad  tracer_shell_pressure_context.csv
388f2eb5ba41ea2616ebc2e11ff300ab53be96c3b43e9b8988a029b5c44e4cc6  validate_xray_cavity_production.py
dd604ca957bca70253db57ee51607fe6908950127d6e50eb151c1833aca57714  xraise_grid_smoke.py
c5eeee835a0f37e3be92ba05d12da4e7adaf6ba5a4111e3a2da9128a3cad7b1b  xray_cavity_production_validation.pbs
```

Remote wrapper syntax, XRAiSE runtime access, accepted C-HI endpoint HDF5
access, queue availability, and no-overwrite target checks passed. The real
endpoint is:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5::Timestep_51
```

Exactly one PBS job was submitted and verified queued:

```text
job_id=775513.kunanyi-ohpc
Job_Name=xcav_valid
job_state=Q
queue=normal
qtime=Thu Jul 23 11:00:51 2026
Resource_List.select=1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime=08:00:00
```

Expected outputs:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-07-23-xray-cavity-production-validation
/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation/xray_cavity_production_validation_2026-07-23.tar.gz
/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation/xray_cavity_production_validation.out
/u/bwbrook/codex_kunanyi/goal044_xray_cavity_production_validation/xray_cavity_production_validation.err
```

The PBS stop rule was invoked immediately after queued-state verification. No
polling, retrieval, product acceptance, lifecycle deletion, PLUTO run, commit,
or push followed submission.

## 2026-07-23 Failed-closed completion review

Status: `failed_closed_recovery_method_refinement_required`.

Barry reported job `775513.kunanyi-ohpc` completed with `Exit_status=1`.
Read-only qstat and compact retrieval confirmed:

```text
job_state=F
Exit_status=1
Stageout_status=1
resources_used.walltime=00:32:35
resources_used.cput=00:25:23
resources_used.mem=1303676kb
```

Stdout records every requested synthetic and real XRAiSE invocation as passed,
followed by `validation_status=fail passed_gates=7/10`. Stderr contains only
`X-ray cavity production validation failed closed`.

Gate outcome:

```text
pass  fixture_schema
pass  physical_flux_conservation
pass  native_axis_equivalence
pass  near_90_continuity
pass  projected_occupancy
fail  synthetic_cavity_recovery
fail  real_endpoint_recovery
fail  energy_convention
pass  determinism
pass  provenance
```

The synthetic recovery gate is a genuine method finding: the production
one-percent X-ray-only core mask is high-purity but does not robustly recover
both known lobes in the asymmetric fixture. The real-endpoint exact-recovery
gate was incorrectly evaluated on different native grids even though the
underlying direct-90 and edge-90 maps agree on a common grid. Zero-energy rows
are downstream of degenerate synthetic fragments.

One focused repair pass changed evidence handling only:

- future nonzero validations archive compact evidence before exiting;
- energy reporting now counts positive rows accurately and verifies exact
  `pV`/`2.5pV`/`4pV` multipliers per component;
- no threshold was relaxed and no XRAiSE or PLUTO rerun was submitted.

Focused validation after the repair:

```text
uv run pytest tests/test_xray_cavity_production_validation_wrapper.py \
  tests/test_xray_cavity_production_validation.py \
  tests/test_xraise_grid_smoke_projection.py \
  tests/test_three_case_cavity_recovery.py -q
31 passed in 0.83s

bash -n scripts/kunanyi/xray_cavity_production_validation.pbs
passed
```

Science note:
`docs/science/xray_cavity_production_validation_2026-07-23.md`.

Retrieved evidence:
`docs/science/assets/xray_cavity_production_validation_2026-07-23/`.
