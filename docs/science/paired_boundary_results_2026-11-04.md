# Paired boundary controls: measured results

## Whole-grid prediction

Both completed 50-Myr atmosphere pairs support the corrected, predeclared
BND-02 boundary-inflow prediction. This is a result for the uniform 1-kpc
controls. It supports the proposed mechanism for the production excess; it
does not by itself certify the production grid or an interior exclusion.

| Quantity at 50 Myr | Cluster | Group |
| --- | ---: | ---: |
| Outflow-minus-reflective mass change (g) | 4.76270e43 | 2.29025e42 |
| Hydrodynamic-energy contrast (erg) | 3.48861e59 | 4.05132e57 |
| Total H+P contrast (erg) | 7.00826e59 | 1.21480e58 |
| H+P contrast / low-power bipolar comparison S(50 Myr) | 22.21 | 0.3850 |
| Mass / predicted mass | 0.97998 | 0.96229 |
| H+P / predicted H+P | 0.97337 | 0.93446 |
| Mass-growth exponent, 10–50 Myr | 1.96610 | 1.93257 |
| Mass transport discrepancy / mass contrast | 5.12e-12 | 1.45e-11 |
| H+P transport discrepancy / H+P contrast | 6.47e-7 | 2.96e-6 |
| Gross repair + absolute residual / absolute H+P contrast | 3.956e-4 | 1.523e-4 |
| Frozen decision | supported | supported |

The mass contrasts exceed the fixed floors, growth exponents lie inside
[1.6, 2.4], and both two-sided transport discrepancies are below 10%.
Accounting contamination is 0.0396% and 0.0152%, respectively, well below its
separate 10% limit. Amplitudes agree within 2–7%; the factor-of-two and 30%
comparisons remain descriptive, as frozen before inspection.
Here `S(t)=2e43 erg/s * t` is only a common scale: these controls contain no
jet and have no injected jet energy. On that scale, the cluster boundary
effect is large enough to account for an apparent excess of about 22 times
the low-power jet input, whereas the group effect is about 0.385 times.

Face H alone accounts for 97.65% and 98.49% of the respective H contrasts.
Adding gravitational work and net conversion repair closes those H identities
to approximately 1e-11 relative precision. The primary attribution test uses
H+P, where fixed-potential gravitational exchange cancels internally. Gross
repair and absolute residuals are retained separately so cancellation between
twins cannot hide substantial accounting contamination.

These ledgers establish a controlled boundary-condition effect at the coarse
resolution. The prediction's production-reference amplitudes were supplied by
the earlier Q-029 analysis and were not independently remeasured here.
Near agreement does not prove resolution independence, explain every
production-grid energy discrepancy, or establish quiet background gas inside
a particular cut. The native interior measurements address the last question.

## Provenance and decision history

The scientific contract was committed as `e56b89f` before capturing the full
ledgers. The capture contains all four ledgers, their budget/output receipts
and four terminal scheduler records. All 16 payload hashes verified locally
and on the project data share. Native output receipts establish the initial
field/grid/configuration identity of each pair; the independent ledger
validator was rerun against the captured bytes.

The first comparison stopped because Python 3.12's compensated sum and the
original Python 3.11 sum differ by 1–3 rounding units in six-face aggregate
transport. This was traced to identical validator source and reproduced by
left-to-right summation. Commit `71bbdbe`, made before computing scientific
contrasts, applies an explicit `8u sum(abs(face terms))` arithmetic bound and
propagates it to the residual receipt checks. Counts, hashes, gravity, repair,
ledger closure thresholds and scientific decision thresholds were unchanged.
Original receipts were preserved; every numerical delta and bound appears in
`provenance.json`. This technical correction followed capture and is not
represented as part of the original freeze.

Each twin is validated and interpolated independently at the frozen physical
ages 10, 20, 30, 40 and 50 Myr, with bracketing ages, steps and interpolation
fractions recorded. In this capture the paired histories happen to share
the same step times; different file sizes did not imply different histories.
No extrapolation or step-index intersection is used. Independent review
reproduced all three comparison products byte-for-byte and verified the final
contrasts directly. A diagnostic fit across native states gives exponents
1.95871 and 1.92851, consistent with the frozen five-age decision; it does not
replace that prespecified fit.

Tracked products:

- `assets/paired_boundary_comparison_2026-11-04/paired_contrasts.csv`
- `assets/paired_boundary_comparison_2026-11-04/verdict.json`
- `assets/paired_boundary_comparison_2026-11-04/provenance.json`
- `assets/paired_boundary_comparison_2026-11-04/analysis_receipt.json`

Raw payloads are retained outside Git in the project data share under
`bnd02_ledgers_2026-11-04_r1/`; the downloaded archive SHA-256 is
`cebd91ce46aa7b3ed7c3c68e8263b7627a0a02dc7a0768de7bad8190c26763a1`.
Reproduce into a new output directory:

```bash
uv run python scripts/science/compare_paired_boundary_prediction.py \
  <ledger_capture_directory> <new_output_directory>
```

## Interior smoke at 0.25 Myr

The 58-test target smoke finished F/0 in 21m 44s. All native-input and stage
checks passed, and the completion receipt binds both measured pairs. The
frozen decision overlay independently verifies the original stage sources and
output hashes. It retains the measured sums and supersedes only r1's
paired-only adoption label.

The table gives the largest of the four component L1 sums, divided by
`0.01 S(0.25 Myr)`. A value at most one passes. Each individual component is
retained in `assets/paired_boundary_interior_2026-11-04/smoke_decision.json`.

| Atmosphere | Cut (kpc) | Paired contrast / bound | Reflective drift / bound | Outflow drift / bound |
| --- | ---: | ---: | ---: | ---: |
| Cluster | 0 | 15.323 | 109.314 | 123.027 |
| Cluster | 1 | 0.9554 | 57.685 | 57.042 |
| Cluster | 2 | 0.1596 | 12.528 | 12.682 |
| Cluster | 4 | 0.00143 | 6.063 | 6.064 |
| Group | 0 | 0.2658 | 4.340 | 4.591 |
| Group | 1 | 0.00881 | 2.412 | 2.406 |
| Group | 2 | 0.00163 | 0.6102 | 0.6118 |
| Group | 4 | 0.00000818 | 0.4792 | 0.4792 |

Thus the cluster's first passing localization cut is 1 kpc, but its absolute
background drift fails at every tested cut. In the group the whole-grid paired
contrast already passes the absolute bound, while both twins first satisfy
the background-stability bound at 2 kpc. Paired agreement alone is insufficient
for adopting a boundary-safe region. The 1-kpc smoke hypothesis is supported
as a localization statement; it is not a statement that the retained gas is
quiet in each simulation. No cut at 50 Myr follows from these early outputs.

The cluster's 1-kpc localization pass has only a 4.5% margin against the
declared bound; 2 kpc reduces the paired maximum to 0.1596 of the bound.
Total-energy L1 sets every table maximum. At 4 kpc, the cluster's thermal and
gravitational drift alone are about 4.39 and 1.68 times their bounds.
Signed total changes are only about 4.6% of the total L1 drift there, showing
why signed cancellation would give a misleading stability assessment. In
the group, gravitational drift still fails at 1 kpc (about 1.46 times its
bound), while thermal drift is just below its bound. Near-equal drift in the
twins is a descriptive common pattern; its physical or numerical cause has
not been identified by this comparison.

Independent review verified the archive, source, completion and decision
hashes and reproduced every table maximum and first passing width.

Raw smoke capture SHA-256:
`fc2d4c86300fb4f0ce4c27ca4b30af718b41c27d41e143ac265f7cd4217df93f`.
Reproduce the decision from the extracted immutable stage:

```bash
uv run python scripts/science/summarize_paired_boundary_interior.py \
  <smoke_capture_directory> smoke <new_decision_json>
```
