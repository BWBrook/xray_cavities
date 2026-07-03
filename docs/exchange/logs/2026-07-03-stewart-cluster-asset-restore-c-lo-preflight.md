# 2026-07-03 - Stewart Cluster Asset Restore And C-LO Preflight

Goal 031 restored the ignored Stewart cluster `002_003` asset and reran the
C-LO config/asset preflight.

## Result

Status: `complete_asset_restored_preflight_clean`.

Decision label:
`C_LO_ASSET_RESTORED_PREFLIGHT_CLEAN_EXECUTION_PACKET_READY`.

The local missing-asset blocker from Goal 030 is resolved. The restored file:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002003.csv
```

was fetched from:

```text
/u/bwbrook/codex_kunanyi/stage_2026-05-08/kunanyi_gate/cluster_002003/tabulated_cosmo_002003.csv
```

and validated as SHA-256
`30cf7aa1ece95c1a0d0d9ea23d6baae2e16469f52c96a08b9a18a681527383aa`,
`608000` bytes, `4000` rows, `6` columns, with strictly increasing radius.
The raw CSV remains ignored under `env/` and was not added to Git.

## Config And Remote Preflight

`C-LO` was rerendered with `--require-assets --check-local-assets` using
variant `particles`, grid `stewart_stretched_250`, and the restored cluster
tabulated path. The config audit passed for `JET_PWR = 1e+43`, `JET_SPD = 0.1`,
and 50 Myr as `15330.06968940` PLUTO code-time units.

Bounded Kunanyi preflight staged only compact config files, the verified
Stewart CSV, and the read-only preflight wrapper under:

```text
/u/bwbrook/codex_kunanyi/goal031_c_lo_asset_restore_preflight
```

Remote SHA checks, remote wrapper syntax, manual wrapper validation, PLUTO and
`jet-setup` path checks, AGN modulefile checks, and runtime module loading
passed. No `qsub` or PBS submission was attempted.

## Follow-Up

Recommended next branch:
`barry_authorized_bounded_c_lo_execution_packet`.

That future packet should submit at most one bounded C-LO job only after Barry
explicitly authorizes compute, then wake and stop once the job is queued or
running. It should preserve inherited C-HI contracts, module-purge hygiene, and
the no-overwrite/stable-archive rules.

## Boundary

No PLUTO/XRAiSE/PRAiSE/radio/cavity/source-age/endpoint/C-LO/G-LO science
compute, PBS submission, finalizer, science-output retrieval, polling loop,
scientific-default change, environment substitution, commit, push, cleanup,
Stas/Patrick contact, `agent_comms` edit, or accepted-asset overwrite occurred.
