#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=${PLUTO_DIR:-"$HOME/git/utas-agn/pluto"}
JET_SETUP=${JET_SETUP:-"$HOME/git/utas-agn/jet-setup"}
BASE=${JET_SETUP_TINY_3D_BASE:-"$HOME/work/pluto-onboarding/jet_setup_tiny_3d_cart"}
PROBLEM="$BASE/problem"
LOGS="$BASE/logs"
RESULTS="$BASE/results"

mkdir -p "$BASE" "$LOGS" "$RESULTS"
rm -rf "$PROBLEM" "$RESULTS"
mkdir -p "$PROBLEM" "$RESULTS"

patch_define() {
  local path="$1"
  local key="$2"
  local value="$3"
  python3 - "$path" "$key" "$value" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
key = sys.argv[2]
value = sys.argv[3]
lines = path.read_text().splitlines()
out = []
replaced = False
for line in lines:
    if line.startswith("#define") and len(line.split()) >= 2 and line.split()[1] == key:
        out.append(f"#define  {key.ljust(28)}   {value}")
        replaced = True
    else:
        out.append(line)
if not replaced:
    raise SystemExit(f"missing define {key} in {path}")
path.write_text("\n".join(out) + "\n")
PY
}

echo "[setup] tiny 3D Cartesian jet-setup problem"
(
  cd "$PROBLEM"
  "$JET_SETUP/tools/setup-problem"
  "$JET_SETUP/tools/create-build-script"
)

patch_define "$PROBLEM/src/definitions.h" PHYSICS HD
patch_define "$PROBLEM/src/definitions.h" DIMENSIONS 3
patch_define "$PROBLEM/src/definitions.h" GEOMETRY CARTESIAN
patch_define "$PROBLEM/src/definitions.h" BODY_FORCE VECTOR
patch_define "$PROBLEM/src/definitions.h" PARTICLES NO
patch_define "$PROBLEM/src/definitions.h" EOS IDEAL
patch_define "$PROBLEM/src/definitions_usr.h" DENSITY_PROFILE ENV_KING
patch_define "$PROBLEM/src/definitions_usr.h" JET_INJECTION_ROTATED NO
patch_define "$PROBLEM/src/definitions_usr.h" JET_RELATIVISTIC_DENSITY NO
patch_define "$PROBLEM/src/definitions_usr.h" PARTICLES_LP_RAISE NO

cat > "$PROBLEM/src/local_make" <<'MAKE'
OBJ += coordinates.o jet.o units.o environment_utilities.o environment.o tools_usr.o read_external_pressure.o galaxy.o
HEADERS += definitions_usr.h pluto_usr.h structs_usr.h coordinates.h jet.h units.h environment_utilities.h environment.h tools_usr.h read_external_pressure.h galaxy.h
MAKE

cat > "$PROBLEM/pluto.ini" <<'INI'
[Grid]

; Tiny full-3D Cartesian jet-setup smoke run.
X1-grid  1  -12.0   48  u   12.0
X2-grid  1  -12.0   48  u   12.0
X3-grid  1  -18.0   72  u   18.0

[Chombo Refinement]

Levels           4
Ref_ratio        2 2 2 2 2
Regrid_interval  2 2 2 2
Refine_thresh    0.3
Tag_buffer_size  3
Block_factor     8
Max_grid_size    64
Fill_ratio       0.75

[Time]

CFL              0.33
CFL_max_var      1.1
tstop            300.0
first_dt         1.0e-3

[Solver]

Solver           hllc

[Boundary]

X1-beg           outflow
X1-end           outflow
X2-beg           outflow
X2-end           outflow
X3-beg           outflow
X3-end           outflow

[Static Grid Output]

log_dir          ./outputs/logs
output_dir       ./outputs
uservar          0
dbl              150.0  -1   single_file
flt              -1.0  -1   single_file
dbl.h5           -1.0  -1
flt.h5           -1.0  -1
vtk              -1.0  -1   single_file
tab              -1.0  -1
ppm              -1.0  -1
png              -1.0  -1
log              20
analysis         -1.0  -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
Plot_interval        -1.0  0

[Particles]

Nparticles          -1    -1
particles_dbl       -1.0  -1
particles_flt       -1.0  -1
particles_vtk       -1.0  -1
particles_tab       -1.0  -1

[Parameters]

JET_PWR                     1e45
JET_SPD                     0.9
JET_CHI                     100.0
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        1.0
JET_INITIAL_RADIUS          1.0
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                300.0
JET_ACTIVE_TIME             300.0
JET_EPISODES                1.0
ENV_RHO_0                   2.4e-27
ENV_R_SCALING               144.0
ENV_DELTA_NFW               0.0
ENV_B_EXPONENT              0.38
ENV_TEMP                    3.462e7
ENV_X1O                     0.0
ENV_X2O                     0.0
ENV_X3O                     0.0
PART_INJECT_FREQUENCY       1.0
STELLAR_MASS                0.0
INI

cp "$PROBLEM/pluto.ini" "$PROBLEM/src/pluto.ini"
cat > "$PROBLEM/src/makefile" <<'MAKE'
ARCH         = Linux.gcc.defs
MAKE

echo "[build] tiny 3D Cartesian jet-setup binary"
(
  cd "$PROBLEM/src"
  python3 - <<PY
import sys
sys.path.append("$PLUTO_DIR/Tools/Python")
from make_problem import MakeProblem
MakeProblem("$PROBLEM/src", "$PLUTO_DIR", 1, 1)
PY
  make clean
  make -j"$(nproc)"
  cp ./pluto ../pluto
) 2>&1 | tee "$LOGS/build.log"

if [ ! -x "$PROBLEM/pluto" ]; then
  echo "[error] build did not produce $PROBLEM/pluto" >&2
  exit 1
fi

echo "[run] tiny 3D Cartesian jet-setup smoke"
(
  cd "$PROBLEM"
  rm -rf outputs
  mkdir -p outputs/logs
  ./pluto -i pluto.ini > outputs/logs/pluto.log 2>&1
) 2>&1 | tee "$LOGS/run.log"

if [ ! -f "$PROBLEM/outputs/data.0002.dbl" ]; then
  echo "[error] expected final dbl output missing" >&2
  ls -R "$PROBLEM/outputs" >&2 || true
  exit 1
fi

cp "$PROBLEM/pluto.ini" "$RESULTS/pluto.ini"
cp "$PROBLEM/src/definitions.h" "$RESULTS/definitions.h"
cp "$PROBLEM/src/definitions_usr.h" "$RESULTS/definitions_usr.h"
cp "$PROBLEM/outputs/logs/pluto.log" "$RESULTS/pluto.log"
cp "$PROBLEM/outputs/dbl.out" "$RESULTS/dbl.out"
cp "$PROBLEM/outputs/grid.out" "$RESULTS/grid.out"
cp "$PROBLEM/outputs"/data.*.dbl "$RESULTS/"

echo "[done] tiny 3D Cartesian jet-setup smoke run complete"
