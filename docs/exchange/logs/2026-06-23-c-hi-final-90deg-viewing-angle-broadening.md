# C-HI Final 90-Degree Viewing-Angle Broadening

Date: 2026-06-23
Agent: `jet`
Goal: `012-c-hi-final-90deg-viewing-angle-broadening`
Status: `complete_product`

## Summary

Goal 012 now has a complete compact local package for the final `C-HI`,
`90 deg` viewing-angle product and a reviewer-facing `0/45/90 deg` comparison
against the accepted Goal 005 `0 deg` and Goal 011 `45 deg` products.

This remains a single-viewing-angle post-processing goal. No new PLUTO
production run, source-age sweep, `C-LO`, `G-LO`, comparison-case processing,
broad view/snapshot batch, scientific-default change, commit, or push occurred.

## Local Preparation

Changed local file:

```text
scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
```

The wrapper uses:

```text
stage: /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle
analysis: /scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening
input: /scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
timestep: Timestep_51
view_angle_deg: 90
```

Expected archive after a successful future run:

```text
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Expected compact output directories:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening/xraise_grid_90deg/
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening/cavity_stub/
```

## Validation

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py -q
3 passed

bash -n scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
<no output>

git diff --check
<no output>
```

Local SHA-256 values:

```text
551bf8b0ab49b1d996eef2384239d221a430566125274df7e8979bd0dc29ec13  scripts/science/xraise_grid_smoke.py
46ae0502715ef21a8977647dd9a0f3a0f517bd3e0afd629864705defeb400fd7  scripts/science/pluto_h5_cavity_stub_extract.c
9592b8b8eeaa49586f9f076266427ef2c8c6a3da5419d76e03b5b0c712bcc778  scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
```

## Blocker

Remote helper probe:

```bash
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; mkdir -p /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle'
```

Result:

```text
MFA check failed.  Please login and activate SSH access via the web portal again.
MFA check failed. Open the TPAC jumpbox SSH window and retry.
```

Exit code: `124`.

## Resume

X-ray Cavities should refresh the TPAC Open OnDemand 5-minute "Enable Jumpbox
SSH" selector through the authorized Chrome route. Then resume Goal 012 from
this dirty local state to:

1. stage `xraise_grid_smoke.py`,
   `pluto_h5_cavity_stub_extract.c`, and
   `c_hi_final_90deg_viewing_angle_broadening.pbs`;
2. verify remote hashes and wrapper syntax;
3. submit the bounded PBS job;
4. verify queued/running state;
5. wake X-ray Cavities with job id, queue state, expected outputs, and current
   git status;
6. stop without polling.

No remote staging, PBS submission, commits, or pushes occurred in this blocked
attempt.

## Submission After Selector Refresh

After X-ray Cavities refreshed the TPAC Open OnDemand selector, the three
required files were staged to:

```text
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle
```

Remote staged SHA-256 checks passed:

```text
xraise_grid_smoke.py: OK
pluto_h5_cavity_stub_extract.c: OK
c_hi_final_90deg_viewing_angle_broadening.pbs: OK
```

Remote wrapper syntax passed:

```text
bash -n c_hi_final_90deg_viewing_angle_broadening.pbs
<no output>
```

Submitted PBS job:

```text
job_id=699822.kunanyi-ohpc
Job_Name = c_hi_xcav90
job_state = R
queue = normal
ctime = Tue Jun 23 23:15:06 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

Stopped immediately after running-state verification, per the PBS stop rule.

## Completion Email And Retrieval Blocker

Barry reported the PBS completion email:

```text
PBS Job Id: 699822.kunanyi-ohpc
Job Name:   c_hi_xcav90
Execution terminated
Exit_status=0
resources_used.cpupercent=89
resources_used.cput=00:12:10
resources_used.mem=1288828kb
resources_used.ncpus=1
resources_used.vmem=1682044kb
resources_used.walltime=00:16:34
```

Attempted the requested remote completion check:

```bash
scripts/kunanyi/run_on_kunanyi.sh 'qstat -x -f 699822.kunanyi-ohpc | egrep "Job_Name|job_state|Exit_status|resources_used|Resource_List.select|Resource_List.walltime|queue =|ctime|mtime|etime"'
```

The helper failed at the TPAC jumpbox selector boundary before any remote
command ran:

```text
MFA check failed.  Please login and activate SSH access via the web portal again.
MFA check failed. Open the TPAC jumpbox SSH window and retry.
```

Exit code: `124`.

No archive, stdout, or stderr retrieval occurred in this continuation.

## Retrieval Resume

X-ray Cavities should refresh the TPAC Open OnDemand 5-minute "Enable Jumpbox
SSH" selector through the authorized Chrome route, then resume retrieval only:

```bash
scripts/kunanyi/fetch_from_kunanyi.sh \
  /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz \
  docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
scripts/kunanyi/fetch_from_kunanyi.sh \
  /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/c_hi_final_90deg_viewing_angle_broadening.out \
  docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.out
scripts/kunanyi/fetch_from_kunanyi.sh \
  /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/c_hi_final_90deg_viewing_angle_broadening.err \
  docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.err
```

Then package the local `90 deg` product and `0/45/90 deg` comparison.

## Complete Retrieval And Package

After a further authorized Chrome/Open OnDemand selector refresh, remote
completion evidence for `699822.kunanyi-ohpc` was confirmed:

```text
Job_Name = c_hi_xcav90
job_state = F
queue = normal
Exit_status = 0
resources_used.cpupercent = 89
resources_used.cput = 00:12:10
resources_used.mem = 1288828kb
resources_used.ncpus = 1
resources_used.vmem = 1682044kb
resources_used.walltime = 00:16:34
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

Retrieved compact products:

```text
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.out
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.err
```

Archive SHA-256:

```text
0a27e7ad51d91a930ec5f1e853265093ec4bf59915bc4c172be8e7fba7150d6f
```

Remote stdout markers:

```text
hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960) time_code=15330.069689399999
xray_90deg_validation=passed
cavity_validation=passed
finished_utc=2026-06-23T13:31:40Z
```

Remote stderr is zero bytes.

Local product:

```text
docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/
```

Primary local assets:

```text
c_hi_final_90deg_viewing_angle_broadening.png
viewing_angle_comparison.csv
viewing_angle_trio_comparison.csv
projection_metrics.csv
cavity_energy_convention.csv
product_provenance.csv
final_90deg_viewing_angle_metadata.json
cavity_stub/cavity_ellipse_boundary_90deg.tsv
```

Headline `0/45/90 deg` comparison:

```text
corrected_xray_max 45/0 = 0.11475003428628802
corrected_xray_max 90/0 = 0.16054725535740694
corrected_xray_max 90/45 = 1.3991042038110435
corrected_xray_pixel_sum 45/0 = 0.44636214774306926
corrected_xray_pixel_sum 90/0 = 0.6312514030682306
corrected_xray_pixel_sum 90/45 = 1.4142135623730925
```

Validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py tests/test_final_90deg_viewing_angle_broadening.py -q
7 passed

bash -n scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
<no output>

uv run python -m json.tool docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/final_90deg_viewing_angle_metadata.json
passed

CSV parse checks:
viewing_angle_comparison.csv_rows=6
viewing_angle_trio_comparison.csv_rows=6
projection_metrics.csv_rows=2
cavity_energy_convention.csv_rows=3
product_provenance.csv_rows=11
xraise_grid_90deg/xraise_grid_smoke_summary.csv_rows=9
cavity_stub/cavity_stub_summary.csv_rows=2

git diff --check
<no output>
```

The fetched `cavity_stub/cavity_ellipse_boundary_0deg.tsv` is retained as
remote provenance only; the packaged figure uses a locally projected
`cavity_stub/cavity_ellipse_boundary_90deg.tsv` from the 3D cavity summary
rows.

Preserved caveats:

- projection-sensitivity only, not publication-ready observables;
- connected-envelope/X-ray-topology caveat;
- sparse-radio diagnostic caveat;
- Level 3 gravity remains `blocked_missing_potential`;
- `pV`, adopted `2.5pV`, and `4pV` convention carried forward.

Recommended next step: review/accept Goal 012. If accepted, write a decision
gate before any broadening beyond this completed viewing-angle trio.
