# Exchange Hub

This directory is the cross-machine handover system for UTAS AGN work.

Its job is to let a fresh agent on WSL, `deep-server`, or the MacBook via
`nectar-vm` pick up quickly without depending on chat history.

## Canonical locations

The same repo-relative path should exist on all machines:

- WSL: `/home/bwbrook/papers/xray_cavities/docs/exchange`
- `deep-server`: `/home/bwbrook/papers/xray_cavities/docs/exchange`
- `nectar-vm`: `/home/ubuntu/papers/xray_cavities/docs/exchange`

For MacBook continuity, treat the Nectar path as the most reliable shared entry
point, because the MacBook can usually reach `nectar-vm` even when it cannot
reach `deep-server`.

## First-read rule for a fresh agent

Before doing any real work, read these in order:

1. `AGENTS.md`
2. `docs/exchange/README.md`
3. `docs/exchange/current_status.md`
4. the newest relevant note under `docs/exchange/logs/`
5. machine-specific notes if needed:
   - `docs/deep_server_setup.md`
   - `docs/nectar_vm_setup.md`

## Pull-first rule

Do not trust exchange notes until this repo has been refreshed on the machine in
front of you.

Use:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

This matters because the repo may lag differently on WSL, `deep-server`, and
`nectar-vm`.

## File roles

- `current_status.md`
  - the living one-page snapshot of where the project stands now
  - update this when the practical state changes
- `logs/*.md`
  - append-only dated handover notes
  - use one note per meaningful session or checkpoint
- `templates/handover-note-template.md`
  - scaffold for a new handover note

## Minimum handover protocol

When finishing a session that materially changes project state:

1. refresh `current_status.md`
2. add a new dated note under `logs/`
3. commit and push the updated handover docs in `xray_cavities`
4. pull `xray_cavities` on the other machine before resuming there

## What to record

Keep it practical and brief. A good handover note should include:

- which machine was used
- which repo commits matter
- which remote workspaces were touched
- what finished successfully
- what is still in progress
- the exact next recommended step
- any sync caveats or blockers

## Helper

Create a new handover note skeleton with:

```bash
cd /home/bwbrook/papers/xray_cavities
./scripts/new_exchange_note.sh short-slug
```

That will create a timestamped markdown note under `docs/exchange/logs/`.
