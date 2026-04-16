#!/usr/bin/env bash
set -euo pipefail

export PLUTO_DIR=/home/bwbrook/git/utas-agn/pluto
BASE=/home/bwbrook/work/pluto-onboarding/rt_instability
SRC=$PLUTO_DIR/Test_Problems/MHD/Rayleigh_Taylor
BUILDS=$BASE/builds
RUNS=$BASE/runs
LOGS=$BASE/logs

mkdir -p "$BUILDS" "$RUNS" "$LOGS"

write_ini() {
  local target="$1"
  cat > "$target" <<INI
[Grid]

X1-grid  1   -0.5   128   u    0.5
X2-grid  1   -1.0   256   u    1.0
X3-grid  1   -0.5     1   u    0.5

[Time]

CFL            0.4
CFL_max_var    1.1
tstop          15.0
first_dt       1.e-3

[Solver]

Solver        roe

[Boundary]

X1-beg    periodic
X1-end    periodic
X2-beg    reflective
X2-end    reflective
X3-beg    periodic
X3-end    periodic

[Static Grid Output]

uservar    0
dbl        5.0  -1   single_file
flt       -1.0  -1   single_file
vtk       -1.0  -1   multiple_files
tab       -1.0  -1
ppm       -1.0  -1
png       -1.0  -1
log         10
analysis  -1.0  -1

[Chombo HDF5 output]

Checkpoint_interval  -1.0  0
Plot_interval        -1.0  0

[Parameters]

ETA                         2.0
GRAV                        -0.1
CHI                         0.0
INI
}

build_case() {
  local scheme="$1"
  local template="$2"
  local build_dir="$BUILDS/$scheme"
  mkdir -p "$build_dir"
  echo "[build] $scheme"
  rm -f "$build_dir"/init.c "$build_dir"/definitions.h "$build_dir"/makefile "$build_dir"/pluto.ini
  cp "$SRC/init.c" "$build_dir/init.c"
  cp "$SRC/$template" "$build_dir/definitions.h"

  case "$scheme" in
    flat_euler)
      perl -0pi -e 's/^#define  RECONSTRUCTION\s+\S+/#define  RECONSTRUCTION                 FLAT/m; s/^#define  TIME_STEPPING\s+\S+/#define  TIME_STEPPING                  EULER/m' "$build_dir/definitions.h"
      ;;
    linear_hancock)
      perl -0pi -e 's/^#define  TIME_STEPPING\s+\S+/#define  TIME_STEPPING                  HANCOCK/m' "$build_dir/definitions.h"
      ;;
    parabolic_rk3)
      :
      ;;
    *)
      echo "Unknown scheme $scheme" >&2
      exit 1
      ;;
  esac

  write_ini "$build_dir/pluto.ini"
  cat > "$build_dir/makefile" <<MAKE
ARCH         = Linux.gcc.defs
MAKE
  (
    cd "$build_dir"
    python3 - <<PY
import sys
sys.path.append("$PLUTO_DIR/Tools/Python")
from make_problem import MakeProblem
MakeProblem("$build_dir", "$PLUTO_DIR", 1, 1)
PY
    make clean
    make -j16
  ) | tee "$LOGS/build_${scheme}.log"
}

run_case() {
  local scheme="$1"
  local case_dir="$RUNS/$scheme"
  mkdir -p "$case_dir"
  ln -sfn "$BUILDS/$scheme/pluto" "$case_dir/pluto"
  write_ini "$case_dir/pluto.ini"
  echo "[run] $scheme"
  (
    cd "$case_dir"
    rm -f data.* *.dbl *.flt *.vtk *.tab dbl.out flt.out vtk.out tab.out grid.out restart.out analysis.out time.out pluto.log
    ./pluto -i pluto.ini > pluto.log 2>&1
  )
  if [ ! -f "$case_dir/data.0003.dbl" ]; then
    echo "[error] expected final output missing for $scheme" >&2
    return 1
  fi
}

build_case flat_euler definitions_03.h
build_case linear_hancock definitions_04.h
build_case parabolic_rk3 definitions_03.h

for scheme in flat_euler linear_hancock parabolic_rk3; do
  run_case "$scheme"
done

echo "[done] RT instability matrix complete"
