# 2026-08-20 - G-HI full-history production

Goal 060 launched the final missing case in the locked four-case factorial.
The trusted Stewart group `002_031` atmosphere, `1e45 erg s^-1` one-sided jet
power, `0.1c` speed, `50 Myr` endpoint, matched fluid cadences, and complete
`0.01 Myr` particle histories all passed local and remote gates.

PBS accepted `786189.kunanyi-ohpc` / `g_hi_hist`, verified `Q` in `normal`
with `64` nodes / `1792` ranks and `48:00:00` walltime. The stop rule held
until Barry's completion email. No scheduler re-check, post-processing,
compaction, deletion, or factorial-completion claim occurred before that
wake-up.

## Completion review

Barry reported `Exit_status=124`; final qstat confirmed state `F` after
`11:06:32`. The wrapper's distinct failure is
`no_progress_watchdog_timeout`, but live evidence identifies scratch-quota
exhaustion as the cause. A disposable `1 MiB` scratch write-and-fsync probe
failed with `Disk quota exceeded` at approximately `7.9 TiB` project-run
usage, while the global filesystem remained half empty. The portal still
rendered exact `20 TiB` and `8 TiB` values, so its display and actual quota
enforcement disagree.

The run reached float HDF5 index `14` and particle history `1499`, then
stalled while writing uncatalogued partial `data.0003.dbl.h5`. The last safe
restart is the structurally validated `10 Myr` tuple: double HDF5 index `2`,
float index `10`, particle index `1000`, step `10011`, required datasets and
shape, and matched fluid/particle times.

Status is now
`blocked_scratch_quota_enforcement_mismatch_restart_ready`. No retry,
compaction, deletion, or post-processing occurred. TPAC must first make the
intended enlarged scratch quota effective and a fresh write probe must pass.

## 2026-08-21 quota-domain correction

Patrick clarified that the approved increase applies to home, not scratch.
The portal values are quotas: `/u/bwbrook=20 TiB` and
`/scratch/bwbrook=8 TiB`. Goal 060 explicitly wrote its heavy output to
scratch, which was already at the unchanged 8 TiB boundary. Direct usage was
about `2.5 GiB` in home and `8.0 TiB` in scratch; a disposable `16 MiB` home
write-and-fsync probe passed and was removed.

The correct recovery is therefore an isolated home-resident continuation from
the validated 10 Myr tuple, not a TPAC scratch-quota repair. The site
`quota_status.sh` helper remains broken for Barry because `~/.tpac-quota` is
missing, but this does not block home writes. No retry was submitted during
this correction.

## Home continuation submission

An isolated home-resident continuation was then prepared from the structurally
validated 10 Myr tuple. The target catalogues stop at double index `2` and
float index `10`; only the selected HDF5/XMF and particle index `1000` are
linked read-only from the preserved scratch root. Partial double index `3` is
absent. The wrapper requires the home path, repeats the write-and-fsync gate,
and revalidates the exact restart pair on its compute node.

PBS accepted `786326.kunanyi-ohpc` / `g_hi_hist_r1`, verified `Q` in `normal`
with `64` nodes / `1792` CPUs and `48:00:00` walltime. The stop rule is active;
no polling or follow-on work occurred.

## 2026-08-23 home continuation completion

Barry reported `786326.kunanyi-ohpc` completed with `Exit_status=0` after
`28:08:03`. Final qstat confirmed state `F`; `Stageout_status=1` is retained as
a scheduler caveat because all required compact stage evidence was available.
The target has `DONE`, no `FAILED`, empty stderr, a revalidated restart pair,
and `MPI_EXIT_CODE=0`.

The exact 50 Myr endpoint is green in both `data.0050.flt.h5::Timestep_50` and
`particles.5000.dbl` at code time `15330.0696894`. Required fluid fields have
shape `1014 x 960 x 960`; the endpoint particle file contains `193,741`
records. A compact canonical audit found no missing or empty selections across
`11` double HDF5, `51` float HDF5, and `5001` particle-history files.

G-HI is complete under a split-root rule: retain scratch through the validated
10 Myr restart boundary, then use the home continuation. This completes the
four-case raw factorial, but the scratch early segment remains protected until
it has been reduced or moved. No raw payload retrieval, compaction, deletion,
post-processing, or further PBS submission occurred.
