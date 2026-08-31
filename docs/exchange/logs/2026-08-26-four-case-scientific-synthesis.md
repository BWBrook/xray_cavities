# 2026-08-26 - four-case scientific synthesis

Goal 065 completes the first joined scientific analysis of the matched
four-case factorial. It combines Goal 062 fluid/gravity/tracer/shock evidence,
Goal 063 background and age-validity decisions, and Goal 064 selected-age
X-ray/cavity and corrected-PRAiSE2 products.

The synthesis preserves all consequential gates. Cavity energy is quantitative
only for exactly two non-crossing opposite-side X-ray components; `G-HI` at
50 Myr is excluded from shock-kinematic tests; `C-LO` whole-domain ambient
energy is not interpreted as coupling efficiency; pressure remains a
tracer-shell proxy; and the deterministic `2x2` factorial receives no
replicate-based p-values.

The three prespecified decisions are now explicit:

1. Cavity-energy recovery has a strong pooled negative association with shock
   Mach, but the case/view-adjusted effect is small and leave-one-case-out
   slopes change sign. Mach is not independently identified.
2. Adopted `2.5pV` divided by integrated spectral age is not a universal power
   estimator. Matched-field median recovery spans `0.00650` to `1.55` across
   cases, and `40/60` spectra have an out-of-band censored break.
3. Standard 150 MHz and 1.4 GHz radio relations show systematic power and
   environment dependence. They do not recover a common unbiased bipolar jet
   power across the factorial.

The package contains joined CSV surfaces, compact sensitivity summaries, one
reviewed four-panel figure, provenance, metadata, and tests. Focused validation
passed with `16` tests. No remote compute or raw-data access was needed.

Decision:
`FOUR_CASE_SYNTHESIS_COMPLETE_SUPERVISOR_INTERPRETATION_READY`.

Status: `complete_local_scientific_synthesis`.

The next high-value step is supervisor interpretation of the paper framing,
not another engineering pass or another simulation/observable run.

## 2026-08-31 correction after supervisor review

Stas's new method directives materially supersede the original Test 2 and the
use of `G-HI/50`. The synthesis has therefore been rebuilt rather than merely
annotated.

- `G-HI/50` is absent from every downstream scientific table and summary.
- The retained cavity surface has `37` quantitative case-age-view rows and
  `74` side components.
- Seven cavity ages remain separate; no fixed `t_buoy=2t_cs` approximation is
  used.
- Mean-pressure spectral age is primary and emissivity-weighted spectral age
  is the sensitivity. Above-band breaks remain censored limits.
- True-age median `2.5pV` power recovery is `0.00810`, `0.628`, `0.00437`, and
  `0.0731` for `C-HI`, `C-LO`, `G-HI`, and `G-LO`.
- Mean-pressure spectral recovery is `0.0124` and `1.05` for the two cluster
  cases, while the group cases yield median lower bounds `>0.00321` and
  `>0.0871`.
- Corrected full-loss radio medians are `0.937/5.10`, `7.34/15.85`,
  `0.520/2.36`, and `4.03/7.02` at 150 MHz/1.4 GHz.

The scientific interpretation is now sharper: age bias modulates inferred
power but cannot explain the high-power cavity-energy deficit. The next
decision-relevant analysis is the independently calculated native-grid versus
observer-like X-ray energetics audit specified by Stas.

Decision:
`FOUR_CASE_SYNTHESIS_CORRECTED_DUAL_SPACE_AUDIT_NEXT`.

Status: `complete_corrected_local_scientific_synthesis`.
