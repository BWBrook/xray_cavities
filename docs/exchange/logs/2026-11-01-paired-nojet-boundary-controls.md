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
