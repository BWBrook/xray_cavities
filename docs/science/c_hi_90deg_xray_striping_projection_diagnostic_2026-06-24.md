# C-HI 90-Degree X-Ray Striping Projection Diagnostic

Date: 2026-06-24

## Summary

Goal 014 diagnoses the visible vertical striping in the Goal 012 final
`C-HI`, `90 deg` corrected X-ray panel using only existing local Goal 005,
Goal 011, and Goal 012 products plus repo-local projection code.

Recommended decision label:

```text
X_RAY_METHOD_REFINEMENT_FIRST
```

The local evidence points to a projection/binning occupancy issue at or near
`90 deg`, not a display-only artifact, not an APEC/Gaunt correction-only
effect, not a physically meaningful cavity feature, and not a reason for
Stas-agent or Patrick-agent escalation by itself.

The next goal should be a local X-ray/projection-method refinement goal before
opening `C-HI` source-age sampling. Q-018 and Q-019 can remain useful review
inputs, but they do not need to block a local method-refinement Goal 015.

## Evidence Base

Local products inspected:

- Goal 005 `0 deg` baseline:
  `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- Goal 011 `45 deg` broadening product:
  `docs/science/c_hi_final_45deg_viewing_angle_broadening_2026-06-23.md`
- Goal 012 `90 deg` broadening product:
  `docs/science/c_hi_final_90deg_viewing_angle_broadening_2026-06-23.md`
- Goal 013 next-step decision packet:
  `docs/science/c_hi_viewing_angle_trio_next_step_decision_gate_2026-06-23.md`

Repo-local code inspected:

- `scripts/science/xraise_grid_smoke.py`
- `scripts/science/build_final_45deg_viewing_angle_broadening.py`
- `scripts/science/build_final_90deg_viewing_angle_broadening.py`

New diagnostic assets:

```text
docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/striping_diagnostics.csv
docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/projection_axis_diagnostics.csv
docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/next_step_recommendation.csv
docs/science/assets/c_hi_90deg_xray_striping_projection_diagnostic_2026-06-24/column_positive_fraction_profiles.png
```

The helper used to generate these assets is:

```text
scripts/science/diagnose_90deg_xray_striping.py
```

It is covered by:

```text
tests/test_90deg_xray_striping_diagnostic.py
```

## Quantitative Findings

The diagnostic compares finite/positive occupancy, all-zero projected columns,
near-empty columns, adjacent-column versus adjacent-row changes, raw/corrected
mask agreement, and projection-axis regularity.

Key X-ray occupancy evidence:

| View | Layer | Positive fraction | Empty column fraction | Empty columns | Positive mask equals raw |
| --- | --- | ---: | ---: | ---: | --- |
| `0 deg` | corrected X-ray | `1.0` | `0.0` | `0` | `not_applicable` |
| `45 deg` | raw X-ray | `0.9770833333333333` | `0.02291666666666667` | `22` | `true` |
| `45 deg` | corrected X-ray | `0.9770833333333333` | `0.02291666666666667` | `22` | `true` |
| `45 deg` | correction ratio | `0.9770833333333333` | `0.02291666666666667` | `22` | `true` |
| `90 deg` | raw X-ray | `0.5833333333333334` | `0.4166666666666667` | `400` | `true` |
| `90 deg` | corrected X-ray | `0.5833333333333334` | `0.4166666666666667` | `400` | `true` |
| `90 deg` | correction ratio | `0.5833333333333334` | `0.4166666666666667` | `400` | `true` |

The 90-degree tracer layer has a larger empty-column fraction
(`0.7083333333333334`), but that is not diagnostic by itself because the tracer
max map is physically compact. The important result is that the ambient X-ray
raw, corrected, and correction-ratio layers all share the same large all-zero
projected-column mask.

The corrected X-ray stripe-anisotropy metric is:

- `0 deg`: `0.5595703840733774`
- `45 deg`: `34.78510916439285`
- `90 deg`: `13.08690701740036`

The high 45-degree anisotropy is mostly a smooth projected-gradient effect with
only `22/960` all-zero columns. The 90-degree product has a much larger
occupancy failure: `400/960` all-zero columns in every X-ray-related layer.

## Axis And Projection Findings

The diagnostic confirms that the `45 deg` and `90 deg` product-local
`x_kpc.tsv` and `u_kpc.tsv` arrays are identical within each product.

That identity is expected from the current implementation, not suspicious by
itself. In `scripts/science/xraise_grid_smoke.py`, nonzero projected views
write the projected sky-horizontal axis to `x_kpc.tsv` and also write the same
array to `u_kpc.tsv`.

The 90-degree projected horizontal axis is regular:

- `n = 960`
- `min_kpc = -199.7881303`
- `max_kpc = 199.7881303`
- median step `0.4166592999999921 kpc`
- strictly increasing: `true`

This axis is not all-close to the original 0-degree nonuniform `x` axis. At
`90 deg`, the projected coordinate is effectively the original `y` direction
with sign reversal. The current projected-view path uses uniform projected bins
and center-bin accumulation, so a stretched/nonuniform source grid can leave
many projected bins empty at the near-exact side-on view.

## Diagnostic Classification

Display or plotting artifact:

```text
not supported
```

The striping is present in the underlying matrices as full-height all-zero
projected columns. It is not only a rendering/layout issue in the PNG.

APEC/Gaunt correction-only artifact:

```text
not supported
```

The raw X-ray, corrected X-ray, and correction-ratio layers share the same
positive mask at `90 deg`. The correction layer does not create the mask.

Physically meaningful projection feature:

```text
not supported by current evidence
```

The all-zero full-height ambient-X-ray columns are a grid/projection occupancy
pattern. The tracer map is compact, but the ambient X-ray mask is not explained
as a lobe/cavity structure by the local evidence.

Upstream XRAiSE calculation issue:

```text
not the leading diagnosis
```

Goal 012 remote stdout reported `hdf5_preflight=passed`,
`xray_90deg_validation=passed`, and `cavity_validation=passed`, with zero-byte
stderr. The local symptom aligns with repo-local projection/bin accumulation
after the existing products are written. A later refinement goal can still
confirm this with a synthetic stretched-grid reproduction.

Projection/binning artifact:

```text
supported
```

The `90 deg` raw, corrected, and correction-ratio X-ray maps share a large
all-zero projected-column mask, while the `45 deg` product shows only a small
edge occupancy effect. The current code path uses uniform projected bins and
center-bin accumulation for nonzero projected views.

## Recommendation

Use this diagnostic to write a local X-ray/projection-method refinement goal
before source-age sampling.

Suggested next-goal shape:

1. reproduce the empty-bin failure with a small synthetic stretched grid at
   `90 deg`;
2. revise the projected-axis/bin accumulation method for near-90-degree views;
3. prove the revised method with focused unit tests and local assets; and
4. rerun only bounded existing-output post-processing if the local method test
   passes and X-ray Cavities authorizes it.

Do not escalate to Stas-agent or Patrick-agent just because Q-018/Q-019 exist.
Escalation would be appropriate only if the local refinement exposes a real
physics/default decision, a production-compute decision, or a significant
blocker.

## Carried Caveats

- Projection-sensitivity only; not publication-ready observables.
- The 90-degree striping should remain visible in review evidence until the
  projection method is refined or explicitly accepted.
- Connected-envelope/X-ray topology caveat is still active.
- Sparse-radio products remain diagnostics, not validated radio observables.
- Level 3 gravity remains `blocked_missing_potential`.
- Future energy summaries should carry `pV`, adopted `2.5pV`, and `4pV`.

## Non-Claims

- This diagnostic does not claim a final observable X-ray product.
- This diagnostic does not change scientific defaults, thresholds, PLUTO
  outputs, XRAiSE physics, PRAiSE parameters, selected IDs, or production-run
  contracts.
- This diagnostic did not run remote commands, Open OnDemand, SSH/SCP, PBS
  jobs, finalizers, Kunanyi staging, PLUTO production, XRAiSE/PRAiSE/radio/
  cavity product regeneration from HDF5, source-age sampling, `C-LO`, `G-LO`,
  comparison-case processing, broad batch work, document builds, commits,
  pushes, or external human/agent contact.
