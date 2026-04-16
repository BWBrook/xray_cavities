# AGENTS.md

This file orients a new Codex agent arriving in `/home/bwbrook/papers/xray_cavities`.

## Purpose

This repo is not the main simulation source tree. It is the local project shell for:

- a repo-local `uv` Python environment
- UTAS AGN analysis and verification tooling
- docs/tooling notes for the current `deep-server` machine

The simulation source lives separately under:

- `/home/bwbrook/git/utas-agn/pluto`
- `/home/bwbrook/git/utas-agn/jet-setup`
- `/home/bwbrook/git/utas-agn/plutokore`
- `/home/bwbrook/git/utas-agn/jet-setup.wiki`

Treat this repo as the stable launch point for Python, notebook, verification, and documentation workflows that operate on those checkouts.

## Git remotes

The UTAS AGN code repos are now set up in a fork-based workflow.

For these repos:

- `/home/bwbrook/git/utas-agn/pluto`
- `/home/bwbrook/git/utas-agn/jet-setup`
- `/home/bwbrook/git/utas-agn/plutokore`

the remotes are intentionally arranged as:

- `origin` = Barry's personal GitLab fork under `BWBrook`
- `upstream` = the canonical `utas-agn` GitLab repo

This means:

- use `git fetch upstream` to bring in lab changes
- use `git push origin ...` or plain `git push` to publish Barry's work safely to the fork
- do not push directly to the canonical lab repos unless the user explicitly decides to do that

`jet-setup.wiki` has not been forked and still points at the canonical repo. Treat it as read-only unless the user explicitly asks to change that arrangement.

## First Reads

Start here, in order:

1. [README.md](/home/bwbrook/papers/xray_cavities/README.md)
2. [docs/deep_server_setup.md](/home/bwbrook/papers/xray_cavities/docs/deep_server_setup.md)
3. `/home/bwbrook/git/utas-agn/jet-setup/README.md`
4. `/home/bwbrook/git/utas-agn/plutokore/README.md`

## Environment

This repo owns a local `uv` environment in `.venv`.

Use it like this:

```bash
cd /home/bwbrook/papers/xray_cavities
uv sync
uv run python
uv run ipython
uv run jupyter lab
```

Important details:

- Python is pinned to `3.12`.
- `plutokore` is an editable local dependency sourced from `/home/bwbrook/git/utas-agn/plutokore`.
- `scipy` is pinned to `<1.14` because `jet-setup/test/environment/verify-environment-stability.py` still imports `scipy.integrate.trapz`.
- `sphinx` is pinned to `<7` because the current `jet-setup` docs theme is not compatible with newer Sphinx.
- `doxygen` is installed repo-locally under `.doxygen/` and linked into `.venv/bin`.

Do not commit `.venv/` or `.doxygen/`.

## What Is Ready

As of `2026-04-16`, this machine is ready for:

- building local `jet-setup` simulation cases
- running representative serial PLUTO cases
- running representative MPI cases with Open MPI
- running the UTAS AGN Python verification tooling
- building the `jet-setup` Sphinx + Doxygen docs

The detailed evidence is recorded in [docs/deep_server_setup.md](/home/bwbrook/papers/xray_cavities/docs/deep_server_setup.md).

## Known UTAS AGN State

Current branches:

- `pluto`: `4.4.0-localchanges`
- `jet-setup`: `pluto-4.4`
- `plutokore`: `master`
- `jet-setup.wiki`: `master`

Important caution:

- `jet-setup` currently contains local uncommitted fixes and test edits on this machine.
- Those changes were made to get the local smoke matrix green and are documented in `docs/deep_server_setup.md`.
- Do not casually discard them.
- The intended home for those changes is Barry's fork, not the canonical lab repo.

## Common Commands

Run a `jet-setup` test through the project environment:

```bash
cd /home/bwbrook/git/utas-agn/jet-setup/test
PLUTO_DIR=/home/bwbrook/git/utas-agn/pluto \
uv run --project /home/bwbrook/papers/xray_cavities \
python run-tests.py king/test-2d-hd-gp-sph -m Linux.gcc.defs
```

Build the `jet-setup` docs:

```bash
cd /home/bwbrook/git/utas-agn/jet-setup/docs
uv run --project /home/bwbrook/papers/xray_cavities \
sphinx-build -b html source _build/html
```

Run the environment stability checker directly:

```bash
uv run --project /home/bwbrook/papers/xray_cavities python - <<'PY'
import importlib.util
from pathlib import Path
spec = importlib.util.spec_from_file_location(
    'verify',
    '/home/bwbrook/git/utas-agn/jet-setup/test/environment/verify-environment-stability.py',
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.verify(Path('/home/bwbrook/git/utas-agn/jet-setup/test/environment/king/test'))
PY
```

## Parallel Runs

PLUTO parallelism here is MPI-based, not thread-count based.

- Build with `Linux.mpicc.defs`.
- Run with `mpiexec -n N ./pluto`.
- Set `OMP_NUM_THREADS=1` unless you intentionally want hybrid MPI/thread behaviour.

For the `king/test-3d-hd-gp-cart` case, `8` MPI ranks worked cleanly and gave a large speedup over serial on this host.

## Working Norms

- Use `uv run --project /home/bwbrook/papers/xray_cavities ...` for Python-facing work on UTAS AGN.
- Keep machine-state notes in `docs/deep_server_setup.md` up to date when you materially change the environment or validation status.
- Prefer committing changes in `xray_cavities` separately from edits made inside `/home/bwbrook/git/utas-agn`, unless the user explicitly asks for a broader batch.
- If a workflow fails, separate environment issues from repo-content issues. At this point most remaining problems are repo-content issues, not missing Ubuntu tooling.

## Known Remaining Risks

- `jet-setup/test/environment/tabulated/test-2d-hd-ga-sph` still fails its own stability thresholds.
- `jet-setup/test/environment/external/test-3d-rhd-ga-cart` references a missing file, `spherical-r200-n3.grid.out`.
- The `jet-setup` test harness still defaults to serial execution; MPI runs currently need a manual build/run path.

If you need the latest validated status, treat [docs/deep_server_setup.md](/home/bwbrook/papers/xray_cavities/docs/deep_server_setup.md) as the source of truth.
