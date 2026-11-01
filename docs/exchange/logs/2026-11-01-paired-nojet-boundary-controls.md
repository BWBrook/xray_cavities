# Paired coarse boundary controls — 1 November 2026

Barry: “Go ahead with the cheap paired reflective/outflow controls, keeping
everything else identical. Hold off on a full production-matched run.” This is
a continuation of turn #5; no return to Claude yet.

Implemented a staged-only PLUTO/jet-setup patch, one common binary workflow,
four fresh 400 × 400 × 500 controls, exact numerical boundary-flux and source
accounting, and independent native/budget validators. Original checkouts and
production inputs are untouched. The scientific plan and local evidence are
in `docs/science/paired_nojet_boundary_experiment_2026-11-01.md`.

Initial local verification: 76 tests pass with one expected exported-stage-only
skip; all 77 pass in the exported stage. Full serial compile/link passes.
Independent review required and obtained true gross conversion-energy changes
and zero-failure gates before interpreting repair magnitude. Remote MPI/HDF5
build, four full-grid smokes, paired identity and closure remain required.

Implementation committed and pushed as `493e724`. The final r1 stage passes
77/77 tests and is frozen locally; its checksum-bound manifests, patch receipt,
and test XML are retained under the paired-experiment assets. The archive is
`/private/tmp/paired_nojet_boundary_2026-11-01_r1.tar.gz`, SHA-256
`0aa334e3a5ec933a749867b2c708cd51ab4884982a2e3780b961672b2fd08973`.

Launch stopped at an access blocker: the Mac mini locked before upload, and
`kunanyi-via-nectar` could not authenticate at TPAC's jumpbox. Barry was asked
to unlock mini. No upload or new build/smoke/simulation submission occurred.
Resume via the existing portal after unlock; verify archive/source hashes,
run the common target build and all four smokes, then inspect measured resource
use and paired closure before launching the four fresh full coarse controls.
No Claude contact or scheduled monitoring was initiated.

Barry unlocked mini; continuation of turn #5. The r1 archive uploaded with its
SHA-256 matching exactly, then every extracted source checksum passed.
Build `872548` finished F/0 in 1:26 on n004, with 77/77 target tests passing.
Target binary SHA-256 is
`b8d17288dc28407cadbe390c3d8db2fb973e788686a20a2bc9da3f9369468386`.

Smoke submissions `872565`–`872568` stayed system-held because their parent
build had already completed before the retrospective afterok dependency was
registered. Empty-dependency qalter syntax was rejected without changing jobs.
After confirming all four remained held with no run directories, they were
cancelled and replaced by `872581`–`872584`, now observed running. All build
receipts were checked first; physics/source/configuration are unchanged.
The runtime parent directories smoke/ and runs/ were created before submission.

The complete target-build capture was downloaded and verified: archive
`7c90831452af8579254db3abbf23f11917a044c16159c075cef90336024c3330`,
54,503 bytes, 29 manifest payloads. Independent review confirmed all payload
hashes, 740 source checksums, definitions/units, source guards and MPI/HDF5
linkage. Build evidence is under the experiment's `target_build/` assets.
Paired-identity gate job `872619` is submitted behind the four running smokes.

## Smoke validation correction and preserved evidence

All four 0.25-Myr smoke simulations completed with measured MPI exit 0 and
passed the native-output validator. Each took 14 accepted updates. Original
PBS jobs were cluster reflective `872581` F/0 (14:43), cluster outflow `872582`
F/0 (14:15), group reflective `872583` F/1 (16:40), and group outflow `872584`
F/0 (16:34). The original pair-gate job `872619` failed its dependency and
published no gate.

The group-reflective failure occurred only in a signed-flux arithmetic
identity: net -6.192058127510826e32 erg versus positive 8.344191381684754e37
and negative -8.344253302265932e37 erg. The summation discrepancy is 5.80e-15
of gross transport. Using the cancelled net as the rounding scale was
inappropriate. The sole validator correction uses positive-minus-negative
transport as its scale. Physical closure, wall transport and cumulative gates
are unchanged. Regression tests accept the observed cancellation and reject
a material 1e-6-gross inconsistency. Local integrated checks pass 82 tests with
one expected exported-stage-only skip.

Original evidence is preserved under `original_smokes/`: all 68 archive
payloads match their manifest, the actual executable matches the common build,
and all 740 frozen source checksums pass. All four corrected local arithmetic
checks pass; these are not a substitute for a fresh target gate. Maximum
interval mass/hydro residual is at most 1.446e-13 of initial storage, with
zero reported conversion/failure events. Peak measured RSS is approximately
24.1 GiB; the 64-GB allocation remains sufficient.

A separate immutable analysis overlay binds the original stage manifest,
original and corrected validators, unchanged output helper, and original PBS.
It changes the full-run wrapper only for overlay verification, the fresh gate
and the corrected budget-validator invocation. Archive SHA-256 is
`c55b659749224e0b14a838b9295bab5a020f4b9eff372aeedb08674cc3f68829`.
Target revalidation `872671` is running with one CPU, 8 GB and 30 minutes.
It will validate all four saved smokes and both pairs before any full launch.
The physics stage, executable and inputs remain unchanged.

Revalidation `872671` finished F/1 in 22 seconds, after all 38 budget tests
passed. It stopped before numerical revalidation because the frozen native
helper compares NFS device numbers across machines: the cluster receipts use
46, group receipts 44, while n001 has a different device identifier. The
observed inode, size, mtime and ctime agree. The next overlay will permit only
a device-number difference, conditional on a fresh full hash matching the
retained SHA-256, all other metadata matching, and unchanged live metadata
across hashing. Original receipts and the failed r1 stage remain immutable.

The independently reviewed r2 overlay is immutable at
`/u/bwbrook/codex_kunanyi/paired_nojet_analysis_overlay_2026-11-01_r2`.
Its archive SHA-256 is
`2b461433030c625ee62a40102659d14dea5329f9f145094d04152278b13aa0e1`.
The helper accepts only device-only differences with matching full-content
hashes and stable remaining metadata. The full-run native validator remains
frozen; the corrected helper serves cross-node smoke revalidation and budget
imports. Four ledger hashes now appear directly in gate evidence. All 91
local tests pass with one expected stage-only skip; independent focused review
passes 79 tests. Revalidation `872682` is running on n001 with one CPU, 8 GB
and a one-hour override, allowing repeated full-content reads. It requires
38 budget and seven stability tests, four native/budget checks and both pair
checks. No physics input, executable or scientific acceptance threshold changed.
