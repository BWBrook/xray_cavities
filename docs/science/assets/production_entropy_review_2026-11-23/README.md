# Production exterior energy balances

Run `python3 scripts/science/review_production_entropy_history.py` from the repository root. The program uses the Python standard library and the five versioned inputs listed in [the input and cross-check record](input_and_crosscheck.json). Use `--output DIRECTORY` for a fresh replay.

## What the balances measure

The production runs saved one output about every million years. We integrated the primary net injector and outer-face rates by the trapezoidal rule on the actual output times. The injector uses the reconstructed face states and shock flags (`linear_snapshot_flags`), and the domain faces use the outermost active cells. The whole-grid energy stock includes thermal, kinetic and gravitational energy with the potential zero at the centre.

Write $D$ for the signed gas energy supplied by the injector, including pressure work. Its potential-energy flux $D_\Phi$ and the change in energy in maintained injector cells $\Delta E_{\rm flag}$ enter separately. With $F$ positive for outward transport through the full domain, the exterior residual is

$$R=\Delta E_{\rm grid}+F-D-D_\Phi-\Delta E_{\rm flag}.$$

The independently summed fixed-box and outer-shell stocks satisfy

$$R-(\Delta E_{\rm box}-D)=\Delta E_{\rm shell}+F-D_\Phi-\Delta E_{\rm flag}.$$

Both comparisons use the same injector delivery. The right side gives the **net** shell balance. Sources inside the shell and transport across the unmeasured inset faces could cancel. The fixed-box and R100 stocks also cannot distinguish acoustic transport from other changes in the enclosed gas. Each R100 stock is a current-minus-initial difference over the aperture at that snapshot. An interval difference between two such stocks uses two different apertures. At late high-power outputs the finite grid clips the sphere. See [the geometry checks](../../turn15_energy_emission_review_2026-11-11.md) and [fixed-box definitions](../../four_case_fixed_histories_2026-11-18.md).

## Tables

- [Annual balances](annual_balances.csv) cover all 197 adjacent production intervals. The final two columns track the cumulative exterior residual at every saved age. G-LO’s interval residual is negative at indices 7–14, positive at 15–49 and negative at 50. Its cumulative residual is negative at indices 12–16 and positive again at 17. The first interval in G-LO is also negative. At the three 50-Myr endpoints a brief programmed speed dip falls between outputs. The published R100 and box measurements and these energy budgets all retain their actual snapshot ages. [Terminal velocity and tracer check](../../three_case_final_interval_2026-11-19.md)
- [Milestone and decade balances](milestone_and_decade_balances.csv) give cumulative windows beginning at zero and disjoint windows ending near 10, 20, 30, 40 and 50 Myr (47 for G-HI). Divide integrated energy by each window’s labelled energy or delivered gas energy as specified in the column name. A decade value of 0.3274 means 32.74% of the energy labelled over that decade. Column `alternative_face_exterior_over_label` shows how the estimate changes with the outer-face prescription. The controlled restarts support the primary choice. The late G-HI extrapolated face value is unavailable.
- [Restart calibration](restart_calibration.csv) uses the 10, 11 and 12 Myr snapshots of each arm for the annual face and injector sums, all 21 saved snapshots for the fine sums, and the stage-weighted changes reported directly by the solver. With the switch on, its entropy update accounts for the measured signed residual in that window. With it off, the solver counter includes ordinary floor repairs. A 12-Myr restart ends at exactly 12 Myr. The original production endpoint can be slightly earlier. The production column uses its actual interval durations. These are jet-on experiments. A direct test of the unperturbed production-grid atmosphere would require a matched no-jet control. At other ages these production budgets lack a stage-resolved solver counter.

All 197 reconstructed exterior residuals agree with the archived interval reductions within $1.5\times10^{-14}$ of the interval label. The shell identity, using a separate fixed-region reader, closes within $2.4\times10^{-10}$ of interval label. Agreement tests the accounting. The late-time residuals support a changing numerical energy source, while the process generating a given residual, the evolution with the switch off and the lobe response at 20–50 Myr require distinct evidence.
