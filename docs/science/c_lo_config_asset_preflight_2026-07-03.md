# C-LO Config And Asset Preflight

Date: 2026-07-03

Status: `blocked_local_asset_missing_no_remote_preflight`

Decision label:
`C_LO_PREFLIGHT_BLOCKED_MISSING_LOCAL_STEWART_002003_ASSET`.

## Summary

Goal 030 was intended to prove whether the first comparison case, `C-LO`, is
ready for a later explicitly authorized execution packet. The local config
evidence is clear: `C-LO` remains the low-power Stewart cluster comparison
case, with `JET_PWR = 1e43 erg/s`, `JET_SPD = 0.1 c`, and the same
`002_003` Stewart cluster tabulated environment family as `C-HI`.

The local asset gate did not pass. The expected ignored asset path is absent:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002003.csv
```

The documented ignored recovery archive is also absent:

```text
env/environments.zip
```

Because the local Stewart asset could not be verified or restored from a
present repo-local surface, no remote preflight was attempted.

## Evidence

The packet used the Goal 029 comparison-readiness decision, the frozen
three-case spec, the three-case config renderer, the generic Kunanyi production
template, and the May Stewart asset inventory/logs. The May notes record that
`tabulated_cosmo_002003.csv` is the selected tabulated cluster environment for
both `C-HI` and `C-LO`, with `4000` rows, but that record is provenance rather
than a currently verifiable local file.

## Config Audit

A placeholder C-LO render is included only as a static audit surface:

```text
docs/science/assets/c_lo_config_asset_preflight_2026-07-03/rendered_c_lo_placeholder_config/
```

It is not launch-ready. It was rendered without `--require-assets` because the
Stewart CSV is absent. The audit confirms the intended `C-LO` constants and
unit convention, but the missing environment file remains a hard preflight
blocker.

## Wrapper Contract

Goal 030 adds a small read-only PBS preflight contract:

```text
scripts/kunanyi/c_lo_config_asset_preflight_contract.pbs
```

It is not a production wrapper. If staged in a later authorized packet, it
checks the staged C-LO config files, parses `render_validation.json`, verifies
the expected C-LO constants, and checks the staged `tabulated_cosmo_002003.csv`
row count and SHA-256. It does not submit jobs, build PLUTO, run PLUTO, run
XRAiSE, produce products, or archive science outputs.

## Remote Preflight

Remote preflight was deliberately not attempted. The Goal 030 packet required
remote preflight only after the local gate passed. It did not pass.

## Recommendation

The next goal should restore the ignored Stewart cluster asset surface locally
from a trusted source, then rerun this C-LO config/asset preflight:

```text
env/extracted/environments/tabulated/tabulated_cosmo_002003.csv
```

After that file is visible and verifies against the documented `4000`-row
Stewart cluster profile, rerender `C-LO` with `--require-assets` and
`--check-local-assets`, then perform the bounded read-only Kunanyi source,
module, asset, hash, and wrapper-syntax preflight. C-LO production compute
should remain blocked until a later explicit Barry-authorized execution packet.

## Boundaries

No remote commands, Open OnDemand, SSH/SCP, `qstat`, Kunanyi staging, PBS jobs,
finalizers, retrieval, polling, PLUTO, XRAiSE, PRAiSE, radio, cavity
extraction, source-age products, endpoint products, `C-LO`/`G-LO` processing,
comparison-case compute, broad sweeps, scientific-default changes, commits,
pushes, cleanup, Stas/Patrick contact, `agent_comms` edits, or accepted-asset
overwrites occurred.
