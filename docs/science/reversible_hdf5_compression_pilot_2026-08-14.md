# Reversible HDF5 compression pilot

## Decision

`REVERSIBLE_HDF5_COMPRESSION_TECHNICALLY_VALIDATED`

PBS `785272.kunanyi-ohpc` (`h5_revpil`) returned `Exit_status=1`, but the first
failure occurred only after both no-overwrite compression copies had completed
and passed hierarchy, metadata, dtype, shape, inventory, and bitwise-value
validation. A fresh XRAiSE process could not discover the dynamically installed
ZFP HDF5 plugin because `HDF5_PLUGIN_PATH` was not exported in the submitted
wrapper.

This is an environment-discovery failure, not evidence of corrupted or lossy
data. The accepted original HDF5 files remain untouched.

The no-recompression finalizer PBS `785371.kunanyi-ohpc` (`h5_readfin`) then
completed with `Exit_status=0`. A fresh process discovered the staged ZFP
plugin, read coordinate and field selections from the existing compressed
float copy, and completed a real 50 Myr XRAiSE calculation. All `973,440`
projected cells were finite and positive in both raw and corrected X-ray maps.
Remote stderr is empty. `Stageout_status=1` remains a scheduler caveat, but the
stage-root archive/stdout/stderr were present and retrieved. XRAiSE reads the
float surface; the double copy was separately reopened and verified bitwise
with the same reversible filter during the original pilot.

## Storage result

| Surface | Original | Reversible copy | Reduction | Time |
|---|---:|---:|---:|---:|
| Float HDF5 | 44,890,581,676 B | 12,367,920,700 B | 72.45% | 57.96 min |
| Double HDF5 | 67,318,639,276 B | 29,900,580,774 B | 55.58% | 75.93 min |

These are HDF5-file results, not a whole-case storage forecast: particle
histories and other products have different retention and compression
behaviour.

Applying the two observed ratios to the Goal 057 matched retention contract,
while leaving the conservative particle-history allowance uncompressed,
projects `0.936 TiB` per case and `3.745 TiB` for the four-case retained set.
This is an inference from one representative G-LO float/double pair, not a
guaranteed quota requirement. The existing `16 TiB` minimum and `20 TiB`
preferred quota request remains appropriate because production needs
source/copy overlap, analysis workspace, safety margin, and protection against
case-to-case compression variation.

## Focused repair

- The local future wrapper now exports the plugin directory discovered from
  `hdf5plugin.PLUGINS_PATH`.
- The dataset router now sends integer arrays and real PLUTO coordinate groups
  (`cell_coords` and `node_coords`) through gzip+shuffle; bulk floating fields
  remain ZFP reversible.
- The completed pilot copies used ZFP reversible for all 12 numeric datasets.
  They are still bitwise-valid, but the coordinate-routing mismatch means they
  are pilot evidence rather than the final retained production encoding.
- Recompressing the same 112 GB of inputs would add little decision value.
  Instead, PBS `785371.kunanyi-ohpc` reused the completed float copy and passed
  both fresh-process reads and a real XRAiSE pass in `00:17:29` walltime.
- Retrieved finalizer archive SHA-256:
  `abe331bceccd0a78de90972db14da9b587cc7809f94c1e846a43f284a5afe572`.
- The archive contains seven compact members; its internal manifest and every
  checksum pass locally.

## Adoption boundary

Use the corrected coordinate/integer routing for future completed HDF5 copies.
Compression acceptance does not authorize automatic deletion: each original
may be removed only after its reversible copy, compact science products,
manifest, checksums, and provenance pointer are accepted. No original or pilot
copy was deleted in Goal 057.
