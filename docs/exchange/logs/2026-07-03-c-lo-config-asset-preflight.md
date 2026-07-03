# 2026-07-03 - C-LO Config And Asset Preflight

Goal 030 created a bounded C-LO config/asset preflight packet.

## Status

Status: `blocked_local_asset_missing_no_remote_preflight`.

Decision label:
`C_LO_PREFLIGHT_BLOCKED_MISSING_LOCAL_STEWART_002003_ASSET`.

## Products

Science note:

```text
docs/science/c_lo_config_asset_preflight_2026-07-03.md
```

Asset bundle:

```text
docs/science/assets/c_lo_config_asset_preflight_2026-07-03/
```

Key assets:

- `local_asset_preflight.csv`
- `c_lo_config_audit.csv`
- `inherited_contract_checklist.csv`
- `wrapper_contract_audit.csv`
- `remote_preflight_status.csv`
- `preflight_blocker_register.csv`
- `next_step_recommendation.csv`
- `c_lo_config_asset_preflight_metadata.json`
- `rendered_c_lo_placeholder_config/`

Wrapper contract:

```text
scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs
```

Goal log:

```text
docs/goals/030-c-lo-config-asset-preflight/Log.md
```

## Interpretation

The C-LO science/config definition is locally clear: Stewart cluster `002_003`,
`JET_PWR = 1e43 erg/s`, `JET_SPD = 0.1 c`, 50 Myr endpoint-first comparison,
and inherited C-HI contracts for refined nonzero projections, topology caveat,
Level 3 gravity blocker, sparse-radio diagnostic status, no-overwrite
provenance, PBS stop rule, and stable archive behavior.

The local asset gate failed because the current checkout does not contain
`env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`, and the
documented ignored recovery archive `env/environments.zip` is also absent. A
placeholder config bundle was generated for static audit only; it is not
launch-ready.

Remote preflight was not attempted because the local gate did not pass.

## Next Step

Recommended next goal:
`restore_local_stewart_cluster_asset_and_rerun_c_lo_preflight`.

That goal should restore the ignored Stewart cluster `002_003` tabulated CSV
from a trusted source, verify checksum/size/row count/provenance, rerender the
C-LO config with `--require-assets --check-local-assets`, and only then attempt
bounded read-only Kunanyi preflight. No C-LO compute should be authorized until
that clean preflight exists.

## Boundary Confirmation

No remote commands, Open OnDemand, SSH/SCP, `qstat`, Kunanyi staging, PBS jobs,
finalizers, retrieval, polling, PLUTO, XRAiSE, PRAiSE, radio, cavity
extraction, source-age products, endpoint products, `C-LO`/`G-LO` processing,
comparison-case compute, broad sweeps, scientific-default changes, commits,
pushes, cleanup, Stas/Patrick contact, `agent_comms` edits, or accepted-asset
overwrites occurred.
