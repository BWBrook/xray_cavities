# C-HI Late Source-Age Pilot

Date: 2026-06-30

## Status

Goal 019 is the post-maintenance bounded submission phase for the first
late-source-age `C-HI` pilot.

Current status:

```text
repair_complete_no_rerun_package_ready
```

This phase should stop immediately after one PBS job is verified queued/running
or after a required preflight check blocks submission.

## Target Surface

New source-age samples:

| Output | Timestep | Planned source age | Action |
| ---: | --- | ---: | --- |
| `46` | `Timestep_46` | `~44.999274 Myr` | process `0/45/90 deg` |
| `49` | `Timestep_49` | `~47.999129 Myr` | process `0/45/90 deg` |

Endpoint control:

| Output | Timestep | Source age | Action |
| ---: | --- | ---: | --- |
| `51` | `Timestep_51` | `50.000000 Myr` | preflight only; reuse accepted Goal 005/016 products |

The endpoint is not rerun by default.

## Local Changes

- `scripts/kunanyi/c_hi_late_source_age_pilot.pbs`
- `tests/test_late_source_age_pilot_wrapper.py`
- `docs/goals/019-c-hi-late-source-age-pilot/Log.md`
- `docs/exchange/logs/2026-06-30-c-hi-late-source-age-pilot.md`
- `docs/science/c_hi_late_source_age_pilot_failure_2026-07-01.md`
- `docs/science/c_hi_late_source_age_pilot_repair_2026-07-01.md`
- `docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/`

## Local Validation

Focused tests passed:

```text
uv run pytest tests/test_source_age_sampling_plan.py tests/test_refined_projection_viewing_rerun.py tests/test_xraise_grid_smoke_projection.py tests/test_late_source_age_pilot_wrapper.py -q
13 passed
```

PBS syntax passed:

```text
bash -n scripts/kunanyi/c_hi_late_source_age_pilot.pbs
```

Whitespace passed:

```text
git diff --check
```

## Remote Contract

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot
```

Remote analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot
```

Expected archive after completion:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

The wrapper must preflight HDF5 file presence/readability, timestep presence,
required datasets, and shape consistency before running any products.

For nonzero views the wrapper must validate:

```text
projection.projected_accumulation=edge_overlap_uniform_cell_projection
```

## Remote Evidence

Chrome/Open OnDemand selector was refreshed successfully:

```text
Enable SSH page reached at https://<tpac-host>/pun/sys/enable_ssh/
Visible status: You have a 5.0 min window which closes at Tue Jun 30 20:52:23 2026 to ssh to <tpac-host>.
```

The repo-local helper then reached jumpbox, but the inner `ssh kunanyi` failed
before command execution because the post-maintenance Kunanyi host key no
longer matched the key stored in `/u/bwbrook/.ssh/known_hosts` on jumpbox:

```text
WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED!
The fingerprint for the ED25519 key sent by the remote host is
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI.
Offending ECDSA key in /u/bwbrook/.ssh/known_hosts:2
Host key for kunanyi has changed and you have requested strict checking.
Host key verification failed.
```

No target HDF5 preflight was reached. No files were staged and no PBS job was
submitted.

No remote `known_hosts` edit or host-key bypass was performed during this
initial blocked attempt. X-ray Cavities then decided whether to authorize a
narrow operational repair for the post-maintenance Kunanyi host key before
rerunning the Goal 019 staging and preflight path.

## Authorized Repair And Submission Continuation

Barry/X-ray Cavities accepted the new post-maintenance Kunanyi ED25519
fingerprint:

```text
SHA256:IzXcim01EZc9FMqnrbDIfX9WfFSrK1RMwFq5McL4zpI
```

Operational host-key repair:

- Scanned the ED25519 key through the authorized jumpbox path.
- Verified the scanned SHA-256 fingerprint exactly matched the accepted value
  before editing `known_hosts`.
- Backed up the jumpbox file to
  `/u/bwbrook/.ssh/known_hosts.goal019_pre_kunanyi_repair_20260630T105724Z`
  with SHA-256
  `90c638295e8e9c9461177e954b75fa27f1709087d58e5ab8cd73c030e5c72aa1`.
- Backed up the local Mac file to
  `/Users/bwbrook/.ssh/known_hosts.goal019_pre_kunanyi_repair_20260630T105949Z`
  with SHA-256
  `03287b5ee2099f789222346b05f7f5e08331a998630ab09d315b87a560a5a8ba`.
- Removed and replaced only stale `kunanyi` entries.
- Did not disable strict host-key checking or use a null known-hosts file.

Remote helper smoke after repair:

```text
<tpac-host>
/u/bwbrook
2026-06-30T10:57:37Z
__CODEX_STATUS__=0
```

Staged files and verified hashes:

```text
a7ef3553a18ef79ee7c29fd40f4b3cbc13a6376e7bc45b0152ea004f05232c0c  xraise_grid_smoke.py
468aeaaa07e05a2cc077c089ab9999dced8dd9490a31bd63cfe6a8a2463e5550  c_hi_late_source_age_pilot.pbs
```

Remote preflight passed:

- remote `bash -n c_hi_late_source_age_pilot.pbs`;
- required XRAiSE runtime/table inputs were readable;
- `data.0046.flt.h5::Timestep_46`,
  `data.0049.flt.h5::Timestep_49`, and endpoint-control
  `data.0051.flt.h5::Timestep_51` were readable;
- required datasets `rho`, `prs`, `tr1`, `vx1`, `vx2`, `vx3` were present;
- target shapes were consistent:
  `(1014, 960, 960)`.

PBS job submitted:

```text
PBS Job Id: 706130.kunanyi-ohpc
Job name: c_hi_lsapil
Queue/state: normal/Q
Resources: select=1:ncpus=1:mpiprocs=1:mem=96gb, walltime=04:00:00
Submitted: Tue Jun 30 21:01:36 2026
```

Expected completion archive:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

Expected stdout/stderr:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot.out
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot.err
```

Stop rule is now active: do not poll, retrieve, finalizer-run, or package until
Barry reports the PBS completion email or X-ray Cavities explicitly authorizes
a re-check.

## Failure Closeout

Barry reported the PBS completion email for `706130.kunanyi-ohpc` with
`Exit_status=1`.

Qstat evidence:

```text
Job Id: 706130.kunanyi-ohpc
Job_Name = c_hi_lsapil
job_state = F
resources_used.cpupercent = 98
resources_used.cput = 00:36:52
resources_used.mem = 1338348kb
resources_used.ncpus = 1
resources_used.vmem = 1770104kb
resources_used.walltime = 00:49:52
Stageout_status = 1
Exit_status = 1
```

Retrieved local failure bundle:

```text
docs/science/assets/c_hi_late_source_age_pilot_failure_2026-07-01/
```

New failure note:

```text
docs/science/c_hi_late_source_age_pilot_failure_2026-07-01.md
```

Retrieved files:

```text
remote_logs/qstat_listing_706130.txt
remote_logs/qstat_706130_excerpt.txt
remote_logs/c_hi_late_source_age_pilot.out
remote_logs/c_hi_late_source_age_pilot.err
remote_logs/c_hi_late_source_age_pilot_2026-06-30.tar.gz
failure_summary.json
failure_summary.csv
partial_output_inventory.csv
remote_file_checksums.csv
```

Retrieved checksums:

```text
34b9c1f807c7ba039b6d749caf7e3039cf201ff7baf4cf6348af2c2d061432fc  c_hi_late_source_age_pilot.out
27b2f90d91cd26de321900928de81164a44029836e037a7c039f0ca83fec6d72  c_hi_late_source_age_pilot.err
ad3863ca7e0d249a566b246da6927cf7677db5ab5182b51d6b7e88188b84e60f  c_hi_late_source_age_pilot_2026-06-30.tar.gz
```

First failure:

```text
tar: 2026-06-30-c-hi-late-source-age-pilot/remote_logs: file changed as we read it
tar: 2026-06-30-c-hi-late-source-age-pilot/output0049_Timestep_49: file changed as we read it
```

Diagnosis:

- Remote preflight had passed before job submission.
- The job produced and validated all six intended products:
  `46/0deg`, `46/45deg`, `46/90deg`, `49/0deg`, `49/45deg`, `49/90deg`.
- Nonzero views used `edge_overlap_uniform_cell_projection`.
- Each validation marker reported zero catastrophic empty-column recurrence.
- The archive is readable locally and contains required compact files for all
  six source-age/view products.
- The nonzero exit was caused by archiving a live analysis directory whose logs
  or directory metadata changed while `tar` was reading it.

Recommendation:

- Do not rerun the XRAiSE/HDF5 products first.
- Patch the wrapper archive step to use a stable manifest/snapshot or exclude
  live logs during tar.
- If X-ray Cavities wants a clean remote artifact, authorize only a tiny
  no-rerun finalizer/repackage against the existing analysis root, unless
  review finds the retrieved archive insufficient.

## Boundary Confirmation

- Failure-closeout retrieval and diagnosis were limited to the already-completed
  Goal 019 job.
- Remote staging and exactly one PBS submission occurred after preflight passed.
- No new PBS submission, rerun, finalizer, or polling loop occurred.
- No endpoint rerun.
- No source-age substitution.
- No PLUTO production.
- No early `5/10 Myr` branch.
- No `C-LO`, `G-LO`, comparison-case processing, PRAiSE/radio/cavity
  regeneration, broad batch, 48-hour production commitment, or
  scientific-default change.
- No commits, pushes, cleanup, Stas/Patrick escalation, or `agent_comms`
  changes.
- Accepted Goal 005/011/012/016/017/018 assets were not overwritten.

## Repair Iteration: Archive Race Patch And No-Rerun Repackage

Date: 2026-07-01

Status:

```text
repair_complete_no_rerun_package_ready
```

Scope:

- patched and tested the local Goal 019 wrapper archive contract;
- validated/repackaged only the existing Goal 019 analysis root;
- did not submit PBS or rerun HDF5/XRAiSE products.

Wrapper repair:

- `scripts/kunanyi/c_hi_late_source_age_pilot.pbs` now creates a stable archive
  snapshot containing completed product directories and copied log files.
- The wrapper writes `archive_manifest.tsv`, `archive_checksums.sha256`, and a
  stable file list, then calls `tar` with `--files-from` instead of recursively
  archiving the live analysis root.
- `tests/test_late_source_age_pilot_wrapper.py` was updated to lock this
  archive contract.

No-rerun remote evidence:

```text
analysis_root=/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot
remote_clean_archive=/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
repackage_validation=passed rows=6
archive_entries=66
remote_command_status=0
```

Clean archive local copy:

```text
docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/remote_logs/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

Clean archive SHA-256:

```text
ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110
```

New repair note:

```text
docs/science/c_hi_late_source_age_pilot_repair_2026-07-01.md
```

New repair bundle:

```text
docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/
```

Key repair assets:

```text
repair_summary.json
repackage_validation_summary.csv
repackage_validation_summary.json
product_inventory.csv
repackage_manifest.tsv
repackage_checksums.sha256
repackage_archive_file_list.txt
remote_logs/no_rerun_repackage_filelist.stdout.log
remote_logs/no_rerun_repackage_filelist.stderr.log
remote_logs/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

Product validation summary:

- `46/Timestep_46`: `0deg`, `45deg`, and `90deg` passed.
- `49/Timestep_49`: `0deg`, `45deg`, and `90deg` passed.
- `45deg` and `90deg` products report
  `edge_overlap_uniform_cell_projection`.
- Raw X-ray, corrected X-ray, and correction-ratio empty projected columns are
  all zero for all six validated product rows.

Caveat:

- PBS job `706130.kunanyi-ohpc` still has the historical scheduler outcome
  `Exit_status=1`; the clean archive is a no-rerun repair package built from
  existing completed outputs, not a replacement PBS completion record.

Boundary confirmation:

- no new PBS submission;
- no HDF5/XRAiSE rerun;
- no endpoint rerun;
- no source-age substitution;
- no early `5/10 Myr` branch;
- no PLUTO production;
- no `C-LO`, `G-LO`, comparison-case processing, PRAiSE/radio/cavity
  regeneration, broad batch, 48-hour production commitment, or
  scientific-default change;
- no commits, pushes, cleanup, Stas/Patrick escalation, or `agent_comms`
  changes;
- accepted Goal 005/011/012/016/017/018 assets and the existing failure bundle
  were not overwritten.
