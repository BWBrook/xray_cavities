# C-LO/G-LO Comparison-Case Readiness

Date: 2026-07-01

Status: `complete_local_readiness_decision_packet`

Decision label:

```text
C_LO_G_LO_READINESS_LOCAL_DOCS_SUFFICIENT_C_LO_PREFLIGHT_NEXT
```

## Summary

Goal 029 maps the accepted `C-HI` control surface onto the planned comparison
cases without running or staging anything. The readiness decision is clear:
the repo-local docs/config evidence is sufficient to choose the next branch,
and the next branch should be a Barry-authorized bounded `C-LO` config and
asset preflight packet.

This is not compute authorization. It does not prepare or submit `C-LO` or
`G-LO`, and it does not claim a comparison result.

## Case Scope

The frozen three-case specification defines:

| Case | Role | Environment | Jet power | Jet speed | Default order |
| --- | --- | --- | ---: | ---: | ---: |
| `C-HI` | accepted control case | Stewart cluster `002_003` | `1e45 erg/s` | `0.1 c` | 1 |
| `C-LO` | baseline science anchor | Stewart cluster `002_003` | `1e43 erg/s` | `0.1 c` | 2 |
| `G-LO` | environment-dependence case | Stewart group `002_031` | `1e43 erg/s` | `0.1 c` | 3 |

Given the accepted Goal 028 control surface, `C-LO` is the right first
comparison preflight. It isolates jet power while keeping the same Stewart
cluster environment as `C-HI`. `G-LO` should remain queued as the environment
comparison unless Barry explicitly changes the launch order.

## Local Readiness

Ready locally:

- The three-case science specification defines `C-LO` and `G-LO`.
- The Honours plan and Meeting 2 plan make the three-case suite mandatory for
  interpretation.
- The accepted C-HI contracts are now strong enough to inherit.
- `scripts/science/render_three_case_configs.py` contains case specs for
  `C-HI`, `C-LO`, and `G-LO`, plus an asset-aware rendering path.
- `scripts/kunanyi/jet_setup_production_template.pbs` is a generic
  production-oriented template.

Not ready for execution inside this goal:

- The ignored local Stewart tabulated CSVs are not visible in this checkout at
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv` and
  `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv`.
- There is no case-specific `C-LO` or `G-LO` wrapper yet.
- No `C-LO` or `G-LO` outputs or products exist.
- Remote preflight, staging, and PBS submission are explicitly out of scope.

The missing ignored CSVs are not a reason to revisit scientific defaults. Prior
repo evidence records that the Stewart cluster and group tabulated profiles
were supplied and passed Nectar and Kunanyi no-jet gates. The next execution
packet simply needs to verify or restore those assets before rendering or
staging anything.

## Inherited C-HI Contracts

Future comparison-case work should inherit these controls:

- Endpoint-first comparison: target the 50 Myr endpoint surface before any
  source-age axis.
- Views: use `0`, `45`, and `90 deg`.
- Projection: require
  `projection.projected_accumulation=edge_overlap_uniform_cell_projection` for
  nonzero views.
- Topology: carry the Goal 027 conditional connected-core status as a caveat,
  not a final topology freeze.
- Energy: keep `pV`, adopted `2.5pV`, and `4pV` visible; keep Level 3 gravity
  as `blocked_missing_potential`.
- Radio: keep sparse PRAiSE and particle-binned maps diagnostic only.
- Provenance: add comparison products beside accepted C-HI products and do not
  overwrite them.
- PBS stop rule: if a future authorized PBS job is submitted and verified
  queued or running, wake X-ray Cavities and stop.
- Archive contract: package from stable snapshots or file lists rather than a
  live mutating analysis root.

The full contract table is in
`assets/c_lo_g_lo_comparison_readiness_2026-07-01/inherited_c_hi_contracts.csv`.

## Next Branch

Recommended next goal shape:

```text
barry_authorized_c_lo_config_asset_preflight_packet
```

Minimum scope for that future packet:

1. Verify or restore the Stewart cluster `002_003` tabulated CSV asset.
2. Render a `C-LO` config bundle from the existing three-case config renderer.
3. Validate rendered units and C-HI-inherited defaults.
4. Create or bind a bounded `C-LO` wrapper or exact qsub contract.
5. If remote preflight is authorized, verify remote paths, modules, hashes, and
   wrapper syntax.
6. Stop before any PBS submission unless that future packet explicitly
   authorizes one.

`G-LO` should wait behind this first `C-LO` preflight unless Barry chooses to
override the order. That keeps the comparison branch conservative: first test
the lower-power cluster case using the same environment family as the proven
control, then carry the learned contract into the group-environment case.

## Escalation

No Stas/Patrick input is needed for this local readiness decision.

Barry authorization is required before:

- restoring or staging assets for execution;
- remote preflight;
- any PBS submission;
- changing the default launch order;
- running a comparison case.

Stas/Patrick input becomes necessary only if a future packet proposes a
scientific-default change, final topology freeze, radio-observable method
freeze, gravitational Level 3 convention, or publication-facing claim.

## Assets

Machine-readable assets live in:

```text
docs/science/assets/c_lo_g_lo_comparison_readiness_2026-07-01/
```

Primary files:

- `comparison_case_readiness_matrix.csv`
- `inherited_c_hi_contracts.csv`
- `local_blocker_register.csv`
- `future_preflight_requirements.csv`
- `authorization_thresholds.csv`
- `next_step_recommendation.csv`
- `comparison_readiness_metadata.json`

## Non-Claims

Goal 029 does not authorize remote work, local rendering for execution,
comparison-case processing, source-age substitution, `C-LO`/`G-LO` compute,
publication-facing claims, commits, pushes, cleanup, or expert contact. It is
an internal readiness packet for the next Barry-authorized branch.
