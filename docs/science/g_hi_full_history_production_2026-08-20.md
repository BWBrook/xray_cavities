# G-HI full-history production

## Decision

Fresh `G-HI` production was the final missing cell of the locked
environment-by-jet-power factorial design. PBS `786189.kunanyi-ohpc` ended
with `Exit_status=124` after scratch-quota exhaustion at 15 Myr, but its
validated 10 Myr restart tuple supported a home-resident continuation. PBS
`786326.kunanyi-ohpc` completed that continuation with `Exit_status=0` and
reached the exact 50 Myr endpoint.

The current decision label is
`G_HI_FULL_HISTORY_ENDPOINT_GREEN_FOUR_CASE_RAW_FACTORIAL_COMPLETE`.
The four-case raw simulation surface is complete. G-HI is intentionally a
split-root dataset until its early scratch segment has been reduced or moved.

## Scientific contract

`G-HI` combines the trusted Stewart group `002_031` atmosphere with one-sided
jet power `1e45 erg s^-1` and speed `0.1c`. It uses the same
`stewart_stretched_250` grid and matched history contract as the accepted
cluster pair: target age `50 Myr`, float HDF5 every `1 Myr`, double HDF5 every
`5 Myr`, and particle histories every `0.01 Myr` (`0..5000` inclusive).

The configuration renderer now includes `G-HI` explicitly in the four-case
suite. The staged group atmosphere has `4000` rows and `6` columns, strictly
increasing radius, and SHA-256
`1bad5c1028439cc8f9e00f5614328c29e9a7e105519245511410e7c170a6de2a`.
The compact rendered configuration is retained with this note; the raw
atmosphere table remains ignored and is represented by its checksum.

## Storage and remote gates

At launch, the authenticated TPAC quota panel's two raw values were incorrectly
interpreted as `20 TiB` allocated and `8 TiB` occupied. Patrick subsequently
clarified that they are separate quotas: `20 TiB` for `/u/bwbrook` and
`8 TiB` for `/scratch/bwbrook`. The Goal 060 wrapper directed its heavy run
tree to `/scratch/bwbrook`, so it was writing against the unchanged 8 TiB
scratch limit rather than the enlarged home allocation. The temporary `16 MiB`
scratch probe passed before cumulative scratch usage reached that limit.

Remote staged hashes matched the local launch manifest. Wrapper, production
template, and watchdog syntax passed. The rendered case, cadence, power,
speed, grid, and atmosphere gates passed. The work root was absent, the PLUTO
and `jet-setup` sources were present, the proven Intel/IMPI/HDF5/ZFP stack
loaded, and the enabled `normal` queue admitted `48:00:00` jobs.

The launch-time storage gate was therefore checking the wrong quota domain.
After the failed run, scratch usage was `8,796,423,717,628` bytes and a
disposable `1 MiB` write followed by `fsync` failed with `Disk quota exceeded`.
Home usage was only `2,636,233,412` bytes. A post-clarification `16 MiB` write,
`fsync`, checksum, and cleanup under `/u/bwbrook` all passed. The underlying
filesystems were only `50%` full globally, confirming a per-user quota boundary
rather than global exhaustion.

The site `quota_status.sh` helper currently exits silently for Barry because
`/u/bwbrook/.tpac-quota` is absent. The portal and direct write evidence are
still sufficient for recovery; TPAC may separately restore that metadata file
so the helper works as intended.

## Submission

PBS accepted `786189.kunanyi-ohpc` / `g_hi_hist` at
`2026-08-20T01:01:26Z`. It was verified `Q` in `normal` with
`select=64:ncpus=28:mpiprocs=28` and `walltime=48:00:00`.

- Stage root:
  `/u/bwbrook/codex_kunanyi/goal060_g_hi_full_history_production`
- Run root:
  `/scratch/bwbrook/xray_cavities_runs/2026-08-20-g-hi-full-history-production`
- Stdout/stderr: `g_hi_full_history_production.out` and
  `g_hi_full_history_production.err` under the stage root.
- Preflight/submission transcripts: `remote_logs/` under the stage root.

The PBS stop rule was invoked immediately after queued-state proof and held
until Barry reported the completion email. No polling, post-processing,
compaction, deletion, or factorial-completion claim occurred in between.

## Failure review

The job progressed normally through the `14 Myr` float surface and particle
history `1499` (`14.99 Myr`). It then began the `15 Myr` double-HDF5 write.
The incomplete `data.0003.dbl.h5` is `44,627,737,880` bytes, has no catalogue
row, and is materially smaller than a complete `67,318,639,276`-byte double
checkpoint. It is not a restart candidate.

The progress watchdog last recorded normal progress at
`2026-08-20T10:36:02Z`. The scratch quota then prevented further output and
also prevented complete failure telemetry: the watchdog trigger and `FAILED`
marker exist but are zero bytes, and the watchdog TSV lacks its normal final
timeout rows. The stage-root stdout remains decisive: `MPI_EXIT_CODE=124`,
`FAILURE_REASON=no_progress_watchdog_timeout`, and
`JOB_END=2026-08-20T12:07:59Z`.

The partial root is preserved read-only at:

```text
/scratch/bwbrook/xray_cavities_runs/2026-08-20-g-hi-full-history-production/G-HI/particles
```

It currently contains approximately `863 GiB`, `15` complete float HDF5
surfaces (`0..14`), `3` complete double HDF5 surfaces (`0..2`), `1500`
particle histories (`0..1499`), and the excluded partial double-HDF5 index 3.

## Validated restart

The last safe restart is the `10 Myr` tuple:

- `data.0002.dbl.h5`, `Timestep_2`, `67,318,639,276` bytes;
- double-HDF5 catalogue index `2`, step `10011`, code time
  `3065.7857363005746`;
- float companion index `10`;
- `particles.1000.dbl`, step `10011`, code time `3065.785736301`;
- `restart.out` record 2, with fluid/particle time difference
  `4.2518877307884395e-10` code units.

The established restart validator scanned all `39,764` particle records,
confirmed unique IDs and the expected 13-field schema, and checked the fluid
HDF5 size, `1014 x 960 x 960` shape, time, catalogue row, and required
`rho/prs/tr1/vx1/vx2/vx3` datasets. Status was `ok`.

## Home continuation

The quota-domain correction opened the existing Goal 060 recovery path. A
dedicated continuation wrapper requires a `/u/bwbrook` run root, performs a
`16 MiB` write-and-fsync probe, revalidates the selected fluid/particle pair on
the compute node, and rejects any target containing partial double-HDF5 index
3. The target contains copied compact configuration/catalogue state and
read-only links to only the selected double-HDF5, float-HDF5, and particle
restart payloads in the preserved scratch source.

PBS accepted `786326.kunanyi-ohpc` / `g_hi_hist_r1` at
`2026-08-21T01:35:44Z`. Initial state was `Q` in `normal`, with the established
`64` nodes / `1792` CPUs and `48:00:00` walltime. New output is directed to:

```text
/u/bwbrook/xray_cavities_runs/2026-08-21-g-hi-full-history-home-continuation/G-HI/particles
```

The failed scratch root remains the early-time provenance source. The
continuation is authoritative after the validated 10 Myr restart boundary;
the later overlapping files left by the failed scratch run are not part of the
canonical sequence.

Compact failure evidence is under `failure_786189/`; home-continuation staging,
submission, and completion evidence is under `home_continuation_786326/`. No
raw HDF5 or particle payload was copied locally or altered remotely.

## Completion review

Barry reported PBS `786326.kunanyi-ohpc` completed with `Exit_status=0` after
`28:08:03` walltime on `64` nodes / `1792` CPUs. Final qstat confirms state
`F`, `Exit_status=0`, and the requested `48:00:00` walltime. It also reports
`Stageout_status=1`; this is retained as a scheduler caveat because the stage
stdout, stderr, catalogues, and validation records were all present and
directly retrievable.

The run has `markers/DONE`, no `markers/FAILED`, an empty stderr, and stdout
markers for `home_write_fsync_probe=passed`,
`restart_pair_validation=passed`, `RUN_KIND=h5_restart_2`, and
`MPI_EXIT_CODE=0`. The home continuation occupies approximately `2.2 TiB`.

The endpoint validation opened `data.0050.flt.h5::Timestep_50` and confirmed
code time `15330.0696894`, the exact configured 50 Myr target. Datasets
`rho`, `prs`, `tr1`, `vx1`, `vx2`, and `vx3` all have shape
`1014 x 960 x 960`. The final `particles.5000.dbl` is structurally readable at
the same code time and step `49156`, with `193,741` particle records.

The canonical G-HI raw sequence is complete and nonempty under one explicit
split-root rule:

- double HDF5: failed scratch indices `0..2`, then home indices `3..10`;
- float HDF5: failed scratch indices `0..10`, then home indices `11..50`;
- particle histories: failed scratch indices `0..1000`, then home indices
  `1001..5000`.

This yields the intended `11` double HDF5 surfaces, `51` float HDF5 surfaces,
and `5001` particle histories without gaps. The failed scratch tree must not be
deleted or compacted until the selected early segment has been reduced or
moved and a replacement canonical manifest has been verified. No science
post-processing, deletion, compaction, or further PBS submission occurred in
this completion review.
