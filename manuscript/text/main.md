# How well do X-ray cavities measure jet energetics?

<div id="authors"></div>

## Abstract

<!-- Maximum 400 words. State the question, four-case design, principal result, and implication. -->

## Keywords

<!-- Select 1-6 terms from the Unified Astronomy Thesaurus. -->

## Introduction

Numerical jet experiments embedded in realistic cosmological environments provide a controlled link between source dynamics and synthetic observables [@yatesJones2023Cosmodragon]. Synthetic X-ray observations further show that cavity enthalpy can be recovered reasonably well while source age and viewing angle remain important sources of uncertainty [@mendygral2011SyntheticCavities].

<!-- Establish the observational problem, knowledge gap, aims, and testable expectations. -->

## Methods

### Simulation design

We compare four jet simulations crossing cluster and group atmospheres with high and low jet power (C-HI, C-LO, G-HI and G-LO). The imposed bipolar powers are $2\times10^{45}$ and $2\times10^{43}$ erg s$^{-1}$, respectively. The analysis uses outputs near 10, 20, 30, 40 and 50 Myr, with actual output times retained in all energy and power calculations. G-HI at 50 Myr is excluded because the source reaches the simulation boundary, leaving 19 case-age combinations. These four simulations are factorial cases, not replicated samples of an astrophysical population.

<!-- Expand the numerical setup and environment description from the validated simulation documentation. -->

### Synthetic X-ray and radio products

<!-- Describe XRAiSE/PRAiSE2 products, viewing angles, masks, and common-age surface. -->

### Cavity geometry, age, and energetics

The primary native cocoon comprises cells with tracer $\mathrm{tr1}>10^{-3}$, evaluated after promotion of the stored tracer to double precision. Each selected cell contributes its full volume, mass and energy. Ambient cells satisfy the exact complement, $\mathrm{tr1}\leq10^{-3}$. Fractional tracer weighting and binary thresholds of $5\times10^{-3}$ and $10^{-2}$ provide sensitivity comparisons. The stored single-precision tracer can differ slightly from the nominal threshold; the largest contribution of cells at its stored representation is less than $2.6\times10^{-7}$ of native enthalpy on the selected surface.

Native enthalpy is $H_{\mathrm{native}}=\alpha\int_{\mathrm{cocoon}}p\,dV$, with $\alpha=2.5$ for the primary non-relativistic convention and $\alpha=4$ as a literature comparator. Thermal, kinetic and gravitational energies form a separate additive ledger. For each component we subtract the initial field in the same cells selected by the current cocoon mask, and do likewise for its ambient complement. These regional differences sum to the retained whole-domain energy change. They describe changes relative to the initial conditions in a current spatial region; they do not follow a material parcel or the evolving cocoon boundary. The initial snapshots already contain a nozzle region. Absolute current lobe energy therefore differs from the regional change, and subtracting the entire initial domain energy from the ambient allocation is not equivalent to subtracting only the initial ambient-region energy.

We normalize the primary native pressure estimate to the cumulative net gas energy transferred from the maintained injector to freely evolved cells at the identical case and actual output age. The signed cone and stationary-region fluxes are added before integrating the saved-state rates from the already initialized $t=0$ output. Gas-energy flux includes internal and kinetic energy and pressure work; it excludes gravitational-potential transport. The primary interface reconstruction is linear with the saved shock-flag fallback, and the primary time integral is trapezoidal. Left/right rectangles, first-order states and forced HLL/HLLC solvers provide sensitivity comparisons. These reconstructions omit intermediate Runge–Kutta states and the unsaved terminal velocity dip, so they are estimates of cumulative delivery rather than exact injection counters. Labelled bipolar kinetic power times actual active age, $E_{\mathrm{label}}$, remains a separate comparator. <!-- claims: NAT-01 -->

We identify shock-processed ambient gas using entropy excess connected to a compressed axial-front seed, with environment-matched no-jet noise calibration. The calculation retains the accepted supersonic-front, seed, extent, boundary, minimum-cell and bilateral validity gates. Selected cells contribute their full current-minus-initial energy, and are a subset of the ambient region. Shock energy must therefore not be added again to the full ambient energy change. The calibration is not a native-resolution cellwise no-jet subtraction. The saved whole-grid boundary and injector flux reconstructions do not measure transport through the moving shock or spherical apertures; agreement of the numerical partition identities does not establish a closed physical energy budget.

X-ray cavity measurements are evaluated independently of tracer-based membership. The primary comparison uses geometric depth, pressure averaged over the inferred ellipsoid, and the same enthalpy convention as the native estimate. We evaluate viewing angles of 0, 45 and 90 degrees and require a valid bilateral cavity topology. Invalid views remain unresolved and do not enter quantitative recovery summaries.

### Statistical comparisons

We report within-case ranges and medians across the accepted ages and views. These are descriptive summaries of repeated measurements, without population-level significance tests or an assumption that ages and views are independent. A factor of two provides a common descriptive recovery band. Spectral breaks above the fitted frequency range yield upper limits on age and lower limits on inferred power; these limits remain separate from exact estimates. Sound-crossing, buoyant-rise and refill clocks use the retained initial-atmosphere sound speed and gravity with the observed component geometry. The mean-pressure spectral clock retains its previously defined fractional-tracer global magnetic-field estimate; it does not use the X-ray pressure or the revised binary-cocoon pressure. The emissivity-weighted field supplies its separate sensitivity comparator.

## Results

### How much cumulative gas delivery does native enthalpy represent?

Native $2.5pV$ divided by reconstructed cumulative net injector gas delivery spans 0.4518–0.4810 in C-HI, 0.5827–0.9864 in C-LO, 0.4043–0.4306 in G-HI and 0.5417–0.6818 in G-LO over the selected actual ages near 10–50 Myr (G-HI ends at 40 Myr on this surface). The corresponding label-normalized ranges are 0.5249–0.5587, 0.6309–1.1075, 0.4682–0.4983 and 0.6147–0.7849; Figure [1](#fig-main-1) retains this labelled comparator. Thus C-LO's late pressure estimate exceeds the labelled kinetic reference but remains below the primary reconstructed cumulative gas supply. These are descriptive fractions for four deterministic cases, not calibrated injection efficiencies. Switching to $4pV$ multiplies every proxy ratio by 1.6. <!-- claims: NAT-01 -->

At the matched outputs near 30 Myr, the pressure estimate and spherical storage comparison are:

| Case | Actual age (Myr) | $2.5pV/D_{\mathrm{gas}}$ | $\Delta E_{R100}/D_{\mathrm{gas}}$ | $2.5pV/\Delta E_{R100}$ |
| --- | ---: | ---: | ---: | ---: |
| C-HI | 29.999994 | 0.4714 | 0.9326 | 0.5054 |
| C-LO | 29.999166 | 0.8714 | 1.0821 | 0.8053 |
| G-HI | 29.999367 | 0.4043 | 0.9322 | 0.4338 |
| G-LO | 29.999644 | 0.6673 | 1.0196 | 0.6545 |

Here $D_{\mathrm{gas}}$ is cumulative signed net gas delivery with the primary trapezoidal rule, while $\Delta E_{R100}$ is thermal-plus-kinetic-plus-fixed-potential change relative to the initial fields in the cells of the current R100 aperture. R100 includes physical cells whose centres lie no farther than the most distant cell with total speed at least 100 km s$^{-1}$; R300 uses 300 km s$^{-1}$. Both apertures contain the entire current lobe and are geometrically complete at these ages. A common external denominator leaves $2.5pV/\Delta E_{R100}$ unchanged. Current absolute pressure energy and signed storage remain different quantities: neither their ratio nor storage/delivery near unity establishes physical closure. Total storage also retains the gravitational-potential-zero dependence associated with regional mass change. <!-- claims: NAT-07 -->

Enthalpy also differs from the actual energy change in the current cocoon region. The latter spans 0.132–0.426 of injected energy in C-HI, 0.425–0.571 in G-HI and 0.013–0.298 in G-LO. In C-LO it ranges from −0.160 to 0.137. Negative gravitational changes relative to the initial fields contribute to this separation, and a negative net regional value does not imply negative absolute energy or a Lagrangian loss from the jet. Thermal pressure alone cannot represent all terms in this accounting.

The selected shock-processed ambient region contains energy changes of 0.666–0.765, 0.505–0.655 and 0.580–0.854 times the injected energy in C-HI, G-HI and G-LO, respectively. C-LO supplies one accepted estimate, 0.223 at 10 Myr; its four later ages fail the bilateral shock gate. This selected energy includes thermal, kinetic and gravitational changes and is not entirely irreversible heat. The estimated irreversible-heating term spans 0.177–0.229, 0.257–0.283 and 0.120–0.263 of injected energy in the three fully resolved series.

The numerical cocoon/ambient decompositions agree with the independently summed retained energy change to the prescribed tolerance of $10^{-9}E_{\mathrm{inj}}$. Physical closure remains unresolved: the retained whole-domain change exceeds injected energy, particularly in C-LO, where the ratio is approximately 6–24. That case's background-dominated ambient budget cannot be interpreted as jet coupling efficiency. The shock measurements support substantial energy outside the native cocoon, while neither their restricted masks nor the whole-domain ledger establish the fraction of jet power irreversibly coupled to the atmosphere.

In paired 10–12 Myr restarts, the entropy update reduced the energy outside
the injector by 9.21% of labelled input in the high-power group jet and by
4.61% in the high-power cluster jet. These were net changes. The same update
added 21.72% and removed 30.93% in the group, and added 29.98% and removed
34.59% in the cluster. Both switch-on controls reproduced the six production
fluid fields at 11 Myr. The test covers these two atmospheres at high power
over this interval. <!-- claims: BND-14 -->

### How accurately do X-ray observations recover cavity enthalpy?

Of the 57 selected case-age-view combinations, 37 pass the bilateral X-ray topology criterion and 20 remain unresolved. Within the valid surface, pressure recovery is within a factor of two for 36 of 37 views, compared with four for volume and five for enthalpy (Figure [2](#fig-main-2)). Thus the dominant measurement discrepancy lies in the recovered cavity extent and topology, rather than in the inferred ambient pressure. This conclusion is conditional on successful cavity identification; excluded views are not assigned small but finite cavity energies.

Median X-ray/native enthalpy ratios are 0.0222 in C-HI, 0.494 in C-LO, 0.00603 in G-HI and 0.0929 in G-LO. The low-power cluster case is the closest median recovery, and the high-power cases show the largest deficits. These values use the binary cocoon required for the native comparison. Fractional tracer weighting gives a C-LO median ratio of 6.76, so its apparent over-recovery under that alternative convention disappears when the full binary region defines native truth. The observer measurements themselves are unchanged. This sensitivity changes the interpretation of C-LO but preserves the broader evidence for geometry-dependent recovery.

### How do uncertain ages affect inferred jet power?

For the constant labelled bipolar kinetic power, with $E_{\mathrm{inj}}$ in this identity denoting $E_{\mathrm{label}}$, the three contributions to an inferred-power error can be written

$$
\frac{Q_{\mathrm{cav}}}{Q_{\mathrm{true}}}
=\frac{H_{\mathrm{native}}}{E_{\mathrm{inj}}}
\frac{H_X}{H_{\mathrm{native}}}
\frac{t_{\mathrm{true}}}{t_{\mathrm{est}}}.
$$

The identity separates the native enthalpy proxy, observational recovery and age estimate, using the same bipolar region and enthalpy convention throughout. When ages are estimated separately for the two sides, we retain the summed power $\sum_s H_{X,s}/t_s$ and define $t_{\mathrm{est}}=H_X/(\sum_s H_{X,s}/t_s)$ for this identity. This effective age is an enthalpy-weighted harmonic mean, distinct from the arithmetic mean used to summarise the two side ages. It does not assume that the factors are statistically independent. Changing the native mask changes the first two factors reciprocally, leaving their product unchanged for a fixed X-ray measurement.

Using X-ray $2.5pV$ and the true age, median inferred-to-known power ratios are 0.0122, 0.514, 0.00292 and 0.0725 for C-HI, C-LO, G-HI and G-LO, respectively. The high-power deficits are therefore already present before any clock error is introduced. Sound-crossing, buoyant-rise, refill, shock and spectral clocks add method-dependent shifts (Figure [3](#fig-main-3)). Among exact mean-pressure spectral estimates, the corresponding medians are 0.0181 for C-HI and 0.856 for C-LO. However, 20 of 37 mean-pressure spectral rows are censored; both group cases supply only power lower limits for this clock. These limits cannot establish a finite correction to their energy deficit. Emissivity-weighted spectral ages remain a sensitivity comparison.


<div id="figures"></div>

## Discussion

The four simulations separate two limitations of cavity calorimetry. Even an exactly measured native enthalpy is a conditional proxy for jet energy because the pressure integral omits kinetic and gravitational changes and does not isolate energy deposited outside the cocoon. The independent X-ray measurement then introduces a larger deficit in the high-power cases through cavity geometry and topology. An age correction acts on that already biased energy estimate.

The binary native definition is consequential for the low-power cluster case. It converts apparent X-ray over-recovery under fractional tracer weighting into a median underestimate. This illustrates why the definition of native truth must accompany a recovery claim. It does not justify using tracer to repair an observed cavity or applying a single empirical correction across environments and powers.

Shock-mask sensitivity also limits the precision of energy-deposition claims. Halving and doubling the shock-mask thresholds leaves the G-HI shock energy almost unchanged, but produces appreciable variation in G-LO and in C-LO's sole resolved point. Together with the absent boundary flux and cellwise no-jet counterfactual, this warrants interpreting the shock integral as a selected-region diagnostic. The present comparison establishes the structure of the bias within four deterministic cases; a population calibration or causal coupling efficiency requires additional evidence.

## Conclusions

<!-- Summarise only conclusions supported across the accepted comparison surface. -->

## Data availability

<!-- State which compact products, manifests, and source data will be archived or access-controlled. -->

## Code availability

<!-- Identify repository releases, external simulation code, and reproducible build instructions. -->

## Author contributions

<!-- Add a CRediT-style statement after author order and responsibilities are agreed. -->

## Financial support

<!-- Add the applicable funding statement or PASA's no-specific-funding statement. -->

## Conflicts of interest

None.

## Acknowledgements

<!-- Include TPAC/Kunanyi and other facility acknowledgements. -->

## AI-use declaration

<!-- Describe AI-assisted analysis and manuscript drafting in accordance with PASA policy. -->

## References
