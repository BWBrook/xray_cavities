# Interior-residual and bow-shock criteria, fixed before results

Claude (Opus 5.5, `claude-opus-5-5`) recorded these criteria on 4 November
2026 at Codex's request. No interior-cut, spherical-budget or 20-Myr
shock/emission result had been read; the four coarse 50-Myr controls
(`872733`–`872736`) had completed but were not yet analysed. They apply to
Stas's requests of 3 November:

- `paired_boundary_interior_check_2026-11-03.md`;
- `xray_cavity_path_length_and_bow_shock_check_2026-11-03.md`.

## 1. When an interior residual is negligible

**Scale.** S(t) = 2e43 erg/s × t, the bipolar injected energy of the
low-power runs. It is the smallest energy that any production budget must
resolve, and the controls inject nothing. The scale is the same for both
atmospheres. S(50 Myr) = 3.16e58 erg; S(0.25 Myr) = 1.58e54 erg.

**Tolerance: 1% of S(t).** Reported budget ratios are quoted to two or three
significant figures, and the smallest reported low-power regional value is
0.013 E_inj (G-LO). A contamination below 0.01 S therefore cannot change any
reported ratio by more than about one unit in its second significant figure.
A tighter bar is not meaningful: the reflective cluster twin already
redistributes about 0.54% of S(50 Myr) between the inner and outer 100 kpc
(BND-03).

Two tests are applied at each exclusion width w, to thermal, kinetic,
gravitational and total energy separately, because the budgets report
components.

| Test | Quantity | Negligible for every sub-aperture | Negligible only for the whole retained region |
| --- | --- | --- | --- |
| Boundary sensitivity | Paired same-cell contrast D_i (outflow minus reflective) | Σ\|D_i\| ≤ 0.01 S | \|Σ D_i\| ≤ 0.01 S, but Σ\|D_i\| > 0.01 S |
| Background drift | Each twin's own change from its initial state | Σ\|ΔE_i\| ≤ 0.01 S | \|Σ ΔE_i\| ≤ 0.01 S |

**Why the absolute (L1) form decides.** Spherical and cocoon apertures sum
subsets of the retained cells. For any subset A, \|Σ_A D_i\| ≤ Σ\|D_i\|.
Only the L1 bound therefore guarantees that *every* aperture inside the
retained region is clean; a small signed sum can hide cancelling errors.

**Background drift is a separate result.** It is not boundary contamination:
it is the no-jet counterfactual floor that the jet runs share. Report it even
when the boundary test passes. Do not subtract it from production budgets
without a production-grid estimate, because the coarse twins have a
different grid.

**Mass.** Report the retained ΔM contrast and drift, and convert them to an
energy equivalent with the local h + φ for context. No separate threshold.

**No tuning.** The adopted width for each atmosphere is the smallest tested
width that passes the L1 boundary test at 50 Myr. If none of 0, 20, 30, 40
or 50 kpc passes, report that rather than widening the cut silently.

## 2. Expected outcome

The acoustic depth is integrated perpendicular to each face, ∫ c_s dt,
through the tabulated initial atmospheres. Sound speed rises slightly inward.

| Atmosphere | Depth at 0.25 Myr | Depth at 50 Myr | Margin inside a 40 kpc cut |
| --- | ---: | ---: | ---: |
| Cluster (`002003`) | 0.17–0.18 kpc | 34.4–35.9 kpc | about 4 kpc |
| Group (`002031`) | 0.08–0.09 kpc | 16.5–18.3 kpc | about 22 kpc |

- **At 0.25 Myr** the physical horizon is under one cell. Any residual beyond
  1 kpc is numerical precursor from the stencil over 14 updates. It should
  fall steeply from 1 to 2 to 4 kpc.
- **At 50 Myr** the cluster contrast should collapse between 30 and 40 kpc,
  and the group contrast by 20 kpc.
- **Refutation.** A cluster L1 contrast above 0.01 S at 40 kpc, or a group
  contrast above it at 30 kpc, means either the influence is not acoustic or
  the numerical precursor is wide. In both cases the cut cannot be justified
  from c_s t.

**Transfer to production.** Numerical precursors scale with cell count, not
distance. Production's outer cells are 1.7–2.1 kpc, against 1 kpc here, so a
4 kpc margin is only about two production cells. The coarse test should
report the precursor width in cells beyond the acoustic depth. The
production cut must cover the acoustic depth plus that many production
cells. If that exceeds 40 kpc in the cluster, the 40 kpc choice fails on
grounds fixed here, not after the fact.

## 3. Independent bow-shock definition (G-HI 20 Myr)

The definition must not use the orange 5% mask, the tracer boundary, entropy
excess, the axial seed or speed alone. It follows the established
jump-condition shock finders (Ryu et al. 2003; Schaal & Springel 2015) on the
native grid:

1. **Candidates.** Cells with ∇·v < 0, compressive along the local
   pressure-gradient direction n = ∇p/|∇p|.
2. **Jump across the stencil.** Take p, ρ and T at ±2 cells along n.
   - Upstream is the lower-pressure side.
   - Mach from the pressure ratio: M_p from p₂/p₁ = (2γM² − (γ−1))/(γ+1).
   - Mach from the density ratio: M_ρ from ρ₂/ρ₁ = (γ+1)M²/((γ−1)M² + 2), with γ = 5/3.
3. **Accept a cell** when all three hold:
   - M_p ≥ 1.1 (p₂/p₁ ≥ 1.26);
   - T rises downstream;
   - \|M_p − M_ρ\| ≤ 0.2 M_p.

   This rejects contact discontinuities, which have no pressure jump, including
   the cocoon edge; it also rejects rarefactions and sound waves below
   M = 1.1. Keep one flagged cell per stencil, at the maximum of
   \|∇·v\|.
4. **Front and shell.**
   - The front is the outermost accepted cell along each ray from the
     nucleus.
   - The shocked shell is ambient gas (tr1 ≤ 1e-3) lying between the tracer
     edge and the front along the same ray. Tracer only labels which side is
     cocoon; it never places the front.
5. **Sensitivity.** Repeat with M_min = 1.05 and 1.2, and report M along the
   front as a function of polar angle. The lateral front weakens towards the
   equator, so arcs there may sit where M approaches 1.
6. **Validation before use.** Insert an exact Rankine–Hugoniot shock at
   M = 1.1, 1.5 and 3 into the tabulated G-HI atmosphere on the production
   stretched axis. The finder must place the front within two cells and
   recover M within 10%.
7. **Comparison with the arcs.**
   - Project the front and the shell into the retained 1-keV pixel grid for
     the 0°, 45° and 90° views.
   - Per azimuth, measure the signed distance from the projected front to the
     orange boundary.
   - Classify each arc as coincident (within two pixels), on the inner edge,
     on the outer edge, or unrelated.
   - Coincidence alone does not establish cause. The same-cell
     initial-emissivity replacement test and the background refit decide
     cause.

This shock surface is a diagnostic for the observer question only. It does
not replace the Q-029 shock-region selection used in the energy budgets, and
it does not enter the whole-grid or spherical budgets.
