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
repair and regression passed independent review and are committed as `374e51d`. The frozen migration code, plan and
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

## Corrected native submission and retained-control audit

Fresh native stage `q031_native_emission_2026-11-01_r1` (archive SHA-256
`cb22c0e1ee43d8ae549b5b4576dbf8703e70fa2eedfa5c8a08485800f23f6e2e`)
passed target smoke 871683: 104 tests, no failures/skips, F/0, 3:38 PBS walltime.
The same-stage smoke receipt was revalidated with user-site Python disabled,
as recorded in the smoke; a login-shell check without that flag correctly
refused the runtime mismatch before any job cancellation or native read.
Held 870719 was then cancelled; replacement 871717 was observed H with
smoke/migration/flux afterok dependencies (871683, 870323, 870374).

The signed no-jet audit passed 21 tests and independent numerical/provenance
review. Source is pushed as `9eb85c1`; stage archive SHA-256 is
`c2d8912105db026d578a161996c40a3feeb182d19cf61256608c619cd056f23e`.
Job 871750 was submitted at about 05:12 UTC, initially Q, requesting
2 CPUs, 8 GB and 2 hours. It runs tests on the target and checks completed
migration-unit receipts before reading any fields. It computes signed
mass/thermal/kinetic/potential changes and full three-dimensional gas motion
at all six times, with nested boundary regions and a final maximum-motion slice.
These are analyses of existing fields; no PLUTO simulation was launched.

Cost/recommendation: `docs/science/matched_nojet_control_recommendation_2026-11-01.md`.
The independently reproduced cell-step extrapolation is 5,337 core-hours for
cluster and 4,946 for group, subject to a matched-grid benchmark. Six double
snapshots need about 404 GB per atmosphere; full fluid cadence about 3.03 TB.
The current recommendation is to defer a full matched run until this control
audit and the existing flux/native work are interpreted, then prioritize
cluster if production-background drift remains material. Claude has the
package/recommendation on board discussion 29; no new response yet.

Native launch evidence was downloaded and verified as an exact 14-member
archive (including its capture manifest), SHA-256
`9bb868b4115173a2bb8f3cccecc4283ee8b7e805bae73c7861220c539456e571`.
All member sizes/hashes, JUnit outcomes, smoke-receipt bindings and all three
PBS dependencies agree. Measured smoke peak RSS was 227,564 KiB. Local evidence:
`docs/science/assets/q031_native_pilot_2026-11-01/remote_evidence/`.
No-jet audit 871750 subsequently started, passed all 21 target tests, and
completed its cluster zero-time snapshot without errors by the 1:52 walltime
check. Outcomes remain pending until both cases and their package complete.

Claude's latest established recommendation (board 2644) is also to defer,
superseding his earlier preference for an immediate matched control. The
remaining difference concerns his analytical energy-closure claim, which is
not adopted pending the actual full-history measurements. Board 2790 corrects
the attribution and preserves this distinction.

## Cluster control result; group retrieval pending

Cluster output-only review passed 6,198 checks, including source identity to
migration-receipt linkage, signed budget algebra and geometry. Whole-grid
energy drift is +2.74828e53 erg (4.36e-9 of initial), with compensating
inner/outer 100-kpc changes of about -/+1.72e56 erg. Maximum speed is
1.54821 km/s, Mach 0.00222435, 0.5 kpc inside a reflective face; the inward
cell-centred velocity is not evidence of wall transport. Full-grid maximum
absolute density/pressure changes are 0.008711%/0.015628% at 50 Myr.

The authenticated portal became inaccessible when the Mac locked. Group
retrieval and final PBS accounting are pending; no job cancellation or
resubmission was attempted. Cluster evidence and the qualified interpretation
are preserved in `docs/science/nojet_control_audit_2026-11-01.md` and its assets.

## Completed two-case audit and final stocktake

After Barry unlocked the Mac, PBS 871750 was verified F/0, 18:49 walltime.
Both six-snapshot controls completed. All 24 result-package members and all
seven enclosing capture members match their manifests by exact membership,
size and hash. Result archive SHA-256:
`253fb8215fd377e0cbbde1436983994fd0f6d74aa747af39a729fa6db26c0da1`;
capture SHA-256:
`b8879dd9f9d968ba7606a875fffd7f6c2823a49ab75df3ed45975cc6a7ee1972`.
The cluster files are unchanged from the partial capture. The complete
expanded package is now `assets/nojet_control_audit_2026-11-01/results_bundle/`;
its cluster subset was moved there without byte changes. Prior partial
receipts are retained with their new preservation-root mapping.

Group whole-grid energy drift is +1.78616e52 erg, 4.13645e-9 of initial
energy, with inner/outer 100-kpc changes -1.24490e55/+1.24669e55 erg.
Maximum speed is 0.981063 km/s, Mach 0.00276157, 0.5 kpc inside the +x
reflective face. Maximum absolute density/pressure departures are
0.022948%/0.039888%. Both controls are quiet in their own configurations;
neither establishes production stability. The final science note includes
the combined comparison and limits.

Migration at 07:23:48 UTC is still R: nine complete units, 5,696,611,330,969
logical bytes, exact source symlinks to live archive directories, receipt
hashes present and no tombstones. C-LO remains `copy-start`, zero verified
file receipts, source still a directory. Flux 870374 and native 871717 remain
H with their recorded dependencies. No payload rehash, resubmission, new
simulation or automation was performed in this closeout.

Independent combined review passed 12,515 checks with no failures or warnings;
checker, report and their hashes are retained with the final evidence package.
