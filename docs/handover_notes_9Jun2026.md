# Handover Notes - 9 June 2026

This note is for a fresh Codex agent picking up the UTAS AGN / X-ray cavities
project on Barry's Mac mini after the 9 June 2026 thread handover.

## First Orientation

Start from the local Mac mini checkout:

```bash
cd /Users/bwbrook/papers/xray_cavities
git fetch --prune origin
git pull --ff-only
git status --short --branch
```

Then read, in this order:

1. `/Users/bwbrook/.codex/AGENTS.md`
2. `AGENTS.md`
3. `README.md`
4. `docs/exchange/README.md`
5. `docs/exchange/current_status.md`
6. `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md`
7. `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
8. `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
9. `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`

This repo is the project shell and analysis/documentation launch point. The
main simulation source trees are separate UTAS AGN checkouts, locally under
`/Users/bwbrook/git/utas-agn/` on the Mac mini and under
`/home/bwbrook/git/utas-agn/` on Linux/HPC hosts:

- `pluto`
- `jet-setup`
- `plutokore`
- `jet-setup.wiki`

Treat `origin` for the fork-backed UTAS AGN repos as Barry's fork and
`upstream` as the canonical lab repo. Do not push to canonical UTAS AGN repos
unless Barry explicitly asks for that.

## Current State

The project is in a solid production/science stage.

- The first full-grid C-HI production run has reached the configured 50 Myr
  endpoint on Kunanyi.
- A 64-node Kunanyi AGN Intel/IMPI stack is now the working production default.
- An 80-node restart remains unreliable and should be treated as a TPAC/HDF5/MPI
  scale issue rather than the default path.
- Dense all-history particle HDF5 caching has been ruled out as infeasible for
  routine analysis.
- Endpoint particle summaries, sparse particle-window products, and a first
  sparse radio bridge have all completed successfully and are documented.
- Raw production files stay on Kunanyi. Pull compact summaries, plots, tables,
  JSON manifests, and archives to this repo only.

At the time this handover was written, local `main` was clean and at:

```text
6d08681 Add C-HI sparse radio bridge
```

## Recent Production History

### 64-node production endpoint

The major C-HI restart run, `c_hi_r9_p64`, completed successfully:

```text
PBS job:     697298.kunanyi-ohpc
Exit status: 0
Nodes/ranks: 64 nodes / 1792 ranks
Walltime:    07:49:58
```

Important endpoint files on Kunanyi:

```text
/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles
```

Final outputs:

- `data.0011.dbl.h5` - about 67 GB
- `data.0051.flt.h5` - about 44.9 GB
- `particles.5000.dbl` - about 23.6 MB
- Endpoint time: 50.00000000000777 Myr
- Endpoint step: 49253
- Endpoint particle count: 196732

Relevant docs:

- `docs/exchange/logs/2026-06-07-c-hi-fullgrid-agn-impi-r9-prod64-complete.md`
- `docs/exchange/logs/2026-06-07-c-hi-fullgrid-agn-impi-r9-prod64-integrity.md`
- `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`

### Node scaling ladder

The restart ladder from output 9 established the current production rule:

- 8 nodes: green
- 16 nodes: green
- 32 nodes: green
- 48 nodes: green
- 64 nodes: green
- 80 nodes: fails/stalls at about 2 hours with `Exit_status=271`

Use 64 nodes as the production sweet spot for this stack unless the task is
explicitly to investigate TPAC's 80-node restart behaviour.

### Particle HDF5 feasibility preflight

The dense all-history particle HDF5 cache was tested and rejected:

- Raw dense matrix estimate: about 109.95 GiB
- Conservative peak estimate: about 1099.55 GiB

Do not submit a dense all-history particle HDF5 cache job. The viable route is
sparse selected-particle analysis.

Relevant docs:

- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-hdf5-preflight-submitted.md`
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-hdf5-preflight-complete.md`

### Endpoint particle summary

The endpoint particle summary completed successfully:

```text
PBS job:     697643.kunanyi-ohpc
Exit status: 0
Walltime:    00:00:39
Archive SHA: a25a805858a438f56369fe4d3690c31bdd358efb0082f73c3d5e51b0633e35e1
```

Endpoint metrics:

- Particles: 196732
- Negative-z particles: 97451
- Positive-z particles: 99281
- Time: 50.00000000000777 Myr
- Step: 49253

Relevant docs:

- `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-endpoint-summary.md`

### Sparse particle window

The sparse selected-particle window completed successfully:

```text
PBS job:     697644.kunanyi-ohpc
Exit status: 0
Walltime:    00:01:04
Archive SHA: 9894f2dfc6cae5b76257b1c5b66b9438fdc25424d66d43ea68df1b2dbc80dc62
```

Configuration and outputs:

- Window: `particles.4950.dbl` to `particles.5000.dbl`
- Stride: 5
- Target endpoint file: `particles.5000.dbl`
- Selected particle IDs: 20000
- Target candidate particles: 195558
- Trajectory rows: 218909
- Side split: 9945 negative-z / 10055 positive-z

Relevant tooling:

- `scripts/science/pluto_particle_sparse_window.py`
- `scripts/kunanyi/c_hi_fullgrid_final_particle_sparse_window.pbs`
- `tests/test_pluto_particle_sparse_window.py`

Relevant docs:

- `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-sparse-window.md`
- `docs/superpowers/plans/2026-06-08-sparse-particle-window.md`

### Sparse radio bridge

The first sparse radio bridge completed successfully:

```text
PBS job:     697646.kunanyi-ohpc
Exit status: 0
Walltime:    00:00:05
Archive SHA: 2be0b61dcc7330727192123f9afd9c9a7138d26ea4f552ba62753cd72e24effe
```

Configuration and metrics:

- Target output: 5000
- Trajectory rows: 218909
- In-frame/selected particles: 20000
- Map shape: 460 x 90 pixels
- Pixel size: 1 kpc
- Positive pixels: 11829
- Mean pressure-history loss proxy: 0.8957169833296894
- Proxy map max: `1.2449378088138194e16` mJy/sr
- Bipolar proxy luminosity: `4.4514434941743747e27` W/Hz
- Current volume convention: 1.0 kpc^3 per particle

Important caveat: this is not final sparse PRAiSE. It is a bridge product using
a pressure-history loss proxy and unit per-particle volumes. It proves the data
path and gives a working target for the next science step.

Relevant tooling:

- `scripts/science/sparse_particle_radio_bridge.py`
- `scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs`
- `tests/test_sparse_particle_radio_bridge.py`

Relevant docs:

- `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md`
- `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge.md`

## Kunanyi Operating Notes

Use the AGN Intel/IMPI stack:

```bash
module use /ds/projects/agn/modulefiles
ml intel impi hdf5/1.12.1p zfp/0.5.5
export HDF5_USE_FILE_LOCKING=FALSE
```

For production C-HI restarts under this stack:

- Prefer 64 nodes / 1792 ranks.
- Use `HDF5_USE_FILE_LOCKING=FALSE`.
- Avoid 80-node restarts unless deliberately testing the TPAC issue.
- Keep production payloads on `/scratch/bwbrook/`.
- Keep compact staging, scripts, and downloaded archives under
  `/u/bwbrook/codex_kunanyi` where convenient.

Patrick's useful guidance from the restart debugging:

- Fresh 80-node starts can run correctly, but 80-node restarts are suspect.
- If a hang occurs while writing HDF5, set `HDF5_USE_FILE_LOCKING=FALSE`.
- Check restart HDF5 shape/datasets with `ls -lh` and `h5ls`.
- Confirm `HDF5_COMPRESSION` is disabled in `definitions_usr.h`; if enabled,
  logs should say HDF5 compression is enabled.
- When narrowing restart failures, add print logging in `hdf5_io.c` inside the
  `jet-setup/src` path.
- If filesystem behaviour remains suspect, test in `/u/bwbrook/` rather than
  `/scratch/bwbrook/`, copying only the final `.dbl.h5`, final particle file,
  and `*.out` files needed for restart.

## Chrome / Open OnDemand / Jumpbox Policy

Kunanyi is not on Tailscale. Direct SSH aliases such as `kunanyi-via-deep` or
`kunanyi-via-nectar` can hit the TPAC jumpbox authentication boundary:

```text
Permission denied (publickey,password)
```

When direct self-driving SSH is not available, use Chrome and the Kunanyi Open
OnDemand portal. Barry now keeps the portal in Chrome, not Safari, specifically
so Codex can use the Chrome plugin.

Useful portal URLs:

```text
https://<tpac-host>/pun/sys/dashboard
https://<tpac-host>/pun/sys/shell/ssh/<tpac-host>
```

If the dashboard exposes an "Enable Jumpbox SSH" control, Barry can manually
enable it. After that, re-test direct SSH from a fresh terminal before falling
back to browser automation.

If Chrome browser-control tools are not visible in a fresh Codex thread, expose
JavaScript execution via tool discovery and bootstrap the Chrome extension
bridge:

```javascript
const { setupBrowserRuntime } = await import("/Users/bwbrook/.codex/plugins/cache/openai-bundled/chrome/26.602.40724/scripts/browser-client.mjs");
await setupBrowserRuntime({ globals: globalThis });
globalThis.browser = await agent.browsers.get("extension");
await browser.user.openTabs();
```

Any non-error response from `browser.user.openTabs()` means the Chrome
extension/native-host bridge is working.

When using the Open OnDemand shell:

- Prefer a fresh shell tab over a long-lived or visually wedged hterm session.
- Avoid long clipboard pastes into the hterm terminal. They can concatenate
  commands before Return and corrupt staged payloads.
- For scripted input through Chrome/Playwright, target the shell iframe's
  terminal textarea and type short commands:

```javascript
const ta = shellTab.playwright.frameLocator("iframe").locator("textarea");
await ta.type("printf '__OK__\\n'\\n", { timeoutMs: 5000 });
```

- For multi-file staging, base64-stage small payloads, decode on Kunanyi, and
  verify with `sha256sum` before `qsub`.
- Use the Open OnDemand Files app to download compact archives from
  `/u/bwbrook/codex_kunanyi`. The file-browser URL shape is:

```text
https://<tpac-host>/pun/sys/dashboard/files/fs/u/bwbrook/codex_kunanyi
```

The Chrome bridge can occasionally leave tabs or finalization calls in a strange
state. That is usually a thread/tooling issue, not a Kunanyi issue. A fresh
Chrome tab, fresh shell, or fresh Codex thread is often the cleanest recovery.

## Local Development And Verification

This repo owns the local project environment. Use:

```bash
cd /Users/bwbrook/papers/xray_cavities
uv sync
uv run python
uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q
```

Do not commit `.venv/` or `.doxygen/`.

Keep changes in this repo separate from edits inside the UTAS AGN source
checkouts unless Barry explicitly asks for a broader batch.

When adding or changing science scripts:

- Add narrow unit tests where feasible.
- Add a dated science note under `docs/science/`.
- Add a dated exchange log under `docs/exchange/logs/`.
- Update `docs/exchange/current_status.md`.
- Commit and push so the next agent can fast-forward cleanly.

## Immediate Next Steps

1. Replace the sparse radio bridge's pressure-history proxy with a true sparse
   PRAiSE-compatible loss interface for selected particle IDs.

   Start by inspecting:

   - `/Users/bwbrook/git/utas-agn/plutokore/src/plutokore/radio/praise2.py`
   - `scripts/science/xraise_particle_radio_smoke.py`
   - `scripts/science/sparse_particle_radio_bridge.py`
   - `docs/science/c_hi_particle_radio_smoke_2026-05-10.md`

   The goal is to preserve the sparse selected-particle pathway while replacing
   the temporary pressure-history proxy with the real loss/radio emissivity
   pathway expected by PRAiSE/XRAiSE.

2. Replace the current unit per-particle volume convention with side-aware
   final-state volumes tied to the final grid/tracer state.

   The present sparse bridge uses:

   ```text
   1.0 kpc^3 per particle
   ```

   That is acceptable for proving the data path, but not for final science.
   Derive side volumes from the final C-HI HDF5 state, likely using
   `data.0051.flt.h5` and/or `data.0011.dbl.h5`, and connect selected particles
   to the final tracer/lobe volume convention.

3. Promote the final C-HI endpoint into the aligned truth/X-ray/radio/cavity
   workflow.

   The next integrated endpoint page should aim to combine:

   - Level 1/2 truth extraction
   - final XRAiSE grid X-ray map
   - sparse PRAiSE radio map
   - cavity geometry and energetics protocol
   - observable-vs-truth comparison

4. Add plot generation for the sparse radio bridge if useful.

   The current bridge product is TSV/CSV/JSON first. A small plotting script
   producing PNG/PDF quicklooks would make review with Barry/Patrick/Stas
   easier.

## Longer-Term Science Plan

The Honours project aim is to test X-ray cavity and radio-lobe energy proxies
against simulation truth in controlled PLUTO AGN jet simulations.

Core planning docs:

- `docs/Honours_Research_Plan.md`
- `docs/Honours_research_plan_feedback_SS_260424.txt`
- `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- `docs/kunanyi_restart_framework.md`

Current anchor case:

- C-HI: high-power cluster, symmetric, full-grid
- Jet power: `1e45 erg/s` (`1e38 W`)
- Jet speed: `0.1c`
- Half-opening angle: 15 degrees
- Cluster environment: centered Stewart cluster
- Particles from start
- Endpoint: 50 Myr

The minimum comparison suite remains:

- Low-power cluster, `1e36 W`
- High-power cluster, `1e38 W` - current anchor case
- Low-power group, `1e36 W`

The immediate scientific value is to turn the completed C-HI endpoint into a
reproducible, documented measurement chain before launching the next major
case. Once the C-HI endpoint chain is robust, use it as the template for the
low-power cluster and group runs.

Longer-term products should include:

- truth energetics from simulation state
- X-ray cavity estimates such as `pV`, `4pV`, buoyancy/sound/refill ages where
  appropriate
- radio lobe extent/luminosity/spectral-age style summaries where the tooling
  supports them
- aligned figures for a small set of viewing angles, likely including 0, 45,
  and 90 degrees
- a concise comparison table showing where observational proxies recover or
  miss the simulation truth

## Remote Compute Policy

The Mac mini is the default local orchestration and proving host, not the place
for serious production compute.

For compute routing, treat `/Users/bwbrook/work/nectar` as the control-plane
source of truth. Start with:

- `/Users/bwbrook/work/nectar/docs/workflows/control-plane-doctrine.md`
- `/Users/bwbrook/work/nectar/docs/workflows/compute-resource-selection.md`
- `/Users/bwbrook/work/nectar/docs/workflows/project-integration.md`
- `/Users/bwbrook/work/nectar/docs/workflows/data-placement.md`
- `/Users/bwbrook/work/nectar/docs/exchange/current_status.md`

Resource defaults:

- Mac mini: local docs, tests, analysis scaffolding, small checks, orchestration.
- `deep-server` / `utas-ubuntu`: large single-host Linux jobs.
- `alien` / Alien WSL: first GPU target for jobs fitting dual RTX 2080 GPUs.
- `nectar-vm`: elastic cloud CPU/GPU or clean disposable cloud state.
- `kunanyi`: genuine multi-node TPAC jobs, not routine single-node work.

For this project, Kunanyi is justified for production PLUTO runs and large
remote post-processing. Keep raw heavy data on Kunanyi and bring back only
summary artefacts.

## Communication And Documentation Policy

- `docs/exchange/current_status.md` is the first-stop cross-machine handover.
- Add dated logs under `docs/exchange/logs/` for each material Kunanyi job,
  science milestone, or handoff.
- Add dated notes under `docs/science/` for analysis products and
  interpretation.
- When Barry relays Patrick/Stas feedback, turn it into either an exchange log,
  a science note, or a bounded next action.
- If `agent_comms/` is present or mentioned, treat it as another relay channel;
  keep messages concise, factual, and tied to exact artefacts/job IDs.
- Prefer exact commands, paths, job IDs, checksums, and success signals over
  prose-only status.

## Cautions

- Do not restart the 80-node production path as the default. It has repeatedly
  failed at the restart scale even though smaller restarts and a fresh 80-node
  run were informative.
- Do not build a dense all-history particle HDF5 cache.
- Do not pull 40-70 GB production HDF5 files to the Mac mini unless Barry
  explicitly approves a reason.
- Do not assume the Chrome bridge is available just because Chrome is open.
  Smoke-test it with `browser.user.openTabs()`.
- Do not assume direct Kunanyi SSH is live; the jumpbox path may require manual
  portal re-authentication or "Enable Jumpbox SSH".
- Do not trust old host wording that describes this machine as a MacBook. The
  active local orchestration host is Barry's Apple Silicon Mac mini.
- Do not discard local changes inside UTAS AGN source checkouts. Some are
  intentional fork-side or bring-up changes.
