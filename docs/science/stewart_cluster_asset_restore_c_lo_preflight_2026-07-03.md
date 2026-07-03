# Stewart Cluster Asset Restore And C-LO Preflight

Date: 2026-07-03

Status: `complete_asset_restored_preflight_clean`

Decision label:
`C_LO_ASSET_RESTORED_PREFLIGHT_CLEAN_EXECUTION_PACKET_READY`.

## Summary

Goal 031 resolves the Goal 030 operational blocker. The missing ignored
Stewart cluster `002_003` tabulated environment file was restored from a
trusted already-used Kunanyi source:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/cluster_002003/tabulated_cosmo_002003.csv
```

The restored local file is:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002003.csv
```

It remains ignored under `env/` and is not part of the committed review bundle.
The committed package records checksum, size, row count, radius range, and
source provenance instead.

## Asset Result

The restored table validates as the intended Stewart `002_003` tabulated
cluster asset:

- SHA-256:
  `30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`.
- Size: `608000` bytes.
- Rows: `4000`.
- Columns: `6`.
- Radius is strictly increasing from `0.0` to
  `1.697122669820252e+24` cm.

All five authorized exact Kunanyi candidates matched the same checksum and
row-count metadata, so the restore is provenance-consistent with the accepted
C-HI/Stewart asset surface rather than an environment substitution.

## Asset-Backed C-LO Config

The C-LO particles config was rerendered with real assets:

```text
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

The render passed and records `environment.status = provided`. Static config
checks confirm `C-LO`, Stewart cluster `002_003`, `JET_PWR = 1e+43 erg/s`,
`JET_SPD = 0.1 c`, and 50 Myr as `15330.06968940` PLUTO code-time units.
The renderer's copied raw table was removed from the committed render bundle;
the raw file remains only under ignored `env/` locally and was staged remotely
only for read-only preflight.

## Remote Read-Only Preflight

Bounded Kunanyi preflight was run only after the local asset-backed gate
passed. No PBS job was submitted.

Remote stage:

```text
/u/bwbrook/codex_kunanyi/goal031_c_lo_asset_restore_preflight
```

The stage included compact rendered config files, the verified Stewart CSV,
and `scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs`. Remote
preflight verified:

- staged SHA-256 values matched local values;
- remote `bash -n` for the wrapper passed;
- manual wrapper validation printed `C_LO_PREFLIGHT_OK=1`;
- `/scratch/bwbrook/git/utas-agn/pluto` exists;
- `/scratch/bwbrook/git/utas-agn/jet-setup` exists;
- `jet-setup/tools/setup-problem` exists;
- `/ds/projects/agn/modulefiles` exists;
- after `module purge`, `intel`, `impi`, `hdf5/1.12.1p`, and `zfp/0.5.5`
  load cleanly and `mpicc`/`mpirun` resolve.

An initial broader source check included
`/scratch/bwbrook/git/utas-agn/plutokore` and reported it absent. That is not
a Goal 031 blocker because the C-LO config/preflight contract and the existing
production-wrapper pattern require PLUTO plus `jet-setup` for this gate. The
absence should be revisited only if a future execution implementation actually
requires remote `plutokore`.

## Recommendation

The next goal can be a Barry-authorized bounded C-LO execution packet. It
should use the restored Stewart `002_003` asset, the asset-backed C-LO config,
the inherited C-HI contracts, explicit module-purge hygiene, the stable archive
contract, and the existing PBS stop rule: submit at most one bounded job,
verify queued/running, wake X-ray Cavities, and stop.

This package does not authorize C-LO compute by itself.

## Boundaries

No PBS job, PLUTO run, XRAiSE run, PRAiSE run, radio or cavity extraction,
source-age product, endpoint product, C-LO/G-LO science compute, finalizer,
science-output retrieval, polling loop, scientific-default change,
environment substitution, commit, push, cleanup, Stas/Patrick contact,
`agent_comms` edit, or accepted-asset overwrite occurred.
