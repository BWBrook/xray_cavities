# Remote Run Sync Helpers

This directory contains the WSL-side helpers for mirroring portable UTAS AGN run directories between compute hosts.

## Host roles

The intended three-machine model is:

- WSL laptop = orchestration hub
- `deep-server` = campus-only trusted execution node
- `nectar-vm` = mobile-accessible secondary execution node

## Sync model

Use these rules consistently:

- source code, docs, and workflow scripts sync through Git
- run directories and outputs sync through `rsync`
- each run has one authoritative host at a time
- mirrored copies are read-only operationally unless explicitly promoted
- live jobs are not migrated between hosts

## Standard run root

Portable runs should live under:

- `/home/<user>/work/utas-agn-runs/<project>/<run_id>/`

with this internal layout:

- `inputs/`
- `outputs/`
- `logs/`
- `plots/`
- `run_manifest.yaml`

A template manifest is provided in this directory.

## Local mirror roots

These helpers use the following WSL-side cache roots:

- `/home/bwbrook/work/remote-mirrors/deep-server`
- `/home/bwbrook/work/remote-mirrors/nectar-vm`

This makes WSL the canonical sync hub between the two remote hosts.

## Scripts

- `pull_run_from_deep_server.sh <run_id>`
  Find a unique run under `deep-server`, then mirror it into the WSL cache.
- `push_run_to_nectar.sh <run_id>`
  Push a mirrored run from the WSL cache onto `nectar-vm`.
- `sync_run_deep_to_nectar.sh <run_id>`
  Pull from `deep-server`, push to `nectar-vm`, then update the mirrored manifest metadata after a successful transfer.

## Important note

These scripts assume future science-facing runs follow the standard run layout. They do not try to retrofit older onboarding workspaces automatically.
