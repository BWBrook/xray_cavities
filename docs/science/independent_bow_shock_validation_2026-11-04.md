# Independent bow-shock finder: synthetic validation

Date: 2026-11-04
Status: **FAIL — no promotion to native G-HI extraction**

## Decision

The implemented detector recovers all expected exact Rankine–Hugoniot shocks
and rejects the prescribed contacts, rarefaction and 10% sound wave at the
primary threshold, `M_min = 1.1`. It does not satisfy the complete validation
contract across the required sensitivity arms: the compressive isentropic
sound wave is flagged in all six placement/orientation cases at
`M_min = 1.05`.

This is a structural counterexample, not a numerical accident. The wave's
endpoint pressure ratio is `1.1 / 0.9 = 1.2222` and its isentropic density ratio
is `1.2222^(1/gamma) = 1.12795`. Substitution into the two shock inversions
gives `M_p = 1.08525` and `M_rho = 1.08545`; temperature rises and the imposed
wave is compressive. It therefore satisfies every proposed cell-level test at
`M_min = 1.05` despite having no entropy production.

Do not run this finder on the native 20-Myr snapshot or use it to interpret the
orange arcs until the criterion is amended and revalidated.

## Scientific target and scope

The target is a local, tracer-independent diagnostic of cells on a bow-shock
surface. The local estimands are shock-normal direction and upstream/downstream
Rankine–Hugoniot Mach numbers inferred separately from pressure and density.
The later prediction target would be the outermost accepted front along each
ray in G-HI at 20 Myr. This tranche validates only the local cell classifier;
it does not estimate a native front, shell, projection, arc alignment or causal
emission effect.

The finder does not read the orange mask, tracer, entropy excess, axial seed or
speed alone. No PLUTO simulation, remote job or native science extraction was
run.

## Implemented detector

`scripts/science/independent_bow_shock.py` implements the fixed candidate:

1. Physical-coordinate derivatives on the non-uniform Cartesian axes give
   `div(v)` and `n = grad(p) / |grad(p)|`.
2. A cell must be compressive. Along the dominant component of `n`, local
   maximum-compression selection keeps the upstream member of an exactly tied
   plateau, preventing the common two-cell central-difference duplicate.
3. The local effective cell length is
   `h_n = 1 / sqrt(sum(n_i^2 / dx_i^2))`. Pressure and density are sampled by
   trilinear interpolation at the physical positions `x +/- 2 h_n n`.
4. The lower-pressure sample is upstream. The code inverts the pressure and
   density Rankine–Hugoniot ratios for `gamma = 5/3`, then requires
   `M_p >= M_min`, downstream temperature rise, and
   `|M_p - M_rho| <= 0.2 M_p`.
5. The production-facing iterator reads haloed 3-D tiles from NumPy, memory-map
   or HDF5-like datasets. Its default core is `16 x 128 x 128` cells with a
   four-cell halo. It yields batches so a later ray reducer need not retain a
   billion-cell mask or even all candidates simultaneously.

The implementation is an adaptation, not a reproduction, of the published
shock-finder lineage. Ryu et al. introduced a grid shock finder based on
compression and thermodynamic jumps; Schaal and Springel emphasised shock-zone
filtering, maximum compression, contact rejection and sensitivity to
implementation details. Their AREPO method uses a temperature-gradient shock
direction and a variable-width shock zone, whereas the fixed criterion tested
here uses a pressure-gradient direction and a fixed `+/-2`-cell stencil.
[Ryu et al. 2003](https://arxiv.org/abs/astro-ph/0305164);
[Schaal & Springel 2015](https://arxiv.org/abs/1407.4117).

## Synthetic data-generating process

The harness parses the retained production `grid.out`, shape
`(z, y, x) = (1014, 960, 960)`, and allocates only 27-cell local patches. It
uses the actual cell centres and edges at:

- a central, uniform-grid placement;
- an outer, stretched-grid placement near `(45, -25, 70) kpc`.

Each placement is crossed with axis-aligned, diagonal and fully oblique planar
fronts. The local background is interpolated from the retained Stewart group
`002031` atmosphere.

For the exact Riemann tests, each normal column uses the tabulated atmosphere
at its projection onto the shock plane. This retains real tangential
stratification but removes the smooth background gradient normal to the plane,
which is necessary for the inserted pressure and density discontinuity itself
to be an exact Rankine–Hugoniot problem. An initial pilot instead multiplied
the radial atmosphere on both sides. At the borderline `M = 1.1`, that added a
second normal pressure gradient and made the constructed case non-exact. The
synthetic construction was corrected before the full matrix; the detector was
not changed. The full result is therefore prospectively tested after this
amendment, not wholly prespecified.

Positive cases are exact shocks at `M = 1.1, 1.5, 3.0`. Negative cases are:

- pressure-balanced contacts with density contrasts 10 and 100;
- a compressive isentropic wave with pressure endpoints 0.9 and 1.1;
- a rarefaction fan.

Every case is evaluated at `M_min = 1.05, 1.1, 1.2`. A shock above the selected
threshold must be detected within two effective cells and both inferred Mach
numbers must be within 10%. A shock below threshold must not be detected. Every
negative must remain unflagged for the complete three-arm validation to pass.

## Results

| Validation block | Result |
| --- | ---: |
| Exact-shock rows | 54 |
| Expected detections | 48 / 48 passed |
| Expected threshold exclusions (`M=1.1`, `M_min=1.2`) | 6 / 6 passed |
| Negative rows | 72 |
| Negative failures at `M_min=1.05` | 6 / 24 |
| Negative failures at `M_min=1.1` | 0 / 24 |
| Negative failures at `M_min=1.2` | 0 / 24 |

All six failures are the isentropic sound wave at `M_min = 1.05`; contacts and
rarefactions produce no accepted cells at any threshold.

Across expected exact-shock detections:

| True M | Median `M_p` relative-error range | Median `M_rho` relative-error range |
| ---: | ---: | ---: |
| 1.1 | -0.414% to +0.208% | -0.544% to +0.274% |
| 1.5 | -0.531% to +0.127% | -0.794% to +0.191% |
| 3.0 | -0.583% to +0.133% | -1.829% to +0.428% |

The largest 95th-percentile front-position error is `0.959` effective cells.
Median absolute alignment between the inferred and true normal ranges from
`0.808` on an oblique, cell-centred discontinuity to effectively `1.0` for an
axis-aligned front. Normal alignment was diagnostic, not a tuned acceptance
criterion.

The pressure-balanced contact test is necessary but weak: its physical common
velocity makes `div(v) = 0`, so it is rejected by the first gate before the
jump discrimination is challenged. Numerically broadened/noisy contacts and
multi-feature overlaps remain untested.

## Failure mechanism and serious alternatives

Pressure and density jump consistency cannot by itself identify irreversible
shock heating at weak amplitude. An isentropic compression can occupy the same
two-dimensional `(p2/p1, rho2/rho1)` neighbourhood as a weak shock closely
enough to satisfy the 20% agreement tolerance.

The least disruptive defensible options are:

1. Keep `M_min = 1.1` as the only classification threshold and label the
   1.05 arm a non-specific morphology sensitivity that cannot establish a
   shock. This matches the present synthetic evidence but changes the approved
   meaning of the sensitivity arm and must be fixed before native inspection.
2. Add an entropy-production condition and revalidate it against broadened
   shock tubes plus no-jet numerical noise. This directly separates the
   isentropic counterexample, but the physical entropic-function increment is
   only `0.0674%` at `M=1.1` and `0.00934%` at `M=1.05`; a usable threshold may
   be below native numerical noise. It cannot be adopted from algebra alone.
3. Use temporal front propagation or shock-frame mass/momentum closure as an
   independent discriminator. This is stronger but needs adjacent native
   outputs and a new, prospectively frozen validation design.

Schaal and Springel's use of aligned density/temperature gradients, a complete
shock zone and variable jump width is another serious comparator. Evidence
that would discriminate the options is a blinded suite of numerically broadened
weak shocks, finite-amplitude acoustic pulses, stratified/noisy contacts and
overlapping waves on the PLUTO grid, followed by a no-jet native false-positive
measurement. Synthetic step recovery alone is insufficient.

## Verification and reproducibility

Focused tests:

```bash
uv run pytest -q tests/test_independent_bow_shock.py
# 19 passed
```

Full matrix:

The complete 126-row result and source/input hashes are retained in
`assets/independent_bow_shock_validation_2026-11-04/`.

```bash
uv run python scripts/science/validate_independent_bow_shock.py
# exits 1 and reports promotion_status = FAIL_NO_PROMOTION
```

Use `--allow-science-fail` only to inspect the complete negative result with a
zero process exit. The test suite explicitly expects the 1.05 sound-wave
counterexample; a green pytest run does not convert the scientific gate to a
pass.

## Recommendation and residual risk

Retain the code and failing harness as a reproducible design test, but do not
promote the three-threshold finder to the G-HI native analysis. Amend the
scientific criterion first, preferably by making 1.1 the sole classification
threshold while developing an entropy- or time-based discriminator for lower
Mach sensitivity. Then validate numerically broadened/noisy cases before any
arc-alignment claim.

Independent scientific review is unlikely to change the algebraic
counterexample or the no-promotion decision. It would materially improve the
choice and calibration of the replacement discriminator, especially because
entropy production at `M <= 1.1` is extremely small and native numerical noise
has not yet been measured.
