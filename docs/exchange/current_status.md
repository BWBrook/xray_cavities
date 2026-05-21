# Current Status

Last updated: 2026-05-21
Primary checkpoint repo: `/home/bwbrook/papers/xray_cavities`

## Read This First

Before trusting anything below, pull the latest `xray_cavities` on the machine
you are using:

```bash
cd /home/<user>/papers/xray_cavities
git pull --ff-only
```

This note should be treated as a post-stage-4 handoff. Always pull the latest
`origin/main` before relying on the exact file set or workflow bundle on any
machine.

Latest full-grid `C-HI` retry launch on 2026-05-21:

- The first 80-node startup job, `692369.kunanyi-ohpc`, failed after PLUTO
  initialization and initial HDF5 writes because UCX/OpenMPI aborted with
  `UD endpoint ... unhandled timeout error` during MPI collectives. This is
  recorded in
  `agent_comms/threads/2026-05-21-c-hi-fullgrid-startup-failure.md`.
- A retry wrapper was prepared and submitted:
  - PBS job: `692504.kunanyi-ohpc`
  - PBS name: `c_hi_fg_retry`
  - Initial state after submission: `Q` on queue `normal`
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
