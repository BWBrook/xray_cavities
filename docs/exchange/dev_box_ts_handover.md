# Dev-Box-TS Handover

Last updated: 2026-05-26
Prepared from: MacBook Neo, `/Users/bwbrook/papers/xray_cavities`
Target agent: a fresh Codex thread running on `dev-box-ts`

This note is written as the thing I would want in front of me if I had just
landed on Barry's always-on Mac Mini and needed to continue the `xray_cavities`
work without relying on chat history.

## First Move On The Mac Mini

Start here:

```bash
cd /Users/bwbrook/papers/xray_cavities
git pull --ff-only
```

Then read, in order:

1. `AGENTS.md`
2. `docs/exchange/README.md`
3. `docs/exchange/dev_box_ts_handover.md`
4. `docs/exchange/current_status.md`
5. `docs/kunanyi_restart_framework.md`
6. `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`
7. the newest relevant file under `docs/exchange/logs/`

The Mac Mini is now a valid primary control/development host for this project,
but it is not the simulation target for heavy PLUTO work. Keep the machine
roles straight:

- Mac Mini: always-on macOS dev box, repo work, document rendering, local
  Python tooling, orchestration.
- MacBook Neo: portable dashboard and GUI fallback.
- `deep-server`: stable Tailscale relay and heavy single-host Linux target.
- Nectar: resizable VM for rehearsal and medium remote work.
- `kunanyi`: PBS-backed production target for multi-node PLUTO jobs.

## Verified Mac Mini State

Checked from the MacBook over `ssh dev-box-ts` on 2026-05-26.

Host baseline:

```text
SSH alias: dev-box-ts
hostname: Mac-mini.lan
user: bwbrook
OS: macOS 26.5, Darwin 25.5.0, arm64
model: Mac16,10
logical CPUs: 10
memory: 24 GiB
data volume: 460 GiB total, about 364 GiB available at check time
Codex CLI: /Users/bwbrook/.local/bin/codex, codex-cli 0.133.0
Quarto: /Users/bwbrook/Applications/quarto/bin/quarto, 1.9.37
```

Tailscale status from the Mini showed these peers:

```text
barrys-mac-mini  <tailscale-ip>
barrys-macbook   <tailscale-ip>
nectar-vm        <tailscale-ip>
utas-ubuntu      <tailscale-ip>
wsl-laptop       <tailscale-ip>
```

The central control-plane repo is also present and was fast-forwarded:

```text
/Users/bwbrook/work/nectar
branch: main
HEAD: cff9b89
status: clean, even with origin/main
```

Use that repo for reusable machine runbooks, especially:

- `/Users/bwbrook/work/nectar/docs/machines/mac-mini-dev-box.md`
- `/Users/bwbrook/work/nectar/docs/workflows/codex-remote-connections.md`
- `/Users/bwbrook/work/nectar/docs/workflows/tailscale-connectivity.md`

## `xray_cavities` Checkout

The Mac Mini checkout is:

```text
/Users/bwbrook/papers/xray_cavities
remote: git@github.com:BWBrook/xray_cavities.git
branch: main
HEAD after migration pass: aadf938
status: clean, even with origin/main
```

The checkout was behind by three commits at first contact and was
fast-forwarded on 2026-05-26. The repo-local Python environment was then built:

```bash
cd /Users/bwbrook/papers/xray_cavities
uv sync --frozen
```

Validation completed:

```text
Python in .venv: 3.12.13
h5py import: 3.16.0
pytest: 9.0.3
plutokore editable dist: 1.20.2.dev92+ge80252cf3
import plutokore: completed successfully after warmup
kunanyi shell/PBS script syntax: bash -n passed
```

Ignored local state after setup:

```text
.venv/
```

No large ignored `env/` directory was present in the Mac Mini
`xray_cavities` checkout at check time. That is acceptable for the current
handover because the active full-grid run state lives on `kunanyi` scratch, not
locally. If a future task needs the huge Stewart environment archives, reacquire
or copy them deliberately; do not add them to Git.

## UTAS AGN GitLab Repos

The relevant GitLab checkouts are present under:

```text
/Users/bwbrook/git/utas-agn
```

Current state after the migration pass:

```text
/Users/bwbrook/git/utas-agn/pluto
  branch: bwbrook/deep-server-bringup
  HEAD: 2674fc3
  origin: git@gitlab.com:BWBrook/pluto.git
  upstream: git@gitlab.com:utas-agn/pluto.git

/Users/bwbrook/git/utas-agn/jet-setup
  branch: bwbrook/deep-server-bringup
  HEAD: e17ac8f
  origin: git@gitlab.com:BWBrook/jet-setup.git
  upstream: git@gitlab.com:utas-agn/jet-setup.git

/Users/bwbrook/git/utas-agn/plutokore
  branch: bwbrook/deep-server-bringup
  HEAD: e80252c
  origin: git@gitlab.com:BWBrook/plutokore.git
  upstream: git@gitlab.com:utas-agn/plutokore.git

/Users/bwbrook/git/utas-agn/jet-setup.wiki
  branch: master
  HEAD: 14d5aa7
  origin: git@gitlab.com:utas-agn/jet-setup.wiki.git
```

The three fork-backed repos had `origin` already set to Barry's GitLab forks.
During this pass, the canonical `upstream` remotes were added and fetched on
the Mac Mini for `pluto`, `jet-setup`, and `plutokore`. Keep using the fork
workflow:

```bash
git fetch upstream
git push origin <branch>
```

Do not push to the canonical `utas-agn` repos unless Barry explicitly asks for
that.

## Secrets And Remote Access

The `kunanyi` helper scripts read:

```text
~/.config/tpac/kunanyi.env
```

This file was copied from the MacBook to the Mac Mini on 2026-05-26 without
printing its contents and locked down to mode `600`.

Important details:

- `TPAC_USER` and `TPAC_PASSWORD` should be defined in that file.
- Never commit it.
- The TPAC Open OnDemand jumpbox window is still required. The helper
  `scripts/kunanyi/enable_jumpbox_ssh_safari.sh` opens the portal endpoint in
  Safari, but it depends on Safari already being logged in to the UTAS/AAF
  session on the machine doing the launch.
- If a `run_on_kunanyi.sh` command says `MFA check failed`, refresh the TPAC
  portal jumpbox window and retry.

The Mac Mini SSH config includes these relevant outbound aliases:

```text
tpac-jumpbox
kunanyi
tpac-jumpbox-via-nectar
kunanyi-via-nectar
utas-ubuntu / deep-server-ts
tpac-jumpbox-via-deep
kunanyi-via-deep
nectar-vm / nectar-codex
nectar-vm-ts / nectar-codex-ts
```

For home-network work, prefer the stable Tailscale/deep route:

```bash
TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep
TPAC_SCP_HOST=kunanyi-via-deep
```

The current `xray_cavities` helper defaults already use those values.

OpenStack/Nectar note: at check time, the Mac Mini did not have a local
OpenStack secret env file or `openstack` CLI on PATH. That is not a blocker for
the current `kunanyi` wait state. If the Mini needs to resize Nectar later,
work from `/Users/bwbrook/work/nectar` and set up the OpenStack client and
secrets there rather than improvising inside `xray_cavities`.

## Current Science/Operations State

The science setup is not blocked by local Mac Mini readiness. The outstanding
blocker is the large-node MPI transport question on `kunanyi`.

Do not submit another 80-node full-grid continuation until Patrick, Stas, or
TPAC provides a sensible answer for the OpenMPI/UCX transport path.

What happened:

- `692369.kunanyi-ohpc` initialized, wrote initial HDF5 output, then failed
  with UCX/OpenMPI `Fatal: UD endpoint ... unhandled timeout error`.
- The first fatal messages clustered around nodes including `n161`, `n163`,
  and `n164`.
- `692504.kunanyi-ohpc` retried from `data.0000.dbl.h5` with
  `OMPI_MCA_pml=ob1` and `OMPI_MCA_btl=self,vader,tcp`.
- That avoided the UCX UD timeout signature but made no useful progress in
  eight hours and was killed at PBS walltime.

Interpretation:

- The PLUTO science configuration appears mechanically sound.
- Plain OB1/TCP is diagnostic evidence, not a viable production fallback.
- The unresolved question is which performant MPI fabric/settings should be
  used for an 80-node PLUTO/HDF5 run on `kunanyi`, or whether suspect nodes
  should be excluded.

The restart framework is now committed and should be the default operating
pattern:

- `docs/kunanyi_restart_framework.md`
- `scripts/kunanyi/inspect_c_hi_fullgrid_restart_state.sh`
- `scripts/kunanyi/c_hi_fullgrid_continue.pbs`
- `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh`
- `scripts/kunanyi/jet_setup_production_template.pbs`

When Barry forwards a PBS email, the first action is inspection, not a blind
resubmit:

```bash
cd /Users/bwbrook/papers/xray_cavities
scripts/kunanyi/inspect_c_hi_fullgrid_restart_state.sh <jobid>
```

Only after the transport issue is resolved should a continuation be staged:

```bash
scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh
```

Use `MIN_RESTART_INDEX=1` if you want to refuse restarting from only the
initial `data.0000.dbl.h5` checkpoint.

## Agent-Comms

Barry is now experimenting with multiple Codex agents, including Stas' and
Patrick's agents, coordinating through repo files. The important directory is:

```text
agent_comms/
```

For this specific blocker, read:

```text
agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md
```

If you need input from Stas-agent or Patrick-agent, write a clear markdown
question there or in a new thread, commit and push it, then Barry can point the
human supervisors at the update. Keep questions scarce and concrete; Patrick's
and Stas' attention is finite.

## Working Style For The Dev-Box Agent

Barry prefers agents that execute after the scope is clear. Keep updates short,
but do not be timid once the path is obvious.

Practical norms:

- Pull first on arrival.
- Keep `docs/exchange/current_status.md` current when the real state changes.
- Add dated notes under `docs/exchange/logs/` for meaningful handoffs.
- Commit and push handoff updates before switching machines.
- Do not run heavy simulations on the Mac Mini.
- Do not treat local ignored payloads as authoritative unless the handoff says
  they were deliberately copied.
- Use the repo scripts rather than inventing one-off SSH incantations.
- Separate inspectable machine facts from questions that must go to
  Stas/Patrick/TPAC.

The next likely useful action from the Mini is either:

1. wait for Patrick's MPI/UCX transport guidance, then encode it into a small
   transport ladder or continuation wrapper; or
2. use the Mini for non-HPC analysis/document work while the transport question
   is pending.
