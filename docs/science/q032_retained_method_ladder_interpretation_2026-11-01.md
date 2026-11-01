# Q-032 retained 60-view method ladder: interpretation

Claude (Opus 5.5, `claude-opus-5-5`) wrote this note on 1 November 2026 from
the products of PBS `870640`. Codex (GPT-6) staged, ran, retrieved and
independently verified those products (`remote_evidence/`,
`independent_review_2026-11-01.json`). This note is a diagnostic. It adopts no
production detector, and the observer conclusions stay provisional.

## What was run

The five observer rungs were legacy 1% area, Goal 045 seed-and-grow, and the
radial-median deficit threshold at 5%, 10% and 20%. They ran on the retained
corrected 1 keV XRAiSE maps:

- four cases, at 10–50 Myr and views 0/45/90°;
- 60 views and 600 method–side rows.

G-HI at 50 Myr is processed but excluded here, as the packaging receipt
requires. That leaves 57 views and 114 sides per rung. No t=0 baseline was
used.

Reproduce with:

```bash
uv run python scripts/science/summarise_q032_retained_ladder.py \
  docs/science/assets/q032_retained_method_ladder_2026-10-31/results/method_ladder_rows.csv \
  docs/science/assets/q032_retained_method_ladder_2026-10-31/interpretation \
  --native-root docs/science/assets/q029_binary_native_refresh_2026-09-06/remote_analysis
```

**Conventions.**
- All-sides statistics count an undetected side as zero volume.
- Volumes are revolution volumes, π Σ|u| dA.
- Two references:
  - the projected tracer mask (LOS-max tr1 > 1e-3) under the same revolution;
  - the native 3D binary tr1 > 1e-3 lobe volume of the same hemisphere, from Q-029.
- The projected-tracer reference overestimates the native volume by a median
  factor of 1.09–1.18 per case. It is a fair proxy, and every conclusion below
  holds against either reference.

## Results

### Recovered / native 3D volume

Median over ages, views and sides; undetected sides count as zero.

| Rung | C-HI | C-LO | G-HI | G-LO | Detected sides |
| --- | ---: | ---: | ---: | ---: | ---: |
| Legacy 1% | 0.02 | 0.50 | 0.01 | 0.10 | 110/114 |
| Seed-and-grow | 0.46 | 0.27 | 0.30 | 0.00 | 83/114 |
| Deficit 5% | 1.08 | 0.38 | 0.78 | 0.46 | 99/114 |
| Deficit 10% | 0.39 | 0.00 | 0.37 | 0.24 | 86/114 |
| Deficit 20% | 0.11 | 0.00 | 0.23 | 0.00 | 60/114 |

### Factorial contrasts

Values are log10 of the volume ratio. Both sides are summed, then the median
is taken over ages 20–40 Myr and the three views; n counts the pairs in which
both sides were detected.

| Contrast | Native | Projected tracer | Legacy 1% | Seed-grow | Deficit 5% | Deficit 10% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Cluster power, C-HI/C-LO | 1.57–1.68 | 1.63 | 0.23 | 1.89 (8/9) | 2.14 (8/9) | 2.23 (2/9) |
| Group power, G-HI/G-LO | 1.43–1.56 | 1.52 | 0.37 | 1.15 (2/9) | 1.78 | 1.83 |
| High-power environment, C-HI/G-HI | −0.54 to −0.61 | −0.58 | −0.15 | −0.70 (8/9) | −0.50 | −0.55 |
| Low-power environment, C-LO/G-LO | −0.68 to −0.73 | −0.68 | −0.03 | +0.25 (3/9) | −1.16 (8/9) | −1.16 (2/9) |

## Findings

1. **The legacy 1% selector cannot carry the factorial comparison.** Its
   fixed area compresses the native power contrast of about 1.6 dex to
   0.2–0.4 dex, and it erases the environment contrast.
   - Recovered/native is 0.01–0.02 in the high-power cases.
   - At early low-power ages it scores nine zero-overlap detections (C-LO
     10/20 Myr and G-LO 10 Myr). The selected deficit there lies off-axis, so
     its revolution volume is 9–99 times the tracer's.
   - This confirms, across all 60 views, the 21 October concern that Stas
     raised. Observer volume, enthalpy and power claims built on it should
     not survive in their current form.

2. **The deficit thresholds overstate the contrasts and depend on the case.**
   Detection fails on faint low-power cocoons, so the low-power denominators
   shrink or vanish.
   - The 5% rung exaggerates the cluster power contrast by about 0.5 dex and
     the low-power environment contrast by about 0.5 dex.
   - At 10% and 20%, C-LO is barely detected (10/30) or not at all (0/30).

3. **Agreement in volume is not agreement in geometry.**
   - **C-HI at 5%.** Recovered/native is 1.08, but completeness is only 0.36
     and purity 0.70–0.77. The match comes from two errors cancelling: about
     a quarter of the recovered area lies outside the tracer, while only a
     third of the tracer is recovered.
   - **Late G-LO and G-HI 20–30 Myr at 0°.** The 5% mask merges with
     background deficits across the midplane. Purity drops to 0.25–0.5 and
     volume inflates 3–13 times.
   - The detected-side median purity of 1.00 hides all of this. Purity has
     to be reported per side.

4. **Seed-and-grow is the most geometry-faithful rung where it fires, but it
   cannot be trusted in the group low-power case.** It fails G-LO: 12/30
   detected, and a median of zero. That leaves its group contrasts
   undefined in 7 of 9 pairs.

5. **The 120 kpc aperture caps late high-power recovery.**
   - The tracer area inside the aperture falls to 0.92, 0.72 and 0.57 for
     C-HI at 30, 40 and 50 Myr.
   - It falls to 0.87 and 0.64 for G-HI at 30 and 40 Myr.
   - So the aperture is not a neutral choice: it removes up to 43% of the
     late high-power cocoon from any method.

6. **View dependence is modest for the fixed-area and seed rungs and large
   for thresholds.** The median max/min of the all-sides ratio across the
   three views is 1.29 for legacy, 1.40 for seed-and-grow, and 1.9–2.9 for
   the deficit rungs.

7. **Topology.** The 5% rung yields connected cross-midplane components in
   24 of 57 views. Production rejects these, and some are background merges
   rather than touching lobes. The topology rule still needs the
   scale-aware validation arm agreed on discussion 29.

## Consequences

- No rung is acceptable for production. This agrees with the synthetic
  harness (r2) on the native simulation maps themselves.
- The failures fall into two classes, and they need different repairs:
  - **detection efficiency** that depends on cocoon contrast (thresholds,
    seed-and-grow on G-LO);
  - **segmentation**: background merging, the off-axis legacy selection and
    aperture clipping.
- A replacement must be judged on per-side completeness and purity and on
  factorial contrasts, not on volume ratios alone. Volume ratios near unity
  occur through compensating errors.
- **Next rungs, in order:**
  1. a t=0-baseline run on the same 60 views (the code exists:
     `--baseline`);
  2. aperture sensitivity at 120 kpc versus a footprint-enclosing aperture;
  3. a background-merge guard tested on the cases listed in finding 3;
  4. the topology validation arm.

  Each is post-processing of retained maps. None needs a new simulation.

## Limits

- The references are tracer-defined cocoons, not X-ray-visible cavities. The
  Q-031 native emission pilot (PBS `871717`, held) will give the shell and
  cocoon emission terms that separate the two.
- Revolution volume assumes axisymmetry per hemisphere. The native
  half-plane integrals in Q-031 test that separately.
- Ages are 10-Myr snapshots with three views each. Within-case statistics
  are correlated across views.
