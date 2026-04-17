#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=/home/bwbrook/git/utas-agn/pluto
JET_SETUP=/home/bwbrook/git/utas-agn/jet-setup
BASE=/home/bwbrook/work/pluto-onboarding/jet_setup_basic
PROBLEM=$BASE/problem
LOGS=$BASE/logs
PLOTS=$BASE/plots
RESULTS=$BASE/results

mkdir -p "$BASE" "$LOGS" "$PLOTS" "$RESULTS"
rm -rf "$PROBLEM"
mkdir -p "$PROBLEM"

cd "$PROBLEM"
"$JET_SETUP/tools/setup-problem"
"$JET_SETUP/tools/create-build-script"

python3 - <<'PY'
from pathlib import Path

problem = Path('/home/bwbrook/work/pluto-onboarding/jet_setup_basic/problem')

def replace_define(path: Path, key: str, value: str):
    lines = path.read_text().splitlines()
    updated = []
    replaced = False
    for line in lines:
        if line.startswith('#define') and key in line:
            updated.append(f'#define  {key.ljust(28)}   {value}')
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        raise RuntimeError(f'Missing define {key} in {path}')
    path.write_text('\n'.join(updated) + '\n')

replace_define(problem / 'src/definitions.h', 'DIMENSIONS', '2')
replace_define(problem / 'src/definitions.h', 'GEOMETRY', 'SPHERICAL')
replace_define(problem / 'src/definitions.h', 'PARTICLES', 'NO')
replace_define(problem / 'src/definitions_usr.h', 'DENSITY_PROFILE', 'ENV_KING')
replace_define(problem / 'src/definitions_usr.h', 'JET_INJECTION_ROTATED', 'NO')
replace_define(problem / 'src/definitions_usr.h', 'PARTICLES_LP_RAISE', 'NO')

(problem / 'src/local_make').write_text(
    'OBJ += coordinates.o jet.o units.o environment_utilities.o environment.o '
    'tools_usr.o read_external_pressure.o galaxy.o\n'
    'HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h '
    'units.h environment_utilities.h environment.h tools_usr.h '
    'read_external_pressure.h galaxy.h\n'
)

(problem / 'pluto.ini').write_text('''[Grid]\n\n; Basic 2D spherical jet run\nX1-grid  1  0.2   96  u  30.0\nX2-grid  1  0.01  64  u  3.141592653589793\nX3-grid  1  0.0    1  u   1.0\n\n[Chombo Refinement]\n\nLevels           4\nRef_ratio        2 2 2 2 2\nRegrid_interval  2 2 2 2\nRefine_thresh    0.3\nTag_buffer_size  3\nBlock_factor     8\nMax_grid_size    64\nFill_ratio       0.75\n\n[Time]\n\nCFL              0.33\nCFL_max_var      1.1\ntstop            613.202787576\nfirst_dt         1.0e-2\n\n[Solver]\n\nSolver           hllc\n\n[Boundary]\n\nX1-beg           userdef\nX1-end           reflective\nX2-beg           axisymmetric\nX2-end           axisymmetric\nX3-beg           reflective\nX3-end           reflective\n\n[Static Grid Output]\n\nlog_dir          ./outputs/logs\noutput_dir       ./outputs\nuservar          0\ndbl              153.300696894  -1   single_file\nflt              -1.0            -1   single_file\ndbl.h5           -1.0            -1\nflt.h5           -1.0            -1\nvtk              -1.0            -1   single_file\ntab              -1.0            -1\nppm              -1.0            -1\npng              -1.0            -1\nlog              20\nanalysis         -1.0            -1\n\n[Chombo HDF5 output]\n\nCheckpoint_interval  -1.0  0\nPlot_interval        -1.0  0\n\n[Particles]\n\nNparticles          -1    -1\nparticles_dbl       -1.0  -1\nparticles_flt       -1.0  -1\nparticles_vtk       -1.0  -1\nparticles_tab       -1.0  -1\n\n[Parameters]\n\nJET_PWR                     1e45\nJET_SPD                     0.9\nJET_CHI                     100.0\nJET_OA_PRIMARY              15.0\nJET_OA_SECONDARY            15.0\nJET_INJECTION_HEIGHT        0.2\nJET_INITIAL_RADIUS          0.2\nJET_X1O                     0.0\nJET_X2O                     0.0\nJET_X3O                     0.0\nJET_ROTATION_ANGLE          0.0\nJET_START_TIME              0.0\nJET_END_TIME                613.202787576\nJET_ACTIVE_TIME             613.202787576\nJET_EPISODES                1.0\nENV_RHO_0                   2.4e-27\nENV_R_SCALING               144.0\nENV_DELTA_NFW               0.0\nENV_B_EXPONENT              0.38\nENV_TEMP                    3.462e7\nENV_X1O                     0.0\nENV_X2O                     0.0\nENV_X3O                     0.0\nPART_INJECT_FREQUENCY       1.0\nSTELLAR_MASS                0.0\n''')
PY

cp "$PROBLEM/pluto.ini" "$PROBLEM/src/pluto.ini"
cat > "$PROBLEM/src/makefile" <<'MAKE'
ARCH         = Linux.gcc.defs
MAKE

(
  cd "$PROBLEM/src"
  python3 - <<PY
import sys
sys.path.append("$PLUTO_DIR/Tools/Python")
from make_problem import MakeProblem
MakeProblem("$PROBLEM/src", "$PLUTO_DIR", 1, 1)
PY
  make clean
  make -j16
  cp ./pluto ../pluto
) 2>&1 | tee "$LOGS/build.log"

if [ ! -x "$PROBLEM/pluto" ]; then
  echo "[error] build did not produce $PROBLEM/pluto" >&2
  exit 1
fi

(
  cd "$PROBLEM"
  rm -rf outputs
  mkdir -p outputs/logs
  ./pluto -i pluto.ini > outputs/logs/pluto.log 2>&1
) 2>&1 | tee "$LOGS/run.log"

if [ ! -f "$PROBLEM/outputs/data.0004.dbl" ]; then
  echo "[error] expected final dbl output missing" >&2
  ls -R "$PROBLEM/outputs" >&2 || true
  exit 1
fi

cp "$PROBLEM/pluto.ini" "$RESULTS/pluto.ini"
cp "$PROBLEM/src/definitions.h" "$RESULTS/definitions.h"
cp "$PROBLEM/src/definitions_usr.h" "$RESULTS/definitions_usr.h"
cp "$PROBLEM/src/init.c" "$RESULTS/init.c"
cp "$PROBLEM/outputs/logs/pluto.log" "$RESULTS/pluto.log"
cp "$PROBLEM/outputs/dbl.out" "$RESULTS/dbl.out"
cp "$PROBLEM/outputs/grid.out" "$RESULTS/grid.out"
cp "$PROBLEM/outputs/data.0004.dbl" "$RESULTS/data.0004.dbl"

echo "[done] basic jet setup build and run complete"
