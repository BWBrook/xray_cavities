# C-HI Late Source-Age Pilot Failure Closeout

Date: 2026-07-01

## Scope

This note closes out the failed Goal 019 submission for PBS job
`706130.kunanyi-ohpc`. It is a retrieval and diagnosis note only. It does not
authorize a rerun, finalizer, source-age substitution, endpoint rerun, or any
broader science expansion.

## Evidence

Retrieved failure bundle:

```text
docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/
```

Key files:

- `remote_logs/qstat_listing_706130.txt`
- `remote_logs/qstat_706130_excerpt.txt`
- `remote_logs/c_hi_late_source_age_pilot.out`
- `remote_logs/c_hi_late_source_age_pilot.err`
- `remote_logs/c_hi_late_source_age_pilot_2026-06-30.tar.gz`
- `failure_summary.json`
- `failure_summary.csv`
- `partial_output_inventory.csv`
- `remote_file_checksums.csv`

Qstat evidence:

```text
PBS Job Id: 706130.kunanyi-ohpc
Job_Name = c_hi_lsapil
job_state = F
resources_used.cput = 00:36:52
resources_used.mem = 1338348kb
resources_used.walltime = 00:49:52
Stageout_status = 1
Exit_status = 1
```

Retrieved archive SHA-256:

```text
ad3863ca7e0d249a566b246da6927cf7677db5ab5182b51d6b7e88188b84e60f
```

The archive is locally readable with `tar -tzf` and contains the expected
compact products for all six planned source-age/view combinations.

## Diagnosis

The first observed failure point is the archive step, after all intended view
products had already passed wrapper validation.

Remote stderr:

```text
tar: 2026-06-30-c-hi-late-source-age-pilot/remote_logs: file changed as we read it
tar: 2026-06-30-c-hi-late-source-age-pilot/output0049_Timestep_49: file changed as we read it
```

The wrapper uses `set -euo pipefail`, so GNU `tar` returning nonzero on
changed live-directory metadata caused the PBS job to exit with status `1`.
The likely mechanism is that the wrapper archived the analysis root while
`tee`-managed logs and recently written output directories were still being
updated.

This is not currently evidence for a missing HDF5 input, missing XRAiSE table,
HDF5 shape mismatch, projection-bin failure, or failed X-ray product
validation.

## Partial Product Inventory

All six expected validation markers are present:

| Output | Timestep | View | Accumulator | Validation |
| ---: | --- | --- | --- | --- |
| `46` | `Timestep_46` | `0deg` | `direct_y_axis_sum` | passed |
| `46` | `Timestep_46` | `45deg` | `edge_overlap_uniform_cell_projection` | passed |
| `46` | `Timestep_46` | `90deg` | `edge_overlap_uniform_cell_projection` | passed |
| `49` | `Timestep_49` | `0deg` | `direct_y_axis_sum` | passed |
| `49` | `Timestep_49` | `45deg` | `edge_overlap_uniform_cell_projection` | passed |
| `49` | `Timestep_49` | `90deg` | `edge_overlap_uniform_cell_projection` | passed |

Each row in `partial_output_inventory.csv` also has the required archive files
present. Because the scheduler and wrapper still report nonzero status, this
should remain a failure closeout rather than an accepted Goal 019 science
product until X-ray Cavities reviews the evidence and authorizes the next
repair step.

## Recommendation

Do not rerun the HDF5/XRAiSE projections first. The smallest safe next step is
a narrow wrapper/package repair:

1. Patch `scripts/kunanyi/c_hi_late_source_age_pilot.pbs` so archive creation
   cannot fail because live logs or directory metadata change while `tar` is
   reading. Options include archiving only an explicit stable manifest,
   excluding live `remote_logs`, or closing/snapshotting logs before `tar`.
2. Add a focused wrapper-contract test that checks the archive step avoids live
   log races.
3. If X-ray Cavities wants a clean remote closeout without recomputing maps,
   authorize a tiny no-rerun finalizer/repackaging step against the existing
   `/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot`
   outputs. Otherwise, review the retrieved archive locally and decide whether
   the existing products can be accepted with the archive-step caveat.

Do not broaden to other source ages, endpoint reruns, comparison cases,
radio/PRAiSE/cavity regeneration, or production simulation work from this
failure closeout.
