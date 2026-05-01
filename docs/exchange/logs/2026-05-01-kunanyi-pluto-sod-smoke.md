# Handover Note: 2026-05-01 kunanyi PLUTO Sod smoke

## Session Context

- Machine used: MacBook Neo as control plane
- Remote access: TPAC jumpbox window opened via Open OnDemand
- Local repo path: `/Users/bwbrook/papers/xray_cavities`

## What Was Done

- Checked whether project/source repos already existed on `kunanyi`.
- Confirmed no useful existing `xray_cavities` / UTAS AGN checkout was present
  under `/u/bwbrook` or `/scratch/bwbrook`.
- Built a clean PLUTO-only source bundle locally from
  `/Users/bwbrook/git/utas-agn/pluto`.
- Copied it to TPAC home via jumpbox:
  `/u/bwbrook/pluto_source_2026-05-01.tgz`.
- Unpacked it to:
  `/scratch/bwbrook/git/utas-agn/pluto`.
- Patched the scratch copy of `Tools/Python/menu.py` so PLUTO's `--no-curses`
  path works under Python 3:
  `raw_input = input`.
- Submitted a tiny PLUTO `HD/Sod` PBS smoke to the `test` queue.

## Source Transfer

The first all-repo tarball unpack was interrupted by wrapper timeout and noisy
macOS extended-attribute warnings. The successful replacement bundle used:

```bash
COPYFILE_DISABLE=1 tar -C /Users/bwbrook/git/utas-agn \
  --no-xattrs \
  --exclude='*/.git' \
  --exclude='*/__pycache__' \
  --exclude='*/.pytest_cache' \
  --exclude='*/.venv' \
  --exclude='*/build' \
  --exclude='*/_build' \
  --exclude='.DS_Store' \
  -czf /tmp/xray_cavities_kunanyi/pluto_source_2026-05-01.tgz \
  pluto
```

This made a roughly `15 MB` bundle. After unpacking, the scratch PLUTO tree was
about `38 MB`, and both `Test_Problems/HD/Sod` and `Test_Problems/HD/Jet` were
present.

## PBS PLUTO Smoke

Submitted job:

```text
688924.kunanyi-ohpc
```

Run details:

```text
queue: test
compute node: n001.kunanyi
resources: select=1:ncpus=2, walltime=00:10:00
workdir: /scratch/bwbrook/pluto_smoke/sod_hd
run dir: /scratch/bwbrook/pluto_smoke/sod_hd/run
```

The job used:

```text
module load HDF5/1.14.0-gompi-2023a
ARCH = Kunanyi.defs
mpicc = /share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpicc
mpirun = /share/apps/software/OpenMPI/4.1.5-GCC-12.3.0/bin/mpirun
HDF5_DIR = /share/apps/software/HDF5/1.14.0-gompi-2023a
```

It generated a PLUTO makefile non-interactively with:

```bash
printf '3\n' | env PLUTO_DIR=/scratch/bwbrook/git/utas-agn/pluto \
  python3 /scratch/bwbrook/git/utas-agn/pluto/setup.py \
  --no-curses --auto-update
```

Then it built with:

```bash
make -j2
```

and ran with:

```bash
mpirun -np 2 ./pluto -i pluto.ini
```

## Validation Output

Key files:

```text
pluto           302K
data.0000.dbl    16K
data.0001.dbl    16K
dbl.out          142
grid.out          20K
pluto.0.log      4.0K
restart.out      256
```

`dbl.out`:

```text
0 0.000000e+00 1.000000e-04 0 single_file little rho vx1 vx2 vx3 prs
1 2.000000e-01 8.148885e-04 235 single_file little rho vx1 vx2 vx3 prs
```

Rank-0 PLUTO log confirmed:

```text
Number of processors: 2
Proc size:            200
Parallel Directions:  X1
Writing file #0 (dbl) to disk...
Starting computation...
Writing file #1 (dbl) to disk...
Elapsed time              0d:0h:0m:11s
Done
```

## Current State

- A scratch PLUTO tree exists at `/scratch/bwbrook/git/utas-agn/pluto`.
- The PLUTO `HD/Sod` smoke is green under PBS with MPI and HDF5 enabled.
- The reusable local PBS script is:
  `scripts/kunanyi/pluto_sod_smoke.pbs`.
- `scripts/kunanyi/run_on_kunanyi.sh` now uses a longer timeout for setup and
  compile jobs.

## Next Recommended Step

Run the official PLUTO `HD/Jet` problem under PBS on kunanyi, still tiny and
within the `test` queue if possible, using the same module stack and setup
pattern.
