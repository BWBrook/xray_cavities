# The last Myr of jet activity in C-HI, C-LO and G-LO

C-LO’s inferred whole-grid energy source fell by **0.0232–0.0294** of labelled interval input from 48–49 to 49–50 Myr. This was less than half the decline in either C-HI or G-LO. C-LO also had an earlier drop of at least this size within the preceding ten interval-to-interval changes under every boundary treatment. The final drops in C-HI and G-LO exceeded all ten preceding drops under each treatment. G-HI ends at 47 Myr.

| Case | Whole-grid source at 48–49 Myr¹ | Whole-grid source at 49–50 Myr¹ | Change in whole-grid source² | Change in nozzle source² | Change in outside balance² |
| --- | ---: | ---: | ---: | ---: | ---: |
| C-HI | 0.98740 | 0.92878 | −0.05866 to −0.05860 | −0.00068 to +0.00221 | −0.06087 to −0.05796 |
| C-LO | 1.48980 | 1.46459 | −0.02938 to −0.02318 | −0.00017 to +0.00692 | −0.03630 to −0.02302 |
| G-LO | 1.18438 | 1.12254 | −0.06188 to −0.06183 | −0.00498 to +0.00028 | −0.06213 to −0.05687 |

¹ Outer active cell boundary reconstruction and trapezoidal integration, normalised by labelled bipolar kinetic power times the actual active duration of each interval. ² Final minus preceding, with each reconstruction and integration rule paired with itself. The 36 combinations per case cover two outer-face methods, three time rules and six nozzle reconstructions. The outside balance is the difference between the whole-grid and nozzle sources. [All 108 paired comparisons and ranges of the ten preceding changes](assets/three_case_final_interval_2026-11-19/matched_final_intervals.csv)

In C-LO the change in the net source was small relative to both terms that determine it. At the tabulated boundary choice the rate of increase in stored energy rose from 45.601 to 46.529 times labelled power. Net outward transport became more negative, from −44.111 to −45.065. Their sum fell by 0.02522. Across the available methods the C-LO outside balance fell in every comparison, although its final value ranged from −1.790 to +0.815.
<!-- claims: BND-08 -->

## What the prescribed velocity dip predicts

The retained source sets the velocity multiplier to `1 − cos(πx/2)` as the phase `x` increases from zero to one in the last 0.05 source Myr before the cycle wraps. Density and pressure have separate prescriptions. With fixed density the ideal kinetic power scales with the cube of this multiplier, whose mean over the ramp is `5/2 − 22/(3π) = 0.16573`. The source and output time conventions put the dip at **49.91548–49.96545 Myr** on the output clock. The snapshots on either side both correspond to full prescribed speed.

Accounting for the analytic steady kinetic power in each case and its actual interval duration, the ideal kinetic shortfall is **0.04164–0.04167** of labelled interval input. This amounts to 71% of the measured decline in C-HI, 67% in G-LO and **142–180% in C-LO**. These percentages compare magnitudes. The saved outputs omit the dip and its propagation to the control surfaces. They cannot measure what share of the whole-grid decline the change in nozzle primitives caused. The terminal balances do show that nearly all of the measured decline appears outside the reconstructed nozzle volume. The retained source-to-executable linkage also remains qualified. [Per-case times and ideal kinetic shortfall](assets/three_case_final_interval_2026-11-19/source_clock.csv)

The tracer supplies a separate check on the timing. Mass loading scales with the first power of velocity. The tagged-mass growth rates fall by 3.12%, 3.18% and 3.10% in C-HI, C-LO and G-LO, close to the 3.18% ideal mass reduction over this interval. [Tagged mass through the cycle](tracer_mass_budget_2026-11-19.md#what-happens-at-the-end-of-the-cycle)
<!-- claims: BND-10 -->

## Reproduce

Restore the [19 November calibration archive](nozzle_flux_calibration_2026-11-19.md#reproduction) under `private_archive/`. From the repository root, run the following command with a fresh output directory.

```sh
.venv/bin/python scripts/science/compare_final_source_intervals.py \
  --calibration private_archive/turn19_nozzle_calibration \
  --output private_archive/final_interval_replay
```

A fresh restore reproduced both published tables byte for byte. An independent calculation checked the 108 scenario pairs against the per-interval and cumulative balances in the three original completion receipts and integrated the endpoint face rates directly. Across 2,487 numerical checks, the largest absolute difference was below 8 × 10⁻¹⁴ in labelled units.
