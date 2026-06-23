# Log: Goal 012 C-HI Final 90-Degree Viewing-Angle Broadening

## 2026-06-23 - orchestrator launch packet

X-ray Cavities accepted Goal 011 as a `complete_product` and published commit
`bc2fe4e`, adding the final `C-HI`, `45 deg` projection-sensitivity product.

Accepted Goal 011 evidence:

- science note:
  `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`;
- asset bundle:
  `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/`;
- remote job `699815.kunanyi-ohpc` completed with `Exit_status=0`;
- focused validation passed with `7 passed`, PBS syntax, JSON parsing, CSV row
  checks, and `git diff --check`;
- headline ratios:
  - corrected X-ray pixel-sum diagnostic `45/0 = 0.44636214774306926`;
  - corrected X-ray max `45/0 = 0.11475003428628802`.

Orchestrator decision: open the final member of the first viewing-angle trio as
final `C-HI`, `90 deg`, post-processing-only. This is intentionally one new
viewing angle at one endpoint, not a source-age sweep, `C-LO`, `G-LO`, new
PLUTO production run, or broader comparison case.

Action repo state at packet creation:

```text
git fetch --prune origin

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
bc2fe4e

git rev-parse --short origin/main
bc2fe4e
```

`jet` must wake X-ray Cavities when complete, blocked, or after any required PBS
job is submitted and verified queued/running.

## 2026-06-23 - jet start state

Start state after the requested sync:

```text
cd /Users/bwbrook/papers/xray_cavities
git fetch --prune origin
git merge --ff-only origin/main
Already up to date.

pwd
/Users/bwbrook/papers/xray_cavities

git status --short --branch
## main...origin/main

git rev-parse --short HEAD
72b6d05
```

Repo-local `AGENTS.md` and the Goal 012 packet were read before project work.
The worktree was clean at start.

## 2026-06-23 - evidence read and path decision

Read the required Goal 012 evidence inside the repo, including:

- `README.md`
- `docs/exchange/current_status.md`
- `docs/goals/011-c-hi-final-45deg-viewing-angle-broadening/Log.md`
- `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/final_45deg_viewing_angle_metadata.json`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/viewing_angle_comparison.csv`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/projection_metrics.csv`
- `docs/science/assets/c_hi_final_45deg_viewing_angle_broadening_2026-06-23/cavity_energy_convention.csv`
- `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/xraise_grid/xraise_grid_smoke_summary.csv`
- `docs/science/c_hi_level3_broadening_decision_packet_2026-06-18.md`
- `agent_comms/threads/2026-06-18-c-hi-level3-broadening-decision.md`
- `docs/Honours_Research_Plan.md`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`

Decision basis confirmed:

- Goal 011 is accepted as `complete_product` and supplies the final `45 deg`
  comparator.
- The Meeting 2 action plan defines `0`, `45`, and `90 deg` as
  post-processing choices only.
- No local committed `90 deg` final endpoint assets exist under
  `docs/science/assets/`.
- The existing `scripts/science/xraise_grid_smoke.py` projection machinery is
  generic for nonzero view angles and can be reused for `90 deg`.

Path decision: a real final `90 deg` X-ray/tracer product requires bounded
full-grid post-processing on the existing final HDF5 output. Goal 012 should
therefore stage and submit a one-node Kunanyi post-processing job, then stop in
`submitted_waiting_pbs_completion` after queued/running verification. If
Kunanyi access cannot be established, stop with a concrete access blocker.

## 2026-06-23 - local preparation and validation

Changed:

- `scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs`
  - bounded final-endpoint `90 deg` post-processing wrapper;
  - reuses the accepted XRAiSE grid projection helper and cavity stub;
  - writes to Goal 012 stage/output paths only.

Local validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py -q
...                                                                      [100%]
3 passed in 0.49s

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

## 2026-06-23 - remote access blocker

Attempted the repo-local Kunanyi helper to create the Goal 012 stage directory:

```bash
scripts/kunanyi/run_on_kunanyi.sh 'hostname; pwd; mkdir -p /u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle'
```

It failed at the TPAC jumpbox selector boundary:

```text
MFA check failed.  Please login and activate SSH access via the web portal again.
MFA check failed. Open the TPAC jumpbox SSH window and retry.
```

Exit code: `124`.

Final status for this turn:

```text
blocked_jumpbox_selector_expired
```

Next action required: X-ray Cavities should refresh the TPAC Open OnDemand
5-minute "Enable Jumpbox SSH" selector through the authorized Chrome route, then
resume Goal 012 from this dirty local state to stage and submit the bounded PBS
job. No remote staging, PBS submission, new PLUTO production, source-age sweep,
`C-LO`, `G-LO`, comparison-case processing, scientific-default change, commit,
or push occurred.

## 2026-06-23 - staged and submitted after selector refresh

After X-ray Cavities refreshed the TPAC Open OnDemand jumpbox selector through
the authorized Chrome route, staged the three required files to:

```text
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle
```

Remote staged SHA-256 checks passed:

```text
xraise_grid_smoke.py: OK
pluto_h5_cavity_stub_extract.c: OK
c_hi_final_90deg_viewing_angle_broadening.pbs: OK
```

Remote wrapper syntax:

```text
bash -n c_hi_final_90deg_viewing_angle_broadening.pbs
<no output>
```

Submitted exactly one bounded PBS job and verified it was running:

```text
job_id=699822.kunanyi-ohpc
Job_Name = c_hi_xcav90
job_state = R
queue = normal
ctime = Tue Jun 23 23:15:06 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
```

Expected outputs:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening/xraise_grid_90deg/
/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening/cavity_stub/
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
```

Stopped immediately after running-state verification per the PBS stop rule. No
polling occurred.

## 2026-06-23 - completion email received but retrieval blocked

Barry reported the PBS completion email for `699822.kunanyi-ohpc`:

```text
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

The helper failed before any remote command ran because the TPAC jumpbox
selector window had expired:

```text
MFA check failed.  Please login and activate SSH access via the web portal again.
MFA check failed. Open the TPAC jumpbox SSH window and retry.
```

Exit code: `124`.

No archive, stdout, or stderr retrieval occurred in this continuation. No
remote finalizer, new PBS submission, new PLUTO production, source-age sweep,
`C-LO`, `G-LO`, comparison-case processing, broad batch, scientific-default
change, commit, push, or cleanup occurred.

Final status for this turn:

```text
blocked_retrieval_jumpbox_selector_expired
```

Next action required: X-ray Cavities should refresh the TPAC Open OnDemand
5-minute "Enable Jumpbox SSH" selector through the authorized Chrome route,
then resume retrieval of the existing completed compact outputs only.

## 2026-06-23 - retrieval and local product package

After X-ray Cavities refreshed the authorized Chrome/Open OnDemand selector,
retrieval resumed from the dirty Goal 012 state. Remote completion evidence was
confirmed with `qstat -x -f 699822.kunanyi-ohpc`:

```text
Job_Name = c_hi_xcav90
resources_used.cpupercent = 89
resources_used.cput = 00:12:10
resources_used.mem = 1288828kb
resources_used.ncpus = 1
resources_used.vmem = 1682044kb
resources_used.walltime = 00:16:34
job_state = F
queue = normal
ctime = Tue Jun 23 23:15:06 2026
mtime = Tue Jun 23 23:31:40 2026
Resource_List.select = 1:ncpus=1:mpiprocs=1:mem=96gb
Resource_List.walltime = 06:00:00
etime = Tue Jun 23 23:15:06 2026
Exit_status = 0
```

Retrieved the existing compact outputs only:

```text
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/c_hi_final_90deg_viewing_angle_broadening.out
/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle/c_hi_final_90deg_viewing_angle_broadening.err
```

Local retrieval targets:

```text
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.out
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/remote_logs/c_hi_final_90deg_viewing_angle_broadening.err
```

Retrieved checksums:

```text
0a27e7ad51d91a930ec5f1e853265093ec4bf59915bc4c172be8e7fba7150d6f  final_90deg_viewing_angle_broadening_2026-06-23.tar.gz
709e5e2f0c42eb70e63264d6bb00a63ffab57466a69d9b980cfda62614b536f9  c_hi_final_90deg_viewing_angle_broadening.out
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  c_hi_final_90deg_viewing_angle_broadening.err
```

Remote stdout markers:

```text
jobid=699822.kunanyi-ohpc
stage_dir=/u/bwbrook/codex_kunanyi/goal012_c_hi_final_90deg_viewing_angle
analysis_root=/scratch/bwbrook/xray_cavities_analysis/2026-06-23-c-hi-final-90deg-viewing-angle-broadening
input_h5=/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5
timestep=Timestep_51
view_angle_deg=90
hdf5_preflight=passed shape_nz_ny_nx=(1014, 960, 960) time_code=15330.069689399999
xray_90deg_validation=passed
cavity_validation=passed
finished_utc=2026-06-23T13:31:40Z
```

Remote stderr is zero bytes.

Extracted the archive locally, excluding the fetched compiled cavity helper
binary, and packaged the complete local review product:

```text
docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md
docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/
scripts/science/build_final_90deg_viewing_angle_broadening.py
tests/test_final_90deg_viewing_angle_broadening.py
```

Primary generated assets:

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

The fetched `cavity_stub/cavity_ellipse_boundary_0deg.tsv` is retained as
remote provenance only. The packaged 90-degree figure uses
`cavity_stub/cavity_ellipse_boundary_90deg.tsv`, projected locally from the 3D
cavity summary rows.

Headline comparison:

```text
corrected_xray_max 90/0 = 0.16054725535740694
corrected_xray_pixel_sum 90/0 = 0.6312514030682306
corrected_xray_max 90/45 = 1.3991042038110435
corrected_xray_pixel_sum 90/45 = 1.4142135623730925
```

Carried-forward bipolar cavity energy convention:

```text
pV = 6.87805393912703e59 erg
adopted 2.5pV = 1.7195134847817575e60 erg
4pV = 2.751221575650812e60 erg
```

Preserved caveats:

- projection-sensitivity probe, not publication-ready observables;
- X-ray topology remains a connected-envelope/single-lobe caveat pending later
  X-ray-based cavity fitting;
- sparse particle-binned radio remains diagnostic, not a validated radio
  observable;
- Level 3 gravitational energy remains `blocked_missing_potential`;
- `pV`, adopted `2.5pV`, and `4pV` are carried with `2.5pV` as the
  non-relativistic interpretation.

No new PBS job, remote finalizer, new PLUTO production, source-age sweep,
`C-LO`, `G-LO`, comparison-case processing, broad batch work,
scientific-default change, commit, push, or cleanup outside Goal 012 files
occurred during retrieval/package.

Focused validation:

```text
uv run pytest tests/test_xraise_grid_smoke_projection.py tests/test_final_90deg_viewing_angle_broadening.py -q
.......                                                                  [100%]
7 passed in 2.05s

bash -n scripts/kunanyi/c_hi_final_90deg_viewing_angle_broadening.pbs
<no output>

uv run python -m json.tool docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23/final_90deg_viewing_angle_metadata.json
passed

uv run python - <<'PY'
import csv
from pathlib import Path
asset = Path('docs/science/assets/c_hi_final_90deg_viewing_angle_broadening_2026-06-23')
for name in [
    'viewing_angle_comparison.csv',
    'viewing_angle_trio_comparison.csv',
    'projection_metrics.csv',
    'cavity_energy_convention.csv',
    'product_provenance.csv',
    'xraise_grid_90deg/xraise_grid_smoke_summary.csv',
    'cavity_stub/cavity_stub_summary.csv',
]:
    rows = list(csv.DictReader((asset / name).open()))
    if not rows:
        raise SystemExit(f'{name}: no rows')
    print(f'{name}_rows={len(rows)}')
PY
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

Final status:

```text
complete_product
```
