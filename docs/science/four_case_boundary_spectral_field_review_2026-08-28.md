# Four-case boundary and spectral-field review

## Simulation setup

| Item | Configuration |
| --- | --- |
| Cases | `C-HI`, `C-LO`, `G-HI`, and `G-LO` |
| Environments | Stewart cluster `002003` for `C-*`; Stewart group `002031` for `G-*` |
| Grid/domain | Cartesian `960 x 960 x 1014`; X1/X2 `-200..200 kpc`, X3 `-250..250 kpc`; central `0.05 kpc` cells with stretched outer zones |
| Jet power | One-sided `1e45 erg/s` for `*-HI`, `1e43 erg/s` for `*-LO`; bipolar injected powers are `2e45` and `2e43 erg/s` |
| Jet geometry | Speed `0.1c`; two `15 deg` cones; initial radius `0.1 kpc`; injection height `0.75 kpc`; centred launch |
| Particles | `Nparticles = 32` per injection event; particle cadence approximately `0.01 Myr` |
| Fluid output | Float approximately every `1 Myr`, double approximately every `5 Myr`; exact 50 Myr endpoint retained |
| Radio model | Corrected PRAiSE2, continuous-injection spectral fit, `z=0.05`, `eta=0.03`, five frequencies from `0.15` to `15 GHz` |
| Review surface | Annual boundary diagnostics at `0..50 Myr`; spectral products at `10/20/30/40/50 Myr` and `0/45/90 deg` |

## Decision

Drop the `G-HI` 50 Myr snapshot from all scientific analysis. It has reached
the axial boundary and is not physically meaningful. The files remain only as
archival provenance and boundary-failure evidence.

The selected `G-HI` science surface now ends at 40 Myr. `C-HI`, `C-LO`, and
`G-LO` retain their 50 Myr snapshots.

## Boundary audit

The audit combines three independent diagnostics:

- three-dimensional lobe extents at fractional tracer threshold `1e-3`;
- the furthest detected axial shock relative to the `+/-250 kpc` X3 faces;
- pressure and axial velocity in the first and last cells of each axial
  profile, relative to the corresponding initial atmosphere.

At the final snapshot:

| Case | Minimum tracer X3 margin (kpc) | Axial shock margin (kpc) | Maximum edge `p/p0` | Result |
| --- | ---: | ---: | ---: | --- |
| `C-HI` | `32.56` | `32.56` | `1.106` | retain 50 Myr |
| `C-LO` | `178.48` | `180.32` | `1.106` | retain 50 Myr |
| `G-HI` | `1.052` | `1.052` | `315.31` | exclude 50 Myr |
| `G-LO` | `165.70` | `165.70` | `1.062` | retain 50 Myr |

For `G-HI`, the tracer occupies the outer X3 cell and the pressure ratios at
the negative and positive faces are `315.31` and `186.91`. The annual axial
audit first detects contamination at snapshot 48: the maximum edge pressure
ratio changes from `1.065` at 47 Myr to `139.90`, `166.03`, and `315.31` at
48, 49, and 50 Myr. None of the other three runs shows boundary contact in
the 0--50 Myr interval.

## Magnetic-field treatments

The five-frequency full-loss spectrum determines the continuous-injection
break frequency. The fitted break therefore does not depend on the magnetic
field subsequently used to convert that break into an age.

The global mean-pressure field is calculated from the fractional-tracer lobe
thermal energy and volume, cell-wise accumulated in the accepted fluid
products:

```text
p_mean(t) = (gamma_gas - 1) E_th,lobe(t) / V_lobe(t)

u_B(t) = eta p_mean(t) / [(gamma_gas - 1)(1 + eta)]

B_mean(t) = sqrt[2 mu_0 u_B(t)],
```

where `gamma_gas=5/3` and `eta=0.03`. This is the representative global
cocoon field requested for the primary spectral-age comparison.

The sensitivity treatment uses the existing full-loss 1.4 GHz
emissivity-weighted effective field from each ray-traced view. It preferentially
weights locally bright, high-pressure plasma and is not a volume-mean cocoon
field.

Both fields are converted to age with

```text
t_spec[Myr] = 1590 sqrt(B[uG])
              / (B[uG]^2 + B_CMB[uG]^2)
              / sqrt[(1 + z) nu_b[GHz]],

B_CMB[uG] = 3.25 (1 + z)^2.
```

If the fitted break lies above `15 GHz`, the reported `15 GHz` break gives an
upper limit on age rather than a detection.

## Recalculated results

The 45-degree view gives the following compact comparison at each case's last
retained science snapshot:

| Case | Age (Myr) | Fitted break (GHz) | Break status | `B_mean` (uG) | `t_mean` (Myr) | `B_emiss` (uG) | `t_emiss` (Myr) |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| `C-HI` | `50` | `12.142` | in band | `5.452` | `24.430` | `17.557` | `5.811` |
| `C-LO` | `50` | `8.885` | in band | `5.808` | `26.937` | `6.306` | `24.848` |
| `G-HI` | `40` | `17.775` | above band | `2.839` | `<32.303` | `4.739` | `<24.710` |
| `G-LO` | `50` | `19.600` | above band | `2.057` | `<33.662` | `2.203` | `<33.612` |

The mean-pressure field declines monotonically with source expansion in all
four simulations. The `C-HI` emissivity-weighted field rises again at 50 Myr
even though the boundary audit is clear; that behaviour reflects weighting by
compact bright/high-pressure regions rather than a rise in the global cocoon
pressure.

Changing the field treatment does not remove the dynamical-versus-spectral
age discrepancy. The mean-pressure treatment is more physically
representative for the global cocoon, while the emissivity-weighted treatment
should remain as an observer-like sensitivity. All retained `G-HI` and `G-LO`
breaks are above the observed band, so their quoted ages are censored upper
limits.

## Consequences for Goal 065

- Remove `G-HI/50` from cavity, radio, spectral-age, and inferred-power
  summaries and plots.
- Rebuild Test 2 using the mean-pressure field as the primary cocoon field and
  the emissivity-weighted field as a sensitivity.
- Recalculate any case medians in Tests 2 and 3 that previously included
  `G-HI/50`.
- Keep the existing Goal 065 Test 1 shock gate; it already excluded the
  boundary-contaminated endpoint, but regenerate joined row counts and labels.
- Do not rerun PLUTO, X-ray synthesis, or PRAiSE for this correction. The
  accepted compact products contain the required information.

## Evidence and reproduction

Machine-readable products and figures are in
`docs/science/assets/four_case_boundary_spectral_field_review_2026-08-28/`.
The main tables are `annual_axial_boundary_audit.csv`, `boundary_audit.csv`,
`spectral_break_frequencies.csv`, and
`spectral_age_field_comparison.csv`.

Rebuild with:

```bash
python scripts/science/build_four_case_boundary_spectral_field_review.py
```
