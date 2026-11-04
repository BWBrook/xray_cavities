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
independent validator job **876541** is running; its staged-contract check and
all 15 target tests passed before the full restart hash. It produces no flux
measurement. Commit `20a32bd` integrates a successful receipt into spherical
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
diagnostic and passes 37 focused tests. Native execution still requires the
successful G-HI lineage and exact native input receipt.
