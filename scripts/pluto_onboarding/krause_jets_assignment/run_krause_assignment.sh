#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=/home/bwbrook/git/utas-agn/pluto
JET_SETUP=/home/bwbrook/git/utas-agn/jet-setup
BASE=/home/bwbrook/work/pluto-onboarding/krause_jets_assignment
PROBLEM=$BASE/problem
RUNS=$BASE/runs
LOGS=$BASE/logs
RESULTS=$BASE/results
OUTPUT_INTERVAL=61.320278758
TSTOP=613.202787576

mkdir -p "$BASE" "$RUNS" "$LOGS" "$RESULTS"
rm -rf "$PROBLEM"
mkdir -p "$PROBLEM"

cd "$PROBLEM"
"$JET_SETUP/tools/setup-problem"
"$JET_SETUP/tools/create-build-script"

python3 - <<'PY'
from pathlib import Path

problem = Path('/home/bwbrook/work/pluto-onboarding/krause_jets_assignment/problem')


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
PY

cat > "$PROBLEM/src/makefile" <<'MAKE'
ARCH         = Linux.gcc.defs
MAKE

cat > "$PROBLEM/src/pluto.ini" <<'INI'
[Grid]

; Krause-style jet assignment build template
X1-grid  1  0.2   192  u  60.0
X2-grid  1  0.01  64  u  3.141592653589793
X3-grid  1  0.0    1  u   1.0

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
tstop            613.202787576
first_dt         1.0e-2

[Solver]

Solver           hllc

[Boundary]

X1-beg           userdef
X1-end           reflective
X2-beg           axisymmetric
X2-end           axisymmetric
X3-beg           reflective
X3-end           reflective

[Static Grid Output]

log_dir          ./outputs/logs
output_dir       ./outputs
uservar          0
dbl              61.320278758   -1   single_file
flt              -1.0           -1   single_file
dbl.h5           -1.0           -1
flt.h5           -1.0           -1
vtk              -1.0           -1   single_file
tab              -1.0           -1
ppm              -1.0           -1
png              -1.0           -1
log              20
analysis         -1.0           -1

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
JET_INJECTION_HEIGHT        0.2
JET_INITIAL_RADIUS          0.2
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                613.202787576
JET_ACTIVE_TIME             613.202787576
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

write_ini() {
  local target="$1"
  local jet_power="$2"
  cat > "$target" <<INI
[Grid]

X1-grid  1  0.2   192  u  60.0
X2-grid  1  0.01  64  u  3.141592653589793
X3-grid  1  0.0    1  u   1.0

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
tstop            ${TSTOP}
first_dt         1.0e-2

[Solver]

Solver           hllc

[Boundary]

X1-beg           userdef
X1-end           reflective
X2-beg           axisymmetric
X2-end           axisymmetric
X3-beg           reflective
X3-end           reflective

[Static Grid Output]

log_dir          ./outputs/logs
output_dir       ./outputs
uservar          0
dbl              ${OUTPUT_INTERVAL}   -1   single_file
flt              -1.0                 -1   single_file
dbl.h5           -1.0                 -1
flt.h5           -1.0                 -1
vtk              -1.0                 -1   single_file
tab              -1.0                 -1
ppm              -1.0                 -1
png              -1.0                 -1
log              20
analysis         -1.0                 -1

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

JET_PWR                     ${jet_power}
JET_SPD                     0.9
JET_CHI                     100.0
JET_OA_PRIMARY              15.0
JET_OA_SECONDARY            15.0
JET_INJECTION_HEIGHT        0.2
JET_INITIAL_RADIUS          0.2
JET_X1O                     0.0
JET_X2O                     0.0
JET_X3O                     0.0
JET_ROTATION_ANGLE          0.0
JET_START_TIME              0.0
JET_END_TIME                ${TSTOP}
JET_ACTIVE_TIME             ${TSTOP}
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
}

run_case() {
  local case_name="$1"
  local jet_power="$2"
  local case_dir="$RUNS/$case_name"
  local result_dir="$RESULTS/$case_name"

  rm -rf "$case_dir" "$result_dir"
  mkdir -p "$case_dir" "$result_dir"

  cp "$PROBLEM/pluto" "$case_dir/pluto"
  cp "$PROBLEM/src/definitions.h" "$case_dir/definitions.h"
  cp "$PROBLEM/src/definitions_usr.h" "$case_dir/definitions_usr.h"
  cp "$PROBLEM/src/local_make" "$case_dir/local_make"
  write_ini "$case_dir/pluto.ini" "$jet_power"

  echo "[run] $case_name (JET_PWR=$jet_power)"
  (
    cd "$case_dir"
    ./pluto -i pluto.ini
  ) 2>&1 | tee "$LOGS/${case_name}.log"

  if [ ! -f "$case_dir/outputs/dbl.out" ]; then
    echo "[error] expected dbl.out missing for $case_name" >&2
    exit 1
  fi

  local nlast
  nlast=$(tail -n 1 "$case_dir/outputs/dbl.out" | awk '{print $1}')
  if [ ! -f "$case_dir/outputs/data.$(printf '%04d' "$nlast").dbl" ]; then
    echo "[error] expected final dbl output missing for $case_name" >&2
    exit 1
  fi

  shopt -s nullglob
  cp "$case_dir/pluto.ini" "$result_dir/"
  cp "$case_dir/definitions.h" "$result_dir/"
  cp "$case_dir/definitions_usr.h" "$result_dir/"
  cp "$case_dir/local_make" "$result_dir/"
  cp "$case_dir/outputs/dbl.out" "$result_dir/"
  cp "$case_dir/outputs/grid.out" "$result_dir/"
  cp "$case_dir/outputs"/data.*.dbl "$result_dir/"
  shopt -u nullglob
}

run_case baseline 1e45
run_case higher_power 3e45

echo "[done] Krause-style jet assignment runs complete"
