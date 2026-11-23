# Does jet-tracer weighting hide older radio-emitting particles?

In G-HI at 20 Myr, removing the jet-tracer emissivity weight brightened the old particle population, steepened the integrated spectrum and lowered its fitted break from **56.02 to 20.11 GHz**. Both fits put the break above the highest observed frequency of 15 GHz. The spectral age remains an upper limit in this view. [Fitted parameters and original control](assets/radio_tracer_weight_check_2026-11-23/result.json)

## Comparison fixed before reading the unweighted spectrum

Use G-HI at nominal 20 Myr, particle output 2000 and the original primary 45-degree radio view. This is the previously exposed G-HI development snapshot. Leave the 54 held-out detector views sealed. Select all active jet particles used in the published radio calculation. Keep the five frequencies, particle histories, cooling, magnetic field, geometry, ray integration and continuous-injection fit fixed. Compare the published emissivity with the same emissivity evaluated at unit tracer for each emitting particle. Use each arm's lossless spectrum to estimate its injection index as in the production fit.

Gemini predicts that removing the tracer factor brightens older electrons relative to recently accelerated electrons, steepens the high-frequency spectrum and lowers its fitted break. Report whether the break crosses into the 0.15–15 GHz band. The weighted control must reproduce the published five luminosities in both loss models and the published break classification before interpreting a difference. Examine the actual tracer passed to PRAiSE2, its relation to time since injection and time since the last qualifying shock, and how the tracer factor affects the source at each frequency. A single pair measures this snapshot and view.

## What changed in this view

| Radio quantity | Production tracer weight | Unit tracer |
| --- | ---: | ---: |
| Injection index fitted from the lossless spectrum | 0.6000 | 0.6000 |
| Spectral index between 1.4 and 15 GHz, full losses | 0.6210 | 0.6448 |
| Best-fit break, GHz | 56.02 | 20.11 |
| Reportable lower bound on break, GHz | 15 | 15 |
| Share of 15-GHz luminosity from particles last shocked 10–20 Myr ago | 4.76% | 10.51% |
| Share of 15-GHz luminosity from particles last shocked within 1 Myr | 60.60% | 33.49% |

With unit tracer, luminosity grew by factors of 4.85, 4.84, 4.82, 4.76 and 4.56 at 0.15, 0.5, 1.4, 4.5 and 15 GHz. The small frequency dependence of that large brightening changes the fitted curvature. Of the 75,481 particles emitting at 0.15 GHz, those last shocked within 1 Myr had a median jet fraction of 0.797. Those last shocked 10–20 Myr earlier had a median of 0.107. The rank correlations between tracer fraction and time since the recorded shock and since injection were −0.578 and −0.609, respectively. The change in the measured spectral index is 0.024. The two numerical break frequencies are model fits beyond the measured band. [Five-frequency spectra](assets/radio_tracer_weight_check_2026-11-23/spectra.csv) · [Age groups and ray-traced light fractions](assets/radio_tracer_weight_check_2026-11-23/particle_age_bins.csv)

Gemini's predicted preference for young particles is present in this case. The single exposed view does not determine how many of the other breaks would move into band. The original radio surface has **37 above-band breaks in 57 retained views** (19 case-ages, three angles each). The older X-ray detector selected 37 of those views, of which **20** have an upper spectral-age limit. Those counts describe different sets of sightlines. [Original radio fits](assets/four_case_boundary_spectral_field_review_2026-08-28/spectral_break_frequencies.csv) · [Historical detector-selected counts](assets/q029_binary_native_refresh_2026-09-06/power_refresh/age_power_method_summary.csv)

## Source and control checks

The native output holds 78,952 physical particle IDs. The production emitter selected 78,918 active histories. The analysis used all 78,918 in their original order and matched the emission time, tracer, pressure, density, injection time and last-shock time against the native file. The smallest tracer value was 0.001537. All weights were positive, so dividing each particle's archived full-loss and lossless emissivity by its own tracer recovers its unit-tracer emissivity directly. This also preserves the production handling of recently injected particles and all other zero-emissivity cases. The spectrum uses the same gas pressure, density, local magnetic field, loss histories, Doppler factors and integration paths in both arms. In particular, the estimated global field used for an age conversion enters after the spectrum has been fitted. [Producer](../../scripts/science/g_lo_snapshot_radio.py) · [Verified field and emissivity formulas](gemini_review_assessment_2026-11-21.md#22-november-2026--how-praise2-uses-the-jet-tracer)

For each arm the production continuous-injection model fits the injection index to the five lossless luminosities. It then fits the break in log frequency to the five full-loss luminosities, allowing a free amplitude, over $10^{-4}$–$10^{5}$ GHz. Only 0.15–15 GHz is observed. The control reproduced all ten originally published luminosities exactly at their stored precision. Its fitted break differed from the archived fit by 0.000008 GHz, within the original cross-platform tolerance. The extra age-group integrals sum to the full 0.15- and 15-GHz luminosities in both arms to relative precision $10^{-12}$. [Original fitter](../../scripts/science/snapshot_inference.py) · [Age-group calculation and weighted-control check](../../scripts/science/check_radio_tracer_weight.py)

## Reproduction

The project archive holds the input slice and the native particle file under `turn26_radio/`. SHA-256 is `3b367a6009462161f4c4f4fc095adba0c28cacb0a8a55a4cd3bdcebbb730510e` for the slice and `a4e8e783045734aae2ed10ccb26085b5e1cca5757fa41d5c9141f7c84da73eee` for `particles.2000.dbl`. The extractor checks the parent emissivity HDF5 digest `aa0dd8f53e41e3e4e480194a95ac8ad3978ad8955e9ecd7217f7f1cde52b3631`. The production metadata records the generating history-cache digest `069755aa70d02df4f8988a27d89dc0d93d26cd4d0a98a6004b74e640b3494c8d`; the five input fields read for this experiment also agree value for value with the original particle snapshot. The JSON result records the model, ray-tracer and original table hashes. [G-HI production metadata](assets/four_case_selected_age_observables_2026-08-26/completed_radio_pair_1/G-HI/g_lo_snapshot_radio_metadata.json) · [Slice extractor](../../scripts/science/check_radio_tracer_weight_inputs.py)

The following command reproduces the calculation from the repository root with `plutokore.radio` from production commit `73210e15d4c60e77ffb317b3ee2b9209c049edd4` on the Python import path.

```sh
d=private_archive/turn26_radio
.venv/bin/python -m scripts.science.check_radio_tracer_weight "$d/G-HI_20_particles.npz" "$d/particles.2000.dbl" "$d/replay"
```

To regenerate the slice from the production HDF5 files, run the extractor with the history cache and emissivity store as arguments and redirect its binary output to `G-HI_20_particles.npz`. The public `spectra.csv` alone suffices to refit both breaks.
