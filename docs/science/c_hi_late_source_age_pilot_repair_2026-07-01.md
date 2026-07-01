# C-HI Late Source-Age Pilot Archive Repair

Date: 2026-07-01

## Scope

This note records a narrow Goal 019 repair iteration after PBS job
`706130.kunanyi-ohpc` exited with `Exit_status=1` at the final archive step.
It does not authorize or perform a new PBS submission, HDF5/XRAiSE rerun,
endpoint rerun, source-age substitution, or broader science expansion.

## Repair Summary

Status:

```text
repair_complete_no_rerun_package_ready
```

The original job remains a nonzero PBS completion:

```text
PBS Job Id: 706130.kunanyi-ohpc
Job name: c_hi_lsapil
Exit_status = 1
Stageout_status = 1
```

The failure class is isolated to the archive contract:

```text
wrapper_archive_race_live_directory_changed_during_tar
```

All six intended source-age/view products had already validated before the
original tar failure. The repaired wrapper now builds archives from a completed
snapshot plus an explicit file list, rather than recursively tarring the live
analysis root or a live directory tree.

## Clean No-Rerun Repackage

No HDF5 or XRAiSE computation was rerun. The no-rerun finalizer validated the
existing analysis root:

```text
/scratch/bwbrook/xray_cavities_analysis/2026-06-30-c-hi-late-source-age-pilot
```

and wrote a clean archive:

```text
/u/bwbrook/codex_kunanyi/goal019_c_hi_late_source_age_pilot/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

Local copy:

```text
docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/remote_logs/c_hi_late_source_age_pilot_repackaged_2026-07-01.tar.gz
```

SHA-256:

```text
ec99aef8ca2394ee15bd8679b37cc7027cf78179249fe1ee6dc2e2bd124de110
```

The clean archive is readable with `tar -tzf` and contains `66` file entries:
the six compact X-ray/tracer products, copied stdout/stderr logs, a
repackage validation summary, manifest, and checksums.

## Product Validation

Machine-readable repair assets:

- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repair_summary.json`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_validation_summary.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_validation_summary.json`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/product_inventory.csv`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_manifest.tsv`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_checksums.sha256`
- `docs/science/assets/c_hi_late_source_age_pilot_repair_2026-07-01/repackage_archive_file_list.txt`

Validated product rows:

| Output | Timestep | View | Accumulator | Empty-column status |
| ---: | --- | --- | --- | --- |
| `46` | `Timestep_46` | `0deg` | `direct_y_axis_sum` | `0/0/0` |
| `46` | `Timestep_46` | `45deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` |
| `46` | `Timestep_46` | `90deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` |
| `49` | `Timestep_49` | `0deg` | `direct_y_axis_sum` | `0/0/0` |
| `49` | `Timestep_49` | `45deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` |
| `49` | `Timestep_49` | `90deg` | `edge_overlap_uniform_cell_projection` | `0/0/0` |

The empty-column tuple is raw X-ray, corrected X-ray, and correction-ratio
empty projected columns. The remote finalizer also checked finite positive
X-ray metrics, expected timestep/view metadata, and the refined nonzero-view
accumulator contract.

## Caveats

- The original scheduler record remains `Exit_status=1`; this repair creates
  a clean review package from already-produced outputs rather than rewriting
  the PBS outcome.
- The products remain compact projection diagnostics, not publication-ready
  observables.
- Connected-envelope X-ray topology, sparse-radio diagnostic status, Level 3
  gravity `blocked_missing_potential`, and the active `pV`/`2.5pV`/`4pV`
  convention remain unchanged.

## Recommendation

Treat Goal 019 as ready for orchestrator review as a no-rerun repair package.
If accepted, the next useful step is a compact Goal 020 review/consolidation
of the late-source-age pilot against the accepted endpoint/refined viewing
surface, without broadening to new source ages or comparison cases yet.
