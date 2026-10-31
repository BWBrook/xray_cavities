# xray_cavities

Local project shell for UTAS AGN analysis, verification, and documentation workflows on `deep-server`.

This repo is intentionally lightweight. The simulation source lives in the separate GitLab checkout under `/home/bwbrook/git/utas-agn`; this repo provides the reproducible Python/docs environment and the handoff notes needed to work against that source tree confidently.

New project agents should start with
[docs/exchange/current_status.md](docs/exchange/current_status.md). The former
`HANDOFF.md` was archived on 2026-10-31 under `docs/exchange/archive/`.

## What lives here

- a repo-local `uv` environment in `.venv`
- a repo-local `doxygen` install in `.doxygen`
- the Python analysis stack used by `plutokore` and `jet-setup` verification scripts
- onboarding and machine-state documentation for the current UTAS AGN setup
- science-run specifications and launch scaffolding for the three-case
  X-ray/radio/truth comparison suite

## Quick start

Create or refresh the environment:

```bash
cd /home/bwbrook/papers/xray_cavities
uv sync
```

Use the environment:

```bash
uv run python
uv run ipython
uv run jupyter lab
```

## Manuscript

The PASA manuscript sources and build configuration live in this repository.
The external `makedoc` engine is invoked through repo-local targets without
copying sources out of `xray_cavities`:

```bash
make manuscript-validate
make manuscript-draft
make manuscript-submission
make manuscript-check
```

See [manuscript/README.md](manuscript/README.md) for the source layout,
authorship gate, PASA conventions, and output locations.

Check docs tooling:

```bash
uv run doxygen --version
uv run sphinx-build --version
```

## Relationship to UTAS AGN

This environment is wired to the local UTAS AGN clones at:

- `/home/bwbrook/git/utas-agn/pluto`
- `/home/bwbrook/git/utas-agn/jet-setup`
- `/home/bwbrook/git/utas-agn/plutokore`
- `/home/bwbrook/git/utas-agn/jet-setup.wiki`

`plutokore` is installed as an editable local dependency from:

```text
/home/bwbrook/git/utas-agn/plutokore
```

That means edits in the `plutokore` checkout are visible immediately inside this environment.

## Common commands

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

## Important pins

Two version constraints here are deliberate:

- `scipy<1.14`
  - needed because `verify-environment-stability.py` still imports `scipy.integrate.trapz`
- `sphinx<7`
  - needed because the current `jet-setup` docs theme is not compatible with newer Sphinx releases

## Docs

- [AGENTS.md](/home/bwbrook/papers/xray_cavities/AGENTS.md): repo-local instructions for the next agent
- [docs/exchange/README.md](/home/bwbrook/papers/xray_cavities/docs/exchange/README.md): cross-machine handover system for WSL, `deep-server`, and `nectar-vm`
- [docs/exchange/current_status.md](/home/bwbrook/papers/xray_cavities/docs/exchange/current_status.md): living project status for the next agent to read first
- [docs/deep_server_setup.md](/home/bwbrook/papers/xray_cavities/docs/deep_server_setup.md): detailed machine state, toolchain notes, smoke-test results, and MPI validation status
- [docs/nectar_vm_setup.md](/home/bwbrook/papers/xray_cavities/docs/nectar_vm_setup.md): Nectar VM clone status and production HDF5 validation
- [docs/science/three_case_spec.md](/home/bwbrook/papers/xray_cavities/docs/science/three_case_spec.md): frozen `C-HI`, `C-LO`, `G-LO` science-run spec
- [docs/science/asset_inventory_2026-05-02.md](/home/bwbrook/papers/xray_cavities/docs/science/asset_inventory_2026-05-02.md): current Stewart/GRAiLE asset inventory and blockers
