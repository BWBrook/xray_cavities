# Turn 15: independent native budgets and inherited G-HI provenance

Date: 5 November 2026. Work in progress; completed measurements and scheduler
submissions are distinguished below. Barry authorised turn 15 after the latest
Claude, Patrick and Stas updates. This work reads existing simulations only.

## Frozen analysis and first job

Commit `46ac912` adds independently reviewed native input contracts, the
case runner, a PBS wrapper, global native-lobe 2.5pV/4pV proxies and the
emission/results plan. Thirty-two focused local tests passed. Separate
contracts exist for C-HI, C-LO and G-LO, each with all 51 saved snapshots.

C-HI snapshot 1 against its actual snapshot 0 completed as
`876531.kunanyi-ohpc`, **F/0 in 21m 35s**. All 30 target tests passed in
54.12 seconds; stderr is empty. Independent review verified 34 capture/stage
hashes, source/input/completion bindings and the compact arithmetic. It also
reconstructed sphere cell counts exactly from the captured grid, and volumes
within 2.3e-16 relative error. Native field integrals were not independently
re-extracted. The result is accepted for raw-measurement expansion.
The extractor's generic external-identity hold remains in the immutable output;
the accompanying preflight separately passes historically bound configuration,
atmosphere, units, geometry, gamma and case-power checks. Historical
source-to-executable linkage remains qualified.

At actual age **0.999920251 Myr**, labelled bipolar input is
**6.311016665e58 erg**:

| Quantity | 100 km/s | 300 km/s |
| --- | ---: | ---: |
| Radius (kpc) | 10.737753 | 10.715145 |
| Thermal change / labelled input | 0.496813 | 0.496803 |
| Kinetic change / labelled input | 0.611843 | 0.611842 |
| Gravitational change / labelled input | 0.000066955 | 0.000066937 |
| Total change / labelled input | 1.108722 | 1.108712 |
| Cocoon total change / labelled input | 0.680813 | 0.680813 |
| Ambient total change / labelled input | 0.427909 | 0.427899 |

Global native-lobe **2.5pV/input = 0.432392** and **4pV/input = 0.691827**.
These are separate proxies, not additive energy terms. Both spheres are
complete, contain the entire traced cocoon and fit inside the candidate inset
box; neither requires clipping. No isolated defining cell or tracer-range
violation appears. Nonetheless 3,848/6,312 disturbance-flagged cells lie
outside R100/R300, and R300 excludes 1,216 cells moving at least 100 km/s.
Neither aperture is certified to contain all disturbances. The roughly 10.87%
excess is not a closure conclusion: realised delivery and surface transport
remain unmeasured, and historical source-to-executable linkage is qualified.

Compact results, input/preflight/completion receipts and the initial component
plots are under `../../science/assets/turn15_spherical_budgets_2026-11-05/`.
The verified smoke capture archive SHA-256 is
`eb1ff9534717eeed273075853800233c3c96b78091158569bb2b357ba635c5f1`.

After review, the independent histories were submitted:

| Case | Job | Requested indices | Submission state |
| --- | --- | --- | --- |
| C-HI | 876542 | 0, 2--50; reuse smoke 1 | Q, no hold |
| C-LO | 876543 | 0--50 | H, afterany:876542 |
| G-LO | 876544 | 0--50 | H, afterany:876543 |

The dependencies serialize native I/O and use `afterany`, so a failed case
does not suppress the next. None depends on G-HI. Every case revalidates its
own contract before reading fields. Full history completion is not claimed.
The initial scheduler client crashed while handling the long index variable;
both active and historical job-name queries confirmed no accepted submission.
Fresh per-case launch scripts then supplied the variables without `qsub -v`.
They preserve the frozen analysis, smoke-review gate and 2-CPU/16-GB/48-hour
resource request. Failed submission evidence is retained; no native result
was overwritten or duplicate analysis submitted.

The immutable spherical stage archive SHA-256 is
`3b3b7c3167ff38b629a7aa7b03e5763c1f75f1ff706641961b1f608b35f1785d`;
its stage manifest is
`84cb193cba9f7527b48a6ad06ba6ceb3976042b606cb85fabed7d7003f1715c2`.
Native files remain in place. This capture does not duplicate their bulk data.

## G-HI repair and source interpretation

Commit `57ad7da` implements the reviewed inherited-source validator and r6
flux wrapper. It binds the retained parent source/build, matching executables,
rendered configuration, atmosphere, historical continuation/restart evidence
and canonical snapshot chain. The downstream flux extractor receives the
verified parent source directory explicitly. The three independent cases
precede G-HI validation in the flux wrapper. No historical source is copied,
rebuilt or invented. Seventy-one focused tests passed in independent review
and parent integration. Commit `7dae34b` additionally records hash-time file
identities for every restart input and tests mutation during hashing. The
independent validator job **876541** completed **F/0 in 14m 22s**. Its
staged-contract check, all 15 target tests, full restart hash and final 98
checksums passed. It produces no flux measurement. The successful lineage
receipt is pinned by SHA-256
`a9704e2ea8f66251e8ea3b05c29e1fd5172bacc207880ee9a204e1d0b44ffcdf`. Commit `20a32bd` integrates a successful receipt into spherical
preflight, admitting only G-HI snapshots 0--47; 31 focused tests pass.

No launch-time source-tree hash manifest was retained. Current source hashes,
identical retained build/parent/continuation executables and historical run
records establish the documented operational binding; they do not create a
missing historical source attestation. The large restart file is rehashed on
a compute node before an accepted receipt is issued.

Source inspection also corrects the BND-05 nozzle explanation: all four
retained parent trees select `DENSITY_LENGTH_SCALE`, not
`DENSITY_JET_POWER`. Injected pressure follows a spatial adiabatic scaling
after its inlet normalization. The previous categorical nozzle exclusion and
pressure-matched enthalpy estimate as a native-flux constraint are withdrawn.
The recorded residuals are unchanged; realised delivery awaits measurement.
Independent source review confirmed this bounded correction.

## Emission and filling preparation

The G-HI/20 diagnostic follows
`../../science/turn15_emission_and_results_plan_2026-11-05.md`: disjoint lobe,
moving ambient and approximately static external masks; 30/100/300 km/s;
same-current-cell initial references; signed deficit attribution; separate
W+/W- reconstructed solids; and unchanged observer comparisons. Retained and
clamped emissivity conventions remain separate.

All three packed observer masks and the XRAiSE/APEC/Gaunt payloads match their
retained manifests. Nine freshly captured metadata/axis files also match the
historical retained-map input binding. Their compact archive SHA-256 is
`8847a50fe5a3724a8b107e2a1481262c089eeb8654a217715db1126c822f8e1f`.
Exact native edges and retained sky bins will expose coverage loss and map
compatibility differences explicitly. These are preparation checks, not new
observer-recovery or emission results. Commit `c5b438d` implements the reviewed
diagnostic and passes 37 focused tests. The actual successful lineage receipt
now supplies a qualified contract for native execution. Emission still requires
the completed snapshot-20 measurement and its exact native input receipt.


## G-HI analysis launch and retained failure

The accepted lineage generated the actual G-HI spherical contract,
SHA-256 `601ee8f013a089f199912e3194028b2bff39cb7a81c169048d4e557e63eb6778`.
Independent review reconstructed it byte-for-byte, verified all 20 staged
Python sources against commit `c5b438d`, and reproduced **80 passing tests**.
The emission gate checks the first budget's case, index, time, input receipt,
extractor identity and complete product inventory. Nine substitutions were
rejected against the genuine earlier smoke. The two budget phases cover
exactly 0--47; emission cannot block the remaining history.

The frozen analysis archive has 51 regular files including its manifest:

- Archive SHA-256: `fb5c270ce38e1b7f927b367c23975ec5ec3a3e32166ed35387c93d713109825d`.
- Manifest SHA-256: `988b30e4d413a0ebe2d61616f9bc88a823b92bf5e82b719457ebac3f97f182d0`.

The uploaded archive and all 50 manifest members verified on Kunanyi. Initial
budget jobs **876545/876546** each failed F/1 after one second: the node's
Bash rejects an empty `plots` array under `set -u`. This happened after stage
integrity checks but before Python, tests or native reads; a direct inspection
confirmed that no `results_*` directory existed. Dependent emission **876547**
terminated without running. These jobs and logs are retained as failed
provenance. The frozen science and inputs are unchanged; a separately pinned
launch overlay addresses only this shell argument handling.


The corrected overlay uses positional arguments instead of the empty Bash
array. Author and independent reviewer each passed all **20 checks under
Bash 3.2.57**, verifying exact arguments, runtime environment, invalid input
rejection, failure propagation and pre/post hashes. Both confirmed that every
r1 member remained unchanged. The overlay archive SHA-256 is
`f2660146211104c352104dce2deab5085fb297856cfab7ca1c7ec905167a68fa`, and its
launch manifest SHA-256 is
`8373bc495b0b0cd913b210fcbf194591968af0db390056246cd5dfefde89ad89`.
Each replacement submission pins both manifests. Remote resubmission checks
required all three original jobs to be terminal and all reserved analysis
output directories to remain absent.


Second-attempt submissions (superseded first20/emission; history retained):

| Phase | Job | Indices | Dependency | Resources |
| --- | --- | --- | --- | --- |
| G-HI first budget | 876551 | 20 | none | 2 CPU, 16 GB, 3 h |
| G-HI remaining history | 876552 | 0--19, 21--47 | afterany:876551 | 2 CPU, 16 GB, 48 h |
| G-HI emission/filling | 876553 | 20 | afterok:876551 | 2 CPU, 32 GB, 12 h |

The history does not depend on emission. Should the first20 phase fail,
remaining raw measurements can proceed while the missing point remains
explicit. Emission must pass the successful first20 receipt and semantic gates
before reading native fields. Optional plots use the same frozen renderer.
No native-emission completion or full-history completion is claimed here.


Replacement job 876551 reached Python and passed all **80 target tests** in
44.677 seconds, with zero failures, errors or skips. This verifies that the
launcher repair passed the previous failure point; it is not a completed
native measurement. At the latest C-HI observation, snapshot 0 had completed
and snapshot 2 had bound its inputs for extraction; these additional points
have not yet undergone the first smoke's independent scientific review.


## Device-namespace rejection and node-bound recovery

Job **876551** subsequently failed native preflight before any measurement,
because the exact restart identity differed on its assigned compute node.
Dependent emission **876553** did not run. The remaining history **876552**
was assigned to the original validation node, passed its full native preflight
and continues there. It is retained without resubmission.

The bounded metadata probe **876554** finished F/0 in one second on the rejected
node. All four restart files differed from the accepted receipt **only in the
filesystem device number**; paths, resolved paths, inode, size, mtime and ctime
matched. The probe also rehashed the small fluid catalogue, reproducing its
accepted SHA-256. It did not reread the large restart payload. This identifies
a node-local filesystem namespace difference, not evidence of changed file
contents. The original strict comparison correctly stopped the cross-node use.

Recovery binds the new first20 and emission requests to the original validation
node, both in PBS resources and through a runtime host guard before reads or
Python. A fresh isolated stage preserves all failed evidence and has no history
launcher. Independent review confirmed all 20 scientific sources remain exact
`c5b438d` Git blobs; the lineage receipt is unchanged. The only contract change
is the path to its staged historical-input witness, giving contract SHA-256
`c59a58b9083c9573ecf5c4d9da3f0424936c5a09f247c645b5fc0fcb47ed1dc5`.
The 49-member preparation check and all staged imports pass; Bash 3.2 checks
confirm correct argument handling and rejection of wrong-host, history and
invalid-option requests. No scientific gate or file-identity field is removed.


The new first20/emission archive contains 50 regular files including its
manifest. Archive SHA-256:
`b5aa5a2bc7f04d43d8ec157b41da64250ec8f58db651b8f9d6001f05d587bcab`;
manifest SHA-256:
`ea7a2b1982ded6f2bf586082212b359acab4a7ed6e87de7f7e0c27519404dc3b`.
The parent verified every archive member locally and every frozen member
remotely before submitting. This stage supplies only the missing index-20
budget and its dependent emission diagnostic; history 876552 continues to
supply the complementary indices from its original stage.


Final active submission set:

| Case/phase | Job | Retained indices | Dependency |
| --- | --- | --- | --- |
| C-HI history | 876542 | 0, 2--50; reuse reviewed smoke 1 | none |
| C-LO history | 876543 | 0--50 | afterany:876542 |
| G-LO history | 876544 | 0--50 | afterany:876543 |
| G-HI history | 876552 | 0--19, 21--47 | original afterany:876551 fulfilled |
| G-HI first20 | 876555 | 20 | none |
| G-HI emission/filling | 876556 | 20 | afterok:876555 |

Jobs 876555 and 876556 are explicitly bound to the validated node. Their
submission states were Q/no hold and H/dependency hold respectively. There is
no dependency from the three independent cases to G-HI, and no dependency from
the G-HI history to emission. Failed first20 and emission attempts remain
terminal and cannot produce duplicate measurements.


At **10:14 AEDT on 5 November**, C-HI 876542 and G-HI history 876552 were R;
C-LO 876543 and G-LO 876544 were H on their declared dependencies;
G-HI first20 876555 was Q/no hold, and emission 876556 was H on afterok:876555.
The fresh first20 stage had not started, so no target startup or completion is
claimed for it. Additional C-HI snapshots 0 and 2 had completed; only smoke
snapshot 1 has the independent scientific review reported above.

The downloaded closeout archive SHA-256 is
`c1e54d5a03ce9404f078625841c86054369ead47064467a91d921ad457d07b35`.
All **57 captured member hashes** verified locally, and captured stage and
overlay manifests match the local freezes byte-for-byte. Raw scheduler and
host-identity records are retained privately. The sanitized public summary is
`../../science/assets/turn15_spherical_budgets_2026-11-05/execution/submission_summary.json`.

Next: inspect completed per-snapshot receipts and aggregate histories, review
the G-HI/20 emission/filling products, and render the four-case component and
native-lobe proxy comparisons. Actual nozzle delivery and aperture transport
still require the separate flux measurement before any closure interpretation.
