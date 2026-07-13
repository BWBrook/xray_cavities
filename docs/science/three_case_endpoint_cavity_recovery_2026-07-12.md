# Three-case endpoint cavity recovery and truth alignment

Date: 2026-07-12

Status: `complete_product`

Decision label:
`THREE_CASE_CAVITY_RECOVERY_AND_LEVEL12_ALIGNMENT_COMPLETE`

## Purpose

Goal 040 tests how much of the accepted 50 Myr C-HI, C-LO, and G-LO lobe
surface can be recovered as an X-ray deficit at `0/45/90 deg`, then aligns
that observer-side recovery with independent Level 1 injected-energy and
Level 2 tracer-lobe truth. It is a common three-case prove-out surface, not a
final observational cavity protocol or publication-ready observable.

## Recovery method

The method keeps three evidential layers separate:

1. X-ray recovery uses corrected X-ray maps and physical axes only.
2. Projected tracer masks at `1e-3`, `5e-3`, and `1e-2` are post-hoc
   validation targets and never influence the X-ray mask.
3. Full-grid Level 1/2 truth and tracer-shell ambient pressure are independent
   remote evidence used only after recovery.

The accepted background is a tracer-blind azimuthal median profile in 5 kpc
radial bins, smoothed over 10 kpc, with a 180 kpc background field and a
nested 120 kpc candidate aperture. The base candidate is the highest-deficit
1 percent of projected physical area inside that aperture. Components must
cover at least 25 kpc2 and use 8-connectivity.

Physical-area weighting is essential because projected pixel areas differ
between views. A pixel-count implementation was rejected during the final
audit: it introduced spurious view dependence and unphysical C-LO oblique
ratios. A synthetic unequal-pixel-area regression test now guards the corrected
selection rule.

The sensitivity grid contains 15 combinations: radial-bin/smoothing pairs
`4/8`, `5/10`, and `8/15` kpc crossed with candidate physical-area fractions
`0.5`, `1`, `2`, `3`, and `5` percent.

## Recovery observations

The base method finds two opposite-side X-ray components in all nine
case/view panels. The selected physical area is approximately `432-452 kpc2`.
At projected tracer threshold `5e-3`, every selected base X-ray pixel lies
inside the tracer projection (`xray_precision=1.0`), while tracer recall is:

- C-HI: `0.0208-0.0303`;
- C-LO: `0.1927-0.2015`;
- G-LO: `0.0897-0.1099`.

The X-ray deficit is therefore a high-purity but incomplete subset of the
tracer-defined projected lobe under this protocol.

The corrected geometric-depth volumes are substantially more stable across
view than the rejected pixel-count result:

- C-HI: `5.48e3-5.96e3 kpc3`;
- C-LO: `5.16e3-5.18e3 kpc3`;
- G-LO: `5.18e3-5.20e3 kpc3`.

Line-of-sight depth is still not identified by the maps; minor, geometric,
and major depth assumptions remain explicit. Broader candidate fractions also
expose topology sensitivity, so no final observational topology is frozen.

## Remote truth evidence

PBS job `756092.kunanyi-ohpc` / `tri_truth` completed with `Exit_status=0`,
walltime `00:22:16`, and empty stderr. All three case validations and the
aggregate `three_case_truth_validation=passed` marker are present. The compact
archive has 24 members, validates against its internal checksums, and has
SHA-256:

`474c06f81d09acdb616345bc56d7919738d894d317b0d98a1fee7f941b9d2e6b`

`Stageout_status=1` remains a scheduler caveat, but the archive and logs were
present at the requested stage paths and were retrieved directly.

At tracer threshold `5e-3`, the bipolar truth surface is:

| Case | Level 1 injected energy (erg) | Level 2 volume (kpc3) | Level 2 energy (erg) | Level 2 / Level 1 |
| --- | ---: | ---: | ---: | ---: |
| C-HI | `3.156e60` | `7.405e5` | `1.388e60` | `0.440` |
| C-LO | `3.156e58` | `1.322e4` | `2.014e58` | `0.638` |
| G-LO | `3.156e58` | `7.917e4` | `1.601e58` | `0.507` |

Side-specific tracer-shell pressures are positive and finite. They are about
`2.78-2.81e-11 dyn cm-2` for C-HI, `3.98-3.99e-11 dyn cm-2` for C-LO, and
`4.10-4.14e-12 dyn cm-2` for G-LO.

## Truth alignment

The base geometric X-ray volumes recover only part of the Level 2
tracer-defined volume:

- C-HI: `0.00740-0.00804` of Level 2;
- C-LO: `0.3906-0.3918` of Level 2;
- G-LO: `0.0655-0.0656` of Level 2.

Using side-specific tracer-shell pressure and the adopted `2.5pV` convention,
the geometric-depth hybrid proxy is:

- C-HI: `0.00358-0.00389` of Level 1 and `0.00813-0.00885` of Level 2;
- C-LO: `0.478-0.480` of Level 1 and `0.750-0.752` of Level 2;
- G-LO: `0.0497-0.0499` of Level 1 and `0.0980-0.0983` of Level 2.

These are hybrid tracer-pressure/X-ray-volume proxies. They are not
observer-only cavity energies. The large case contrast is an observation on
the accepted processed endpoints; its physical interpretation remains an
inference requiring the retained topology, pressure, and depth caveats.

## Products

Asset root:

`docs/science/assets/three_case_endpoint_cavity_recovery_2026-07-12/`

Key observer-side files:

- `three_case_endpoint_cavity_recovery.png`;
- `xray_recovery_summary.csv`;
- `xray_component_summary.csv`;
- `projected_tracer_alignment.csv`;
- `method_sensitivity.csv`;
- `three_case_endpoint_cavity_recovery_metadata.json`.

Key truth-alignment files:

- `case_truth_summary.csv`;
- `truth_threshold_sensitivity.csv`;
- `tracer_shell_pressure_context.csv`;
- `xray_truth_alignment.csv`;
- `xray_truth_method_sensitivity.csv`;
- `three_case_truth_alignment.png`;
- `three_case_truth_alignment_metadata.json`;
- `remote_completion_summary.csv`.

Retrieved provenance is preserved under `remote_logs/`; extracted compact
truth products are under `remote_products/`. No HDF5, PLUTO `data.*`, or
particle payload was copied locally.

## Interpretation boundary

Projected recovery is observer-side; tracer overlap and Level 1/2 are
simulation truth; tracer-shell pressure plus X-ray volume is a hybrid proxy.
Sparse radio remains diagnostic, Level 3 gravity remains
`blocked_missing_potential`, and final observational topology remains open.
