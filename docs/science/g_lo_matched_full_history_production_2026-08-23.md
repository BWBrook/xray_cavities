# G-LO matched full-history production

## Decision

The four planned treatments already existed, but their raw temporal surfaces
were not fully matched. `C-HI`, `C-LO`, and `G-HI` retain `51` float HDF5
snapshots, `11` double HDF5 checkpoints, and `5001` particle histories. The
accepted compacted `G-LO` evidence retains complete particles but only six
fluid ages (`0/10/20/30/40/50 Myr`).

That surface is adequate for coarse endpoint and common-age comparisons, but
it is not adequate for the planned high-resolution temporal analyses of shock
derivatives, cavity recovery against Mach number, and transition timing. With
the enlarged home quota and proven 64-node production scale now available,
one fresh matched-cadence `G-LO` rerun was scientifically justified. The run
has now passed its completion gate. The decision label is
`G_LO_MATCHED_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_MATCHED_RAW_FACTORIAL_COMPLETE`.

## Locked contract

The rerun preserves the accepted `G-LO` scientific defaults:

- Stewart group atmosphere `002_031`;
- one-sided jet power `1e43 erg s^-1` and jet speed `0.1c`;
- exact `50 Myr` target;
- float HDF5 every `1 Myr` (`0..50` expected);
- double HDF5 every `5 Myr` (`0..10` expected);
- particle history every `0.01 Myr` (`0..5000` expected); and
- the established 64-node, 1792-rank runtime with a progress watchdog.

This is a fresh, no-overwrite run. The wrapper writes only under
`/u/bwbrook`, rejects an existing work root, and performs a disposable
`16 MiB` write-and-fsync probe before setup. The historical compacted `G-LO`
roots remain accepted and read-only until this rerun completes and passes an
independent endpoint/cadence review.

## Storage and remote preflight

The live home tree occupied `2,394,234,566,848` bytes against the known
`21,990,232,555,520`-byte (`20 TiB`) home quota. This left far more than the
conservative `4 TiB` launch headroom. The disposable write-and-fsync probe
passed and was removed.

Remote staged hashes matched the local wrapper, production template,
watchdog, rendered configuration, and trusted group-profile table. Shell
syntax passed. The rendered `G-LO` case, power, speed, duration, and output
cadences matched the locked contract. The atmosphere table had `4000` rows,
`6` columns, and monotonically increasing radius. PLUTO, `jet-setup`, the
Intel/IMPI/HDF5/ZFP stack, and MPI launch tools were present. The fresh work
root was absent, and the enabled `normal` queue admitted the requested
`48:00:00` walltime.

## Submission

PBS accepted `786516.kunanyi-ohpc` / `g_lo_hist2`. It was verified `Q` in
`normal` with `select=64:ncpus=28:mpiprocs=28`, `1792` ranks, `128gb` memory,
and `48:00:00` walltime.

- Stage root:
  `/u/bwbrook/codex_kunanyi/goal061_g_lo_matched_full_history_production`
- Run root:
  `/u/bwbrook/xray_cavities_runs/2026-08-23-g-lo-matched-full-history-production`
- Stdout/stderr: `g_lo_matched_full_history_production.out` and `.err` under
  the stage root.
- Preflight and initial scheduler evidence: `remote_logs/` under the stage
  root.

The PBS stop rule was invoked immediately after queued-state verification. No
polling, post-processing, compaction, deletion, or follow-on job occurred.

## Completion review

Barry reported PBS `786516.kunanyi-ohpc` completed with `Exit_status=0` after
`30:01:35` walltime. Final qstat confirms state `F`, `1792` CPUs, and the
reported CPU and memory use. `Stageout_status=1` is retained as a scheduler
caveat because all required stage-root and run-root evidence remained present
and was retrieved directly.

Run evidence is internally consistent:

- stdout records `home_write_fsync_probe=passed`, `RUN_KIND=fresh`,
  `MPI_EXIT_CODE=0`, and `JOB_END=2026-08-24T19:25:28Z`;
- `markers/DONE` is present and `markers/FAILED` is absent;
- stderr contains only the known nonfatal 93-byte `setup-problem: git: command
  not found` source-metadata warning;
- float HDF5 indices are continuous and non-empty from `0..50` (`51` files);
- double HDF5 indices are continuous and non-empty from `0..10` (`11` files);
- particle histories are continuous and non-empty from `0..5000` (`5001`
  files); and
- the remote output directory occupies approximately `2.9 TiB`.

Independent HDF5 inspection opened `data.0050.flt.h5::Timestep_50` and
`data.0010.dbl.h5::Timestep_10`. Both carry exact code time
`15330.0696894`, contain `rho/prs/tr1/vx1/vx2/vx3`, and give common field
shape `1014 x 960 x 960`. First/last scalar samples for every required field
were finite.

The established restart validator then bound double checkpoint `10` to
particle history `5000` at step `49462` and the same exact code time. It
scanned all `197,568` endpoint particle records, confirmed unique IDs
`1..197568`, validated the 13-field/15-element schema, and matched the expected
file size.

Remote and locally retrieved SHA-256 values agree for all ten compact evidence
files. The retrieved remote-log bundle is approximately `124 KiB`, and the
full compact local asset bundle is approximately `160 KiB`; no HDF5 or
particle payload was copied.

## Canonical status

The new home-resident Goal 061 run is the canonical `G-LO` source for future
matched-cadence analysis. The four cases now share the intended
`51/11/5001` temporal surface, with G-HI retaining its documented split-root
provenance. The historical compacted G-LO roots remain useful provenance and
must not be deleted by implication; their eventual lifecycle decision is
separate from this acceptance.

No post-processing, compaction, deletion, or follow-on PBS submission occurred
in this completion review.
