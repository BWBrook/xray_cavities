# Goal 065 log

## 2026-08-26 - complete local scientific synthesis

- Joined the accepted Goal 062 fluid/gravity/tracer/shock surface, Goal 063
  background and shock-validity gates, and Goal 064 X-ray/cavity and
  corrected-PRAiSE2 products at `10/20/30/40/50 Myr`.
- Preserved the exact two-component X-ray topology gate, the `G-HI`
  shock-validity exclusion at 50 Myr, the tracer-shell pressure label, and the
  `C-LO` background-dominated ambient-energy caveat.
- Built compact surfaces for cavity recovery, shock-Mach sensitivity, radio
  scaling power, integrated spectral fits, cavity/spectral and cavity/age
  power inference, descriptive factorial effects, and provenance.
- Kept inference descriptive: four deterministic factorial cells, no
  replicate p-values, and explicit leave-one-case-out sensitivity.
- Test 1 found a strong pooled negative cavity-bias/Mach pattern that becomes
  weak and sign-sensitive after case/view adjustment.
- Test 2 found `2.5pV / t_spec` strongly case dependent, with `40/60` spectra
  carrying an out-of-band censored break.
- Test 3 found both tested radio-luminosity relations systematically dependent
  on power and environment rather than universally unbiased.
- Generated and visually reviewed the four-panel synthesis figure. One focused
  repair added the missing case/view legend and clarified the bottom-right
  axis label.

Validation:

```text
uv run pytest tests/test_four_case_scientific_synthesis.py tests/test_snapshot_synthesis.py tests/test_snapshot_inference.py -q
16 passed in 0.85s
```

Decision:
`FOUR_CASE_SYNTHESIS_COMPLETE_SUPERVISOR_INTERPRETATION_READY`.

Status: `complete_local_scientific_synthesis`.

No remote command, PBS job, raw-data access, observable recomputation,
scientific-default change, or accepted-asset overwrite occurred.

## 2026-08-31 - corrected synthesis after supervisor method review

- Applied Stas's boundary directive by excluding `G-HI/50` from every
  scientific surface while retaining its source files as archival evidence.
- Replaced the former single spectral-age power surface with seven separate
  clocks: true, sound crossing, buoyant rise, refill, bilateral supersonic
  shock, mean-pressure spectral, and emissivity-weighted spectral age.
- Made mean-pressure spectral age primary, emissivity-weighted spectral age a
  sensitivity, and above-15-GHz breaks explicit age upper limits/power lower
  limits excluded from ordinary medians.
- Rebuilt all case medians, row counts, radio summaries, factorial contrasts,
  provenance, metadata, and the synthesis figure.
- Confirmed that clock choice changes inferred power by factors of a few but
  does not explain the severe high-power X-ray cavity-energy deficit.
- Locked the next scientific question as a dual-space energetics audit that
  independently computes native-grid truth and observer-like X-ray recovery
  before decomposing volume, pressure, enthalpy, and missing-outburst biases.

Decision:
`FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT`.

Status: `complete_corrected_local_scientific_synthesis`.

No remote compute, raw HDF5 access, observable rerun, PLUTO production, or
scientific-default change occurred.
