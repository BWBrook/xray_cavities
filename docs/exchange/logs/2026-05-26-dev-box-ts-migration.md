# 2026-05-26 Dev-Box-TS Migration Checkpoint

Machine used: MacBook Neo
Target checked: Mac Mini via `ssh dev-box-ts`

## Summary

The Mac Mini is ready to act as the always-on macOS development/control host for
`xray_cavities`. The project repo was fast-forwarded, the local `uv`
environment was built, the UTAS AGN GitLab repos were verified, canonical
`upstream` remotes were added where needed, and the TPAC password env file was
installed without printing its contents.

## Verified Paths

```text
/Users/bwbrook/papers/xray_cavities
/Users/bwbrook/git/utas-agn/pluto
/Users/bwbrook/git/utas-agn/jet-setup
/Users/bwbrook/git/utas-agn/plutokore
/Users/bwbrook/git/utas-agn/jet-setup.wiki
/Users/bwbrook/work/nectar
```

## Important Commits

```text
xray_cavities: aadf938 on main
nectar: cff9b89 on main
pluto: 2674fc3 on bwbrook/deep-server-bringup
jet-setup: e17ac8f on bwbrook/deep-server-bringup
plutokore: e80252c on bwbrook/deep-server-bringup
jet-setup.wiki: 14d5aa7 on master
```

## Validation

```text
ssh dev-box-ts: works
Tailscale peers: MacBook, Mac Mini, Nectar, utas-ubuntu/deep-server, WSL visible
uv sync --frozen: completed in xray_cavities
Python smoke: Python 3.12.13, h5py 3.16.0, pytest 9.0.3
plutokore editable dist: 1.20.2.dev92+ge80252cf3
import plutokore: completed successfully
kunanyi script syntax: bash -n passed
```

## Caveats

- The Mac Mini has `~/.config/tpac/kunanyi.env`, but still needs an active TPAC
  Open OnDemand jumpbox window before `kunanyi` SSH helpers can work.
- The ignored `env/` payloads are not present in the Mac Mini checkout.
- OpenStack/Nectar CLI control was not configured on the Mac Mini in this pass.
- Do not launch another 80-node C-HI full-grid continuation until Patrick,
  Stas, or TPAC resolves the OpenMPI/UCX transport question.

## New Handover

The detailed first-read document for the next Mac Mini agent is:

```text
docs/exchange/dev_box_ts_handover.md
```
