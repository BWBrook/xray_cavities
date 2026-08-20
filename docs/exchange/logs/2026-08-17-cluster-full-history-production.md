# 2026-08-17 - Cluster full-history production

The approved Kunanyi quota increase opened the Goal 057 production gate. TPAC
reported `20 TiB` allocated and `8 TiB` occupied, leaving approximately
`12 TiB` before launch. This exceeds the conservative `5.638 TiB` raw forecast
for the two matched cluster reruns, while preserving room for operational
overlap and later validated compression.

Fresh `C-HI` and `C-LO` configs were rendered from the trusted Stewart cluster
`002_003` table. Local tests and remote hash, syntax, asset, no-overwrite,
source, module, and queue gates passed. Both jobs use the proven 64-node scale,
the full `48:00:00` walltime, complete fluid checkpoints, and `0.01 Myr`
particle histories:

- `785822.kunanyi-ohpc` / `c_hi_hist`: verified `R`;
- `785823.kunanyi-ohpc` / `c_lo_hist`: verified `Q`.

The stop rule is active. Wait for Barry's completion emails before any
endpoint review. Do not post-process partial output, compact or delete raw
files, or submit `G-HI` by implication.

## 2026-08-19 C-HI completion

PBS `785822.kunanyi-ohpc` / `c_hi_hist` completed green in `32:30:03`.
Read-only review confirmed the exact 50 Myr endpoint, `51` continuous float
HDF5 outputs, `11` continuous double HDF5 outputs, and all `5001` particle
histories from index `0` through `5000`. The run occupies about `2.9 TiB`.

`Stageout_status=1` and the nonfatal 93-byte missing-`git` warning are retained
as operational caveats; all required compact logs were directly retrievable.
No raw payload was copied or altered. C-HI is accepted as bankable. C-LO was
not queried and remains waiting for Barry's completion notice.

## 2026-08-20 C-LO completion and Goal 059 closeout

PBS `785823.kunanyi-ohpc` / `c_lo_hist` completed green in `31:49:01`.
Read-only review confirmed the exact 50 Myr endpoint, continuous `51/11`
float/double HDF5 sequences, and all `5001` particle histories from index `0`
through `5000`. The run occupies about `2.9 TiB`.

`Stageout_status=1` and the known nonfatal missing-`git` warning remain
operational caveats, but all eight required compact logs/catalogues were
retrieved and hashed. No raw payload was copied or changed. Both cluster cases
are now accepted as bankable matched-history surfaces, approximately `5.8 TiB`
combined. Goal 059 is complete; fresh `G-HI` is the next planned production
case, subject to a separate consequential launch decision.
