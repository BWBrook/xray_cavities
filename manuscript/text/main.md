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

### Synthetic X-ray products

We use the existing corrected, noiseless 1-keV X-ray images at the three
side-on azimuths. Radio spectral-age inference is outside the scope of the
present cavity-energetics comparison.

### Cavity geometry, age, and energetics

The primary native cocoon comprises cells with tracer $\mathrm{tr1}>10^{-3}$, evaluated after promotion of the stored tracer to double precision. Each selected cell contributes its full volume, mass and energy. Ambient cells satisfy the exact complement, $\mathrm{tr1}\leq10^{-3}$. Fractional tracer weighting and binary thresholds of $5\times10^{-3}$ and $10^{-2}$ provide sensitivity comparisons. The stored single-precision tracer can differ slightly from the nominal threshold; the largest contribution of cells at its stored representation is less than $2.6\times10^{-7}$ of native enthalpy on the selected surface.

Native enthalpy is $H_{\mathrm{native}}=\alpha\int_{\mathrm{cocoon}}p\,dV$, with $\alpha=2.5$ for the primary non-relativistic convention and $\alpha=4$ as a literature comparator. Thermal, kinetic and gravitational energies form a separate additive ledger. For each component we subtract the initial field in the same cells selected by the current cocoon mask, and do likewise for its ambient complement. These regional differences sum to the retained whole-domain energy change. They describe changes relative to the initial conditions in a current spatial region; they do not follow a material parcel or the evolving cocoon boundary. The initial snapshots already contain a nozzle region. Absolute current lobe energy therefore differs from the regional change, and subtracting the entire initial domain energy from the ambient allocation is not equivalent to subtracting only the initial ambient-region energy.

We normalize the primary native pressure estimate to the cumulative net gas energy transferred from the maintained injector to freely evolved cells at the identical case and actual output age. The signed cone and stationary-region fluxes are added before integrating the saved-state rates from the already initialized $t=0$ output. Gas-energy flux includes internal and kinetic energy and pressure work; it excludes gravitational-potential transport. The primary interface reconstruction is linear with the saved shock-flag fallback, and the primary time integral is trapezoidal. Left/right rectangles, first-order states and forced HLL/HLLC solvers provide sensitivity comparisons. These reconstructions omit intermediate Runge–Kutta states and the unsaved terminal velocity dip, so they are estimates of cumulative delivery rather than exact injection counters. Labelled bipolar kinetic power times actual active age, $E_{\mathrm{label}}$, remains a separate comparator. <!-- claims: NAT-01 -->

We identify shock-processed ambient gas using entropy excess connected to a compressed axial-front seed, with environment-matched no-jet noise calibration. The calculation retains the accepted supersonic-front, seed, extent, boundary, minimum-cell and bilateral validity gates. Selected cells contribute their full current-minus-initial energy, and are a subset of the ambient region. Adding the shock energy to the full ambient change would count these cells twice. The calibration uses the available coarser no-jet runs. Transport across the moving shock and spherical apertures remains unmeasured. <!-- claims: NAT-03 NAT-04 -->

We tested X-ray cavity outlines on corrected 1-keV images of the 19 case–age combinations at three side-on azimuths ($0^\circ$, $45^\circ$ and $90^\circ$). The methods use X-ray brightness to select pixels. We reserved the projected jet tracer and the native three-dimensional lobe volumes for evaluating the outlines. We tested a fixed-area selector, an algorithm that grows regions from seed pixels, and cuts at 5%, 10% and 20% below the radial median brightness. <!-- claims: DET-01 DET-04 -->

### Statistical comparisons

We report within-case ranges and medians across ages and views of the same simulation. For the detector tests each side contributes its reconstructed volume, with zero assigned to an undetected side. We also measure the fraction of projected tracer area inside the outline (completeness) and the fraction of the selected area that overlaps the tracer (purity). <!-- claims: DET-01 DET-02 -->

For a cavity with a validated outline, the X-ray enthalpy estimator uses geometric depth, ambient pressure averaged over the inferred ellipsoid, and the same enthalpy convention as the native estimate. We retain all three adopted cavity clocks separately: sound-crossing, buoyant-rise and refill ages. They use the observed geometry with the initial atmosphere's sound speed or gravity. Each prescription gives its own enthalpy-to-power estimate, rather than being averaged into a single age. The true simulation age supplies a control for separating enthalpy and volume errors from the assumed clock. No spectral age is inferred from the radio emission.

For a constant labelled bipolar kinetic power, the cavity-power estimate can be factorised as

$$
\frac{Q_{\mathrm{cav}}}{Q_{\mathrm{label}}}
=\frac{H_{\mathrm{native}}}{E_{\mathrm{label}}}
\frac{H_X}{H_{\mathrm{native}}}
\frac{t_{\mathrm{true}}}{t_{\mathrm{est}}}.
$$

Here $E_{\mathrm{label}}=Q_{\mathrm{label}}t_{\mathrm{true}}$, and $H_X$ and $H_{\mathrm{native}}$ use the same bipolar enthalpy convention. If the two sides have separate age estimates $t_s$, the effective age is $t_{\mathrm{est}}=H_X/(\sum_s H_{X,s}/t_s)$ so that the power is the sum of the two side powers. Knowing the true age fixes the last factor. The primary actual-input comparison replaces $Q_{\mathrm{label}}$ by cumulative net injector gas delivery divided by $t_{\mathrm{true}}$, and $E_{\mathrm{label}}$ by that same cumulative delivery. Estimating $H_X$ still requires a validated cavity outline.

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

The actual energy change in the current cocoon region spans 0.132–0.426 of labelled input in C-HI, 0.425–0.571 in G-HI and 0.013–0.298 in G-LO. In C-LO it ranges from −0.160 to 0.137. The gravitational term can decrease relative to the initial fields in the same cells. A negative total therefore describes a regional change under the chosen gravitational reference. <!-- claims: NAT-02 -->

The selected shock-processed ambient region gains 0.666–0.765, 0.505–0.655 and 0.580–0.854 times the labelled input in C-HI, G-HI and G-LO, respectively. C-LO supplies one accepted estimate, 0.223 at 10 Myr. Its four later ages fail the bilateral shock criterion. This energy includes thermal, kinetic and gravitational changes. The estimated irreversible-heating term spans 0.177–0.229, 0.257–0.283 and 0.120–0.263 of labelled input in the three fully resolved series. <!-- claims: NAT-03 -->

The cocoon and ambient contributions sum to the independently measured whole-domain energy change within $10^{-9}E_{\mathrm{label}}$. C-LO gains about 6–24 times the labelled jet input across the domain, which includes a large energy inflow through its outer boundary. This inflow must be accounted for before interpreting the domain's energy gain as a response to the jet. <!-- claims: NAT-04 BND-01 BND-02 -->

During the 10–12 Myr restarts, the high-power group lobe gained enthalpy
equal to 41.7% of the net gas energy delivered over those two Myr with the
entropy update on and 51.1% with it off. In the cluster the corresponding
gains were 50.8% and 63.4%. These ratios measure the growth of the lobe's
pressure-volume proxy. They cannot establish how much energy heated the
atmosphere. At 12 Myr, switching off the update increased lobe enthalpy by
3.56% in the group and 4.25% in the cluster. Lobe volumes changed by
+0.015% and −0.155%, respectively, so higher mean pressure accounts for
most of the increase. About five-sixths of the cumulative net gas supply
predates the restart. With that common history included, lobe enthalpy as a
fraction of supply rose from 42.83% to 44.40% in the group and from 48.17%
to 50.27% in the cluster. Each case has one pair, and the enthalpy gap grew
more in the second Myr than in the first. Its size at 30–50 Myr remains
unmeasured. <!-- claims: NAT-12 -->

In the low-power pairs, the same entropy update added 3.88% of labelled
input to gas outside the injector in the cluster and removed 1.96% in the
group over 10–12 Myr. The signed solver counter met all four prospective
1-Myr predictions. With the switch off, all 38 post-startup exterior
residuals met the registered ±0.2% bound. Over the two Myr, lobe enthalpy
gain per unit of net gas delivered changed from 67.6% to 72.6% in the group
and from 89.4% to 88.8% in the cluster. In the low-power cluster, requiring
0.5% or 1% jet material reversed the sign of this small enthalpy contrast.
At the primary lobe edge, switching the update off narrowed the low-power
advantage from 39 to 25 percentage points in the cluster and from 26 to 21
points in the group. Low power retained the higher fraction at all three
tracer cuts in both atmospheres. <!-- claims: BND-15 NAT-12 NAT-13 -->

In the same pairs, the entropy update reduced the energy outside
the injector by 9.21% of labelled input in the high-power group jet and by
4.61% in the high-power cluster jet. These were net changes. The same update
added 21.72% and removed 30.93% in the group, and added 29.98% and removed
34.59% in the cluster. Both switch-on controls reproduced the six production
fluid fields at 11 Myr. <!-- claims: BND-14 -->

At 30 Myr the reconstructed cumulative energy balance outside the injector
was −6.73% and −6.78% of delivered gas energy in the high-power cluster and
group. The corresponding low-power balances were +8.74% and +1.97%. G-LO’s
annual balance changed from negative to positive over 14–15 Myr, and its
cumulative balance returned above zero at 17 Myr. The direct measurements
of the entropy update cover 10–12 Myr. At the later ages we can reconstruct
the balance from storage and transport, while its partition among solver
operations and its effect on lobe enthalpy remain uncertain. <!-- claims: BND-14 BND-15 BND-16 -->

The cluster restarts sampled a relatively weak phase of that residual.
In C-HI it was about −4.6% of labelled energy over 10–12 Myr and −12.1%
in the interval ending at 30 Myr. C-LO went from +3.0% and +4.7% in the
two restart intervals to +15.4% in the interval ending at 30 Myr.
Both high-power lobes gained more enthalpy with the update off, and their
annual exterior residuals stayed negative after 12 Myr. We therefore expect
the production high-power fractions to be biased low if the later energy
loss continues to draw on the lobe. Redistribution between the lobe,
its surroundings and bulk motion leaves the size of such a bias open.
<!-- claims: NAT-12 NAT-13 BND-16 -->

### Can a brightness deficit identify the lobe?

Across the 57 views, some algorithms missed the low-contrast lobes and others selected unrelated deficits or merged the lobe with the background. In C-HI, the 5% brightness-deficit threshold gave a median recovered volume of 1.08 times the native lobe volume. Yet its outlines covered only 36% of the projected tracer area, and only 70–77% of the selected area overlapped the tracer. Agreement in volume can therefore arise from errors on opposite sides of the outline. These tests leave the four-case X-ray enthalpy and power recovery unresolved. <!-- claims: DET-01 DET-02 -->

We then froze two background-refitted rules and tested them on 54 held-out,
noiseless 1-keV views, excluding the G-HI/20 development case. The 18
case-ages each supplied three azimuths and two hemispheres. A passing
outline had to cover at least 75% of the projected lobe, place at least
95% of its selected area on the lobe and avoid the aperture boundary.
On images alone, seed/grow recovered a median 22.8% of the lobe area and
the radial 5% rule recovered 41.6%. Neither passed on any of the 108
science sides. Both returned empty masks on all 24 initial control sides.
Replacing the emissivity of moving ambient gas using native simulation
fields brought the pass counts to 6 and 13, respectively. <!-- claims: DET-05 -->

<div id="figures"></div>

## Discussion

Even when the native pressure and volume are known, their product omits the kinetic and gravitational energy changes and energy stored outside the lobe. The observational comparison poses a separate problem. The C-HI outlines that reproduced the lobe volume missed most of its projected area. The held-out test confirms that these two image-only rules systematically omit lobe area. Their inferred volumes therefore provide an uncertain basis for comparing X-ray enthalpies or clocks across atmospheres. <!-- claims: NAT-02 NAT-07 DET-01 DET-02 DET-05 -->

Halving or doubling the shock-mask thresholds changes G-HI's estimated shock energy little, while G-LO's estimates and the sole accepted C-LO point depend on that choice. The integral measures energy change in the selected cells. Inferring irreversible atmospheric heating also requires their thermodynamic histories and energy transport. <!-- claims: NAT-03 -->

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

OpenAI Codex (GPT-6) ran the paired tests, reconstructed the energy
budgets, tested the radio emissivity weighting, sealed and scored the X-ray outlines, and drafted the analysis.
Anthropic Claude (Fable 5.2) registered the low-power energy forecasts,
independently checked the four restart budgets and lobe contrasts, refitted
the public radio spectra, and replayed the held-out X-ray masks and overlap
measurements. Google
DeepMind Gemini (4 Carbon) independently checked the low-power lobe
arithmetic, compared the production histories and proposed the radio test.

## References
