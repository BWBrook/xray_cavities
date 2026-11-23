# Prediction custody for the 54-view X-ray test

Each of the four production runs has a stretched Cartesian grid of 960 × 960 × 1,014 cells. The cluster and group jets have labelled bipolar powers of $2\times10^{45}$ erg/s (HI) and $2\times10^{43}$ erg/s (LO). The native reader uses the archived single-precision PLUTO outputs, their paired zero-age fields, the case atmosphere and exact cell edges. Each unit images thermal emission at 1 keV ($2.417990504024\times10^{17}$ Hz), redshift 0.05, at side-on azimuths 0°, 45° and 90°. The table gives actual native times, file and grid identities, prior input receipts, and G-HI's inherited lineage. [22 native inputs](assets/xray_prediction_seal_2026-11-23/native_inputs.csv)

## Frozen comparison

Eighteen science case-ages give 54 views. Four initial snapshots add 12 null views. The G-HI 20-Myr development case is excluded. Each view yields 16 masks across the original seed/grow and radial 5%-deficit methods, both emissivity corrections, the observer-only arm and the truth-assisted replacement at three velocity cuts. The observer-only arm sees the current whole brightness and axes. The diagnostic also uses the emissivity change in the same current, non-lobe cells selected by native velocity. Its primary cut is 100 km/s. The two arms share a 120-kpc search aperture. Independent scoring after release will retain all 108 science sides per primary arm/method and all initial nulls. [Frozen cohort, estimands and failure criteria](background_refit_blind_protocol_2026-11-11.md)

## Native production and custody

Earlier summaries from legacy detectors were public, and G-HI/20 informed the design. The prospective test concerns these particular frozen refit masks on the other 54 views. Existing native energy analyses could use fields from the same simulations. Those outputs did not enter the observer-only detector or change the frozen operators, cohort or scoring criteria. [Exposure record at freeze](background_refit_blind_protocol_2026-11-11.md#frozen-cohort-and-exposure-limits)

The 22 requests bind both the original native input receipt and its prior successful completion. All corresponding receipt hashes, production case contracts and native file identities were checked at staging. The emissivity code and correction tables match the G-HI development checksums. The frozen evaluator, configuration and scientific sources match `c352554`; the map producer and assembler match `f1218f1`. Twenty-five tests ran against the extracted source stage. A separate synthetic exercise followed all 66 units through the custody wrapper and verified that scoring access had already closed when predictions began. [Staging identities and scheduler receipts](assets/xray_prediction_seal_2026-11-23/preparation.json)

The assembler verifies SHA-256 and ZIP member names on prediction-input and scoring payloads before writing two manifests. It never decodes a truth array. The custody wrapper removes read permission from all 66 truth rasters and the scoring manifest before the frozen predictor starts, keeps the original prediction receipt, and records SHA-256 for each predicted file. Its path-free seal lists the 1,056 mask labels by frozen variant and view without exposing selections. Claude's independent review of the prediction archive and native provenance precedes any release of the scoring files. [Frozen predictor](../../scripts/science/run_background_refit_blind.py) · [Custody wrapper](../../scripts/kunanyi/seal_blind_emission_predictions.py)

The original native jobs **883556–883562** exited 127 in the non-login shell before Python ran, and the dependent seal **883563** did not execute. Metadata probe **883552** rejected an unsupported PBS dispatch flag. Two later probes verified G-HI mount identities. The repaired submission used the installed analysis interpreter by absolute path. All 22 native tasks in **883566–883572** returned zero, followed by the prediction and seal in **883573**. PBS registered abort and end email for every science job. The analysis stage, predictor, configuration, native contracts and data bindings have identical hashes across both submissions. [Registration and repair](assets/xray_prediction_seal_2026-11-23/preparation.json) · [Final scheduler record](assets/xray_prediction_seal_2026-11-23/scheduler_final.json)

## Sealed predictions

On 24 November, the custody wrapper closed scoring access at **02:21:18 AEDT**. An independent check at **02:23:07** found all 67 scoring files at mode `000`, two predictions written and the final seal still pending. The witness, including the map and scoring-manifest commitments, went into public commit `35c0879` while the predictor ran. At **03:53:51**, the completed seal bound 66 prediction files and their 1,056 masks to the input receipts. [Live witness](assets/xray_prediction_seal_2026-11-23/live_custody_witness.json) · [Completed seal and per-view hashes](assets/xray_prediction_seal_2026-11-23/seal.json)

The preregistered, prediction-only audit independently checked all 22 native input bindings, all 66 detector-input and prediction file pairs, and the 16 mask labels in each prediction. It compared byte hashes, array headers and coordinate axes without inspecting brightness or mask pixels. Scoring remains closed pending Claude's review of these commitments and the source provenance. [Independent audit](assets/xray_prediction_seal_2026-11-23/prediction_audit.json) · [Audit code](../../scripts/science/audit_xray_prediction_seal.py)

To reproduce that check, run the following from the repository on the original processing site, with `seal_dir` set to the completed private seal directory. The manifests bind the original input paths.

```sh
python scripts/science/audit_xray_prediction_seal.py \
  --seal "$seal_dir/seal.json" \
  --maps-manifest "$seal_dir/manifests/maps_manifest.json" \
  --predictions "$seal_dir/predictions" \
  --config configs/background_refit_blind_2026-11-11.json \
  --native-inputs docs/science/assets/xray_prediction_seal_2026-11-23/native_inputs.csv
```

PBS job **883580** archived the 66 detector-input files, 66 sealed predictions, and 100 accompanying manifests, contracts and receipts. The archive's 1,161,011,200 bytes have SHA-256 `d9e36825bd6c6032adc2f9124bef3aaa7044401b879efb6a82862012ae4d9c77`. Two separate private stores rehashed the archive and all 232 members before installing their copies at **04:01:25** and **04:07:47 AEDT**. The scoring rasters and manifest remain in the custody of the original site. [Archive and receiver verification](assets/xray_prediction_seal_2026-11-23/archive_verification.json)

Reviewers with the project holdings can find `predictive_evidence.tar` and its creator inventory under `private_archive/turn27_blind_2026-11-23_r1/verified_archive/` in the analysis checkout. The public seal gives the hashes for checking each archived prediction and detector input before releasing the scoring truth.
