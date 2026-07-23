# Goal 045 Log - X-ray Cavity Recovery Method Refinement

## 2026-07-23 Method audit and contract freeze

Status: `submitted_waiting_pbs_completion`.

Goal 044 remains an immutable failed-closed production validation. Its map
projection gates are green, but its fixed global one-percent tail mixed a
high-purity deficit-core detector with projected geometry and hybrid energy
estimation. The real direct-90/edge-90 recovery gate also compared masks on
different native grids.

The Goal 045 contract was frozen before evaluation. It replaces post-hoc
global-tail tuning with a tracer-blind, hemisphere-aware seed-and-grow method,
area-weighted truth metrics, smooth-background and one-sided-ablation
controls, explicit geometry resolution, and a third symmetric common grid for
direct/edge recovery equivalence.

The frozen production background is a robust degree-6 two-dimensional
Chebyshev model of log intensity on normalized coordinates, solved by SVD with
fixed lower-outlier clipping. Degree-5/6/7 convergence, condition number, and
blocked spatial cross-validation form a required stability gate. Independent
radial backgrounds, not the fitted polynomial, construct the negative
controls.

The method uses the known bipolar jet axis but not tracer truth. Because that
choice can encourage bilateral detections, the negative controls are required
gates rather than optional diagnostics.

Local results across two fixtures and `direct0`/`edge45`/`edge90`:

- all 12 side-angle recovery rows passed;
- minimum area-weighted precision `1.0`;
- minimum area-weighted IoU `0.79044`;
- maximum centroid error `1.8091 kpc`;
- maximum projected-area error `0.20956`;
- maximum geometric-volume proxy error `0.286441`;
- maximum secondary-fragment fraction `0.0`;
- all expected components resolved;
- smooth null detected zero sides and all 12 one-sided controls detected only
  the retained side; and
- degree-5/6/7 blocked-CV RMSE was
  `0.03816 / 0.03664 / 0.03676`, with all fits converged and maximum condition
  number `248.66`.

The independent integration review found and repaired two non-scientific
defects before submission: the provenance gate now requires hashes for the
synthetic fixture contract and Goal 045 wrapper, and a Python startup failure
now creates a diagnostic surface before failed evidence is archived.

Final local validation:

```text
uv run pytest tests/test_hemisphere_seed_grow_recovery.py \
  tests/test_xray_cavity_recovery_method_refinement.py \
  tests/test_xray_cavity_recovery_method_refinement_wrapper.py \
  tests/test_xray_cavity_production_validation.py \
  tests/test_xray_cavity_production_validation_wrapper.py \
  tests/test_xraise_grid_smoke_projection.py \
  tests/test_three_case_cavity_recovery.py -q
69 passed in 1.07s
```

`bash -n`, Python compilation, and `git diff --check` passed. Remote staged
SHA-256 values matched local files; remote wrapper syntax and Python
compilation passed; Goal 044 source contracts and provenance were readable.

Submitted exactly one evaluation-only PBS job:

```text
job_id=775522.kunanyi-ohpc
Job_Name=xcav_refine
job_state=Q
queue=normal
ctime=Thu Jul 23 14:11:47 2026
select=1:ncpus=1:mpiprocs=1:mem=16gb
walltime=01:00:00
```

The PBS stop rule is active. No polling occurred after queued verification.
No XRAiSE or PLUTO rerun, lifecycle action, commit, or push occurred.

## 2026-07-23 Completion review

Status: `complete_product`.

Barry reported job `775522.kunanyi-ohpc` completed with `Exit_status=0`.
Read-only scheduler verification and direct retrieval confirmed:

```text
job_state=F
Exit_status=0
Stageout_status=1
resources_used.walltime=00:00:30
resources_used.cput=00:00:25
resources_used.mem=1316464kb
```

Stdout reports `validation_status=pass passed_gates=7/7` and stderr is empty.
The retrieved archive SHA-256 is
`462199cc4537cf987556c04961dd807e5a0a465ede40f0af46c1c2f34a4675a1`.
The archive opens and all internal checksums pass.
Its self-referential manifest row records the manifest's pre-write size as
zero, while the completed file and final checksum are correct; this is
retained as a nonmaterial packaging caveat rather than triggering a rerun.

Remote evidence confirms:

- `18/18` background-stability fits converged;
- `12/12` synthetic side-angle recovery rows passed;
- `18/18` independent negative controls passed;
- `3/3` direct-90/edge-90 common-grid comparisons passed;
- `24/24` expected geometries resolved;
- `42/42` energy rows were finite and positive in `14/14` exact multiplier
  groups; and
- all `40` selected map inputs and `9/9` required code/input roles were
  hash-recorded.

Goal 045 is accepted as a green fixture-informed production-pipeline
validation. It resolves the Goal 044 recovery-refinement requirement and the
associated X-ray lifecycle hold, but it does not certify a general
instrument/noise-aware observational method or authorize deletion outside the
separate Goal 042/043 lifecycle contract.

Science note:
`docs/science/xray_cavity_recovery_method_refinement_2026-07-23.md`.

Retrieved evidence:
`docs/science/assets/xray_cavity_recovery_method_refinement_2026-07-23/`.
