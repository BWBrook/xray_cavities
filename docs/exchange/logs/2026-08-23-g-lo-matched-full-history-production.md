# 2026-08-23 - G-LO matched full-history production

The four treatment cells existed, but the raw cadence was asymmetric. `C-HI`,
`C-LO`, and `G-HI` retain matched `51/11/5001` fluid and particle surfaces;
the compacted `G-LO` evidence retains complete particles but only six fluid
ages. That is enough for coarse comparisons, not the intended time-resolved
shock and cavity-recovery work.

A fresh no-overwrite `G-LO` rerun was therefore launched under the established
group `002_031`, low-power, `50 Myr`, `1/5/0.01 Myr` contract. It writes to
the expanded home allocation and leaves the historical G-LO roots untouched.
The remote target, storage, write/fsync, hash, syntax, configuration, asset,
runtime, and queue gates all passed.

PBS `786516.kunanyi-ohpc` / `g_lo_hist2` was verified `Q` in `normal` with
`64` nodes / `1792` ranks and `48:00:00` walltime. The stop rule is active.
Wait for Barry's completion email before any scheduler re-check or endpoint
review. Do not post-process partial output, compact/delete either G-LO source,
or claim a matched-cadence four-case factorial before the completion gate.

## 2026-08-25 completion

PBS `786516.kunanyi-ohpc` completed green in `30:01:35`. Final scheduler,
marker, stdout, catalogue, HDF5, restart, and particle checks agree. The run
reached the exact 50 Myr endpoint with continuous non-empty `51/11/5001`
float/double/particle sequences. Both fluid endpoints contain all six required
`1014 x 960 x 960` fields. Particle endpoint `5000` contains `197,568` unique
valid records at the same step and code time.

The new home run occupies approximately `2.9 TiB` and is now the canonical
matched G-LO source. The full four-case matched-cadence raw factorial is green.
Approximately `124 KiB` of remote validation evidence was retrieved; the full
compact local bundle is approximately `160 KiB`, and no raw payload was copied
or changed. Historical compacted G-LO roots remain protected provenance, and
no post-processing or lifecycle action followed.
