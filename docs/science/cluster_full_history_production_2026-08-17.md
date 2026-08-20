# Cluster full-history production launch

## Decision

The approved Kunanyi quota increase opens the production gate established by
Goal 057. Fresh, matched-history `C-HI` and `C-LO` simulations were therefore
submitted together under the locked four-case contract. The decision label is
`CLUSTER_FULL_HISTORY_PRODUCTION_SUBMITTED_QUOTA_GATE_GREEN`.

## Storage gate

### Observation

The authenticated TPAC Open OnDemand dashboard reported a Kunanyi allocation
of `21990232555520` bytes and occupied storage of `8796093022208` bytes. These
correspond to `20 TiB` allocated and `8 TiB` occupied. A temporary `16 MiB`
write probe under `/scratch/bwbrook` also succeeded and was removed. Kunanyi's
`quota` command remained unavailable because its quota RPC service refused the
connection; this is an instrumentation limitation, not evidence that the
approved allocation is absent.

### Inference

The dashboard values imply approximately `12 TiB` of headroom before launch.
Goal 057's conservative uncompressed forecast is `2.819 TiB` per matched case,
or `5.638 TiB` for these two cluster reruns. The gate therefore has substantial
room for both raw runs and later reversible-copy validation. This is not a
guarantee against transient source/copy overlap, so lifecycle checks remain
required before any source deletion.

## Locked production contract

| Field | `C-HI` | `C-LO` |
| --- | --- | --- |
| Stewart atmosphere | cluster `002_003` | cluster `002_003` |
| One-sided jet power | `1e45 erg s^-1` | `1e43 erg s^-1` |
| Jet speed | `0.1c` | `0.1c` |
| Target age | `50 Myr` | `50 Myr` |
| Float HDF5 cadence | `1 Myr` | `1 Myr` |
| Double HDF5 cadence | `5 Myr` | `5 Myr` |
| Particle history cadence | `0.01 Myr` | `0.01 Myr` |
| Resources | `64 x 28 = 1792` ranks | `64 x 28 = 1792` ranks |
| PBS walltime | `48:00:00` | `48:00:00` |
| Fresh run root | `2026-08-17-c-hi-full-history-rerun` | `2026-08-17-c-lo-full-history-rerun` |

Both wrappers fail closed if their work root already exists, use the proven
Intel/IMPI/HDF5/ZFP stack, and run through the established progress watchdog.
They contain no follow-on submission, post-processing, compaction, or cleanup.

## Preflight and submission

Local wrapper, template, watchdog, and contract tests passed (`23 passed`).
Remote staged hashes and shell syntax matched, both rendered configurations
validated against the trusted Stewart cluster table, the two run roots were
absent, the source/tool paths were present, and the `normal` queue admitted the
requested `48:00:00` walltime. The remote preflight transcript is retained at
`/u/bwbrook/codex_kunanyi/goal059_cluster_full_history_production/remote_logs/pre_submission_preflight_2026-08-17.txt`.

PBS accepted both jobs at `2026-08-17T05:23:18Z`:

- `785822.kunanyi-ohpc` / `c_hi_hist`: verified `R` in `normal`;
- `785823.kunanyi-ohpc` / `c_lo_hist`: verified `Q` in `normal`.

Each requests `select=64:ncpus=28:mpiprocs=28` and `walltime=48:00:00`.
The PBS stop rule was invoked immediately after this proof; no later scheduler
query or remote action occurred.

## Boundaries and next step

These are production simulations, not science products. Do not claim endpoint
completion, post-process partial output, compact data, or delete source files
until Barry reports the corresponding completion email and a compact
checkpoint/endpoint review passes. `G-HI` remains the next production case,
but should start only after these two runs establish their storage and runtime
outcomes under the expanded quota.

## C-HI completion review - 2026-08-19

### Observation

Barry reported completion of PBS `785822.kunanyi-ohpc` / `c_hi_hist` with
`Exit_status=0`. The final scheduler record agrees: state `F`, walltime
`32:30:03`, CPU time `907:44:00`, `1792` CPUs, and `8548832kb` memory.
`Stageout_status=1` is retained as a scheduler caveat, but the stage-root
stdout, stderr, launch transcripts, checkpoint catalogues, and watchdog log
were all directly retrievable.

The production evidence is internally consistent:

- stdout records `RUN_KIND=fresh`, `MPI_EXIT_CODE=0`, and
  `JOB_END=2026-08-18T13:53:21Z`;
- `markers/DONE` is present and `markers/FAILED` is absent;
- the float HDF5 sequence is continuous from `data.0000` through `data.0050`
  (`51` files), and its endpoint `Timestep_50` has exact code time
  `15330.069689399999`;
- the double HDF5 sequence is continuous from `data.0000` through `data.0010`
  (`11` files), and its endpoint `Timestep_10` has the same exact code time;
- both endpoint files contain all six required fields with common shape
  `1014 x 960 x 960`; and
- particle histories are non-empty and gap-free from `particles.0000.dbl`
  through `particles.5000.dbl` (`5001` files).

The C-HI work directory occupies approximately `2.9 TiB`, consistent with
Goal 057's conservative `2.819 TiB` forecast. Stderr contains only the known
93-byte `git: command not found` warning from source-metadata collection; the
staged configuration hashes remain preserved in `source_revisions.txt`.

### Decision

`C-HI` is accepted as a complete, bankable 50 Myr full-history production
surface. The decision label is
`C_HI_FULL_HISTORY_ENDPOINT_GREEN_C_LO_STILL_WAITING`. This acceptance does
not start post-processing, compaction, or source deletion. The state of
`C-LO` was deliberately not queried during this continuation and remains
waiting for Barry's own PBS completion notice.

## C-LO completion review - 2026-08-20

### Observation

Barry reported completion of PBS `785823.kunanyi-ohpc` / `c_lo_hist` with
`Exit_status=0`. The final scheduler record agrees: state `F`, walltime
`31:49:01`, CPU time `888:21:39`, `1792` CPUs, and `8423336kb` memory.
`Stageout_status=1` is retained as a scheduler caveat, but all required
stage-root and run-root compact evidence was directly retrievable.

The independent run review passed the same endpoint and history gates as
`C-HI`:

- stdout records `RUN_KIND=fresh`, `MPI_EXIT_CODE=0`, and
  `JOB_END=2026-08-19T21:42:23Z`;
- `markers/DONE` is present and `markers/FAILED` is absent;
- the float HDF5 sequence is continuous from `data.0000` through `data.0050`
  (`51` files), with endpoint group `Timestep_50` at exact code time
  `15330.069689399999`;
- the double HDF5 sequence is continuous from `data.0000` through `data.0010`
  (`11` files), with endpoint group `Timestep_10` at the same exact time;
- both endpoint files contain `rho/prs/tr1/vx1/vx2/vx3` with common shape
  `1014 x 960 x 960`; and
- particle histories are non-empty and gap-free from `particles.0000.dbl`
  through `particles.5000.dbl` (`5001` files).

The C-LO work directory occupies approximately `2.9 TiB`. Together the two
new cluster runs retain approximately `5.8 TiB` of matched raw evidence.
Only eight compact C-LO logs and catalogues (`478550` bytes total) were copied
locally; no HDF5 or particle payload was transferred or changed. Stderr
contains only the known 93-byte `git: command not found` warning from
source-metadata collection.

### Decision

Both matched cluster cases are accepted as complete, bankable 50 Myr
full-history production surfaces. The Goal 059 decision label is
`MATCHED_CLUSTER_FULL_HISTORY_PAIR_GREEN_G_HI_READY`. This completes the
cluster-production tranche and makes fresh `G-HI` the next production case in
the agreed four-case sequence. It does not authorize that consequential
production launch by implication, nor does it start post-processing,
compaction, or source deletion.
