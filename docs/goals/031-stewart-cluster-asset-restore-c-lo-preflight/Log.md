# Goal 031 Log - Stewart Cluster Asset Restore And C-LO Preflight

Date: 2026-07-03

## Start State

- Working directory: `/Users/bwbrook/papers/xray_cavities`.
- Branch/HEAD at start: `main` at `2393f19`.
- Git status at start: `## main...origin/main`.
- Fast-forward check: `git pull --ff-only` reported already up to date.
- Repo-local `AGENTS.md` was read before goal work.

## Boundary

Goal 031 is an operational asset/preflight repair. No PBS submission, PLUTO,
XRAiSE, PRAiSE, radio, cavity extraction, source-age products, endpoint
products, `C-LO`/`G-LO` science compute, comparison-case compute, broad
sweeps, finalizers, science-output retrieval, polling loops,
scientific-default changes, environment substitution, source-age substitution,
commits, pushes, cleanup, Stas/Patrick contact, or `agent_comms` edits are
authorized.

## Evidence Read

- `AGENTS.md`.
- `docs/exchange/current_status.md`.
- Goal 030 science note, Goal log, and asset CSVs:
  `local_asset_preflight.csv`, `preflight_blocker_register.csv`,
  `c_lo_config_audit.csv`, and `wrapper_contract_audit.csv`.
- `docs/exchange/logs/2026-05-05-stewart-assets-and-graile.md`.
- `docs/science/asset_inventory_2026-05-02.md`.
- `docs/science/stewart_environment_gate_2026-05-05.md`.
- `docs/science/stewart_environment_gate_status_2026-05-05.md`.
- `scripts/science/render_three_case_configs.py`.
- `scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs`.
- `tests/test_c_lo_config_asset_preflight_contract.py`.

## Work Performed

- Re-checked the expected ignored local paths:
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv` and
  `env/environments.zip`; both were absent before restore.
- Used the authorized Chrome/Open OnDemand route to open the TPAC SSH selector.
- Searched only the authorized trusted Kunanyi candidate paths and bounded
  roots. All five exact candidates existed and matched SHA-256
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`.
- Restored exactly `tabulated_cosmo_002003.csv` from
  `/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/cluster_002003/`
  into the ignored local path
  `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`.
- Validated the restored table: `608000` bytes, `4000` rows, `6` columns,
  strictly increasing radius from `0.0` to `1.697122669820252e+24` cm.
- Confirmed the raw restored file is ignored by the repo's `env/` rule and is
  not part of the committed asset bundle.
- Rerendered the C-LO particles config with real assets:

```bash
uv run python scripts/science/render_three_case_configs.py \
  --case C-LO \
  --variant particles \
  --grid stewart_stretched_250 \
  --duration-myr 50 \
  --snapshot-interval-myr 1 \
  --dbl-h5-interval-myr 5 \
  --particle-interval-myr 0.01 \
  --particles-per-injection 32 \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --require-assets \
  --check-local-assets \
  --output docs/science/assets/stewart_cluster_asset_restore_c_lo_preflight_2026-07-03/rendered_c_lo_config \
  --force
```

- Removed the renderer-copied raw Stewart CSV from the committed render bundle.
- Staged compact config files, the verified Stewart CSV, and the preflight
  wrapper under
  `/u/bwbrook/codex_kunanyi/goal031_c_lo_asset_restore_preflight`.
- Verified remote SHA-256 values, remote wrapper syntax, manual wrapper
  validation, PLUTO and `jet-setup` path presence, `jet-setup/tools/setup-problem`,
  AGN modulefiles, and runtime module loading.

## Remote Notes

The first remote validation log included a broader
`/scratch/bwbrook/git/utas-agn/plutokore` check and reported it absent. That is
not a Goal 031 blocker because this preflight contract and the existing
production-wrapper pattern use PLUTO plus `jet-setup`.

The first runtime-module check also saw Kunanyi's default `gnu8` compiler
module conflict with `intel`. A rerun with `module purge` loaded
`intel/18.0.1.163`, `impi/2018.1.163`, `hdf5/1.12.1p`, and `zfp/0.5.5`
cleanly and resolved `mpicc`/`mpirun`.

No `qsub` or PBS submission was attempted.

## Decision

Decision label:
`C_LO_ASSET_RESTORED_PREFLIGHT_CLEAN_EXECUTION_PACKET_READY`.

The Goal 030 missing-local-Stewart-asset blocker is resolved. Local
asset-backed config rendering and bounded remote read-only preflight are clean.
The next goal can be a Barry-authorized bounded C-LO execution packet, but
Goal 031 itself does not authorize compute.

## Validation

Validation passed:

- `uv run python -m json.tool docs/science/assets/stewart_cluster_asset_restore_c_lo_preflight_2026-07-03/stewart_cluster_asset_restore_c_lo_preflight_metadata.json`
- CSV parse/expected-column/nonempty checks for the seven new Goal 031 CSV
  assets.
- Restored asset validation recorded in `asset_validation.csv`.
- Renderer command with `--require-assets --check-local-assets` passed.
- `bash -n scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs`
- `uv run pytest tests/test_c_lo_config_asset_preflight_contract.py -q`
  (`3 passed`).
- `git diff --check`
- Targeted unresolved-marker scan over the Goal 031 science note, exchange log,
  Goal log, and current status returned no hits.
- Confirmed no raw `tabulated_cosmo_002003.csv` exists under the committed Goal
  031 asset bundle; the restored raw file is ignored under `env/`.

## Final Status

Status: `complete_asset_restored_preflight_clean`.

Out-of-scope work did not occur.
