# 2026-08-13 - Four-case pre-production readiness

Goal 057 prepared the matched `C-HI/C-LO/G-LO/G-HI` production and storage
contract while the TPAC quota increase is pending.

Local work completed:

- corrected PRAiSE2's radiative coefficient to the published `4/3` form in
  the `plutokore` working tree;
- built a coefficient-only G-LO comparison against the immutable Goal 056
  source and deterministic 4096-particle panel;
- built a no-overwrite reversible HDF5 compression pilot with bitwise and
  real-analysis readability gates;
- recorded a conservative `11.277 TiB` uncompressed four-case forecast,
  `16 TiB` minimum quota target, and `20 TiB` preferred headroom;
- established the production order `C-HI`, `C-LO`, `G-HI`, with existing
  `G-LO` analysed first and rerun only if a specific gap emerges; and
- defined a five-stage reusable `G-LO` snapshot-analysis skeleton.

Remote pilots:

- `785271.kunanyi-ohpc` / `g_lo_c1cmp`: coefficient comparison, verified `R`.
- `785272.kunanyi-ohpc` / `h5_revpil`: reversible compression and XRAiSE
  readability pilot, verified `R`.

Post-submission local review hardened future compression by routing integer
arrays through gzip and exporting `HDF5_PLUGIN_PATH` for fresh analysis
processes. The submitted job was not altered. A readability-only failure
should be finalized against its existing compressed copies rather than causing
a full recompression rerun.

Stop rule is active. Wait for Barry's PBS completion emails before retrieving
or interpreting either pilot. Do not submit new full-history production until
the quota increase is confirmed.

## 2026-08-14 completion continuation

The coefficient pilot completed green and is accepted. Corrected PRAiSE2 is
the production method; its integrated endpoint effect ranges from `-0.096%` at
0.15 GHz to `-2.694%` at 15 GHz, with no added non-finite values.

The compression pilot returned nonzero only at the fresh-process XRAiSE read.
Both reversible copies had already passed bitwise/schema/metadata validation,
reducing the sampled float and double files by `72.45%` and `55.58%`.
The failure was missing `HDF5_PLUGIN_PATH`. Future routing also now recognises
real `cell_coords`/`node_coords` groups as gzip targets. No recompression was
started: a one-CPU readability-only finalizer, PBS `785371.kunanyi-ohpc`, was
submitted and verified queued. Wait for Barry's completion email and do not
delete original or pilot files.

PBS `785371.kunanyi-ohpc` completed green. Fresh-process plugin discovery,
coordinate/field reads, and the real 50 Myr XRAiSE calculation all passed;
stderr is empty and the retrieved seven-member archive is checksum-clean.
Reversible HDF5 compression is now technically validated. Measured-ratio
planning projects about `0.936 TiB` per retained case and `3.745 TiB` across
four cases, excluding operational overlap and safety margin. Keep the existing
`16-20 TiB` quota request and the production submission hold until TPAC confirms
the increase. Compression acceptance is not automatic deletion authority.
