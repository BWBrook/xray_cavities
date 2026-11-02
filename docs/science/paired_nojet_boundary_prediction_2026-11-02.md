# Paired boundary controls: prediction recorded before the 50-Myr results

Claude (Opus 5.5, `claude-opus-5-5`) recorded this prediction on 2 November
2026, while PBS `872733`–`872736` were running and before any 50-Myr output
had been read. The experiment, by Codex (GPT-6), is described in
`paired_nojet_boundary_experiment_2026-11-01.md`.

## Hypothesis

Outflow (zero-gradient) boundaries on the hydrostatic stratified atmosphere
drive inflow through every face. That inflow carries enthalpy and potential
energy into the grid, and accounts for the whole-grid energy excess in the
production jet runs. The excess is largest relative to injection in C-LO, at
5–23 E_inj.

## Production reference

The production boundary mass gain does not depend on jet power. Whole-grid
ΔM is taken from the Q-029 native ledgers (`bipolar_total`). The jet mass
loading is removed using the HI−LO difference of about 2.2e41 g per 10 Myr;
the 1e43 erg/s low-power runs carry about 1% of that.

| Atmosphere | ΔM at 50 Myr, LO | ΔM at 50 Myr, HI minus jet mass | ΔM(t)/ΔM(50) at 10/20/30/40 Myr |
| --- | ---: | ---: | --- |
| Cluster | 4.86e43 g | 4.86e43 g | 0.044 / 0.165 / 0.364 / 0.641 |
| Group | 2.38e42 g | about 2.4e42 g (G-HI ends at 40 Myr) | 0.046 / 0.171 / 0.372 / 0.648 |

The growth is close to t², which gives 0.04 / 0.16 / 0.36 / 0.64.

The boundary specific enthalpy is h = 2.5 kT/(μ m_u), with μ = 0.60364, over
the face radii of 200–283 kpc. It is 6.9–7.3e15 erg/g in the cluster and
1.6–1.9e15 erg/g in the group. Including potential, h + φ is about 1.5e16 erg/g
in the cluster and about 5.3e15 erg/g in the group.

## Prediction for the coarse pairs (outflow minus reflective, at 50 Myr)

| Quantity | Cluster | Group |
| --- | ---: | ---: |
| Mass contrast ΔM | ≈ 4.9e43 g | ≈ 2.4e42 g |
| Hydrodynamic-energy contrast ΔH ≈ ΔM·h | ≈ 3.4e59 erg | ≈ 4.2e57 erg |
| Total contrast Δ(H+P) ≈ ΔM·(h+φ) | ≈ 7.2e59 erg | ≈ 1.3e58 erg |
| Time dependence | ≈ t² | ≈ t² |

- The reflective twins should remain quiet, as in the May-8 audit.
- Measured face transport should account for the contrast, as it already
  does in the 0.25-Myr smokes (99.97% and 99.98%).

**Tolerance.** The coarse grid is uniform at 1 kpc. Production's outermost
cells are about 1.7 kpc on the x/y faces and 2.1 kpc on the z faces, estimated
from the geometric stretching in `pluto.ini`. How the inflow scales with face
cell size is not known in advance. Agreement within a factor of about two
therefore supports the hypothesis. Agreement within about 30% would also
indicate that the artefact is insensitive to face resolution.

**Early consistency check.** Scaling the 50-Myr production values by t² down
to 0.25 Myr predicts ΔH contrasts of 8.5e54 erg (cluster) and 1.04e53 erg
(group). The smokes measured 1.14e55 and 1.35e53 erg, about 1.3 times the
prediction in both atmospheres. Production growth also runs slightly above
t² at early times (fit residual 1.09 at 10 Myr). Both deviations point the
same way.

## What would refute it

- A 50-Myr mass contrast below about 1e43 g (cluster) or 5e41 g (group).
- Growth far from t².
- A contrast that measured face transport does not explain.

Any of these means the coarse outflow boundary does not reproduce the
production inflow. The production excess would then need another
explanation, or a production-matched control.
