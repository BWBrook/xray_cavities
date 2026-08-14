# Goal 057 log

## 2026-08-13 - local contract complete; remote pilots running

- Implemented Patrick's published PRAiSE2 equation (3) radiative coefficient
  in the `plutokore` working tree using named physical constants.
- Preserved the pinned Goal 056 source as immutable baseline provenance and
  added a controlled coefficient-only diagnostic on the exact 4096-particle
  panel at five frequencies and five source ages.
- Added a reversible, streaming HDF5 compressor with bitwise value,
  dtype/shape, attribute, inventory, and real-XRAiSE-readability gates.
- Added a matched four-case production/retention contract, conservative
  uncompressed storage forecast, protected `G-LO` snapshot manifest, and
  staged per-snapshot analysis skeleton.
- Estimated `2.819 TiB` uncompressed per matched case and `11.277 TiB` for the
  four-case design; retained `16 TiB` as the minimum quota target and `20 TiB`
  as preferred working headroom.
- Staged self-contained, SHA-verified payloads under
  `/u/bwbrook/codex_kunanyi/goal057_preproduction_readiness`.
- Submitted PBS `785271.kunanyi-ohpc` / `g_lo_c1cmp` and verified state `R` in
  `normal` with `1:ncpus=16:mem=96gb`, walltime `24:00:00`.
- Submitted PBS `785272.kunanyi-ohpc` / `h5_revpil` and verified state `R` in
  `normal` with `1:ncpus=1:mem=32gb`, walltime `24:00:00`.
- One focused post-submission review found that fresh Python processes need the
  installed ZFP plugin directory exported through `HDF5_PLUGIN_PATH`; it also
  routed non-floating numeric arrays to gzip. The local future wrapper and
  tests are hardened. The running job remains immutable; if only readability
  fails, use its completed compressed copies in a no-recompression finalizer.
- Invoked the stop rule immediately after running-state verification. No
  production simulation, source deletion, or post-submission polling occurred.

Status: `submitted_waiting_remote_pilots`.

## 2026-08-14 - coefficient accepted; compression readability repair queued

- PBS `785271.kunanyi-ohpc` / `g_lo_c1cmp` completed green with
  `Exit_status=0`; retrieved archive SHA-256 is
  `2752dd195d6678d81200052ab2c9393725c0eada87d6919418f19c964a10ecbb`.
- The required coefficient probe ratio is `1.3333333292256078`, no non-finite
  values were added, and all comparison gates passed. Corrected PRAiSE2 is the
  production method.
- At 50 Myr, corrected/uncorrected weighted emissivity ranges from `0.999036`
  at 0.15 GHz to `0.973059` at 15 GHz. The high-frequency effect is material
  for `21.24%` of weight and changes 443 particle emission classes.
- PBS `785272.kunanyi-ohpc` / `h5_revpil` completed both reversible copies and
  bitwise gates, then returned `Exit_status=1` when a fresh XRAiSE process did
  not discover the ZFP plugin directory.
- Float and double file reductions were `72.45%` and `55.58%`, respectively.
  Original inputs remain untouched.
- Local review also found real coordinate groups are named `cell_coords` and
  `node_coords`; future copies now route these and integer arrays through
  gzip+shuffle. The completed all-ZFP pilot copies remain bitwise-valid but are
  not promoted as the final encoding policy.
- Submitted no-recompression readability finalizer PBS
  `785371.kunanyi-ohpc` / `h5_readfin`; verified `Q` in `normal`, one CPU,
  32 GB, walltime `04:00:00`, then stopped without polling.

Status: `coefficient_complete_compression_readability_finalizer_waiting`.

## 2026-08-14 - remote pilots complete; quota hold remains

- PBS `785371.kunanyi-ohpc` / `h5_readfin` completed with `Exit_status=0` in
  `00:17:29`; `Stageout_status=1` is retained as a scheduler caveat, but the
  stage-root archive/stdout/stderr were present and retrieved.
- Fresh-process ZFP reads passed, including real `cell_coords` and `rho`
  selections from the existing compressed float copy.
- The 50 Myr XRAiSE pass completed over the `1014 x 960` projected grid. Raw
  and corrected maps each have `973440/973440` finite positive cells.
- Retrieved archive SHA-256 is
  `abe331bceccd0a78de90972db14da9b587cc7809f94c1e846a43f284a5afe572`;
  all seven internal members pass their recorded checksums and stderr is empty.
- Reversible HDF5 compression is technically validated. Future completed
  copies use ZFP reversible for bulk floating fields and gzip+shuffle for
  coordinates and integer arrays.
- Applying measured ratios to Goal 057's retention design projects `0.936 TiB`
  per case and `3.745 TiB` for four retained cases, with particle histories
  left uncompressed. This is a planning inference, not a quota guarantee; the
  `16-20 TiB` request remains appropriate for source/copy overlap and headroom.
- No source or pilot file was deleted. Deletion remains a separate per-file
  lifecycle action after copy, compact-product, checksum, and provenance gates.
- Corrected plutokore source/test are published on
  `bwbrook/deep-server-bringup` as commit
  `a190f0d96610c781a7ff71860333a0aae3cdfe92`; future production staging uses
  that corrected revision.

Status: `complete_preproduction_readiness_quota_hold`.
