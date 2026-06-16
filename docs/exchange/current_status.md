# Current Status

Last updated: 2026-06-16
Primary checkpoint repo: `/Users/bwbrook/papers/xray_cavities` on MacBook/Mac Mini,
or `/home/bwbrook/papers/xray_cavities` on Linux hosts.

## Read This First

Before trusting anything below, pull the latest `xray_cavities` on the machine
you are using:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

This note should be treated as a post-Goal-007 handoff. Always pull the latest
`origin/main` before relying on the exact file set or workflow bundle on any
machine.

Latest observational-product readiness gate on 2026-06-16:

- Goal 007 is the local response to Patrick-agent's `Q-014` `HOLD` and
  clarification. The issue is now framed as X-ray observational-product and
  plotting readiness, plus radio-observable status, before any broadening.
- New tooling:
  - `scripts/science/build_final_observational_product_readiness.py`
  - `tests/test_final_observational_product_readiness.py`
- Local product assets:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/`
- Main figure:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/c_hi_final_observational_product_readiness.png`
- Metadata:
  `docs/science/assets/c_hi_final_observational_product_readiness_2026-06-16/observational_product_readiness_metadata.json`
- Science note:
  `docs/science/c_hi_final_observational_product_readiness_2026-06-16.md`
- Exchange log:
  `docs/exchange/logs/2026-06-16-c-hi-final-observational-product-readiness.md`
- Agent-comms review thread:
  `agent_comms/threads/2026-06-16-c-hi-observational-product-readiness.md`
- Open question added:
  `Q-015` to `patrick-agent`.
- The new figure uses the full local corrected 1 keV X-ray field
  `x = -199.1538544` to `199.1538544 kpc` and
  `z = -248.9480743` to `248.9480743 kpc`, plus a cavity-focused panel and a
  boxcar unsharp-mask residual panel. Tracer contours and current
  tracer-defined cavity ellipses are diagnostic overlays only.
- Headline recommendation: the package is ready for Patrick-agent review, not
  for method freeze or broadening. The X-ray topology remains unresolved
  between a visually connected shocked-shell/envelope interpretation and the
  current two tracer-defined side ellipsoids. Sparse PRAiSE and
  particle-binned radio products remain particle-emissivity diagnostics, not
  validated radio observables.
- Recommended next goal depends on Patrick-agent's `Q-015` response. If the
  product remains on `HOLD`, prioritize a narrow X-ray-based cavity/topology
  fitting method. If Patrick-agent accepts the X-ray product, the next radio
  goal should be full raytraced radio surface-brightness at two or more
  frequencies before using radio maps as observables.

Latest method-review decision packet on 2026-06-11:

- Accepted Goal 006 created a concise `C-HI` final method-review decision packet from
  accepted Goals 003-005, the Goal 004 audit, the Honours plan, Meeting 2, and
  agent-comms review history.
- Decision note:
  `docs/science/c_hi_final_method_review_decision_packet_2026-06-11.md`
- Machine-readable matrix:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/method_decision_matrix.csv`
- Scalar evidence:
  `docs/science/assets/c_hi_final_method_review_decision_packet_2026-06-11/scalar_evidence.csv`
- Agent-comms review thread:
  `agent_comms/threads/2026-06-11-c-hi-final-method-review.md`
- Open questions added:
  `Q-012` and `Q-013` for `stas-agent`, `Q-014` for `patrick-agent`.
- Headline recommendation: do not broaden immediately to `45/90 deg`,
  source-age sampling, `C-LO`, or `G-LO`. First ask Stas-agent and
  Patrick-agent to review the method. Future products should carry `pV`,
  `2.5pV`, and `4pV`; `2.5pV` is the candidate default physical interpretation
  for non-relativistic plasma pending Stas-agent review, while `4pV` remains a
  literature comparator.
- The packet asks whether the Level 3 ambient-energy method must precede
  broadening or can proceed as a parallel next method goal.
- Future large PBS job rule: after submit and queued/running verification, the
  action agent should wake the orchestrator and stop until Barry reports a PBS
  completion email or explicitly requests a re-check.
- Current state: waiting for Stas-agent and Patrick-agent responses in the
  agent-comms thread before opening controlled views, source-age sampling, or
  comparison-case broadening.

Latest final endpoint X-ray/cavity alignment gate on 2026-06-11:

- Accepted Goal 005 produced the first final 50 Myr `C-HI`, `0 deg` X-ray/cavity
  alignment product using the completed endpoint, accepted Level 1/2 truth, and
  Goal 003 volume-coupled radio scalars.
- New tooling:
  - `scripts/science/build_final_xray_cavity_alignment.py`
  - `scripts/kunanyi/c_hi_final_endpoint_xray_cavity_alignment.pbs`
  - `tests/test_final_xray_cavity_alignment.py`
- The final X-ray/cavity extraction used:
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`
  and timestep `Timestep_51`.
- PBS job `697898.kunanyi-ohpc` completed the heavy X-ray and cavity
  extraction but exited `1` during post-cavity validation because `python`
  resolved to an older interpreter after the HDF5 module load. The wrapper was
  corrected to reload `Anaconda3/2024.02-1`; a lightweight finalizer validated
  the already-produced outputs and wrote the archive.
- Remote output root:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment`
- Remote archive:
  `/u/bwbrook/codex_kunanyi/goal005_final_xray_cavity_alignment/final_endpoint_xray_cavity_alignment_2026-06-11.tar.gz`
- Archive SHA-256:
  `2d75e982a389ac0db6f9459c14d27ab3c5e749d045da18050f47df544f4c155e`
- Local review assets:
  `docs/science/assets/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11/`
- Science note:
  `docs/science/c_hi_final_endpoint_xray_cavity_alignment_2026-06-11.md`
- Exchange log:
  `docs/exchange/logs/2026-06-11-c-hi-final-endpoint-xray-cavity-alignment.md`
- Headline result: `gate_status = green`. The corrected 1 keV X-ray map is
  finite/nonblank with max `2.874403714611562e6 mJy sr^-1`; the cavity tracer
  volumes match accepted Level 2 `tracer > 5e-3` side volumes to numerical
  precision; bipolar cavity `4pV = 2.751221575650812e60 erg`, which is
  `0.8718095088507404` of Level 1 bipolar injected energy and
  `1.9819430042244381` times the Level 2 tracer-lobe energy.
- Interpretation: the final `C-HI` endpoint X-ray/cavity path is accepted as
  green for bounded prove-out review, not a publication-ready observable. The
  next decision should be a Barry/Stas/Patrick review of the cavity protocol
  and whether the Level 3 ambient-energy/method goal must come before
  broadening to `C-LO`, `G-LO`, multi-angle, or source-age sampling.

Latest production prove-out gap audit on 2026-06-11:

- Accepted Goal 004 reconciled the Meeting 2 action plan, Honours plan and Stas
  feedback, accepted Goals 001-003, and current full-run evidence.
- Audit note:
  `docs/science/c_hi_final_production_prove_out_gap_audit_2026-06-11.md`
- Machine-readable matrix:
  `docs/science/assets/c_hi_final_production_prove_out_gap_audit_2026-06-11/prove_out_matrix.csv`
- Exchange log:
  `docs/exchange/logs/2026-06-11-c-hi-final-production-prove-out-gap-audit.md`
- Headline conclusion: the first full 50 Myr `C-HI` run is a credible anchor
  for continued prove-out, with green endpoint integrity, particle state,
  sparse-window, Level 1/2 truth, and sparse PRAiSE-compatible radio-volume
  coupling. It does not yet prove the final X-ray path, final cavity protocol,
  Level 3 ambient-energy method, beam/instrument treatment, viewing-angle or
  source-age sampling, or readiness for the mandatory `C-LO`/`G-LO` cases.
- Recommended next action: superseded by the Goal 005 final endpoint
  X-ray/cavity alignment gate above.

Latest final volume-coupled sparse comparison on 2026-06-11:

- The completed 50 Myr `C-HI` final grid/tracer endpoint has now been used to
  declare side volumes for the existing sparse PRAiSE-compatible radio bridge.
- New tooling:
  - `scripts/science/build_final_volume_coupled_comparison.py`
  - `scripts/kunanyi/c_hi_fullgrid_final_volume_coupled_comparison.pbs`
  - `tests/test_final_volume_coupled_comparison.py`
- The remote truth extraction used final HDF5 endpoint
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`
  and timestep `Timestep_51`.
- PBS job `697875.kunanyi-ohpc` completed green:
  - job name: `c_hi_vc_cmp`
  - request: `select=1:ncpus=1:mpiprocs=1:mem=96gb`
  - output root:
    `/scratch/bwbrook/xray_cavities_analysis/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison`
  - remote archive:
    `/u/bwbrook/codex_kunanyi/goal003_final_volume_coupled_comparison/final_volume_coupled_comparison_2026-06-11.tar.gz`
  - archive SHA-256:
    `0fe05b959843748aec1fdbdd0e08a871e03dccfb3017b78351b31f9c569a0083`
- Final `tracer > 5e-3` declared side volumes:
  - negative z: `367123.31815126061 kpc^3`
  - positive z: `373343.26830024854 kpc^3`
  - bipolar total: `740466.58644933475 kpc^3`
- The volume-coupled external-loss bridge preserved the Goal 001/002 selected
  ID and loss-table contract:
  - selected particles: `20000`
  - matched selected IDs: `20000`
  - extra loss-table IDs: `0`
  - `loss_model_key = external_praise_compatible`
  - `volume_assignment = declared side volumes divided evenly across selected particles`
- Local review assets:
  `docs/science/assets/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11/`
- Science note:
  `docs/science/c_hi_fullgrid_final_volume_coupled_comparison_2026-06-11.md`
- Exchange log:
  `docs/exchange/logs/2026-06-11-c-hi-fullgrid-final-volume-coupled-comparison.md`
- Interpretation: this is a final-endpoint volume-coupling comparison product,
  not a finished observational result. It does not change the sparse
  selected-ID population, PRAiSE parameters, observing frequency, redshift,
  tracer threshold, or sparse-window selection.
- Next action: superseded by the Goal 004 prove-out audit above.

Latest final sparse radio bridge on 2026-06-08:

- The completed 50 Myr `C-HI` full-grid sparse particle window has now been
  connected to a first 150 MHz radio bridge product.
- New tooling:
  - `scripts/science/sparse_particle_radio_bridge.py`
  - `scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs`
  - `tests/test_sparse_particle_radio_bridge.py`
- Local verification passed:
  - `uv run pytest tests/test_sparse_particle_radio_bridge.py -q`
  - `uv run pytest tests/test_sparse_particle_radio_bridge.py tests/test_pluto_particle_sparse_window.py -q`
  - `bash -n scripts/kunanyi/c_hi_fullgrid_final_sparse_radio_bridge.pbs`
- Remote staging used the authenticated Chrome/Open OnDemand shell because
  plain SSH control-socket auth was unavailable. The reliable route was a fresh
  shell tab plus terminal-iframe textarea typing; long hterm clipboard batches
  can concatenate and corrupt staged data.
- Staged remote checksums matched local:
  - `spr.py`:
    `29d827cff6a8587e00f0c7b909c32ed9bd6f0c3ec3ad208052ddedc684d124dd`
  - `spr.pbs`:
    `dbf2315ba4df7557c2c10571216cceab40357a135df39cc36dc1669f50c2f1a5`
- PBS job `697646.kunanyi-ohpc` completed green:
  - job name: `c_hi_spr_fin`
  - `Exit_status=0`
  - `resources_used.walltime=00:00:05`
  - `resources_used.cput=00:00:04`
  - stderr size: `0` bytes
- Remote output directory:
  `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge`
- Remote archive:
  `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.tar.gz`
- Archive SHA-256:
  `2be0b61dcc7330727192123f9afd9c9a7138d26ea4f552ba62753cd72e24effe`
- Compact products were pulled locally through the Open OnDemand Files app and
  unpacked under:
  `docs/science/assets/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08/`
- Headline metrics:
  - target index: `5000`
  - sparse trajectory rows consumed: `218909`
  - selected target particles: `20000`
  - particles in frame: `20000`
  - map shape: `460 x 90`
  - pressure-history loss proxy mean: `0.8957169833296894`
  - bipolar proxy luminosity: `4.4514434941743747e27 W Hz^-1`
- Science report:
  `docs/science/c_hi_fullgrid_final_sparse_radio_bridge_2026-06-08.md`
- Exchange log:
  `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-sparse-radio-bridge.md`
- Interpretation: this is a morphology/continuity bridge, not the final sparse
  PRAiSE loss kernel. The loss term is
  `clip(final pressure / max positive sparse-window pressure, 0, 1)`, and the
  luminosity scale uses `1.0 kpc^3` per selected particle.
- Next action: replace the pressure-history proxy with a true sparse
  PRAiSE-compatible loss interface, then couple that map to final grid/tracer
  volumes and the observable comparison page.

Latest restart-framework update on 2026-05-25:

- Long `kunanyi` PLUTO runs should now be treated as restartable PBS
  segments, not single precious jobs. Barry will feed PBS failures from email;
  Codex should inspect, classify, and continue from the latest valid
  restart-capable `dbl.h5` output.
- New restart operations guide:
  `docs/kunanyi_restart_framework.md`
- New inspection helper:
  `scripts/kunanyi/inspect_c_hi_fullgrid_restart_state.sh <jobid>`
- New continuation wrapper/helper:
  - `scripts/kunanyi/c_hi_fullgrid_continue.pbs`
  - `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_continue.sh`
- The generic remote helpers now default to the home-network Tailscale route
  through `deep-server`:
  - `scripts/kunanyi/run_on_kunanyi.sh` defaults to
    `TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep`
  - `scripts/kunanyi/copy_to_kunanyi.sh` and
    `scripts/kunanyi/fetch_from_kunanyi.sh` default to
    `TPAC_SCP_HOST=kunanyi-via-deep`
- The production template now verifies restart catalogue entries against
  actual `data.NNNN.dbl.h5`/`data.NNNN.dbl` files before restart, records
  `MPI_EXIT_CODE`, classifies common MPI failures, and carries the reason into
  `FAILED`.
- Superseded by the 2026-05-31 AGN Intel/IMPI 80-node result below. The
  current large-scale blocker is no longer the original OpenMPI/UCX abort
  signature; it is an AGN Intel/IMPI parallel HDF5 restart hang at 2240 ranks.

Latest Mac Mini migration checkpoint on 2026-05-26:

- The always-on Mac Mini is reachable as `dev-box-ts` from the MacBook over
  Tailscale and is now a valid first-class development/control host for this
  repo.
- New handover for a fresh Mac Mini agent:
  `docs/exchange/dev_box_ts_handover.md`
- Mac Mini `xray_cavities` checkout:
  - path: `/Users/bwbrook/papers/xray_cavities`
  - branch: `main`
  - HEAD after pull: `aadf938`
  - state: clean and even with `origin/main`
- Mac Mini repo-local Python environment was built with `uv sync --frozen`.
  Basic smoke checks passed for Python `3.12.13`, `h5py`, `pytest`, and the
  editable `plutokore` distribution.
- Relevant UTAS AGN GitLab checkouts are present under
  `/Users/bwbrook/git/utas-agn`:
  - `pluto` on `bwbrook/deep-server-bringup` at `2674fc3`
  - `jet-setup` on `bwbrook/deep-server-bringup` at `e17ac8f`
  - `plutokore` on `bwbrook/deep-server-bringup` at `e80252c`
  - `jet-setup.wiki` on `master` at `14d5aa7`
- The fork-backed GitLab repos now have both Barry fork `origin` and canonical
  `upstream` remotes configured on the Mac Mini.
- The TPAC secret env file was copied to the Mac Mini at
  `~/.config/tpac/kunanyi.env` with mode `600`; do not commit or print it.
- The Mac Mini does not currently have the ignored large `env/` payloads, an
  OpenStack/Nectar secret env, or `openstack` CLI on PATH. That is not a
  blocker for the current `kunanyi` wait state; use `/Users/bwbrook/work/nectar`
  if Nectar resizing/control needs to move to the Mini later.

Latest AGN Intel/IMPI follow-up on 2026-05-29:

- Patrick changed `/ds/projects/agn` from `drwxrwxr--` to `drwxrwxr-x`,
  which is enough for Barry's `bwbrook` account to traverse the AGN group tree
  without an ACL.
- The exact Patrick-agent stack now loads on `kunanyi`:
  `module use /ds/projects/agn/modulefiles; ml intel impi hdf5/1.12.1p zfp/0.5.5`.
- The loaded compiler/MPI paths are:
  - `mpicc=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin_ohpc/mpicc`
  - `mpirun=/share/apps/intel/xe_2018_update1/compilers_and_libraries_2018.1.163/linux/mpi/intel64/bin/mpirun`
  - `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
- The guarded tiny PLUTO 3D Cartesian smoke was submitted and completed green:
  - PBS job: `696012.kunanyi-ohpc`
  - request: `select=2:ncpus=8:mpiprocs=8`, `walltime=00:20:00`
  - nodes: `(n166:ncpus=8)+(n190:ncpus=8)`
  - `resources_used.walltime=00:17:39`
  - `Exit_status=0`
  - output catalogue reached `data.0000.dbl`, `data.0001.dbl`, and
    `data.0002.dbl`
  - no UCX `UD endpoint ... unhandled timeout error` signature appeared.
- Non-fatal caveats: PBS stderr still includes a startup/module warning about
  an attempted `gnu8/ohpc` load while `intel` is active, and
  `jet-setup/tools/setup-problem` still reports `git: command not found`.
  Neither blocked the tiny Intel/IMPI run.
- The next bounded production-style `C-HI` full-grid restart was submitted
  under the same AGN Intel/IMPI/HDF5/ZFP stack and completed green:
  - PBS job: `696086.kunanyi-ohpc`
  - request: `select=8:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - `resources_used.walltime=00:39:20`
  - `Exit_status=0`
  - `KUNANYI_MODULE_STACK=agn_intel_impi`
  - `MPI_FLAVOR=intelmpi`
  - `FORCE_REBUILD=1`
  - `RUN_KIND=h5_restart_0`
  - `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 0`
  - `MPI_EXIT_CODE=0`
  - PLUTO saw `Number of processors: 224`, restarted from
    `data.0000.dbl.h5`, and wrote fresh full-grid `data.0001.dbl.h5`,
    `data.0001.flt.h5`, `particles.0001.dbl` through `particles.0004.dbl`,
    and `restart.out`.
  - `dbl.h5.out` and `flt.h5.out` now both include output `1` at
    `t = 1.011234e+01`, `dt = 2.777278e-01`, step `135`.
  - No UCX `UD endpoint ... unhandled timeout error`, `MPI_ABORT`, or
    segmentation-fault signature appeared.
- Caveats remain non-fatal: the Lmod `gnu8/ohpc` versus `intel` warning,
  `setup-problem: line 11: git: command not found`, and the known
  `SetOutputVar(): var_name 'energy' cannot be set/unset for writing` message.
- Next action: treat the AGN Intel/IMPI path as validated at 8-node full-grid
  restart scale.
- Barry chose to proceed directly to the full 80-node AGN Intel/IMPI
  continuation. It has been staged and submitted:
  - PBS job: `696197.kunanyi-ohpc`
  - job name: `c_hi_fg_agn80`
  - queue/state at submit: `normal` / `Q`
  - request: `select=80:ncpus=28:mpiprocs=28`, `walltime=48:00:00`
  - wrapper: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.pbs`
  - stdout/stderr:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.out`
    and
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_continue.err`
  - restart source verified at submit:
    `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/data.0001.dbl.h5`
  - restart index: `1`
  - `dbl.h5.out` submit tail included outputs `0` and `1`, with output `1`
    at `t = 1.011234e+01`, `dt = 2.777278e-01`, step `135`.
  - module stack verified immediately before `qsub`:
    `intel/18.0.1.163`, `impi/2018.1.163`, `hdf5/1.12.1p`, `zfp/0.5.5`.
- The 80-node AGN Intel/IMPI continuation completed with a walltime kill:
  - PBS job: `696197.kunanyi-ohpc`
  - `Exit_status=271`
  - `resources_used.walltime=48:01:46`
  - `resources_used.cput=1342:50:36`
  - `resources_used.ncpus=2240`
  - stderr: `PBS: job killed: walltime 172896 exceeded limit 172800`
  - local marker: `FAILED`, with `exit_code=143`, `signal=TERM`,
    `finished_utc=2026-05-31T03:20:28Z`.
- The run rebuilt under AGN Intel/IMPI and launched as intended:
  - `KUNANYI_MODULE_STACK=agn_intel_impi`
  - `MPI_FLAVOR=intelmpi`
  - `MODULES=intel/18.0.1.163:impi/2018.1.163:hdf5/1.12.1p:zfp/0.5.5`
  - `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - `NRANKS=2240`
  - `RUN_KIND=h5_restart_1`
  - `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5 -h5restart 1`
- The failure mode is now sharply localized:
  - all `2240` per-rank logs reached their final
    `> restarting from file #1 (dbl.h5)` line.
  - a post-restart scan found `0` rank logs reaching `Starting computation`,
    `Restarting from Particle`, a `step:` line, or a `Writing file` line after
    that final restart line.
  - `dbl.h5.out` and `flt.h5.out` still stop at output `1`; no
    `data.0002.*` file was written.
  - the only output file newer than the 696197 nodefile was `grid.out`, written
    during startup.
  - no UCX `UD endpoint ... unhandled timeout error`, `MPI_ABORT`, or
    segmentation-fault signature was found for this AGN Intel/IMPI run.
- Interpretation: `696197` did not reproduce the old UCX crash. It appears to
  have hung or effectively stalled inside the full-grid parallel HDF5 restart
  from `data.0001.dbl.h5` at 80 nodes / 2240 ranks. CPU utilization was very
  low for the allocation, so this looks like an MPI-IO/HDF5/filesystem-scale
  issue rather than productive compute.
- Next action: package this evidence for Patrick/Stas/TPAC. The key question is
  why the same AGN Intel/IMPI/HDF5 stack restarts the full-grid HDF5 output at
  8 nodes / 224 ranks but stalls before particle restart/computation at
  80 nodes / 2240 ranks.

Latest Patrick fresh-start completion on 2026-06-03:

- Patrick advised trying a fresh run rather than restarting from previous
  outputs, and setting `HDF5_USE_FILE_LOCKING=FALSE` if the simulation hangs
  while writing HDF5 on the older HDF5 stack.
- Patrick-agent's latest `origin/main` access reply was incorporated into the
  local working tree without fast-forwarding over the dirty worktree. That
  reply confirms the AGN module/library access issue was resolved; the tiny
  smoke and 8-node restart checks are already green as documented above.
- A fresh 80-node full-grid `C-HI` particles job was staged, submitted, and
  completed green:
  - PBS job: `696619.kunanyi-ohpc`
  - job name: `c_hi_fg_fresh`
  - final state: `F`
  - `Exit_status=0`
  - `resources_used.walltime=47:33:46`
  - `resources_used.cput=1329:31:13`
  - `resources_used.ncpus=2240`
  - request: `select=80:ncpus=28:mpiprocs=28`, `walltime=48:00:00`
  - wrapper: `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.pbs`
  - stdout/stderr:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.out`
    and
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_fresh_start.err`
  - run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh`
  - config source:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_2026-05-19/C-HI/particles`
  - `RESTART_POLICY=force-fresh`
  - `HDF5_USE_FILE_LOCKING=FALSE`
  - `KUNANYI_MODULE_STACK=agn_intel_impi`
  - `MPI_FLAVOR=intelmpi`
  - `RUN_KIND=fresh`
  - `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5`
  - `MPI_EXIT_CODE=0`
  - `JOB_START=2026-06-01T03:06:33Z`
  - `JOB_END=2026-06-03T02:40:14Z`
- The new run root deliberately avoids clobbering the previous
  `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
  evidence tree. The stage helper also refuses to submit if the fresh output
  directory already contains files unless explicitly overridden.
- Remote verification found a `DONE` marker and no `FAILED` marker:
  `status=done`, `case_id=C-HI`, `case_variant=particles`,
  `pbs_jobid=696619.kunanyi-ohpc`,
  `finished_utc=2026-06-03T02:40:14Z`.
- Output products reached the intended fresh-run endpoint:
  - output volume: `2.5T`
  - `dbl.h5.out_lines=10`, ending at output `9`,
    `t = 1.311314e+04`, step `42194`
  - `flt.h5.out_lines=44`, ending at output `43`,
    `t = 1.311314e+04`, step `42194`
  - HDF5 counts: `10` double-precision HDF5 outputs and `44`
    floating-point HDF5 outputs
  - particle outputs: `4278`, ending at `particles.4277.dbl`
  - final large outputs include `data.0009.dbl.h5` and `data.0043.flt.h5`
- In-place product integrity/readability checks on 2026-06-03 were green:
  - final double HDF5:
    `data.0009.dbl.h5`, size `67318639276`, HDF5 readable, with
    `/Timestep_9/vars/{rho,vx1,vx2,vx3,prs,tr1}` datasets shaped
    `{1014, 960, 960}`
  - final float HDF5:
    `data.0043.flt.h5`, size `44890581676`, HDF5 readable, with
    `/Timestep_43/vars/{rho,vx1,vx2,vx3,prs,tr1}` datasets shaped
    `{1014, 960, 960}`
  - scalar reads succeeded for both double and float `rho` and `vx1`;
    for example `rho(0,0,0)=0.00106042` and
    `vx1(0,0,0)=4.16167e-05`
  - XMF sidecars reference the expected final HDF5 files and time
    `1.311314e+04`
  - `restart.out` exists, is non-empty, and is `1280` bytes
  - final particle file `particles.4277.dbl` exists, is `20220069` bytes, and
    its ASCII header reports `nparticles=168496`,
    `time=1.311314069772e+04`, and `stepNumber=42194`
- Bounded rank-log sampling found `2240` rank logs; sampled ranks ended with
  `> Done` after writing `particles.4277.dbl`. No UCX, UD endpoint,
  `MPI_ABORT`, segmentation fault, or HDF5 diagnostic signature appeared in
  the checked stdout/stderr/sample tails. Stderr still has the known non-fatal
  Lmod compiler-module warning and `setup-problem: line 11: git: command not
  found`.
- Interpretation: Patrick's fresh-start pathway works at full 80-node /
  2240-rank scale under the AGN Intel/IMPI/HDF5/ZFP stack with
  `HDF5_USE_FILE_LOCKING=FALSE`. The previous 80-node failure remains best
  interpreted as restart-specific or restart-triggered, not a general inability
  of the stack to run the full-grid case at scale.
- Next recommended action: submit a short bounded 80-node restart probe from
  output `9` with the same AGN Intel/IMPI stack and
  `HDF5_USE_FILE_LOCKING=FALSE`. Success means the segmented production
  pathway is viable; a stall would crisply localize the issue to full-scale
  HDF5 restart behaviour even from a clean fresh-generated output.
- The bounded 80-node restart probe from output `9` has now been staged and
  submitted:
  - PBS job: `696911.kunanyi-ohpc`
  - job name: `c_hi_fg_r9probe`
  - queue/state at submit: `normal` / `Q`
  - request: `select=80:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - wrapper:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.pbs`
  - stdout/stderr:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.out`
    and
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_80node_restart_probe.err`
  - local helper:
    `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_80node_restart_probe.sh`
  - remote run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh`
  - `EXPECTED_RESTART_INDEX=9`
  - `RESTART_POLICY=auto`
  - expected template `RUN_KIND`: `h5_restart_9`
  - `PLUTO_MAXTIME_HOURS=0.5`
  - `HDF5_USE_FILE_LOCKING=FALSE`
  - `KUNANYI_MODULE_STACK=agn_intel_impi`
  - `MPI_FLAVOR=intelmpi`
- Pre-submit remote validation re-read
  `/Timestep_9/vars/rho` from `data.0009.dbl.h5`, verified the AGN module
  stack, and confirmed the latest `dbl.h5.out` restart index was exactly `9`
  before `qsub`.
- Expected next action: when Barry's PBS email lands for `696911.kunanyi-ohpc`,
  inspect whether `RUN_KIND=h5_restart_9` reached computation and wrote a new
  HDF5 output, ideally `data.0010.dbl.h5`. A green result validates segmented
  full-scale production. A stall cleanly reproduces the restart-specific
  blocker from a known-good fresh output.
- Result now known: `696911.kunanyi-ohpc` reproduced the full-scale restart
  blocker.
  - job name: `c_hi_fg_r9probe`
  - `Exit_status=271`
  - `resources_used.walltime=02:01:12`
  - `resources_used.cput=56:05:35`
  - `resources_used.ncpus=2240`
  - PBS stderr: `PBS: job killed: walltime 7262 exceeded limit 7200`
  - marker state: only `FAILED`, with `exit_code=143`, `signal=TERM`,
    `finished_utc=2026-06-03T07:22:18Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=2240`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - no new science products appeared:
    `data.0010.dbl.h5`, `data.0044.flt.h5`, and `particles.4278.dbl` are
    absent; `dbl.h5.out` still has `10` lines ending at output `9`, and
    `flt.h5.out` still has `44` lines ending at output `43`
  - `data.*.dbl.h5` count remains `10`, `data.*.flt.h5` count remains `44`,
    and particle output count remains `4278`
  - direct sampled rank logs (`pluto.0`, `pluto.1`, `pluto.27`, `pluto.28`,
    `pluto.1119`, `pluto.1120`, `pluto.2238`, `pluto.2239`) all end at
    `> restarting from file #9 (dbl.h5)`, with no subsequent
    `Starting computation`, particle restart, `step:`, or write line in the
    sampled tails
  - the full rank-log set is large (`2240` files, about `1.03 GB` total);
    broad all-rank scans were deliberately abandoned after they became slow on
    remote scratch. The deterministic sample plus unchanged output catalogues
    is enough to classify the run.
- Interpretation: the clean fresh 80-node run and HDF5 products are good, but
  a 2240-rank restart from the clean output `9` still stalls inside or
  immediately after the parallel HDF5 restart read, before particle restart or
  computation. Patrick's `HDF5_USE_FILE_LOCKING=FALSE` write-hang mitigation
  was carried through, so this is not simply the old file-locking write issue.
  It is now best framed for Patrick/TPAC as a full-scale parallel HDF5 restart
  read problem under the AGN Intel/IMPI/HDF5 stack.
- Next recommended action: do not spend another 80-node allocation on the same
  restart path unchanged. Escalate this evidence to Patrick/TPAC, and if more
  local probing is useful, run a node-count ladder from the same clean output
  `9` to locate the restart failure threshold before trying another production
  continuation. A fresh full-duration strategy remains viable, but segmented
  full-scale restart is not yet validated.
- Barry has sent the short evidence summary to Patrick. The first node-count
  ladder rung has been staged and submitted from the same clean fresh output
  `9`, isolated from the successful fresh run tree:
  - PBS job: `697160.kunanyi-ohpc`
  - job name: `c_hi_r9_08n`
  - queue/state at submit: `normal` / `Q`
  - request: `select=8:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - wrapper:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs`
  - stdout/stderr:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_08node.out`
    and
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_ladder_08node.err`
  - local helper:
    `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_agn_impi_restart_ladder.sh`
  - isolated rung run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-05-c-hi-fullgrid-agn-impi-r9-ladder-08node`
  - source fresh run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh`
  - restart input:
    `data.0009.dbl.h5`, restart index `9`
  - particle input:
    `particles.4277.dbl`
  - `PLUTO_MAXTIME_HOURS=0.5`
  - `HDF5_USE_FILE_LOCKING=FALSE`
  - `KUNANYI_MODULE_STACK=agn_intel_impi`
  - `MPI_FLAVOR=intelmpi`
- The ladder helper copies only small catalogues/metadata into the rung work
  root and symlinks the large HDF5/particle restart inputs back to the
  known-good fresh products. This prevents a successful rung from appending
  `data.0010.*` or `particles.4278.dbl` into the clean fresh production tree.
- Result now known: `697160.kunanyi-ohpc` completed green at 8 nodes /
  224 ranks.
  - job name: `c_hi_r9_08n`
  - `Exit_status=0`
  - `resources_used.walltime=00:39:50`
  - `resources_used.cput=17:40:28`
  - `resources_used.ncpus=224`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697160.kunanyi-ohpc`,
    `finished_utc=2026-06-05T04:10:41Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=224`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - the isolated rung wrote new regular outputs while preserving symlinks to
    the fresh-run restart inputs:
    `data.0010.dbl.h5`, `data.0044.flt.h5`, and
    `particles.4278.dbl` through `particles.4287.dbl`
  - `dbl.h5.out` now has `11` lines ending at output `10`,
    `t = 1.314390e+04`, `dt = 3.139112e-01`, step `42292`
  - `flt.h5.out` now has `45` lines ending at output `44`,
    `t = 1.314390e+04`, `dt = 3.139112e-01`, step `42292`
  - sampled ranks `0`, `1`, `27`, `28`, `111`, `112`, `222`, and `223`
    all reached writes and ended with `> Done`.
- Interpretation: restart from the clean fresh output `9` is still valid at
  8-node scale under the AGN Intel/IMPI/HDF5 stack. The failure threshold is
  therefore above 224 ranks and below or at 2240 ranks.
- Result now known: `697174.kunanyi-ohpc` completed green at 16 nodes /
  448 ranks.
  - PBS job: `697174.kunanyi-ohpc`
  - job name: `c_hi_r9_16n`
  - `Exit_status=0`
  - `resources_used.walltime=00:37:52`
  - `resources_used.cput=16:37:43`
  - `resources_used.ncpus=448`
  - request: `select=16:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697174.kunanyi-ohpc`,
    `finished_utc=2026-06-05T04:55:40Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=448`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - the isolated rung wrote `data.0010.dbl.h5`, `data.0044.flt.h5`, and
    particle outputs through `particles.4298.dbl`; source restart files remained
    symlinks to the fresh run
  - `dbl.h5.out` now has `11` lines ending at output `10`,
    `t = 1.317530e+04`, `dt = 3.139112e-01`, step `42392`
  - `flt.h5.out` now has `45` lines ending at output `44`,
    `t = 1.317530e+04`, `dt = 3.139112e-01`, step `42392`
  - sampled ranks `0`, `1`, `27`, `28`, `223`, `224`, `446`, and `447`
    all reached particle write `#4298` and ended with `> Done`.
  - non-fatal stderr is still the known Lmod compiler-module warning about
    `gnu8/8.3.0` while `intel` is active.
- Interpretation: restart from the clean fresh output `9` is valid through
  16-node scale under the AGN Intel/IMPI/HDF5 stack. The failure threshold is
  therefore above 448 ranks and below or at 2240 ranks.
- Result now known: `697223.kunanyi-ohpc` completed green at 32 nodes /
  896 ranks.
  - PBS job: `697223.kunanyi-ohpc`
  - job name: `c_hi_r9_32n`
  - `Exit_status=0`
  - `resources_used.walltime=00:35:03`
  - `resources_used.cput=15:27:14`
  - `resources_used.ncpus=896`
  - request: `select=32:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697223.kunanyi-ohpc`,
    `finished_utc=2026-06-05T06:53:35Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=896`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - the isolated rung wrote `data.0010.dbl.h5`, floating HDF5 outputs through
    `data.0045.flt.h5`, and particle outputs through `particles.4307.dbl`;
    source restart files remained symlinks to the fresh run
  - `dbl.h5.out` now has `11` lines ending at output `10`,
    `t = 1.320512e+04`, `dt = 3.139112e-01`, step `42487`
  - `flt.h5.out` now has `46` lines ending at output `45`,
    `t = 1.320512e+04`, `dt = 3.139112e-01`, step `42487`
  - sampled ranks `0`, `1`, `27`, `28`, `447`, `448`, `894`, and `895`
    all reached particle write `#4307` and ended with `> Done`.
  - non-fatal stderr is still the known Lmod compiler-module warning about
    `gnu8/8.3.0` while `intel` is active.
- Interpretation: restart from the clean fresh output `9` is valid through
  32-node scale under the AGN Intel/IMPI/HDF5 stack. The failure threshold is
  therefore above 896 ranks and below or at 2240 ranks.
- Result now known: `697235.kunanyi-ohpc` completed green at 48 nodes /
  1344 ranks.
  - PBS job: `697235.kunanyi-ohpc`
  - job name: `c_hi_r9_48n`
  - `Exit_status=0`
  - `resources_used.walltime=00:34:58`
  - `resources_used.cput=15:09:47`
  - `resources_used.ncpus=1344`
  - request: `select=48:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697235.kunanyi-ohpc`,
    `finished_utc=2026-06-05T08:07:58Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=1344`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - the isolated rung wrote `data.0010.dbl.h5`, floating HDF5 outputs through
    `data.0045.flt.h5`, and particle outputs through `particles.4320.dbl`;
    source restart files remained symlinks to the fresh run
  - `dbl.h5.out` now has `11` lines ending at output `10`,
    `t = 1.324467e+04`, `dt = 3.139112e-01`, step `42613`
  - `flt.h5.out` now has `46` lines ending at output `45`,
    `t = 1.324467e+04`, `dt = 3.139112e-01`, step `42613`
  - sampled ranks `0`, `1`, `27`, `28`, `671`, `672`, `1342`, and `1343`
    all reached particle write `#4320` and ended with `> Done`.
  - all `1344` `pluto.<rank>.log` files ended with `> Done`.
  - non-fatal stderr is still the known Lmod compiler-module warning about
    `gnu8/8.3.0` while `intel` is active.
- Interpretation: restart from the clean fresh output `9` is valid through
  48-node scale under the AGN Intel/IMPI/HDF5 stack. The failure threshold is
  therefore above 1344 ranks and below or at 2240 ranks.
- Result now known: `697252.kunanyi-ohpc` completed green at 64 nodes /
  1792 ranks.
  - PBS job: `697252.kunanyi-ohpc`
  - job name: `c_hi_r9_64n`
  - `Exit_status=0`
  - `resources_used.walltime=00:35:12`
  - `resources_used.cput=15:13:03`
  - `resources_used.ncpus=1792`
  - request: `select=64:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697252.kunanyi-ohpc`,
    `finished_utc=2026-06-05T15:39:57Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=1792`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - the isolated rung wrote `data.0010.dbl.h5`, floating HDF5 outputs through
    `data.0045.flt.h5`, and particle outputs through `particles.4326.dbl`;
    source restart files remained symlinks to the fresh run
  - `dbl.h5.out` now has `11` lines ending at output `10`,
    `t = 1.326068e+04`, `dt = 3.139112e-01`, step `42664`
  - `flt.h5.out` now has `46` lines ending at output `45`,
    `t = 1.326068e+04`, `dt = 3.139112e-01`, step `42664`
  - sampled ranks `0`, `1`, `27`, `28`, `895`, `896`, `1790`, and `1791`
    all reached particle write `#4326` and ended with `> Done`.
  - all `1792` `pluto.<rank>.log` files ended with `> Done`.
  - non-fatal stderr is still the known Lmod compiler-module warning about
    `gnu8/8.3.0` while `intel` is active.
- Interpretation: restart from the clean fresh output `9` is valid through
  64-node scale under the AGN Intel/IMPI/HDF5 stack. The failure threshold is
  therefore above 1792 ranks and below or at 2240 ranks.
- Result now known: `697285.kunanyi-ohpc` reproduced the 80-node restart stall
  at 2240 ranks.
  - PBS job: `697285.kunanyi-ohpc`
  - job name: `c_hi_r9_80n`
  - `Exit_status=271`
  - `resources_used.walltime=02:01:12`
  - `resources_used.cput=55:16:36`
  - `resources_used.ncpus=2240`
  - request: `select=80:ncpus=28:mpiprocs=28`, `walltime=02:00:00`
  - marker state: only `FAILED`, with `status=failed`,
    `pbs_jobid=697285.kunanyi-ohpc`,
    `exit_code=143`,
    `signal=TERM`,
    `finished_utc=2026-06-06T02:11:45Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 0.5 -h5restart 9`,
    `NRANKS=2240`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`,
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi`
  - `MPI_EXIT_CODE` was not emitted; stdout ended with `JOB_SIGNAL=TERM` and
    `JOB_END=2026-06-06T02:11:45Z`
  - stderr included PBS walltime termination:
    `job killed: walltime 7262 exceeded limit 7200`
  - no new HDF5 or particle products were written:
    `data.0010.dbl.h5`, `data.0044.flt.h5`, `data.0045.flt.h5`, and
    `particles.4278.dbl` were absent; only the source symlinks
    `data.0009.dbl.h5` and `particles.4277.dbl` existed
  - `dbl.h5.out`, `flt.h5.out`, and `restart.out` remained at their source
    lengths (`10`, `44`, and `11` lines respectively)
  - all `2240` `pluto.<rank>.log` files ended with
    `> restarting from file #9 (dbl.h5)`;
    exact aggregate:
    `TOTAL=2240`,
    `RESTART_LAST=2240`,
    `DONE_LAST=0`,
    `WRITING_LAST=0`,
    `OTHER_LAST=0`,
    `RESTART_SEEN=2240`,
    `DONE_SEEN=0`,
    `WRITING_SEEN=0`
- Interpretation: the 80-node restart stall is reproducible under the AGN
  Intel/IMPI/HDF5 stack from the clean fresh output `9`. The practical
  production restart size is therefore 64 nodes / 1792 ranks. The failure
  boundary lies between 64 and 80 nodes, and it appears to be a parallel HDF5
  restart-read / MPI-IO / filesystem-scale issue rather than a simulation-time
  compute issue.
- Recommended next action:
  - treat 64 nodes as the current production sweet spot for C-HI restarts;
  - send Patrick/TPAC the concise 64-pass / 80-fail evidence bundle if they want
    to debug the 2240-rank boundary;
  - only pursue 80-node debugging if there is a real throughput requirement for
    80 nodes, since 64 nodes is already multi-node production scale and has
    passed the restart ladder cleanly.
- Barry and Codex then restarted science production at the 64-node sweet spot:
  - PBS job: `697298.kunanyi-ohpc`
  - job name: `c_hi_r9_p64`
  - queue/state at submit: `normal` / `Q`
  - request: `select=64:ncpus=28:mpiprocs=28`, `walltime=48:00:00`
  - PLUTO maxtime: `47.5` hours
  - wrapper:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_restart_ladder.pbs`
  - stdout/stderr:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_prod64.out`
    and
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_agn_impi_r9_prod64.err`
  - source workdir:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles`
  - production continuation root:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64`
  - production workdir:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles`
  - restart source:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5`
  - particle source:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/particles.4277.dbl`
  - submit validation loaded `intel/18.0.1.163`, `impi/2018.1.163`,
    `hdf5/1.12.1p`, and `zfp/0.5.5`; confirmed
    `HDF5_DIR=/ds/projects/agn/libraries/hdf5p/1.12.1-impi` and
    `HDF5_USE_FILE_LOCKING=FALSE`; and confirmed source restart index `9`.
- Result now known: `697298.kunanyi-ohpc` completed green, and the short
  walltime is explained by the finite C-HI `tstop`.
  - `Exit_status=0`
  - `resources_used.walltime=07:49:58`
  - `resources_used.cput=217:45:08`
  - `resources_used.ncpus=1792`
  - marker state: only `DONE`, with `status=done`,
    `pbs_jobid=697298.kunanyi-ohpc`,
    `finished_utc=2026-06-06T11:22:11Z`
  - launch state:
    `RUN_KIND=h5_restart_9`,
    `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 47.5 -h5restart 9`,
    `NRANKS=1792`,
    `MPI_EXIT_CODE=0`,
    `HDF5_USE_FILE_LOCKING=FALSE`,
    `KUNANYI_MODULE_STACK=agn_intel_impi`,
    `MPI_FLAVOR=intelmpi`
  - `pluto.ini` has `tstop = 15330.06968940`
  - `dbl.h5.out` now has `12` lines, ending at output `11`:
    `1.533007e+04`, `dt = 1.377728e-01`, step `49253`
  - `flt.h5.out` now has `52` lines, ending at output `51`:
    `1.533007e+04`, `dt = 1.377728e-01`, step `49253`
  - new regular products include `data.0010.dbl.h5`, `data.0011.dbl.h5`,
    `data.0044.flt.h5` through `data.0051.flt.h5`, and particle outputs
    through `particles.5000.dbl`
  - sampled ranks `0`, `1`, `27`, `28`, `895`, `896`, `1790`, and `1791`
    all reached `particles.5000.dbl`, reported elapsed time
    `0d:7h:47m:36s`, and ended with `> Done`
  - exact all-rank scan:
    `TOTAL=1792`,
    `DONE_LAST=1792`,
    `RESTART_SEEN=1792`,
    `DONE_SEEN=1792`,
    `WRITE11_SEEN=1792`,
    `OTHER_LAST=0`
- Interpretation: this was not an early failure. The 64-node continuation
  consumed the remaining simulation interval from clean output `9` to the
  configured C-HI endpoint, wrote the final HDF5 and particle products, and
  exited normally. Treat the
  `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64`
  tree as the current completed science production endpoint.
- Product-integrity/readability checks on 2026-06-07 were green under the AGN
  Intel/IMPI HDF5 stack:
  - HDF5 tools resolved from
    `/ds/projects/agn/libraries/hdf5p/1.12.1-impi/bin`
  - final `data.0011.dbl.h5` size: `67318639276` bytes
  - final `data.0051.flt.h5` size: `44890581676` bytes
  - both final HDF5 files contain `/vars/{prs,rho,tr1,vx1,vx2,vx3}` with shape
    `{1014, 960, 960}`
  - scalar reads succeeded for `rho`, `vx1`, and `tr1` from both final files
  - final XMF sidecars reference `<Time Value="1.533007e+04"/>` and the
    matching final HDF5 datasets
  - final particle file `particles.5000.dbl` reports `196732` particles,
    `time = 1.533006968940e+04`, and `stepNumber = 49253`
  - detailed note:
    `docs/exchange/logs/2026-06-07-c-hi-fullgrid-agn-impi-r9-prod64-integrity.md`
- Compact quick-look extraction completed on 2026-06-07:
  - PBS job: `697386.kunanyi-ohpc`
  - job name: `c_hi_final_ql`
  - result: `Exit_status = 0`
  - walltime used: `00:04:34`
  - peak memory: `3771068kb`
  - request: `select=1:ncpus=1:mpiprocs=1:mem=32gb`, `walltime=01:00:00`
  - input:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/data.0051.flt.h5`
  - timestep: `Timestep_51`
  - compact output directory:
    `/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-quicklook`
  - compact archive fetched locally:
    `build/science/kunanyi_stage_2026-06-07/c_hi_fullgrid_final_quicklook_697386_compact_2026-06-07.tar.gz`
  - archive SHA-256:
    `26f8ab57e4f8e3913bc629abb391f699c75b45296d474fe2c411736a0b71098c`
  - report:
    `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.md`
  - PDF:
    `docs/science/c_hi_fullgrid_final_quicklook_2026-06-07.pdf`
  - assets:
    `docs/science/assets/c_hi_fullgrid_final_quicklook_2026-06-07/`
  - detailed note:
    `docs/exchange/logs/2026-06-07-c-hi-fullgrid-final-quicklook-complete.md`
- Full-grid final particle-HDF5 feasibility preflight completed on 2026-06-08:
  - PBS job: `697639.kunanyi-ohpc`
  - job name: `c_hi_ph5_pf`
  - result: `Exit_status=0`
  - walltime used: `00:08:13`
  - peak memory: `188228kb`
  - CPU time: `00:00:08`
  - request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`, `walltime=00:30:00`
  - wrapper:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight.pbs`
  - estimator:
    `/u/bwbrook/codex_kunanyi/particle_loss_runtime/estimate_particle_hdf5_feasibility.py`
  - input run output directory:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs`
  - compact output directory:
    `/scratch/bwbrook/xray_cavities_analysis/2026-06-07-c-hi-fullgrid-final-particle-hdf5-preflight`
  - summary archive:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_hdf5_preflight_2026-06-07.tar.gz`
  - local helper commit:
    `bab5037 Add C-HI particle cache feasibility preflight`
  - staging note: the Mac-origin tar extraction on Kunanyi printed harmless
    `LIBARCHIVE.xattr.com.apple.provenance` warnings before `qsub` succeeded.
  - final particle output count: `5001`
  - final particle count: `196732`
  - particle field count: `13`
  - total field width: `15` scalar-field equivalents
  - dense raw float64 matrix estimate: `109.9545581638813 GiB`
  - saved float32 matrix estimate: `54.97727908194065 GiB`
  - conservative peak-memory estimate: `1099.545581638813 GiB`
  - recommendation:
    `DO_NOT_BUILD_FULL_HISTORY_CACHE_WITH_CURRENT_APPROACH`
  - detailed note:
    `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-hdf5-preflight-complete.md`
- Endpoint-only final particle summary completed on 2026-06-08:
  - PBS job: `697643.kunanyi-ohpc`
  - job name: `c_hi_pend_sum`
  - result: `Exit_status = 0`
  - walltime used: `00:00:39`
  - CPU time: `00:00:02`
  - peak memory: `9444kb`
  - peak virtual memory: `367032kb`
  - request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`,
    `walltime=00:30:00`
  - stderr was empty
  - staged remote script:
    `/u/bwbrook/codex_kunanyi/pes.py`
  - staged remote wrapper:
    `/u/bwbrook/codex_kunanyi/pend.pbs`
  - input particle file:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs/particles.5000.dbl`
  - compact output directory:
    `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-endpoint-summary`
  - summary archive:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.tar.gz`
  - archive SHA-256:
    `a25a805858a438f56369fe4d3690c31bdd358efb0082f73c3d5e51b0633e35e1`
  - final particle count: `196732`
  - endpoint time: `50.00000000000777 Myr`
  - position envelope:
    `x=-29.695625916316235..30.132441460503376 kpc`,
    `y=-32.27023110544345..30.062788186588232 kpc`,
    `z=-215.6060699853556..216.06201669846072 kpc`
  - lobe particle split:
    `97451` negative-z particles and `99281` positive-z particles
  - report:
    `docs/science/c_hi_fullgrid_final_particle_endpoint_summary_2026-06-08.md`
  - detailed note:
    `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-endpoint-summary.md`
- Sparse-window final particle trajectory extraction completed on 2026-06-08:
  - PBS job: `697644.kunanyi-ohpc`
  - job name: `c_hi_psw_fin`
  - result: `Exit_status = 0`
  - walltime used: `00:01:04`
  - CPU time: `00:00:13`
  - peak memory: `92200kb`
  - peak virtual memory: `684996kb`
  - request: `select=1:ncpus=1:mpiprocs=1:mem=8gb`,
    `walltime=00:30:00`
  - stderr was empty
  - staged remote script:
    `/u/bwbrook/codex_kunanyi/psw.py`
  - staged remote wrapper:
    `/u/bwbrook/codex_kunanyi/psw.pbs`
  - local script:
    `scripts/science/pluto_particle_sparse_window.py`
  - input particle directory:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-06-c-hi-fullgrid-agn-impi-r9-prod64/C-HI/particles/problem/outputs`
  - window:
    target `5000`, start `4950`, end `5000`, stride `5`
  - tracer threshold: `0.005`
  - target candidates: `195558`
  - selected IDs: `20000`
  - trajectory rows: `218909`
  - compact output directory:
    `/scratch/bwbrook/xray_cavities_analysis/2026-06-08-c-hi-fullgrid-final-particle-sparse-window`
  - summary archive:
    `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.tar.gz`
  - archive SHA-256:
    `9894f2dfc6cae5b76257b1c5b66b9438fdc25424d66d43ea68df1b2dbc80dc62`
  - report:
    `docs/science/c_hi_fullgrid_final_particle_sparse_window_2026-06-08.md`
  - detailed note:
    `docs/exchange/logs/2026-06-08-c-hi-fullgrid-final-particle-sparse-window.md`
- Next action: connect the sparse trajectory product to particle-loss/radio
  calculations for the final output. Do not return to a blind dense
  all-history `plutokore.load_all_particles()` particle-HDF5 cache over all
  `5001` particle outputs.
- Patrick's 2026-06-05 troubleshooting reply is now incorporated into the
  decision tree:
  - keep running the node-count restart ladder;
  - verify the restart HDF5 file size/datasets/shape;
  - confirm `HDF5_COMPRESSION` is disabled and no
    `> HDF5 compression enabled` banner appears;
  - inspect PLUTO/stdout/stderr logs for hints;
  - if the ladder identifies a failure threshold, add targeted print logging in
    `jet-setup/src/hdf5_io.c` restart logic to narrow the exact stuck call;
  - if scratch/NFS remains implicated, try a bounded restart from `/u/bwbrook/`
    using only the final `.dbl.h5`, final particle file, and `*.out` catalogues.
- Quick follow-up checks on 2026-06-05 already cover the first compression/HDF5
  items:
  - source restart file:
    `/scratch/bwbrook/xray_cavities_runs/2026-06-01-c-hi-fullgrid-agn-impi-fresh/C-HI/particles/problem/outputs/data.0009.dbl.h5`
  - `ls -lh` size: `63G`; final particle file
    `particles.4277.dbl` size: `20M`
  - AGN `h5ls -r` found `/Timestep_9/vars/{prs,rho,tr1,vx1,vx2,vx3}` all with
    shape `{1014, 960, 960}`
  - AGN `h5dump` scalar read of `/Timestep_9/vars/rho[0,0,0]` returned
    `0.00106042`
  - sampled rank-0 logs from the fresh run and green 8/16/32-node ladder rungs
    had no `HDF5 compression enabled` banner
  - local and remote source/config searches found no active
    `HDF5_COMPRESSION` hit; the only local hit was the banner print site in
    `/Users/bwbrook/git/utas-agn/jet-setup/src/hdf5_io.c`

Latest full-grid `C-HI` retry diagnosis on 2026-05-22:

- Retry job `692504.kunanyi-ohpc` finished after the full `8` hour walltime:
  - `Exit_status = 271`
  - `resources_used.walltime = 08:00:52`
  - PBS stderr: `job killed: walltime 28842 exceeded limit 28800`
- The retry did use the intended restart and transport settings:
  - `RUN_KIND=h5_restart_0`
  - `RUN_ARGS=-i pluto.ini -e environment.ini -maxtime 3.5 -h5restart 0`
  - `OMPI_MCA_pml=ob1`
  - `OMPI_MCA_btl=self,vader,tcp`
- It made no useful simulation progress beyond the existing initial output:
  - `dbl.h5.out` still contains only output `0`
  - `flt.h5.out` still contains only output `0`
  - only `data.0000.dbl.h5`, `data.0000.flt.h5`, and
    `particles.0000.dbl` exist
- Interpretation: forcing OB1/TCP avoided the previous UCX UD timeout
  signature but is not a viable `80` node production transport path for this
  full-grid job; it stalled or progressed too slowly and was killed by PBS
  walltime.
- The remote marker directory showed a misleading `DONE` marker after the
  PBS walltime kill. The production template has now been patched locally so
  future non-zero `mpirun` exits and TERM/INT signals write `FAILED` and
  remove stale `DONE` markers.
- Recommended next move: do not rerun the `80` node full-grid case with plain
  TCP. Ask TPAC about the UCX `UD endpoint ... unhandled timeout error` from
  job `692369`, and test a smaller transport ladder or a UCX setting that
  avoids UD without falling all the way back to TCP.

Previous full-grid `C-HI` retry launch on 2026-05-21:

- The first 80-node startup job, `692369.kunanyi-ohpc`, failed after PLUTO
  initialization and initial HDF5 writes because UCX/OpenMPI aborted with
  `UD endpoint ... unhandled timeout error` during MPI collectives. This is
  recorded in
  `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`.
- A retry wrapper was prepared and submitted:
  - PBS job: `692504.kunanyi-ohpc`
  - PBS name: `c_hi_fg_retry`
  - Initial state after submission: `Q` on queue `normal`
  - Follow-up `qstat` at `2026-05-21 16:15` showed:
    `comment = Not Running: Not enough free nodes available`
  - Request:
    - `select=80:ncpus=28:mpiprocs=28`
    - `walltime=08:00:00`
    - `PLUTO_MAXTIME_HOURS=3.5`
    - `RESTART_POLICY=auto`
  - It reuses the existing run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
  - It should restart from `data.0000.dbl.h5` via the existing `dbl.h5.out`
    catalogue rather than deleting the previous startup output.
  - It exports OpenMPI MCA settings to avoid the UCX path that failed:
    - `OMPI_MCA_pml=ob1`
    - `OMPI_MCA_btl=self,vader,tcp`
    - `OMPI_MCA_btl_tcp_if_exclude=lo`
    - `OMPI_MCA_oob_tcp_if_exclude=lo`
- Remote files staged for the retry:
  - `/u/bwbrook/codex_kunanyi/jet_setup_production_template_latest.pbs`
  - `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.pbs`
- Local launch helper:
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_retry_ob1_tcp.sh`
- Expected next action: after the PBS email lands, inspect:
  - `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.out`
  - `/u/bwbrook/codex_kunanyi/c_hi_fullgrid_startup_retry_ob1_tcp.err`
  - `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/markers/`
  - `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup/C-HI/particles/problem/outputs/`
- Home-network access update:
  - direct MacBook TCP/22 to `<tpac-host>` still hangs from Barry's
    home network
  - MacBook -> Tailscale `utas-ubuntu` / `deep-server` -> TPAC jumpbox ->
    `kunanyi` works
  - local Mac SSH aliases now include `tpac-jumpbox-via-deep` and
    `kunanyi-via-deep`
  - `scripts/kunanyi/run_on_kunanyi.sh` works from home with:
    `TPAC_JUMPBOX_ALIAS=tpac-jumpbox-via-deep TPAC_CLUSTER_HOST=kunanyi`
  - `scripts/kunanyi/copy_to_kunanyi.sh` should use
    `TPAC_SCP_HOST=kunanyi-via-deep` for uploads over the same route
  - a probe at `2026-05-21 23:09 AEST` showed `692504.kunanyi-ohpc` running
    with `resources_used.walltime = 00:28:27`

Previous full-grid `C-HI` startup/checkpoint launch on 2026-05-20:

- The prepared full-grid startup/checkpoint packet was staged to `kunanyi`
  and submitted from campus/`eduroam`.
- PBS job: `692369.kunanyi-ohpc`
- PBS name: `c_hi_fg_start`
- Initial state after submission: `Q` on queue `normal`
- Remote validation before `qsub` passed:
  - `REMOTE_RENDER_VALIDATION_OK=1`
  - `NPARTICLES=32.0`
- Request:
  - `select=80:ncpus=28:mpiprocs=28`
  - `walltime=04:00:00`
  - `PLUTO_MAXTIME_HOURS=3.5`
  - `RESTART_POLICY=force-fresh`
- Mail notifications are enabled for `barry.brook@utas.edu.au`.
- Expected next action: wait for the PBS email, then use the job logs and
  output catalogue under
  `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
  to verify build, startup, HDF5 output, restart marker, and `DONE`/`FAILED`
  state.

Prepared full-grid `C-HI` startup packet on 2026-05-19:

- Patrick-agent and Stas-agent have both reviewed the next full-grid startup
  gate. The explicit decision is `GO WITH CHANGES`.
- The required pre-launch change has been implemented: `Nparticles` now uses
  `32` particles per injection event instead of `16`.
- The rendered and validated launch snapshot is recorded under:
  `docs/science/assets/c_hi_fullgrid_startup_2026-05-19/`
- The ignored runnable bundle is expected at:
  `build/science/c_hi_fullgrid_startup_2026-05-19/`
- The PBS wrapper for the first full-grid startup/checkpoint gate is:
  `scripts/kunanyi/c_hi_fullgrid_startup_checkpoint.pbs`
- The one-command stage/submit helper is:
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh`
- The intended first launch is deliberately bounded, not the full 48-hour
  science segment:
  - `select=80:ncpus=28:mpiprocs=28`
  - `walltime=04:00:00`
  - `PLUTO_MAXTIME_HOURS=3.5`
  - `RESTART_POLICY=force-fresh`
  - run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-05-19-c-hi-fullgrid-startup`
- The launch command used on campus/`eduroam` was:
  `scripts/kunanyi/stage_and_submit_c_hi_fullgrid_startup.sh`

- Soft follow-up only: Stas-agent asked Patrick-agent to confirm that
  `dbl.h5` outputs five times less frequently than `flt.h5` is acceptable.
  Patrick-agent had already stated that no HDF5 restart policy change was
  requested, so this is not being treated as a blocker for the startup gate.

Latest agent-comms update on 2026-05-19:

- pulled Stas-agent's first feedback commit:
  - `d46912c` (`Update Stas agent feedback`)
  - Stas-agent is now active in `agent_comms/agents/stas-agent.md`
  - Stas-agent responded in
    `agent_comms/threads/2026-05-11-c-hi-science-interpretation.md`
- Stas-agent's reduced-grid diagnostic requests are:
  - add x-z midplane slices for density, pressure, tracer, and z-velocity
  - use/supplement cavity energetics with `2.5pV` for non-relativistic plasma
  - add tracer-energy/injected-energy and `2.5pV`/injected-energy time-series
    ratio plots
  - include setup blocks at the start of analysis summaries
  - add density along the jet axis for the same snapshots
- Barry asked for a clear Stas-agent green-light request while Patrick was
  travelling. The request is appended to
  `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md`.
- Stas-agent responded `GO WITH CHANGES`; the required `Nparticles = 32`
  change has been implemented and the startup/checkpoint gate has been
  submitted.
- Remaining open question:
  - `Q-009`: Patrick-agent should confirm Stas-agent's non-blocking question
    about whether `dbl.h5` cadence every `5 Myr` remains acceptable relative
    to `flt.h5` every `1 Myr`.

Latest MacBook/kunanyi update on 2026-05-13:

- the `8` node `C-HI` mini-production continuation completed cleanly:
  - PBS job: `691422.kunanyi-ohpc` (`c_hi_8mini`)
  - exit status: `0`
  - request: `select=8:ncpus=28:mpiprocs=28`
  - ranks: `224`
  - walltime used: `14:45:00`
  - restart mode: `-h5restart 7`
  - PLUTO guard: `-maxtime 14.5`
  - start checkpoint: `10.278362 Myr`
  - final regular output: `data.0039.flt.h5`, `33.374180 Myr`
  - final restart-capable checkpoint: `data.0012.dbl.h5`, `33.374180 Myr`
  - particle files now extend through `particles.3343.dbl`
  - output volume after run: `217G`
- compact run metadata was fetched locally:
  `build/science/kunanyi_stage_2026-05-08/c_hi_8mini_691422_compact_2026-05-13.tar.gz`
- meeting-facing update:
  - `docs/science/c_hi_8node_mini_production_2026-05-13.md`
  - `docs/science/c_hi_8node_mini_production_2026-05-13.pdf`
- meeting-3 configuration audit now exists and should be treated as the next
  pre-production review packet:
  - `docs/science/c_hi_run_configuration_audit_2026-05-13.md`
  - `docs/science/c_hi_run_configuration_audit_2026-05-13.pdf`
  - generated assets under
    `docs/science/assets/c_hi_run_configuration_audit_2026-05-13/`
  - key finding: `691422.kunanyi-ohpc` used the reduced
    `kunanyi_single_node_250` grid (`404 x 404 x 452`, central `0.05 kpc`,
    coarse outer cells), so it is a good rehearsal lane but not the final
    production grid
- `docs/science/c_hi_8node_mini_production_2026-05-13.md` was updated with a
  run-spec block covering grid, parameters, output file sizes, modules, and
  rank layout
- `agent_comms/threads/2026-05-13-c-hi-grid-config-review.md` asks Patrick's
  and Stas' agents to review the concrete run spec and final-grid assumptions
  before full-grid production
- `scripts/kunanyi/jet_setup_production_template.pbs` now records more explicit
  source provenance for future jobs: git root/branch/head/status when
  available, missing-git state when not, and PLUTO binary SHA-256
- `scripts/kunanyi/c_hi_to33_particle_hdf5.pbs` now requests `48gb` memory for
  future reruns, matching the observed memory scale of the completed
  particle-HDF5 rebuild more honestly than the temporary `16gb` scheduler-fit
  request
- follow-up diagnostic dependency chain submitted:
  - `691762.kunanyi-ohpc` (`c_hi_ph5_33`): completed successfully; rebuilt
    particle HDF5 through roughly `33 Myr`
  - `691763.kunanyi-ohpc` (`c_hi_s33`): running as of
    `2026-05-13 14:52 AEST`; extracts truth/cavity/XRAiSE/radio scalar series
    for outputs `15 20 25 30 35 39`
- latest exchange notes:
  - `docs/exchange/logs/2026-05-13-c-hi-8mini-complete.md`
  - `docs/exchange/logs/2026-05-13-c-hi-run-config-audit.md`

Previous MacBook/kunanyi update on 2026-05-12:

- the long-queued `80` node allocation smoke was cancelled after more than a
  day in queue:
  - cancelled PBS job: `690703.kunanyi-ohpc` (`c_hi_80alloc`)
  - reason: supervisor advice and meeting-driven need for a runnable
    mini-production segment before 2026-05-13 13:00 AEST
- several scheduler-fit shapes were tried and cancelled after PBS reported
  insufficient CPU resources:
  - `691414.kunanyi-ohpc`: `25` full nodes, `700` ranks
  - `691416.kunanyi-ohpc`: `23` full nodes, `644` ranks
  - `691417.kunanyi-ohpc`: `25` partial nodes, `500` ranks
  - `691418.kunanyi-ohpc`: `16` full nodes, `448` ranks
- live mini-production continuation:
  - PBS job: `691422.kunanyi-ohpc` (`c_hi_8mini`)
  - request: `select=8:ncpus=28:mpiprocs=28`
  - ranks: `224`
  - walltime: `15:00:00`
  - PLUTO guard: `-maxtime 14.5`
  - start status: running from `Tue May 12 20:31 AEST 2026`
  - latest poll in this handoff: still running at `20:39 AEST`, walltime
    `00:07:21`, with `224` CPUs assigned
  - purpose: continue the reduced-grid particles-enabled `C-HI` case from the
    latest HDF5 restart checkpoint and produce a meeting-ready mini-production
    segment
  - expected notification: PBS begin/end/abort email to
    `barry.brook@utas.edu.au`
- added runnable mini-production PBS wrappers:
  - `scripts/kunanyi/c_hi_25node_mini_production.pbs`
  - `scripts/kunanyi/c_hi_25node_partial_mini_production.pbs`
  - `scripts/kunanyi/c_hi_16node_mini_production.pbs`
  - `scripts/kunanyi/c_hi_8node_mini_production.pbs`
  - `scripts/kunanyi/c_hi_23node_mini_production.pbs`
- launch note:
  `docs/exchange/logs/2026-05-12-c-hi-mini-production-pivot.md`

Previous MacBook/kunanyi update on 2026-05-11:

- repo-mediated multi-agent collaboration has been scaffolded under
  `agent_comms/`
  - purpose: asynchronous communication among Barry's, Stas', and Patrick's
    Codex agents through GitHub pull/edit/commit/push workflows
  - first reads:
    `agent_comms/README.md`, `agent_comms/AGENTS.md`, and
    `agent_comms/requests/open_questions.md`
  - initial active threads cover onboarding/current state, production-scale
    allocation, and `C-HI` science interpretation
  - exchange note:
    `docs/exchange/logs/2026-05-11-agent-comms-scaffold.md`
- production-scale allocation testing started, later superseded by the
  2026-05-12 mini-production pivot above:
  - PBS job `690703.kunanyi-ohpc` (`c_hi_80alloc`) was queued on `normal`
  - requested allocation: `select=80:ncpus=28:mpiprocs=28`
  - requested MPI ranks: `2240`
  - walltime: `00:20:00`
  - purpose: validate production-scale PBS nodefile, OpenMPI hostfile launch,
    and collective HDF5 write without running a PLUTO science segment
  - initial scheduler comment:
    `Not Running: Not enough free nodes available`
  - expected email notifications: begin, abort, and end (`#PBS -m abe`)
  - launch note:
    `docs/exchange/logs/2026-05-11-c-hi-80node-allocation-smoke.md`
- bounded continuation job `690650.kunanyi-ohpc` (`c_hi_to10`) completed
  successfully with `Exit_status = 0`
- the run used `select=2:ncpus=28:mpiprocs=28`, `56` MPI ranks, and consumed
  `06:44:13` walltime
- output volume is now about `95G`
- regular `flt.h5` outputs now cover the intended `6-10 Myr` block:
  - output `10`: `5.999728 Myr`
  - output `11`: `6.998996 Myr`
  - output `12`: `7.999292 Myr`
  - output `13`: `8.999584 Myr`
  - output `14`: `9.999876 Myr`
  - output `15`: `10.278362 Myr`, walltime-stop output
- restart-capable `dbl.h5` outputs now include:
  - output `6`: `9.999876 Myr`
  - output `7`: `10.278362 Myr`
- for the next continuation, use `-h5restart 7` to continue from the final
  walltime-stop checkpoint, or `-h5restart 6` to deliberately restart from the
  nominal `10 Myr` checkpoint
- direct MacBook jumpbox access worked again after Barry refreshed the TPAC
  Open OnDemand SSH window
- follow-up diagnostics were submitted as a dependency chain:
  - `690680.kunanyi-ohpc` (`c_hi_ph5_10`): rebuild particle HDF5 through the
    new particle outputs
  - `690681.kunanyi-ohpc` (`c_hi_s10`): afterok dependency on `690680`, compact
    truth/cavity/XRAiSE/radio scalar series for outputs `10 11 12 13 14`
- both follow-up diagnostics completed successfully with `Exit_status = 0`
- the particle HDF5 cache now spans `0-10.278 Myr`, with `1033` particle times
  and a full remote HDF5 size of `423 MB`
- compact through-10-Myr diagnostics are now stored under:
  - `docs/science/assets/c_hi_to10_snapshot_series_2026-05-11/`
  - `docs/science/assets/c_hi_to10_particle_hdf5_2026-05-11/`
  - `docs/science/assets/c_hi_to10_combined_series_2026-05-11/`
- at the nominal `10 Myr` output:
  - Level 2 tracer-lobe bipolar volume: `3.6574e4 kpc^3`
  - Level 2 tracer-lobe bipolar energy: `3.4309e59 erg`
  - bipolar `4pV`: `6.8561e59 erg`
  - tracer z extent: `47.71 kpc`
  - lossy `150 MHz` radio luminosity proxy: `7.7444e27 W Hz^-1`
  - radio lobe balance, `+z / -z`: `0.977`
- the latest through-10-Myr report and PDF are:
  - `docs/science/c_hi_to10_snapshot_series_2026-05-11.md`
  - `docs/science/c_hi_to10_snapshot_series_2026-05-11.pdf`
- latest exchange notes:
  - `docs/exchange/logs/2026-05-11-agent-comms-scaffold.md`
  - `docs/exchange/logs/2026-05-11-c-hi-80node-allocation-smoke.md`
  - `docs/exchange/logs/2026-05-10-c-hi-to10-continuation-launch.md`
  - `docs/exchange/logs/2026-05-11-c-hi-to10-complete-and-diagnostics.md`
- the meeting transcript gives the relevant full-grid production scale:
  Stas described a standard run as about `80 nodes x 28 cores per node`, with
  about three `48 h` chunks to reach `100 Myr`; the current 2-node jobs should
  therefore be read as reduced-grid shakedown/continuation runs, not as the
  intended final full-grid allocation
- the particles-enabled high-power cluster case, `C-HI`, has now passed the
  early diagnostic run gate on `kunanyi`
- continuation job `690560.kunanyi-ohpc` (`c_hi_2node_to5`) completed with
  `Exit_status = 0`
- resources were `select=2:ncpus=28:mpiprocs=28` on nodes `n194` and `n029`
  for `56` MPI ranks
- the run restarted from `data.0003.dbl.h5` with `-h5restart 3` and stopped
  safely with Patrick's `-maxtime` pattern
- regular science-cadence `flt.h5` outputs now exist at about `1`, `2`, `3`,
  `4`, and `5 Myr`
- restart-capable `dbl.h5` outputs now exist through the nominal `5 Myr`
  checkpoint plus a walltime-forced `5.455 Myr` checkpoint
- quick-look job `690583.kunanyi-ohpc` extracted the nominal 5 Myr output,
  `data.0008.flt.h5`, successfully
- default-threshold tracer extent at `4.9994 Myr` is about `+/-9.46 kpc` in
  `x/y` and `+/-33.0 kpc` in `z`, comfortably inside the `X3 = +/-250 kpc`
  domain
- first truth smoke job `690585.kunanyi-ohpc` also completed with
  `Exit_status = 0` against the same `data.0008.flt.h5` snapshot
- Level 1 elapsed injected energy at `4.9994 Myr` is `1.5777e59 erg`
  one-sided and `3.1554e59 erg` bipolar
- Level 2 default tracer-mask (`tracer > 5e-3`) bipolar quantities are
  `10791.8 kpc^3`, `9.6642e58 erg` thermal, `8.7948e58 erg` kinetic, and
  `1.8459e59 erg` total
- the first aligned observable smoke job, `690612.kunanyi-ohpc`
  (`c_hi_obs5`), completed against the same 5 Myr target:
  - grid file: `data.0008.flt.h5`
  - grid time: `4.9994348189788402 Myr`
  - particle file: `particles.0503.dbl`
  - particle time: `4.9994348189790641 Myr`
  - view: `0 deg`
- this observable product is a bridge smoke, not the final full
  GRAiLE/XRAiSE pipeline: it ports the XRAiSE grid bremsstrahlung expression
  before APEC/Gaunt correction and a lossless `plutokore` radio
  pressure/tracer scaling because `kunanyi` does not yet have the required
  Python analysis stack loaded
- bridge observable metrics:
  - particles loaded: `16056`
  - raw 1 keV X-ray map max: `1.4382e6 mJy sr^-1`
  - 150 MHz radio proxy max: `6.6204e15 mJy sr^-1`
  - 150 MHz radio luminosity proxy: `5.4149e26 W Hz^-1`
- the first cavity-protocol stub job, `690620.kunanyi-ohpc`
  (`c_hi_cavity5`), completed against the same 5 Myr target:
  - one tracer-defined ellipsoid per lobe, threshold `tracer > 5e-3`
  - local ambient pressure/density from a same-side ellipsoidal shell with
    `tracer <= 1e-3`
  - fitted semi-axes: `9.465 x 9.465 x 16.510 kpc` for both lobes
  - local ambient pressure: `1.7422e-10 dyn cm^-2`
  - `pV`: `3.1709e58 erg` per lobe
  - `4pV`: `1.2684e59 erg` per lobe
  - sound age: `13.45 Myr` per lobe
- the cavity buoyancy/refill ages are recorded only as provisional smoke
  values because their gravity term is currently a hydrostatic shell proxy
- the first XRAiSE grid-thermal smoke job, `690624.kunanyi-ohpc`
  (`c_hi_xrgrid5`), completed against the same 5 Myr target:
  - runtime: `Anaconda3/2024.02-1` on a `kunanyi` compute node
  - supplied assets used: `xraise.py`, `apec_corrections.txt`, and
    `gaunt_lut_2d.npz`
  - raw pre-correction 1 keV map max: `1.4382e6 mJy sr^-1`
  - APEC/Gaunt-corrected 1 keV map max: `2.8783e6 mJy sr^-1`
  - correction-ratio range: `1.3273` to `2.4404`
- this supersedes the earlier C bridge for the grid-thermal X-ray map
- the particle-loss-aware GRAiLE/XRAiSE runtime gate is also complete:
  - particle HDF5 preprocessing job: `690635.kunanyi-ohpc` (`c_hi_part_h5`)
  - particle-loss smoke job: `690636.kunanyi-ohpc` (`c_hi_ploss5`)
  - staged runtime: `plutokore` plus tiny import shims under
    `/u/bwbrook/codex_kunanyi/particle_loss_runtime`
  - processed particle HDF5:
    `/scratch/bwbrook/xray_cavities_analysis/2026-05-10-c-hi-particles-hdf5/C-HI.particles.hdf5`
  - particle IDs represented: `17516`
  - particle times represented: `550`, spanning `0.0` to `5.4550 Myr`
  - full-loss emissivity smoke at grid output `8`, particle output `503`:
    `17516` finite values, `13144` positive values, `0` NaNs, max `4.2874`
- the first particle-loss-aware radio/lobe smoke is complete:
  - radio smoke job: `690641.kunanyi-ohpc` (`c_hi_radio5`)
  - frequency: `150 MHz`
  - selected particles: `16054`
  - lossy radio map max: `3.6847e15 mJy sr^-1`
  - bipolar lossy luminosity proxy: `6.3450e27 W Hz^-1`
  - negative-z and positive-z lobe luminosity proxies are closely matched:
    `3.1963e27` and `3.1487e27 W Hz^-1`
- the aligned 5 Myr smoke package now has truth, cavity, XRAiSE grid-thermal,
  particle-loss, and radio/lobe products for the same snapshot/view
- the aligned comparison and deterministic particle-radio gate is complete:
  - comparison assets:
    `docs/science/assets/c_hi_aligned_comparison_2026-05-10/`
  - determinism job: `690644.kunanyi-ohpc` (`c_hi_rdet5`)
  - rerun comparison: `NUMBA_NUM_THREADS=1` versus `4`
  - result: exact hashes matched, arrays allclose, max array relative
    difference `0.0`, max scalar-metric relative difference `0.0`
  - determinism assets:
    `docs/science/assets/c_hi_particle_radio_determinism_2026-05-10/`
- the aligned early-snapshot scalar-series gate is complete:
  - PBS job: `690646.kunanyi-ohpc` (`c_hi_eseries`)
  - regular grid outputs processed: `2`, `4`, `6`, `7`, and `8`
    (`0.9990`, `1.9996`, `2.9999`, `3.9991`, and `4.9994 Myr`)
  - compact assets:
    `docs/science/assets/c_hi_early_snapshot_series_2026-05-10/`
  - tracer volume grows from `539.62` to `10791.77 kpc^3`
  - tracer z extent grows from `10.08` to `33.04 kpc`
  - by 5 Myr, Level 2 tracer-lobe energy is about `0.585` of elapsed
    bipolar injection, and bipolar `4pV` is about `0.804` of elapsed bipolar
    injection
  - radio lobe balance stays near unity, ranging from `0.9720` to `1.0579`
- the latest report and PDF are:
  - `docs/science/c_hi_to5_quicklook_2026-05-10.md`
  - `docs/science/c_hi_to5_quicklook_2026-05-10.pdf`
  - `docs/science/c_hi_observable_smoke_2026-05-10.md`
  - `docs/science/c_hi_observable_smoke_2026-05-10.pdf`
  - `docs/science/c_hi_cavity_stub_2026-05-10.md`
  - `docs/science/c_hi_cavity_stub_2026-05-10.pdf`
  - `docs/science/c_hi_xraise_grid_smoke_2026-05-10.md`
  - `docs/science/c_hi_xraise_grid_smoke_2026-05-10.pdf`
  - `docs/science/c_hi_particle_loss_smoke_2026-05-10.md`
  - `docs/science/c_hi_particle_loss_smoke_2026-05-10.pdf`
  - `docs/science/c_hi_particle_radio_smoke_2026-05-10.md`
  - `docs/science/c_hi_particle_radio_smoke_2026-05-10.pdf`
  - `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.md`
  - `docs/science/c_hi_aligned_comparison_and_determinism_2026-05-10.pdf`
  - `docs/science/c_hi_early_snapshot_series_2026-05-10.md`
  - `docs/science/c_hi_early_snapshot_series_2026-05-10.pdf`
  - `docs/science/c_hi_to10_snapshot_series_2026-05-11.md`
  - `docs/science/c_hi_to10_snapshot_series_2026-05-11.pdf`
- latest exchange note:
  `docs/exchange/logs/2026-05-11-c-hi-to10-complete-and-diagnostics.md`
- this next-step note was superseded on 2026-05-12: `690703.kunanyi-ohpc` was
  cancelled, and the active job became the `8` node mini-production
  continuation `691422.kunanyi-ohpc`

Update on 2026-04-24:

- Barry is moving active work to a MacBook for a one-week trip.
- A new primary cross-machine handover has been added at
  `docs/READ_THIS_FIRST.md`.
- The current planning package consists of:
  - `docs/Honours_Research_Plan.md`
  - `docs/Honours_Research_Meeting_Brief.md`
  - `docs/Honours_Research_Meeting_Slides.qmd`
- The next MacBook-side task is to turn the revised three-case plan into a
  concrete pilot/comparison specification and begin execution-path smoke tests,
  especially on resized `nectar-vm` and `kunanyi`.
- When the trip ends, the MacBook agent should write a return handoff under
  `docs/exchange/logs/` before WSL resumes the work.

Follow-up on the same day:

- `nectar-vm` was successfully pulled forward to the exchange-hub commit
- `deep-server` could not `git pull` from GitHub because its GitHub SSH auth is
  not configured yet
- to keep continuity intact anyway, the exchange docs were synced onto
  `deep-server` directly from WSL
- after the final stage-4 checkpoint, `nectar-vm` also pulled the updated
  `plutokore` commit cleanly
- `deep-server` ran the stage-4 capstone successfully, but a later
  `plutokore` GitLab pull from that machine failed on SSH auth, so its local
  `plutokore` checkout may remain dirty even though the synced file content used
  for this task is current

MacBook follow-up after Stas' 2026-04-24 feedback:

- Stas' plan feedback was added at
  `docs/Honours_research_plan_feedback_SS_260424.txt`
- `docs/Honours_Research_Plan.md` was revised so that:
  - jet power and environment are the primary variables
  - source age and viewing angle are secondary sampling axes
  - radio synchrotron products are part of the core project
  - Step 11 is mandatory rather than optional
  - the minimum comparison suite is now three simulations:
    low-power cluster, high-power cluster, and low-power group
  - the fully relativistic `0.98c` branch is explicitly out of current scope
- the MacBook has local UTAS AGN mirrors under `/Users/bwbrook/git/utas-agn`
  for context and light editing, but simulation work should still be offloaded
  to resized `nectar-vm` and then `kunanyi`
- MacBook GitLab SSH auth has been checked and now works

MacBook follow-up after Patrick's jet-assignment materials:

- Patrick supplied the missing official Martin Krause jet assignment plus
  companion jet-theory slides, unpacked locally under ignored
  `docs/jet-theory/`
- the prior "Krause-style" capstone remains a useful pure-Python analysis
  precursor, but the official worksheet is now the canonical next warm-up task
- the immediate recommended execution path is:
  - run PLUTO `Test_Problems/HD/Jet` on resized `nectar-vm`
  - use external Mach `20`, pressure equilibrium, and two resolutions
    (`10` and `20` cells per beam radius)
  - produce the worksheet's density snapshots and shock/instability/backflow
    diagnostics
  - then repeat the diagnostic exercise as a small full-3D Cartesian
    `jet-setup` run before returning to the three-case science suite
- details are in
  `docs/exchange/logs/2026-04-30-patrick-jet-assignment.md`

MacBook/Nectar follow-up after official assignment execution:

- `nectar-vm` was resized to `c3.3xlarge` and used as the execution host
- Patrick's official PLUTO `HD/Jet` assignment was run at `10` and `20` cells
  per beam radius, with external Mach `20`, pressure equilibrium, and four
  nonzero density snapshots for each resolution
- the resulting report and artifacts are:
  - `docs/onboarding/reports/2026-04-30-official-jet-assignment.qmd`
  - `docs/onboarding/assets/official_jet_assignment_2026-04-30/`
- a tiny full-3D Cartesian `jet-setup` smoke was also run on resized Nectar:
  HD, particles off, King environment, `48 x 48 x 72`, final time `300`
- the resulting report and artifacts are:
  - `docs/onboarding/reports/2026-04-30-jet-setup-tiny-3d-cart.qmd`
  - `docs/onboarding/assets/jet_setup_tiny_3d_cart_2026-04-30/`
- details are in
  `docs/exchange/logs/2026-04-30-nectar-official-jet-and-3d-smoke.md`
- after the run, `nectar-vm` was parked back on `c3.xsmall`

MacBook/kunanyi follow-up:

- TPAC jumpbox access was tested successfully via the Open OnDemand 5-minute
  SSH window
- local SSH aliases now include `tpac-jumpbox` and `kunanyi`
- `ssh kunanyi` via jumpbox lands on `<tpac-host>`
- PBS tools are visible on the login node:
  - `qsub`: `/opt/pbs/bin/qsub`
  - `qstat`: `/opt/pbs/bin/qstat`
- the first clean PBS smoke job completed on compute node `n001.kunanyi`:
  - job id `688913.kunanyi-ohpc`
  - queue `test`
  - scratch workdir `/scratch/bwbrook/codex_smoke`
- details are in:
  - `docs/kunanyi_setup.md`
  - `docs/exchange/logs/2026-04-30-kunanyi-first-pbs-smoke.md`

MacBook/kunanyi follow-up on 2026-05-01:

- targeted module inventory completed successfully via
  `scripts/kunanyi/module_inventory.sh`
- best first PLUTO/HDF5 stack identified as:
  `HDF5/1.14.0-gompi-2023a`
- this stack provides GCC 12.3, OpenMPI 4.1.5, and parallel HDF5 1.14.0
- a PBS compile/run smoke completed on compute node `n001.kunanyi`:
  - job id `688922.kunanyi-ohpc`
  - queue `test`
  - workdir `/scratch/bwbrook/codex_hdf5_probe`
  - compiled with `h5pcc`
  - ran with `mpirun -np 2`
  - created and inspected `mpi_hdf5_smoke.h5`
- next kunanyi step is a tiny PLUTO build/run under PBS using this module stack
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-module-and-hdf5-smoke.md`

Second MacBook/kunanyi follow-up on 2026-05-01:

- no existing UTAS AGN source checkout was found under `/u/bwbrook` or
  `/scratch/bwbrook`
- a clean PLUTO source bundle was transferred through jumpbox to TPAC home and
  unpacked to `/scratch/bwbrook/git/utas-agn/pluto`
- PLUTO's Python 3 `--no-curses` setup path needed a scratch-only
  `raw_input = input` compatibility patch in `Tools/Python/menu.py`
- a tiny PLUTO `HD/Sod` smoke built and ran under PBS:
  - job id `688924.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - run command `mpirun -np 2 ./pluto -i pluto.ini`
  - outputs included `data.0000.dbl`, `data.0001.dbl`, `dbl.out`, `grid.out`,
    and `pluto.0.log`
- next kunanyi step is a tiny official PLUTO `HD/Jet` PBS run
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-sod-smoke.md`

Third MacBook/kunanyi follow-up on 2026-05-01:

- a tiny official PLUTO `HD/Jet` PBS smoke completed successfully:
  - job id `688926.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `16 x 48`, cylindrical 2D
  - `ETA = 10`, external Mach target `20`, PLUTO `MACH = 6.32455532034`
  - run command `mpirun -np 2 ./pluto -i pluto.ini`
  - outputs included `data.0000.dbl`, `data.0001.dbl`, `data.0002.dbl`,
    `dbl.out`, `grid.out`, and `pluto.0.log`
- PBS resource sizing notes were added for single-node and multi-node runs:
  `select=N:ncpus=28:mpiprocs=28`
- next kunanyi rung is either a larger 2D official jet run or the first
  `jet-setup` / tiny 3D smoke path on `kunanyi`
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-jet-smoke.md`

Fourth MacBook/kunanyi follow-up on 2026-05-01:

- a scaled official PLUTO `HD/Jet` 2D PBS smoke completed successfully:
  - job id `688930.kunanyi-ohpc`
  - queue `test`
  - compute node `n001.kunanyi`
  - resources `select=1:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `64 x 192`, cylindrical 2D
  - `ETA = 10`, external Mach target `20`, PLUTO `MACH = 6.32455532034`
  - run command `mpirun -np 8 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:00:21`
  - outputs included `data.0000.dbl` through `data.0004.dbl`, `dbl.out`,
    `grid.out`, and `pluto.0.log`
- next kunanyi rung is the first `jet-setup` / tiny 3D smoke path on one node
- after that, test multi-node parallelisation explicitly
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-pluto-jet-2d-scaled.md`

Fifth MacBook/kunanyi follow-up on 2026-05-01:

- a tiny full-3D Cartesian `jet-setup` PBS smoke completed successfully on one
  `kunanyi` node:
  - job id `688935.kunanyi-ohpc`
  - queue `test`
  - compute node `n010.kunanyi`
  - resources `select=1:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - stack `HDF5/1.14.0-gompi-2023a`
  - makefile architecture `Kunanyi.defs`
  - grid `48 x 48 x 72`, Cartesian 3D
  - King atmosphere, HD, particles off
  - `tstop = 300`
  - run command `mpirun -np 8 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:01:26`, `cput = 00:04:55`, and
    peak memory about `342 MB`
  - outputs included `data.0000.dbl` through `data.0002.dbl`, `dbl.out`,
    `grid.out`, and eight per-rank PLUTO logs
- the first attempt, job `688934.kunanyi-ohpc`, failed because the current
  `jet-setup` `definitions.h` does not define `COMPONENTS`; the PBS script now
  leaves that absent define alone
- next kunanyi rung is an explicit multi-node MPI test
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-jet-setup-tiny-3d-cart.md`

Sixth MacBook/kunanyi follow-up on 2026-05-01:

- PBS email notifications were tested successfully:
  - script `scripts/kunanyi/email_notify_smoke.pbs`
  - job id `688936.kunanyi-ohpc`
  - mail recipient `barry.brook@utas.edu.au`
  - mail points `abe`
  - completed with `Exit_status = 0`
  - Barry confirmed receipt of the PBS completion email
- a two-node `jet-setup` 3D MPI smoke completed successfully:
  - script `scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs`
  - job id `688937.kunanyi-ohpc`
  - queue `test`
  - compute nodes `n010.kunanyi` and `n011.kunanyi`
  - resources `select=2:ncpus=8:mpiprocs=8`, walltime request `00:20:00`
  - `NRANKS` was computed from `PBS_NODEFILE` as `16`
  - run command `mpirun -np 16 ./pluto -i pluto.ini`
  - completed with `Exit_status = 0`
  - PBS accounting reported `walltime = 00:00:54`, `cput = 00:05:40`, and
    peak memory about `617 MB`
  - outputs included `data.0000.dbl` through `data.0002.dbl`, `dbl.out`,
    `grid.out`, and 16 per-rank PLUTO logs
- the core launch pattern for production jobs is now validated:
  `select=N:ncpus=28:mpiprocs=28`, derive ranks from `PBS_NODEFILE`, run with
  `mpirun -np "$NRANKS"`, and use `#PBS -M barry.brook@utas.edu.au` plus
  `#PBS -m ae` for completion/failure notifications
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-email-and-multinode-smoke.md`

Production-prep follow-up on 2026-05-01:

- `kunanyi` is now infrastructure-ready for full jobs once the science cases
  are properly packaged
- `docs/kunanyi_setup.md` now records the remaining preparation passes before
  any serious 48-hour multi-node production run:
  - lock the case specification
  - build a production PBS template
  - add restart/resume handling and `DONE`/`FAILED` markers
  - confirm output volume and data retention/transfer plan
  - run an intermediate-size rehearsal
  - then launch production jobs
- a short collaborator-facing status update was added as:
  - `docs/kunanyi_status_update_2026-05-01.md`
  - `docs/kunanyi_status_update_2026-05-01.pdf`
- details are in:
  - `docs/exchange/logs/2026-05-01-kunanyi-production-prep.md`

Science-package follow-up on 2026-05-02:

- This block is historical. The 2026-05-07 supervisor-meeting-2 follow-up below
  supersedes the `300 Myr` first-run target and hydro-first staging.
- the next science plan has been converted into a frozen three-case spec:
  `docs/science/three_case_spec.md`
- case IDs are now locked as:
  - `C-HI`: Stewart cluster, `JET_PWR = 1e45 erg/s`, `JET_SPD = 0.1`,
    first validation case
  - `C-LO`: Stewart cluster, `JET_PWR = 1e43 erg/s`, `JET_SPD = 0.1`,
    baseline science anchor
  - `G-LO`: Stewart group, `JET_PWR = 1e43 erg/s`, `JET_SPD = 0.1`,
    environment-dependence case
- shared defaults are locked at HD, centered launch,
  `JET_RELATIVISTIC_DENSITY = NO`, `15 deg` primary/secondary opening
  angles, and `300 Myr` active/final time
- the 3 x 3 observable protocol is locked at snapshots `100`, `200`, and
  `300 Myr`, viewed at `0`, `45`, and `90 deg`
- the current asset inventory is recorded in:
  `docs/science/asset_inventory_2026-05-02.md`
- the real Stewart cluster/group environment files are still missing as
  confirmed production assets; the visible tabulated/example files are not to
  be promoted to science inputs unless Stas/Patrick confirm them
- the X-ray/GRAiLE or predecessor-project pipeline remains a named asset gate
- static config scaffolding now exists at:
  `scripts/science/render_three_case_configs.py`
- tabulated-environment inspection scaffolding now exists at:
  `scripts/science/inspect_tabulated_environment.py`
- a production-oriented `kunanyi` template now exists at:
  `scripts/kunanyi/jet_setup_production_template.pbs`
- next science action is asset acquisition and Nectar environment gates, not a
  full `kunanyi` production submission
- details are in:
  - `docs/exchange/logs/2026-05-02-three-case-science-package.md`

Stewart/GRAiLE asset follow-up on 2026-05-05:

- Patrick supplied the missing large environment archive under ignored `env/`
  as `env/environments.zip`; only lightweight/tabulated assets were extracted
- Stas clarified that science runs must use the radially averaged tabulated
  environments, not the full 3D cubes, because spurious grid motion makes the
  full-grid profiles unreliable for energetics
- selected science environment files are now:
  - cluster `002_003`: `env/extracted/environments/tabulated/tabulated_cosmo_002003.csv`
  - group `002_031`: `env/extracted/environments/tabulated/tabulated_cosmo_002031.csv`
- both selected files have `4000` rows, six cgs columns, and radius range
  `0` to `1.697123e24 cm`
- Patrick also supplied old simulation INIs under `env/inis.zip`; these show
  the important conversion
  `1 Myr = 306.601393788 PLUTO code-time units`
- post-meeting correction: `scripts/science/render_three_case_configs.py` now
  renders PLUTO core time controls in code time, while keeping
  `JET_END_TIME` and `JET_ACTIVE_TIME` as physical Myr values
- Patrick supplied GRAiLE/XRAiSE assets under `env/graile-all.zip`; the blocker
  is now porting those scripts from Georgia's absolute paths, not acquiring
  the X-ray assets
- new helper for the immediate Nectar gate:
  `scripts/science/render_stewart_environment_gate_tests.py`
- next action is to resize `nectar-vm` to `c3.3xlarge`, sync the tabulated
  assets/gate tests there, and run no-jet stability checks for cluster and
  group
- details are in:
  - `docs/exchange/logs/2026-05-05-stewart-assets-and-graile.md`

Supervisor-meeting-2 follow-up on 2026-05-07:

- Barry supplied the 2026-05-06 supervisor meeting transcript and a GPT-5.5
  Pro draft action plan:
  - `docs/codex_utas_phys_hons_meeting_2_transcript.md`
  - `docs/codex_utas_phys_hons_meeting_2_action_plan.md`
- the action plan has been reconciled against the transcript and repo state
- key corrections now binding:
  - `JET_END_TIME` and `JET_ACTIVE_TIME` are physical Myr values, not PLUTO
    code-time values
  - PLUTO core controls such as `tstop` and static-grid output intervals
    remain in PLUTO code time; later review clarified that Chombo
    `Checkpoint_interval` is disabled for the static-grid run path
  - the nominal first science run is particles-enabled `C-HI`, not a
    hydro-only rehearsal
  - first target duration is about `50 Myr`, not `300 Myr`
  - early diagnostics should be inspected after the first `3-5` snapshots at
    about `1 Myr` cadence
  - `JET_PWR` is confirmed as one-sided jet power
  - views are post-processing only; use `0 deg` as the easiest first view
- `docs/science/three_case_spec.md` is now spec version `three-case-v0.3`
- `scripts/science/render_three_case_configs.py` now defaults to the
  particles-enabled nominal science variant and writes `run_definition.json`
  plus `render_validation.json`
- the `kunanyi` production template now defaults to `CASE_VARIANT=particles`
- details are in:
  - `docs/exchange/logs/2026-05-07-supervisor-meeting-2-plan-update.md`

Patrick/Stas configuration review applied on 2026-05-08:

- Patrick confirmed the jet parameters and corrected the restart/output plan:
  static-grid PLUTO restarts from `*.dbl` or `*.dbl.h5`, so `dbl.h5` should
  be written every `5 Myr`; Chombo `Checkpoint_interval` is disabled
- PLUTO production/rehearsal jobs should pass `-maxtime`, e.g. `47.5` for a
  `48` hour PBS walltime, so a final `*.{flt,dbl}.h5` output is written before
  PBS termination
- Stas confirmed X3 should extend to `+/-250 kpc` and asked that the grid
  preserve the `200 kpc` resolution across coordinates
- the new grid preset is `stewart_stretched_250`:
  - X1/X2 retain the old `+/-200 kpc` patching
  - X3 uses `357` outer stretch cells on each side between `10` and `250 kpc`
  - this matches the old `dx` at about `200 kpc` (`~1.693 kpc`)
- the first-pass C-HI injection/output defaults are now:
  - `JET_INITIAL_RADIUS = 0.1`
  - `JET_INJECTION_HEIGHT = 0.75`
  - `JET_CHI = 1.0`
  - `JET_RELATIVISTIC_DENSITY = NO`
  - `particles_dbl = 3.06601394` code-time units (`0.01 Myr`)
  - `PART_INJECT_FREQUENCY = 0.01`
  - `Nparticles -1 16.0`
- `scripts/science/render_three_case_configs.py`,
  `scripts/science/render_stewart_environment_gate_tests.py`, and
  `scripts/kunanyi/jet_setup_production_template.pbs` have been updated to
  encode these rules
- the pre-review 2026-05-07 packet has been superseded by:
  - `docs/science/c_hi_configuration_lock_2026-05-08.qmd`
  - `docs/science/c_hi_configuration_lock_2026-05-08.pdf`
  - `docs/science/assets/c_hi_configuration_lock_2026-05-08/`
- static config validation passed with `render_validation.json: ok = true`
- a transfer-ready local tarball was prepared at
  `build/science/kunanyi_stage_2026-05-08/c_hi_and_environment_gate_2026-05-08.tar.gz`
- the production-like `kunanyi` Stewart no-jet environment/MPI/HDF5 gate
  passed for both confirmed radially averaged Stewart environments:
  `cluster_002003` and `group_002031`
- `cluster_002003` gate:
  - job id: `690366.kunanyi-ohpc`
  - exit status: `0`
  - walltime: `00:48:57`
  - peak memory reported by PBS: `24518028kb`
  - six `dbl.h5` outputs were written from `0` to `50 Myr`
  - live output footprint was about `33 GB`
- `group_002031` gate:
  - job id: `690371.kunanyi-ohpc`
  - exit status: `0`
  - walltime: `00:45:22`
  - peak memory reported by PBS: `24520976kb`
  - six `dbl.h5` outputs were written from `0` to `50 Myr`
  - live output footprint was about `33 GB`
- during that first gate, the one-off remote PBS script exposed an output-dir
  mismatch; the durable fix is now in
  `scripts/science/render_stewart_environment_gate_tests.py` and
  `scripts/kunanyi/stewart_environment_gate.pbs`
- compact Kunanyi gate artifacts have been retrieved locally at
  `build/science/kunanyi_stage_2026-05-08/stewart_gate_compact_results_2026-05-08.tar.gz`
  with SHA-256
  `adb099cd1557b192d23f48b6d5a1976225a607ebce9df7c2854b66d44a125c80`
- the first jet-bearing, particles-enabled `C-HI` one-node segment completed
  cleanly on `kunanyi`:
  - job id: `690426.kunanyi-ohpc`
  - job name: `c_hi_1node`
  - resources: `select=1:ncpus=28:mpiprocs=28`
  - walltime: `02:00:00`; `PLUTO_MAXTIME_HOURS=1.5`
  - exit status: `0`
  - PBS walltime used: `01:39:28`
  - PBS CPU time used: `44:04:38`
  - PBS peak memory: `30525360kb`
  - run root:
    `/scratch/bwbrook/xray_cavities_runs/2026-05-08-c-hi-segment`
  - `DONE` marker written, with no `FAILED` marker observed
  - PLUTO stopped itself via `-maxtime` and wrote final restart-capable HDF5
    outputs before PBS termination
  - output directory footprint: about `17 GB`
  - output files: `data.0000` and `data.0001` for both `dbl.h5` and `flt.h5`,
    plus `particles.0000.dbl` through `particles.0045.dbl`
  - final recorded time in `dbl.h5.out`/`flt.h5.out`: `t = 1.371692e+02`
    code units, step `583`
  - `h5ls` can read the `dbl.h5`/`flt.h5` files and sees the expected
    `Timestep_*`, `cell_coords`, and `node_coords` groups
  - generated grid: `404 x 404 x 452`; the central uniform patch remains
    `0.05 kpc`, while outer one-node shakedown edge cells are deliberately
    coarse
- two useful launch lessons were captured:
  - the production template needs `-include Particles/makefile` when
    `PARTICLES_LP` is enabled
  - the full `stewart_stretched_250` grid parses as roughly
    `960 x 960 x 1014` cells and is too large for a one-node particle
    shakedown; use `kunanyi_single_node_250` for this stage
- compact evidence from the completed run has been retrieved locally at
  `build/science/kunanyi_stage_2026-05-08/c_hi_1node_690426_compact_results_2026-05-09.tar.gz`
  with SHA-256
  `bba6a6505bd29cb832d419ae54d38471676f3f1e8b131bf9d6592c2de7477d26`
- first early-output quick-look diagnostics have now been generated:
  - quick-look extraction job id: `690451.kunanyi-ohpc`
  - inspected file: `data.0001.flt.h5`
  - inspected time: `0.4474 Myr`
  - products:
    `docs/science/c_hi_quicklook_2026-05-09.md` and
    `docs/science/c_hi_quicklook_2026-05-09.pdf`, with figures under
    `docs/science/assets/c_hi_quicklook_2026-05-09/`
  - at the default `tracer > 5e-3` threshold the early tracer region spans
    about `x,y = +/-2.33 kpc` and `z = +/-6.22 kpc`
  - central zoom maps show the expected symmetric bipolar tracer, density,
    pressure, and `vz` structure
- the first restart-continuation segment has now completed cleanly:
  - run job id: `690452.kunanyi-ohpc`
  - job name: `c_hi_restart`
  - resources: `select=1:ncpus=28:mpiprocs=28`
  - restart mode: `RUN_KIND=h5_restart_1`
  - PLUTO args: `-i pluto.ini -e environment.ini -maxtime 1.5 -h5restart 1`
  - exit status: `0`
  - PBS walltime used: `01:40:09`
  - PBS CPU time used: `44:14:47`
  - PBS peak memory: `30588076kb`
  - new restart-capable output: `data.0002.dbl.h5` at `1.0101 Myr`
  - nominal science-cadence output: `data.0002.flt.h5` at `0.9990 Myr`
  - forced float output: `data.0003.flt.h5` at `1.0101 Myr`
  - particles now extend through `particles.0103.dbl`
  - `markers/DONE` was written, with no `FAILED` marker observed
- a 1 Myr restart quick-look has now been generated:
  - quick-look extraction job id: `690479.kunanyi-ohpc`
  - inspected file: `data.0002.flt.h5`
  - inspected time: `0.9990 Myr`
  - products:
    `docs/science/c_hi_restart_quicklook_2026-05-09.md`, with figures under
    `docs/science/assets/c_hi_restart_quicklook_2026-05-09/`
  - at the default `tracer > 5e-3` threshold the tracer region spans about
    `x,y = +/-3.84 kpc` and `z = +/-10.1 kpc`
  - compact evidence bundle:
    `build/science/kunanyi_stage_2026-05-08/c_hi_restart_690452_quicklook_690479_compact_2026-05-09.tar.gz`
  - compact evidence SHA-256:
    `fe6c5259dcbe95d759d965d5b2e574e323af168dd127469a9c39d404e2cec2f2`
- this validates the build/output/restart/quick-look path, but it is not yet a
  production science snapshot
- the intermediate two-node restart rehearsal has now completed successfully:
  - first failed attempt `690481.kunanyi-ohpc` exposed an OpenMPI slot-discovery
    issue; the template now writes an explicit hostfile from `PBS_NODEFILE`
  - second failed attempt `690483.kunanyi-ohpc` exposed missing HDF5 runtime
    library propagation to the second node; the template now exports
    `PATH`, `LD_LIBRARY_PATH`, and HDF5-related variables through `mpirun`
  - successful run job id: `690484.kunanyi-ohpc`
  - job name: `c_hi_2node_env`
  - resources: `select=2:ncpus=28:mpiprocs=28`
  - nodes: `n038` and `n083`
  - restart mode: `RUN_KIND=h5_restart_2`
  - exit status: `0`
  - PBS walltime used: `01:45:08`
  - PBS CPU time used: `45:43:18`
  - PBS peak memory: `18587788kb`
  - new restart-capable output: `data.0003.dbl.h5` at `2.1501 Myr`
  - nominal 2 Myr science-cadence output: `data.0004.flt.h5` at `1.9996 Myr`
  - forced float output: `data.0005.flt.h5` at `2.1501 Myr`
  - particles now extend through `particles.0218.dbl`
  - `markers/DONE` was written, with no `FAILED` marker observed
- a 2 Myr two-node quick-look has now been generated:
  - quick-look extraction job id: `690559.kunanyi-ohpc`
  - inspected file: `data.0004.flt.h5`
  - inspected time: `1.9996 Myr`
  - products:
    `docs/science/c_hi_2node_quicklook_2026-05-09.md`, with figures under
    `docs/science/assets/c_hi_2node_quicklook_2026-05-09/`
  - at the default `tracer > 5e-3` threshold the tracer region spans about
    `x,y = +/-5.63 kpc` and `z = +/-16.5 kpc`
  - compact evidence bundle:
    `build/science/kunanyi_stage_2026-05-08/c_hi_2node_690484_quicklook_690559_compact_2026-05-09.tar.gz`
  - compact evidence SHA-256:
    `e002e0df31f5f2749ce823f7ca5b897c4b6b4cb7b322be9e29e9fb8cf9b045bb`
- the subsequent 5 Myr continuation is now complete; see the 2026-05-10
  update at the top of this file for the current state
- details are in:
  - `docs/exchange/logs/2026-05-08-patrick-stas-c-hi-feedback.md`
  - `docs/exchange/logs/2026-05-08-kunanyi-stewart-environment-gates.md`
  - `docs/exchange/logs/2026-05-08-c-hi-single-node-particle-segment.md`
  - `docs/exchange/logs/2026-05-09-c-hi-restart-segment.md`
  - `docs/exchange/logs/2026-05-09-c-hi-two-node-restart-rehearsal.md`

## Project Structure

Working model:

- WSL laptop = control plane
- `deep-server` = primary execution machine for simulation work
- `nectar-vm` = secondary execution machine and exchange hub
- `xray_cavities` = versioned environment/docs/workflow shell
- `/home/*/git/utas-agn` = actual UTAS AGN source tree

Primary branch context on all three main UTAS AGN repos:

- `pluto`: `bwbrook/deep-server-bringup`
- `jet-setup`: `bwbrook/deep-server-bringup`
- `plutokore`: `bwbrook/deep-server-bringup`

## Onboarding Progress

Completed satisfactorily:

1. PLUTO Sod shock tube, including solver and resolution comparisons
2. PLUTO instability-resolution comparisons
   - RT: `flat/euler`, `linear/hancock`, `parabolic/rk3`
   - KH: `flat/euler`, `linear/rk2`, `parabolic/rk3`
3. `jet-setup` familiarization and first basic jet run
4. small follow-up jet parameter sweep with a refined long-domain rerun
5. pure-Python Krause-style jet-analysis capstone
   - fresh two-case jet mini-suite on `deep-server`
   - tracer-based lobe diagnostics via `plutokore`
   - remade figures with no `pyPLUTO`

Current onboarding reports are under:

- `/home/bwbrook/papers/xray_cavities/docs/onboarding/reports/`

Most recent stage-3 reports:

- `2026-04-17-jet-setup-basic.qmd`
- `2026-04-17-jet-parameter-sweep.qmd`

Final stage-4 report:

- `2026-04-17-krause-jets-assignment.qmd`

Shareable PDFs are built under `_build/reports/` and copied to:

- `/mnt/c/Users/bwbrook/OneDrive - University of Tasmania/EXCHANGE/xray_cavities_files/reports`

## Remote Execution State

Important remote workspaces already exist on `deep-server`:

- `/home/bwbrook/work/pluto-onboarding/sod_hd`
- `/home/bwbrook/work/pluto-onboarding/rt_instability`
- `/home/bwbrook/work/pluto-onboarding/kh_instability`
- `/home/bwbrook/work/pluto-onboarding/jet_setup_basic`
- `/home/bwbrook/work/pluto-onboarding/jet_parameter_sweep`
- `/home/bwbrook/work/pluto-onboarding/krause_jets_assignment`

Nectar is now a valid secondary execution node with:

- `uv`
- Open MPI
- parallel HDF5
- UTAS AGN clones under `/home/ubuntu/git/utas-agn`
- `xray_cavities` under `/home/ubuntu/papers/xray_cavities`

For production-style HDF5 builds on Nectar, use the Nectar-specific PLUTO defs:

- `Config/Nectar.gcc.defs`
- `Config/Nectar.mpicc.defs`

## Most Recent Meaningful Result

The latest science-facing checkpoint is the aligned `C-HI` particles-enabled
5 Myr observable/truth smoke package on `kunanyi`.

Summary:

- `C-HI` now has regular HDF5 float outputs at about `1`, `2`, `3`, `4`, and
  `5 Myr`
- HDF5 restart and two-node MPI launch are validated through the production
  template
- the nominal 5 Myr quick-look is symmetric and far from the outer grid
  boundaries
- Level 1 injected-energy accounting and Level 2 tracer-mask lobe energetics
  have been extracted for the same `data.0008.flt.h5` snapshot
- the XRAiSE grid-thermal path and the particle-loss-aware runtime path are now
  both proven for the declared 5 Myr, `0 deg` target
- the first particle-loss-aware radio/lobe map and luminosity proxy are also
  complete for the same snapshot/view
- the next work is to build a compact aligned comparison package and run the
  deterministic particle-loss/radio cross-check

Repo-scoped artifacts:

- `docs/science/c_hi_to5_quicklook_2026-05-10.md`
- `docs/science/c_hi_to5_quicklook_2026-05-10.pdf`
- `docs/science/c_hi_xraise_grid_smoke_2026-05-10.md`
- `docs/science/c_hi_xraise_grid_smoke_2026-05-10.pdf`
- `docs/science/c_hi_particle_loss_smoke_2026-05-10.md`
- `docs/science/c_hi_particle_loss_smoke_2026-05-10.pdf`
- `docs/science/c_hi_particle_radio_smoke_2026-05-10.md`
- `docs/science/c_hi_particle_radio_smoke_2026-05-10.pdf`
- `docs/science/assets/c_hi_to5_quicklook_2026-05-10/`
- `docs/science/assets/c_hi_particle_loss_smoke_2026-05-10/`
- `docs/science/assets/c_hi_particle_radio_smoke_2026-05-10/`
- `docs/exchange/logs/2026-05-10-c-hi-particle-radio-smoke.md`

The previous major science-facing checkpoint was the Stewart environment gate on
resized Nectar.

Summary:

- Patrick supplied the Stewart environment archive and GRAiLE/XRAiSE bundle
- Stas clarified that science runs should use the radially averaged tabulated
  environments rather than the full 3D grids
- the selected cluster `002_003` and group `002_031` tabulated files were
  staged to Nectar and tested as no-jet hydrostatic gates
- both gates completed to `300 Myr` and passed the existing
  `jet-setup/test/environment/verify-environment-stability.py` checks

Key gate metrics:

- cluster `002_003`:
  - max central density drift `0.136%`
  - max central pressure drift `0.226%`
  - max Mach `0.0242`
- group `002_031`:
  - max central density drift `0.284%`
  - max central pressure drift `0.473%`
  - max Mach `0.0330`

Repo-scoped artifacts:

- `docs/science/stewart_environment_gate_2026-05-05.md`
- `docs/science/stewart_environment_gate_2026-05-05.pdf`
- `docs/science/stewart_environment_gate_status_2026-05-05.md`
- `docs/science/stewart_environment_gate_status_2026-05-05.pdf`
- `docs/science/assets/stewart_environment_gate_2026-05-05/stewart_environment_gate_timeseries.png`
- `docs/science/assets/stewart_environment_gate_2026-05-05/stewart_environment_gate_profiles.png`
- `docs/science/assets/stewart_environment_gate_2026-05-05/stewart_environment_gate_metrics.csv`

## Next Recommended Step

The onboarding sequence and the early `C-HI` execution-path smoke tests are now
complete through the 5 Myr diagnostic snapshot, including first truth,
cavity-protocol, XRAiSE grid-thermal, particle-loss runtime, and
particle-loss-aware radio/lobe products for the same snapshot/view.

The next move should be to build the first aligned comparison package,
using:

- `jet-setup` for new simulation runs
- the pure-Python `plutokore` lane for analysis
- the MacBook as a control/orchestration machine only
- resized `nectar-vm` for tests, 2D runs, and micro-3D smoke runs
- `kunanyi` for full 3D production once its access/module/build/submission path
  has been smoke-tested

As of 2026-05-10, the immediate target remains the 5 Myr `C-HI`, `0 deg`
snapshot unless we deliberately choose to wait for a later, larger cavity:

1. fold the aligned X-ray, radio, truth, and cavity quantities into a compact
   one-page comparison report for the 5 Myr target
2. run a deterministic particle-loss/radio cross-check, at minimum comparing
   `NUMBA_NUM_THREADS=1` and `4`, because supplied `xraise.py` emits a Numba
   parallel-safety warning
3. only then decide whether to continue `C-HI` toward longer snapshots or begin
   preparing the full production chain

The Stewart tabulated assets are present locally and the Nectar no-jet
stability gates are green for both selected science environments:

- cluster `002_003` for `C-HI` and `C-LO`: max central density drift `0.136%`,
  max Mach `0.0242`
- group `002_031` for `G-LO`: max central density drift `0.284%`, max Mach
  `0.0330`

The detailed Stewart gate report and plots are in
`docs/science/stewart_environment_gate_2026-05-05.md`; that report has been
marked with a post-meeting correction note where the follow-on plan changed.

After the Nectar environment gate, `nectar-vm` was parked back to `c3.xsmall`.

## Resume Checklist For A Fresh Agent

1. pull `xray_cavities`
2. read `AGENTS.md`
3. read `docs/exchange/current_status.md`
4. read the newest note under `docs/exchange/logs/`
5. if simulation work is needed, confirm access to:
   - `deep-server` from WSL, or
   - `nectar-vm` from the MacBook
6. if using `deep-server`, prefer existing remote workspaces rather than making
   new scratch directories without a reason
7. if using `nectar-vm`, pull `xray_cavities` and the UTAS AGN repos before
   assuming parity with WSL
8. read the final onboarding capstone report before proposing new jet-analysis
   work

## Handover Checklist

Before stopping on any machine:

1. update this file if project state changed
2. add a dated note under `docs/exchange/logs/`
3. commit and push the exchange docs if they changed
4. if the work matters for MacBook continuity, pull the updated repo on
   `nectar-vm`

## Known Non-Issue

`xray_cavities` may still show unrelated untracked `sci_lit/` files locally.
Those are intentionally out of scope for the UTAS AGN onboarding workflow unless
the user explicitly asks to work on them.
