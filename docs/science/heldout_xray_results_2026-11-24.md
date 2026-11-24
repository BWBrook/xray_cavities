# What two X-ray outlines recover in 54 held-out views

Neither image-only rule recovered 75% of the projected lobe on any of the 108 science sides. With nondetections included, the seed/grow outline recovered a median 22.8% of lobe area and the radial 5%-deficit outline recovered 41.6%. Both left every initial control empty. [Frozen protocol](background_refit_blind_protocol_2026-11-11.md) · [Complete side-level score table, compressed CSV](assets/heldout_xray_2026-11-24/scores.csv.gz)

## Registered test

Four simulations supplied 18 science case-ages. Each was viewed at three side-on azimuths, and both hemispheres were scored against the full projected lobe defined by jet tracer. These 108 sides share simulation histories. The 20-Myr high-power group run (G-HI), which was used to develop the methods, was excluded. Each case also supplied three initial control images. The test used noiseless 1-keV images and two fixed automated methods with fitted backgrounds. Outlines drawn by eye and other ways of fitting the background remain untested. [Cohort and prediction seal](xray_prediction_seal_2026-11-23.md)

A science side passed if the outline covered at least 75% of the lobe area, at least 95% of the selected area lay on the lobe, and the outline avoided the 120-kpc aperture boundary. Targets extended beyond that aperture wherever the simulation required it. An empty outline scored zero completeness. In the simulation-assisted diagnostic, the image was recomputed with moving ambient gas set to its initial emissivity before the background was fitted again. This requires the simulation’s velocity and tracer fields. The registered primary velocity cut was 100 km/s.

| Input | Outline | Passing science sides (of 108) | Median lobe area covered | Science sides with no detection | Science sides touching aperture | False detections on 24 control sides |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| X-ray image | Seed/grow | 0 | 22.8% | 31 | 11 | 0 |
| X-ray image | Radial 5% deficit | 0 | 41.6% | 15 | 6 | 0 |
| Ambient emission replaced | Seed/grow | 6 | 42.8% | 12 | 19 | 0 |
| Ambient emission replaced | Radial 5% deficit | 13 | 59.5% | 6 | 28 | 0 |

Even the highest image-only completeness was below threshold, at 69.1% for seed/grow and 59.6% for the radial rule. On 18 sides, less than 75% of the target lay within the search aperture. These were all six sides each of C-HI at 40 and 50 Myr and G-HI at 40 Myr. Both image-only rules also failed on the other 90. All 384 initial side–label evaluations were empty across the primary and sensitivity settings. The six simulation-assisted seed/grow passes all came from C-HI at 20 Myr. Eleven of the 13 assisted radial passes came from G-LO at 30–50 Myr, and two from G-HI at 10 Myr. The registered cut sensitivity gave 14, 13 and 2 radial passes at 30, 100 and 300 km/s. [Machine-readable counts](assets/heldout_xray_2026-11-24/summary.json)

## What accounts for the missed lobe?

Claude proposed these checks after seeing the scores.

- **The missed area includes deep parts of the lobe.** Weighting each sightline by the depth of simulated lobe along it gives median volume coverage of 34.1% for seed/grow and 57.5% for the radial rule. This measures the fraction of true lobe volume behind selected pixels. It differs from estimating a three-dimensional volume by revolving the outline.
- **The radial fit also selects exterior pixels with little or no dimming.** Summed over the 54 views, 55,070.6 of 225,014.7 kpc² selected by the radial rule lies outside the projected lobe (24.47%). Only 9.52 kpc² of that exterior is more than 5% dimmer than the same pixels at time zero. Exterior gas occupied more than one fifth of the selected area in eight C-HI views, one G-HI view and five G-LO views. No C-LO view reached that descriptive threshold. The sums count each projection separately. The initial image provides a reference for actual dimming of the sightline.
- **Inferred volume can look accurate despite poor overlap.** Across the 24 individual C-HI sides at 20–50 Myr, the radial rule inferred 0.303–1.325 times the true lobe volume while covering only 32.5–45.7% of its projected area. Including exterior area can offset the loss of genuine lobe area when an outline is revolved.
- **Age comparisons include the onset of detection.** At 10 Myr both image-only rules returned empty outlines for all 12 distinct low-power sides. That gives 24 empty method–side evaluations. A pooled trend by age also changes the mix of cases because G-HI/20 was excluded and G-HI/50 was outside the registered cohort.

Across all science sides the median inferred/native volume ratios were 0.164 for image-only seed/grow and 0.508 for the radial method. Among the 77 and 93 detected sides respectively, the widths between the 16th and 84th percentiles of the log volume ratio were 1.121 and 0.590 dex. In the 10–12 Myr entropy-switch pairs, the largest change in lobe enthalpy gained per unit of delivered energy was 0.097 dex at the primary tracer cut and 0.114 dex across all three cuts. The collaboration kept the 12–20 Myr continuations deferred on the basis of this larger **geometric** uncertainty. Estimating scatter in recovered enthalpy would also require pressure measurements. [Paired native measurements at each tracer cut](assets/low_power_entropy_review_2026-11-23/four_case_increments_by_cut.csv)

## Verification and reproduction

Codex (OpenAI, GPT-6) ran the frozen scorer after matching the scoring manifest and every target raster to their commitments. Claude (Anthropic, Fable 5.2) replayed all 1,056 masks before the targets were released, then rescored all 2,112 side–label rows. All 23 shared fields agreed with the original-site table. Claude independently summed physical pixel areas for truth, selection and overlap and reproduced completeness and purity. His rescoring used the project aperture function. Codex subsequently checked aperture contact directly from the physical radius of each selected pixel centre and its four face neighbours. All 2,112 contact flags agreed. Combining that calculation with Claude’s independent overlap areas recovered every pass decision. [Prediction and scoring custody](xray_prediction_seal_2026-11-23.md)

The compressed table decompresses to the original CSV with all native qualification flags, SHA-256 `717680dbe1c5ac98c579aee1681cf527385115c73f4aac6678b19050470cee11`. Rows are keyed by `unit_id`, mask `key` and `hemisphere`. The `primary` field selects the retained-linear image correction and the registered velocity cut for the assisted method. Blank purity denotes zero selected area. Blank completeness on an initial control denotes zero target area. The inputs retain their native sky-coverage, emissivity and boundary qualifications. [Score reduction and aperture check](../../scripts/science/summarise_heldout_xray.py)

From the repository root, the first command reproduces the registered counts from the score table. Reviewers with the two original private archives can also reproduce the depth and brightness measurements and check all aperture contacts with the second command.

```sh
.venv/bin/python scripts/science/summarise_heldout_xray.py
.venv/bin/python scripts/science/summarise_heldout_xray.py \
  --private-archives "$PREDICTION_TAR" "$SCORING_TAR"
```
