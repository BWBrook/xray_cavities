# Turn 15: emission decomposition, cavity filling and Results sequence

Date: 2026-11-05. Status: implementation plan; no new native result or detector
acceptance. Prepared by Codex from the 4-November Patrick/Stas requests and
Claude's board messages 2879–2880. The independent spherical-budget submissions
remain first priority. This diagnostic reads existing outputs only.

## First native comparison

Use G-HI snapshot 20 and its actual initial snapshot, after qualification of
the accepted continuation/source chain. Bind actual HDF5 time, grid, primitives,
environment, emissivity code/tables and retained-map identities. Start with
0/90-degree maps; calculate 45 degrees in the same bounded extraction as the
projection cross-check. These are azimuths about the jet axis, all side-on.
Retain the existing G-HI 48–50 exclusion in any later extension.

Use the retained observer seed-and-grow and 5%-deficit masks as **diagnostic
comparators**, with their original backgrounds and selection parameters.
Neither is promoted to a production detector by this test. Do not use tracer
truth to choose a threshold, repair an outline or optimise an observer fit.
Report each lobe and the bipolar result, including nondetections and aperture
contact; an empty detection has no defined filling fraction.

## Cell partition and additive projected quantities

Promote stored tracer to float64 before applying the strict threshold. For
each speed threshold v_c, define the disjoint current-cell masks

```
C = tr1 > 1e-3
A = (~C) & (sqrt(vx1**2 + vx2**2 + vx3**2) >= v_c)
E = (~C) & (~A)
```

The expanding-source diagnostic is C+A; E is approximately static external
gas. A is operationally **moving ambient**, not proof of a jet origin or an
irreversible shock. Slow lobe cells stay in C. Preserve out-of-range tracer
counts and boundary/coverage flags. Do not require a shock mask or supersonic
motion. Use 100 and 300 km/s first, with a predeclared 30-km/s sensitivity arm
to expose weak motion; none defines a universal cavity or static medium.
Also tabulate the speed distribution of tracer-negative cells with >=1%
density or pressure change, so even the lowest cut's missed disturbance is
visible. Distinguish possible boundary-driven motion from the source.

Apply one projection operator P, path lengths and pixel grid to all fields.
For k in C,A,E, keep the current mask fixed for both epochs and save

```
S_k     = P[1_k(t) j(t)]
S_0,k   = P[1_k(t) j(0)]
D_k     = S_0,k - S_k                 # signed deficit contribution
L_k     = P[1_k(t)]                   # geometric path length
S       = S_C + S_A + S_E
S_0     = S_0,C + S_0,A + S_0,E
D_0     = D_C + D_A + D_E = S_0 - S
```

Verify component closure pixelwise and after area integration, independently
against the full-map projection. Use the same cells at t=0, not a newly
classified initial mask. Save signed deficits, not positive-clipped maps.
Masking emission is not removal of the gas in a physical no-jet simulation;
the initial state also is not the evolved no-jet counterfactual.

Compare the original observer background B_obs separately:

```
D_obs = B_obs - S = D_C + D_A + D_E + (B_obs - S_0).
```

This identity distinguishes lobe deficits, moving/static ambient changes and
background-estimation differences. Show source-only, external-only and total
brightness with corresponding same-cell initial references and deficits.
An independently fitted component background, if shown, is an additional
observer experiment: its deficits do not inherit this additive identity.

For the shell diagnostic replace moving-ambient emissivity by its initial
same-cell value: S_test = S + D_A. First hold B_obs fixed and reapply the
unchanged detection rule; then refit the background and repeat. Compare both
with the original mask. Keep the sign: heating/compression need not increase
the corrected 1-keV emissivity. The change is a controlled emissivity
diagnostic, not a hydrodynamic counterfactual or shock-energy measurement.

## Filling requires both a spatial definition and a denominator

Claude's symmetrized revolution estimator pi*integral(|u| dA) does not uniquely
specify a binary 3D region for an asymmetric outline. At each z, revolve the
selected positive-u radial intervals and negative-u radial intervals separately
about the jet axis, retaining holes/disconnected intervals. This gives two
binary reconstructed solids W+ and W-. Their mean geometric volume equals
the symmetrized estimator when |u| is integrated exactly within each pixel.
Do not take their union, fill holes or substitute a fitted ellipse silently.

For each solid use native cell-centre membership and full finite-volume cell
weights to report:

- volume filling: sum(W C V) / sum(W V);
- lobe mass share: sum(W C rho V) / sum(W rho V);
- lobe pressure-integral share: sum(W C p V) / sum(W p V).

The last ratio is also the 2.5pV or 4pV share; the common coefficient cancels.
These are binary-tracer regional shares, not microscopic pure-jet fractions.
Report W+ and W- separately and a pooled ratio formed from summed numerators
and summed denominators. This exposes the reconstruction ambiguity instead
of averaging fractions with unequal volume. Report exact pixel-revolution
volume and native-cell volume separately, with their discretization mismatch;
never divide a native-cell numerator by an incompatible geometric denominator
and call the resulting number a bounded filling fraction. Flag domain
truncation and check a refined geometry on a synthetic grid before use.

For projected emission, evaluate the fixed observed mask M in the full line
of sight. Give the cocoon brightness share integral_M(S_C)/integral_M(S),
where positivity permits, and separately the signed **deficit-attribution
ratio** integral_M(D_C)/integral_M(D_obs). The latter is Claude's cocoon
replacement proposal. It can exceed one, be negative or be undefined when
the observed deficit vanishes; it is not a fraction constrained to [0,1].
Publish numerator, denominator and cancellation/near-zero flags, without
clipping. These are brightness integrals, not detector counts unless an
instrument response is actually applied. Line-of-sight C emission is distinct
from emission inside the reconstructed W solids; label both domains.

Explain apparent filling using the complete signed deficit identity above.
For missed tracer sightlines, bin L_C, L_C/L_whole, S_0 and D_obs/B_obs;
compare tips/rims with interiors and report completeness/purity separately
from volume recovery. A large projected purity does not prove 3D filling.

## Reuse and smallest implementation

| Existing code | Reuse or constraint |
| --- | --- |
| `build_q031_native_emission.py`: `load_tables`, `cell_emissivity` | Bind the same XRAiSE/APEC/Gaunt identities. Preserve retained-linear versus clamped-coordinate comparison and non-finite/out-of-table diagnostics; do not silently change correction policy. |
| Same file: `project_chunk`, `accumulate_direct_y`, `accumulate_overlap_fields`, `accumulate_tracer_overlap` | Reuse native-cell projection arithmetic and tracer maximum. Adapt accumulator names for C/A/E in a separate small G-HI/20 driver. Cross-check physical edges against `measure_q031_fluxes.read_grid`; the pilot helper reconstructs edges from centres. |
| Same file: `closure_check`, `validate_projected_integral`, `exact_abs_u_moments` | Reuse additive/integrated checks and exact positive/negative-u moments. |
| Same file: `run_case`, `select_source`, `reference_rows` | Do not call unchanged for this test: they enforce snapshot 40 and old shock-reference contracts. Preserve the historical pilot; do not relax those gates to relabel it as the new analysis. |
| `build_q032_selected_age_method_ladder.py`: `load_view`, `ladder_runs`, `analyse_view`; `xray_cavity_method_ladder.py`: `seed_grow`, `deficit_threshold`, `score_rows` | Reuse unchanged observer comparators and area metrics. `side_volumes` uses pixel-centre moments; show its difference from exact moments. |
| `independent_bow_shock.py`: `iter_shock_candidates_tiled` | Optional independent overlay, only after explicitly revising and testing the compressive-front contract. Current code still labels shock candidates and includes temperature/Mach-agreement gates; renaming its output alone does not implement the proposed new estimand. |

One streamed native traversal can compute current/initial emissivity once,
then accumulate the three velocity partitions, path maps and native filling
integrals for all three views. Keep only compact maps/tables locally; native
fields and any working arrays stay on the compute resource. Geometry of the
observed W solids is known from the retained masks before traversal. A later
background-refit mask must not be assigned old W filling numbers; report
projected recovery first or explicitly perform its new native integration.

Required tests: mask exhaustiveness/disjointness with slow tracer cells;
all-three-component speed and equality; current-mask initial subtraction;
pixel/integrated map and signed-deficit identities; bright/negative-change
ambient examples; absent/near-zero deficit; asymmetric/holey revolution
solids and volume convergence; fixed-background versus refitted-background
separation; wrong native/table/map identity rejection. The existing failed
weak-wave shock test stays failed under its original shock interpretation.

Smallest returned package: per-view NPZ maps and projection receipt; per-side
filling/deficit/path-length CSV; three matched map panels with tracer/observer
outlines; a before/replacement/refit recovery table; correction-domain and
boundary flags. This answers G-HI/20 first. Four-case expansion follows only
after checking native/projection identity and these arithmetic tests.

## Results and figure sequence

1. **True-volume energetics:** per-case time series of resolved native
   2.5*sum_C(pV) and 4*sum_C(pV) divided by true-age bipolar input, alongside
   spherical thermal/kinetic/gravitational changes split C/ambient. Show the
   100/300-km/s aperture sensitivity, missing radii, coverage and contamination
   flags. Enthalpy is a proxy comparison, never an additive fourth energy term.
   Do not label its shortfall as shock energy without component evidence.
2. **Additional observation error:** matched V_X/V_C and H_X/H_native by
   case, age, hemisphere and side-on azimuth. First fix pressure to the
   native lobe mean p_bar = sum_C(pV)/V_C, so the proxy ratio isolates volume;
   then show observer p_X/p_bar and the full H_X/H_native. This is a declared
   reference convention, not a claim that pressure is uniform. Present
   nondetections/clipping and independent truth metrics, without reinstating
   withdrawn legacy recovery numbers.
3. **Explanation maps:** G-HI/20 source/external/total brightness and signed
   deficits, followed by the replacement/refit comparison and filling table.
   Extend representative contrasts to the four cases after the first check.
4. **Clock layer later:** H_X/t_est versus input power, keeping age bias
   separate from both physical-proxy and observational pressure/volume error.

Update manuscript claims only from measured, source-bound results. Existing
claims of shock processing or successful observer recovery cannot be carried
forward solely because these planned panels share their topic.
