# Production energy excess after the boundary term

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
