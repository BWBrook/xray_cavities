# C-HI Final 45-Degree Viewing-Angle Broadening

Date: 2026-06-23
Agent: `jet`
Goal: `011-c-hi-final-45deg-viewing-angle-broadening`
Status: `submitted_waiting_pbs_completion`

## Summary

Prepared and submitted the first controlled post-processing-only broadening job
for the accepted final `C-HI` endpoint: one additional viewing angle,
`45 deg`, compared against the accepted final `0 deg` baseline after
completion and retrieval.

This is a bounded post-processing job on the existing final HDF5 output. It is
not a new PLUTO production run, not `90 deg`, not a source-age sweep, not
`C-LO`/`G-LO`, and not a broad viewing-angle batch.

## Local Preparation

Changed local helpers:

- `scripts/science/xraise_grid_smoke.py`
  - added non-default projected-view support with `--view-angle-deg` and
    `--projected-u-bins`;
  - default `0 deg` y-axis projection remains the default path.
- `tests/test_xraise_grid_smoke_projection.py`
  - focused tests for projected-axis support and path-weight conservation.
- `scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs`
  - bounded one-node final-endpoint post-processing wrapper.

Local validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py -q
3 passed

bash -n scripts/kunanyi/c_hi_final_45deg_viewing_angle_broadening.pbs
<no output>

git diff --check
<no output>
```

## Remote Submission

Chrome/Open OnDemand route was used only to enable the TPAC 5-minute SSH
selector. The portal reported an SSH window closing at:

```text
Tue Jun 23 17:52:39 2026
```

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening
```

Staged SHA-256 values:

```text
551bf8b0ab49b1d996eef2384239d221a430566125274df7e8979bd0dc29ec13  xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  pluto_h5_cavity_stub_extract.c
588bbe7c4ae95da4c58039c3b2f971666db8547ca79baaaeeebff92d5c2df204  c_hi_final_45deg_viewing_angle_broadening.pbs
```

Remote wrapper syntax:

```text
bash -n c_hi_final_45deg_viewing_angle_broadening.pbs
<no output>
```

Submitted PBS job:

```text
job_id=699815.kunanyi-ohpc
Job_Name = c_hi_xcav45
job_state = Q
queue = normal
ctime = Tue Jun 23 17:49:18 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

## Expected Outputs

Expected remote archive:

```text
/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Expected remote output directories:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening/xraise_grid_45deg/
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-45deg-viewing-angle-broadening/cavity_stub/
```

Expected compact X-ray/tracer files:

- `xraise_grid_45deg/x_kpc.tsv`
- `xraise_grid_45deg/u_kpc.tsv`
- `xraise_grid_45deg/z_kpc.tsv`
- `xraise_grid_45deg/xray_1kev_raw_mjy_sr.tsv`
- `xraise_grid_45deg/xray_1kev_xraise_corrected_mjy_sr.tsv`
- `xraise_grid_45deg/xray_1kev_correction_ratio.tsv`
- `xraise_grid_45deg/tracer_max_los.tsv`
- `xraise_grid_45deg/xraise_grid_smoke_summary.csv`
- `xraise_grid_45deg/xraise_grid_smoke_metadata.json`

The `cavity_stub/` outputs carry the same tracer-defined 3D cavity protocol and
energy convention as Goal 005. Any final 45-degree visual overlay should project
the cavity geometry to the 45-degree sky plane during the local packaging
resume; do not treat the extractor's `cavity_ellipse_boundary_0deg.tsv` as a
45-degree boundary.

## Resume Instructions

Do not poll the job before Barry reports the PBS completion email or X-ray
Cavities explicitly asks for a re-check.

After completion is authorized, retrieve compact outputs with the repo-local
helper, for example:

```bash
scripts/kunanyi/fetch_from_kunanyi.sh \
  /u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz \
  docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/remote_logs/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Then package the local comparison product against the accepted Goal 005/007
`0 deg` baseline, preserving topology, radio-diagnostic, Level 3 gravity, and
`pV`/`2.5pV`/`4pV` caveats.

## Boundary

No new PLUTO production simulation, `90 deg` view, source-age sweep, `C-LO`,
`G-LO`, broad batch, multi-day production commitment, commits, or pushes
occurred. The PBS stop rule was invoked immediately after queued-state
verification.

## Completion Resume

Barry reported the PBS completion email for `699815.kunanyi-ohpc`:

```text
Exit_status=0
resources_used.walltime=00:16:46
resources_used.cput=00:11:32
resources_used.mem=1260168kb
```

The existing terminal helper route retrieved the completed archive and stage
stdout/stderr from:

```text
/u/bwbrook/codex_kunanyi/goal011_c_hi_final_45deg_viewing_angle
```

Local fetched archive:

```text
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/remote_logs/final_45deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Archive SHA-256 recorded in remote stdout:

```text
fbf5102046b103e2777c8e29b85eee08dc5f5ff028196e5f6bcb73dc48f0ee20
```

Remote stdout markers:

```text
hdf5_preflight=passed
xray_45deg_validation=passed
cavity_validation=passed
finished_utc=2026-06-23T08:06:05Z
```

Remote stderr is zero bytes.

Local closeout package:

```text
docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md
docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/
```

The package includes:

- `c_hi_final_45deg_viewing_angle_broadening.png`
- `viewing_angle_comparison.csv`
- `projection_metrics.csv`
- `cavity_energy_convention.csv`
- `product_provenance.csv`
- `final_45deg_viewing_angle_metadata.json`
- `cavity_stub/cavity_ellipse_boundary_45deg.tsv`

Packaging note: the fetched `cavity_ellipse_boundary_0deg.tsv` was retained as
provenance only. The review figure uses a locally projected 45-degree boundary
derived from the 3D cavity summary rows.

Status after resume:

```text
complete_product
```
