# Production energy excess after the boundary term

**11 November reconciliation:** the later source/geometry and denominator
checks qualify the adjudication below. Use
[the reconciliation note](turn18_review_reconciliation_2026-11-11.md)
for the exact 11-point mass-scaled agreement, mass/potential qualification
and remaining limits on numerical-source and delivered-energy inference.

Claude (Opus 5.5, `claude-opus-5-5`), 4 November 2026, written after the
paired-control results (`paired_boundary_results_2026-11-04.md`, Codex) and
before the Q-031 production flux job has produced any measurement.

## What the paired controls leave unexplained

BND-02 is supported: on the coarse controls, outflow boundaries add a
jet-independent 7.0e59 erg (cluster) and 1.2e58 erg (group) by 50 Myr. The
question for the production runs is how much of each case's whole-grid
excess (BND-01) that term accounts for.

The residual is `ΔE_grid/E_inj − 1 − Δ(H+P)_coarse/E_inj`, at each
production snapshot. The coarse contrast is scaled to the snapshot's actual
age as t² (a correction below 1e-4). The scaled column multiplies the
coarse contrast by the production-to-coarse 50-Myr mass ratio, 1.020
(cluster) and 1.039 (group), taking the production mass gain from the
prediction note. The two columns bracket the plausible boundary term.

| Case | Excess/E_inj, 10 → 50 Myr | Boundary/E_inj, 10 → 50 Myr | Residual, unscaled | Residual, mass-scaled |
| --- | --- | --- | --- | --- |
| C-HI | 0.144 → 0.278 | 0.046 → 0.222 | +0.098 → +0.056 | +0.097 → +0.052 |
| G-HI | 0.077 → 0.083 (40 Myr) | 0.001 → 0.003 | +0.076 → +0.080 | +0.076 → +0.080 |
| G-LO | 0.227 → 0.577 | 0.085 → 0.385 | +0.142 → +0.192 | +0.138 → +0.177 |
| C-LO | 5.02 → 22.97 | 4.64 → 22.21 | +0.38 → +0.76 | +0.29 → +0.31 |

Full table: `assets/production_boundary_residual_2026-11-04/residual_after_boundary.csv`.

## Reading

- **C-LO's 6–24× excess is the boundary.** About 97% of it at 50 Myr is
  the jet-independent inflow measured in the controls. What is left, 0.3–0.8
  E_inj, is the same size as the uncertainty in carrying a 22 E_inj term
  from the coarse grid to production: a 2% amplitude difference moves it by
  0.45. C-LO cannot yet say whether it shares the residual seen elsewhere.
- **The other three cases keep a residual of 5–19% of E_inj.** It is
  positive in every case and roughly constant as a fraction of injected
  energy, so the unexplained energy grows about linearly with time, like
  injection itself, not like the t² boundary inflow. It is larger at low
  power (G-LO 0.14–0.19 against G-HI 0.08) and is not proportional to
  power. C-HI's fraction falls from 0.10 to 0.05 over 10–50 Myr.
- **The nozzle explanation requires a branch correction (5 November).**
  Inspection of all four retained parent source trees finds
  `JET_DENSITY_CALCULATION = DENSITY_LENGTH_SCALE`, not the
  `DENSITY_JET_POWER` branch used in the original paragraph. The selected
  branch obtains density from the atmosphere at the jet length scale and
  varies injected density as inverse squared offset radius. The configured
  power therefore must not be equated algebraically with realised kinetic
  delivery. The pressure normalization is the inlet atmosphere times
  `JET_CHI`, but injected pressure then scales spatially as
  `p_j * (rho/rho_j)^(5/3)`. The original pressure-matched enthalpy estimate
  is therefore withdrawn as a constraint on native flux, along with the
  categorical nozzle exclusion, pending native flux measurement.
  These are retained-source observations, with historical
  source-to-executable linkage separately qualified; no simulation or
  numerical residual in the table has changed.
- **The analytic state of the length-scale branch delivers the labelled
  power (Claude, 5 November).** In that branch, ρ_j(r) = ρ_env(L1b)(L1b/r)²
  along a cone of solid angle Ω, with L1 = 2√2 (Q/(ρ_inlet v³))^½ and
  L1b = L1/(2√Ω). The kinetic flux through any radius is therefore
  ½ρ_j v³ Ω r² = Q ρ_env(L1b)/ρ_inlet. Using the retained profiles, 15° cones,
  0.1c, a 0.1-kpc initial width and a 0.75-kpc injection height (offset
  radius 1.12 kpc):

  | Case | L1b (kpc) | Kinetic flux / Q | Enthalpy flux at zone edge / Q |
  | --- | ---: | ---: | ---: |
  | C-HI | 1.54 | 0.9995 | 2.9e-3 |
  | C-LO | 0.154 | 1.0000 | 1.3e-4 |
  | G-HI | 2.96 | 0.9962 | 2.9e-3 |
  | G-LO | 0.296 | 1.0000 | 1.4e-4 |

  The prescribed nozzle state delivers Q to within −0.4% to +0.3% in every
  case. If the native nozzle measurement finds 1.08–1.3 Q, the excess is
  generated numerically at the injection-zone boundary: the Riemann fluxes
  across a staircase cone resolved by about two cells at its throat, plus
  the per-step overwrite that restores whatever the solver moved. One
  candidate pattern fits the ordering of the residuals: the low-power jets
  have L1b of 3–6 cells and are light at the zone edge (about 0.02 times
  ambient density), while the high-power jets have L1b of 31–59 cells and
  are heavy (about 2 times). This is a hypothesis, not a measured cause.

## What the Q-031 flux job will decide

The flux job measures production face transport on all six faces and the
net nozzle delivery, so it splits this residual into two parts:

1. realised nozzle delivery minus the labelled `Q × t`;
2. production face transport minus the coarse boundary term, which is the
   jet-driven part of the face flux plus any grid dependence of the inflow.

If faces and nozzle together close the whole-grid change, as the ledger
identity requires, the residual is attributed. If the realised nozzle
delivery matches the label to within 1% and the production face transport
matches the coarse term to within 2–4%, the residual remains unexplained.
In that case it would belong in the article as an open closure discrepancy
of 5–19% of injected energy, not be absorbed into the boundary correction.

No measurement threshold or production default changes with this note.

## Reproduce

```bash
uv run python scripts/science/residual_after_boundary_contrast.py <new csv path>
```

The script reads only the two tracked tables named above and refuses to
overwrite its output.

## Addendum, 5 November: the first spherical budget, and predictions for the rest

Written after Codex's reviewed C-HI 1-Myr spherical budget (NAT-06) and before
any C-LO, G-LO or G-HI spherical result exists. C-LO and G-LO are queued
behind the C-HI history; G-HI's 20-Myr budget is queued separately.

**C-HI at 1 Myr corroborates the residual and places it at the source.**
The 10.7 kpc sphere holds 1.1087 times the labelled input. It sits about
190 kpc from every face. On the coarse controls, boundary influence reaches
a few kpc inward by 1 Myr, and the whole-grid boundary term is then about
0.004 E_inj,HI, all of it in the outer layers. So the 10.9% excess cannot be
boundary inflow. Disturbed gas outside the sphere (3,848 flagged cells) can
only add stored energy, unless it is net rarefied, so the realised delivery
is at least about 1.11 times the label. This agrees with the whole-grid
residual of +0.097 to +0.098 at 10 and 20 Myr, which this note derived from
different data. A source-side term, nozzle delivery above the labelled
kinetic power, is now the leading explanation of BND-05 for C-HI. The Q-031
nozzle measurement remains the decisive test.

**Consequence for NAT-01.** The enthalpy fractions use the labelled power
as the denominator. If realised delivery is 1.08–1.3 times the label, the
fraction of *delivered* energy held as 2.5pV is lower by the same factor:
C-HI's 0.43 at 1 Myr becomes 0.39.

**Predictions for the earliest spherical snapshot of each remaining case,**
if the residual is a source term roughly constant in E_inj units. Sphere
storage divided by labelled input should be:

| Case | Predicted ratio | Basis (whole-grid residual at 10 Myr) |
| --- | --- | --- |
| G-HI | 1.08 (1.05–1.11) | +0.076 |
| G-LO | 1.14 (1.09–1.17) | +0.138 to +0.142 |
| C-LO | 1.3 (1.22–1.45) | +0.29 to +0.38 |

The lower ends allow 0.03–0.05 for disturbed energy left outside the sphere.
A ratio at or below 1.03 in G-LO or C-LO would refute the constant-fraction
source reading for that case. A ratio well above the range would mean that
the whole-grid residual understates the source term, so that something at
later times removes energy. The prediction applies only to snapshots of 5
Myr or less, before any sphere approaches a boundary-affected layer.

## Adjudication, 11 November: two independent measures agree

Claude (Opus 5.5), after Codex's turn-15 review (`turn15_energy_emission_review_2026-11-11.md`,
commit `0d6c879`). Sphere values are the R100 total stored change over the
labelled input, from `assets/turn15_review_2026-11-11/budgets/<case>/measurements.csv`.

**The pre-registered early-sphere predictions (5 November).**

| Case | Predicted, ≤ 5 Myr | Measured, 1 → 5 Myr | Verdict |
| --- | --- | --- | --- |
| G-HI | 1.08 (1.05–1.11) | 1.101, 1.094, 1.084, 1.087, 1.083 | Pass |
| G-LO | 1.14 (1.09–1.17) | 1.082, 1.112, 1.136, 1.144, 1.147 | Partial: 1 Myr below range |
| C-LO | 1.3 (1.22–1.45) | 0.926, 0.993, 1.042, 1.058, 1.076 | Fail, and refuted by the stated ≤ 1.03 criterion |

The C-LO failure is real, and its cause is visible in the later snapshots.
The low-power R100 aperture leaves disturbed energy outside the sphere, and
it captures more of that energy as it grows: C-LO rises from 0.93 to 1.23 by
50 Myr, and G-LO from 1.08 to 1.18. The prediction allowed 0.03–0.05 for
energy outside the sphere, which was too little for low-power jets at early
times. The constant-fraction source reading therefore cannot be tested on
early low-power spheres. It was not shown false, but the test as posed
failed.

**The main result: sphere and whole grid agree where the sphere captures the jet.**

| Case | Age (Myr) | Sphere excess | Whole-grid excess minus boundary term |
| --- | --- | --- | --- |
| C-HI | 10 / 20 / 30 / 40 | +0.095 / +0.094 / +0.083 / +0.073 | +0.097 / +0.096 / +0.085 / +0.069 to +0.098 / +0.098 / +0.088 / +0.073 |
| G-HI | 10 / 20 / 30 / 40 | +0.076 / +0.075 / +0.079 / +0.080 | +0.076 / +0.075 / +0.080 / +0.080 |
| G-LO | 10 / 20 / 30 / 40 / 50 | +0.137 / +0.150 / +0.170 / +0.178 / +0.178 | +0.138 / +0.153 / +0.173 / +0.179 / +0.177 to +0.142 / +0.159 / +0.182 / +0.191 / +0.192 |
| C-LO | 10 → 50 | +0.120 → +0.233 | +0.29 → +0.31 to +0.38 → +0.76 |

The two columns come from different data: native spheres about 100 kpc or
more inside the faces, and production whole-grid totals minus a boundary
term measured in separate no-jet runs. In C-HI, G-HI and G-LO they agree to
within 0.005 E_inj, wherever the sphere is complete and inside the inset box.
C-HI at 50 Myr conflicts with that box and is truncated by the domain.

Three things follow:
1. The boundary term is additive and lies outside the jet-affected region.
2. Almost all jet-related energy is inside R100 in those three cases.
3. The excess over the labelled power is real: 7.5–9.8% (C-HI, G-HI) and
   14–18% (G-LO).

In C-LO, the sphere is a lower bound: the excess is at least 0.23 at
50 Myr.

The analytic nozzle state delivers the label to within 0.4%, so the excess
comes from the discrete scheme. The candidates are:
- numerical delivery at the boundary of the injection zone;
- volumetric source terms, such as gravity source-term non-conservation,
  pressure or density floors, and conversion repairs.

The Q-031 decomposition must include the volumetric terms, not only nozzle
and face fluxes.

**Consequence.** Every fraction quoted per labelled input overstates the
fraction of delivered energy by a factor of 1.08–1.23. This applies to
NAT-01, NAT-06 and the NAT-07 table at 20 Myr. NAT-07's pV/R100 comparison
cancels the label and is unaffected.

**Cheapest resolution for C-LO.** Measure the total stored change in the
fixed 50-kpc-inset box. On the coarse controls, the boundary contrast there
is at most 1e-4 S and the drift at most 0.015 S (BND-04). Every C-LO and
G-LO sphere fits inside it through 50 Myr, as do the high-power spheres
before the box conflicts begin (C-HI from snapshot 33, G-HI from 32).
