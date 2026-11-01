# Migration and analysis stocktake — 1 November 2026

Barry requested live migration verification, an audit of the retained cluster
and group no-jet controls, a costed recommendation on a matched-grid control,
and updates on flux, native emission and the 60-view cavity diagnostic. This
request authorises retained-output analysis; no new PLUTO simulation is launched.

## Migration at 04:53 UTC

PBS 870323 remains running, about 25 hours into its 72-hour allocation.
Nine units are complete, representing 5,696,611,330,969 logical bytes. The
C-HI full-history unit completed at 01:03:17 UTC: all 7,119 regular files,
3,090,276,948,775 bytes, have fresh device-transition-epoch hash receipts.
For all nine units, receipt paths cover the manifest's regular files, sizes
match, the normalized plan binding matches, source compatibility links target
live archive directories exactly, and no tombstones remain. This is a review
of migration receipts and live link metadata, not a new payload rehash or a
filesystem quota measurement.

C-LO is at `copy-start`; its source is still a directory and the archive
copy exists. Its 3,099,597,012,312 bytes have no verification receipts yet.
Copy completion, source/archive hashing, promotion, removal of the verified
scratch duplicate and final ten-unit completion remain. Flux 870374 and native
870719 remain dependency-held. Their dependencies must not be bypassed.

Evidence: `docs/science/assets/migration_stocktake_2026-11-01/` contains
scheduler records, the read-only capture script, report, compressed receipt
capture and local validation. Capture archive SHA-256:
`0aca0f64d206617d69ea0e6c67cf5b0d379226b120e0d0016c780b8c0b975fad`.
The report's `plan_hash` field hashes raw input JSON; local validation explicitly
normalizes it with schema 2, matching frozen receipt hash
`698d01634ade85df5fac6d42716c5463af56118230b085021ba7b205739c8900`.

This exposed a defect in the native launch gate: it hashes the raw plan rather
than the frozen migration's normalized representation. A narrowly scoped
repair and regression are in progress. The frozen migration code, plan and
receipts are unchanged. Native scientific extraction has not begun.

## Q-032 completed diagnostic delivered

PBS 870640 finished `F/0`, walltime 11:25. Its 6,716,187-byte archive hashes to
`f968ee66dfb7da4257a018ef5e983f720bf327c770aa9511f5167d72a7ca039f`, matching the
portal. All 124 members, including the manifest, match the packaging receipt
by hash and size; all 123 manifest payloads match and no extras are present.
Input-before/after receipt hashes are identical. The package contains exactly
60 maps, 600 unique method-side rows, 60 masks and 60 stamps. An independent
mask recomputation reproduced 3,600 derived values plus shape, hemisphere,
axis and detection checks. Remote source maps were not independently reread
in this stocktake.

Products are in
`docs/science/assets/q032_retained_method_ladder_2026-10-31/results/` and
`remote_evidence/`. The external receipt explicitly excludes G-HI/50 from
scientific inference; inner rows/metadata do not repeat that flag. Preserve
all raw products and exclude those three views when summarizing eligible
results. No new production method or topology policy is adopted. Claude retains
Q-032 interpretation ownership and has the delivery on discussion 29.

For 57 eligible views, detected-side median projected tracer completeness is
0.093 for legacy 1% area, 0.399 for seed-grow and 0.450 for the 5% deficit
threshold. These medians condition on detection and do not apply topology
acceptance. The 5% method has 24 connected-cross-midplane views; more recovered
area alone does not validate two-lobe recovery. Legacy falsely recovers
C-LO/10 at 0 and 45 degrees with zero tracer overlap. The 120-kpc aperture
clips tracer footprints in 18/30 C-HI and 12/24 eligible G-HI sides. Projected
revolution-volume ratios are not native 3D volume recovery. No initial or
evolved no-jet baseline was supplied to this diagnostic.

## Existing no-jet control configuration

The recovered May-8 compact archive matches its historical SHA-256
`adb099cd1557b192d23f48b6d5a1976225a607ebce9df7c2854b66d44a125c80`.
Actual cluster 690366 and group 690371 configurations both specify reflective
boundaries on all six faces, unlike production outflow boundaries. They also
use a 400×400×500 uniform 1-kpc grid, compared with 960×960×1014 production
cells and a 0.05-kpc minimum spacing. Thus these controls differ in boundary
conditions as well as resolution and cannot be subtracted from production.

Their existing shock calibration samples every fourth cell and clips negative
departures; its small positive maxima do not establish integrated energy or
mass stability. A signed full-cell audit of the existing six snapshots per
case is being prepared and independently reviewed. The archived inputs are
already in the completed gates migration unit, so that audit need not wait
for C-LO migration. It will run on Kunanyi to avoid transferring about 69 GB
of native fields, and will not modify them.
