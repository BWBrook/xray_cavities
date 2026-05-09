# kunanyi Setup Notes

Last updated: 2026-05-02

These notes record the first successful MacBook control-plane access path to
TPAC's `kunanyi` HPC.

## Access Model

Direct SSH uses a short-lived jumpbox access window opened from the Open
OnDemand portal.

1. Open the TPAC Open OnDemand portal.
2. Enable the 5-minute jumpbox SSH window.
3. SSH to the jumpbox:

```bash
ssh tpac-jumpbox
```

4. From the jumpbox, SSH to the `kunanyi` login node:

```bash
ssh kunanyi
```

Local Mac SSH aliases are configured in `~/.ssh/config`:

```sshconfig
Host tpac-jumpbox
  HostName <tpac-host>
  User bwbrook
  ServerAliveInterval 30

Host kunanyi
  HostName kunanyi
  User bwbrook
  ProxyJump tpac-jumpbox
  ServerAliveInterval 30
```

The first successful login path landed on:

- jumpbox: `jumpbox-2`
- login node: `<tpac-host>`

## Secret Location

The Mac stores TPAC credentials outside the repo at:

```text
/Users/bwbrook/.config/tpac/kunanyi.env
```

Expected contents:

```bash
TPAC_USER='bwbrook'
TPAC_PASSWORD='...'
```

The file should remain mode `600`.

## Filesystems

TPAC-provided paths:

- home: `/u/bwbrook`
- scratch: `/scratch/bwbrook`

Use scratch for job working directories. It is not backed up.

## Login Node Inventory

Confirmed on `kunanyi-00`:

- shell: `/bin/bash`
- `qsub`: `/opt/pbs/bin/qsub`
- `qstat`: `/opt/pbs/bin/qstat`
- PBS server: `kunanyi-ohpc`
- PBS status: active
- Lmod is available:
  - `Modules based on Lua: Version 8.1.18`

Observed queues included:

- `test`
- `normal`
- `express`
- `LARGE_MEM`
- `MEM512GB`

Do not run simulations or compiles on the login node. Submit work through PBS,
or request an interactive job for builds.

## PBS Resource Sizing

Use `select`, `ncpus`, and `mpiprocs` to control node/core layout.

Small shared-node smoke tests can request only a few cores:

```pbs
#PBS -l select=1:ncpus=2
```

For a full 28-core node with one MPI rank per core:

```pbs
#PBS -l select=1:ncpus=28:mpiprocs=28
```

For a multi-node run:

```pbs
#PBS -l select=4:ncpus=28:mpiprocs=28
```

That layout is intended to pair with:

```bash
mpirun -np 112 ./pluto -i pluto.ini
```

Before launching serious 3D jobs, confirm the correct production queue,
walltime, storage location, and whether TPAC expects full-node requests for
large MPI work.

## First PBS Smoke Test

The first clean PBS compute-node smoke used:

- script: `scripts/kunanyi/smoke_job.pbs`
- remote scratch directory: `/scratch/bwbrook/codex_smoke`
- queue: `test`
- resources: `select=1:ncpus=1`, `walltime=00:02:00`

Submission result:

```text
SUBMITTED=688913.kunanyi-ohpc
```

Output confirmed execution on a compute node:

```text
HOST=n001.kunanyi
USER=bwbrook
PWD=/scratch/bwbrook/codex_smoke
PBS_JOBID=688913.kunanyi-ohpc
PBS_O_WORKDIR=/scratch/bwbrook/codex_smoke
PBS_QUEUE=test
PBS_NODEFILE=/var/spool/pbs/aux/688913.kunanyi-ohpc
NODEFILE_CONTENTS=n001.kunanyi
NCPUS=28
```

The job printed locale warnings to stderr:

```text
setlocale: LC_ALL: cannot change locale (C.UTF-8)
```

These warnings did not prevent job execution. If they become noisy in later
automation, set a compatible locale before SSH/PBS submission.

## Next HPC Smoke Steps

1. Clone or sync the UTAS AGN repos into `/scratch/bwbrook` or another agreed
   working location.
2. Build a tiny PLUTO case under PBS.
3. Retrieve artifacts back through jumpbox/home.

The local helper for targeted module inventory is:

```bash
scripts/kunanyi/module_inventory.sh
```

It expects an active TPAC jumpbox SSH window and reads credentials from
`/Users/bwbrook/.config/tpac/kunanyi.env`.

## Module Inventory

Confirmed on `2026-05-01`:

- `HDF5/1.14.0-gompi-2023a`
- `OpenMPI/4.1.5-GCC-12.3.0`
- `GCC/12.3.0`
- `CMake/3.26.3-GCCcore-12.3.0`
- `Python/3.11.3-GCCcore-12.3.0`
- `git/2.41.0-GCCcore-12.3.0-nodocs`
- `netCDF/4.9.2-gompi-2023a`

The best first PLUTO/HDF5 stack is:

```bash
module purge
module load HDF5/1.14.0-gompi-2023a
```

This loads the GCC 12.3 / OpenMPI 4.1.5 / HDF5 1.14.0 `gompi/2023a`
environment.

## MPI + Parallel HDF5 Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/hdf5_probe.pbs`
- job id: `688922.kunanyi-ohpc`
- queue: `test`
- compute node: `n001.kunanyi`
- scratch workdir: `/scratch/bwbrook/codex_hdf5_probe`

The job loaded `HDF5/1.14.0-gompi-2023a`, compiled a C smoke program with
`h5pcc`, ran it with `mpirun -np 2`, and created/dumped
`mpi_hdf5_smoke.h5`.

Key output:

```text
mpirun (Open MPI) 4.1.5
MPI ranks: 2
Parallel HDF5 file created.
```

This validates that the core compiler/MPI/HDF5 stack needed for PLUTO HDF5
smoke work is available and works on a compute node.

## PLUTO Sod Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/pluto_sod_smoke.pbs`
- job id: `688924.kunanyi-ohpc`
- queue: `test`
- compute node: `n001.kunanyi`
- scratch PLUTO tree: `/scratch/bwbrook/git/utas-agn/pluto`
- run directory: `/scratch/bwbrook/pluto_smoke/sod_hd/run`

The job loaded `HDF5/1.14.0-gompi-2023a`, generated a PLUTO makefile with
`ARCH = Kunanyi.defs`, built with `make -j2`, and ran the PLUTO `HD/Sod`
problem with:

```bash
mpirun -np 2 ./pluto -i pluto.ini
```

Key outputs:

```text
data.0000.dbl
data.0001.dbl
dbl.out
grid.out
pluto.0.log
restart.out
```

`dbl.out` recorded the initial output and final `t = 0.2` output:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 2.000000e-01 8.148885e-04 235 single_file little rho vx1 vx2 vx3 prs
```

The rank-0 PLUTO log reported:

```text
Number of processors: 2
Parallel Directions:  X1
Elapsed time              0d:0h:0m:11s
Done
```

This is the first confirmed PLUTO build/run smoke on `kunanyi`.

## PLUTO Jet Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/pluto_jet_smoke.pbs`
- job id: `688926.kunanyi-ohpc`
- queue: `test`
- compute node: `n001.kunanyi`
- scratch PLUTO tree: `/scratch/bwbrook/git/utas-agn/pluto`
- run directory: `/scratch/bwbrook/pluto_smoke/jet_hd/run`

This was a deliberately tiny official PLUTO `HD/Jet` smoke:

```text
grid: 16 x 48
domain: r = 0..4, z = 0..12
tstop: 1.0
ETA: 10.0
external Mach target: 20.0
MACH parameter: 6.32455532034
MPI ranks: 2
```

The job loaded `HDF5/1.14.0-gompi-2023a`, generated a PLUTO makefile with
`ARCH = Kunanyi.defs`, built with `make -j2`, and ran:

```bash
mpirun -np 2 ./pluto -i pluto.ini
```

`dbl.out` recorded the initial output, a mid-run output, and final `t = 1.0`
output:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 4.929819e-01 1.550904e-02 74 single_file little rho vx1 vx2 vx3 prs
2 1.000000e+00 9.293902e-04 108 single_file little rho vx1 vx2 vx3 prs
```

This validates the official PLUTO jet problem path under PBS on `kunanyi`.

## PLUTO Scaled 2D Jet Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/pluto_jet_2d_scaled.pbs`
- job id: `688930.kunanyi-ohpc`
- queue: `test`
- compute node: `n001.kunanyi`
- resources: `select=1:ncpus=8:mpiprocs=8`, requested walltime `00:20:00`
- scratch PLUTO tree: `/scratch/bwbrook/git/utas-agn/pluto`
- run directory: `/scratch/bwbrook/pluto_smoke/jet_hd_2d_scaled/run`

This scaled the official PLUTO `HD/Jet` smoke while keeping it a deliberately
small single-node check:

```text
grid: 64 x 192
domain: r = 0..4, z = 0..12
tstop: 2.0
ETA: 10.0
external Mach target: 20.0
MACH parameter: 6.32455532034
MPI ranks: 8
```

The job loaded `HDF5/1.14.0-gompi-2023a`, generated a PLUTO makefile with
`ARCH = Kunanyi.defs`, built with `make -j8`, and ran:

```bash
mpirun -np 8 ./pluto -i pluto.ini
```

PBS accounting reported `Exit_status = 0`, `resources_used.walltime =
00:00:21`, and `exec_host = n001/3*8`. The run produced five double outputs:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 4.980701e-01 3.908019e-03 158 single_file little rho vx1 vx2 vx3 prs
2 9.979077e-01 4.112735e-03 282 single_file little rho vx1 vx2 vx3 prs
3 1.497833e+00 4.037600e-03 405 single_file little rho vx1 vx2 vx3 prs
4 2.000000e+00 1.844065e-03 530 single_file little rho vx1 vx2 vx3 prs
```

This validates a modestly scaled official PLUTO 2D jet path using more than two
MPI ranks on one `kunanyi` node.

## `jet-setup` Tiny 3D Cartesian Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/jet_setup_tiny_3d_cart.pbs`
- successful job id: `688935.kunanyi-ohpc`
- first failed job id: `688934.kunanyi-ohpc`
- queue: `test`
- compute node: `n010.kunanyi`
- resources: `select=1:ncpus=8:mpiprocs=8`, requested walltime `00:20:00`
- scratch PLUTO tree: `/scratch/bwbrook/git/utas-agn/pluto`
- scratch `jet-setup` tree: `/scratch/bwbrook/git/utas-agn/jet-setup`
- run directory: `/scratch/bwbrook/jet_setup_smoke/tiny_3d_cart/problem`

The `jet-setup` source bundle was copied through jumpbox, unpacked under
`/scratch/bwbrook/git/utas-agn/jet-setup`, and used to scaffold a tiny
Cartesian 3D problem matching the Nectar smoke exercise:

```text
grid: 48 x 48 x 72
domain: x = -12..12, y = -12..12, z = -18..18
physics: HD
geometry: Cartesian 3D
environment: King
particles: off
tstop: 300.0
MPI ranks: 8
```

The successful job loaded `HDF5/1.14.0-gompi-2023a`, generated a PLUTO
makefile with `ARCH = Kunanyi.defs`, built with `make -j8`, and ran:

```bash
mpirun -np 8 ./pluto -i pluto.ini
```

PBS accounting for `688935.kunanyi-ohpc` reported `Exit_status = 0`,
`resources_used.walltime = 00:01:26`, `resources_used.cput = 00:04:55`,
`resources_used.mem = 342164kb`, and `exec_host = n010/1*8`.

`dbl.out` recorded the initial output, a mid-run output, and final `t = 300`
output:

```text
0 0.000000e+00 1.000000e-03 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.497451e+02 6.727975e-01 282 single_file little rho vx1 vx2 vx3 prs tr1
2 3.000000e+02 2.431960e-01 506 single_file little rho vx1 vx2 vx3 prs tr1
```

The output files on scratch include three `7.6 MB` double dumps,
`grid.out`, `dbl.out`, and eight per-rank PLUTO logs. Rank 0 finished with:

```text
> Writing file #2 (dbl) to disk...
> Elapsed time              0d:0h:0m:34s
> Done
```

The first attempt, `688934.kunanyi-ohpc`, failed quickly during script setup
because the current `jet-setup` `definitions.h` does not define `COMPONENTS`.
The PBS script now leaves that absent define alone. The script still emits a
harmless `git: command not found` warning from `tools/setup-problem` when the
Git module is not loaded; it did not affect the green run.

This validates the first one-node `jet-setup` 3D path on `kunanyi`.

## PBS Email Notifications

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/email_notify_smoke.pbs`
- job id: `688936.kunanyi-ohpc`
- queue: `test`
- compute node: `n004.kunanyi`
- mail recipient: `barry.brook@utas.edu.au`
- mail points: `abe`

The PBS directives are:

```bash
#PBS -M barry.brook@utas.edu.au
#PBS -m abe
```

PBS history recorded:

```text
Job_Name = email_notify_smoke
job_state = F
Mail_Points = abe
Mail_Users = barry.brook@utas.edu.au
Exit_status = 0
resources_used.walltime = 00:00:21
```

Barry confirmed that the completion email arrived from
`adm@<tpac-host>`.

For production simulations, use:

```bash
#PBS -M barry.brook@utas.edu.au
#PBS -m ae
```

where `a` means abort and `e` means end. The `b` begin notification is useful
for smoke tests, but probably too chatty for routine long production jobs.

## `jet-setup` Two-Node 3D MPI Smoke

Confirmed on `2026-05-01` with:

- script: `scripts/kunanyi/jet_setup_tiny_3d_cart_multinode.pbs`
- job id: `688937.kunanyi-ohpc`
- queue: `test`
- compute nodes: `n010.kunanyi` and `n011.kunanyi`
- resources: `select=2:ncpus=8:mpiprocs=8`, requested walltime `00:20:00`
- scratch PLUTO tree: `/scratch/bwbrook/git/utas-agn/pluto`
- scratch `jet-setup` tree: `/scratch/bwbrook/git/utas-agn/jet-setup`
- run directory:
  `/scratch/bwbrook/jet_setup_smoke/tiny_3d_cart_multinode/problem`

This reused the tiny Cartesian 3D case and derived rank count from
`PBS_NODEFILE`:

```bash
NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

The allocation spanned two nodes:

```text
exec_host = n010/1*8+n011/0*8
resources_used.ncpus = 16
```

PBS accounting reported:

```text
Exit_status = 0
resources_used.walltime = 00:00:54
resources_used.cput = 00:05:40
resources_used.mem = 616720kb
resources_used.vmem = 5858392kb
```

The run produced the expected 3D outputs:

```text
data.0000.dbl
data.0001.dbl
data.0002.dbl
dbl.out
grid.out
logs/pluto.0.log ... logs/pluto.15.log
restart.out
```

`dbl.out` recorded the same three outputs as the one-node case:

```text
0 0.000000e+00 1.000000e-03 0 single_file little rho vx1 vx2 vx3 prs tr1
1 1.497451e+02 6.727975e-01 282 single_file little rho vx1 vx2 vx3 prs tr1
2 3.000000e+02 2.431960e-01 506 single_file little rho vx1 vx2 vx3 prs tr1
```

Rank 0 finished with:

```text
> Writing file #2 (dbl) to disk...
> Elapsed time              0d:0h:0m:20s
> Done
```

This validates that PLUTO/`jet-setup` can run across multiple `kunanyi` nodes.
For full-node production jobs, the expected pattern is:

```bash
#PBS -l select=N:ncpus=28:mpiprocs=28
NRANKS=$(wc -l < "$PBS_NODEFILE")
mpirun -np "$NRANKS" ./pluto -i pluto.ini
```

## Preparation Passes Before Full 3D Jobs

The infrastructure path is now validated, but full production simulations
should wait until the science/job package is made production-safe. Do these
preparation passes before submitting any 48-hour multi-node run.

1. Lock the case specification.
   - Confirm the three-case science suite: low-power cluster, high-power
     cluster, and low-power group.
   - Record physics switches, jet parameters, environment parameters, grid,
     domain, final time, source age outputs, and viewing-angle products.
   - Confirm whether each case needs particles, radio outputs, X-ray products,
     tracer/truth products, or all of these.

2. Build a production PBS template.
   - Use full-node requests when appropriate:
     `select=N:ncpus=28:mpiprocs=28`.
   - Derive `NRANKS` from `PBS_NODEFILE`.
   - Include `#PBS -M barry.brook@utas.edu.au` and `#PBS -m ae`.
   - Write absolute stdout/stderr paths under `/u/bwbrook/codex_kunanyi/` or a
     case-specific home log directory.
   - Emit `JOB_START`, `JOB_END`, module stack, nodefile contents, rank count,
     source revision, and run directory.

3. Add restart and resume handling.
   - Set `dbl.h5` cadence in `pluto.ini` before long jobs; static-grid PLUTO
     restarts from `*.dbl` or `*.dbl.h5`, not Chombo checkpoints.
   - Keep Chombo `Checkpoint_interval` disabled unless the adaptive-grid code
     is deliberately introduced later.
   - Keep restart files in scratch during the run.
   - Add simple `DONE` and `FAILED` markers in the run directory.
   - Make reruns detect whether they are fresh starts or restarts.

4. Confirm output volume and retention plan.
   - Estimate size of `dbl`, HDF5, particle, radio, X-ray, and diagnostic
     products before launch.
   - Decide what stays on scratch temporarily, what is copied to home, and what
     is pulled back to the MacBook or Nectar for analysis.
   - Avoid leaving large completed datasets on scratch without an explicit
     cleanup/transfer step.

5. Run an intermediate-size rehearsal.
   - Use the production script structure, but with a smaller grid or shorter
     final time.
   - Exercise `dbl.h5` writing, restart with `-h5restart`, `DONE`/`FAILED`
     markers, email alerts, and artifact retrieval.
   - Treat this as the last gate before the full three-case run.

6. Launch production jobs.
   - Submit only after the case spec, PBS template, restart path, output plan,
     and intermediate rehearsal are green.
   - After submission, the jumpbox session can close; PBS owns the job.
   - Monitor via email and later `qstat -x -f <jobid>`, stdout/stderr logs, and
     run-directory markers.

## Three-Case Science Package

Added on `2026-05-02`; corrected after the `2026-05-06` supervisor meeting
and Patrick/Stas' `2026-05-08` configuration review:

- frozen science spec:
  `docs/science/three_case_spec.md`
- current science asset inventory:
  `docs/science/asset_inventory_2026-05-02.md`
- config renderer:
  `scripts/science/render_three_case_configs.py`
- production-oriented PBS template:
  `scripts/kunanyi/jet_setup_production_template.pbs`

The PBS template implements the validated production shape:

```pbs
#PBS -l select=1:ncpus=28:mpiprocs=28
#PBS -M barry.brook@utas.edu.au
#PBS -m ae
```

It derives `NRANKS` from `PBS_NODEFILE`, logs PLUTO and `jet-setup` source
revisions, applies generated `definitions_overrides.json`, uses
`pluto.ini`/`environment.ini` from the selected case bundle, detects fresh
runs versus `.dbl.h5`/`.dbl` restarts, passes `-maxtime` to PLUTO by default,
and writes `DONE`/`FAILED` markers under the run directory.

Example review-package render after the real Stewart assets are known:

```bash
python3 scripts/science/render_three_case_configs.py \
  --variant particles \
  --case C-HI \
  --grid stewart_stretched_250 \
  --duration-myr 50 \
  --snapshot-interval-myr 1 \
  --dbl-h5-interval-myr 5 \
  --particle-interval-myr 0.01 \
  --particles-per-injection 16 \
  --cluster-tabulated env/extracted/environments/tabulated/tabulated_cosmo_002003.csv \
  --check-local-assets \
  --output build/science/c_hi_configuration_lock_2026-05-08 \
  --force
```

Then copy the generated case directory to `kunanyi` and submit with case
variables, for example:

```bash
qsub -v CASE_ID=C-HI,CASE_VARIANT=particles,CASE_CONFIG_DIR=/u/bwbrook/xray_cavities_cases/C-HI/particles \
  scripts/kunanyi/jet_setup_production_template.pbs
```

For a `48:00:00` PBS walltime, leave the template default
`PLUTO_MAXTIME_HOURS=47.5` in place so PLUTO writes a final static-grid HDF5
output before PBS can kill the job. Override only for shorter rehearsals, for
example `PLUTO_MAXTIME_HOURS=1.5` for a two-hour walltime.

Do not submit this as a 48-hour production run yet. The production-like no-jet
Stewart environment/MPI/HDF5 gate passed on `kunanyi` for both confirmed
radially averaged environments on `2026-05-08`:

- `cluster_002003`: `690366.kunanyi-ohpc`, exit status `0`, walltime
  `00:48:57`
- `group_002031`: `690371.kunanyi-ohpc`, exit status `0`, walltime
  `00:45:22`

The first jet-bearing `C-HI` particles segment completed on `2026-05-09` as
`690426.kunanyi-ohpc`. It used one Kunanyi node, `28` MPI ranks, a
`02:00:00` walltime, and `PLUTO_MAXTIME_HOURS=1.5`. PBS reported
`Exit_status = 0`, `walltime = 01:39:28`, `cput = 44:04:38`, and peak memory
`30525360kb`.

Two practical launch lessons are now folded into the workflow:

- particle builds need the generated problem `local_make` to include
  `Particles/makefile`; otherwise `PARTICLES_LP` builds fail on
  `particles.h`
- the full `stewart_stretched_250` grid is too large for a one-node particle
  shakedown, parsing as roughly `960 x 960 x 1014` cells; use the
  `kunanyi_single_node_250` grid for one-node rehearsal and keep the full grid
  for multi-node production planning

The completed run wrote a `DONE` marker, stopped cleanly through PLUTO
`-maxtime`, and wrote `data.0000`/`data.0001` for both `dbl.h5` and `flt.h5`
plus `particles.0000.dbl` through `particles.0045.dbl`. `h5ls` can read the
HDF5 files. The final forced HDF5 output is at `t = 1.371692e+02` code units
and step `583`, so this is an infrastructure shakedown rather than a science
snapshot. Compact evidence is stored locally under
`build/science/kunanyi_stage_2026-05-08/` with SHA-256
`bba6a6505bd29cb832d419ae54d38471676f3f1e8b131bf9d6592c2de7477d26`.

## Jumpbox SSH Window Automation

The Open OnDemand endpoint for enabling jumpbox SSH is:

```text
https://<tpac-host>/pun/sys/enable_ssh/
```

A plain `curl` request to this URL is not enough because the request is routed
through the UTAS SAML/AAF browser login flow and can end in a stale-request
page. The practical automation route on the MacBook is therefore to reuse the
authenticated Safari session.

If Safari is already logged in to the Kunanyi portal, this helper opens the
Enable SSH endpoint and starts a fresh five-minute window:

```bash
scripts/kunanyi/enable_jumpbox_ssh_safari.sh
```

Computer Use can also click the portal's `Enable Jumpbox SSH` link directly.
That route was tested successfully on 2026-05-09 and opened a new window
ending at `Sat May 9 13:36:27 2026`.
